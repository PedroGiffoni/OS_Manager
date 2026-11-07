from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.automation import matches
from app.db import Base
from app.models import (
    Component,
    Release,
    Role,
    Task,
    TaskComponent,
    TaskDependency,
    TaskRelease,
    User,
)
from app.schemas import AutomationRuleInput, WorkflowCondition
from app.workflows import conditions_match


def test_workflows_and_automations_match_release_component_and_open_blockers():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="admin"))
        db.flush()
        author = User(username="rule-author", role="admin", grants=[], password_hash="hash")
        db.add(author)
        db.flush()
        release = Release(name="V1", author_id=author.id)
        component = Component(name="API", author_id=author.id)
        prerequisite = Task(title="Pré-requisito", creator_id=author.id, status="production")
        linked = Task(title="Card associado", creator_id=author.id)
        blocked = Task(title="Card bloqueado", creator_id=author.id)
        db.add_all([release, component, prerequisite, linked, blocked])
        db.flush()
        db.add_all([
            TaskRelease(task_id=linked.id, release_id=release.id, author_id=author.id),
            TaskComponent(task_id=linked.id, component_id=component.id, author_id=author.id),
            TaskDependency(
                source_task_id=prerequisite.id,
                target_task_id=blocked.id,
                link_type="blocks",
                author_id=author.id,
            ),
        ])
        db.flush()

        linked_conditions = [
            {"field": "release_assigned", "operator": "eq", "value": True},
            {"field": "component_assigned", "operator": "eq", "value": True},
        ]
        blocked_condition = [{"field": "blocked", "operator": "eq", "value": True}]
        assert conditions_match(linked_conditions, linked, db)
        assert conditions_match(blocked_condition, blocked, db)
        assert not conditions_match(blocked_condition, linked, db)

        rule = SimpleNamespace(conditions={"blocked": True})
        assert matches(rule, blocked, db)
        assert not matches(rule, linked, db)

        prerequisite.status = "done"
        db.flush()
        assert not conditions_match(blocked_condition, blocked, db)
        assert not matches(rule, blocked, db)
    engine.dispose()


def test_new_link_conditions_reject_non_boolean_values():
    for field in ("release_assigned", "component_assigned", "blocked"):
        assert WorkflowCondition(field=field, operator="eq", value=False).value is False
        try:
            WorkflowCondition(field=field, operator="eq", value="false")
        except ValueError:
            pass
        else:
            raise AssertionError(f"{field} aceitou valor não booleano")

    try:
        AutomationRuleInput(
            name="Regra inválida",
            trigger="status_changed",
            conditions={"blocked": 1},
            action="add_comment",
            config={"body": "Revisar"},
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Automação aceitou condição blocked não booleana")
