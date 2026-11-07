from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.collaboration import CommentInput, _record_attachment_added, add_comment
from app.db import Base
from app.models import Attachment, Audit, AutomationRule, Comment, Role, Task, User


def test_user_comment_runs_automation_without_recursive_comment_trigger():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="comment-actor", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        task = Task(title="Comentário com regra", creator_id=actor.id)
        rule = AutomationRule(
            name="Responder comentário",
            trigger="comment_added",
            conditions={"comment_contains": "inicial"},
            action="add_comment",
            config={"body": "Comentário automático"},
            actions=[{"action": "add_comment", "config": {"body": "Comentário automático"}}],
            author_id=actor.id,
        )
        db.add_all([task, rule])
        db.flush()

        result = add_comment(task.id, CommentInput(body="Comentário inicial"), user=actor, db=db)

        comments = list(db.scalars(select(Comment).where(Comment.task_id == task.id).order_by(Comment.id)))
        automation_audits = list(
            db.scalars(select(Audit).where(Audit.entity == "task", Audit.entity_id == task.id, Audit.action == "automation_applied"))
        )
        assert result["id"] == comments[0].id
        assert [row.body for row in comments] == ["Comentário inicial", "Comentário automático"]
        assert len(automation_audits) == 1
        assert automation_audits[0].details["trigger"] == "comment_added"
        assert automation_audits[0].details["source_event"] == {"comment_id": comments[0].id}
        assert "Comentário inicial" not in str(automation_audits[0].details)
    engine.dispose()


def test_attachment_event_runs_automation_and_records_only_safe_source_metadata():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        actor = User(username="attachment-actor", password_hash="hash", role="admin", grants=[])
        db.add(actor)
        db.flush()
        task = Task(title="Anexo com regra", creator_id=actor.id)
        rule = AutomationRule(
            name="Priorizar anexo",
            trigger="attachment_added",
            conditions={"attachment_media_types": ["text/plain"]},
            action="set_priority",
            config={"priority": 7},
            actions=[{"action": "set_priority", "config": {"priority": 7}}],
            author_id=actor.id,
        )
        db.add_all([task, rule])
        db.flush()
        attachment = Attachment(
            task_id=task.id,
            name="nome-confidencial.txt",
            media_type="text/plain",
            content=b"comprovante de teste",
            size=len(b"comprovante de teste"),
            sha256="a" * 64,
            author_id=actor.id,
        )
        db.add(attachment)
        db.flush()
        _record_attachment_added(db, actor, task, attachment)
        db.flush()

        audit_row = db.scalar(
            select(Audit).where(Audit.entity == "task", Audit.entity_id == task.id, Audit.action == "automation_applied")
        )
        assert task.priority == 7
        assert audit_row.details["trigger"] == "attachment_added"
        assert audit_row.details["source_event"] == {
            "attachment_id": attachment.id,
            "media_type": "text/plain",
            "size": len(b"comprovante de teste"),
        }
        assert "nome-confidencial" not in str(audit_row.details)
    engine.dispose()
