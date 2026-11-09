from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.automation import matches, run_automations, run_due_scheduled_automations
from app.db import Base
from app.main import automation_payload, include_task, sprint_action, update_task_schedule
from app.models import Audit, AutomationRule, AutomationRun, Board, Comment, Role, SchemaVersion, Sprint, SprintTask, Task, TaskWatcher, User
from app.schemas import AssignSprint, SprintAction, TaskScheduleInput
from app.schemas import AutomationRuleInput


@pytest.mark.parametrize(
    "trigger",
    [
        "card_created",
        "task_updated",
        "field_changed",
        "assignee_changed",
        "due_changed",
        "priority_changed",
        "status_changed",
        "comment_added",
        "attachment_added",
        "link_added",
        "link_removed",
        "hours_submitted",
        "hours_decided",
        "sprint_started",
        "sprint_completed",
        "sprint_scope_changed",
        "development_event",
        "scheduled_daily",
    ],
)
def test_supported_automation_events_accept_bounded_rules(trigger):
    rule = AutomationRuleInput(
        name="Regra de teste",
        trigger=trigger,
        schedule_time="08:30" if trigger == "scheduled_daily" else None,
        action="set_priority",
        conditions={"approval_states": ["approved", "rejected"]},
        config={"priority": 5},
    )
    assert rule.trigger == trigger


def test_field_changed_trigger_is_allowlisted_and_matches_only_selected_fields():
    configured = AutomationRuleInput(
        name="Prioridade ou área mudou",
        trigger="field_changed",
        conditions={"changed_fields": ["priority", "area"]},
        actions=[{"action": "set_priority", "config": {"priority": 5}}],
    )
    task = SimpleNamespace(
        status="todo", work_type="task", approval="pending", priority=1,
        labels=[], due=None, assignee_user_id=None,
    )
    assert matches(
        SimpleNamespace(conditions=configured.conditions),
        task,
        event_context={"changed_fields": ["area"]},
    )
    assert not matches(
        SimpleNamespace(conditions=configured.conditions),
        task,
        event_context={"changed_fields": ["title"]},
    )
    with pytest.raises(ValidationError):
        AutomationRuleInput(
            name="Campo sem gatilho",
            trigger="task_updated",
            conditions={"changed_fields": ["priority"]},
            actions=[{"action": "set_priority", "config": {"priority": 5}}],
        )
    with pytest.raises(ValidationError):
        AutomationRuleInput(
            name="ID inválido",
            trigger="field_changed",
            conditions={"changed_fields": ["bad field"]},
            actions=[{"action": "set_priority", "config": {"priority": 5}}],
        )


def test_sprint_scope_trigger_filters_addition_and_removal():
    configured = AutomationRuleInput(
        name="Ao retirar da sprint",
        trigger="sprint_scope_changed",
        conditions={"sprint_scope_actions": ["removed"]},
        actions=[{"action": "add_label", "config": {"text": "backlog", "color": "#2563eb"}}],
    )
    task = SimpleNamespace(
        status="backlog", work_type="task", approval="pending", priority=1,
        labels=[], due=None, assignee_user_id=None,
    )
    rule = SimpleNamespace(conditions=configured.conditions)
    assert matches(rule, task, event_context={"action": "removed", "sprint_id": 7})
    assert not matches(rule, task, event_context={"action": "added", "sprint_id": 7})
    with pytest.raises(ValidationError):
        AutomationRuleInput(
            name="Ação fora do gatilho", trigger="card_created",
            conditions={"sprint_scope_actions": ["removed"]}, action="set_priority",
            config={"priority": 2},
        )


def test_automation_conditions_can_filter_approval_state():
    rule = SimpleNamespace(
        conditions={
            "approval_states": ["rejected"],
            "work_types": ["bug"],
            "priority_min": 2,
            "due_set": True,
        }
    )
    task = SimpleNamespace(
        status="review",
        work_type="bug",
        approval="rejected",
        priority=4,
        labels=[],
        due="2026-11-10",
    )
    assert matches(rule, task)
    task.approval = "approved"
    assert not matches(rule, task)
    task.approval = "rejected"
    task.due = None
    assert not matches(rule, task)


