from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.main import create_board
from app.models import Board, BoardMember, KanbanColumn, Role, User
from app.schemas import BoardInput


def test_new_board_gets_independent_columns_and_membership():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Role(id="admin"), Role(id="supplier")])
        db.flush()
        admin = User(id=1, username="admin", role="admin", password_hash="test", grants=[])
        supplier = User(id=2, username="supplier", role="supplier", password_hash="test", grants=[])
        db.add_all([admin, supplier])
        db.flush()
        db.add(Board(id=1, name="Quadro principal", author_id=admin.id))
        db.add(BoardMember(board_id=1, user_id=admin.id, granted_by=admin.id))
        db.add_all(
            [
                KanbanColumn(key=key, title=title, is_system=True, category=category,
                             workflow_order=order, view_order=position)
                for key, title, category, order, position in (
                    ("backlog", "Backlog", "todo", 0, 0),
                    ("todo", "A fazer", "todo", 100, 1),
                    ("production", "Em produção", "in_progress", 200, 2),
                    ("review", "Em revisão", "in_progress", 300, 3),
                    ("done", "Concluído", "done", 1000, 4),
                )
            ]
        )
        db.flush()
        db.info.update(board_id=1, user_role="admin")

        created = create_board(BoardInput(name="Demandas terceirizadas", user_ids=[supplier.id]), admin, db)
        assert [member["id"] for member in created["members"]] == [supplier.id]
        new_board_columns = list(db.scalars(select(KanbanColumn).order_by(KanbanColumn.workflow_order)))
        assert len(new_board_columns) == 5
        assert all(column.board_id == created["id"] for column in new_board_columns)

        db.info["board_id"] = 1
        principal_columns = list(db.scalars(select(KanbanColumn)))
        assert len(principal_columns) == 5
        assert all(column.board_id == 1 for column in principal_columns)


def test_orm_board_scope_changes_with_selected_board_and_rejects_cross_board_writes():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="internal"))
        db.flush()
        actor = User(id=1, username="user", role="internal", password_hash="test", grants=[])
        db.add(actor)
        db.flush()
        db.add_all([
            Board(id=1, name="Interno", author_id=actor.id),
            Board(id=2, name="Terceirizado", author_id=actor.id),
        ])
        db.flush()
        from app.models import Task
        db.add_all([
            Task(id=1, board_id=1, title="Card interno", creator_id=actor.id),
            Task(id=2, board_id=2, title="Card externo", creator_id=actor.id),
        ])
        db.commit()

        db.info["board_id"] = 1
        assert [task.id for task in db.scalars(select(Task))] == [1]
        db.info["board_id"] = 2
        assert [task.id for task in db.scalars(select(Task))] == [2]
        db.add(Task(id=3, board_id=1, title="Gravação cruzada", creator_id=actor.id))
        try:
            db.flush()
        except ValueError as error:
            assert "outro quadro" in str(error)
        else:
            raise AssertionError("cross-board write must be rejected")
