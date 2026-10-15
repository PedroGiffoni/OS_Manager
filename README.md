# OS Manager

Sistema web local em português para demandas, fornecedores, sprints, Kanban, configuração individual de cards, horas, aprovações e relatórios. Frontend React/TypeScript; API FastAPI; SQLAlchemy e Alembic; SQLite persistente. Nenhuma conta externa, banco servidor ou serviço pago é necessário para funcionar após instalar as dependências.

O projeto está isolado em `os-manager`, dentro da pasta aberta que contém a instalação do Pen. Os binários preexistentes foram preservados. SQLite atende ao desenvolvimento e aos testes; o SGBD institucional será definido pela TI e exige avaliação e homologação próprias.

## Início rápido no Windows

Requisitos: Python 3.12 ou superior, Node.js 22.12 ou superior e npm. A primeira instalação baixa pacotes gratuitos. Execute em PowerShell, a partir desta pasta:

```powershell
.\scripts\Setup-Local.ps1 -Demo
```

Se a política de execução impedir scripts, use os comandos manuais abaixo; não é necessário mudar a política global. Abra dois terminais:

```powershell
# Terminal 1, a partir de os-manager
.\scripts\Start-Backend.ps1
# Terminal 2, a partir de os-manager
.\scripts\Start-Frontend.ps1
```

Frontend: http://127.0.0.1:5173 · OpenAPI: http://127.0.0.1:8000/api/docs · Health: http://127.0.0.1:8000/api/v1/health

Instalação manual, também adaptável a Linux/macOS usando `.venv/bin/python`:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.lock.txt
cd backend
../.venv/Scripts/python.exe -m alembic upgrade head
$env:OS_MANAGER_ALLOW_DEMO_SEED='true'
../.venv/Scripts/python.exe -m app.seed
Remove-Item Env:OS_MANAGER_ALLOW_DEMO_SEED
# Para iniciar a API neste terminal:
../.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Em outro terminal, a partir da raiz:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

O padrão `DATABASE_URL=sqlite:///./data/os_manager.db` é relativo ao diretório de execução do backend. Com os comandos acima, o arquivo fica em `backend/data/os_manager.db`, ignorado pelo Git. O diretório é criado automaticamente. Para outro local, defina `DATABASE_URL` antes de executar migrações e servidor. `.env.example` documenta as variáveis; as variáveis devem ser exportadas no ambiente, não há leitura implícita de `.env` pelo Python.

## Contas fictícias

Senha de todas as contas locais do seed: `DemoLocal!2026`. O seed exige `OS_MANAGER_ALLOW_DEMO_SEED=true` e recusa alterar um banco que já contenha usuários. O servidor local Uvicorn não executa seed; o entrypoint de contêiner permite seed opcional explícito para testes. Na nuvem, exige senha privada e configuração HTTPS conforme DEPLOYMENT.md.

| Conta | Perfil e permissões |
| --- | --- |
| admin | Administrador com todas as permissões |
| gestor | Criar/configurar tarefas, gerenciar/reabrir sprints, fornecedores/tarifas, aprovar horas, ver/exportar finanças |
| gestor_sem_aprovacao | Gestor com criação de tarefas, sprints e exportação operacional; sem aprovação e sem finanças |
| interno | Criar tarefas, configurar cards, gerenciar sprints e exportar dados operacionais |
| fornecedor | Ana Exemplo; somente suas tarefas, seus apontamentos e exportação operacional do próprio escopo |
| fornecedor2 | Bruno Exemplo; mesmo isolamento, sem acesso às tarefas de Ana |

Tarifas e demandas do seed são inteiramente fictícias. Não use essas contas em um ambiente institucional.

## Testes e verificações

```powershell
cd backend
../.venv/Scripts/python.exe -m pytest -q
../.venv/Scripts/python.exe -m ruff check app tests
cd ../frontend
npm.cmd run test
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
npm.cmd audit
cd ..
.venv/Scripts/python.exe -m pip_audit --local
```

Para Playwright, instale o navegador uma vez e use o runner isolado:

```powershell
cd frontend
npx.cmd playwright install chromium
cd ..
.venv/Scripts/python.exe scripts/run_e2e.py
```