def test_scheduled_automation_filters_overdue_and_due_window():
    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).date()
    task = SimpleNamespace(
        status="todo", work_type="task", approval="pending", priority=0,
        labels=[], due=(today + timedelta(days=3)).isoformat(), assignee_user_id=None,
    )
    rule = SimpleNamespace(conditions={"due_within_days": 5, "overdue": False})
    assert matches(rule, task)
    task.due = (today + timedelta(days=8)).isoformat()
    assert not matches(rule, task)
    task.due = (today - timedelta(days=1)).isoformat()
    assert not matches(rule, task)
    rule.conditions = {"overdue": True}
    assert matches(rule, task)


def test_automation_validates_due_date_window_conditions():
    with pytest.raises(ValidationError):
        AutomationRuleInput(
            name="Janela inválida", trigger="scheduled_daily", schedule_time="09:00",
            action="set_priority", config={"priority": 1}, conditions={"due_within_days": -1},
        )
    with pytest.raises(ValidationError):
        AutomationRuleInput(
            name="Booleano inválido", trigger="scheduled_daily", schedule_time="09:00",
            action="set_priority", config={"priority": 1}, conditions={"overdue": 1},
        )


def test_weekly_automation_schedule_validates_days_and_frequency():
    weekly = AutomationRuleInput(
        name="Rotina semanal",
        trigger="scheduled_daily",
        schedule_time="09:00",
        schedule_frequency="weekly",
        schedule_weekdays=[2, 0],
        action="set_priority",
        config={"priority": 1},
    )
    assert weekly.schedule_weekdays == [0, 2]
    payload = automation_payload(SimpleNamespace(
        id=1,
        name=weekly.name,
        trigger=weekly.trigger,
        schedule_time=weekly.schedule_time,
        schedule_frequency=weekly.schedule_frequency,
        schedule_weekdays=weekly.schedule_weekdays,
        conditions=weekly.conditions,
        action=weekly.action,
        config=weekly.config,
        actions=[{"action": "set_priority", "config": {"priority": 1}}],
        enabled=True,
    ))
    assert payload["schedule_frequency"] == "weekly"
    assert payload["schedule_weekdays"] == [0, 2]
    with pytest.raises(ValidationError, match="dias da semana"):
        AutomationRuleInput(
            name="Sem dia",
            trigger="scheduled_daily",
            schedule_time="09:00",
            schedule_frequency="weekly",
            action="set_priority",
            config={"priority": 1},
        )
    with pytest.raises(ValidationError, match="únicos"):
        AutomationRuleInput(
            name="Dia duplicado",
            trigger="scheduled_daily",
            schedule_time="09:00",
            schedule_frequency="weekly",
            schedule_weekdays=[1, 1],
            action="set_priority",
            config={"priority": 1},
        )
    with pytest.raises(ValidationError):
        AutomationRuleInput(
            name="Dia inválido",
            trigger="scheduled_daily",
            schedule_time="09:00",
            schedule_frequency="weekly",
            schedule_weekdays=[7],
            action="set_priority",
            config={"priority": 1},
        )


def test_custom_field_automation_condition_matches_current_schema_values_with_types():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="field-rule-admin", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        task = Task(title="Card configurável", creator_id=actor.id)
        db.add(task)
        db.flush()
        db.add(SchemaVersion(
            task_id=task.id,
            version=1,
            fields=[
                {"id": "area", "label": "Área", "type": "select"},
                {"id": "hours", "label": "Horas", "type": "number"},
                {"id": "urgent", "label": "Urgente", "type": "checkbox"},
            ],
            values={"area": "Operações", "hours": 12, "urgent": True},
            author_id=actor.id,
        ))
        db.flush()
        rule = SimpleNamespace(conditions={"custom_field_equals": {"area": "Operações", "hours": 12.0, "urgent": True}})
        assert matches(rule, task, db)
        rule.conditions = {"custom_field_equals": {"urgent": 1}}
        assert not matches(rule, task, db)
        rule.conditions = {"custom_field_equals": {"removed_field": "value"}}
        assert not matches(rule, task, db)
        assert not matches(rule, task)
    engine.dispose()


