"""Run Playwright against a disposable SQLite database, without touching development data."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="os-manager-e2e-") as temp:
    env = {**os.environ, "DATABASE_URL": "sqlite:///" + str(Path(temp) / "e2e.db"), "OS_MANAGER_ALLOW_DEMO_SEED": "true", "TRUSTED_ORIGINS": "http://127.0.0.1:5174", "VITE_API_TARGET": "http://127.0.0.1:8001"}
    for arguments in [["-m", "alembic", "upgrade", "head"], ["-m", "app.seed"]]:
        subprocess.run([sys.executable, *arguments], cwd=root/"backend", env=env, check=True)
    executable = sys._base_executable if os.name == "nt" else sys.executable
    if os.name == "nt":
        env["PYTHONPATH"] = str(Path(sys.prefix)/"Lib"/"site-packages") + os.pathsep + str(root/"backend")
    with open(Path(temp)/"server.log", "w", encoding="utf-8") as log:
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
            command = ["cmd.exe", "/d", "/c", "npm.cmd", "run", "test:e2e"] if os.name == "nt" else ["npm", "run", "test:e2e"]
            result = subprocess.run(command, cwd=root/"frontend", env=env, timeout=240)
        finally:
            server.terminate()
            server.wait(timeout=15)
    raise SystemExit(result.returncode)