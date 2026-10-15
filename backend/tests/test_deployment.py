import importlib.util
from pathlib import Path
import pytest
from app.start import validate_environment


def cloud(**changes):
    return {
        "CLOUD_DEPLOYMENT": "true",
        "COOKIE_SECURE": "true",
        "TRUSTED_ORIGINS": "https://os-manager.vercel.app",
        **changes,
    }


def test_runtime_port_and_explicit_seed():
    assert validate_environment({}) == (8000, False)
    assert validate_environment(cloud(PORT="10000")) == (10000, False)
    assert validate_environment(
        cloud(
            OS_MANAGER_ALLOW_DEMO_SEED="true", OS_MANAGER_DEMO_PASSWORD="PrivateTestPassword!2026"
        )
    ) == (8000, True)


@pytest.mark.parametrize(
    "changes",
    [
        {"PORT": "0"},
        {"PORT": "not-a-port"},
        {"COOKIE_SECURE": "false"},
        {"TRUSTED_ORIGINS": ""},
        {"TRUSTED_ORIGINS": "http://app.example.com"},
        {"TRUSTED_ORIGINS": "https://*.vercel.app"},
        {"TRUSTED_ORIGINS": "https://app.example.com/"},
        {"OS_MANAGER_ALLOW_DEMO_SEED": "true"},
        {"OS_MANAGER_ALLOW_DEMO_SEED": "true", "OS_MANAGER_DEMO_PASSWORD": "DemoLocal!2026"},
    ],
)
def test_public_runtime_rejects_unsafe_configuration(changes):
    with pytest.raises(ValueError):
        validate_environment(cloud(**changes))


def load_configurator():
    path = Path(__file__).resolve().parents[2] / "scripts" / "configure_vercel.py"
    spec = importlib.util.spec_from_file_location("configure_vercel", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.configuration


def test_vercel_proxy_preserves_api_path_and_avoids_personalized_cache():
    config = load_configurator()("https://backend.example.com/")
    assert config["rewrites"][0] == {
        "source": "/api/:path*",
        "destination": "https://backend.example.com/api/:path*",
    }
    assert "no-store" in str(config["headers"])
    assert "api" in config["rewrites"][1]["source"]


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://localhost",
        "https://example.com/api",
        "https://name:secret@example.com",
        "https://example.com?q=x",
    ],
)
def test_vercel_proxy_rejects_invalid_origins(url):
    with pytest.raises(ValueError):
        load_configurator()(url)


def test_https_session_through_frontend_origin(clients, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setenv("COOKIE_SECURE", "true")
    monkeypatch.setenv("TRUSTED_ORIGINS", "https://os-manager.vercel.app")
    with TestClient(app, base_url="https://os-manager.vercel.app") as client:
        client.headers["Origin"] = "https://os-manager.vercel.app"
        response = client.post(
            "/api/v1/auth/login", json={"username": "supplier", "password": "TestPassword!2026"}
        )
        assert response.status_code == 200
        cookie = response.headers["set-cookie"].lower()
        assert "secure" in cookie and "httponly" in cookie and "samesite=strict" in cookie
        assert "domain=" not in cookie
        assert client.get("/api/v1/auth/me").status_code == 200
        assert client.get("/api/v1/auth/me").headers["cache-control"] == "no-store"
        client.headers["X-CSRF-Token"] = response.json()["csrf"]
        client.headers["Origin"] = "https://attacker.example.com"
        assert client.post("/api/v1/auth/logout").status_code == 403
        client.headers["Origin"] = "https://os-manager.vercel.app"
        assert client.post("/api/v1/auth/logout").status_code == 200
        assert client.get("/api/v1/auth/me").status_code == 401


def test_private_cloud_seed_is_idempotent_and_does_not_log_password(tmp_path):
    import os
    import subprocess
    import sys
    import sqlite3

    password = "PrivateTestingOnly!2026"
    database = tmp_path / "cloud-seed.db"
    env = {
        **os.environ,
        **cloud(OS_MANAGER_ALLOW_DEMO_SEED="true", OS_MANAGER_DEMO_PASSWORD=password),
        "DATABASE_URL": "sqlite:///" + str(database),
    }
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=env,
        check=True,
        capture_output=True,
    )
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, "-m", "app.seed"], env=env, check=True, capture_output=True, text=True
        )
        assert password not in result.stdout + result.stderr
    with sqlite3.connect(database) as conn:
        assert conn.execute("select count(*) from users").fetchone()[0] == 6
        stored = conn.execute("select password_hash from users where username='admin'").fetchone()[
            0
        ]
    from app.security import hasher

    assert hasher.verify(stored, password)
