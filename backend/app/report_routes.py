from datetime import date
from fastapi import APIRouter, Depends, Query
from .db import get_db
from .security import current_user
from .reporting import records
from .report_filters import catalogue, filter_context, filter_summary

router = APIRouter(prefix="/api/v1/reports", tags=["Relatórios"])


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
