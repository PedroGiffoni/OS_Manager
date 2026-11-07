"""Persist deduplicated SCM events and run their trusted automation rules."""

from sqlalchemy.exc import IntegrityError

from .automation import run_automations
from .models import DevelopmentEvent


def record_development_event(
    db,
    *,
    provider,
    delivery_id,
    task,
    event_type,
    summary,
    url="",
    actor_name="",
    occurred_at=None,
    metadata=None,
):
    """Store one provider delivery for one card; duplicates have no side effects."""
    if not task or task.archived:
        return False
    event_metadata = metadata if isinstance(metadata, dict) else {}
    event = DevelopmentEvent(
        provider=provider,
        delivery_id=delivery_id,
        task_id=task.id,
        event_type=event_type[:60],
        summary=summary[:500],
        url=url[:1000],
        actor=actor_name[:160],
        occurred_at=occurred_at[:80] if occurred_at else None,
        details=event_metadata,
    )
    try:
        with db.begin_nested():
            db.add(event)
            db.flush()
    except IntegrityError:
        return False

    context = {
        "provider": provider,
        "event_type": event_type[:60],
        **event_metadata,
    }
    run_automations(db, None, task, "development_event", event_context=context)
    return True
