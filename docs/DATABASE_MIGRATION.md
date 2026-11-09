# Banco de dados da aplicação

## Decisão vigente

PostgreSQL é o único banco de dados operacional da aplicação em desenvolvimento local, Docker Compose e Render. O driver é psycopg 3; SQLAlchemy centraliza conexões/sessões e Alembic controla o esquema. `DATABASE_URL` no backend local usa por padrão `postgresql+psycopg://os_manager:os_manager@localhost:5432/os_manager`; no Compose usa o serviço interno `postgres`; no Render usa a URL interna de `os-manager-test-db`.

O Compose mantém o banco local no volume `postgres-data` e cria um banco separado `os_manager_e2e` para Playwright. O runner E2E verifica o nome dedicado antes de limpar o schema. Nunca configure o banco de desenvolvimento ou produção em `E2E_DATABASE_URL`.

## Dados legados SQLite

O arquivo `backend/data/os_manager.db` de versões anteriores não é mais aberto pela aplicação nem importado automaticamente. Ele permanece intocado como cópia local até que o responsável decida se ainda precisa desses dados. A demonstração Render usa seu próprio PostgreSQL e dados fictícios; ela não copia a base local.

Se for necessário recuperar dados desse arquivo, tratar como migração única e explícita: fazer backup consistente, levantar inventário e totais, transformar dados em carga idempotente para PostgreSQL, preservar IDs/UTC/valores em centavos/minutos/histórico, conferir chaves estrangeiras e comparar contagens. Não enviar o arquivo SQLite ao Render nem substituir o banco online sem cópia de segurança e janela de manutenção.

## Testes e operação

Algumas unidades de teste e testes de migração legados ainda usam SQLite em memória como fixture descartável; não é configurado como banco da aplicação. Playwright usa exclusivamente PostgreSQL no banco dedicado `os_manager_e2e`.

O PostgreSQL do Render Free é temporário e expira em **06/12/2026**, conforme o painel do provedor. Exporte dados fictícios antes dessa data se forem necessários. A instância gratuita não é recomendação de produção institucional. Antes da implantação definitiva, confirmar com TI topologia, backup/restore, retenção, TLS, credenciais, permissões, observabilidade, carga, disponibilidade e homologação.
