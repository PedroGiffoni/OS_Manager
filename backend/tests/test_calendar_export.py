import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db import Base
from app.main import app, calendar_feed_status, calendar_subscription_feed, create_calendar_feed, export_calendar, revoke_calendar_feed
from app.models import CalendarFeedToken, Role, Supplier, Task, User
from app.schemas import CalendarExportInput


def test_calendar_export_respects_supplier_scope_and_escapes_ical_text():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Role(id="internal"), Role(id="supplier")])
        db.flush()
        supplier_user = User(
            id=1,
            username="supplier-calendar",
            role="supplier",
            password_hash="unused-test-hash",
            grants=[],
        )
        other_user = User(
            id=2,
            username="other-calendar",
            role="supplier",
            password_hash="unused-test-hash",
            grants=[],
        )
        db.add_all([supplier_user, other_user])
        db.flush()
        db.add_all(
            [
                Supplier(id=1, name="Fornecedor A", function="Dev", user_id=1),
                Supplier(id=2, name="Fornecedor B", function="QA", user_id=2),
            ]
        )
        db.flush()
        db.add_all(
            [
                Task(
                    id=1,
                    title="Card, com; separadores\nBEGIN:VEVENT",
                    creator_id=1,
                    supplier_id=1,
                    due="2026-11-10",
                ),
                Task(
                    id=2,
                    title="Card privado de outro fornecedor",
                    creator_id=2,
                    supplier_id=2,
                    due="2026-11-11",
                ),
                Task(
                    id=3,
                    title="Card sem prazo",
                    creator_id=1,
                    supplier_id=1,
                ),
            ]
        )
        db.flush()

        response = export_calendar(
            CalendarExportInput(task_ids=[1, 2, 3]), supplier_user, db
        )
        content = response.body.decode("utf-8")

    assert response.media_type.startswith("text/calendar")
    assert "filename=\"gestao-de-demandas.ics\"" in response.headers["content-disposition"]
    assert "SUMMARY:OS-1 · Card\\, com\\; separadores\\nBEGIN:VEVENT" in content
    assert "DTSTART;VALUE=DATE:20261110" in content
    assert "DTEND;VALUE=DATE:20261111" in content
    assert "Card privado de outro fornecedor" not in content
    assert "Card sem prazo" not in content
    assert content.count("\r\nBEGIN:VEVENT\r\n") == 1
    engine.dispose()


def test_calendar_export_input_rejects_duplicates_and_oversized_lists():
    with pytest.raises(ValidationError):
        CalendarExportInput(task_ids=[1, 1])
    with pytest.raises(ValidationError):
        CalendarExportInput(task_ids=list(range(1, 5002)))


def test_calendar_subscription_uses_documented_http_basic_authentication():
    operation = app.openapi()["paths"]["/api/v1/calendar/feed.ics"]["get"]
    assert operation["security"] == [{"HTTPBasic": []}]
    assert app.openapi()["components"]["securitySchemes"]["HTTPBasic"]["scheme"] == "basic"


def test_personal_calendar_feed_uses_revolving_basic_token_and_supplier_scope():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Role(id="supplier")])
        db.flush()
        account = User(
            id=1,
            username="feed-owner",
            role="supplier",
            grants=[],
            password_hash="test-hash",
        )
        other = User(
            id=2,
            username="feed-other",
            role="supplier",
            grants=[],
            password_hash="test-hash",
        )
        db.add_all([account, other])
        db.flush()
        db.add_all([
            Supplier(id=1, name="Fornecedor dono", function="Dev", user_id=1),
            Supplier(id=2, name="Fornecedor privado", function="QA", user_id=2),
        ])
        db.flush()
        db.add_all([
            Task(id=1, title="Card visível", creator_id=1, supplier_id=1, due="2026-11-10"),
            Task(id=2, title="Card de terceiros", creator_id=2, supplier_id=2, due="2026-11-11"),
        ])
        db.flush()

        first = create_calendar_feed(account, db)
        assert len(first["token"]) >= 64
        assert calendar_feed_status(account, db)["enabled"] is True
        stored = db.get(CalendarFeedToken, account.id)
        assert stored.token_hash != first["token"]

        def request_for(token):
            return HTTPBasicCredentials(username="calendar", password=token)

        with pytest.raises(HTTPException) as missing_auth:
            calendar_subscription_feed(None, db)
        assert missing_auth.value.status_code == 401
        assert missing_auth.value.headers["WWW-Authenticate"].startswith("Basic")
        with pytest.raises(HTTPException) as invalid_auth:
            calendar_subscription_feed(request_for("invalid-calendar-token"), db)
        assert invalid_auth.value.status_code == 401

        feed = calendar_subscription_feed(request_for(first["token"]), db)
        content = feed.body.decode()
        assert feed.headers["cache-control"] == "private, no-store"
        assert "UID:os-1@gestao-de-demandas.local" in content
        assert "LAST-MODIFIED:" in content
        assert "Card de terceiros" not in content
        assert "Fornecedor dono" not in content
        assert "cents" not in content

        second = create_calendar_feed(account, db)
        assert second["token"] != first["token"]
        with pytest.raises(HTTPException) as revoked:
            calendar_subscription_feed(request_for(first["token"]), db)
        assert revoked.value.status_code == 401

        revoke_calendar_feed(account, db)
        assert calendar_feed_status(account, db)["enabled"] is False
        with pytest.raises(HTTPException) as deleted:
            calendar_subscription_feed(request_for(second["token"]), db)
        assert deleted.value.status_code == 401
    engine.dispose()
