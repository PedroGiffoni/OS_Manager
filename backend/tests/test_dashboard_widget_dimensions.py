from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.dashboard_widgets import (
    current_status_age_days,
    current_status_entry_times,
    created_resolved_series,
    widget_group_keys,
    widget_group_sort_key,
    widget_measure_value,
)
from app.db import Base
from app.main import dashboard_widget_data, default_dashboard
from app.models import Audit, Component, DashboardWidget, KanbanColumn, Release, Role, Task, TaskComponent, TaskRelease, User
from app.schemas import DashboardWidgetInput


def test_widget_dimensions_cover_planning_hierarchy_and_deadline_groups():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        owner = User(username="dashboard-owner", role="admin", grants=[], password_hash="hash")
        db.add(owner)
        db.flush()
        parent = Task(title="Épico de referência", work_type="epic", creator_id=owner.id)
        task = Task(
            title="Card do release",
            creator_id=owner.id,
            parent_id=None,
            priority=3,
            work_type="bug",
            due="2026-10-28",
            estimated_minutes=300,
            used_minutes=120,
            status="production",
        )
        db.add_all([parent, task])
        db.flush()
        task.parent_id = parent.id
        release = Release(name="Versão 1", author_id=owner.id)
        component = Component(name="API", author_id=owner.id)
        db.add_all([release, component])
        db.flush()
        db.add_all([
            TaskRelease(task_id=task.id, release_id=release.id, author_id=owner.id),
            TaskComponent(task_id=task.id, component_id=component.id, author_id=owner.id),
        ])
        db.flush()

        assert widget_group_keys(db, task, "work_type") == ["Bug"]
        assert widget_group_keys(db, task, "release") == ["Versão 1"]
        assert widget_group_keys(db, task, "component") == ["API"]
        assert widget_group_keys(db, task, "parent") == [f"OS-{parent.id} · Épico de referência"]
        assert widget_group_keys(db, task, "parent", show_parent_details=False) == ["Card pai vinculado"]
        assert widget_group_keys(db, task, "due_month") == ["10/2026"]
        assert widget_group_keys(db, task, "created_month") == [task.created_at[5:7] + "/" + task.created_at[:4]]
        assert widget_group_keys(db, task, "overdue", today=date(2026, 11, 7)) == ["Atrasados"]
        assert widget_measure_value(task, "remaining_minutes") == 180
    engine.dispose()


def test_widget_dimensions_have_untitled_and_closed_safe_buckets():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        owner = User(username="dashboard-owner", role="admin", grants=[], password_hash="hash")
        db.add(owner)
        db.flush()
        task = Task(title="Sem vínculos", creator_id=owner.id, status="done", due="2026-10-01")
        db.add(task)
        db.flush()
        assert widget_group_keys(db, task, "release") == ["Sem release"]
        assert widget_group_keys(db, task, "component") == ["Sem componente"]
        assert widget_group_keys(db, task, "parent") == ["Sem card pai"]
        assert widget_group_keys(db, task, "due_month") == ["10/2026"]
        assert widget_group_keys(db, task, "overdue", today=date(2026, 11, 7)) == ["No prazo / sem prazo"]
        assert widget_measure_value(task, "avg_open_age_days", today=date(2026, 11, 7)) is None
    engine.dispose()


