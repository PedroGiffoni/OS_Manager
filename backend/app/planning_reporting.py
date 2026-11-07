"""Progress reports for an epic or planned release/version."""

from collections import Counter

from sqlalchemy import select

from .models import Component, Release, Task, TaskComponent, TaskRelease
from .services import fail


def epic_descendant_ids(db, epic_id):
    """Walk a task tree in portable batches; visited IDs also break legacy cycles."""
    seen = {epic_id}
    descendants = set()
    frontier = {epic_id}
    while frontier:
        following = set()
        identities = sorted(frontier)
        for offset in range(0, len(identities), 500):
            batch = identities[offset : offset + 500]
            children = db.scalars(select(Task).where(Task.parent_id.in_(batch)))
            for child in children:
                if child.parent_id not in batch or child.id in seen:
                    continue
                seen.add(child.id)
                following.add(child.id)
                if not child.archived:
                    descendants.add(child.id)
        frontier = following
    return descendants


def planning_report(
    db,
    kind,
    identity,
    jql="",
    *,
    allow_configuration_history=True,
    actor_user_id=None,
    actor_role=None,
):
    descendant_ids = None
    if kind == "release":
        container = db.get(Release, identity)
        if not container or container.archived:
            fail("Release não encontrada.", 404)
        query = (
            select(Task)
            .join(TaskRelease, TaskRelease.task_id == Task.id)
            .where(TaskRelease.release_id == identity, Task.archived.is_(False))
        )
        heading = {
            "kind": "release",
            "id": container.id,
            "name": container.name,
            "starts": container.starts,
            "due": container.due,
            "released_at": container.released_at,
        }
    elif kind == "epic":
        container = db.get(Task, identity)
        if not container or container.archived or container.work_type != "epic":
            fail("Épico não encontrado.", 404)
        descendant_ids = epic_descendant_ids(db, identity)
        query = select(Task).where(
            Task.id.in_(descendant_ids), Task.archived.is_(False)
        )
        heading = {"kind": "epic", "id": container.id, "name": container.title}
    else:
        fail("Tipo de relatório inválido.")

    if jql.strip():
        from .query_language import apply_query

        query = apply_query(
            query,
            jql,
            allow_configuration_history=allow_configuration_history,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
        )
    rows = list(db.scalars(query.order_by(Task.priority, Task.id)))
    if descendant_ids is not None:
        rows = [row for row in rows if row.id in descendant_ids and not row.archived]

    counts = Counter(row.status for row in rows)
    total = len(rows)
    completed = counts.get("done", 0)
    estimate_minutes = sum(row.estimated_minutes for row in rows)
    status_keys = sorted(counts)
    details = []
    for task in rows:
        components = list(
            db.scalars(
                select(Component.name)
                .join(TaskComponent, TaskComponent.component_id == Component.id)
                .where(TaskComponent.task_id == task.id)
            )
        )
        details.append(
            {
                "id": task.id,
                "title": task.title,
                "work_type": task.work_type,
                "parent_id": task.parent_id,
                "status": task.status,
                "priority": task.priority,
                "due": task.due,
                "estimated_minutes": task.estimated_minutes,
                "components": components,
            }
        )
    return {
        "container": heading,
        "summary": {
            "cards": total,
            "completed": completed,
            "completion_percent": round(completed * 100 / total, 1) if total else 0,
            "estimated_hours": round(estimate_minutes / 60, 2),
        },
        "by_status": [{"status": status, "cards": counts[status]} for status in status_keys],
        "tasks": details,
        "definition": "Conclusão considera cards atualmente em Concluído. Horas são estimativas de planejamento; não representam custo nem horas aprovadas.",
    }
