import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.main import create_saved_filter, delete_saved_filter, list_saved_filters, update_saved_filter
from app.models import Role, User, UserGroup, UserGroupMembership
from app.schemas import SavedFilterInput


def test_saved_filters_can_be_shared_by_role_or_group_without_sharing_results():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Role(id=role) for role in ("admin", "manager", "internal", "supplier")])
        db.flush()
        owner = User(username="filter-owner", password_hash="hash", role="admin", grants=[])
        teammate = User(username="filter-teammate", password_hash="hash", role="internal", grants=[])
        outsider = User(username="filter-outsider", password_hash="hash", role="manager", grants=[])
        supplier = User(username="filter-supplier", password_hash="hash", role="supplier", grants=[])
        db.add_all([owner, teammate, outsider, supplier])
        db.flush()
        group = UserGroup(name="Planejamento", author_id=owner.id)
        db.add(group)
        db.flush()
        db.add(UserGroupMembership(group_id=group.id, user_id=teammate.id, author_id=owner.id))
        db.commit()

        role_filter = create_saved_filter(
            SavedFilterInput(name="Atrasadas", query='resolution IS EMPTY AND due < "2026-11-07"', shared=True, shared_roles=["internal"]),
            user=owner,
            db=db,
        )
        group_filter = create_saved_filter(
            SavedFilterInput(name="Da equipe", query='priority >= 3', shared=True, shared_group_ids=[group.id]),
            user=owner,
            db=db,
        )
        private_filter = create_saved_filter(
            SavedFilterInput(name="Pessoal", query='assignee = currentUser()'), user=owner, db=db
        )
        supplier_filter = create_saved_filter(
            SavedFilterInput(name="Minhas atividades", query='assignee = currentUser()'),
            user=supplier,
            db=db,
        )

        assert {row["id"] for row in list_saved_filters(offset=0, limit=100, user=owner, db=db)} == {
            role_filter["id"], group_filter["id"], private_filter["id"]
        }
        teammate_filters = list_saved_filters(offset=0, limit=100, user=teammate, db=db)
        assert {row["id"] for row in teammate_filters} == {role_filter["id"], group_filter["id"]}
        assert list_saved_filters(offset=0, limit=100, user=outsider, db=db) == []
        assert [row["id"] for row in list_saved_filters(offset=0, limit=100, user=supplier, db=db)] == [supplier_filter["id"]]

        group.active = False
        db.flush()
        assert {row["id"] for row in list_saved_filters(offset=0, limit=100, user=teammate, db=db)} == {role_filter["id"]}

        updated = update_saved_filter(
            role_filter["id"],
            SavedFilterInput(name="Atrasadas", query='statusCategory = "To Do"', shared=True, shared_roles=["internal"]),
            user=owner,
            db=db,
        )
        assert updated["query"] == 'statusCategory = "To Do"'
        with pytest.raises(HTTPException) as denied_update:
            update_saved_filter(
                role_filter["id"],
                SavedFilterInput(name="Tomado", query="priority >= 2"),
                user=teammate,
                db=db,
            )
        assert denied_update.value.status_code == 404
        with pytest.raises(HTTPException) as denied_delete:
            delete_saved_filter(role_filter["id"], user=teammate, db=db)
        assert denied_delete.value.status_code == 404
        with pytest.raises(HTTPException) as manager_share_denied:
            create_saved_filter(
                SavedFilterInput(name="Sem permissão", query="priority >= 1", shared=True, shared_roles=["internal"]),
                user=outsider,
                db=db,
            )
        assert manager_share_denied.value.status_code == 403
        with pytest.raises(HTTPException) as invalid_query:
            create_saved_filter(SavedFilterInput(name="Consulta inválida", query="DROP TABLE tasks"), user=owner, db=db)
        assert invalid_query.value.status_code == 422
        with pytest.raises(HTTPException) as duplicate:
            create_saved_filter(SavedFilterInput(name="Pessoal", query="priority >= 1"), user=owner, db=db)
        assert duplicate.value.status_code == 409
    engine.dispose()


def test_shared_saved_filter_schema_rejects_private_data_queries_and_invalid_shares():
    with pytest.raises(ValueError, match="valores de campos personalizados"):
        SavedFilterInput(name="Campos", query="field_area WAS Operações", shared=True, shared_roles=["internal"])
    with pytest.raises(ValueError, match="texto amplo"):
        SavedFilterInput(name="Texto", query='text ~ "urgente"', shared=True, shared_roles=["manager"])
    with pytest.raises(ValueError, match="ao menos um papel"):
        SavedFilterInput(name="Sem destino", query="status = todo", shared=True)
    with pytest.raises(ValueError, match="repetidos"):
        SavedFilterInput(name="Grupos", query="status = todo", shared=True, shared_group_ids=[2, 2])
    with pytest.raises(ValueError, match="consulta para salvar"):
        SavedFilterInput(name="Vazio", query="   ")


def test_saved_filter_endpoints_are_registered_in_versioned_openapi():
    from app.main import app

    operations = app.openapi()["paths"]
    assert set(operations["/api/v1/saved-filters"]) == {"get", "post"}
    assert set(operations["/api/v1/saved-filters/{identity}"]) == {"put", "delete"}
