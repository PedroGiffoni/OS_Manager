import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from py_vapid import Vapid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import InAppNotification, Role, Task, TaskWatcher, User
from app.push_notifications import endpoint_hash
from app.services import audit


def test_task_audit_notifies_watchers_but_not_actor():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Role(id="admin"), Role(id="internal")])
        db.flush()
        actor = User(username="actor", password_hash="hash", role="admin", grants=[])
        watcher = User(username="watcher", password_hash="hash", role="internal", grants=[])
        db.add_all([actor, watcher])
        db.flush()
        task = Task(title="Atividade de teste", creator_id=actor.id)
        db.add(task)
        db.flush()
        db.add(TaskWatcher(task_id=task.id, user_id=watcher.id))
        db.flush()

        audit(db, actor, "task", task.id, "status_changed", destination="production")
        db.flush()

        rows = list(db.scalars(select(InAppNotification)))
        assert len(rows) == 1
        assert rows[0].user_id == watcher.id
        assert rows[0].actor_id == actor.id
        assert rows[0].action == "status_changed"
        assert rows[0].task_id == task.id
    engine.dispose()


def test_notification_preferences_are_private_and_smtp_is_optional(clients, monkeypatch):
    admin = clients["admin"]
    manager = clients["manager"]
    monkeypatch.setenv("SMTP_HOST", "mail.example.test")
    monkeypatch.setenv("SMTP_FROM", "noreply@example.test")

    saved = admin.put(
        "/api/v1/me/notification-preferences",
        json={"email": "admin@example.test", "email_enabled": True},
    )
    assert saved.status_code == 200
    assert saved.json()["email"] == "admin@example.test"
    assert saved.json()["email_enabled"] is True
    assert "SMTP_PASSWORD" not in saved.text

    manager_preferences = manager.get("/api/v1/me/notification-preferences")
    assert manager_preferences.status_code == 200
    assert manager_preferences.json()["email"] == ""
    assert manager_preferences.json()["email_enabled"] is False

    monkeypatch.delenv("SMTP_HOST")
    unavailable = manager.put(
        "/api/v1/me/notification-preferences",
        json={"email": "manager@example.test", "email_enabled": True},
    )
    assert unavailable.status_code == 503

    invalid = manager.put(
        "/api/v1/me/notification-preferences",
        json={"email": "not-an-email", "email_enabled": False},
    )
    assert invalid.status_code == 422


def test_push_subscription_api_is_per_user_encrypted_and_removable(clients, monkeypatch):
    vapid = Vapid()
    vapid.generate_keys()
    public = vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    private = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
    def encode(value):
        return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
    monkeypatch.setenv("PUSH_VAPID_PUBLIC_KEY", encode(public))
    monkeypatch.setenv("PUSH_VAPID_PRIVATE_KEY", encode(private))
    monkeypatch.setenv("PUSH_VAPID_SUBJECT", "mailto:push@example.test")
    monkeypatch.setenv("PUSH_SUBSCRIPTION_FERNET_KEY", Fernet.generate_key().decode("ascii"))
    payload = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test-device-token",
        "keys": {"p256dh": encode(b"\x04" + b"p" * 64), "auth": encode(b"a" * 16)},
    }
    digest = endpoint_hash(payload["endpoint"])

    config = clients["admin"].get(f"/api/v1/me/push-configuration?endpoint_identity={digest}")
    assert config.status_code == 200 and config.json()["available"] is True
    assert config.json()["active_on_this_browser"] is False
    assert "PUSH_VAPID_PRIVATE_KEY" not in config.text

    created = clients["admin"].post("/api/v1/me/push-subscriptions", json=payload)
    assert created.status_code == 201 and created.json()["device_count"] == 1
    assert payload["endpoint"] not in created.text

    active = clients["admin"].get(f"/api/v1/me/push-configuration?endpoint_identity={digest}")
    assert active.json()["active_on_this_browser"] is True
    other_user = clients["manager"].get(f"/api/v1/me/push-configuration?endpoint_identity={digest}")
    assert other_user.json()["active_on_this_browser"] is False
    assert other_user.json()["device_count"] == 0

    denied = clients["manager"].delete(f"/api/v1/me/push-subscriptions/{digest}")
    assert denied.status_code == 404
    removed = clients["admin"].delete(f"/api/v1/me/push-subscriptions/{digest}")
    assert removed.status_code == 200 and removed.json()["device_count"] == 0


def test_push_subscription_requires_optional_vapid_configuration(clients, monkeypatch):
    for name in (
        "PUSH_VAPID_PUBLIC_KEY",
        "PUSH_VAPID_PRIVATE_KEY",
        "PUSH_VAPID_SUBJECT",
        "PUSH_SUBSCRIPTION_FERNET_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    response = clients["admin"].get("/api/v1/me/push-configuration")
    assert response.status_code == 200 and response.json()["available"] is False
    unavailable = clients["admin"].post(
        "/api/v1/me/push-subscriptions",
        json={
            "endpoint": "https://fcm.googleapis.com/fcm/send/x",
            "keys": {
                "p256dh": base64.urlsafe_b64encode(b"\x04" + b"p" * 64).decode().rstrip("="),
                "auth": base64.urlsafe_b64encode(b"a" * 16).decode().rstrip("="),
            },
        },
    )
    assert unavailable.status_code == 503
