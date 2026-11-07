import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.dashboard_widgets import filtered_widget_query
from app.db import Base
from app.models import Role, Supplier, Task, User
from app.schemas import DashboardWidgetInput


def test_widget_query_refines_the_existing_authorized_task_scope():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Role(id="supplier"))
        db.flush()
        actor = User(username="supplier-user", role="supplier", grants=[], password_hash="hash")
        db.add(actor)
        db.flush()
        first = Supplier(name="Um", function="Dev")
        second = Supplier(name="Dois", function="QA")
        db.add_all([first, second])
        db.flush()
        allowed = Task(title="Permitido", creator_id=actor.id, supplier_id=first.id, priority=3)
        low_priority = Task(title="Fora do filtro", creator_id=actor.id, supplier_id=first.id, priority=1)
        outside_scope = Task(title="Fora do escopo", creator_id=actor.id, supplier_id=second.id, priority=5)
        db.add_all([allowed, low_priority, outside_scope])
        db.flush()

        scoped = select(Task).where(Task.supplier_id == first.id)
        filtered = filtered_widget_query(scoped, "priority >= 2", "supplier")

        assert db.scalars(filtered).all() == [allowed]
    engine.dispose()


def test_widget_query_keeps_configuration_history_admin_only():
    with pytest.raises(HTTPException) as error:
        filtered_widget_query(select(Task), 'field_config_area_label CHANGED TO "Área"', "manager")
    assert error.value.status_code == 403
    admin_query = filtered_widget_query(
        select(Task), 'field_config_area_label CHANGED TO "Área"', "admin"
    )
    assert admin_query is not None


def test_shared_widget_refuses_filters_that_could_leak_custom_values():
    with pytest.raises(ValueError, match="personalizados"):
        DashboardWidgetInput(
            name="Filtro privado",
            group_by="status",
            jql='field_area = "Interno"',
            shared=True,
            shared_roles=["internal"],
        )
    with pytest.raises(ValueError, match="personalizados"):
        DashboardWidgetInput(
            name="Busca geral",
            group_by="status",
            jql='text ~ "confidencial"',
            shared=True,
            shared_roles=["internal"],
        )
    private_widget = DashboardWidgetInput(
        name="Pessoal", group_by="status", jql='text ~ "termo"'
    )
    assert private_widget.jql == 'text ~ "termo"'
