"""Run Playwright against a dedicated disposable PostgreSQL test database."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.parse import urlsplit
from sqlalchemy import create_engine

root = Path(__file__).resolve().parents[1]
database_url = os.getenv(
    "E2E_DATABASE_URL",
    "postgresql+psycopg://os_manager:os_manager@localhost:5432/os_manager_e2e",
)
parsed_database = urlsplit(database_url)
if not parsed_database.scheme.startswith("postgresql") or parsed_database.path.strip("/") not in {"os_manager_e2e", "os_manager_test"}:
    raise SystemExit("E2E_DATABASE_URL deve apontar para um banco PostgreSQL dedicado chamado os_manager_e2e ou os_manager_test.")
env = {**os.environ, "DATABASE_URL": database_url, "OS_MANAGER_ALLOW_DEMO_SEED": "true", "TRUSTED_ORIGINS": "http://127.0.0.1:5174", "VITE_API_TARGET": "http://127.0.0.1:8001"}
# Only the named E2E database is reset; development and hosted databases are not touched.
engine = create_engine(database_url)
with engine.begin() as connection:
    connection.exec_driver_sql("DROP SCHEMA public CASCADE")
    connection.exec_driver_sql("CREATE SCHEMA public")
engine.dispose()
for arguments in [["-m", "alembic", "upgrade", "head"], ["-m", "app.seed"]]:
    subprocess.run([sys.executable, *arguments], cwd=root/"backend", env=env, check=True)
executable = sys._base_executable if os.name == "nt" else sys.executable
if os.name == "nt":
    env["PYTHONPATH"] = str(Path(sys.prefix)/"Lib"/"site-packages") + os.pathsep + str(root/"backend")
with open(Path(tempfile.gettempdir())/"os-manager-e2e-server.log", "w", encoding="utf-8") as log:
    server = subprocess.Popen([executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001"], cwd=root/"backend", env=env, stdout=log, stderr=log)
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen("http://127.0.0.1:8001/api/v1/health", timeout=1)
                break
            except OSError:
                if server.poll() is not None:
                    raise RuntimeError("Backend E2E não iniciou; consulte o teste de migração.")
                time.sleep(.2)
        command = ["cmd.exe", "/d", "/c", "npm.cmd", "run", "test:e2e", "--", *sys.argv[1:]] if os.name == "nt" else ["npm", "run", "test:e2e", "--", *sys.argv[1:]]
        result = subprocess.run(command, cwd=root/"frontend", env=env, timeout=240)
    finally:
        server.terminate()
        server.wait(timeout=15)
raise SystemExit(result.returncode)