def test_dashboard_widget_schema_allows_new_groups_and_exact_remaining_measure():
    widget = DashboardWidgetInput(name="Cards por release", group_by="release", measure="remaining_minutes")
    assert widget.group_by == "release"
    assert widget.measure == "remaining_minutes"

    average = DashboardWidgetInput(name="Idade média", group_by="status", measure="avg_open_age_days", chart="line")
    assert average.measure == "avg_open_age_days"
    assert average.chart == "line"
    resolution = DashboardWidgetInput(
        name="Tempo de conclusão", group_by="resolved_month", measure="avg_resolution_days", chart="line"
    )
    assert resolution.measure == "avg_resolution_days"
    time_in_status = DashboardWidgetInput(
        name="Tempo na etapa", group_by="status", measure="avg_current_status_days", chart="bar"
    )
    assert time_in_status.measure == "avg_current_status_days"
    trend = DashboardWidgetInput(
        name="Criados × concluídos",
        group_by="created_month",
        measure="created_vs_resolved",
        chart="line",
    )
    assert trend.measure == "created_vs_resolved"
    matrix = DashboardWidgetInput(
        name="Status por prioridade", group_by="status", group_by_secondary="priority",
        measure="count", chart="matrix",
    )
    assert matrix.chart == "matrix"
    with pytest.raises(ValueError, match="duas dimensões"):
        DashboardWidgetInput(name="Matriz incompleta", group_by="status", chart="matrix")
    with pytest.raises(ValueError, match="diferentes"):
        DashboardWidgetInput(
            name="Matriz repetida", group_by="status", group_by_secondary="status", chart="matrix"
        )


def test_filter_results_widget_schema_validates_columns_and_limit():
    widget = DashboardWidgetInput(name="Resultados", group_by="status", chart="filter_results")
    assert widget.result_columns == ["key", "summary", "status", "priority", "assignee", "due"]
    assert widget.max_results == 50
    assert DashboardWidgetInput(
        name="Resultados customizados", group_by="status", chart="filter_results",
        result_columns=["key", "supplier"], max_results=10,
    ).result_columns == ["key", "supplier"]
    with pytest.raises(ValueError, match="Repita|repita"):
        DashboardWidgetInput(
            name="Coluna duplicada", group_by="status", chart="filter_results",
            result_columns=["key", "key"],
        )
    with pytest.raises(ValueError):
        DashboardWidgetInput(
            name="Limite inválido", group_by="status", chart="filter_results", max_results=101,
        )


def test_filter_results_widget_returns_only_selected_safe_columns_and_respects_filters():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        owner = User(username="results-dashboard", role="admin", grants=[], password_hash="hash")
        db.add(owner)
        db.flush()
        dashboard = default_dashboard(db, owner)
        matching = Task(
            title="Card filtrado", creator_id=owner.id, priority=1, status="todo",
            estimated_minutes=300, used_minutes=240,
        )
        excluded = Task(title="Outro card", creator_id=owner.id, priority=3, status="production")
        db.add_all([matching, excluded])
        db.flush()
        widget = DashboardWidget(
            user_id=owner.id, dashboard_id=dashboard.id, name="Resultados filtrados",
            jql="priority <= 2", group_by="status", measure="count", chart="filter_results",
            result_columns=["key", "summary", "priority"], max_results=1,
        )
        db.add(widget)
        db.flush()
        result = dashboard_widget_data(widget.id, jql="", user=owner, db=db)

    assert result["total"] == 1
    assert result["result_columns"] == ["key", "summary", "priority"]
    assert result["data"] == [{"key": f"OS-{matching.id}", "summary": "Card filtrado", "priority": 1}]
    assert "cost" not in str(result).lower()
    engine.dispose()


def test_created_month_widget_and_months_sort_chronologically():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        owner = User(username="dashboard-trend", role="admin", grants=[], password_hash="hash")
        db.add(owner)
        db.flush()
        task = Task(title="Criado em novembro", creator_id=owner.id, created_at="2026-11-07T10:00:00+00:00")
        old_task = Task(title="Card aberto antigo", creator_id=owner.id, status="production", created_at="2026-10-28T10:00:00+00:00")
        db.add(task)
        db.add(old_task)
        db.flush()

        assert widget_group_keys(db, task, "created_month") == ["11/2026"]
        assert widget_measure_value(old_task, "avg_open_age_days", today=date(2026, 11, 7)) == 10
        assert [name for name, _ in sorted(
            [("11/2026", 1), ("02/2026", 1), ("10/2025", 1)],
            key=lambda item: widget_group_sort_key(item, "created_month"),
        )] == ["10/2025", "02/2026", "11/2026"]
    engine.dispose()


