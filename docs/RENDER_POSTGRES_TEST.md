# PostgreSQL no Render para testes

O backend de demonstração e o desenvolvimento local usam PostgreSQL. `DATABASE_URL` no Render deve usar a URL **interna** do banco, pois API e Postgres estão ambos em Ohio. A variável é configurada como segredo no serviço; não grave credenciais no Git, em Blueprint ou em logs.

## Banco deste teste

- Nome: `os-manager-test-db`
- Plano: Free, PostgreSQL 16, 1 GB
- Região: Ohio
- Criação: 06/11/2026
- Expiração informada pelo Render: 06/12/2026

O Render Free apaga o banco após 30 dias; ele não inclui backups nem pool gerenciado. A hospedagem é somente para dados fictícios e testes. Exporte os dados antes da expiração se quiser guardá-los.

## Desenvolvimento local

O desenvolvimento local também usa PostgreSQL, iniciado pelo Docker Compose e persistido em `postgres-data`. O valor local padrão de `DATABASE_URL` é `postgresql+psycopg://os_manager:os_manager@localhost:5432/os_manager`; a API dentro do Compose usa `postgresql+psycopg://os_manager:os_manager@postgres:5432/os_manager`. A aplicação usa migrações Alembic tanto localmente quanto no Render.

## Seed do ambiente online

O banco de testes online é inicializado por Alembic e recebe os dados de demonstração fictícios quando `OS_MANAGER_ALLOW_DEMO_SEED=true`. O seed é idempotente: só cria contas, fornecedores e demandas quando ainda não há usuários. Ele não copia dados locais nem sessões. A senha privada das contas permanece no segredo `OS_MANAGER_DEMO_PASSWORD` do Render.

O arquivo SQLite legado não é usado em nenhum ambiente da aplicação e não é importado. Se houver necessidade futura de recuperar dados que estavam nele, não use o seed nem XLSX/PDF como ETL. Siga o procedimento de [DATABASE_MIGRATION.md](DATABASE_MIGRATION.md), incluindo backup, conferência de FKs, valores, BLOBs e auditoria.
