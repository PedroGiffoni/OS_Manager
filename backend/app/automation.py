"""Small, deterministic automation runner. It never evaluates user code."""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .audit_trail import add_task_watcher, notify_task_watchers, record_task_changes
from .models import AutomationRule, AutomationRun, Audit, Comment, Task, User
from .security import active_internal_user
from fastapi import HTTPException
from .workflows import apply_custom_field_updates, custom_fields_match, task_link_conditions


def matches(rule, task, db=None, event_context=None):
    conditions = rule.conditions or {}
    if "comment_contains" in conditions:
        if not event_context or not event_context.get("comment_body"):
            return False
        if conditions["comment_contains"].casefold() not in event_context["comment_body"].casefold():
            return False
    if "attachment_media_types" in conditions:
        if not event_context or event_context.get("media_type") not in conditions["attachment_media_types"]:
            return False
    if "link_types" in conditions:
        if not event_context or event_context.get("link_type") not in conditions["link_types"]:
            return False
    if "changed_fields" in conditions:
        if not event_context or not set(conditions["changed_fields"]).intersection(
            event_context.get("changed_fields", [])
        ):
            return False
    if "sprint_scope_actions" in conditions:
        if not event_context or event_context.get("action") not in conditions["sprint_scope_actions"]:
            return False
    if conditions.get("custom_field_equals"):
        if custom_fields_match(db, task, conditions["custom_field_equals"]) is not True:
            return False
    if conditions.get("statuses") and task.status not in conditions["statuses"]:
        return False
    if conditions.get("work_types") and task.work_type not in conditions["work_types"]:
        return False
    if conditions.get("approval_states") and task.approval not in conditions["approval_states"]:
        return False
    if conditions.get("assignee_user_ids") and task.assignee_user_id not in conditions["assignee_user_ids"]:
        return False
    if "priority_min" in conditions and task.priority < conditions["priority_min"]:
        return False
    if "priority_max" in conditions and task.priority > conditions["priority_max"]:
        return False
    if conditions.get("labels"):
        card_labels = {label.get("text", "").casefold() for label in task.labels or []}
        if not card_labels.intersection(label.casefold() for label in conditions["labels"]):
            return False
    if "due_set" in conditions and (task.due is not None) is not conditions["due_set"]:
        return False
    today = datetime.now(timezone.utc).date()
    if "overdue" in conditions:
        is_overdue = bool(task.due and date.fromisoformat(task.due) < today)
        if is_overdue is not conditions["overdue"]:
            return False
    if "due_within_days" in conditions:
        if not task.due:
            return False
        due_date = date.fromisoformat(task.due)
        if not today <= due_date <= today + timedelta(days=conditions["due_within_days"]):
            return False
    for condition_key, event_key in (
        ("development_providers", "provider"),
        ("development_event_types", "event_type"),
        ("development_states", "state"),
    ):
        if condition_key in conditions:
            if event_context is None:
                return False
            allowed_values = {str(value).casefold() for value in conditions[condition_key]}
            if str(event_context.get(event_key, "")).casefold() not in allowed_values:
                return False
    link_values = None
    for key in ("release_assigned", "component_assigned", "blocked"):
        if key not in conditions:
            continue
        if link_values is None:
            link_values = task_link_conditions(db, task)
        if link_values[key] is not conditions[key]:
            return False
    return True


