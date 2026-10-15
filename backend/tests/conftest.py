import os
import subprocess
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import get_db
from app.main import app
from app.models import Role, Permission, User, Supplier, Rate
from app.security import hasher, PERMISSIONS


@pytest.fixture
def clients(tmp_path):
    url = "sqlite:///" + str(tmp_path / "integration.db")
    env = {**os.environ, "DATABASE_URL": url}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
        env=env,
        capture_output=True,
    )
    engine = create_engine(url, connect_args={"check_same_thread": False})
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as db:
        db.add_all([Role(id=r) for r in ["admin", "manager", "internal", "supplier"]])
        db.add_all([Permission(id=p) for p in PERMISSIONS])
        db.flush()
        hashed = hasher.hash("TestPassword!2026")
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
