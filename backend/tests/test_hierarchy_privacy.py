import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.main import task_hours_history, validate_parent
from app.models import Hours, Role, Supplier, Task, User
from app.services import task_payload


def test_supplier_payload_hides_parent_outside_supplier_scope():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="supplier"))
        db.flush()
        current_user = User(
            username="supplier-a", password_hash="hash", role="supplier", grants=[]
        )
        other_user = User(
            username="supplier-b", password_hash="hash", role="supplier", grants=[]
        )
        db.add_all([current_user, other_user])
        db.flush()
        current_supplier = Supplier(name="Fornecedor A", function="Dev", user_id=current_user.id)
        other_supplier = Supplier(name="Fornecedor B", function="Dev", user_id=other_user.id)
        db.add_all([current_supplier, other_supplier])
        db.flush()
        hidden_parent = Task(
            title="Atividade de outro fornecedor",
            creator_id=other_user.id,
            supplier_id=other_supplier.id,
        )
        visible_parent = Task(
            title="Atividade do fornecedor A",
            creator_id=current_user.id,
            supplier_id=current_supplier.id,
        )
        db.add_all([hidden_parent, visible_parent])
        db.flush()
        child = Task(
            title="Subtarefa atribuída",
            creator_id=current_user.id,
            supplier_id=current_supplier.id,
            work_type="subtask",
            parent_id=hidden_parent.id,
        )
        db.add(child)
        db.flush()

        payload = task_payload(db, current_user, child)
        assert payload["parent_id"] is None

        child.parent_id = visible_parent.id
        db.flush()
        payload = task_payload(db, current_user, child)
        assert payload["parent_id"] == visible_parent.id

        child.hours_version = 1
        db.add(Hours(
            task_id=child.id,
            version=1,
            estimated_minutes=60,
            used_minutes=30,
            author_id=other_user.id,
            comment="Nota de outro fornecedor",
        ))
        db.flush()
        assert task_payload(db, current_user, child)["worklog_comment"] == ""
        db.add(Hours(
            task_id=child.id,
            version=2,
            estimated_minutes=60,
            used_minutes=35,
            author_id=current_user.id,
            comment="Comentário do fornecedor atual",
        ))
        child.hours_version = 2
        db.flush()
        assert task_payload(db, current_user, child)["worklog_comment"] == "Comentário do fornecedor atual"
        own_history = task_hours_history(child.id, offset=0, limit=10, user=current_user, db=db)
        assert own_history["total"] == 1
        assert [entry["version"] for entry in own_history["items"]] == [2]
        assert own_history["items"][0]["comment"] == "Comentário do fornecedor atual"
        with pytest.raises(HTTPException) as denied_history:
            task_hours_history(child.id, offset=0, limit=10, user=other_user, db=db)
        assert denied_history.value.status_code == 404

    engine.dispose()


def test_hierarchy_enforces_epic_standard_card_and_subtask_levels():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="internal"))
        db.flush()
        actor = User(username="hierarchy-admin", password_hash="hash", role="internal", grants=[])
        db.add(actor)
        db.flush()
        epic = Task(title="Épico", creator_id=actor.id, work_type="epic")
        task = Task(title="Tarefa", creator_id=actor.id, work_type="task")
        story = Task(title="História", creator_id=actor.id, work_type="story")
        db.add_all([epic, task])
        db.flush()
        story.parent_id = epic.id
        db.add(story)
        db.flush()

        validate_parent(db, None, epic.id, "story")
        validate_parent(db, None, story.id, "subtask")
        with pytest.raises(HTTPException) as invalid_subtask_parent:
            validate_parent(db, None, epic.id, "subtask")
        assert "história, tarefa ou bug" in invalid_subtask_parent.value.detail["message"]
        with pytest.raises(HTTPException) as invalid_standard_parent:
            validate_parent(db, None, task.id, "story")
        assert "vinculados a um épico" in invalid_standard_parent.value.detail["message"]

        child = Task(
            title="Subtarefa",
            creator_id=actor.id,
            work_type="subtask",
            parent_id=task.id,
        )
        db.add(child)
        db.flush()
        with pytest.raises(HTTPException) as invalid_parent_retype:
            validate_parent(db, task, None, "epic")
        assert "cards filhos incompatíveis" in invalid_parent_retype.value.detail["message"]
    engine.dispose()
