from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Audit, Comment, KanbanColumn, Role, SchemaVersion, Task, User, WorkflowTransition
from app.schemas import WorkflowCondition, WorkflowTransitionInput, Move
from app.services import move_task
from app.workflows import conditions_match, transition_policy


def test_transition_policy_can_be_generic_or_scoped_by_card_type():
    scoped = SimpleNamespace(work_types=["bug", "task"], enabled=False)
    generic = SimpleNamespace(work_types=[], enabled=True)

    bug_policy = transition_policy([scoped], "bug")
    assert bug_policy.enabled is False
    assert transition_policy([scoped], "story") is None
    assert transition_policy([generic], "story").enabled is True


def test_transition_input_validates_supported_card_types():
    rule = WorkflowTransitionInput(
        source="todo", target="production", work_types=["bug", "task"]
    )
    assert rule.work_types == ["bug", "task"]
    with pytest.raises(ValidationError):
        WorkflowTransitionInput(
            source="todo", target="production", work_types=["bug", "bug"]
        )


def test_workflow_due_conditions_handle_overdue_windows_and_missing_dates():
    today = datetime.now(timezone.utc).date()
    def task(due, status="production"):
        return SimpleNamespace(
            due=due,
            status=status,
            approval="pending",
            work_type="task",
            priority=1,
            supplier_id=None,
            parent_id=None,
            assignee_user_id=None,
            labels=[],
        )

    overdue = task((today - timedelta(days=1)).isoformat())
    due_today = task(today.isoformat())
    outside_window = task((today + timedelta(days=8)).isoformat())
    completed = task((today - timedelta(days=1)).isoformat(), status="done")
    no_due = task(None)

    assert conditions_match([{"field": "due_overdue", "operator": "eq", "value": True}], overdue)
    assert not conditions_match([{"field": "due_overdue", "operator": "eq", "value": True}], completed)
    assert conditions_match([{"field": "due_within_days", "operator": "eq", "value": 7}], due_today)
    assert not conditions_match([{"field": "due_within_days", "operator": "eq", "value": 7}], outside_window)
    assert conditions_match([{"field": "due_within_days", "operator": "not_eq", "value": 7}], no_due)

    valid = WorkflowCondition(field="due_within_days", operator="eq", value=7)
    assert valid.value == 7
    with pytest.raises(ValidationError):
        WorkflowCondition(field="due_within_days", operator="eq", value=3651)
    with pytest.raises(ValidationError):
        WorkflowCondition(field="due_overdue", operator="gte", value=True)


def test_transition_policy_applies_different_type_rules_without_duplicate_rows():
    base = SimpleNamespace(
        work_types=[],
        type_rules={
            "bug": {"enabled": False, "roles": ["admin"], "required_fields": ["severity"]},
            "story": {"enabled": True, "roles": ["manager"], "required_fields": ["acceptance"]},
        },
        enabled=True,
        roles=[],
        required_fields=[],
    )
    bug = transition_policy([base], "bug")
    story = transition_policy([base], "story")
    task = transition_policy([base], "task")

    assert bug.enabled is False
    assert bug.allowed_roles == frozenset({"admin"})
    assert bug.required_fields == ("severity",)
    assert story.enabled is True
    assert story.allowed_roles == frozenset({"manager"})
    assert story.required_fields == ("acceptance",)
    assert task.enabled is True
    assert task.allowed_roles is None
    assert task.required_fields == ()


def test_transition_type_rules_validate_field_ids_and_roles():
    rule = WorkflowTransitionInput(
        source="todo",
        target="production",
        type_rules={"bug": {"roles": ["admin"], "required_fields": ["severity"]}},
    )
    assert rule.type_rules["bug"].roles == ["admin"]
    with pytest.raises(ValidationError):
        WorkflowTransitionInput(
            source="todo",
            target="production",
            type_rules={"bug": {"roles": ["invalid-role"]}},
        )
    with pytest.raises(ValidationError):
        WorkflowTransitionInput(
            source="todo",
            target="production",
            type_rules={"bug": {"required_fields": ["invalid-id!"]}},
        )


def test_type_policy_can_override_base_role_allowlist_and_add_fields():
    row = SimpleNamespace(
        work_types=[],
        enabled=True,
        roles=["admin", "internal"],
        required_fields=["common_check"],
        type_rules={"bug": {"enabled": True, "roles": ["manager"], "required_fields": ["severity"]}},
    )
    policy = transition_policy([row], "bug")
    assert policy.allowed_roles == frozenset({"manager"})
    assert policy.required_fields == ("common_check", "severity")


