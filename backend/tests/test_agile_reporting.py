from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agile_reporting import _forecast, _percentile, sprint_agile_report
from app.db import Base
from app.models import Audit, Sprint, SprintTask, Task, User


class ReportSession:
    def __init__(self, sprint, links, tasks, audits, sprint_audits=None):
        self.sprint = sprint
        self.links = links
        self.tasks = tasks
        self.audits = audits
        self.sprint_audits = sprint_audits or []

    def get(self, model, identity):
        return self.sprint if model is Sprint and identity == self.sprint.id else None

    def scalars(self, statement):
        model = statement.column_descriptions[0]["entity"]
        if model is SprintTask:
            return iter(self.links)
        if model is Task:
            return iter(self.tasks.values())
        if model is Audit:
            if "sprint" in statement.compile().params.values():
                return iter(self.sprint_audits)
            return iter(self.audits)
        if model is Sprint:
            return iter([])
        raise AssertionError(f"Consulta inesperada no relatório: {model}")


def test_agile_report_builds_burnup_burndown_flow_and_cycle_from_audit():
    sprint = SimpleNamespace(
        id=7,
        name="Sprint de teste",
        starts="2026-11-01",
        ends="2026-11-05",
        state="closed",
        archived=False,
    )
    task_done = SimpleNamespace(
        id=21, created_at="2026-10-20T12:00:00+00:00", status="done", estimated_minutes=120
    )
    task_open = SimpleNamespace(
        id=22, created_at="2026-10-21T12:00:00+00:00", status="todo", estimated_minutes=60
    )
    links = [
        SimpleNamespace(task_id=21, final_status="done", snapshot={"estimated_minutes": 120}),
        SimpleNamespace(task_id=22, final_status="todo", snapshot={"estimated_minutes": 60}),
    ]
    audits = [
        SimpleNamespace(
            entity_id=21, created_at="2026-11-01T10:00:00+00:00", details={"destination": "todo"}
        ),
        SimpleNamespace(
            entity_id=21,
            created_at="2026-11-02T10:00:00+00:00",
            details={"destination": "production"},
        ),
        SimpleNamespace(
            entity_id=21, created_at="2026-11-04T10:00:00+00:00", details={"destination": "done"}
        ),
        SimpleNamespace(
            entity_id=22, created_at="2026-11-01T11:00:00+00:00", details={"destination": "todo"}
        ),
    ]
    result = sprint_agile_report(
        ReportSession(sprint, links, {21: task_done, 22: task_open}, audits), 7
    )
    assert result["summary"]["committed_cards"] == 2
    assert result["summary"]["completed_cards"] == 1
    assert result["burndown"][0]["remaining"] == 2
    assert result["burndown"][-1]["remaining"] == 1
    assert result["burnup"][-1]["completed"] == 1
    assert result["cycle_times"] == [
        {
            "task_id": 21,
            "started_on": "2026-11-02",
            "completed_on": "2026-11-04",
            "days": 2.0,
            "cycle_number": 1,
        }
    ]
    assert result["control_chart"] == {
        "sample_count": 1,
        "average_days": 2.0,
        "p50_days": 2.0,
        "p85_days": 2.0,
        "p95_days": 2.0,
        "minimum_days": 2.0,
        "maximum_days": 2.0,
    }
    assert result["summary"]["planned_hours"] == 3
    assert result["issues"]["completed"] == [
        {"task_id": 21, "title": "OS-21", "status": "done", "estimated_hours": 2}
    ]
    assert result["issues"]["not_completed"] == [
        {"task_id": 22, "title": "OS-22", "status": "todo", "estimated_hours": 1}
    ]
    selected_window = sprint_agile_report(
        ReportSession(sprint, links, {21: task_done, 22: task_open}, audits),
        7,
        cycle_start_status="todo",
        cycle_end_status="done",
    )
    assert selected_window["cycle_window"] == {
        "start_status": "todo",
        "end_status": "done",
    }
    assert selected_window["cycle_times"][0]["days"] == 3.0


def test_agile_report_uses_closure_snapshot_for_issue_list():
    sprint = SimpleNamespace(
        id=7, name="Sprint encerrada", starts="2026-11-01", ends="2026-11-05",
        state="closed", archived=False,
    )
    task = SimpleNamespace(
        id=21, title="Título editado depois", created_at="2026-10-20T12:00:00+00:00",
        status="backlog", estimated_minutes=900,
    )
    link = SimpleNamespace(
        task_id=21, final_status="review",
        snapshot={"title": "Título no encerramento", "status": "review", "estimated_minutes": 120},
    )
    result = sprint_agile_report(ReportSession(sprint, [link], {21: task}, []), 7)

    assert result["issues"]["not_completed"] == [
        {"task_id": 21, "title": "Título no encerramento", "status": "review", "estimated_hours": 2}
    ]


