import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.main import create_task_link
from app.models import Role, Task, TaskDependency, User
from app.schemas import TaskLinkInput
from app.services import blocking_path_exists


def test_blocking_dependency_graph_detects_cycles_but_ignores_other_link_types():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            db.add(Role(id="internal"))
            db.flush()
            user = User(
                username="planner",
                role="internal",
                grants=["manage_planning"],
                password_hash="test",
            )
            db.add(user)
            db.flush()
            tasks = [
                Task(title=f"Tarefa {index}", creator_id=user.id)
                for index in range(1, 5)
            ]
            db.add_all(tasks)
            db.flush()
            db.add_all(
                [
                    TaskDependency(
                        source_task_id=tasks[0].id,
                        target_task_id=tasks[1].id,
                        link_type="blocks",
                        author_id=user.id,
                    ),
                    TaskDependency(
                        source_task_id=tasks[1].id,
                        target_task_id=tasks[2].id,
                        link_type="blocks",
                        author_id=user.id,
                    ),
                    TaskDependency(
                        source_task_id=tasks[2].id,
                        target_task_id=tasks[3].id,
                        link_type="relates",
                        author_id=user.id,
                    ),
                ]
            )
            db.flush()

            assert blocking_path_exists(db, tasks[0].id, tasks[2].id)
            assert not blocking_path_exists(db, tasks[0].id, tasks[3].id)
            assert not blocking_path_exists(db, tasks[2].id, tasks[0].id)

            with pytest.raises(HTTPException) as cycle:
                create_task_link(
                    tasks[1].id,
                    TaskLinkInput(target_task_id=tasks[0].id, link_type="blocks"),
                    user,
                    db,
                )
            assert cycle.value.status_code == 409
            assert cycle.value.detail["code"] == "DEPENDENCY_CYCLE"

            related = create_task_link(
                tasks[1].id,
                TaskLinkInput(target_task_id=tasks[0].id, link_type="relates"),
                user,
                db,
            )
            assert related["link_type"] == "relates"
    finally:
        engine.dispose()
