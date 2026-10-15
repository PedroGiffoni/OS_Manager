"""Run browser tests against a disposable demo; password arrives through stdin, never argv."""

import argparse
import getpass
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--base-url", required=True)
args = parser.parse_args()
origin = args.base_url.rstrip("/")
parsed = urlsplit(origin)
if (
    parsed.scheme != "https"
    or not parsed.hostname
    or parsed.path
    or parsed.username
    or parsed.query
):
    parser.error("Use somente a origem HTTPS da demonstração descartável.")
print(
    "Aguardando credencial de teste pela entrada padrão; não será registrada.",
    flush=True,
)
try:
    if sys.stdin.isatty():
        password = getpass.getpass("Senha privada de teste: ")
    else:
        credentials = json.loads(sys.stdin.readline())
        password = credentials["password"]
except (ValueError, KeyError) as exc:
    raise SystemExit("Credencial ausente ou inválida.") from exc
if not isinstance(password, str) or len(password) < 16:
    raise SystemExit("Senha privada de teste inválida.")
env = {**os.environ, "E2E_BASE_URL": origin, "E2E_PASSWORD": password}
command = (
    ["cmd.exe", "/d", "/c", "npm.cmd", "run", "test:e2e"]
    if os.name == "nt"
    else ["npm", "run", "test:e2e"]
)
result = subprocess.run(
    command,
    check=False,
    cwd=Path(__file__).resolve().parents[1] / "frontend",
    env=env,
    timeout=420,
)
raise SystemExit(result.returncode)
