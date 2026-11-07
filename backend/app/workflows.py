"""Resolution helpers for persisted transition policies."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from .audit_trail import add_task_watcher, notify_task_watchers, record_task_changes
from sqlalchemy import select

from .models import Audit, Comment, SchemaVersion, Task, TaskComponent, TaskDependency, TaskRelease
from .security import active_internal_user

@dataclass(frozen=True)
class EffectiveTransitionPolicy:
    enabled: bool
    allowed_roles: frozenset[str] | None
    required_fields: tuple[str, ...]
    conditions: tuple[dict, ...]
    actions: tuple[dict, ...]


def transition_policy(rows, work_type):
    """Merge the base rule and the selected work type's additional restrictions."""
    for row in rows:
        scoped_types = getattr(row, "work_types", None) or []
        base_applies = not scoped_types or work_type in scoped_types
        type_rule = (getattr(row, "type_rules", None) or {}).get(work_type)
        if not base_applies and not type_rule:
            continue

        enabled = getattr(row, "enabled", True) if base_applies else True
        base_roles = set(getattr(row, "roles", None) or []) if base_applies else set()
        required_fields = list(getattr(row, "required_fields", None) or []) if base_applies else []
        if type_rule:
            enabled = enabled and type_rule.get("enabled", True)
            type_roles = set(type_rule.get("roles", []))
            if type_roles:
                base_roles = type_roles
            required_fields.extend(type_rule.get("required_fields", []))
        base_conditions = list(getattr(row, "conditions", None) or []) if base_applies else []
        base_actions = list(getattr(row, "actions", None) or []) if base_applies else []
        type_conditions = (type_rule or {}).get("conditions", [])
        type_actions = (type_rule or {}).get("actions", [])

        return EffectiveTransitionPolicy(
            enabled=enabled,
            allowed_roles=frozenset(base_roles) if base_roles else None,
            required_fields=tuple(dict.fromkeys(required_fields)),
            conditions=tuple(base_conditions + type_conditions),
            actions=tuple(base_actions + type_actions),
        )
    return None


def task_link_conditions(db, task):
    if db is None:
        return {"release_assigned": False, "component_assigned": False, "blocked": False}
    release_assigned = db.scalar(
        select(TaskRelease.id).where(TaskRelease.task_id == task.id).limit(1)
    ) is not None
    component_assigned = db.scalar(
        select(TaskComponent.id).where(TaskComponent.task_id == task.id).limit(1)
    ) is not None
    blocked = db.scalar(
        select(TaskDependency.id)
        .join(Task, Task.id == TaskDependency.source_task_id)
        .where(
            TaskDependency.target_task_id == task.id,
            TaskDependency.link_type == "blocks",
            Task.status != "done",
            Task.archived.is_(False),
        )
        .limit(1)
    ) is not None
    return {
        "release_assigned": release_assigned,
        "component_assigned": component_assigned,
        "blocked": blocked,
    }


def apply_custom_field_updates(db, actor, task, updates):
    """Version safe scalar edits to existing, editable card fields."""
    from .services import current_schema, fail, validate_fields

    schema = current_schema(db, task)
    if not schema:
        fail("O card não possui campos personalizados configurados.")
    definitions = {field["id"]: field for field in schema.fields}
    values = dict(schema.values or {})
    for identity, value in updates.items():
        field = definitions.get(identity)
        if not field or field["type"] not in {"short_text", "long_text", "number", "date", "select", "checkbox"}:
            fail("A ação referencia um campo editável indisponível.")
        if actor.role not in field["editable_by"] or actor.role not in field["visible_to"]:
            fail("O perfil que disparou a ação não pode editar esse campo.", 403)
        if task.status in field["required_for"] and (
            value is None or value == "" or field["type"] == "checkbox" and value is not True
        ):
            fail("A ação não pode limpar um campo obrigatório na etapa atual.")
        values[identity] = value

    validate_fields(schema.fields, values)
    changes = {
        identity: {
            "before": schema.values.get(identity),
            "after": values.get(identity),
            "visible_to": list(definitions[identity]["visible_to"]),
        }
        for identity in updates
        if schema.values.get(identity) != values.get(identity)
    }
    if changes:
        db.add(
            SchemaVersion(
                task_id=task.id,
                version=schema.version + 1,
                fields=schema.fields,
                values=values,
                author_id=actor.id,
            )
        )
    return changes


def custom_fields_match(db, task, expected_values):
    if db is None or not expected_values:
        return None
    schema = db.scalar(
        select(SchemaVersion)
        .where(SchemaVersion.task_id == task.id)
        .order_by(SchemaVersion.version.desc())
    )
    if not schema:
        return None
    definitions = {field["id"] for field in schema.fields}
    values = schema.values or {}
    for field_id, expected in expected_values.items():
        if field_id not in definitions:
            return None
        actual = values.get(field_id)
        if isinstance(actual, bool) or isinstance(expected, bool):
            if type(actual) is not type(expected) or actual != expected:
                return False
        elif isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
            try:
                if Decimal(str(actual)) != Decimal(str(expected)):
                    return False
            except (InvalidOperation, ValueError):
                return False
        elif type(actual) is not type(expected) or actual != expected:
            return False
    return True