O runner cria SQLite temporário, aplica migrações, executa seed e inicia a API em 8001 e Vite em 5174. Não toca no banco de desenvolvimento. Resultados efetivamente executados e bloqueios estão em `docs/VALIDATION.md`.

## Docker opcional

Com Docker Desktop Linux em execução:

```powershell
docker compose up --build
# Em outro terminal, apenas em demonstração:
docker compose exec -e OS_MANAGER_ALLOW_DEMO_SEED=true backend python -m app.seed
```

Acesse http://localhost:8080. O volume nomeado `sqlite-data` persiste o banco e os anexos. Não execute `down -v` se quiser preservar os dados. O daemon Docker estava indisponível durante a verificação deste ambiente; veja `docs/KNOWN_LIMITATIONS.md`.

## Demonstração ponta a ponta

1. Entre como admin. Em Administração, crie uma conta de perfil `supplier`; anote seu ID. Em Fornecedores, cadastre nome/função, vincule essa conta e informe a tarifa fictícia de R$ 120/h.
2. Em Backlog, crie uma atividade atribuída ao fornecedor. Ela pode ser salva sem horas. Abra o card, use Construtor do card, adicione campos, configure obrigatoriedade/visibilidade/edição e salve.
3. Crie uma sprint, adicione a atividade do backlog e inicie. Ela passa a A fazer.
4. Como fornecedor, abra sua tarefa. Tentar entrar em produção sem horas previstas é bloqueado. Informe 10 horas previstas e salve; mova para produção. Informe 8 horas utilizadas e mova para revisão.
5. Como gestor, em Aprovações de horas, rejeite com justificativa. Como fornecedor, corrija/reapresente. Como gestor autorizado, aprove e conclua. Fornecedor não consegue concluir nem consultar tarifas.
6. Reajuste a tarifa cadastral para R$ 150/h. A tarefa existente continua usando R$ 120/h e total aprovado R$ 960,00.
7. Consulte Visão geral/Relatórios e exporte XLSX/PDF, selecionando os filtros e a inclusão financeira quando autorizada.
8. Encerre a sprint com outra atividade pendente. Ela retorna ao backlog; o histórico e o retrato da sprint encerrada são preservados.

## Estrutura

```text
backend/
  app/             API, segurança, modelos, serviços, repositórios e relatórios
  migrations/      Alembic 0001 a 0004
  tests/           integração, autorização, concorrência e migrações
  data/            SQLite local e BLOBs de anexos, fora do Git
frontend/
  src/             páginas React, construtor, Kanban e testes Vitest/RTL
  e2e/             cenários reais de navegador Playwright
scripts/           instalação/início local e runner E2E isolado
docs/              arquitetura, regras, métricas, migração futura e validação
docker-compose.yml
```

Consulte também `docs/ARCHITECTURE.md`, `docs/PERMISSIONS.md`, `docs/METRICS.md`, `docs/DATABASE_MIGRATION.md`, `docs/DECISIONS.md` e `docs/KNOWN_LIMITATIONS.md`.
## Publicação para testes

Aplicação: **https://os-manager-phi.vercel.app** · Backend: https://os-manager-api.onrender.com · Código: [PedroGiffoni/OS_Manager](https://github.com/PedroGiffoni/OS_Manager).

Contas de nuvem: os mesmos usuários fictícios descritos acima, mas com senha privada gerada para a publicação. Consulte **OS_MANAGER_DEMO_PASSWORD** no [painel Render](https://dashboard.render.com/web/srv-db8irum89jmc73dttfl0); não use a senha local na nuvem. O usuário autorizou SQLite descartável: alterações, anexos e sessões podem desaparecer quando o Render Free reinicia ou suspende. Use apenas exemplos fictícios.

Publicação e fluxo verificados: health HTTP 200, build remoto e **4 E2E no domínio publicado passaram**. Estado, contas e como repetir: [DEPLOYMENT_STATUS.md](docs/DEPLOYMENT_STATUS.md). Guia de configuração: [DEPLOYMENT.md](docs/DEPLOYMENT.md).
