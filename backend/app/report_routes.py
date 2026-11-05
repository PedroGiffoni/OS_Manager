from datetime import date
from fastapi import APIRouter, Depends, Query
from .db import get_db
from .security import current_user
from .services import fail
from .reporting import records
from .report_filters import catalogue, filter_context, filter_summary


def internal_reports(user=Depends(current_user)):
    if user.role == "supplier":
        fail("Relatórios disponíveis apenas para usuários internos.", 403)


router = APIRouter(
    prefix="/api/v1/reports", tags=["Relatórios"], dependencies=[Depends(internal_reports)]
)


@router.get("/fields")
def report_fields(sprint_id: int | None = None, user=Depends(current_user), db=Depends(get_db)):
    return catalogue(db, user, records(db, user, sprint_id=sprint_id))


@router.get("/preview")
def preview(
    field_filters: str = Query(default="[]", max_length=12000),
    status: str | None = None,
    sprint_id: int | None = None,
    supplier_id: int | None = None,
    starts: date | None = None,
    ends: date | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    user=Depends(current_user),
    db=Depends(get_db),
):
    context = filter_context(db, user, field_filters, sprint_id)
    rows = records(db, user, status, sprint_id, supplier_id, starts, ends, context)
    keys = [
        "id",
        "title",
        "status",
        "due",
        "estimated_minutes",
        "used_minutes",
        "approval",
        "cost_cents",
    ]
    return {
        "total": len(rows),
        "offset": offset,
        "limit": limit,
        "filters": filter_summary(*context),
        "items": [
            {key: row[key] for key in keys if key in row} for row in rows[offset : offset + limit]
        ],
    }


@router.get("/analysis")
def analysis(
    field_filters: str = Query(default="[]", max_length=12000),
    status: str | None = None,
    sprint_id: int | None = None,
    supplier_id: int | None = None,
    starts: date | None = None,
    ends: date | None = None,
    idle_days: int = Query(default=7, ge=1, le=3650),
    min_phase_hours: str | None = Query(default=None, max_length=30),
    overdue_only: bool = False,
    only_reopened: bool = False,
    approval_state: str | None = Query(
        default=None, pattern="^(pending|approved|rejected|resubmitted)$"
    ),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    user=Depends(current_user),
    db=Depends(get_db),
):
    from .analytics import report

    result = report(
        db,
        user,
        {
            "field_filters": field_filters,
            "status": status,
            "sprint_id": sprint_id,
            "supplier_id": supplier_id,
            "starts": starts,
            "ends": ends,
            "min_phase_hours": min_phase_hours,
            "overdue_only": overdue_only,
            "only_reopened": only_reopened,
            "approval_state": approval_state,
        },
        idle_days=idle_days,
    )
    result["items"] = result["items"][offset : offset + limit]
    result.update(offset=offset, limit=limit)
    return result


@router.get("/cards/{identity}")
def card_analysis(
    identity: int, sprint_id: int | None = None, user=Depends(current_user), db=Depends(get_db)
):
    from .analytics import card_detail

    return card_detail(db, user, identity, sprint_id)
