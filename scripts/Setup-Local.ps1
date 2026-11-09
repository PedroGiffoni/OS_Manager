param([switch]$Demo)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot
Set-Location $projectRoot
if (-not $env:DATABASE_URL) { $env:DATABASE_URL='postgresql+psycopg://os_manager:os_manager@localhost:5432/os_manager' }
if ($env:DATABASE_URL -match '@(localhost|127\.0\.0\.1):5432/') {
    docker compose up -d postgres
    if ($LASTEXITCODE) { throw 'Não foi possível iniciar o PostgreSQL local. Inicie o Docker Desktop e tente novamente.' }
    $postgresReady=$false
    for ($attempt=0; $attempt -lt 30; $attempt++) {
        docker compose exec -T postgres pg_isready -U os_manager -d os_manager *> $null
        if ($LASTEXITCODE -eq 0) { $postgresReady=$true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $postgresReady) { throw 'O PostgreSQL local não ficou pronto em 60 segundos.' }
}
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
