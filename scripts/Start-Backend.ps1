$ErrorActionPreference='Stop'
if (-not $env:DATABASE_URL) { $env:DATABASE_URL='postgresql+psycopg://os_manager:os_manager@localhost:5432/os_manager' }
Set-Location (Join-Path (Split-Path $PSScriptRoot) 'backend')
& ../.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log --log-level info
