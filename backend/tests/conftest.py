import pytest
import app.main as main_module
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base, get_db
from app.main import app
from app.models import Role, Permission, User, Supplier, Rate, KanbanColumn, Dashboard, Board, BoardMember
from app.security import PERMISSIONS

@pytest.fixture
def clients(tmp_path, monkeypatch):
    # Retain Argon2 verification while making multi-user HTTP tests fast.
    test_hasher = PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)
    monkeypatch.setattr(main_module, "hasher", test_hasher)
    test_db = tmp_path / "integration.db"
    engine = create_engine(f"sqlite:///{test_db}", connect_args={"check_same_thread": False})
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as db:
        db.add_all([Role(id=r) for r in ["admin", "manager", "internal", "supplier"]])
        db.add_all([Permission(id=p) for p in PERMISSIONS])
        db.flush()
        hashed = test_hasher.hash("TestPassword!2026")
        db.add_all(
            [
                User(
                    id=1,
                    username="admin",
                    role="admin",
                    grants=[],
                    password_hash=hashed,
                ),
                User(
                    id=2,
                    username="manager",
                    role="manager",
                    grants=[
                        "approve_hours",
                        "view_financial",
                        "manage_sprints",
                        "reopen_sprints",
                        "create_tasks",
                        "export_data",
                        "export_financial",
                    ],
                    password_hash=hashed,
                ),
                User(
                    id=3,
                    username="no_grant",
                    role="manager",
                    grants=[],
                    password_hash=hashed,
                ),
                User(
                    id=4,
                    username="supplier",
                    role="supplier",
                    grants=[],
                    password_hash=hashed,
                ),
                User(
                    id=5,
                    username="other",
                    role="supplier",
                    grants=[],
                    password_hash=hashed,
                ),
            ]
        )
        db.flush()
        db.add(Board(id=1, name="Quadro principal", description="Quadro de teste", author_id=1))
        db.flush()
        db.add_all([BoardMember(board_id=1, user_id=user_id, granted_by=1) for user_id in range(1, 6)])
        db.add_all(
            [
                Supplier(id=1, name="Fornecedor exemplo", function="Dev", user_id=4),
                Supplier(id=2, name="Outro fornecedor", function="Design", user_id=5),
            ]
        )
        db.flush()
        db.add_all(
            [
                Rate(supplier_id=1, cents=12000, author_id=1),
                Rate(supplier_id=2, cents=15000, author_id=1),
            ]
        )
        db.add_all(
            [
                KanbanColumn(key="backlog", title="Backlog", is_system=True, category="todo", workflow_order=0, view_order=0),
                KanbanColumn(key="todo", title="A fazer", is_system=True, category="todo", workflow_order=100, view_order=1),
                KanbanColumn(key="production", title="Em produção", is_system=True, category="in_progress", workflow_order=200, view_order=2),
                KanbanColumn(key="review", title="Em revisão", is_system=True, category="in_progress", workflow_order=300, view_order=3),
                KanbanColumn(key="done", title="Concluído", is_system=True, category="done", workflow_order=1000, view_order=4),
            ]
        )
        db.add_all(
            [
                Dashboard(user_id=user_id, name="Visão geral", is_default=True)
                for user_id in (1, 2, 3)
            ]
        )

    def override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    result = {}
    for name in ["admin", "manager", "no_grant", "supplier", "other"]:
        client = TestClient(app)
        response = client.post(
            "/api/v1/auth/login",
            json={"username": name, "password": "TestPassword!2026"},
        )
        assert response.status_code == 200, response.text
        client.headers["X-CSRF-Token"] = response.json()["csrf"]
        result[name] = client
    yield result
    for client in result.values():
        client.close()
    app.dependency_overrides.clear()
    engine.dispose()
