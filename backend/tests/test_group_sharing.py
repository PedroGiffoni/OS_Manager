from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from pydantic import ValidationError
import pytest

from app.db import Base
from app.main import shared_with_user
from app.models import Role, User, UserGroup, UserGroupMembership
from app.schemas import DashboardWidgetInput, SavedViewInput


def test_group_sharing_respects_membership_active_state_and_supplier_boundary():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Role(id=value) for value in ("admin", "manager", "internal", "supplier")])
        db.flush()
        admin = User(id=1, username="admin", role="admin", password_hash="x", grants=[])
        member = User(id=2, username="member", role="internal", password_hash="x", grants=[])
        outsider = User(id=3, username="outsider", role="manager", password_hash="x", grants=[])
        supplier = User(id=4, username="supplier", role="supplier", password_hash="x", grants=[])
        db.add_all([admin, member, outsider, supplier])
        db.flush()
        group = UserGroup(id=1, name="Produto", description="", active=True, author_id=admin.id)
        db.add(group)
        db.flush()
        db.add(UserGroupMembership(group_id=group.id, user_id=member.id, author_id=admin.id))
        db.flush()
        view = type(
            "SharedView",
            (),
            {"shared": True, "shared_roles": [], "shared_group_ids": [group.id]},
        )()

        assert shared_with_user(view, member, db)
        assert not shared_with_user(view, outsider, db)
        assert not shared_with_user(view, supplier, db)
        group.active = False
        db.flush()
        assert not shared_with_user(view, member, db)

    engine.dispose()


def test_shared_views_and_widgets_require_valid_audience_targets():
    view = SavedViewInput(
        name="Equipe",
        shared=True,
        shared_group_ids=[4],
    )
    widget = DashboardWidgetInput(
        name="Cards da equipe",
        group_by="status",
        shared=True,
        shared_group_ids=[4],
    )
    assert view.shared_group_ids == [4]
    assert widget.shared_group_ids == [4]
    with pytest.raises(ValidationError):
        SavedViewInput(name="Grupo repetido", shared=True, shared_group_ids=[4, 4])
    with pytest.raises(ValidationError):
        DashboardWidgetInput(name="Sem destino", group_by="status", shared=True)