def test_workflow_conditions_and_actions_can_be_scoped_to_card_type():
    row = SimpleNamespace(
        work_types=[],
        enabled=True,
        roles=[],
        required_fields=[],
        conditions=[{"field": "priority", "operator": "gte", "value": 2}],
        actions=[{"action": "add_label", "config": {"text": "Validado", "color": "#2B4EDA"}}],
        type_rules={
            "bug": {
                "enabled": True,
                "roles": [],
                "required_fields": [],
                "conditions": [{"field": "due_set", "operator": "eq", "value": True}],
                "actions": [{"action": "add_comment", "config": {"body": "Revisar impacto."}}],
            }
        },
    )
    bug_policy = transition_policy([row], "bug")
    story_policy = transition_policy([row], "story")

    assert len(bug_policy.conditions) == 2
    assert [item["action"] for item in bug_policy.actions] == ["add_label", "add_comment"]
    assert len(story_policy.conditions) == 1
    assert [item["action"] for item in story_policy.actions] == ["add_label"]
    assert not conditions_match(bug_policy.conditions, SimpleNamespace(
        approval="pending", work_type="bug", priority=3, supplier_id=None,
        due=None, parent_id=None, labels=[],
    ))
    assert conditions_match(bug_policy.conditions, SimpleNamespace(
        approval="pending", work_type="bug", priority=3, supplier_id=None,
        due="2026-11-07", parent_id=None, labels=[],
    ))
    assert conditions_match([
        {"field": "label", "operator": "eq", "value": "urgente"},
        {"field": "parent_set", "operator": "eq", "value": True},
    ], SimpleNamespace(
        approval="pending", work_type="subtask", priority=0, supplier_id=None,
        due=None, parent_id=9, labels=[{"text": "URGENTE"}],
    ))


def test_type_specific_workflow_rules_validate_condition_and_action_catalogs():
    rule = WorkflowTransitionInput(
        source="todo",
        target="production",
        type_rules={"bug": {
            "conditions": [{"field": "label", "operator": "eq", "value": "Urgente"}],
            "actions": [{"action": "set_priority", "config": {"priority": 10}}],
        }},
    )
    assert rule.type_rules["bug"].conditions[0]["field"] == "label"
    with pytest.raises(ValidationError):
        WorkflowTransitionInput(source="todo", target="production", type_rules={"bug": {
            "conditions": [{"field": "unknown", "operator": "eq", "value": "x"}],
        }})


def test_transition_can_require_individual_custom_field_value_from_current_schema():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="workflow-field-admin", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        task = Task(title="Campo para transição", creator_id=actor.id)
        db.add(task)
        db.flush()
        db.add(SchemaVersion(
            task_id=task.id,
            version=1,
            fields=[{"id": "acceptance", "label": "Aceite", "type": "checkbox"}],
            values={"acceptance": True},
            author_id=actor.id,
        ))
        db.flush()
        task_stub = SimpleNamespace(
            id=task.id, approval="pending", work_type="task", priority=1,
            supplier_id=None, due=None, parent_id=None, labels=[],
        )
        rule = WorkflowTransitionInput(
            source="todo",
            target="production",
            conditions=[{
                "field": "custom_field_equals",
                "custom_field_id": "acceptance",
                "operator": "eq",
                "value": True,
            }],
        )
        assert conditions_match([condition.model_dump() for condition in rule.conditions], task_stub, db)
        task_schema = db.query(SchemaVersion).filter_by(task_id=task.id).one()
        task_schema.values = {"acceptance": False}
        db.flush()
        assert not conditions_match([condition.model_dump() for condition in rule.conditions], task_stub, db)
        not_equal = [{"field": "custom_field_equals", "custom_field_id": "acceptance", "operator": "not_eq", "value": True}]
        assert conditions_match(not_equal, task_stub, db)
        task_schema.fields = []
        db.flush()
        assert not conditions_match(not_equal, task_stub, db)
    engine.dispose()


def test_custom_field_transition_condition_requires_valid_id_and_scalar_value():
    valid = WorkflowTransitionInput(
        source="todo",
        target="production",
        conditions=[{"field": "custom_field_equals", "custom_field_id": "area", "operator": "eq", "value": "Operações"}],
    )
    assert valid.conditions[0].custom_field_id == "area"
    for condition in (
        {"field": "custom_field_equals", "custom_field_id": "bad-id!", "operator": "eq", "value": "x"},
        {"field": "custom_field_equals", "custom_field_id": "area", "operator": "gte", "value": "x"},
        {"field": "priority", "custom_field_id": "area", "operator": "gte", "value": 2},
    ):
        with pytest.raises(ValidationError):
            WorkflowTransitionInput(source="todo", target="production", conditions=[condition])


