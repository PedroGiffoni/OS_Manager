from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select
from .models import Sprint, SprintTask, Audit
from .repositories import filtered_tasks
from .security import allowed
from .services import task_payload, cost_cents
from .settings import local_today, timestamp_date


def records(db, user, status=None, sprint_id=None, supplier_id=None, starts=None, ends=None):
    rows = list(
        db.scalars(
            filtered_tasks(
                db,
                user,
                status=None,
                sprint_id=sprint_id,
                supplier_id=None if sprint_id else supplier_id,
                starts=starts,
                ends=ends,
            )
        )
    )
    sprint = db.get(Sprint, sprint_id) if sprint_id else None
    links = (
        {
            link.task_id: link
            for link in db.scalars(select(SprintTask).where(SprintTask.sprint_id == sprint_id))
        }
        if sprint
        else {}
    )
    result = []
    financial = user.role in {"admin", "manager"} and allowed(user, "view_financial")
    for task in rows:
        payload = task_payload(db, user, task)
        if sprint_id is not None and financial:
            payload["cost_cents"] = cost_cents(db, task, sprint_id)
        if sprint and sprint.state == "closed" and links[task.id].snapshot:
            snapshot = links[task.id].snapshot
            for key in [
                "status",
                "estimated_minutes",
                "used_minutes",
                "approval",
                "hours_version",
                "supplier_id",
                "title",
                "description",
                "due",
                "completed_at",
            ]:
                if key in snapshot:
                    payload[key] = snapshot[key]
            if financial:
                payload["cost_cents"] = snapshot["cost_cents"]
            payload["read_only"] = True
        if supplier_id is not None and payload["supplier_id"] != supplier_id:
            continue
        if not status or payload["status"] == status:
            result.append(payload)
    return result


def indicators(db, rows):
    done = sum(row["status"] == "done" for row in rows)
    with_due = [row for row in rows if row["status"] == "done" and row["due"]]
    on_time = 0
    for row in with_due:
        completed = db.scalar(
            select(Audit)
            .where(
                Audit.entity == "task",
                Audit.entity_id == row["id"],
                Audit.action == "status_changed",
            )
            .order_by(Audit.id.desc())
        )
        if (
            completed
            and completed.details.get("destination") == "done"
            and timestamp_date(row.get("completed_at") or completed.created_at) <= row["due"]
        ):
            on_time += 1
    percent = lambda numerator, denominator: (
        str(
            (Decimal(numerator) * 100 / Decimal(denominator)).quantize(
                Decimal(".01"), rounding=ROUND_HALF_UP
            )
        )
        if denominator
        else "0"
    )
    result = {
        "planned": len(rows),
        "done": done,
        "pending": len(rows) - done,
        "overdue": sum(
            bool(row["due"] and row["due"] < local_today().isoformat() and row["status"] != "done")
            for row in rows
        ),
        "estimated_minutes": sum(row["estimated_minutes"] for row in rows),
        "used_minutes": sum(row["used_minutes"] for row in rows),
        "completion_percent": percent(done, len(rows)),
        "on_time_percent": percent(on_time, len(with_due)),
        "completed_with_due": len(with_due),
        "by_status": [
            {"status": status, "count": sum(row["status"] == status for row in rows)}
            for status in ["backlog", "todo", "production", "review", "done"]
        ],
    }
    result["deviation_minutes"] = result["used_minutes"] - result["estimated_minutes"]
    return result
