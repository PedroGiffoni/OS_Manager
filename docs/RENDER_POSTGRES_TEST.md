# PostgreSQL no Render para testes

O backend de demonstração usa PostgreSQL gerenciado no Render, separado do SQLite local. O SQLite permanece como padrão de desenvolvimento. `DATABASE_URL` no Render deve usar a URL **interna** do banco, pois API e Postgres estão ambos em Ohio. A variável é configurada como segredo no serviço; não grave credenciais no Git, em Blueprint ou em logs.

## Banco deste teste

- Nome: `os-manager-test-db`
- Plano: Free, PostgreSQL 16, 1 GB
- Região: Ohio
- Criação: 06/11/2026
- Expiração informada pelo Render: 06/12/2026

O Render Free apaga o banco após 30 dias; ele não inclui backups nem pool gerenciado. A hospedagem é somente para dados fictícios e testes. Exporte os dados antes da expiração se quiser guardá-los.

## Desenvolvimento local

O `DATABASE_URL` local continua como `sqlite:///./data/os_manager.db`. Migrações são executadas no início pela aplicação e o driver psycopg 3 permite conectar ao PostgreSQL quando `DATABASE_URL` usa `postgres://`, `postgresql://` ou `postgresql+psycopg://`.

## Seed do ambiente online

O banco de testes online é inicializado por Alembic e recebe os dados de demonstração fictícios quando `OS_MANAGER_ALLOW_DEMO_SEED=true`. O seed é idempotente: só cria contas, fornecedores e demandas quando ainda não há usuários. Ele não copia o arquivo SQLite local nem sessões. A senha privada das contas permanece no segredo `OS_MANAGER_DEMO_PASSWORD` do Render.

Para uma futura migração de dados institucionais, não use esse seed ou um XLSX/PDF como ETL. Siga o procedimento de [DATABASE_MIGRATION.md](DATABASE_MIGRATION.md), incluindo cópia consistente do SQLite, conferência de FKs, valores, BLOBs, auditoria e rollback.
