"""Version diffs for business mutations; no endpoints modify or delete audit events."""

from copy import deepcopy
import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .email_notifications import queue_notification_emails
from .push_notifications import queue_web_push_notifications
from .models import InAppNotification, TaskFieldChange, TaskWatcher


def changes(before, after):
    return [
        {"field": key, "before": deepcopy(before.get(key)), "after": deepcopy(value)}
        for key, value in after.items()
        if before.get(key) != value
    ]


def record_task_changes(db, audit_row, entity, action, details):
    """Normalize task history into portable scalar rows for advanced CHANGED queries."""
    if entity != "task":
        return
    entries = []
    if action == "status_changed" and "origin" in details and "destination" in details:
        entries.append(
            {
                "field": "status",
                "kind": "value",
                "before": details["origin"],
                "after": details["destination"],
            }
        )
    raw_changes = details.get("changes", [])
    if isinstance(raw_changes, list):
        entries.extend(change for change in raw_changes if isinstance(change, dict))
    elif isinstance(raw_changes, dict):
        entries.extend(
            {"field": field, "kind": "value", **change}
            for field, change in raw_changes.items()
            if isinstance(change, dict)
        )
    for change in entries:
        field = change.get("field")
        if not isinstance(field, str) or not field or "before" not in change or "after" not in change:
            continue
        kind = change.get("kind", "value")
        if kind == "configuration" and all(
            value is None or isinstance(value, dict)
            for value in (change["before"], change["after"])
        ):
            # Store scalar-by-property aliases so config history is queryable
            # without relying on a database-specific JSON query operator.
            before_config = change["before"] or {}
            after_config = change["after"] or {}
            for prop in sorted(before_config.keys() | after_config.keys()):
                before_value = before_config.get(prop)
                after_value = after_config.get(prop)
                if before_value == after_value:
                    continue
                db.add(
                    TaskFieldChange(
                        audit=audit_row,
                        field=f"config_{field}_{prop}",
                        kind="configuration_property",
                        before_json=json.dumps(before_value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                        after_json=json.dumps(after_value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    )
                )
        db.add(
            TaskFieldChange(
                audit=audit_row,
                field=field,
                kind=kind,
                before_json=json.dumps(change["before"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                after_json=json.dumps(change["after"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            )
        )


def notify_task_watchers(db, actor, task_id, action, timestamp=None):
    watcher_ids = db.scalars(
        select(TaskWatcher.user_id).where(
            TaskWatcher.task_id == task_id,
            TaskWatcher.user_id != actor.id,
        )
    )
    notifications = [
        InAppNotification(
            user_id=watcher_id,
            task_id=task_id,
            actor_id=actor.id,
            action=action,
            **({"created_at": timestamp} if timestamp else {}),
        )
        for watcher_id in watcher_ids
    ]
    db.add_all(notifications)
    queue_notification_emails(db, notifications)
    queue_web_push_notifications(db, notifications)


def add_task_watcher(db, task_id, user_id):
    """Add a watcher once, including when two rules race on the unique key."""
    existing = db.scalar(
        select(TaskWatcher).where(
            TaskWatcher.task_id == task_id,
            TaskWatcher.user_id == user_id,
        )
    )
    if existing:
        return False
    try:
        with db.begin_nested():
            db.add(TaskWatcher(task_id=task_id, user_id=user_id))
            db.flush()
    except IntegrityError:
        return False
    return True


def field_changes(previous, fields, values):
    old_fields = {f["id"]: f for f in previous.fields} if previous else {}
    new_fields = {f["id"]: f for f in fields}
    old_values = previous.values if previous else {}
    result = []
    for key in sorted(old_fields.keys() | new_fields.keys()):
        old, new = old_fields.get(key), new_fields.get(key)
        definition = new or old
        visibility = sorted(set((old or new)["visible_to"]) & set((new or old)["visible_to"]))
        for kind, before, after in [
            ("configuration", old, new),
            ("value", old_values.get(key), values.get(key)),
        ]:
            if before != after:
                result.append(
                    {
                        "field": key,
                        "label": definition["label"],
                        "kind": kind,
                        "before": deepcopy(before),
                        "after": deepcopy(after),
                        "visible_to": visibility,
                    }
                )
    return result


def visible_details(details, user, financial, current_fields):
    def clean(value):
        if isinstance(value, dict):
            return {
                key: clean(item)
                for key, item in value.items()
                if financial or "cost" not in key and "rate" not in key
            }
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    result = clean(details)
    if isinstance(details.get("changes"), list):
        result["changes"] = [
            clean({key: value for key, value in change.items() if key != "visible_to"})
            for change in details["changes"]
            if isinstance(change, dict) and "field" in change
            if (
                (financial or "cost" not in change["field"] and "rate" not in change["field"])
                and ("visible_to" not in change or user.role in change["visible_to"])
                and (
                    change["field"] not in current_fields
                    or user.role in current_fields[change["field"]]["visible_to"]
                )
            )
        ]
    elif isinstance(details.get("changes"), dict):
        result["changes"] = {
            key: clean(value)
            for key, value in details["changes"].items()
            if (financial or "cost" not in key and "rate" not in key)
            and (
                key not in current_fields
                or user.role in current_fields[key]["visible_to"]
            )
        }
    return result