def test_workflow_conditions_and_actions_are_validated_as_allowlisted_values():
    rule = WorkflowTransitionInput(
        source="todo",
        target="production",
        conditions=[{"field": "priority", "operator": "gte", "value": 3}],
        actions=[{"action": "add_comment", "config": {"body": "Iniciar checklist."}}],
    )
    assert rule.conditions[0].value == 3
    assert rule.actions[0].config == {"body": "Iniciar checklist."}
    due_action = WorkflowTransitionInput(
        source="todo",
        target="production",
        actions=[{"action": "set_due_after_days", "config": {"days": 30}}],
    )
    assert due_action.actions[0].config == {"days": 30}
    watcher_action = WorkflowTransitionInput(
        source="todo",
        target="production",
        actions=[{"action": "add_watcher", "config": {"user_id": 9}}],
    )
    assert watcher_action.actions[0].action == "add_watcher"
    custom_field_action = WorkflowTransitionInput(
        source="todo",
        target="production",
        actions=[{"action": "set_custom_fields", "config": {"values": {"area": "Operações"}}}],
    )
    assert custom_field_action.actions[0].config["values"] == {"area": "Operações"}
    with pytest.raises(ValidationError):
        WorkflowTransitionInput(
            source="todo", target="production",
            actions=[{"action": "set_custom_fields", "config": {"values": {"bad-id!": "x"}}}],
        )
    remove_label = WorkflowTransitionInput(
        source="todo",
        target="production",
        actions=[{"action": "remove_label", "config": {"text": "Legado"}}],
    )
    assert remove_label.actions[0].config == {"text": "Legado"}
    with pytest.raises(ValidationError):
        WorkflowTransitionInput(
            source="todo",
            target="production",
            actions=[{"action": "remove_label", "config": {"text": " "}}],
        )
    with pytest.raises(ValidationError):
        WorkflowTransitionInput(
            source="todo",
            target="production",
            conditions=[{"field": "status", "operator": "eq", "value": "todo"}],
        )
    with pytest.raises(ValidationError):
        WorkflowTransitionInput(
            source="todo",
            target="production",
            actions=[{"action": "add_comment", "config": {"body": "<script>" * 500}}],
        )
    with pytest.raises(ValidationError):
        WorkflowTransitionInput(
            source="todo",
            target="production",
            actions=[{"action": "set_due_after_days", "config": {"days": -1}}],
        )


def test_transition_action_adds_internal_watcher_idempotently():
    from app.workflows import apply_transition_actions
    from app.models import TaskWatcher

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="internal"))
        db.flush()
        actor = User(id=1, username="ator", role="internal", password_hash="hash", grants=[])
        watcher = User(id=2, username="observador", role="internal", password_hash="hash", grants=[])
        db.add_all([actor, watcher])
        db.flush()
        task = Task(id=1, title="Acompanhar alteração", creator_id=actor.id)
        db.add(task)
        db.flush()
        actions = [{"action": "add_watcher", "config": {"user_id": watcher.id}}]

        apply_transition_actions(db, actor, task, actions, "todo", "production")
        apply_transition_actions(db, actor, task, actions, "todo", "production")
        db.flush()

        assert len(db.scalars(select(TaskWatcher).where(TaskWatcher.task_id == task.id)).all()) == 1
        audit = db.scalar(select(Audit).where(Audit.action == "workflow_actions_applied"))
        assert audit.details["watcher_ids_added"] == [watcher.id]
    engine.dispose()


def test_workflow_action_versions_and_audits_custom_field_edits():
    from app.models import TaskFieldChange
    from app.workflows import apply_transition_actions

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="manager"))
        db.flush()
        actor = User(id=1, username="gestora", role="manager", password_hash="hash", grants=[])
        db.add(actor)
        db.flush()
        task = Task(id=1, title="Atualizar área", creator_id=actor.id, status="todo")
        db.add(task)
        db.flush()
        field = {
            "id": "area", "label": "Área", "type": "short_text", "options": [],
            "required_for": [], "editable_by": ["manager"], "visible_to": ["manager"],
        }
        db.add(SchemaVersion(task_id=task.id, version=1, fields=[field], values={"area": "Operações"}, author_id=actor.id))
        db.flush()

        apply_transition_actions(
            db, actor, task,
            [{"action": "set_custom_fields", "config": {"values": {"area": "Finanças"}}}],
            "todo", "production",
        )
        db.flush()

        versions = db.scalars(select(SchemaVersion).where(SchemaVersion.task_id == task.id).order_by(SchemaVersion.version)).all()
        assert [version.values["area"] for version in versions] == ["Operações", "Finanças"]
        assert versions[-1].author_id == actor.id
        audit = db.scalar(select(Audit).where(Audit.action == "workflow_actions_applied"))
        assert audit.details["changes"][0]["field"] == "area"
        normalized = db.scalar(select(TaskFieldChange).where(TaskFieldChange.audit_id == audit.id))
        assert normalized.field == "area"
        assert normalized.before_json == '"Operações"'
        assert normalized.after_json == '"Finanças"'
    engine.dispose()