def test_automation_custom_field_conditions_validate_scalar_json_and_field_ids():
    valid = AutomationRuleInput(
        name="Área prioritária",
        trigger="task_updated",
        conditions={"custom_field_equals": {"area": "Operações", "urgent": True, "hours": 8}},
        actions=[{"action": "set_priority", "config": {"priority": 5}}],
    )
    assert valid.conditions["custom_field_equals"]["urgent"] is True
    for invalid in (
        {"invalid-key!": "x"},
        {"field": {"nested": "object"}},
        {"field": ["array"]},
        {f"field_{index}": index for index in range(11)},
    ):
        with pytest.raises(ValidationError):
            AutomationRuleInput(
                name="Condição inválida",
                trigger="task_updated",
                conditions={"custom_field_equals": invalid},
                actions=[{"action": "set_priority", "config": {"priority": 5}}],
            )
def test_development_event_automation_conditions_are_bounded_to_scm_trigger():
    valid = AutomationRuleInput(
        name="Build aprovado",
        trigger="development_event",
        conditions={
            "development_providers": ["github"],
            "development_event_types": ["workflow_run"],
            "development_states": ["success"],
        },
        actions=[{"action": "set_priority", "config": {"priority": 5}}],
    )
    assert valid.conditions["development_providers"] == ["github"]
    with pytest.raises(ValidationError):
        AutomationRuleInput(
            name="Provedor inválido",
            trigger="development_event",
            conditions={"development_providers": ["unknown"]},
            actions=[{"action": "set_priority", "config": {"priority": 5}}],
        )


def test_comment_and_attachment_event_filters_are_bounded_and_match_metadata():
    comment_rule = AutomationRuleInput(
        name="Comentar demanda específica",
        trigger="comment_added",
        conditions={"comment_contains": "urgente"},
        actions=[{"action": "set_priority", "config": {"priority": 5}}],
    )
    attachment_rule = AutomationRuleInput(
        name="Anexo de evidência",
        trigger="attachment_added",
        conditions={"attachment_media_types": ["application/pdf", "image/png"]},
        actions=[{"action": "set_priority", "config": {"priority": 5}}],
    )
    task = SimpleNamespace(
        status="todo", work_type="task", approval="pending", assignee_user_id=None,
        priority=1, labels=[], due=None,
    )
    assert matches(
        SimpleNamespace(conditions=comment_rule.conditions),
        task,
        event_context={"comment_body": "A entrega é urgente", "comment_id": 4},
    )
    assert not matches(
        SimpleNamespace(conditions=comment_rule.conditions),
        task,
        event_context={"comment_body": "Acompanhar depois", "comment_id": 5},
    )
    assert matches(
        SimpleNamespace(conditions=attachment_rule.conditions),
        task,
        event_context={"media_type": "application/pdf"},
    )
    assert not matches(
        SimpleNamespace(conditions=attachment_rule.conditions),
        task,
        event_context={"media_type": "text/plain"},
    )
    with pytest.raises(ValidationError):
        AutomationRuleInput(
            name="Comentário em gatilho errado",
            trigger="card_created",
            conditions={"comment_contains": "urgente"},
            actions=[{"action": "set_priority", "config": {"priority": 5}}],
        )
    with pytest.raises(ValidationError):
        AutomationRuleInput(
            name="Tipo de arquivo não permitido",
            trigger="attachment_added",
            conditions={"attachment_media_types": ["application/x-executable"]},
            actions=[{"action": "set_priority", "config": {"priority": 5}}],
        )


def test_link_automation_filters_are_bounded_to_link_events():
    for trigger in ("link_added", "link_removed"):
        rule = AutomationRuleInput(
            name="Relacionar atividade",
            trigger=trigger,
            conditions={"link_types": ["blocks", "duplicates"]},
            actions=[{"action": "set_priority", "config": {"priority": 4}}],
        )
        assert matches(
            rule,
            SimpleNamespace(),
            event_context={"link_type": "blocks", "target_task_id": 12},
        )
        assert not matches(
            rule,
            SimpleNamespace(),
            event_context={"link_type": "relates", "target_task_id": 12},
        )
    for trigger, conditions in (
        ("task_updated", {"link_types": ["blocks"]}),
        ("link_added", {"link_types": ["unknown"]}),
        ("link_removed", {"link_types": []}),
    ):
        with pytest.raises(ValidationError):
            AutomationRuleInput(
                name="Relação inválida",
                trigger=trigger,
                conditions=conditions,
                actions=[{"action": "set_priority", "config": {"priority": 4}}],
            )
    with pytest.raises(ValidationError):
        AutomationRuleInput(
            name="Gatilho incorreto",
            trigger="card_created",
            conditions={"development_states": ["success"]},
            actions=[{"action": "set_priority", "config": {"priority": 5}}],
        )
