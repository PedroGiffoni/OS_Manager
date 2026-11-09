"""Run personal saved-filter subscriptions and create scoped in-app alerts."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import delete, func, select

from .email_notifications import queue_notification_emails
from .push_notifications import queue_web_push_notifications
from .models import FilterSubscription, FilterSubscriptionMatch, InAppNotification, Task, User
from .query_language import apply_query
from .repositories import filtered_tasks

logger = logging.getLogger(__name__)
MAX_ALERTS_PER_RUN = 50


def utc_now():
    return datetime.now(timezone.utc)


def next_run(frequency, current):
    return current + (timedelta(days=7) if frequency == "weekly" else timedelta(days=1))


def matching_task_ids(db, user, query):
    statement = apply_query(
        filtered_tasks(db, user),
        query,
        allow_configuration_history=user.role == "admin",
        actor_user_id=user.id,
        actor_role=user.role,
    )
    return list(
        db.scalars(statement.order_by(None).with_only_columns(Task.id).order_by(Task.id))
    )


def initialize_matches(db, user, subscription):
    """Capture the current result set so creation/editing does not alert old matches."""
    ids = matching_task_ids(db, user, subscription.query)
    db.execute(
        delete(FilterSubscriptionMatch).where(
            FilterSubscriptionMatch.subscription_id == subscription.id
        )
    )
    db.add_all(
        FilterSubscriptionMatch(subscription_id=subscription.id, task_id=identity)
        for identity in ids
    )
    return len(ids)


def run_due_filter_subscriptions(session_factory, *, now_utc=None, limit=100):
    current = now_utc or utc_now()
    current = current.astimezone(timezone.utc)
    current_text = current.isoformat()
    with session_factory() as db:
        due_ids = list(
            db.scalars(
                select(FilterSubscription.id)
                .where(
                    FilterSubscription.active.is_(True),
                    FilterSubscription.next_run_at <= current_text,
                )
                .order_by(FilterSubscription.next_run_at, FilterSubscription.id)
                .limit(limit)
            )
        )

        processed = 0
        created_alerts = 0
        for identity in due_ids:
            subscription = db.scalar(
                select(FilterSubscription)
                .where(FilterSubscription.id == identity)
                .with_for_update()
            )
            if not subscription or not subscription.active or subscription.next_run_at > current_text:
                continue
            # A scheduler session has no request context; establish the subscription's
            # board before reading cards or writing notifications/audit data.
            db.info["board_id"] = subscription.board_id
            user = db.get(User, subscription.user_id)
            if not user or not user.active:
                subscription.active = False
                subscription.last_error = "A conta vinculada foi desativada."
                subscription.last_run_at = current_text
                db.commit()
                continue

            try:
                current_ids = set(matching_task_ids(db, user, subscription.query))
                existing_rows = list(
                    db.scalars(
                        select(FilterSubscriptionMatch).where(
                            FilterSubscriptionMatch.subscription_id == subscription.id
                        )
                    )
                )
                existing_ids = {row.task_id for row in existing_rows}
                for row in existing_rows:
                    if row.task_id not in current_ids:
                        db.delete(row)

                newly_matching = sorted(current_ids - existing_ids)
                alerts = newly_matching[:MAX_ALERTS_PER_RUN]
                db.add_all(
                    FilterSubscriptionMatch(
                        subscription_id=subscription.id, task_id=task_id
                    )
                    for task_id in alerts
                )
                notification_rows = [
                    InAppNotification(
                        user_id=user.id,
                        task_id=task_id,
                        actor_id=None,
                        action="filter_match",
                        source_label=subscription.name,
                    )
                    for task_id in alerts
                ]
                db.add_all(notification_rows)
                queue_notification_emails(db, notification_rows)
                queue_web_push_notifications(db, notification_rows)
                subscription.last_run_at = current_text
                subscription.last_error = ""
                if len(newly_matching) > len(alerts):
                    # Drain large result changes in small, idempotent batches.
                    subscription.next_run_at = (current + timedelta(minutes=1)).isoformat()
                else:
                    subscription.next_run_at = next_run(
                        subscription.frequency, current
                    ).isoformat()
                db.commit()
                processed += 1
                created_alerts += len(alerts)
            except HTTPException:
                db.rollback()
                failed = db.get(FilterSubscription, identity)
                if failed:
                    failed.active = False
                    failed.last_run_at = current_text
                    failed.last_error = (
                        "A consulta deixou de ser válida ou autorizada. Revise a assinatura."
                    )
                    db.commit()
            except Exception:
                db.rollback()
                logger.exception("Falha ao executar assinatura de filtro %s.", identity)

        return {"processed": processed, "notifications": created_alerts}


def subscription_payload(db, subscription):
    return {
        "id": subscription.id,
        "name": subscription.name,
        "query": subscription.query,
        "frequency": subscription.frequency,
        "active": subscription.active,
        "match_count": db.scalar(
            select(func.count())
            .select_from(FilterSubscriptionMatch)
            .where(FilterSubscriptionMatch.subscription_id == subscription.id)
        )
        or 0,
        "next_run_at": subscription.next_run_at,
        "last_run_at": subscription.last_run_at,
        "last_error": subscription.last_error,
        "created_at": subscription.created_at,
    }
