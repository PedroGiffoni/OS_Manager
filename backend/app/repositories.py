from datetime import timedelta
from sqlalchemy import select
from .models import Task, SprintTask
from .services import scoped_tasks, fail


def filtered_tasks(
    db,
    user,
    q="",
    status=None,
    sprint_id=None,
    supplier_id=None,
    starts=None,
    ends=None,
):
    if starts and ends and ends < starts:
        fail("Período de filtro inválido.")
    query = scoped_tasks(db, user)
    if q:
        query = query.where(Task.title.contains(q, autoescape=True))
    if status is not None:
        query = query.where(Task.status == status)
    if supplier_id is not None:
        query = query.where(Task.supplier_id == supplier_id)
    if sprint_id is not None:
        query = query.where(
            Task.id.in_(select(SprintTask.task_id).where(SprintTask.sprint_id == sprint_id))
        )
    if starts:
        query = query.where(Task.created_at >= starts.isoformat())
    if ends:
        query = query.where(Task.created_at < (ends + timedelta(days=1)).isoformat())
    return query
