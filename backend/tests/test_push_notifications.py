import base64
import json
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from py_vapid import Vapid
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import (
    InAppNotification,
    PushOutbox,
    PushSubscription,
    Role,
    Supplier,
    Task,
    User,
)
from app.push_notifications import (
    decrypt_subscription,
    deliver_due_push_notifications,
    encrypt_subscription,
    endpoint_hash,
    push_settings,
    queue_web_push_notifications,
    send_push,
    validate_push_endpoint,
    validate_subscription_payload,
)


def keyset(monkeypatch):
    vapid = Vapid()
    vapid.generate_keys()
    public = vapid.public_key.public_bytes(
        encoding=Encoding.X962,
        format=PublicFormat.UncompressedPoint,
    )
    private = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")

    def b64(value):
        return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")

    monkeypatch.setenv("PUSH_VAPID_PUBLIC_KEY", b64(public))
    monkeypatch.setenv("PUSH_VAPID_PRIVATE_KEY", b64(private))
    monkeypatch.setenv("PUSH_VAPID_SUBJECT", "mailto:push@example.test")
    monkeypatch.setenv("PUSH_SUBSCRIPTION_FERNET_KEY", Fernet.generate_key().decode("ascii"))
    return push_settings()


def make_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)


def sample_subscription(endpoint="https://updates.push.services.mozilla.com/push/v1/device-token"):
    def b64(value):
        return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")

    return {
        "endpoint": endpoint,
        "keys": {"p256dh": b64(b"\x04" + b"p" * 64), "auth": b64(b"a" * 16)},
    }


def test_push_endpoint_allowlist_and_subscription_key_validation():
    assert validate_push_endpoint("https://updates.push.services.mozilla.com/push/v1/key")
    assert validate_push_endpoint("https://fcm.googleapis.com/fcm/send/token")
    assert not validate_push_endpoint("http://fcm.googleapis.com/fcm/send/token")
    assert not validate_push_endpoint("https://fcm.googleapis.com.attacker.invalid/push")
    assert not validate_push_endpoint("https://127.0.0.1/admin")
    assert validate_subscription_payload(sample_subscription())
    invalid = sample_subscription()
    invalid["endpoint"] = "https://127.0.0.1/admin"
    assert not validate_subscription_payload(invalid)


def test_encrypted_subscription_is_queued_once_and_delivered(monkeypatch):
    settings = keyset(monkeypatch)
    engine, factory = make_factory()
    received = []
    payload = sample_subscription()
    digest = endpoint_hash(payload["endpoint"])
    encrypted = encrypt_subscription(payload, settings)
    assert payload["endpoint"] not in encrypted
    assert decrypt_subscription(encrypted, settings) == payload

    with factory() as db:
        db.add(Role(id="admin"))
        db.flush()
        user = User(username="push-admin", password_hash="hash", role="admin", grants=[])
        db.add(user)
        db.flush()
        task = Task(title="Título de atividade privada", creator_id=user.id)
        db.add(task)
        db.flush()
        db.add(PushSubscription(
            endpoint_hash=digest,
            user_id=user.id,
            encrypted_payload=encrypted,
        ))
        notice = InAppNotification(
            user_id=user.id,
            task_id=task.id,
            actor_id=None,
            action="status_changed",
        )
        db.add(notice)
        db.flush()
        assert queue_web_push_notifications(db, [notice]) == 1
        assert queue_web_push_notifications(db, [notice]) == 0
        db.commit()

    result = deliver_due_push_notifications(
        factory,
        now_utc=datetime.now(timezone.utc) + timedelta(minutes=1),
        sender=lambda subscription, config: received.append((subscription, config)),
    )
    assert result == {"configured": True, "sent": 1, "skipped": 0, "failed": 0}
    assert received[0][0] == payload
    with factory() as db:
        outbox = db.scalar(select(PushOutbox))
        assert outbox.status == "sent" and outbox.attempts == 1
    engine.dispose()


def test_supplier_push_is_skipped_when_task_is_no_longer_assigned(monkeypatch):
    keyset(monkeypatch)
    engine, factory = make_factory()
    sent = []
    payload = sample_subscription()
    digest = endpoint_hash(payload["endpoint"])
    encrypted = encrypt_subscription(payload)
    with factory() as db:
        db.add_all([Role(id="admin"), Role(id="supplier")])
        db.flush()
        admin = User(username="push-owner", password_hash="hash", role="admin", grants=[])
        supplier_user = User(username="push-supplier", password_hash="hash", role="supplier", grants=[])
        db.add_all([admin, supplier_user])
        db.flush()
        supplier = Supplier(name="Fornecedor", function="Teste", user_id=supplier_user.id)
        db.add(supplier)
        db.flush()
        task = Task(title="Card removido do escopo", creator_id=admin.id)
        db.add(task)
        db.flush()
        db.add(PushSubscription(
            endpoint_hash=digest,
            user_id=supplier_user.id,
            encrypted_payload=encrypted,
        ))
        notice = InAppNotification(
            user_id=supplier_user.id,
            task_id=task.id,
            actor_id=admin.id,
            action="status_changed",
        )
        db.add(notice)
        db.flush()
        queue_web_push_notifications(db, [notice])
        db.commit()

    result = deliver_due_push_notifications(
        factory,
        now_utc=datetime.now(timezone.utc) + timedelta(minutes=1),
        sender=lambda *_args: sent.append(True),
    )
    assert result["skipped"] == 1
    assert sent == []
    engine.dispose()


def test_webpush_message_contains_no_card_identifiers_or_details(monkeypatch):
    import pywebpush

    settings = keyset(monkeypatch)
    subscription = sample_subscription()
    captured = {}
    monkeypatch.setattr(pywebpush, "webpush", lambda **kwargs: captured.update(kwargs))

    send_push(subscription, settings)

    payload = json.loads(captured["data"])
    assert payload["title"] == "Gestão de Demandas"
    assert "notificação" in payload["body"]
    assert "OS-" not in captured["data"]
    assert "Título de atividade privada" not in captured["data"]
    assert captured["ttl"] == 300 and captured["timeout"] == 15