def run_automations(db, actor, task, trigger, rule_ids=None, event_context=None):
    """Apply matching safe actions in the triggering transaction."""
    query = (
        select(AutomationRule)
        .where(AutomationRule.enabled.is_(True), AutomationRule.trigger == trigger)
        .order_by(AutomationRule.id)
        .limit(100)
    )
    if rule_ids is not None:
        query = query.where(AutomationRule.id.in_(rule_ids))
    rules = db.scalars(query)
    for rule in rules:
        rule_actor = actor or db.get(User, rule.author_id)
        if not rule_actor or not matches(rule, task, db, event_context):
            continue
        before = {
            "priority": task.priority,
            "labels": list(task.labels or []),
            "due": task.due,
            "assignee_user_id": task.assignee_user_id,
        }
        comment_ids = []
        watcher_ids = []
        skipped_actions = []
        custom_field_changes = {}
        actions = rule.actions or [{"action": rule.action, "config": rule.config or {}}]
        for configured in actions:
            kind, config = configured["action"], configured["config"]
            if kind == "set_priority":
                task.priority = config["priority"]
            elif kind == "add_label":
                text = config["text"].strip()
                labels = list(task.labels or [])
                if (
                    not any(label["text"].casefold() == text.casefold() for label in labels)
                    and len(labels) < 8
                ):
                    labels.append({"text": text, "color": config["color"]})
                    task.labels = labels
            elif kind == "remove_label":
                text = config["text"].strip().casefold()
                task.labels = [
                    label for label in task.labels or []
                    if label.get("text", "").casefold() != text
                ]
            elif kind == "add_comment":
                comment = Comment(
                    task_id=task.id,
                    body=config["body"].strip(),
                    author_id=rule_actor.id,
                )
                db.add(comment)
                db.flush()
                comment_ids.append(comment.id)
            elif kind == "set_due_after_days":
                created_date = date.fromisoformat(task.created_at[:10])
                task.due = (created_date + timedelta(days=config["days"])).isoformat()
            elif kind == "assign_internal_user":
                try:
                    assigned = active_internal_user(db, config["user_id"])
                except HTTPException:
                    skipped_actions.append({"action": kind, "reason": "assignee_unavailable"})
                    continue
                task.assignee_user_id = assigned.id
            elif kind == "add_watcher":
                try:
                    watcher = active_internal_user(db, config["user_id"])
                except HTTPException:
                    skipped_actions.append({"action": kind, "reason": "watcher_unavailable"})
                    continue
                if add_task_watcher(db, task.id, watcher.id):
                    watcher_ids.append(watcher.id)
            elif kind == "set_custom_fields":
                for identity, change in apply_custom_field_updates(
                    db, rule_actor, task, config["values"]
                ).items():
                    custom_field_changes.setdefault(identity, change)
                    custom_field_changes[identity]["after"] = change["after"]
        after = {
            "priority": task.priority,
            "labels": list(task.labels or []),
            "due": task.due,
            "assignee_user_id": task.assignee_user_id,
        }
        custom_field_changes = {
            identity: change
            for identity, change in custom_field_changes.items()
            if change["before"] != change["after"]
        }
        if before == after and not custom_field_changes and not comment_ids and not watcher_ids and not skipped_actions:
            continue
        changes = {
            key: {"before": before[key], "after": after[key]}
            for key in before
            if before[key] != after[key]
        }
        changes.update(custom_field_changes)
        details = {
            "actor_name": rule_actor.username,
            "rule_id": rule.id,
            "rule_name": rule.name,
            "trigger": trigger,
            "changes": changes,
            "comment_id": comment_ids[0] if comment_ids else None,
            "comment_ids": comment_ids,
            "watcher_ids_added": watcher_ids,
            "skipped_actions": skipped_actions,
            "development_event": event_context if trigger == "development_event" else None,
            "due_change": event_context if trigger == "due_changed" else None,
            "priority_change": event_context if trigger == "priority_changed" else None,
            "task_link": (
                {
                    key: event_context[key]
                    for key in ("link_type", "target_task_id")
                    if key in event_context
                }
                if trigger in {"link_added", "link_removed"} and event_context
                else None
            ),
            "source_event": (
                {
                    key: event_context[key]
                    for key in ("comment_id", "attachment_id", "media_type", "size")
                    if key in event_context
                }
                if trigger in {"comment_added", "attachment_added"} and event_context
                else None
            ),
            "changed_fields": (
                sorted(set(event_context.get("changed_fields", [])))
                if trigger == "field_changed" and event_context
                else None
            ),
            "sprint_scope_change": (
                {
                    key: event_context[key]
                    for key in ("action", "sprint_id")
                    if key in event_context
                }
                if trigger == "sprint_scope_changed" and event_context
                else None
            ),
        }
        audit_row = Audit(
            actor_id=rule_actor.id,
            entity="task",
            entity_id=task.id,
            action="automation_applied",
            details=details,
        )
        db.add(audit_row)
        record_task_changes(db, audit_row, "task", "automation_applied", details)
        notify_task_watchers(db, rule_actor, task.id, "automation_applied")


def run_due_scheduled_automations(session_factory, now=None):
    """Run each enabled daily/weekly rule once per eligible UTC date."""
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    instant = instant.astimezone(timezone.utc)
    day, hhmm = instant.date().isoformat(), instant.strftime("%H:%M")
    with session_factory() as lookup:
        rule_ids = list(
            lookup.scalars(
                select(AutomationRule.id).where(
                    AutomationRule.enabled.is_(True),
                    AutomationRule.trigger == "scheduled_daily",
                    AutomationRule.schedule_time <= hhmm,
                )
            )
        )
    completed = 0
    for rule_id in rule_ids:
        with session_factory() as db:
            rule = db.get(AutomationRule, rule_id)
            if rule:
                # Scheduled jobs run without an HTTP request. Scope all card reads and
                # automation writes to the rule's board explicitly.
                db.info["board_id"] = rule.board_id
            if (
                not rule
                or not rule.enabled
                or rule.trigger != "scheduled_daily"
                or not rule.schedule_time
                or rule.schedule_time > hhmm
                or rule.schedule_frequency == "weekly"
                and instant.weekday() not in (rule.schedule_weekdays or [])
            ):
                continue
            run = AutomationRun(rule_id=rule.id, run_date=day, completed_at=instant.isoformat())
            db.add(run)
            try:
                # Claim before applying actions so concurrent workers cannot double-run.
                db.flush()
            except IntegrityError:
                db.rollback()
                continue
            actor = db.get(User, rule.author_id)
            if actor:
                last_id = 0
                while True:
                    tasks = list(
                        db.scalars(
                            select(Task)
                            .where(Task.id > last_id, Task.archived.is_(False))
                            .order_by(Task.id)
                            .limit(250)
                        )
                    )
                    if not tasks:
                        break
                    for task in tasks:
                        run_automations(db, actor, task, "scheduled_daily", [rule.id])
                    last_id = tasks[-1].id
            db.commit()
            completed += 1
    return completed