def test_dashboard_time_in_current_status_uses_audit_and_applies_query_filters():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        owner = User(username="status-age-dashboard", role="admin", grants=[], password_hash="hash")
        db.add(owner)
        db.flush()
        db.add(KanbanColumn(key="production", title="Em produção", workflow_order=1, view_order=1, category="in_progress"))
        db.flush()
        now = datetime.now(timezone.utc)
        older_task = Task(
            title="Entrou nesta etapa há dez dias",
            creator_id=owner.id,
            status="production",
            priority=1,
            created_at=(now - timedelta(days=20)).isoformat(),
        )
        fallback_task = Task(
            title="Sem transição auditada",
            creator_id=owner.id,
            status="production",
            priority=2,
            created_at=(now - timedelta(days=5)).isoformat(),
        )
        db.add_all([older_task, fallback_task])
        db.flush()
        db.add_all(
            [
                Audit(
                    actor_id=owner.id,
                    entity="task",
                    entity_id=older_task.id,
                    action="status_changed",
                    details={"origin": "todo", "destination": "production"},
                    created_at=(now - timedelta(days=10)).isoformat(),
                ),
                Audit(
                    actor_id=owner.id,
                    entity="task",
                    entity_id=fallback_task.id,
                    action="status_changed",
                    details={"origin": "todo", "destination": "review"},
                    created_at=(now - timedelta(days=1)).isoformat(),
                ),
            ]
        )
        db.flush()
        entries = current_status_entry_times(db, [older_task, fallback_task])
        assert entries[older_task.id] == (now - timedelta(days=10)).isoformat()
        assert entries[fallback_task.id] == fallback_task.created_at
        assert current_status_age_days(entries[older_task.id], now=now) == 10

        dashboard = default_dashboard(db, owner)
        widget = DashboardWidget(
            user_id=owner.id,
            dashboard_id=dashboard.id,
            name="Tempo na etapa",
            group_by="status",
            measure="avg_current_status_days",
            chart="bar",
        )
        db.add(widget)
        db.flush()
        complete = dashboard_widget_data(widget.id, jql="", user=owner, db=db)
        filtered = dashboard_widget_data(
            widget.id, jql="priority = 1", user=owner, db=db
        )

    assert complete["data"] == [{"name": "Em produção", "value": 7.5}]
    assert filtered["data"] == [{"name": "Em produção", "value": 10.0}]
    engine.dispose()


def test_resolution_gadgets_use_audited_completion_time():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        owner = User(username="resolution-dashboard", role="admin", grants=[], password_hash="hash")
        db.add(owner)
        db.flush()
        task = Task(
            title="Concluído",
            creator_id=owner.id,
            status="done",
            created_at="2026-11-01T09:00:00+00:00",
        )
        db.add(task)
        db.flush()
        db.add_all([
            Audit(
                actor_id=owner.id,
                entity="task",
                entity_id=task.id,
                action="status_changed",
                details={"origin": "review", "destination": "done"},
                created_at="2026-11-07T15:00:00+00:00",
            ),
            Audit(
                actor_id=owner.id,
                entity="task",
                entity_id=task.id,
                action="status_changed",
                details={"origin": "done", "destination": "review"},
                created_at="2026-11-08T10:00:00+00:00",
            ),
            Audit(
                actor_id=owner.id,
                entity="task",
                entity_id=task.id,
                action="status_changed",
                details={"origin": "review", "destination": "done"},
                created_at="2026-11-10T10:00:00+00:00",
            ),
        ])
        db.flush()
        latest_resolution = "2026-11-10T10:00:00+00:00"
        assert widget_group_keys(db, task, "resolved_month", resolved_at=latest_resolution) == ["11/2026"]
        assert widget_measure_value(task, "avg_resolution_days", resolved_at=latest_resolution) == 9
        assert widget_measure_value(task, "avg_resolution_days") is None
        task.created_at = "2026-09-01T09:00:00+00:00"
        trend = created_resolved_series([task], {task.id: latest_resolution})
        assert trend == [
            {"name": "09/2026", "created": 1, "resolved": 0},
            {"name": "10/2026", "created": 0, "resolved": 0},
            {"name": "11/2026", "created": 0, "resolved": 1},
        ]
    engine.dispose()
