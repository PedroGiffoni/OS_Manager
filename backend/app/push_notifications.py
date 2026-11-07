"""Optional privacy-preserving Web Push subscriptions and delivery worker."""

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import os
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from sqlalchemy import select

from .models import (
    InAppNotification,
    PushOutbox,
    PushSubscription,
    Supplier,
    Task,
    User,
)

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 5
MAX_DEVICES_PER_USER = 10
ALLOWED_PUSH_HOSTS = {
    "fcm.googleapis.com",
    "updates.push.services.mozilla.com",
    "web.push.apple.com",
}


def _decode_urlsafe(value):
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise ValueError("Invalid base64url value")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _encode_urlsafe(value):
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def push_settings():
    public = os.getenv("PUSH_VAPID_PUBLIC_KEY", "").strip()
    private = os.getenv("PUSH_VAPID_PRIVATE_KEY", "").strip()
    subject = os.getenv("PUSH_VAPID_SUBJECT", "").strip()
    encryption_key = os.getenv("PUSH_SUBSCRIPTION_FERNET_KEY", "").strip()
    if not all((public, private, subject, encryption_key)):
        return None
    if not subject.startswith(("mailto:", "https://")) or "\r" in subject or "\n" in subject:
        return None
    try:
        from py_vapid import Vapid

        public_bytes = _decode_urlsafe(public)
        if len(public_bytes) != 65:
            return None
        vapid = Vapid.from_string(private)
        derived_public = vapid.public_key.public_bytes(
            encoding=Encoding.X962,
            format=PublicFormat.UncompressedPoint,
        )
        if derived_public != public_bytes:
            return None
        Fernet(encryption_key.encode("ascii"))
    except Exception:
        return None
    return {
        "public_key": public,
        "private_key": private,
        "subject": subject,
        "fernet": Fernet(encryption_key.encode("ascii")),
    }


def endpoint_hash(endpoint):
    return hashlib.sha256(endpoint.encode("utf-8")).hexdigest()


def validate_push_endpoint(endpoint):
    if not isinstance(endpoint, str) or len(endpoint) > 2048:
        return False
    try:
        parsed = urlsplit(endpoint)
        return (
            parsed.scheme == "https"
            and parsed.hostname in ALLOWED_PUSH_HOSTS
            and parsed.username is None
            and parsed.password is None
            and parsed.port in (None, 443)
            and bool(parsed.path)
        )
    except ValueError:
        return False


def validate_subscription_payload(subscription):
    if not isinstance(subscription, dict) or not validate_push_endpoint(subscription.get("endpoint")):
        return False
    keys = subscription.get("keys")
    if not isinstance(keys, dict):
        return False
    try:
        p256dh = _decode_urlsafe(keys.get("p256dh"))
        auth = _decode_urlsafe(keys.get("auth"))
    except (ValueError, TypeError):
        return False
    return len(p256dh) == 65 and p256dh[0] == 4 and 16 <= len(auth) <= 32


