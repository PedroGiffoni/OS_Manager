import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.automation import matches, run_automations
from app.db import Base
from app.main import validate_workflow_assignees, workflow_assignee_directory
from app.models import AutomationRule, Audit, Comment, InAppNotification, Role, Task, TaskWatcher, User
from app.schemas import AutomationRuleInput, WorkflowAction, WorkflowCondition, WorkflowTransitionInput
from app.workflows import apply_transition_actions


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def seed_users(db):
    db.add_all([Role(id="internal"), Role(id="supplier")])
    db.flush()
    actor = User(id=1, username="gestor", role="internal", password_hash="test")
    internal = User(id=2, username="analista", role="internal", password_hash="test")
    supplier = User(id=3, username="fornecedor", role="supplier", password_hash="test")
    task = Task(id=1, title="Card", creator_id=1)
    db.add_all([actor, internal, supplier, task])
    db.flush()
    return actor, internal, supplier, task


def test_assignee_action_schema_requires_positive_integer():
    assert WorkflowAction(action="assign_internal_user", config={"user_id": 1})
    with pytest.raises(ValidationError):
        WorkflowAction(action="assign_internal_user", config={"user_id": "1"})
    condition = WorkflowCondition(field="assignee", operator="eq", value=2)
    assert condition.value == 2
    with pytest.raises(ValidationError):
        WorkflowCondition(field="assignee", operator="eq", value=0)


def test_workflow_assigns_internal_user_and_rejects_supplier_before_side_effects():
    engine = make_db()
    with Session(engine) as db:
        actor, _internal, _supplier, task = seed_users(db)
        db.add(TaskWatcher(task_id=task.id, user_id=2))
        db.flush()
        apply_transition_actions(
            db, actor, task,
            [{"action": "assign_internal_user", "config": {"user_id": 2}}],
            "todo", "production",
        )
        db.flush()
        audit = db.scalar(select(Audit).where(Audit.action == "workflow_actions_applied"))
        assert task.assignee_user_id == 2
        assert audit.details["changes"][0]["field"] == "assignee_user_id"
        notice = db.scalar(select(InAppNotification).where(InAppNotification.user_id == 2))
        assert notice.action == "workflow_actions_applied"

        with pytest.raises(HTTPException) as error:
            apply_transition_actions(
                db, actor, task,
                [
                    {"action": "add_comment", "config": {"body": "Não persistir."}},
                    {"action": "assign_internal_user", "config": {"user_id": 3}},
                ],
                "todo", "production",
            )
        assert error.value.status_code == 422
        assert task.assignee_user_id == 2
        assert db.scalars(select(Comment)).all() == []
    engine.dispose()


def test_automation_assigns_active_user_and_audits_deactivated_target_skip():
    engine = make_db()
    with Session(engine) as db:
        actor, internal, _supplier, task = seed_users(db)
        db.add(AutomationRule(
            id=1,
            name="Atribuir responsável",
            trigger="card_created",
            action="assign_internal_user",
            config={"user_id": 2},
            actions=[{"action": "assign_internal_user", "config": {"user_id": 2}}],
            conditions={},
            author_id=actor.id,
        ))
        db.add(TaskWatcher(task_id=task.id, user_id=2))
        db.flush()
        run_automations(db, actor, task, "card_created")
        db.flush()
        assert task.assignee_user_id == internal.id
        audit = db.scalar(select(Audit).where(Audit.action == "automation_applied"))
        assert audit.details["changes"]["assignee_user_id"] == {"before": None, "after": 2}
        notice = db.scalar(select(InAppNotification).where(InAppNotification.user_id == 2))
        assert notice.action == "automation_applied"

        internal.active = False
        task.assignee_user_id = None
        run_automations(db, actor, task, "card_created")
        db.flush()
        audits = db.scalars(select(Audit).where(Audit.action == "automation_applied").order_by(Audit.id)).all()
        assert task.assignee_user_id is None
        assert audits[-1].details["skipped_actions"] == [
            {"action": "assign_internal_user", "reason": "assignee_unavailable"}
        ]
    engine.dispose()


def test_automation_schema_accepts_assignment_as_primary_action():
    rule = AutomationRuleInput(
        name="Atribuir", trigger="card_created",
        actions=[{"action": "assign_internal_user", "config": {"user_id": 2}}],
    )
    assert rule.action == "assign_internal_user"
    filtered = AutomationRuleInput(
        name="Por responsável", trigger="card_created", action="add_comment",
        config={"body": "Acompanhar"}, conditions={"assignee_user_ids": [2]},
    )
    assert filtered.conditions["assignee_user_ids"] == [2]
    with pytest.raises(ValidationError):
        AutomationRuleInput(
            name="ID inválido", trigger="card_created", action="add_comment",
            config={"body": "Acompanhar"}, conditions={"assignee_user_ids": ["2"]},
        )


def test_automation_can_match_cards_by_internal_assignee():
    rule = type("Rule", (), {"conditions": {"assignee_user_ids": [2]}})()
    task = type("Task", (), {"assignee_user_id": 2})()
    assert matches(rule, task)
    task.assignee_user_id = 3
    assert not matches(rule, task)


def test_assignee_directory_is_permission_scoped_and_hides_suppliers():
    engine = make_db()
    with Session(engine) as db:
        manager, _internal, _supplier, _task = seed_users(db)
        manager.grants = ["manage_workflows"]
        assert {row["id"] for row in workflow_assignee_directory(manager, db)} == {1, 2}
        supplier_actor = db.get(User, 3)
        with pytest.raises(HTTPException) as error:
            workflow_assignee_directory(supplier_actor, db)
        assert error.value.status_code == 403
    engine.dispose()


def test_workflow_configuration_rejects_supplier_as_condition_or_action_target():
    engine = make_db()
    with Session(engine) as db:
        _actor, _internal, _supplier, _task = seed_users(db)
        payload = WorkflowTransitionInput(
            source="todo", target="production",
            actions=[{"action": "assign_internal_user", "config": {"user_id": 3}}],
        )
        with pytest.raises(HTTPException):
            validate_workflow_assignees(db, payload)
        condition_payload = WorkflowTransitionInput(
            source="todo", target="production",
            conditions=[{"field": "assignee", "operator": "eq", "value": 3}],
        )
        with pytest.raises(HTTPException):
            validate_workflow_assignees(db, condition_payload)
    engine.dispose()