def test_automation_rejects_unknown_approval_states_and_triggers():
    with pytest.raises(ValidationError):
        AutomationRuleInput(
            name="Regra inválida",
            trigger="hours_decided",
            action="set_priority",
            conditions={"approval_states": ["paid"]},
            config={"priority": 1},
        )
    with pytest.raises(ValidationError):
        AutomationRuleInput(
            name="Agendamento sem horário",
            trigger="scheduled_daily",
            action="set_priority",
            config={"priority": 1},
        )


def test_automation_accepts_and_orders_multiple_validated_actions():
    rule = AutomationRuleInput(
        name="Preparar card",
        trigger="card_created",
        actions=[
            {"action": "set_priority", "config": {"priority": 8}},
            {"action": "add_label", "config": {"text": "Triagem", "color": "#2B4EDA"}},
            {"action": "remove_label", "config": {"text": "Legado"}},
            {"action": "set_due_after_days", "config": {"days": 14}},
            {"action": "add_comment", "config": {"body": "Card recebido."}},
            {"action": "add_watcher", "config": {"user_id": 19}},
        ],
    )
    assert [action.action for action in rule.actions] == ["set_priority", "add_label", "remove_label", "set_due_after_days", "add_comment", "add_watcher"]
    assert rule.action == "set_priority"
    assert rule.config == {"priority": 8}
    with pytest.raises(ValidationError):
        AutomationRuleInput(
            name="Sem ações",
            trigger="card_created",
        )
    with pytest.raises(ValidationError):
        AutomationRuleInput(
            name="Ações demais",
            trigger="card_created",
            actions=[{"action": "add_comment", "config": {"body": "ok"}}] * 11,
        )


def test_automation_action_sequence_applies_in_order_with_one_audit_and_version():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="internal"))
        db.flush()
        actor = User(
            id=1,
            username="gestora",
            role="internal",
            password_hash="test-only",
            grants=[],
        )
        watcher = User(
            id=2,
            username="observador",
            role="internal",
            password_hash="test-only",
            grants=[],
        )
        db.add_all([actor, watcher])
        db.flush()
        db.add(Board(id=1, name="Quadro principal", author_id=actor.id))
        db.flush()
        task = Task(id=1, title="Card para comentar", creator_id=1, labels=[{"text": "Legado", "color": "#888888"}])
        rule = AutomationRule(
            id=1,
            name="Preparar card",
            trigger="card_created",
            action="set_priority",
            conditions={},
            config={"priority": 8},
            actions=[
                {"action": "set_priority", "config": {"priority": 8}},
                {"action": "add_label", "config": {"text": "Triagem", "color": "#2B4EDA"}},
                {"action": "remove_label", "config": {"text": "legado"}},
                {"action": "set_due_after_days", "config": {"days": 14}},
                {"action": "add_comment", "config": {"body": "Revisar entrega antes da aprovação."}},
                {"action": "add_watcher", "config": {"user_id": 2}},
            ],
            author_id=1,
        )
        db.add_all([task, rule])
        db.flush()
        initial_version = task.version

        run_automations(db, actor, task, "card_created")
        db.flush()

        comment = db.scalar(select(Comment).where(Comment.task_id == task.id))
        audit = db.scalar(select(Audit).where(Audit.action == "automation_applied"))
        assert comment.body == "Revisar entrega antes da aprovação."
        assert comment.author_id == actor.id
        assert audit.details["comment_id"] == comment.id
        assert task.priority == 8
        assert task.labels == [{"text": "Triagem", "color": "#2B4EDA"}]
        assert task.due == (date.fromisoformat(task.created_at[:10]) + timedelta(days=14)).isoformat()
        assert task.version == initial_version + 1
        assert list(audit.details["changes"]) == ["priority", "labels", "due"]
        assert audit.details["comment_ids"] == [comment.id]
        assert audit.details["watcher_ids_added"] == [watcher.id]
        assert db.scalar(
            select(TaskWatcher).where(TaskWatcher.task_id == task.id, TaskWatcher.user_id == watcher.id)
        ) is not None

        run_automations(db, actor, task, "card_created")
        db.flush()
        assert len(db.scalars(select(TaskWatcher).where(TaskWatcher.task_id == task.id)).all()) == 1
    engine.dispose()


