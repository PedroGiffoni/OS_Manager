param([switch]$Demo)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot
Set-Location $projectRoot
if (!(Test-Path '.venv/Scripts/python.exe')) { python -m venv .venv; if ($LASTEXITCODE) { throw 'Falha ao criar venv' } }
& .venv/Scripts/python.exe -m pip install -r backend/requirements.lock.txt
if ($LASTEXITCODE) { throw 'Falha ao instalar backend' }
Push-Location backend
try {
    & ../.venv/Scripts/python.exe -m alembic upgrade head
    if ($LASTEXITCODE) { throw 'Falha na migração' }
    if ($Demo) { try { $env:OS_MANAGER_ALLOW_DEMO_SEED='true'; & ../.venv/Scripts/python.exe -m app.seed; if ($LASTEXITCODE) { throw 'Falha no seed' } } finally { Remove-Item Env:OS_MANAGER_ALLOW_DEMO_SEED -ErrorAction SilentlyContinue } }
} finally { Pop-Location }
Push-Location frontend
try { npm.cmd ci; if ($LASTEXITCODE) { throw 'Falha ao instalar frontend' } } finally { Pop-Location }
Write-Host 'Pronto. Execute Start-Backend.ps1 e Start-Frontend.ps1 em dois terminais.'