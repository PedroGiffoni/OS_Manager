"""Single-process entrypoint for local containers and disposable cloud tests."""

import os
import subprocess
import sys
from urllib.parse import urlsplit


def validate_environment(env):
    try:
        port = int(env.get("PORT", "8000"))
    except ValueError as exc:
        raise ValueError("PORT deve ser um inteiro.") from exc
    if not 1 <= port <= 65535:
        raise ValueError("PORT fora do intervalo permitido.")
    cloud = env.get("CLOUD_DEPLOYMENT") == "true"
    seed = env.get("OS_MANAGER_ALLOW_DEMO_SEED") == "true"
    if cloud:
        if env.get("COOKIE_SECURE") != "true":
            raise ValueError("Publicação exige COOKIE_SECURE=true.")
        origins = env.get("TRUSTED_ORIGINS", "").split(",")
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
                or "*" in origin
                or origin != origin.strip()
            ):
                raise ValueError("TRUSTED_ORIGINS exige origens HTTPS exatas, sem barra final.")
        if seed:
            password = env.get("OS_MANAGER_DEMO_PASSWORD", "")
            if len(password) < 16 or password == "DemoLocal!2026":
                raise ValueError("Seed público exige senha privada com pelo menos 16 caracteres.")
    return port, seed


def main():
    port, seed = validate_environment(os.environ)
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    if seed:
        subprocess.run([sys.executable, "-m", "app.seed"], check=True)
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
            "--workers",
            "1",
            "--no-access-log",
        ],
    )


if __name__ == "__main__":
    main()