def conditions_match(conditions, task, db=None):
    actual_values = {
        "approval": task.approval,
        "work_type": task.work_type,
        "priority": task.priority,
        "supplier_assigned": task.supplier_id is not None,
        "due_set": task.due is not None,
        "parent_set": task.parent_id is not None,
        "assignee": getattr(task, "assignee_user_id", None),
    }
    evaluation_date = datetime.now(timezone.utc).date()
    link_values = None
    for condition in conditions or ():
        field = condition["field"]
        if field in {"due_overdue", "due_within_days"}:
            due = date.fromisoformat(task.due) if task.due else None
            if field == "due_overdue":
                actual = bool(due and due < evaluation_date and task.status != "done")
                expected = condition["value"]
            else:
                days = condition["value"]
                actual = bool(due and evaluation_date <= due <= evaluation_date + timedelta(days=days))
                expected = True
            if condition["operator"] == "eq" and actual != expected:
                return False
            if condition["operator"] == "not_eq" and actual == expected:
                return False
            continue
        if field == "custom_field_equals":
            is_match = custom_fields_match(
                db, task, {condition["custom_field_id"]: condition["value"]}
            )
            if is_match is None:
                return False
            if condition["operator"] == "eq" and not is_match:
                return False
            if condition["operator"] == "not_eq" and is_match:
                return False
            continue
        if field in {"release_assigned", "component_assigned", "blocked"}:
            if link_values is None:
                link_values = task_link_conditions(db, task)
            actual = link_values[field]
            expected = condition["value"]
            if condition["operator"] == "eq" and actual != expected:
                return False
            if condition["operator"] == "not_eq" and actual == expected:
                return False
            continue
        if field == "label":
            has_label = any(
                (item.get("text") or "").casefold() == condition["value"].casefold()
                for item in task.labels or []
            )
            actual = has_label
            expected = True
        else:
            actual = actual_values[field]
            expected = condition["value"]
        operator = condition["operator"]
        if operator == "eq" and actual != expected:
            return False
        if operator == "not_eq" and actual == expected:
            return False
        if operator == "gte" and actual < expected:
            return False
        if operator == "lte" and actual > expected:
            return False
    return True


def apply_transition_actions(db, actor, task, actions, source, target):
    configured_actions = tuple(actions or ())
    # Validate every reference before applying any side effect, so an invalid
    # assignee cannot leave comments or other changes behind in the transaction.
    assignees = {
        configured["config"]["user_id"]: active_internal_user(db, configured["config"]["user_id"])
        for configured in configured_actions
        if configured["action"] == "assign_internal_user"
    }
    watchers = {
        configured["config"]["user_id"]: active_internal_user(db, configured["config"]["user_id"])
        for configured in configured_actions
        if configured["action"] == "add_watcher"
    }
    before = {"priority": task.priority, "labels": list(task.labels or []), "due": task.due, "assignee_user_id": task.assignee_user_id}
    comment_ids = []
    watcher_ids = []
    custom_field_changes = {}
    for configured in configured_actions:
        kind, config = configured["action"], configured["config"]
        if kind == "set_priority":
            task.priority = config["priority"]
        elif kind == "add_label":
            labels = list(task.labels or [])
            label = config["text"].strip()
            if any(item.get("text", "").casefold() == label.casefold() for item in labels):
                continue
            if len(labels) >= 8:
                from .services import fail

                fail("A ação do workflow excede o limite de etiquetas do card.", 409)
            labels.append({"text": label, "color": config["color"]})
            task.labels = labels
        elif kind == "remove_label":
            label = config["text"].strip().casefold()
            task.labels = [
                item for item in task.labels or []
                if item.get("text", "").casefold() != label
            ]
        elif kind == "set_due_after_days":
            created_date = date.fromisoformat(task.created_at[:10])
            task.due = (created_date + timedelta(days=config["days"])).isoformat()
        elif kind == "assign_internal_user":
            task.assignee_user_id = assignees[config["user_id"]].id
        elif kind == "add_watcher":
            watcher_id = watchers[config["user_id"]].id
            if add_task_watcher(db, task.id, watcher_id):
                watcher_ids.append(watcher_id)
        elif kind == "set_custom_fields":
            for identity, change in apply_custom_field_updates(
                db, actor, task, config["values"]
            ).items():
                custom_field_changes.setdefault(identity, change)
                custom_field_changes[identity]["after"] = change["after"]
        else:
            comment = Comment(task_id=task.id, body=config["body"].strip(), author_id=actor.id)
            db.add(comment)
            db.flush()
            comment_ids.append(comment.id)
    after = {"priority": task.priority, "labels": list(task.labels or []), "due": task.due, "assignee_user_id": task.assignee_user_id}
    changes = [
        {"field": key, "kind": "value", "before": before[key], "after": after[key]}
        for key in before
        if before[key] != after[key]
    ]
    changes.extend(
        {"field": identity, "kind": "value", **change}
        for identity, change in custom_field_changes.items()
        if change["before"] != change["after"]
    )
    if not changes and not comment_ids and not watcher_ids:
        return
    details = {
        "actor_name": actor.username,
        "source": source,
        "destination": target,
        "changes": changes,
        "comment_ids": comment_ids,
        "watcher_ids_added": watcher_ids,
    }
    row = Audit(
        actor_id=actor.id,
        entity="task",
        entity_id=task.id,
        action="workflow_actions_applied",
        details=details,
    )
    db.add(row)
    record_task_changes(db, row, "task", "workflow_actions_applied", details)
    notify_task_watchers(db, actor, task.id, "workflow_actions_applied")