def test_assignee_changed_automation_applies_once_and_is_not_recursively_triggered():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(id=1, username="owner", role="admin", password_hash="hash", grants=[])
        db.add(actor)
        db.flush()
        task = Task(id=1, title="Mudar responsável", creator_id=actor.id)
        rule = AutomationRule(
            id=1,
            name="Marcar reatribuição",
            trigger="assignee_changed",
            action="add_label",
            config={"text": "Reatribuído", "color": "#2B4EDA"},
            conditions={},
            author_id=actor.id,
        )
        db.add_all([task, rule])
        db.flush()

        run_automations(db, actor, task, "assignee_changed")
        run_automations(db, actor, task, "assignee_changed")
        db.flush()

        assert task.labels == [{"text": "Reatribuído", "color": "#2B4EDA"}]
        events = db.scalars(select(Audit).where(Audit.action == "automation_applied")).all()
        assert len(events) == 1
        assert events[0].details["trigger"] == "assignee_changed"
    engine.dispose()


def test_due_changed_automation_records_old_and_new_deadline():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(id=1, username="owner", role="admin", password_hash="hash", grants=[])
        task = Task(id=1, title="Alterar prazo", creator_id=1, due="2026-11-10")
        rule = AutomationRule(
            id=1,
            name="Avisar mudança de prazo",
            trigger="due_changed",
            action="set_priority",
            config={"priority": 4},
            conditions={},
            author_id=1,
        )
        db.add_all([actor, task, rule])
        db.flush()

        run_automations(
            db, actor, task, "due_changed",
            event_context={"old_due": "2026-11-10", "new_due": "2026-11-14"},
        )
        db.flush()

        audit = db.scalar(select(Audit).where(Audit.action == "automation_applied"))
        assert task.priority == 4
        assert audit.details["trigger"] == "due_changed"
        assert audit.details["due_change"] == {"old_due": "2026-11-10", "new_due": "2026-11-14"}
    engine.dispose()


def test_priority_changed_automation_records_old_and_new_priority():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(id=1, username="owner", role="admin", password_hash="hash", grants=[])
        task = Task(id=1, title="Prioridade alterada", creator_id=1, priority=2)
        rule = AutomationRule(
            id=1,
            name="Marcar prioridade urgente",
            trigger="priority_changed",
            action="add_label",
            config={"text": "Urgente", "color": "#D94040"},
            conditions={"priority_min": 4},
            author_id=1,
        )
        db.add_all([actor, task, rule])
        db.flush()
        task.priority = 5

        run_automations(
            db, actor, task, "priority_changed",
            event_context={"old_priority": 2, "new_priority": 5},
        )
        db.flush()

        audit = db.scalar(select(Audit).where(Audit.action == "automation_applied"))
        assert task.labels == [{"text": "Urgente", "color": "#D94040"}]
        assert audit.details["priority_change"] == {"old_priority": 2, "new_priority": 5}
    engine.dispose()


def test_automation_can_version_and_audit_custom_field_updates():
    from app.models import TaskFieldChange

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(id=1, username="owner", role="admin", password_hash="hash", grants=[])
        db.add(actor)
        db.flush()
        task = Task(id=1, title="Campo via automação", creator_id=actor.id, status="todo")
        field = {
            "id": "area", "label": "Área", "type": "select", "options": ["Operações", "Dados"],
            "required_for": [], "editable_by": ["admin"], "visible_to": ["admin"],
        }
        db.add_all([
            task,
            SchemaVersion(task_id=task.id, version=1, fields=[field], values={"area": "Operações"}, author_id=actor.id),
            AutomationRule(
                id=1, name="Classificar por dados", trigger="card_created", action="set_custom_fields",
                config={"values": {"area": "Dados"}}, actions=[{
                    "action": "set_custom_fields", "config": {"values": {"area": "Dados"}},
                }], conditions={}, author_id=actor.id,
            ),
        ])
        db.flush()

        run_automations(db, actor, task, "card_created")
        db.flush()

        versions = db.scalars(select(SchemaVersion).where(SchemaVersion.task_id == task.id).order_by(SchemaVersion.version)).all()
        assert [row.values["area"] for row in versions] == ["Operações", "Dados"]
        audit = db.scalar(select(Audit).where(Audit.action == "automation_applied"))
        assert audit.details["changes"]["area"]["before"] == "Operações"
        assert audit.details["changes"]["area"]["after"] == "Dados"
        assert audit.details["changes"]["area"]["visible_to"] == ["admin"]
        normalized = db.scalar(select(TaskFieldChange).where(TaskFieldChange.audit_id == audit.id))
        assert normalized.field == "area"
    engine.dispose()


