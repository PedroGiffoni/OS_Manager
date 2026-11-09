"""Label and measure helpers for configurable dashboard widgets."""

from datetime import date, datetime, timezone

from sqlalchemy import select

from .models import (
    Audit,
    Component,
    KanbanColumn,
    Release,
    Sprint,
    Supplier,
    Task,
    TaskComponent,
    TaskRelease,
    User,
)
from .services import get_column


def filtered_widget_query(query, jql, role, actor_user_id=None):
    from .query_language import apply_query

    return apply_query(
        query,
        jql,
        allow_configuration_history=role == "admin",
        actor_user_id=actor_user_id,
        actor_role=role,
    )


WORK_TYPE_LABELS = {
    "epic": "Épico",
    "story": "História",
    "task": "Tarefa",
    "bug": "Bug",
    "subtask": "Subtarefa",
}


def widget_group_keys(db, task, dimension, today=None, show_parent_details=True, resolved_at=None):
    if dimension == "status":
        column = get_column(db, task.status)
        return [column.title if column else task.status]
    if dimension == "priority":
        return [f"Prioridade {task.priority}"]
    if dimension == "supplier":
        supplier = db.get(Supplier, task.supplier_id) if task.supplier_id else None
        return [supplier.name if supplier else "Não atribuído"]
    if dimension == "sprint":
        sprint = db.get(Sprint, task.sprint_id) if task.sprint_id else None
        return [sprint.name if sprint else "Sem sprint"]
    if dimension == "approval":
        return [{
            "pending": "Aguardando",
            "approved": "Aprovado",
            "rejected": "Rejeitado",
            "resubmitted": "Reapresentado",
        }.get(task.approval, task.approval)]
    if dimension == "work_type":
        return [WORK_TYPE_LABELS.get(task.work_type, task.work_type)]
    if dimension == "assignee":
        assignee = db.get(User, task.assignee_user_id) if task.assignee_user_id else None
        return [assignee.username if assignee else "Não atribuído"]
    if dimension == "release":
        labels = list(
            db.scalars(
                select(Release.name)
                .join(TaskRelease, TaskRelease.release_id == Release.id)
                .where(TaskRelease.task_id == task.id, Release.archived.is_(False))
                .order_by(Release.name, Release.id)
            )
        )
        return labels or ["Sem release"]
    if dimension == "component":
        labels = list(
            db.scalars(
                select(Component.name)
                .join(TaskComponent, TaskComponent.component_id == Component.id)
                .where(TaskComponent.task_id == task.id, Component.active.is_(True))
                .order_by(Component.name, Component.id)
            )
        )
        return labels or ["Sem componente"]
    if dimension == "parent":
        parent = db.get(Task, task.parent_id) if task.parent_id else None
        if not parent:
            return ["Sem card pai"]
        if not show_parent_details:
            return ["Card pai vinculado"]
        return [f"OS-{parent.id} · {parent.title}"]
    if dimension == "due_month":
        if not task.due:
            return ["Sem prazo"]
        try:
            due = date.fromisoformat(task.due)
        except ValueError:
            return ["Prazo inválido"]
        return [due.strftime("%m/%Y")]
    if dimension == "created_month":
        try:
            created = datetime.fromisoformat(task.created_at.replace("Z", "+00:00"))
        except (AttributeError, ValueError):
            return ["Data de criação inválida"]
        return [created.strftime("%m/%Y")]
    if dimension == "resolved_month":
        if task.status != "done" or not resolved_at:
            return ["Sem resolução registrada"]
        try:
            resolved = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
        except (AttributeError, ValueError):
            return ["Data de resolução inválida"]
        return [resolved.strftime("%m/%Y")]
    if dimension == "overdue":
        current_day = today or datetime.now(timezone.utc).date()
        overdue = bool(task.due and task.due < current_day.isoformat() and task.status != "done")
        return ["Atrasados" if overdue else "No prazo / sem prazo"]
    raise ValueError("Dimensão de widget desconhecida.")


def widget_group_sort_key(item, dimension):
    """Keep month-based dashboard groups in calendar order."""
    name = item[0]
    if dimension in {"created_month", "due_month", "resolved_month"}:
        try:
            month, year = name.split("/")
            return (0, int(year), int(month))
        except (ValueError, AttributeError):
            return (1, 0, name.casefold())
    return (0, name.casefold())


def widget_measure_value(task, measure, today=None, resolved_at=None):
    if measure == "count":
        return 1
    if measure == "estimated_minutes":
        return task.estimated_minutes
    if measure == "used_minutes":
        return task.used_minutes
    if measure == "remaining_minutes":
        return max(0, task.estimated_minutes - task.used_minutes)
    if measure == "avg_open_age_days":
        if task.status == "done":
            return None
        try:
            created = datetime.fromisoformat(task.created_at.replace("Z", "+00:00"))
        except (AttributeError, ValueError):
            return None
        current_day = today or datetime.now(timezone.utc).date()
        return max(0, (current_day - created.date()).days)
    if measure == "avg_resolution_days":
        if task.status != "done" or not resolved_at:
            return None
        try:
            created = datetime.fromisoformat(task.created_at.replace("Z", "+00:00"))
            resolved = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
        except (AttributeError, ValueError):
            return None
        return max(0, (resolved.date() - created.date()).days)
    raise ValueError("Medida de widget desconhecida.")


def current_status_entry_times(db, tasks):
    """Resolve current-status entry times from the latest matching audit event."""
    if not tasks:
        return {}
    status_by_task = {task.id: task.status for task in tasks}
    entries, latest_seen = {}, set()
    events = db.scalars(
        select(Audit)
        .where(
            Audit.entity == "task",
            Audit.entity_id.in_(status_by_task),
            Audit.action == "status_changed",
        )
        .order_by(Audit.created_at.desc(), Audit.id.desc())
    )
    for event in events:
        if event.entity_id in latest_seen:
            continue
        latest_seen.add(event.entity_id)
        if (event.details or {}).get("destination") == status_by_task[event.entity_id]:
            entries[event.entity_id] = event.created_at
    for task in tasks:
        entries.setdefault(task.id, task.created_at)
    return entries


def current_status_age_days(entered_at, now=None):
    if not entered_at:
        return None
    try:
        entered = datetime.fromisoformat(entered_at.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    if entered.tzinfo is None:
        entered = entered.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return round(max(0, (current - entered).total_seconds() / 86400), 1)


def created_resolved_series(tasks, resolved_at_by_task):
    """Return a gap-filled UTC monthly series for matching cards and resolutions."""
    created = {}
    resolved = {}

    def month_number(value):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.year * 12 + parsed.month - 1

    def label(month):
        year, zero_month = divmod(month, 12)
        return f"{zero_month + 1:02d}/{year}"

    for task in tasks:
        try:
            month = month_number(task.created_at)
        except (AttributeError, TypeError, ValueError):
            continue
        created[month] = created.get(month, 0) + 1
        completed_at = resolved_at_by_task.get(task.id)
        if task.status == "done" and completed_at:
            try:
                month = month_number(completed_at)
            except (TypeError, ValueError):
                continue
            resolved[month] = resolved.get(month, 0) + 1

    months = sorted(created.keys() | resolved.keys())
    if not months:
        return []
    return [
        {
            "name": label(month),
            "created": created.get(month, 0),
            "resolved": resolved.get(month, 0),
        }
        for month in range(months[0], months[-1] + 1)
    ]