def test_agile_report_identifies_cards_added_after_sprint_start():
    sprint = SimpleNamespace(
        id=7, name="Sprint ativa", starts="2026-11-01", ends="2026-11-10",
        state="active", archived=False,
    )
    tasks = {
        21: SimpleNamespace(id=21, title="Comprometido", created_at="2026-10-20T12:00:00+00:00", status="todo", estimated_minutes=60),
        22: SimpleNamespace(id=22, title="Adicionado depois", created_at="2026-10-21T12:00:00+00:00", status="todo", estimated_minutes=30),
    }
    links = [
        SimpleNamespace(task_id=21, final_status=None, snapshot={}),
        SimpleNamespace(task_id=22, final_status=None, snapshot={}),
    ]
    task_audits = [
        SimpleNamespace(entity_id=21, action="included_in_sprint", created_at="2026-11-01T09:00:00+00:00", details={"sprint_id": 7, "destination": "todo"}),
        SimpleNamespace(entity_id=22, action="included_in_sprint", created_at="2026-11-02T11:00:00+00:00", details={"sprint_id": 7, "destination": "todo"}),
    ]
    start_audit = SimpleNamespace(
        created_at="2026-11-01T10:00:00+00:00", details={"committed_task_ids": [21]}
    )

    result = sprint_agile_report(
        ReportSession(sprint, links, tasks, task_audits, [start_audit]), 7
    )

    assert [item["task_id"] for item in result["issues"]["added_during_sprint"]] == [22]


def test_effort_burndown_reconstructs_estimate_changes_from_start_snapshot_and_audit():
    sprint = SimpleNamespace(
        id=7, name="Sprint ativa", starts="2026-11-01", ends="2026-11-04",
        state="active", archived=False,
    )
    task = SimpleNamespace(
        id=21, title="Atividade", created_at="2026-10-20T12:00:00+00:00",
        status="done", estimated_minutes=180,
    )
    link = SimpleNamespace(task_id=21, final_status=None, snapshot={})
    audits = [
        SimpleNamespace(
            id=1, entity_id=21, action="status_changed", created_at="2026-11-02T10:00:00+00:00",
            details={"origin": "todo", "destination": "production"},
        ),
        SimpleNamespace(
            id=2, entity_id=21, action="hours_submitted", created_at="2026-11-03T10:00:00+00:00",
            details={"changes": [{"field": "estimated_minutes", "before": 120, "after": 180}]},
        ),
        SimpleNamespace(
            id=3, entity_id=21, action="status_changed", created_at="2026-11-04T10:00:00+00:00",
            details={"origin": "production", "destination": "done"},
        ),
    ]
    sprint_start = SimpleNamespace(
        created_at="2026-11-01T10:00:00+00:00",
        details={"committed_task_ids": [21], "committed_estimates": {"21": 120}},
    )

    result = sprint_agile_report(
        ReportSession(sprint, [link], {21: task}, audits, [sprint_start]), 7
    )

    assert result["effort_burndown"] == [
        {"date": "2026-11-01", "remaining_hours": 2, "scope_hours": 2},
        {"date": "2026-11-02", "remaining_hours": 2, "scope_hours": 2},
        {"date": "2026-11-03", "remaining_hours": 3, "scope_hours": 3},
        {"date": "2026-11-04", "remaining_hours": 0, "scope_hours": 3},
    ]


def test_forecast_uses_median_and_percentile_range_from_closed_sprints():
    forecast = _forecast(18, [6, 8, 10, 12])

    assert forecast["status"] == "ready"
    assert forecast["history_sprints"] == 4
    assert forecast["median_completed_hours_per_sprint"] == 9
    assert forecast["p25_completed_hours_per_sprint"] == 7.5
    assert forecast["p75_completed_hours_per_sprint"] == 10.5
    assert forecast["expected_sprints"] == 2
    assert forecast["minimum_sprints"] == 1.71
    assert forecast["maximum_sprints"] == 2.4


def test_forecast_does_not_invent_estimate_without_enough_history_or_lower_velocity():
    insufficient = _forecast(10, [6, 8])
    zero_lower = _forecast(10, [0, 0, 10])

    assert insufficient["status"] == "insufficient_history"
    assert insufficient["expected_sprints"] is None
    assert zero_lower["status"] == "zero_lower_velocity"
    assert zero_lower["maximum_sprints"] is None


def test_forecast_returns_zero_when_no_planned_work_remains():
    forecast = _forecast(0, [])

    assert forecast["status"] == "no_remaining_work"
    assert forecast["expected_sprints"] == 0
    assert forecast["minimum_sprints"] == 0
    assert forecast["maximum_sprints"] == 0


def test_agile_report_applies_advanced_query_to_sprint_and_historical_velocity():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(id=1, username="reporter", role="admin", grants=[], password_hash="hash"))
        db.flush()
        sprint = Sprint(
            id=7,
            name="Sprint de análise",
            objective="Validar filtros",
            starts="2026-11-01",
            ends="2026-11-05",
            state="active",
            owner_id=1,
        )
        db.add(sprint)
        low = Task(id=21, title="Prioridade baixa", creator_id=1, priority=1, estimated_minutes=60)
        high = Task(id=22, title="Prioridade alta", creator_id=1, priority=3, estimated_minutes=180)
        db.add_all([low, high])
        db.flush()
        db.add_all([
            SprintTask(task_id=21, sprint_id=7, snapshot={"estimated_minutes": 60}),
            SprintTask(task_id=22, sprint_id=7, snapshot={"estimated_minutes": 180}),
        ])
        db.flush()

        result = sprint_agile_report(db, 7, "priority >= 2")

    assert result["filter"]["jql"] == "priority >= 2"
    assert result["summary"]["committed_cards"] == 1
    assert result["summary"]["planned_hours"] == 3
    engine.dispose()


def test_control_chart_percentile_uses_linear_interpolation():
    assert _percentile([0, 10, 20, 30], 0.5) == 15
    assert round(_percentile([0, 10, 20, 30], 0.85), 2) == 25.5