def test_schedule_endpoint_fires_due_changed_only_when_deadline_changes():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(id=1, username="owner", role="admin", password_hash="hash", grants=[])
        task = Task(id=1, title="Alterar cronograma", creator_id=1, due="2026-11-10")
        rule = AutomationRule(
            id=1,
            name="Marcar prazo alterado",
            trigger="due_changed",
            action="set_priority",
            config={"priority": 4},
            conditions={},
            author_id=1,
        )
        db.add_all([actor, task, rule])
        db.flush()

        update_task_schedule(
            task.id,
            TaskScheduleInput(planned_start="2026-11-08", due="2026-11-14", version=task.version),
            actor,
            db,
        )
        assert task.priority == 4
        events = db.scalars(
            select(Audit).where(Audit.action == "automation_applied")
        ).all()
        assert len(events) == 1
        assert events[0].details["due_change"] == {"old_due": "2026-11-10", "new_due": "2026-11-14"}

        update_task_schedule(
            task.id,
            TaskScheduleInput(planned_start="2026-11-08", due="2026-11-14", version=task.version),
            actor,
            db,
        )
        events = db.scalars(
            select(Audit).where(Audit.action == "automation_applied")
        ).all()
        assert len(events) == 1
    engine.dispose()


def test_comment_automation_requires_bounded_plain_text():
    valid = AutomationRuleInput(
        name="Comentário automático",
        trigger="card_created",
        action="add_comment",
        config={"body": "Iniciar checklist."},
    )
    assert valid.config["body"] == "Iniciar checklist."
    with pytest.raises(ValidationError):
        AutomationRuleInput(
            name="Comentário vazio",
            trigger="card_created",
            action="add_comment",
            config={"body": "   "},
        )


def test_starting_sprint_runs_card_automation_in_transaction():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(
            id=1,
            username="admin-teste",
            role="admin",
            password_hash="test-only",
            grants=[],
        )
        db.add(actor)
        db.flush()
        db.add(Board(id=1, name="Quadro principal", author_id=actor.id))
        db.flush()
        sprint = Sprint(
            id=1,
            name="Sprint automatizada",
            objective="Testar gatilhos",
            starts="2026-11-01",
            ends="2026-11-14",
            owner_id=actor.id,
        )
        task = Task(id=1, title="Card da sprint", creator_id=actor.id, sprint_id=1)
        db.add_all([sprint, task])
        db.flush()
        db.add_all(
            [
                SprintTask(task_id=task.id, sprint_id=sprint.id),
                AutomationRule(
                    name="Comentário no início",
                    trigger="sprint_started",
                    action="add_comment",
                    conditions={},
                    config={"body": "Sprint iniciada."},
                    author_id=actor.id,
                ),
            ]
        )
        db.flush()

        response = sprint_action(
            sprint.id,
            SprintAction(version=sprint.version, action="start"),
            actor,
            db,
        )

        assert response == {"ok": True}
        assert sprint.state == "active"
        assert db.scalar(select(Comment).where(Comment.task_id == task.id)).body == "Sprint iniciada."
        assert db.scalar(select(Audit).where(Audit.entity == "sprint")).action == "start"
    engine.dispose()
    with pytest.raises(ValidationError):
        AutomationRuleInput(
            name="Gatilho inválido",
            trigger="daily_schedule",
            action="set_priority",
            config={"priority": 1},
        )


