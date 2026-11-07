from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from pydantic import ValidationError
from fastapi import HTTPException

from app.db import Base
from app.filter_subscriptions import initialize_matches, run_due_filter_subscriptions
from app.main import (
    create_filter_subscription,
    delete_filter_subscription,
    list_filter_subscriptions,
    update_filter_subscription,
)
from app.models import (
    FilterSubscription,
    FilterSubscriptionMatch,
    InAppNotification,
    Role,
    Supplier,
    Task,
    User,
)
from app.schemas import FilterSubscriptionInput


def create_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)


def test_scheduled_subscription_alerts_only_on_new_matches_and_allows_reentry():
    engine, factory = create_factory()
    current = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)
    with factory.begin() as db:
        db.add(Role(id="internal"))
        db.flush()
        user = User(username="equipe", password_hash="hash", role="internal", grants=[])
        db.add(user)
        db.flush()
        existing_task = Task(title="Já estava em revisão", creator_id=user.id, status="review")
        db.add(existing_task)
        db.flush()
        subscription = FilterSubscription(
            user_id=user.id,
            name="Aguardando revisão",
            query='status = "review"',
            frequency="daily",
            active=True,
            next_run_at=current.isoformat(),
        )
        db.add(subscription)
        db.flush()
        assert initialize_matches(db, user, subscription) == 1

    with factory.begin() as db:
        user = db.scalar(select(User).where(User.username == "equipe"))
        new_task = Task(title="Nova em revisão", creator_id=user.id, status="review")
        db.add(new_task)
        db.flush()
        new_task_id = new_task.id

    result = run_due_filter_subscriptions(factory, now_utc=current)
    assert result == {"processed": 1, "notifications": 1}
    with factory() as db:
        notice = db.scalar(select(InAppNotification))
        assert notice.task_id == new_task_id
        assert notice.action == "filter_match"
        assert notice.source_label == "Aguardando revisão"
        assert db.scalar(select(FilterSubscriptionMatch).where(
            FilterSubscriptionMatch.task_id == new_task_id
        )) is not None

        subscription = db.scalar(select(FilterSubscription))
        subscription.next_run_at = current.isoformat()
        db.commit()
    assert run_due_filter_subscriptions(factory, now_utc=current)["notifications"] == 0

    with factory.begin() as db:
        task = db.get(Task, new_task_id)
        task.status = "todo"
        subscription = db.scalar(select(FilterSubscription))
        subscription.next_run_at = current.isoformat()
    run_due_filter_subscriptions(factory, now_utc=current)
    with factory.begin() as db:
        task = db.get(Task, new_task_id)
        task.status = "review"
        subscription = db.scalar(select(FilterSubscription))
        subscription.next_run_at = current.isoformat()
    run_due_filter_subscriptions(factory, now_utc=current)
    with factory() as db:
        assert len(list(db.scalars(select(InAppNotification)))) == 2
    engine.dispose()


def test_supplier_subscription_is_scoped_to_assigned_tasks():
    engine, factory = create_factory()
    current = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)
    with factory.begin() as db:
        db.add(Role(id="supplier"))
        db.flush()
        user = User(username="fornecedor", password_hash="hash", role="supplier", grants=[])
        other_user = User(username="outro", password_hash="hash", role="supplier", grants=[])
        db.add_all([user, other_user])
        db.flush()
        supplier = Supplier(name="Fornecedor A", function="Design", user_id=user.id)
        other_supplier = Supplier(name="Fornecedor B", function="Dev", user_id=other_user.id)
        db.add_all([supplier, other_supplier])
        db.flush()
        assigned = Task(
            title="Minha atividade",
            creator_id=user.id,
            supplier_id=supplier.id,
            status="review",
        )
        unrelated = Task(
            title="Atividade de outra pessoa",
            creator_id=other_user.id,
            supplier_id=other_supplier.id,
            status="review",
        )
        db.add_all([assigned, unrelated])
        db.flush()
        subscription = FilterSubscription(
            user_id=user.id,
            name="Em revisão",
            query='status = "review"',
            frequency="daily",
            active=True,
            next_run_at=current.isoformat(),
        )
        db.add(subscription)
        db.flush()
        assert initialize_matches(db, user, subscription) == 1

    with factory.begin() as db:
        other_user = db.scalar(select(User).where(User.username == "outro"))
        other_supplier = db.scalar(select(Supplier).where(Supplier.user_id == other_user.id))
        db.add(
            Task(
                title="Nova atividade alheia",
                creator_id=other_user.id,
                supplier_id=other_supplier.id,
                status="review",
            )
        )
        subscription = db.scalar(select(FilterSubscription))
        subscription.next_run_at = current.isoformat()

    assert run_due_filter_subscriptions(factory, now_utc=current)["notifications"] == 0
    with factory() as db:
        assert list(db.scalars(select(InAppNotification))) == []
    engine.dispose()


def test_filter_subscription_schema_restricts_schedule_and_blank_queries():
    assert FilterSubscriptionInput(name="Aguardando", query='status = "review"').frequency == "daily"
    for payload in (
        {"name": "Sem consulta", "query": "   "},
        {"name": "Frequência inválida", "query": "status = todo", "frequency": "hourly"},
    ):
        try:
            FilterSubscriptionInput(**payload)
        except ValidationError:
            continue
        raise AssertionError("Schema deveria rejeitar assinatura inválida.")


def test_filter_subscriptions_are_private_and_admin_history_query_is_restricted():
    engine, factory = create_factory()
    with factory() as db:
        db.add_all([Role(id="admin"), Role(id="manager")])
        db.flush()
        admin = User(username="admin", password_hash="hash", role="admin", grants=[])
        manager = User(username="manager", password_hash="hash", role="manager", grants=[])
        db.add_all([admin, manager])
        db.flush()
        created = create_filter_subscription(
            FilterSubscriptionInput(name="Privado", query='status = "review"'),
            user=admin,
            db=db,
        )
        assert list_filter_subscriptions(user=manager, db=db) == []
        with pytest.raises(HTTPException) as update_error:
            update_filter_subscription(
                created["id"],
                FilterSubscriptionInput(name="Invasão", query='status = "review"'),
                user=manager,
                db=db,
            )
        assert update_error.value.status_code == 404
        with pytest.raises(HTTPException) as delete_error:
            delete_filter_subscription(created["id"], user=manager, db=db)
        assert delete_error.value.status_code == 404
        with pytest.raises(HTTPException) as restricted:
            create_filter_subscription(
                FilterSubscriptionInput(
                    name="Configuração interna",
                    query='field_config_demo_label CHANGED FROM "Rótulo" TO "Novo"',
                ),
                user=manager,
                db=db,
            )
        assert restricted.value.status_code == 403
    engine.dispose()
