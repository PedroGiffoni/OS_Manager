from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.email_notifications import (
    deliver_due_email_notifications,
    queue_notification_emails,
    send_notification_email,
)
from app.models import (
    EmailOutbox,
    InAppNotification,
    NotificationPreference,
    Role,
    Supplier,
    Task,
    User,
)


def make_session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)


def test_opted_in_notifications_are_queued_and_delivered_without_task_details(monkeypatch):
    engine, factory = make_session_factory()
    monkeypatch.setenv("SMTP_HOST", "mail.example.test")
    monkeypatch.setenv("SMTP_FROM", "noreply@example.test")
    delivered = []
    with factory() as db:
        db.add(Role(id="admin"))
        db.flush()
        user = User(username="email-user", password_hash="hash", role="admin", grants=[])
        db.add(user)
        db.flush()
        db.add(NotificationPreference(
            user_id=user.id,
            email="person@example.test",
            email_enabled=True,
        ))
        task = Task(title="Sensitive task title", creator_id=user.id)
        db.add(task)
        db.flush()
        notice = InAppNotification(
            user_id=user.id,
            task_id=task.id,
            actor_id=None,
            action="status_changed",
        )
        db.add(notice)
        db.flush()
        assert queue_notification_emails(db, [notice]) == 1
        db.commit()

    result = deliver_due_email_notifications(
        factory,
        now_utc=datetime.now(timezone.utc) + timedelta(minutes=1),
        sender=delivered.append,
    )
    assert result == {"configured": True, "sent": 1, "skipped": 0, "failed": 0}
    assert delivered == ["person@example.test"]
    with factory() as db:
        outbox = db.scalar(select(EmailOutbox))
        assert outbox.status == "sent"
        assert outbox.attempts == 1
    engine.dispose()


def test_delivery_is_disabled_without_smtp_configuration(monkeypatch):
    engine, factory = make_session_factory()
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_FROM", raising=False)
    delivered = []
    result = deliver_due_email_notifications(factory, sender=delivered.append)
    assert result == {"configured": False, "sent": 0, "skipped": 0, "failed": 0}
    assert delivered == []
    engine.dispose()


def test_email_content_is_generic_and_does_not_include_card_details(monkeypatch):
    import app.email_notifications as email_module

    captured = []

    class SMTPStub:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("mail.example.test", 587, 15)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def send_message(self, message):
            captured.append(message)

    monkeypatch.setenv("SMTP_HOST", "mail.example.test")
    monkeypatch.setenv("SMTP_FROM", "noreply@example.test")
    monkeypatch.setenv("SMTP_STARTTLS", "false")
    monkeypatch.setattr(email_module.smtplib, "SMTP", SMTPStub)

    send_notification_email("person@example.test")

    assert len(captured) == 1
    assert captured[0]["To"] == "person@example.test"
    assert "notificação" in captured[0].get_content()
    assert "Sensitive task title" not in captured[0].get_content()
    assert "OS-" not in captured[0].get_content()


def test_supplier_email_is_skipped_when_task_is_no_longer_assigned_to_supplier(monkeypatch):
    engine, factory = make_session_factory()
    monkeypatch.setenv("SMTP_HOST", "mail.example.test")
    monkeypatch.setenv("SMTP_FROM", "noreply@example.test")
    delivered = []
    with factory() as db:
        db.add_all([Role(id="admin"), Role(id="supplier")])
        db.flush()
        admin = User(username="mail-admin", password_hash="hash", role="admin", grants=[])
        supplier_user = User(username="mail-supplier", password_hash="hash", role="supplier", grants=[])
        db.add_all([admin, supplier_user])
        db.flush()
        supplier = Supplier(name="Fornecedor", function="Teste", user_id=supplier_user.id)
        db.add(supplier)
        db.flush()
        db.add(NotificationPreference(
            user_id=supplier_user.id,
            email="supplier@example.test",
            email_enabled=True,
        ))
        task = Task(title="Card fora do escopo", creator_id=admin.id, supplier_id=None)
        db.add(task)
        db.flush()
        notice = InAppNotification(
            user_id=supplier_user.id,
            task_id=task.id,
            actor_id=admin.id,
            action="status_changed",
        )
        db.add(notice)
        db.flush()
        queue_notification_emails(db, [notice])
        db.commit()

    result = deliver_due_email_notifications(
        factory,
        now_utc=datetime.now(timezone.utc) + timedelta(minutes=1),
        sender=delivered.append,
    )
    assert result["skipped"] == 1
    assert delivered == []
    with factory() as db:
        assert db.scalar(select(EmailOutbox)).status == "skipped"
    engine.dispose()