def test_sprint_scope_automation_runs_when_card_is_added_and_returned():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="admin-scope", role="admin", password_hash="test-only", grants=[])
        db.add(actor)
        db.flush()
        sprint = Sprint(
            name="Escopo automatizado", objective="", starts="2026-11-01",
            ends="2026-11-14", owner_id=actor.id,
        )
        task = Task(title="Card em backlog", creator_id=actor.id)
        db.add_all([sprint, task])
        db.flush()
        db.add_all([
            AutomationRule(
                name="Ao entrar", trigger="sprint_scope_changed", action="add_label",
                conditions={"sprint_scope_actions": ["added"]},
                config={"text": "planejado", "color": "#2563eb"}, author_id=actor.id,
            ),
            AutomationRule(
                name="Ao voltar", trigger="sprint_scope_changed", action="add_label",
                conditions={"sprint_scope_actions": ["removed"]},
                config={"text": "replanejar", "color": "#dc2626"}, author_id=actor.id,
            ),
        ])
        db.flush()

        include_task(
            sprint.id,
            AssignSprint(version=sprint.version, task_id=task.id, task_version=task.version),
            actor,
            db,
        )
        assert {label["text"] for label in task.labels} == {"planejado"}

        sprint_action(sprint.id, SprintAction(version=sprint.version, action="start"), actor, db)
        sprint_action(sprint.id, SprintAction(version=sprint.version, action="close"), actor, db)
        assert task.status == "backlog"
        assert {label["text"] for label in task.labels} == {"planejado", "replanejar"}
        changes = db.scalars(
            select(Audit).where(Audit.action == "automation_applied").order_by(Audit.id)
        ).all()
        assert [row.details["sprint_scope_change"]["action"] for row in changes] == ["added", "removed"]
        assert all(row.details["sprint_scope_change"]["sprint_id"] == sprint.id for row in changes)
    engine.dispose()


def test_daily_automation_runs_once_per_utc_day_and_catches_up_after_restart():
    from datetime import datetime, timezone

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions() as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="admin-teste", role="admin", password_hash="test-only", grants=[])
        db.add(actor)
        db.flush()
        task = Task(title="Card da rotina", creator_id=actor.id, status="todo")
        rule = AutomationRule(
            name="Comentário diário",
            trigger="scheduled_daily",
            schedule_time="08:30",
            action="add_comment",
            conditions={"statuses": ["todo"]},
            config={"body": "Lembrete de acompanhamento."},
            author_id=actor.id,
        )
        db.add_all([task, rule])
        db.commit()

    instant = datetime(2026, 11, 7, 9, 0, tzinfo=timezone.utc)
    assert run_due_scheduled_automations(sessions, instant) == 1
    assert run_due_scheduled_automations(sessions, instant) == 0
    assert run_due_scheduled_automations(
        sessions, datetime(2026, 11, 8, 8, 29, tzinfo=timezone.utc)
    ) == 0
    assert run_due_scheduled_automations(
        sessions, datetime(2026, 11, 8, 8, 30, tzinfo=timezone.utc)
    ) == 1
    with sessions() as db:
        assert len(db.scalars(select(Comment)).all()) == 2
        assert len(db.scalars(select(Audit).where(Audit.action == "automation_applied")).all()) == 2
    engine.dispose()


def test_weekly_automation_runs_only_selected_utc_weekdays_and_is_idempotent():
    from datetime import datetime, timezone

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    with sessions() as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="admin-semanal", role="admin", password_hash="test-only", grants=[])
        db.add(actor)
        db.flush()
        task = Task(title="Card da rotina semanal", creator_id=actor.id, status="todo")
        rule = AutomationRule(
            name="Comentário às segundas e quartas",
            trigger="scheduled_daily",
            schedule_time="08:30",
            schedule_frequency="weekly",
            schedule_weekdays=[0, 2],
            action="add_comment",
            config={"body": "Revisar o andamento."},
            author_id=actor.id,
        )
        db.add_all([task, rule])
        db.commit()

    assert run_due_scheduled_automations(
        sessions, datetime(2026, 11, 9, 8, 29, tzinfo=timezone.utc)
    ) == 0
    assert run_due_scheduled_automations(
        sessions, datetime(2026, 11, 9, 8, 30, tzinfo=timezone.utc)
    ) == 1
    assert run_due_scheduled_automations(
        sessions, datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
    ) == 0
    assert run_due_scheduled_automations(
        sessions, datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc)
    ) == 0
    assert run_due_scheduled_automations(
        sessions, datetime(2026, 11, 11, 8, 30, tzinfo=timezone.utc)
    ) == 1
    with sessions() as db:
        assert len(db.scalars(select(Comment)).all()) == 2
        assert len(db.scalars(select(AutomationRun)).all()) == 2
    engine.dispose()
