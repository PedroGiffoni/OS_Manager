"""Optional, privacy-preserving SMTP delivery for in-app notification events."""

from email.message import EmailMessage
import logging
import os
import smtplib
import ssl
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from .models import EmailOutbox, InAppNotification, NotificationPreference, Supplier, Task, User

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 5


def smtp_settings():
    host = os.getenv("SMTP_HOST", "").strip()
    sender = os.getenv("SMTP_FROM", "").strip()
    if not host or not sender or "\r" in sender or "\n" in sender:
        return None
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        return None
    if not 1 <= port <= 65535:
        return None
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")
    if bool(username) != bool(password):
        return None
    use_ssl = os.getenv("SMTP_SSL", "false").lower() == "true"
    starttls = os.getenv("SMTP_STARTTLS", "true").lower() == "true"
    if use_ssl and starttls:
        return None
    return {
        "host": host,
        "port": port,
        "sender": sender,
        "username": username,
        "password": password,
        "use_ssl": use_ssl,
        "starttls": starttls,
        "app_url": os.getenv("APP_PUBLIC_URL", "http://127.0.0.1:5173").rstrip("/"),
    }


def queue_notification_emails(db, notifications):
    rows = list(notifications)
    if not rows:
        return 0
    db.flush()
    user_ids = {row.user_id for row in rows}
    enabled = set(
        db.scalars(
            select(NotificationPreference.user_id).where(
                NotificationPreference.user_id.in_(user_ids),
                NotificationPreference.email_enabled.is_(True),
                NotificationPreference.email.is_not(None),
            )
        )
    )
    existing = set(
        db.scalars(
            select(EmailOutbox.notification_id).where(
                EmailOutbox.notification_id.in_([row.id for row in rows])
            )
        )
    )
    queued = [
        EmailOutbox(notification_id=row.id)
        for row in rows
        if row.user_id in enabled and row.id not in existing
    ]
    db.add_all(queued)
    return len(queued)


def send_notification_email(recipient):
    settings = smtp_settings()
    if not settings:
        raise RuntimeError("SMTP is not configured")
    message = EmailMessage()
    message["Subject"] = "Nova notificação no Gestão de Demandas"
    message["From"] = settings["sender"]
    message["To"] = recipient
    message.set_content(
        "Você tem uma nova notificação no Gestão de Demandas.\n\n"
        "Entre na aplicação para consultar as atualizações às quais sua conta tem acesso:\n"
        f"{settings['app_url']}\n\n"
        "Este e-mail não contém detalhes de atividades."
    )
    client_type = smtplib.SMTP_SSL if settings["use_ssl"] else smtplib.SMTP
    with client_type(settings["host"], settings["port"], timeout=15) as client:
        if settings["starttls"]:
            client.starttls(context=ssl.create_default_context())
        if settings["username"]:
            client.login(settings["username"], settings["password"])
        client.send_message(message)


def deliver_due_email_notifications(
    session_factory,
    *,
    now_utc=None,
    limit=50,
    sender=send_notification_email,
):
    """Claim and deliver a bounded batch; failures are retried with backoff."""
    current = now_utc or datetime.now(timezone.utc)
    current = current.astimezone(timezone.utc)
    current_text = current.isoformat()
    stale_before = (current - timedelta(minutes=10)).isoformat()
    if not smtp_settings():
        return {"configured": False, "sent": 0, "skipped": 0, "failed": 0}

    with session_factory() as db:
        candidates = list(
            db.scalars(
                select(EmailOutbox.id)
                .where(
                    EmailOutbox.attempts < MAX_ATTEMPTS,
                    EmailOutbox.next_attempt_at <= current_text,
                    (EmailOutbox.status == "pending")
                    | ((EmailOutbox.status == "sending") & (EmailOutbox.updated_at <= stale_before)),
                )
                .order_by(EmailOutbox.next_attempt_at, EmailOutbox.id)
                .limit(max(1, min(limit, 100)))
            )
        )

    result = {"configured": True, "sent": 0, "skipped": 0, "failed": 0}
    for identity in candidates:
        with session_factory() as db:
            row = db.scalar(
                select(EmailOutbox).where(EmailOutbox.id == identity).with_for_update()
            )
            if not row or row.attempts >= MAX_ATTEMPTS:
                continue
            if row.status == "sending" and row.updated_at > stale_before:
                continue
            notice = db.get(InAppNotification, row.notification_id)
            user = db.get(User, notice.user_id) if notice else None
            preference = db.get(NotificationPreference, user.id) if user else None
            task_query = select(Task).where(
                Task.id == (notice.task_id if notice else -1),
                Task.archived.is_(False),
            )
            if user and user.role == "supplier":
                supplier_id = select(Supplier.id).where(Supplier.user_id == user.id)
                task_query = task_query.where(Task.supplier_id.in_(supplier_id))
            accessible = bool(
                notice
                and user
                and user.active
                and preference
                and preference.email_enabled
                and preference.email
                and db.scalar(task_query)
            )
            if not accessible:
                row.status = "skipped"
                row.updated_at = current_text
                db.commit()
                result["skipped"] += 1
                continue
            recipient = preference.email
            row.status = "sending"
            row.attempts += 1
            row.updated_at = current_text
            db.commit()

        try:
            sender(recipient)
        except Exception:
            logger.warning("Email notification delivery failed (outbox_id=%s).", identity)
            with session_factory() as db:
                row = db.get(EmailOutbox, identity)
                if row:
                    row.status = "failed" if row.attempts >= MAX_ATTEMPTS else "pending"
                    delay = min(2 ** row.attempts, 24 * 60)
                    row.next_attempt_at = (current + timedelta(minutes=delay)).isoformat()
                    row.updated_at = current_text
                    db.commit()
            result["failed"] += 1
        else:
            with session_factory() as db:
                row = db.get(EmailOutbox, identity)
                if row:
                    row.status = "sent"
                    row.updated_at = datetime.now(timezone.utc).isoformat()
                    db.commit()
            result["sent"] += 1
    return result
