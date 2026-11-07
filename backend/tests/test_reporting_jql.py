from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.analytics import report
from app.db import Base
from app.models import Role, Task, User
from app.reporting import records


def test_operational_records_apply_jql_after_user_scope_and_other_filters():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="report-admin", password_hash="hash", role="admin", grants=[])
        other = User(username="other-admin", password_hash="hash", role="admin", grants=[])
        db.add_all([actor, other])
        db.flush()
        selected = Task(
            title="Demanda filtrada",
            priority=4,
            creator_id=actor.id,
            assignee_user_id=actor.id,
            created_at="2026-11-07T10:00:00+00:00",
        )
        lower_priority = Task(
            title="Prioridade baixa",
            priority=1,
            creator_id=actor.id,
            assignee_user_id=actor.id,
            created_at="2026-11-07T11:00:00+00:00",
        )
        other_assignee = Task(
            title="Outro responsável",
            priority=4,
            creator_id=actor.id,
            assignee_user_id=other.id,
            created_at="2026-11-07T12:00:00+00:00",
        )
        db.add_all([selected, lower_priority, other_assignee])
        db.flush()

        rows = records(
            db,
            actor,
            starts=None,
            ends=None,
            jql="priority >= 3 AND assignee = currentUser()",
        )
        assert [row["id"] for row in rows] == [selected.id]

        operational = report(
            db,
            actor,
            {
                "field_filters": "[]",
                "jql": "priority >= 3 AND assignee = currentUser()",
            },
            reference=datetime(2026, 11, 7, 18, tzinfo=timezone.utc),
        )
        assert operational["total"] == 1
        assert operational["jql"] == "priority >= 3 AND assignee = currentUser()"
        assert operational["items"][0]["id"] == selected.id

        high_priority = records(db, actor, jql="priority >= 3")
        assert {row["id"] for row in high_priority} == {selected.id, other_assignee.id}
    engine.dispose()
