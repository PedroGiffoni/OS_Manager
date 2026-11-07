from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.integration_events import record_development_event
from app.models import Audit, AutomationRule, DevelopmentEvent, Role, Task, User


def test_development_webhook_triggers_filtered_automation_once_per_delivery():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="internal"))
        db.flush()
        author = User(
            id=1,
            username="regra-autora",
            password_hash="hash",
            role="internal",
            grants=[],
        )
        db.add(author)
        db.flush()
        task = Task(id=10, title="Pipeline do card OS-10", creator_id=author.id, priority=1)
        matching_rule = AutomationRule(
            id=1,
            name="Marcar build aprovado",
            trigger="development_event",
            conditions={
                "development_providers": ["github"],
                "development_event_types": ["workflow_run"],
                "development_states": ["success"],
            },
            action="set_priority",
            config={"priority": 8},
            actions=[{"action": "set_priority", "config": {"priority": 8}}],
            author_id=author.id,
        )
        db.add_all([task, matching_rule])
        db.flush()

        accepted = record_development_event(
            db,
            provider="github",
            delivery_id="delivery-1",
            task=task,
            event_type="workflow_run",
            summary="Build concluído",
            actor_name="dev-user",
            metadata={"state": "success", "repository": "org/repo"},
        )
        duplicate = record_development_event(
            db,
            provider="github",
            delivery_id="delivery-1",
            task=task,
            event_type="workflow_run",
            summary="Build concluído",
            actor_name="dev-user",
            metadata={"state": "success", "repository": "org/repo"},
        )
        db.flush()

        assert accepted is True
        assert duplicate is False
        assert task.priority == 8
        assert len(db.scalars(select(DevelopmentEvent)).all()) == 1
        audits = db.scalars(
            select(Audit).where(Audit.action == "automation_applied")
        ).all()
        assert len(audits) == 1
        assert audits[0].details["development_event"] == {
            "provider": "github",
            "event_type": "workflow_run",
            "state": "success",
            "repository": "org/repo",
        }

        no_match = record_development_event(
            db,
            provider="github",
            delivery_id="delivery-2",
            task=task,
            event_type="workflow_run",
            summary="Build com falha",
            metadata={"state": "failure"},
        )
        db.flush()
        assert no_match is True
        assert task.priority == 8
        assert len(db.scalars(select(DevelopmentEvent)).all()) == 2
        assert len(db.scalars(select(Audit).where(Audit.action == "automation_applied")).all()) == 1

    engine.dispose()
