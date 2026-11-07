import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db import Base
from app.main import apply_capacity_leveling, capacity_group_directory, capacity_payload, create_capacity
from app.models import ResourceCapacity, Role, Supplier, Task, User, UserGroup, UserGroupMembership
from app.schemas import CapacityInput, CapacityLevelingApply
from pydantic import ValidationError


def test_capacity_forecast_counts_overlapping_task_effort_only():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Role(id="internal"), Role(id="supplier")])
        db.flush()
        owner = User(
            id=1,
            username="responsavel",
            role="internal",
            password_hash="unused-test-hash",
            grants=["manage_capacity"],
        )
        supplier_user = User(
            id=2,
            username="fornecedor",
            role="supplier",
            password_hash="unused-test-hash",
            grants=[],
        )
        db.add_all([owner, supplier_user])
        db.flush()
        supplier = Supplier(id=1, name="Fornecedor teste", function="Dev", user_id=2)
        db.add(supplier)
        db.flush()
        team = UserGroup(name="Equipe produto", description="", active=True, author_id=1)
        db.add(team)
        db.flush()
        team_membership = UserGroupMembership(group_id=team.id, user_id=1, author_id=1)
        db.add(team_membership)
        db.flush()
        assert capacity_group_directory(user=owner, db=db) == [
            {"id": team.id, "name": "Equipe produto", "member_count": 1}
        ]
        db.add_all(
            [
                Task(
                    title="Sobrepõe período",
                    creator_id=1,
                    assignee_user_id=1,
                    supplier_id=1,
                    planned_start="2026-11-05",
                    due="2026-11-12",
                    estimated_minutes=600,
                ),
                Task(
                    title="Sem datas",
                    creator_id=1,
                    assignee_user_id=1,
                    estimated_minutes=120,
                ),
                Task(
                    title="Fora do período",
                    creator_id=1,
                    assignee_user_id=1,
                    planned_start="2026-12-01",
                    due="2026-12-10",
                    estimated_minutes=900,
                ),
            ]
        )
        capacity = ResourceCapacity(
            user_id=1,
            starts="2026-11-01",
            ends="2026-11-30",
            minutes=1200,
            author_id=1,
        )
        db.add(capacity)
        created_capacity = create_capacity(
            CapacityInput(
                group_id=team.id,
                starts="2026-11-01",
                ends="2026-11-30",
                minutes=1200,
            ),
            user=owner,
            db=db,
        )
        db.flush()
        db.delete(team_membership)
        db.flush()
        team_capacity = db.get(ResourceCapacity, created_capacity["id"])

        payload = capacity_payload(db, capacity)
        team_payload = capacity_payload(db, team_capacity)

    assert payload["demand_minutes"] == 600
    assert payload["demand_tasks"] == 1
    assert payload["unplanned_tasks"] == 1
    assert payload["utilization_percent"] == 50
    assert payload["overload_minutes"] == 258
    assert sum(day["demand_minutes"] for day in payload["daily"]) == 600
    assert sum(day["capacity_minutes"] for day in payload["daily"]) == 1200
    assert next(day for day in payload["daily"] if day["date"] == "2026-11-05")["demand_minutes"] == 100
    assert all(day["date"] not in {"2026-11-07", "2026-11-08"} for day in payload["daily"])
    assert team_payload["group_name"] == "Equipe produto"
    assert team_payload["group_member_count"] == 1
    assert team_payload["demand_minutes"] == 600
    assert team_payload["demand_tasks"] == 1
    assert team_payload["unplanned_tasks"] == 1
    assert sum(day["demand_minutes"] for day in team_payload["daily"]) == 600
    engine.dispose()


def test_capacity_leveling_plan_is_versioned_and_does_not_change_task_dates():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="internal"))
        db.flush()
        owner = User(
            id=1,
            username="capacity-owner",
            role="internal",
            password_hash="test-hash",
            grants=["manage_capacity"],
        )
        db.add(owner)
        db.flush()
        tasks = [
            Task(
                title="Card flexível",
                creator_id=owner.id,
                supplier_id=1,
                planned_start="2026-11-09",
                due="2026-11-10",
                estimated_minutes=60,
            ),
            Task(
                title="Card de um dia",
                creator_id=owner.id,
                supplier_id=1,
                planned_start="2026-11-09",
                due="2026-11-09",
                estimated_minutes=60,
            ),
        ]
        db.add_all(tasks)
        capacity = ResourceCapacity(
            supplier_id=1,
            starts="2026-11-09",
            ends="2026-11-10",
            minutes=120,
            author_id=owner.id,
        )
        db.add(capacity)
        db.flush()

        payload = capacity_payload(db, capacity)
        original_dates = [(task.planned_start, task.due) for task in tasks]
        assert payload["overload_minutes"] == 30
        assert payload["levelable_minutes"] == 30
        assert payload["suggested_overload_minutes"] == 0
        assert payload["suggested_shifts"] == [
            {
                "task_id": tasks[0].id,
                "title": "Card flexível",
                "from_date": "2026-11-09",
                "to_date": "2026-11-10",
                "minutes": 30,
            }
        ]
        assert original_dates == [("2026-11-09", "2026-11-10"), ("2026-11-09", "2026-11-09")]

        applied = apply_capacity_leveling(
            capacity.id, CapacityLevelingApply(expected_plan_version=0), owner, db
        )
        assert applied["leveling_plan_version"] == 1
        assert applied["leveling_plan_active"] is True
        assert applied["leveling_plan_stale"] is False
        assert applied["overload_minutes"] == 0
        assert sum(day["demand_minutes"] for day in applied["daily"]) == 120
        assert [(task.planned_start, task.due) for task in tasks] == original_dates

        with pytest.raises(HTTPException) as duplicate:
            apply_capacity_leveling(
                capacity.id, CapacityLevelingApply(expected_plan_version=0), owner, db
            )
        assert duplicate.value.status_code == 409

        tasks[0].estimated_minutes = 90
        db.flush()
        stale = capacity_payload(db, capacity)
        assert stale["leveling_plan_active"] is False
        assert stale["leveling_plan_stale"] is True
        assert stale["leveling_plan_version"] == 1
    engine.dispose()


def test_capacity_input_requires_exactly_one_positive_resource_identity():
    valid = CapacityInput(group_id=3, starts="2026-11-01", ends="2026-11-30", minutes=2400)
    assert valid.group_id == 3
    for values in (
        {},
        {"supplier_id": 1, "group_id": 3},
        {"user_id": 0},
    ):
        with pytest.raises(ValidationError):
            CapacityInput(starts="2026-11-01", ends="2026-11-30", minutes=60, **values)