def test_transition_action_removes_label_case_insensitively_and_is_idempotent():
    from app.workflows import apply_transition_actions

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="internal"))
        db.flush()
        actor = User(id=1, username="ator", role="internal", password_hash="hash", grants=[])
        db.add(actor)
        db.flush()
        task = Task(
            id=1, title="Limpar etiqueta", creator_id=actor.id,
            labels=[{"text": "LEGADO", "color": "#888888"}, {"text": "Urgente", "color": "#FF0000"}],
        )
        db.add(task)
        db.flush()
        action = [{"action": "remove_label", "config": {"text": "legado"}}]

        apply_transition_actions(db, actor, task, action, "todo", "production")
        apply_transition_actions(db, actor, task, action, "todo", "production")
        db.flush()

        assert task.labels == [{"text": "Urgente", "color": "#FF0000"}]
        events = db.scalars(select(Audit).where(Audit.action == "workflow_actions_applied")).all()
        assert len(events) == 1
        assert events[0].details["changes"][0]["field"] == "labels"
    engine.dispose()


def test_configured_workflow_conditions_block_and_actions_apply_atomically():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="manager"))
        db.flush()
        manager = User(
            id=1,
            username="gestora",
            role="manager",
            password_hash="test-only",
            grants=[],
        )
        db.add(manager)
        db.flush()
        db.add_all([
            KanbanColumn(key="todo", title="A fazer", is_system=True, workflow_order=1, view_order=1),
            KanbanColumn(key="production", title="Em produção", is_system=True, workflow_order=2, view_order=2),
        ])
        task = Task(
            id=1,
            title="Card com regra",
            creator_id=manager.id,
            status="todo",
            priority=2,
            work_type="bug",
            estimated_minutes=60,
        )
        transition = WorkflowTransition(
            source="todo",
            target="production",
            enabled=True,
            roles=["manager"],
            work_types=[],
            type_rules={"bug": {
                "enabled": True,
                "roles": [],
                "required_fields": [],
                "conditions": [{"field": "due_set", "operator": "eq", "value": True}],
                "actions": [
                    {"action": "add_comment", "config": {"body": "Validar impacto do bug."}},
                    {"action": "set_due_after_days", "config": {"days": 7}},
                ],
            }},
            required_fields=[],
            conditions=[{"field": "priority", "operator": "gte", "value": 3}],
            actions=[
                {"action": "set_priority", "config": {"priority": 5}},
                {"action": "add_label", "config": {"text": "Pronto", "color": "#2B4EDA"}},
                {"action": "add_comment", "config": {"body": "Checklist iniciado."}},
            ],
            author_id=manager.id,
        )
        db.add_all([task, transition])
        db.flush()

        with pytest.raises(HTTPException) as error:
            move_task(db, manager, task, Move(version=task.version, status="production"))
        assert error.value.status_code == 409
        assert task.status == "todo"
        assert db.scalars(select(Comment)).all() == []

        task.priority = 3
        task.version += 1
        with pytest.raises(HTTPException) as error:
            move_task(db, manager, task, Move(version=task.version, status="production"))
        assert error.value.status_code == 409
        assert task.status == "todo"
        task.due = date(2026, 11, 7).isoformat()
        task.version += 1
        move_task(db, manager, task, Move(version=task.version, status="production"))
        db.flush()
        assert task.status == "production"
        assert task.priority == 5
        assert task.labels == [{"text": "Pronto", "color": "#2B4EDA"}]
        assert task.due == (date.fromisoformat(task.created_at[:10]) + timedelta(days=7)).isoformat()
        assert {row.body for row in db.scalars(select(Comment)).all()} == {
            "Checklist iniciado.", "Validar impacto do bug."
        }
        assert db.scalar(select(Audit).where(Audit.action == "workflow_actions_applied"))
    engine.dispose()