def encrypt_subscription(subscription, settings=None):
    current = settings or push_settings()
    if not current:
        raise ValueError("Push is not configured")
    encoded = json.dumps(subscription, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return current["fernet"].encrypt(encoded).decode("ascii")


def decrypt_subscription(encrypted_payload, settings=None):
    current = settings or push_settings()
    if not current:
        raise ValueError("Push is not configured")
    return json.loads(current["fernet"].decrypt(encrypted_payload.encode("ascii")))


def queue_web_push_notifications(db, notifications):
    rows = list(notifications)
    if not rows:
        return 0
    db.flush()
    by_user = {}
    for row in rows:
        by_user.setdefault(row.user_id, []).append(row.id)
    subscriptions = list(
        db.scalars(
            select(PushSubscription).where(PushSubscription.user_id.in_(set(by_user)))
        )
    )
    if not subscriptions:
        return 0
    pairs = [(notice_id, subscription.endpoint_hash) for subscription in subscriptions for notice_id in by_user[subscription.user_id]]
    existing = set(
        db.execute(
            select(PushOutbox.notification_id, PushOutbox.subscription_hash).where(
                PushOutbox.notification_id.in_({notice_id for notice_id, _ in pairs}),
                PushOutbox.subscription_hash.in_({identity for _, identity in pairs}),
            )
        ).all()
    )
    pending = [
        PushOutbox(notification_id=notice_id, subscription_hash=identity)
        for notice_id, identity in pairs
        if (notice_id, identity) not in existing
    ]
    db.add_all(pending)
    return len(pending)


def send_push(subscription_info, settings=None):
    current = settings or push_settings()
    if not current:
        raise RuntimeError("Web Push is not configured")
    if not validate_push_endpoint(subscription_info.get("endpoint", "")):
        raise ValueError("Unsupported push endpoint")
    from pywebpush import webpush

    payload = {
        "title": "Gestão de Demandas",
        "body": "Você tem uma nova notificação. Entre na aplicação para consultar as atualizações.",
        "url": "/",
    }
    webpush(
        subscription_info=subscription_info,
        data=json.dumps(payload, separators=(",", ":")),
        vapid_private_key=current["private_key"],
        vapid_claims={"sub": current["subject"]},
        ttl=300,
        timeout=15,
    )


def _task_is_visible(db, user, task_id):
    query = select(Task.id).where(Task.id == task_id, Task.archived.is_(False))
    if user.role == "supplier":
        supplier_id = select(Supplier.id).where(Supplier.user_id == user.id)
        query = query.where(Task.supplier_id.in_(supplier_id))
    return db.scalar(query) is not None


def deliver_due_push_notifications(
    session_factory,
    *,
    now_utc=None,
    limit=50,
    sender=send_push,
):
    current = now_utc or datetime.now(timezone.utc)
    current = current.astimezone(timezone.utc)
    current_text = current.isoformat()
    stale_before = (current - timedelta(minutes=10)).isoformat()
    settings = push_settings()
    if not settings:
        return {"configured": False, "sent": 0, "skipped": 0, "failed": 0}

    with session_factory() as db:
        candidates = list(
            db.scalars(
                select(PushOutbox.id)
                .where(
                    PushOutbox.attempts < MAX_ATTEMPTS,
                    PushOutbox.next_attempt_at <= current_text,
                    (PushOutbox.status == "pending")
                    | ((PushOutbox.status == "sending") & (PushOutbox.updated_at <= stale_before)),
                )
                .order_by(PushOutbox.next_attempt_at, PushOutbox.id)
                .limit(max(1, min(limit, 100)))
            )
        )

    result = {"configured": True, "sent": 0, "skipped": 0, "failed": 0}
    for identity in candidates:
        with session_factory() as db:
            row = db.scalar(select(PushOutbox).where(PushOutbox.id == identity).with_for_update())
            if not row or row.attempts >= MAX_ATTEMPTS:
                continue
            if row.status == "sending" and row.updated_at > stale_before:
                continue
            notice = db.get(InAppNotification, row.notification_id)
            subscription = db.get(PushSubscription, row.subscription_hash)
            user = db.get(User, notice.user_id) if notice else None
            accessible = bool(
                notice
                and subscription
                and user
                and user.active
                and subscription.user_id == user.id
                and _task_is_visible(db, user, notice.task_id)
            )
            if not accessible:
                row.status = "skipped"
                row.updated_at = current_text
                db.commit()
                result["skipped"] += 1
                continue
            try:
                subscription_info = decrypt_subscription(subscription.encrypted_payload, settings)
            except Exception:
                row.status = "failed"
                row.attempts = MAX_ATTEMPTS
                row.updated_at = current_text
                db.commit()
                result["failed"] += 1
                continue
            row.status = "sending"
            row.attempts += 1
            row.updated_at = current_text
            db.commit()

        try:
            sender(subscription_info, settings)
        except Exception as error:
            response = getattr(error, "response", None)
            status_code = getattr(error, "status_code", None) or getattr(response, "status_code", None)
            logger.warning("Web Push delivery failed (outbox_id=%s).", identity)
            with session_factory() as db:
                row = db.get(PushOutbox, identity)
                if status_code in {404, 410}:
                    subscription = db.get(PushSubscription, row.subscription_hash) if row else None
                    if subscription:
                        db.delete(subscription)
                    db.commit()
                    result["skipped"] += 1
                    continue
                if row:
                    row.status = "failed" if row.attempts >= MAX_ATTEMPTS else "pending"
                    row.next_attempt_at = (
                        current + timedelta(minutes=min(2 ** row.attempts, 24 * 60))
                    ).isoformat()
                    row.updated_at = current_text
                    db.commit()
            result["failed"] += 1
        else:
            with session_factory() as db:
                row = db.get(PushOutbox, identity)
                if row:
                    row.status = "sent"
                    row.updated_at = datetime.now(timezone.utc).isoformat()
                    db.commit()
            result["sent"] += 1
    return result
