from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Release, Task, User
from app.planning_reporting import planning_report


class PlanningReportSession:
    def __init__(self, container, tasks):
        self.container = container
        self.tasks = tasks

    def get(self, model, identity):
        expected = Task if hasattr(self.container, "work_type") else Release
        if model is expected and identity == self.container.id:
            return self.container
        return None

    def scalars(self, statement):
        model = statement.column_descriptions[0]["entity"]
        return iter(self.tasks if model is Task else [])


def test_epic_progress_report_aggregates_children_without_financial_values():
    epic = SimpleNamespace(id=9, title="Épico de teste", work_type="epic", archived=False)
    tasks = [
        SimpleNamespace(
            id=10,
            title="Concluída",
            work_type="task",
            status="done",
            priority=2,
            due=None,
            estimated_minutes=120,
            parent_id=9,
            archived=False,
        ),
        SimpleNamespace(
            id=11,
            title="Em andamento",
            work_type="task",
            status="production",
            priority=4,
            due="2026-12-01",
            estimated_minutes=60,
            parent_id=9,
            archived=False,
        ),
    ]
    result = planning_report(PlanningReportSession(epic, tasks), "epic", 9)
    assert result["summary"] == {
        "cards": 2,
        "completed": 1,
        "completion_percent": 50.0,
        "estimated_hours": 3.0,
    }
    assert [item["status"] for item in result["by_status"]] == ["done", "production"]
    assert "cost" not in str(result).lower()


def test_release_report_uses_associated_tasks():
    release = SimpleNamespace(
        id=4,
        name="Versão 1",
        starts="2026-11-01",
        due="2026-12-01",
        released_at=None,
        archived=False,
    )
    task = SimpleNamespace(
        id=15,
        title="Entrega",
        work_type="task",
        parent_id=None,
        status="todo",
        priority=1,
        due="2026-11-30",
        estimated_minutes=30,
    )
    result = planning_report(PlanningReportSession(release, [task]), "release", 4)
    assert result["container"]["name"] == "Versão 1"
    assert result["summary"]["cards"] == 1
    assert result["tasks"][0]["estimated_minutes"] == 30


def test_planning_report_applies_advanced_filter_before_aggregating():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(id=1, username="reporter", role="admin", grants=[], password_hash="hash"))
        db.flush()
        epic = Task(id=9, title="Épico", work_type="epic", creator_id=1)
        db.add(epic)
        db.flush()
        db.add_all([
            Task(id=10, title="Prioridade normal", parent_id=9, creator_id=1, priority=1),
            Task(id=11, title="Prioridade urgente", parent_id=9, creator_id=1, priority=4),
            Task(id=12, title="Subtarefa urgente", work_type="subtask", parent_id=10, creator_id=1, priority=4),
        ])
        db.flush()

        result = planning_report(db, "epic", 9, "priority >= 3")

    assert result["summary"]["cards"] == 2
    assert {row["id"] for row in result["tasks"]} == {11, 12}
    engine.dispose()
