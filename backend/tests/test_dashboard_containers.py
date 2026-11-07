import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.main import (
    accessible_dashboard,
    create_dashboard,
    create_dashboard_widget,
    default_dashboard,
    delete_dashboard,
    list_dashboard_widgets,
    list_dashboards,
    dashboard_widget_data,
    rename_dashboard,
)
from app.models import Dashboard, DashboardWidget, Role, User, UserGroup, UserGroupMembership
from app.schemas import DashboardInput, DashboardWidgetInput


def test_independent_dashboards_and_shared_widget_visibility_are_scoped():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Role(id="admin"), Role(id="internal"), Role(id="supplier")])
        db.flush()
        owner = User(username="dashboard-owner", password_hash="hash", role="admin", grants=[])
        member = User(username="dashboard-member", password_hash="hash", role="internal", grants=[])
        stranger = User(username="dashboard-stranger", password_hash="hash", role="internal", grants=[])
        supplier = User(username="dashboard-supplier", password_hash="hash", role="supplier", grants=[])
        db.add_all([owner, member, stranger, supplier])
        db.flush()

        owner_default = default_dashboard(db, owner)
        second = create_dashboard(DashboardInput(name="Entregas"), user=owner, db=db)
        assert second["name"] == "Entregas"
        second_row = db.get(Dashboard, second["id"])
        renamed = rename_dashboard(
            second_row.id, DashboardInput(name="Entregas do trimestre"), user=owner, db=db
        )
        assert renamed["name"] == "Entregas do trimestre"
        group = UserGroup(name="Leitores", description="", active=True, author_id=owner.id)
        db.add(group)
        db.flush()
        db.add(UserGroupMembership(group_id=group.id, user_id=member.id, author_id=owner.id))
        db.add_all([
            DashboardWidget(
                user_id=owner.id,
                dashboard_id=owner_default.id,
                name="Privado",
                group_by="status",
                measure="count",
                chart="bar",
            ),
            DashboardWidget(
                user_id=owner.id,
                dashboard_id=second_row.id,
                name="Compartilhado",
                group_by="priority",
                measure="count",
                chart="bar",
                shared=True,
                shared_roles=[],
                shared_group_ids=[group.id],
            ),
        ])
        db.flush()

        visible_dashboards = list_dashboards(member, db)
        assert [item["id"] for item in visible_dashboards] == [
            default_dashboard(db, member).id,
            second_row.id,
        ]
        assert visible_dashboards[1]["read_only"] is True
        shared_widgets = list_dashboard_widgets(second_row.id, member, db)
        assert [item["name"] for item in shared_widgets] == ["Compartilhado"]
        with pytest.raises(HTTPException) as shared_write_denied:
            create_dashboard_widget(
                DashboardWidgetInput(
                    name="Invasão", group_by="status", dashboard_id=second_row.id
                ),
                user=member,
                db=db,
            )
        assert shared_write_denied.value.status_code == 403
        assert accessible_dashboard(db, stranger, second_row.id) is None
        with pytest.raises(HTTPException) as denied:
            list_dashboard_widgets(second_row.id, stranger, db)
        assert denied.value.status_code == 404
        assert list_dashboards(supplier, db) == []
        assert list_dashboard_widgets(None, supplier, db) == []
        with pytest.raises(HTTPException) as supplier_widget_denied:
            create_dashboard_widget(
                DashboardWidgetInput(name="Relatório", group_by="status"),
                user=supplier,
                db=db,
            )
        assert supplier_widget_denied.value.status_code == 403
        assert list_dashboard_widgets(second_row.id, supplier, db) == []
        with pytest.raises(HTTPException) as supplier_data_denied:
            dashboard_widget_data(999, user=supplier, db=db)
        assert supplier_data_denied.value.status_code == 403

        empty = create_dashboard(DashboardInput(name="Vazio"), user=owner, db=db)
        assert delete_dashboard(empty["id"], user=owner, db=db) == {"ok": True}
        with pytest.raises(HTTPException) as default_delete_denied:
            delete_dashboard(owner_default.id, user=owner, db=db)
        assert default_delete_denied.value.status_code == 409
        with pytest.raises(HTTPException) as nonempty:
            delete_dashboard(second_row.id, user=owner, db=db)
        assert nonempty.value.status_code == 409
    engine.dispose()
