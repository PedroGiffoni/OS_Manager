# Validação executada

## Recorrência semanal de automações — 07/11/2026

- O construtor de automações agora aceita execução diária ou semanal com seleção de dias da semana. Horários e weekdays usam UTC (segunda=0 até domingo=6). A execução permanece idempotente por regra e data; uma recorrência semanal selecionada em vários dias executa uma vez em cada dia escolhido, sem repetição no mesmo dia.
- Migração `0037` adiciona frequência e dias, preservando regras anteriores como diárias. No downgrade, regras semanais são desativadas antes da remoção dos campos para não virarem execuções diárias inesperadas.
- `.venv\\Scripts\\python.exe -m pytest backend\\tests\\test_automation.py backend\\tests\\test_weekly_automation_migration.py backend\\tests\\test_automation_run_log.py -q`: **36 passed**, um aviso httpx/Starlette; inclui seleção/validação de dias, execução nos dias configurados, ausência nos demais, idempotência no mesmo dia, comportamento seguro no downgrade e autorização/redação do log de automações.
- Ruff nos módulos/testes alterados: **passou**. Frontend `npm run typecheck`, `npm run lint`, `npm test -- --run` (**5 arquivos, 21 testes**) e `npm run build`: **passaram**; mantém aviso informativo de bundle principal acima de 500 kB.
- Alembic em SQLite temporário: `upgrade head → downgrade 0036 → upgrade head` passou e `alembic current` confirmou `0037 (head)`. Revisões anteriores emitem avisos conhecidos sobre CHECK constraints sem nome durante recriação batch; não impediram a migração.

## Auditoria de execuções de automação — 07/11/2026

- A API `GET /api/v1/automations/runs` e a aba de planejamento mostram até 100 eventos aplicados por página, com atualização visual a cada 15 segundos. O payload omite valores alterados e conteúdo de comentários; permissão `manage_automation` é exigida.
- O teste direto do handler cobre paginação, resumo de propriedades, ausência de comentário confidencial/custo e bloqueio de fornecedor/gestor sem permissão. A inicialização de `TestClient` local ficou pendente no sandbox Windows nesta execução, então não foi declarado teste HTTP para a rota.
- `.venv\\Scripts\\python.exe -m pytest backend\\tests\\test_automation_run_log.py backend\\tests\\test_automation.py -q`: **35 passed**, um aviso de depreciação httpx/Starlette. Ruff: **All checks passed**.
- Frontend: `npm run typecheck`, `npm run lint`, `npm test -- --run` (**5 arquivos, 21 testes**) e `npm run build`: **passaram**. O build mantém o aviso informativo do bundle principal acima de 500 kB.

## Campo `resolution` na consulta avançada — 07/11/2026

- A JQL filtra os motivos persistidos `Done`, `Fixed`, `Duplicate`, `Won't Do`, `Cannot Reproduce` e `Other`. Cards já concluídos recebem `Done` pela migração `0039`; reabertura limpa a resolução efetiva e mantém o evento no histórico.
- A versão anterior do teste, que verificava apenas a resolução derivada da categoria `Done`, foi substituída pelos testes de motivo persistido e histórico abaixo.
- Testes de consulta, aceite concluir/reabrir e ciclo de migrações: **61 passed** (`test_query_language.py`, `test_acceptance.py` e `test_migrations_upgrade_downgrade_empty_database`). A migração `0039` passou por upgrade, downgrade completo e upgrade novamente em SQLite.
- Regressão completa do backend: **247 passed in 56,89s** (exclui `test_deployment.py`). Playwright completo: **14 passed in 37,1s**, incluindo o modal de resolução e o registro do motivo `Fixed` no card.
- Após ajustar o serviço para detectar a categoria final, passaram **23 testes** de aceite/planejamento, o E2E específico do fluxo (**1 passed in 8,2s**) e o caso de rejeição de resolução fora da lista (**1 passed**).
- TypeScript, ESLint, Vitest (**5 arquivos, 21 testes**) e build passaram. O bundle principal tem 657,79 kB; permanece o aviso Vite acima de 500 kB.

## Filtros JQL salvos e compartilhados — 07/11/2026

- Criar/listar/editar/excluir filtros pessoais ou compartilhados foi integrado à consulta global; papéis e grupos internos determinam o compartilhamento, enquanto cada consulta permanece sujeita à autorização individual dos cards. Fornecedores veem somente filtros próprios. Consultas compartilhadas que tentem inferir texto amplo ou valores de campos personalizados são rejeitadas.
- `.venv\\Scripts\\python.exe -m pytest backend\\tests\\test_saved_filters.py backend\\tests\\test_saved_filter_migration.py -q`: **4 passed**, um aviso de depreciação httpx/Starlette. Cobriu escopo por papel/grupo, revogação por grupo inativo, filtros pessoais de fornecedor, propriedade para editar/remover, permissão para compartilhar, consultas/nomes inválidos, OpenAPI e ciclo da migração.
- Ruff nos módulos, teste e migração: **passou**. Frontend `npm run typecheck`, `npm run lint`, `npm test -- --run` (**5 arquivos, 21 testes**) e `npm run build`: **passaram**; bundle principal segue acima do limite informativo de 500 kB.
- Alembic em SQLite temporário: `upgrade head → downgrade 0037 → upgrade head` passou e `alembic current` confirmou `0038 (head)`. Avisos existentes sobre CHECK constraints sem nome em migrações anteriores não impediram o ciclo.
- E2E dedicado `scripts/run_e2e.py --grep "filtro JQL salvo" --reporter=line`: **1 passed** em Chrome do sistema, API/Vite locais e SQLite descartável. Confirma criação/compartilhamento por administrador, aplicação por pessoa interna e ausência para fornecedor. A limpeza usa sessão de API isolada; não houve publicação remota.
- Regressão backend direcionada a filtros/JQL/relatórios: **56 passed**; Ruff: **All checks passed**. Frontend: TypeScript, ESLint e build passaram; Vitest: **5 arquivos, 21 testes**. Bundle principal 655,29 kB e chunk de gráficos 414,18 kB; permanece o aviso Vite acima de 500 kB.

## Regressão completa após paridade Jira incremental — 07/11/2026

- Backend `backend\.venv\Scripts\python.exe -m pytest tests --ignore=tests\test_deployment.py -q --show-capture=no`, executado a partir de `backend`: **247 passed in 56,33s**. `test_deployment.py` permanece excluído porque depende do ambiente de deploy.
- Playwright `scripts/run_e2e.py --reporter=line`: **14 passed in 37,4s**, usando Chrome do sistema, SQLite temporário, API/Vite locais. Inclui o compartilhamento de filtro entre administrador e usuário interno e o isolamento para fornecedor; suíte repetida após a adição dos gatilhos de relação.
- Typecheck, ESLint, Vitest (**5 arquivos, 21 testes**), build de produção e Ruff passaram. Permanecem os avisos conhecidos de chunks Vite acima de 500 kB e CHECK constraints sem nome nas migrações antigas.

## Automações de relações entre cards — 07/11/2026

- A criação e remoção de dependências dispara automações transacionais. `link_types` filtra `blocks`, `relates` e `duplicates`; auditoria registra somente o tipo e a identidade do card relacionado.
- `backend\.venv\Scripts\python.exe -m pytest tests\test_automation.py tests\test_planning_foundation.py -q`: **51 passed**; cobertura valida schema, filtro por tipo, isolamento do gatilho e execução ao criar/remover uma relação via API. Regressão backend completa: **247 passed** (exclui `test_deployment.py`).
- Frontend TypeScript, ESLint e build passaram. O bundle principal tem 656,08 kB e o chunk de gráficos 414,18 kB, acima do limite informativo de 500 kB; constraints CHECK antigas sem nome também seguem como aviso.

## Feed iCalendar pessoal — 07/11/2026

- A agenda agora oferece feed contínuo somente leitura. Cada usuário emite/rotaciona uma chave bearer aleatória; o banco armazena apenas SHA-256, e a revogação invalida a credencial imediatamente. A rota declara Basic Auth no OpenAPI, desafia clientes sem credenciais e revalida usuário ativo e escopo atual dos cards em cada leitura. O payload não inclui fornecedores, horas ou valores financeiros.
- Migração `0036` cria tabela de token pessoal com chave estrangeira em cascata e unicidade da credencial. Em SQLite temporário, `upgrade head → downgrade 0035 → upgrade head` passou e `alembic current` confirmou `0036 (head)`.
- `.venv\\Scripts\\python.exe -m pytest backend\\tests\\test_calendar_export.py backend\\tests\\test_personal_calendar_feeds_migration.py -q`: **5 passed**, um aviso de depreciação httpx/Starlette. Inclui geração, hash, Basic Auth documentado no OpenAPI, isolamento do fornecedor, rotação, revogação, cache privado e migração.
- Ruff backend: **passou**. Frontend: `npm run typecheck`, `npm run lint`, `npm test -- --run` (**5 arquivos, 21 testes**) e `npm run build`: **passaram**; build mantém aviso informativo do bundle principal acima de 500 kB.
- O teste via `TestClient` autenticado ficou travado durante a inicialização do fixture de HTTP local neste ambiente Windows; por isso, a verificação da lógica de handler foi feita diretamente com credenciais Basic e SQLite isolado. Não foi declarado E2E HTTP validado para esta mudança.

## Gadget de resultados filtrados no dashboard — 07/11/2026

- Widgets internos podem exibir uma tabela de resultados de cards com seleção de até 10 colunas allowlistadas, limite configurável de 1 a 100, total independente do limite e filtros do painel mais JQL do widget. Valores financeiros e campos personalizados não são retornados; fornecedores não podem acessar dashboards personalizados.
- Migração `0035` adiciona colunas e limite com defaults compatíveis com widgets existentes. Teste cobre backfill e downgrade.
- `.venv\\Scripts\\python.exe -m pytest backend\\tests\\test_dashboard_widget_dimensions.py backend\\tests\\test_dashboard_filter_results_migration.py backend\\tests\\test_dashboard_widget_query.py backend\\tests\\test_dashboard_containers.py -q`: **13 passed**, um aviso httpx/Starlette.
- Ruff nos módulos/testes alterados: **passou**. Frontend: `npm run typecheck`, `npm run lint`, `npm test -- --run` (**5 arquivos, 20 testes**) e `npm run build`: **passaram**; build mantém aviso informativo do bundle principal acima de 500 kB.
- Alembic `upgrade head → downgrade 0034 → upgrade head` em arquivo SQLite temporário: **passou**; `alembic current` confirmou `0035 (head)`. A migração emite avisos preexistentes de CHECK sem nome ao recriar tabelas em revisões anteriores; não impediu upgrade/downgrade.

## Correções de integração e auditoria — 07/11/2026

- A suíte HTTP autenticada expôs e corrigiu a serialização de detalhes de auditoria de automações, que podia receber `changes` em formato de objeto em vez de lista.
- Dependência `httpx2==2.13.0` adicionada para o `TestClient` nas versões atuais do Starlette; testes de compartilhamento passaram a selecionar explicitamente o dashboard compartilhado e confirmar respostas 403 para acessos negados.
- `python -m pytest --ignore=tests/test_deployment.py -q --show-capture=no`: **195 passed** naquele incremento. `tests/test_deployment.py` foi excluído por executar verificações de publicação externa, não por falha local.
- `tests/test_planning_foundation.py tests/test_report_filters.py`: **14 passed** após os ajustes direcionados.
- A cobertura HTTP foi executada fora do sandbox restritivo de sockets locais do Windows. Não foram executados E2E de navegador nem o teste de deploy externo nesta rodada.
- `git diff --check`: passou.

## Gatilhos de automação por mudança de prazo e prioridade — 07/11/2026

- `due_changed` e `priority_changed` estão disponíveis na interface e na API. O primeiro cobre edição do card e cronograma e não dispara sem diferença de data; o segundo guarda a prioridade anterior/nova. Testes diretos do serviço/endpoint verificam contexto e auditoria.
- `.venv\\Scripts\\python.exe -m pytest tests/test_automation.py -q`: **31 passed**, um aviso de depreciação httpx/Starlette. Ruff nos módulos e testes backend alterados: **passou**.
- Frontend: `npm run typecheck`, `npm run lint`, `npm test -- --run` (**3 arquivos, 6 testes**) e `npm run build`: **passaram**. O Vitest usou `LOCALAPPDATA` temporário por restrição de escrita no caminho padrão; o build mantém aviso informativo do bundle principal acima de 500 kB.
- `git diff --check`: **passou**, com os avisos usuais do Git sobre conversão LF/CRLF.

## Widgets de análise e filtros JQL de planejamento — 07/11/2026

- Widgets agora agrupam cards por mês de criação e apresentam os dados em gráfico de linha; períodos mensais são ordenados cronologicamente. A métrica de idade média calcula dias UTC desde a criação para cards ainda abertos e exclui concluídos. A API continua usando a consulta filtrada e o escopo de acesso já aplicado pelo dashboard. Na JQL, `key` funciona como alias Jira de `issuekey`, `issue` e `id`, incluindo filtro e ordenação pela chave `OS-<id>`. Consultas também filtram/ordenam início planejado, prazo final, minutos estimados e utilizados, aceitando funções relativas UTC para datas e `IS EMPTY`/`IS NOT EMPTY` no início planejado.
- `.venv\\Scripts\\python.exe -m pytest tests/test_dashboard_widget_dimensions.py tests/test_query_language.py -q`: **49 passed**, um aviso de depreciação httpx/Starlette. Ruff nos módulos e testes Python alterados: **passou**.
- Frontend: `npm run typecheck`, `npm run lint`, `npm test -- --run` (**3 arquivos, 6 testes**) e `npm run build`: **passaram**. O Vitest exigiu `LOCALAPPDATA` temporário por restrição de escrita no diretório padrão; o build mantém aviso do bundle principal acima de 500 kB.
- `git diff --check`: **passou**, com avisos normais de conversão LF/CRLF do Git para arquivos existentes.

## Assinaturas agendadas de filtros — 07/11/2026

- Usuários podem criar, editar, pausar, retomar e excluir até 20 filtros salvos, com periodicidade diária ou semanal. A criação/edição captura a lista corrente como base para não notificar resultados antigos. O worker reavalia o filtro dentro do escopo do usuário e gera avisos internos para novas correspondências; mudanças futuras de consulta/permissão podem desativar a assinatura com mensagem segura. Fornecedores continuam restritos às próprias atividades. E-mail/push não é exigido nem enviado.
- Migração `0023` adiciona assinaturas, estado de correspondência e rótulo de origem da notificação. O teste verifica o default dos avisos existentes e cascata/downgrade. Assinaturas limitam novas notificações a 50 por execução e drenam lotes adicionais em intervalos curtos.
- `.venv\Scripts\python.exe -m pytest tests/test_filter_subscriptions.py tests/test_filter_subscriptions_migration.py tests/test_dashboard_widget_order_migration.py tests/test_agile_reporting.py -q`: **10 passed**, um aviso de depreciação httpx/Starlette. Inclui reentrada de cards nos resultados, escopo do fornecedor, privacidade por usuário, regra administrativa do histórico e constraints de migração.
- Suíte Python sem testes HTTP conhecidos por travar neste ambiente Windows: **78 passed**, um aviso httpx/Starlette. `ruff check --no-cache` nos módulos e testes alterados: **passou**.
- Alembic em arquivo SQLite temporário: `upgrade head → downgrade 0022 → upgrade head`: **passou**, corrente em `0023 (head)`. OpenAPI confirmou os métodos das rotas de assinatura e reordenação de widgets. Não substitui requisições HTTP autenticadas.
- `npm run typecheck`, `npm run build`, `npm run lint`, `npm test`: **passaram**; Vitest 3 arquivos/6 testes. O build mantém aviso informativo de bundle principal acima de 500 kB. `git diff --check`: **passou**.

## Ordem pessoal dos widgets do painel — 07/11/2026

- A posição dos widgets agora é salva por usuário, inclusive para gadgets compartilhados, sem mudar a ordem dos demais usuários. A API exige que a lista corresponda ao conjunto visível, valida IDs únicos e mantém permissões financeiras aplicadas.
- Nova migração `0022` cria `dashboard_widget_positions`, com chave composta por usuário/widget, cascata para exclusões e índice por usuário/posição. Foram adicionados testes de API para isolamento da ordem e rejeição de listas inválidas, além de teste de migração/cascata.
- `npm run typecheck`, `npm run build` e `npm test`: **passaram**; o Vitest executou 3 arquivos e 6 testes. O build mantém aviso informativo de bundle acima de 500 kB.
- Sintaxe Python dos seis arquivos alterados: **passou**; `git diff --check`: **passou**.
- Os novos testes Python de API e migração não foram executados neste ambiente: FastAPI/SQLAlchemy/Alembic não estão instalados e o pip não consegue acessar o índice por bloqueio de rede/DNS. A lógica backend e migração não devem ser consideradas validadas até rodar a suíte Python em ambiente com as dependências instaladas.

## Previsão por velocidade histórica — 07/11/2026

- O relatório de sprint inclui horas planejadas restantes, mediana de velocidade e faixa entre percentis 25/75 das até seis sprints encerradas anteriores. A previsão só calcula faixa com três sprints e percentil conservador positivo; não converte o resultado em uma data prometida. Casos sem histórico e velocidade zero são tratados explicitamente.
- `npm run typecheck` e `npm run build` em `frontend`: **passaram**. O bundle principal permanece acima do limite informativo de 500 kB.
- `npm test` com `LOCALAPPDATA` apontado para diretório temporário: **3 arquivos e 6 testes passaram**. Verificação isolada da função de cálculo: **4 cenários passaram** (faixa mediana/percentis, histórico insuficiente, velocidade inferior zero e nenhuma hora planejada restante). A compilação de sintaxe Python passou sem gerar bytecode.
- `git diff --check`: **passou**.
- `python -m pytest tests/test_agile_reporting.py -q` não pôde iniciar: FastAPI não está instalado no Python ativo. `pytest.exe` do Anaconda falha ao carregar uma DLL (`Realocação Inválida da DLL do Sistema`). A criação de ambiente virtual falhou no `ensurepip`; a instalação pelo pip não pôde acessar o índice de pacotes por bloqueio de DNS/rede. Os novos testes unitários estão escritos, mas não foram executados. Não considerar essa parte do backend validada neste ambiente.

Verificações realizadas em 15/10/2026 no Windows, Python 3.13 e Node.js v24.11.0. Dados de integração e E2E são fictícios, em bancos SQLite temporários separados do desenvolvimento. Não houve uso de servidor de banco, conta externa ou serviço pago. Os comandos abaixo foram executados; esta página não substitui homologação institucional.

## Resultado final por comando

| Comando e diretório | Resultado real |
| --- | --- |
| backend: ../.venv/Scripts/python.exe -m pytest -q | **17 passed, 1 warning in 19.78s** |
| backend: ../.venv/Scripts/python.exe -m ruff check app tests | **All checks passed!** |
| frontend: npm.cmd run test | **2 arquivos, 5 testes passaram**, última execução em 2.54s |
| frontend: npm.cmd run build | TypeScript + Vite: **build passou**, assets gerados em dist |
| frontend: npm.cmd run typecheck | tsc -b: **código 0** |
| frontend: npm.cmd run lint | ESLint: **código 0**, sem erros |
| frontend: npm.cmd run format:check | **All matched files use Prettier code style!** |
| raiz: .venv/Scripts/python.exe scripts/run_e2e.py | **4 passed (9.5s)**, API/SQLite temporários e Chromium real |
| frontend: npm.cmd audit | **found 0 vulnerabilities** |
| raiz: .venv/Scripts/python.exe -m pip_audit --local | **No known vulnerabilities found** |
| raiz: ./scripts/Setup-Local.ps1 -Demo | Instalação pelos locks passou; Alembic passou; seed recusou reaplicar sobre usuários existentes; npm ci passou |
| raiz: docker compose config --quiet | **código 0**, sintaxe Compose válida |
| docker info | **Falhou**: pipe dockerDesktopLinuxEngine indisponível; daemon não está em execução |

Trechos finais da saída:

```text
17 passed, 1 warning in 19.78s
All checks passed!
Test Files  2 passed (2)
Tests       5 passed (5)
✓ built in 229ms
All matched files use Prettier code style!
4 passed (9.5s)
found 0 vulnerabilities
No known vulnerabilities found
```

O aviso Python é da integração httpx/Starlette TestClient depreciada; não é falha de teste. O npm também informa depreciação das linhas Recharts 2 e ESLint 9. Os locks foram auditados sem vulnerabilidades conhecidas na data da execução; isso não constitui garantia permanente nem análise completa de segurança.

## Evidências por marco

1. Fundação local: Alembic aplicou em banco vazio; autenticação, sessão, CSRF, concessões e revogação foram exercitadas; script de setup e build passaram. Compose tem configuração válida, mas execução de contêineres NÃO foi validada.
2. Fornecedores: criação atômica de fornecedor/tarifa, histórico de reajustes, snapshots de alocação e isolamento financeiro. Teste R$ 120/h → reajuste R$ 150/h → aprovação de 8 h manteve custo de R$ 960,00.
3. Backlog/sprints: vínculo ativo único, rejeição de duplicidade, encerramento com retorno de pendentes, preservação histórica, arquivamento conservador e migrações upgrade → downgrade → upgrade em SQLite vazio.
4. Kanban/cards: transições recusadas conservam estado/versão; ordem tem controle de versão; schemas preservam valores; campos ocultos/editáveis têm validação no servidor. Drag and drop real foi exercitado no navegador e um problema de colisão com o próprio card foi encontrado e corrigido. Construtor inclui campos adicionais e referências nativas ordenáveis; campos nativos de horas foram testados no fluxo real.
5. Horas/aprovações: exclusividade do fornecedor, estimativa obrigatória, total utilizado obrigatório, rejeição/reapresentação, aprovação explícita, idempotência, concorrência de aprovação, conclusão exclusiva por gestor e reabertura com retirada do consolidado corrente. Arredondamento de 0,5 centavo resultou em 1 centavo com ROUND_HALF_UP.
6. Dashboards/exports: filtros e escopo, custos aprovados, Excel com células de texto protegidas contra fórmulas, PDF lido com pypdf para conferir inclusão/ausência de informação financeira. Replanejar horas já aprovadas não duplica custo entre sprints.
7. Qualidade: lint/typecheck/build, suites Python/Vitest/Playwright, auditorias de dependências e inspeção das capturas desktop (1440 px), móvel (390 px) e Kanban. Nenhuma página operacional depende de valores simulados em código frontend.

## Cenários Playwright

- Gestor cria atividade; fornecedor informa horas; bloqueios de transição; gestor aprova/conclui e baixa Excel.
- Cadastro de fornecedor e tarifa; configuração individual do card e persistência de valor personalizado.
- Drag and drop inválido mantém origem e apresenta horas previstas faltantes; captura desktop/mobile e verificação de largura responsiva/logout.
- Inclusão e reordenação de campos nativos; fornecedor edita horas pelos campos personalizados; os minutos são persistidos nos registros estruturais e tarifas continuam ausentes do payload.

## Bloqueio de Docker

Saída observada: `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine ... The system cannot find the file specified.`

Para validar depois de iniciar Docker Desktop com engine Linux:

```powershell
docker compose up --build
docker compose ps
docker compose exec -e OS_MANAGER_ALLOW_DEMO_SEED=true backend python -m app.seed
```

Verificar frontend em http://localhost:8080, health em http://127.0.0.1:8000/api/v1/health, login/fluxo e persistência após restart. Não remover o volume para esse teste. Nenhum resultado de build/execução Docker foi presumido ou declarado como passado.

## Preparação de publicação Vercel/Render — 15/10/2026

- `python -m pytest -q` no backend: **35 passed**, 1 aviso conhecido httpx/Starlette, 24,99 s. Inclui configuração de porta, exigência de HTTPS/Secure, origens exatas, rejeição de seed público sem senha privada, geração do proxy, sessão HTTPS com CSRF/origem e seed privado idempotente em SQLite temporário sem registrar a senha.
- `python -m ruff check app tests`: **All checks passed**.
- `python -m ruff format --check app tests`: **19 files already formatted**.
- `npm run build`: **passou**, TypeScript e Vite; 662 módulos, saída `frontend/dist`.
- `python scripts/run_e2e.py`: **4 passed (9.9s)**, banco temporário, migrações e seed local; nenhum dado de desenvolvimento alterado.
- `vercel whoami`: **Logged out**. A tentativa sob sandbox foi impedida de criar o diretório global da CLI; a verificação autorizada fora do sandbox confirmou ausência de sessão.
- A pasta não possui repositório Git remoto configurado. Integrações GitHub/Vercel/Render foram localizadas, mas nenhuma conexão foi confirmada.
- `render.yaml`, entrypoint e gerador `scripts/configure_vercel.py` preparados. Nenhuma URL real foi inventada no arquivo Vercel; ele será gerado com a origem efetiva do backend.
- **Não executados:** criação de serviço, build Docker remoto, deploy Vercel/Render, validação do Blueprint no provedor e testes dos domínios públicos. Dependem das contas e da escolha de persistência. Testes locais não homologam a hospedagem.


## Publicação remota efetivamente executada — 15/10/2026

Após autorização de My Workspace/dados descartáveis: Render Docker Free live; Vercel produção READY/promovida e Git conectado. URLs e IDs em DEPLOYMENT_STATUS.md. Health direto/pelo frontend HTTP 200 `status=ok`. Build Vercel npm ci + TypeScript + Vite passou (662 módulos, build remoto concluído), npm audit informou 0 vulnerabilidades. `scripts/run_remote_e2e.py --base-url https://os-manager-phi.vercel.app`: **4 passed (51.3s)**. A senha foi recebida por terminal oculto e fornecida apenas ao ambiente do processo filho; traces remotos desativados. Logs Render filtrados por error não retornaram eventos.

O teste HTTP via `vercel curl` no domínio estável teve uma tentativa com timeout de 45 s; a verificação comum seguinte retornou 200 e os quatro testes do navegador passaram. O serviço gratuito pode ter retomada lenta. O primeiro domínio específico de deployment exigiu a autenticação Vercel já existente; o domínio estável foi acessado normalmente pelo navegador. Não foi removida a proteção da Vercel.

Não executado teste de carga, recuperação de backup, suspensão deliberada ou homologação institucional. PDF e IDOR granular foram exercitados na suíte Python local, enquanto a suíte remota verifica o fluxo do navegador e Excel. Docker local ainda indisponível; Docker remoto foi construído e executado pelo Render.

## Funcionalidades inspiradas nas lacunas do Jira — 06/11/2026

- `npm run build`: **passou**, TypeScript e Vite; o bundler emitiu aviso informativo de chunk principal acima de 500 kB.
- `ruff check --no-cache app tests/test_planning_foundation.py tests/test_integration_helpers.py`: **All checks passed**.
- `pytest tests/test_integration_helpers.py -q`: **3 passed** (assinaturas, leitura de IDs, URLs e resumo de webhook).
- `DATABASE_URL=sqlite:///./tmp/parity_final.db python -m alembic upgrade head`: **passou** até `0010`; Alembic emitiu avisos de constraints CHECK sem nome em revisões antigas `0006`/tarefas/sprints.
- Na mesma base descartável, `alembic downgrade 0009` seguido de `alembic upgrade head`: **passou**, confirmando reversão e reaplicação da migração `0010`.
- **Não validados nesta rodada:** testes de API que usam `TestClient` e os fluxos de ponta a ponta dos novos recursos. A tentativa anterior ficou bloqueada no `socketpair` do event loop Proactor do Windows, antes de chegar à lógica dos endpoints. Isso não é tratado como teste aprovado.
- Foi adicionado teste de integração para o endpoint de relatórios ágeis (sprint, horas planejadas e restrição a fornecedores), mas ele pertence à suíte `TestClient` e ainda não foi executado com sucesso neste ambiente.
- Na execução inicial desta rodada, ainda faltavam previsão de capacidade interna e representação atualizada de parte dos recursos. A seção seguinte registra a complementação e as validações posteriores; permanecem as lacunas explicitadas no plano de paridade.

## Implementação de paridade e previsão de capacidade — 06/11/2026

- `pytest tests/test_workflows.py tests/test_capacity_reporting.py tests/test_query_language.py tests/test_planning_reporting.py tests/test_agile_reporting.py tests/test_integration_helpers.py -q`: **19 passed**, 1 aviso de depreciação conhecido do TestClient/httpx.
- `ruff check --no-cache app tests/test_capacity_reporting.py tests/test_planning_foundation.py tests/test_query_language.py tests/test_planning_reporting.py tests/test_agile_reporting.py tests/test_integration_helpers.py`: **All checks passed**.
- `tsc -b && vite build && eslint src`: **código 0**, build e lint passaram. Vite emitiu aviso de chunk principal de 554 kB acima de 500 kB.
- `git diff --check`: **passou**.
- Alembic em SQLite temporário: **upgrade head → downgrade 0012 → upgrade head passou**, incluindo as migrações `0012` (responsável interno) e `0013` (escopo de workflow por tipo de card).
- A verificação de API que usa `TestClient` e os fluxos E2E das funções novas **não foram validados nesta rodada**. O TestClient já apresentou bloqueio no event loop Proactor do Windows. A tentativa de Vitest falhou antes da execução dos testes porque o runner não conseguiu criar `.vitest-secret-token` no diretório de usuário, cache local ou diretório `LOCALAPPDATA` redirecionado para a pasta do projeto; por isso nenhum teste frontend foi declarado como aprovado nesta rodada. Lint, typecheck e build frontend foram executados separadamente.
- Foram cobertos por teste unitário os cálculos de demanda por período, cards sem datas, capacidade percentual e ausência de sobrecarga. Os testes de rota para responsável interno, isolamento do payload do fornecedor e bloqueio de períodos sobrepostos foram adicionados, mas aguardam execução da suíte de integração HTTP.
- Persistem as diferenças listadas na seção de limitações: subconjunto de JQL, automações/workflows mais enxutos, sem notificações/assinaturas, marketplace ou planejamento preditivo/nivelamento multi-equipe. A implementação não é paridade integral com todos os módulos/planos do Jira.

## Compartilhamento de filtros por grupos internos — 06/11/2026

- `pytest tests/test_group_sharing.py tests/test_workflows.py tests/test_capacity_reporting.py tests/test_query_language.py tests/test_planning_reporting.py tests/test_agile_reporting.py tests/test_integration_helpers.py -q`: **21 passed**, 1 aviso conhecido httpx/Starlette.
- `ruff check --no-cache app ...`: **All checks passed** para os módulos e testes alterados nesta rodada.
- `tsc -b && vite build && eslint src`: **código 0**; TypeScript, build e lint passaram. O chunk principal de 559 kB continua acima do limite informativo do Vite.
- Alembic em SQLite temporário: **upgrade head → downgrade 0013 → upgrade head passou**, incluindo migração `0014` para grupos e compartilhamento.
- `git diff --check`: **passou**.
- O teste unitário exercitou escopo por associação, revogação ao desativar grupo e isolamento de fornecedor. Os testes de endpoint adicionados para CRUD de grupo e filtros/widgets permanecem sem execução pela limitação TestClient/Proactor descrita acima; Vitest também continua sem iniciar por bloqueio de criação do token no sandbox. Nenhum fluxo HTTP/E2E foi declarado validado.

## Acompanhamento e notificações internas — 06/11/2026

- `npm run build`: TypeScript e Vite passaram; chunk principal de 562 kB gerou aviso informativo acima de 500 kB.
- `npm run lint`: **passou** (`eslint src`).
- `ruff check --no-cache backend/app/main.py backend/app/models.py backend/app/services.py backend/migrations/versions/0015_task_watchers_notifications.py`: **All checks passed**.
- Migração até `0015` em `backend/tmp/notifications_migration.db`: **passou**. Permanecem avisos de constraints CHECK sem nome em migrações antigas.
- `python -m pytest tests/test_notifications.py tests/test_group_sharing.py tests/test_workflows.py -q`: **5 passed**, 1 aviso conhecido da integração httpx/Starlette. Inclui criação de notificação para watchers, exclusão do autor e isolamento/revogação do compartilhamento por grupo.
- A tentativa de executar `tests/test_planning_foundation.py` com `.venv` ficou sem saída por mais de 60 s no TestClient/event loop Proactor e foi interrompida; a execução global `pytest.exe` também falhou ao carregar no Windows com erro de relocação de DLL. `python -m pytest` via Python global não tem FastAPI instalado. A cobertura HTTP dessa função permanece pendente; nenhum teste de rota foi declarado aprovado.

## Workflows por tipo de card — 06/11/2026

- `python -m pytest tests/test_workflows.py -q`: **5 passed**, 1 aviso conhecido do TestClient/httpx. Cobriu regra genérica, escopo legado, políticas específicas por tipo, substituição da lista de perfis, união dos campos obrigatórios e validação do payload.
- `ruff check --no-cache app/main.py app/models.py app/schemas.py app/services.py app/workflows.py migrations/versions/0016_workflow_type_rules.py tests/test_workflows.py`: **All checks passed**.
- `npm run build` e `npm run lint`: **passaram**; bundle principal 565 kB, com aviso informativo do Vite.
- Migração Alembic em SQLite temporário: **upgrade até `0016` → downgrade para `0015` → upgrade até `0016` passou**, preservando a linha única por transição e acrescentando regras específicas em JSON portável.
- Testes HTTP de movimentação com cada política específica ainda dependem de resolver o bloqueio TestClient/Proactor no Windows.

## Histórico de status na busca avançada — 06/11/2026

- `python -m pytest tests/test_query_language.py -q`: **14 passed**, 1 aviso conhecido TestClient/httpx. Inclui consulta SQLite real filtrando transição por origem, destino, autor e datas, além de formas inválidas e combinações com relações entre cards.
- `ruff check --no-cache app/query_language.py tests/test_query_language.py`: **All checks passed**.
- A busca histórica continua dentro da JQL reduzida; não foram adicionados operadores de histórico para outros campos nem funções do Jira.

## Consulta e automações incrementais — 07/11/2026

- `python -m pytest tests/test_automation.py tests/test_query_language.py tests/test_workflows.py tests/test_notifications.py tests/test_group_sharing.py tests/test_capacity_reporting.py tests/test_planning_reporting.py tests/test_agile_reporting.py tests/test_integration_helpers.py -q`: **37 passed**, 1 aviso conhecido TestClient/httpx.
- `ruff check --no-cache app/automation.py app/main.py app/schemas.py app/query_language.py app/workflows.py tests/test_automation.py tests/test_query_language.py tests/test_workflows.py`: **All checks passed**.
- `npm run build` e `npm run lint`: **passaram**. Bundle principal 566 kB; aviso informativo do Vite acima de 500 kB.
- A execução de `scripts/run_e2e.py` não concluiu: Playwright ultrapassou o limite de 240 segundos e foi encerrado. Nenhum E2E foi contabilizado como aprovado.
- A validação de rotas via `TestClient`/event loop Windows continua pendente; uma tentativa alternativa via servidor HTTP local não conseguiu completar o health check. Os testes SQLite dos filtros e testes unitários das regras de automação passaram, mas não substituem a cobertura HTTP.

## Distribuição diária de capacidade — 07/11/2026

- `python -m pytest backend/tests/test_capacity_reporting.py -q` via `.venv`: **1 passed**, 1 aviso conhecido da integração httpx/Starlette. Verificou distribuição por dias úteis, preservação da soma de minutos e alerta para sobrecarga concentrada em dias específicos.
- `ruff check --no-cache backend/app/main.py backend/tests/test_capacity_reporting.py`: **passou**.
- `npm run build` e `npm run lint`: **passaram**; bundle principal 567 kB, com aviso informativo do Vite acima de 500 kB.
- A execução combinada com `test_planning_foundation.py` foi interrompida após vários erros e demora excessiva na infraestrutura `TestClient` do Windows; não foi contabilizada como aprovada. A falha não reproduziu no teste isolado de capacidade.

## Ações e gatilhos adicionais de automação — 07/11/2026

- `.venv\Scripts\python.exe -m pytest backend/tests/test_automation.py backend/tests/test_capacity_reporting.py -q`: **13 passed**, 1 aviso conhecido de depreciação httpx/Starlette. Cobriu a nova ação de comentário com gravação em `comments` e auditoria e o início de sprint acionando a regra na transação.
- `ruff check --no-cache backend/app/main.py backend/app/automation.py backend/app/schemas.py backend/tests/test_automation.py backend/tests/test_capacity_reporting.py`: **passou**.
- `npm run lint` e `npm run build`: **passaram**. O bundle principal está em 568 kB e mantém aviso informativo do Vite acima de 500 kB.
- `npm test`: **2 arquivos e 5 testes passaram**. Foi necessário fornecer temporariamente o token local do Vitest em diretório ignorado do repositório, pois a sandbox bloqueou a criação automática; o arquivo foi removido ao final.

## Histórico `CHANGED` em campos nativos — 07/11/2026

- `.venv\Scripts\python.exe -m pytest backend/tests/test_query_language.py backend/tests/test_automation.py backend/tests/test_capacity_reporting.py -q`: **28 passed**, 1 aviso conhecido httpx/Starlette. Inclui histórico de status, prioridade e prazo removido (`EMPTY`), com filtro por autor/período e gravação normalizada pelo helper de auditoria.
- `ruff check --no-cache` nos módulos/modelos/migração/testes relacionados: **passou**; `git diff --check`: **passou**.
- Migração `0017` exercitada em SQLite temporário: upgrade de `0016` com auditoria legada, backfill e busca histórica passaram; downgrade para `0016` e re-upgrade com novo backfill também passaram. O arquivo temporário foi removido.
- A fixture HTTP foi alterada para SQLite em arquivo temporário por teste, sem subprocesso Alembic; migrações são validadas separadamente. A tentativa de `GET /health` não retorna no TestClient nem no ASGI transport neste Windows, inclusive com a camada HTTP isolada. Nenhuma chamada HTTP foi contabilizada como aprovada nesta tentativa.

## Filtros vazios e histórico de campos personalizados — 07/11/2026

- `.venv\Scripts\python.exe -m pytest backend/tests/test_query_language.py -q`: **19 passed**, 1 aviso conhecido de depreciação httpx/Starlette. Inclui execução SQLite de `IS EMPTY`/`IS NOT EMPTY` para prazo, fornecedor, sprint, pai, responsável, release, componente e etiquetas; validação de campos inválidos; e consultas `field_<id> CHANGED`/`WAS IN` para valores personalizados.
- Suíte combinada de consulta, automação e capacidade: **32 passed**, 1 aviso conhecido.
- `.venv\Scripts\ruff.exe check --no-cache backend/app/query_language.py backend/tests/test_query_language.py`: **All checks passed**.
- `git diff --check`: **passou**.
- Os testes exercitam a camada SQLAlchemy e SQLite local temporário. A rota HTTP `/tasks` com o parâmetro `jql` continua pendente de validação neste Windows pelo bloqueio TestClient/ASGI documentado acima.

## Agendamento de automações — 07/11/2026

- `.venv\Scripts\python.exe -m pytest backend/tests/test_automation.py -q`: **14 passed**. Cobriu execução diária em UTC, captura de atraso após reinício dentro do mesmo dia, idempotência na mesma data e aplicação de condições/ações.
- Suíte combinada de consulta, automação e capacidade: **34 passed**, 1 aviso conhecido httpx/Starlette.
- `ruff check --no-cache` nos módulos/testes de automação e consulta: **All checks passed**.
- `npm run build`: TypeScript e Vite passaram; bundle principal 568 kB e aviso informativo de chunk acima de 500 kB. `npm run lint`: passou.
- `npm test`: **2 arquivos e 5 testes passaram**. Foi criado um token aleatório temporário na pasta local ignorada do Vitest por limitação de permissão do diretório de usuário; o arquivo foi removido após o teste.
- Migrações em SQLite descartável: `upgrade head` (inclui `0018`), `downgrade 0017` e novo `upgrade head` passaram. Os únicos avisos foram de constraints CHECK sem nome em migrações anteriores; o banco temporário foi removido.
- A execução do worker é validada diretamente com sessões SQLAlchemy. A inicialização ASGI e a rota HTTP permanecem pendentes pelo bloqueio de TestClient/ASGI Windows documentado acima.

## Condições e ações de workflows — 07/11/2026

- `.venv\Scripts\python.exe -m pytest backend/tests/test_workflows.py -q`: **7 passed**, 1 aviso conhecido httpx/Starlette. Uma condição falsa mantém status e comentários inalterados; a condição verdadeira efetua a transição e executa ações de prioridade, etiqueta e comentário na mesma sessão.
- Suíte combinada de workflows, automações, consultas e capacidade: **41 passed**, 1 aviso conhecido.
- `ruff check --no-cache` nos módulos e testes de workflows/automações/consulta: **All checks passed**.
- `npm run build`: TypeScript/Vite passaram; bundle de 575 kB com aviso informativo acima de 500 kB. `npm run lint` passou.
- `npm test`: **2 arquivos e 5 testes passaram**. Foi necessário fornecer um token aleatório temporário no diretório local ignorado de Vitest; o arquivo foi removido após execução. O teste repetido concluiu sem aviso de processo preso.
- Migrações em SQLite descartável: `upgrade head` (inclui `0019`), `downgrade 0018` e novo `upgrade head` passaram, com avisos de constraints CHECK sem nome de migrações antigas; o arquivo temporário foi removido.

## JQL nas visualizações do quadro — 07/11/2026

- A visualização de quadro, tabela, linha do tempo e calendário aplica a JQL avançada no servidor e combina o resultado com os filtros rápidos locais. Visualizações salvas incluem a expressão JQL; compartilhamento continua condicionado à autorização interna existente.
- O quadro percorre `/tasks` em páginas de 200 itens, mantendo escopo e autorização do servidor para cada consulta, sem limitar silenciosamente os resultados a apenas a primeira página.
- Erros da JQL não escondem a barra de views/filtros, então a consulta pode ser corrigida sem sair do quadro; a interface mostra os operadores aceitos.
- `npm run build`: **passou** (TypeScript e Vite); bundle principal 576,61 kB, com aviso informativo do Vite acima de 500 kB.
- `npm run lint`: **passou**.
- `npm test`: **3 arquivos e 6 testes passaram**, incluindo teste da caixa de consulta avançada e do callback de edição. Foi necessário criar temporariamente o token aleatório exigido pelo Vitest no diretório ignorado `frontend/node_modules/.vitest`; o arquivo criado para a execução foi removido.
- `.venv\\Scripts\\python.exe -m pytest tests/test_automation.py tests/test_query_language.py tests/test_workflows.py tests/test_notifications.py tests/test_group_sharing.py tests/test_capacity_reporting.py tests/test_planning_reporting.py tests/test_agile_reporting.py tests/test_integration_helpers.py -q`: **51 passed**, um aviso conhecido de depreciação httpx/Starlette.
- `git diff --check`: **passou**. Os testes unitários/serviços de JQL passam; a rota HTTP de quadro com autenticação continua pendente de validação integrada neste Windows pelo bloqueio de TestClient/ASGI já descrito.

## Políticas de workflow por tipo — 07/11/2026

- Regras específicas de tipo agora podem acrescentar condições e ações à transição, além de perfis e campos obrigatórios. A base e a política específica são aplicadas em conjunto; as validações nativas continuam obrigatórias.
- Condições permitidas incluem etiqueta, presença de prazo e hierarquia de card, com comparação de etiquetas sem distinção entre maiúsculas/minúsculas. Valores e ações são validados pela lista permitida no backend. A persistência existente em JSON não exigiu nova migração.
- `.venv\\Scripts\\python.exe -m pytest tests/test_workflows.py -q`: **9 passed**. Inclui bloqueio quando uma condição exclusiva de bug não é satisfeita e execução atômica das ações base e específicas por tipo.
- `ruff check --no-cache app/schemas.py app/workflows.py tests/test_workflows.py`: **passou**.
- Suíte combinada de workflows, automações, consulta avançada, notificações, compartilhamento, capacidade e relatórios: **53 passed**, dois avisos de depreciação (httpx/Starlette e adapter de data do sqlite3).
- `npm run build`: **passou**; bundle principal 578,67 kB e aviso informativo acima de 500 kB. `npm run lint`: **passou**. `npm test`: **3 arquivos e 6 testes passaram**.
- `git diff --check`: **passou**. A política é verificada no serviço e nos schemas; a rota HTTP autenticada continua sem homologação integrada neste ambiente Windows.

## Sequências de ações de automação — 07/11/2026

- Cada regra de automação agora aceita de uma a dez ações allowlisted, executadas na ordem configurada dentro da mesma transação. As mudanças de campos e comentários da sequência geram um evento de auditoria; uma regra que altera vários campos incrementa uma vez a versão do card.
- Migração `0020` adiciona `actions` em JSON e converte os pares `action`/`config` legados para sequências de um item. O downgrade mantém a primeira ação quando só existe uma e falha explicitamente quando uma sequência maior causaria perda de dados.
- `.venv\\Scripts\\python.exe -m pytest tests/test_automation.py tests/test_automation_migration.py tests/test_query_language.py tests/test_workflows.py tests/test_notifications.py tests/test_group_sharing.py tests/test_capacity_reporting.py tests/test_planning_reporting.py tests/test_agile_reporting.py tests/test_integration_helpers.py -q`: **56 passed**, dois avisos conhecidos (depreciação httpx/Starlette e adapter de data do sqlite3).
- Teste Alembic em SQLite temporário: `upgrade head → downgrade 0019 → upgrade head` **passou**; testes da migração verificam backfill legado, downgrade reversível de uma ação e recusa de downgrade com múltiplas ações.
- `ruff check --no-cache` nos módulos/testes de automação, workflow e consulta: **passou**. `npm run build`: **passou**; bundle principal 580,04 kB, com aviso informativo acima de 500 kB. `npm run lint`: **passou**. `npm test`: **3 arquivos e 6 testes passaram**.
- `git diff --check`: **passou**. A integração das novas sequências por endpoint autenticado/E2E permanece pendente pela limitação HTTP/ASGI Windows descrita acima.

## Prazo relativo e filtro de prazo em automações — 07/11/2026

- Workflows e automações aceitam a ação `set_due_after_days`, limitada a 0–3.650 dias corridos após a criação do card. A data fixa usa `created_at` como base para permanecer idempotente em agendamentos diários e a mudança gera histórico nativo do campo de prazo.
- Automações aceitam `due_set=true/false` para filtrar cards com/sem prazo; a validação do backend exige booleano estrito.
- `.venv\\Scripts\\python.exe -m pytest tests/test_automation.py tests/test_workflows.py tests/test_automation_migration.py -q`: **26 passed**, um aviso conhecido httpx/Starlette. Inclui execução da ação nas sequências, verificação da data calculada, incremento único de versão, histórico e filtros com/sem prazo.
- `ruff check --no-cache` nos módulos e testes de schema, automação e workflow: **passou**.
- `npm run build`: **passou**; bundle principal 581,44 kB e aviso informativo acima de 500 kB. `npm run lint`: **passou**. `npm test`: **3 arquivos e 6 testes passaram**.
- `git diff --check`: **passou**. A integração via endpoint autenticado/E2E permanece pendente pela limitação HTTP/ASGI Windows descrita acima.

## Histórico `WAS` / `WAS IN` — 07/11/2026

- `.venv\Scripts\python.exe -m pytest backend/tests/test_query_language.py -q`: **15 passed**, 1 aviso conhecido httpx/Starlette. Verifica valor histórico anterior/novo, listas `WAS IN`, `EMPTY`, autor e período com consulta SQLAlchemy executada em SQLite.
- Suíte combinada de consulta, automação e capacidade: **28 passed**, 1 aviso conhecido.
- `ruff check --no-cache backend/app/query_language.py backend/tests/test_query_language.py backend/tests/conftest.py`: **passou**.

## Atribuição por workflows e automações — 07/11/2026

- Ações `assign_internal_user` aceitam somente contas internas ativas. A API oferece diretório filtrado a quem gerencia workflows ou automações; fornecedor não pode ser destino nem aparece nessa lista.
- Workflows validam os destinos antes de executar efeitos, evitando comentários/parciais em transição inválida. Automações auditam e ignoram a ação se o usuário for desativado após a configuração, preservando as outras ações da sequência.
- `.venv\Scripts\python.exe -m pytest backend/tests/test_assignee_actions.py backend/tests/test_automation.py backend/tests/test_workflows.py -q`: **28 passed**, um aviso de depreciação httpx/Starlette.
- `ruff check` nos módulos de segurança, workflows, automações, serviços, schemas, API e teste novo: **passou**. `npm run lint`: **passou**. `npm run build`: **passou**, bundle principal 582,93 kB com aviso informativo acima de 500 kB. `npm test` com `LOCALAPPDATA` temporário: **3 arquivos e 6 testes passaram**.
- `git diff --check`: **passou**. Testes HTTP autenticados/E2E permanecem pendentes pela limitação do ambiente Windows descrita nesta documentação.

## Condições por responsável interno — 07/11/2026

- Workflows podem exigir que a atividade esteja atribuída a uma conta interna selecionada; as condições por tipo continuam respeitando a mesma regra. Automações podem filtrar por responsável interno, validar referências ativas e ignorar corretamente os cards de outra pessoa.
- `.venv\Scripts\python.exe -m pytest backend/tests/test_assignee_actions.py backend/tests/test_automation.py backend/tests/test_workflows.py -q`: **29 passed**, um aviso httpx/Starlette.
- `ruff check --no-cache` nos módulos e testes de schema, API, automação, workflow e segurança: **passou**. `npm run lint`: **passou**. `npm run build`: **passou**, bundle principal 584,24 kB (aviso informativo acima de 500 kB). `npm test` com `LOCALAPPDATA` temporário: **3 arquivos e 6 testes passaram**.
- `git diff --check`: **passou**. As validações HTTP autenticadas e E2E ainda dependem de ambiente ASGI funcional; não foram declaradas validadas aqui.

## Filtros de automação por prazo — 07/11/2026

- Regras agendadas podem selecionar cards vencidos ou com prazo nos próximos N dias corridos (0–3.650), usando data UTC do servidor. O filtro é reavaliado em cada execução diária; não precisa de serviço externo nem migração.
- `.venv\Scripts\python.exe -m pytest backend/tests/test_assignee_actions.py backend/tests/test_automation.py backend/tests/test_workflows.py backend/tests/test_notifications.py -q`: **34 passed**, um aviso httpx/Starlette. Inclui filtros de atraso e janela de vencimento, validação de permissões/destinos, condições de responsável e avisos de mudanças por automação/workflow para observadores.
- `ruff check --no-cache` nos módulos/testes de schema, API, automação, workflow e segurança: **passou**. `npm run lint`: **passou**. `npm run build`: **passou**, bundle principal 585,15 kB com aviso informativo acima de 500 kB. `npm test` com `LOCALAPPDATA` temporário: **3 arquivos e 6 testes passaram**.
- `git diff --check`: **passou**. Endpoints HTTP autenticados e E2E ainda não foram validados neste ambiente Windows.

## Histórico consultável de configuração de campos — 07/11/2026

- `field_config_<id>_<propriedade> CHANGED/WAS` consulta as mudanças por propriedade de campos personalizados. Criação, edição e remoção de campos geram aliases históricos sem depender de JSON específico do banco. Consultas são restritas a administradores; perfis sem esse privilégio recebem erro 403 antes de buscar os cards.
- Migração `0021` cria aliases para configurações históricas existentes; downgrade remove apenas as linhas derivadas, preservando as linhas originais de configuração.
- `.venv\Scripts\python.exe -m pytest backend/tests/test_query_language.py backend/tests/test_field_configuration_history_migration.py backend/tests/test_automation_migration.py -q`: **23 passed**, um aviso de depreciação httpx/Starlette. Ruff nos módulos, migração e testes: **passou**.
- Alembic em SQLite temporário: **upgrade head → downgrade 0020 → upgrade head**, concluído em `0021 (head)`. Emitidos apenas avisos preexistentes sobre constraints CHECK sem nome nas tabelas `tasks` e `sprints`.
- `git diff --check`: **passou**. A chamada autenticada da rota ainda não foi exercitada por HTTP neste ambiente Windows.

## Notificações para mudanças automáticas — 07/11/2026

- A trilha de atividade de workflows e automações agora notifica usuários que acompanham o card, com o mesmo escopo, ator e exclusão do próprio autor das alterações manuais.
- `.venv\Scripts\python.exe -m pytest backend/tests/test_assignee_actions.py backend/tests/test_automation.py backend/tests/test_workflows.py backend/tests/test_notifications.py -q`: **34 passed**, um aviso httpx/Starlette; Ruff nos módulos e testes alterados: **passou**.
- `npm run lint`, `npm run build`, `npm test` e `git diff --check` passaram após as alterações de UI e filtros de prazo; os testes HTTP/E2E ainda não foram validados neste ambiente Windows.

## Filtros avançados em relatórios ágeis — 07/11/2026

- Relatórios de sprint e de release/épico agora recebem `jql=` com a consulta segura compartilhada com o quadro. Os filtros são aplicados antes de calcular os totais e séries. A autorização existente para pesquisa de histórico de configuração continua restrita a administradores.
- `.venv\Scripts\python.exe -m pytest tests/test_agile_reporting.py tests/test_planning_reporting.py tests/test_query_language.py -q`: **28 passed**, 1 aviso conhecido httpx/Starlette. Inclui testes SQLite de filtragem dos indicadores.
- `npm run typecheck`, `npm run lint` e `npm run build`: **passaram**. Bundle principal 595,47 kB, com aviso informativo acima de 500 kB. `npm test -- --run` com `LOCALAPPDATA` em pasta temporária autorizada: **3 arquivos e 6 testes passaram**.
- `git diff --check`: **passou**. Testes HTTP autenticados/E2E continuam pendentes pela limitação ASGI/Windows descrita acima.

## Busca textual ampliada e metadados de integração SCM — 07/11/2026

- `text ~` agora pesquisa título, descrição e valores atuais de campos personalizados. Eventos de webhook armazenam somente metadados normalizados de repositório, branch, commit, PR, estado e ambiente; payloads brutos continuam descartados. A migração `0024` adiciona o campo JSON e tem downgrade reversível.
- `.venv\Scripts\python.exe -m pytest tests/test_integration_helpers.py tests/test_development_event_details_migration.py tests/test_query_language.py tests/test_agile_reporting.py tests/test_planning_reporting.py -q`: **35 passed**, um aviso conhecido httpx/Starlette.
- Suíte Python ampliada, excluindo os testes HTTP conhecidos por travar neste Windows: **83 passed**, um aviso httpx/Starlette.
- `ruff check --no-cache` nos módulos e testes alterados: **passou**. Alembic SQLite temporário: `upgrade head → downgrade 0023 → upgrade head`, final em **0024 (head)**. Os avisos de constraints CHECK sem nome em `tasks` e `sprints` já existiam.
- `npm run typecheck`, `npm run lint`, `npm run build` e `npm test -- --run`: **passaram**; Vitest registrou **3 arquivos e 6 testes**. O bundle principal tem 595,84 kB e gera aviso informativo acima de 500 kB.
- `git diff --check`: **passou**. A cobertura HTTP autenticada e a integração real com provedores externos permanecem pendentes; validações de metadados e migração foram locais.

## Condições de workflow e automação por vínculo — 07/11/2026

- Regras de transição e automações agora filtram por vínculo de release, componente e dependência bloqueadora. Um card é considerado bloqueado quando tem uma dependência `blocks` de um predecessor não concluído; concluir o predecessor libera o critério. Os critérios são booleanos estritos, verificados com consultas no backend.
- `.venv\Scripts\python.exe -m pytest tests/test_link_based_rules.py tests/test_workflows.py tests/test_automation.py tests/test_assignee_actions.py -q`: **35 passed**, um aviso httpx/Starlette. Ruff nos módulos e testes: **All checks passed**.
- Suíte Python ampliada, excluindo testes HTTP conhecidos por travar neste Windows: **85 passed**, um aviso httpx/Starlette.
- `npm run typecheck`, `npm run lint` e `npm run build`: **passaram**. Bundle principal 598,02 kB, com aviso informativo acima de 500 kB.
- A verificação exercitou dados SQLite e regras de serviço; rotas HTTP autenticadas/E2E continuam pendentes pela limitação do ambiente Windows.

## Agrupamentos adicionais de dashboard — 07/11/2026

- Widgets podem agrupar por tipo de card, responsável interno, release, componente, pai e período/situação de prazo, além das dimensões anteriores. A medida `remaining_minutes` mostra `max(estimado − utilizado, 0)` sem participar de custos.
- Grupos de release/componente preservam a cardinalidade muitos-para-muitos: cards com mais de um vínculo aparecem em cada grupo e isso está documentado. Para fornecedor, o agrupamento de hierarquia não serializa título/ID do card pai fora do escopo autorizado.
- `.venv\Scripts\python.exe -m pytest tests/test_dashboard_widget_dimensions.py tests/test_group_sharing.py -q`: **5 passed**, um aviso httpx/Starlette. Ruff nos módulos alterados: **All checks passed**.
- `npm run typecheck`, `npm run lint` e `npm run build`: **passaram**. Bundle principal 598,83 kB, com aviso informativo acima de 500 kB. `git diff --check`: **passou**.
- A execução conjunta com `test_planning_foundation.py` travou no TestClient Windows após cinco testes; foi interrompida e os testes novos foram executados isoladamente. Nenhum resultado HTTP foi declarado.

## Filtros JQL individuais em widgets — 07/11/2026

- Cada widget de dashboard agora salva sua própria consulta JQL e a aplica aos cards depois do escopo de acesso do usuário. Widgets compartilhados não aceitam busca ampla `text ~` nem campos personalizados `field_*`, evitando inferência de conteúdo oculto por contagens agregadas.
- Migração `0025` adiciona `jql` com valor vazio para widgets existentes. Ciclo Alembic em SQLite temporário `upgrade head → downgrade 0024 → upgrade head`: **passou**; foram emitidos avisos conhecidos sobre constraints CHECK sem nome em `tasks` e `sprints`.
- `.venv\Scripts\python.exe -m pytest tests/test_dashboard_widget_query.py tests/test_dashboard_widget_query_migration.py tests/test_dashboard_widget_dimensions.py tests/test_query_language.py -q`: **28 passed**, 1 aviso de depreciação httpx/Starlette.
- `ruff check --no-cache` nos módulos e testes alterados: **passou**. `npm run typecheck`, `npm run lint`, `npm run build`: **passaram**. Vitest: **3 arquivos e 6 testes passaram**. Build mantém aviso informativo por bundle principal de 599,34 kB acima de 500 kB.
- Testes diretos do SQLAlchemy/SQLite validam o filtro e a autorização; cobertura autenticada HTTP/E2E ainda está pendente pela limitação do TestClient/ASGI Windows descrita acima.

## Funções JQL contextuais e datas relativas — 07/11/2026

- JQL resolve `assignee = currentUser()` usando o ID da sessão autenticada e `sprint in openSprints()`/`closedSprints()` usando estados não arquivados. `due` e `created` aceitam `now()`, início/fim de dia, semana, mês e ano em UTC, com deslocamento de dias, semanas, meses e anos.
- As funções são aplicadas às consultas de cards, assinaturas, widgets e relatórios de sprint/release/épico; sem ator autenticado, `currentUser()` é recusado. Nenhum trecho de expressão do usuário é executado.
- `.venv\Scripts\python.exe -m pytest tests/test_query_language.py tests/test_dashboard_widget_query.py tests/test_agile_reporting.py tests/test_planning_reporting.py tests/test_filter_subscriptions.py -q`: **38 passed**, 1 aviso conhecido httpx/Starlette. Inclui execução das consultas em SQLite, isolamento de `currentUser()`, estados de sprint, fronteiras UTC e deslocamento de mês.
- `ruff check --no-cache` nos módulos e testes de consulta, dashboard, assinaturas e relatórios: **passou**. A suíte de frontend não foi repetida porque esta etapa não alterou código frontend; typecheck, lint, build e Vitest passaram na etapa anterior.
- A paridade da JQL permanece parcial; este incremento não implementa funções, operadores ou entidades ainda listados como ausentes.

## Relatório hierárquico de épicos e privacidade — 07/11/2026

- O relatório de épico percorre descendentes em todos os níveis, informa tipo e card pai, e mantém os indicadores filtrados pela JQL.
- Consultas de fornecedor agora recusam filtros de hierarquia; o payload também oculta o ID de um pai fora do escopo daquele fornecedor.
- `.venv\\Scripts\\python.exe -m pytest tests/test_planning_reporting.py tests/test_query_language.py tests/test_reporting_jql.py tests/test_hierarchy_privacy.py -q`: **33 passaram**, com um aviso conhecido de depreciação httpx/Starlette.
- `ruff check` nos módulos e testes tocados: **passou** (o Ruff avisou que não conseguiu gravar cache local por permissão; a análise terminou sem erros). `git diff --check`: **passou**.
- `npm run typecheck`, `npm run lint` e `npm run build`: **passaram**. Bundle principal 600,53 kB, com aviso informativo acima de 500 kB. `npm test -- --run`: **3 arquivos e 6 testes passaram**.
- A tabela de épico na interface agora mostra tipo e card pai. Testes HTTP autenticados/E2E não foram repetidos nesta etapa.

## Intervalo JQL em consultas históricas — 07/11/2026

- `CHANGED` e `WAS` aceitam `DURING (início, fim)` para filtrar o instante das alterações; datas incluem o dia inteiro em UTC e timestamps ISO 8601 permitem intervalos precisos. `WAS NOT`/`WAS NOT IN` selecionam somente cards com histórico no escopo e sem nenhum dos valores listados. Combinar `DURING` com `AFTER`/`BEFORE` é recusado.
- `.venv\\Scripts\\python.exe -m pytest tests/test_query_language.py tests/test_reporting_jql.py tests/test_agile_reporting.py tests/test_planning_reporting.py -q`: **40 passaram**, com um aviso conhecido de depreciação httpx/Starlette. Ruff nos módulos e testes de consulta: **passou**.
- Testes cobrem WAS/CHANGED, autor, dias inclusivos, instantes ISO, fora do intervalo, datas inválidas e limites invertidos; nenhum backend externo foi usado.

## Ações de observador em workflows e automações — 07/11/2026

- Workflows por transição/tipo e automações podem adicionar um observador interno ativo ao card. A ação é registrada em auditoria, participa das notificações existentes e é idempotente; contas de fornecedor/inativas não podem ser selecionadas ou aplicadas.
- `.venv\\Scripts\\python.exe -m pytest tests/test_automation.py tests/test_workflows.py tests/test_notifications.py -q`: **28 passaram**, com um aviso conhecido de depreciação httpx/Starlette. Ruff nos módulos e testes tocados: **passou**.
- `npm run typecheck`, `npm run lint`, `npm run build`: **passaram**; bundle principal 601,11 kB, com aviso informativo acima de 500 kB. `npm test -- --run` com `LOCALAPPDATA` em diretório temporário autorizado: **3 arquivos e 6 testes passaram**.
- `git diff --check`: **passou**. Testes HTTP autenticados/E2E não foram executados nesta etapa.

## Webhooks de desenvolvimento como gatilho de automação — 07/11/2026

- Eventos assinados GitHub/GitLab/Bitbucket agora podem acionar automações filtradas por provedor, tipo de evento e estado normalizado. O evento é gravado e a regra roda na mesma transação; a restrição única por provedor/entrega/card impede reaplicação em reenvios concorrentes. Auditoria usa a conta autora da regra e registra o contexto normalizado, sem guardar o payload bruto.
- `.venv\\Scripts\\python.exe -m pytest tests/test_development_automations.py tests/test_automation.py tests/test_integration_helpers.py -q`: **25 passaram**, com um aviso conhecido de depreciação httpx/Starlette. Ruff nos módulos e testes tocados: **passou**.
- `npm run typecheck`, `npm run lint`, `npm run build`: **passaram**; bundle principal 602,76 kB, com aviso informativo acima de 500 kB. `npm test -- --run` com `LOCALAPPDATA` em diretório temporário autorizado: **3 arquivos e 6 testes passaram**.
- Testes HTTP com assinatura real continuam pendentes devido à limitação ASGI/Windows registrada neste documento; o serviço de persistência/automação foi testado em SQLite.

## Ordenação JQL composta — 07/11/2026

- `ORDER BY` aceita até cinco campos allowlisted com direção individual, incluindo `id`; sem filtro pode ordenar todos os cards. O ID crescente é desempate padrão, salvo quando o próprio ID já foi especificado.
- `.venv\\Scripts\\python.exe -m pytest tests/test_query_language.py tests/test_reporting_jql.py tests/test_agile_reporting.py tests/test_planning_reporting.py -q`: **43 passaram**, com um aviso conhecido de depreciação httpx/Starlette. A consulta foi executada em SQLite para validar a ordenação por data, prioridade e ID; filtros repetidos/não permitidos foram recusados.
- Ruff nos módulos e testes JQL: **passou**. `git diff --check`: **passou**.

## Pesquisa JQL em comentários — 07/11/2026

- `comment ~ "termo"` pesquisa comentários somente do card avaliado; `text ~ "termo"` também passou a considerar comentários além de título, descrição e campos personalizados. As consultas continuam subordinadas ao escopo de segurança do conjunto de cards.
- `.venv\\Scripts\\python.exe -m pytest tests/test_query_language.py tests/test_reporting_jql.py tests/test_agile_reporting.py tests/test_planning_reporting.py -q`: **43 passaram**, com um aviso conhecido de depreciação httpx/Starlette. Ruff nos módulos e testes JQL: **passou**.

## Filtros JQL por observador — 07/11/2026

- `watcher = currentUser()`/`!= currentUser()` resolvem o usuário autenticado; usuários internos podem filtrar IDs com `=`, `!=`, `IN` e `NOT IN`, além de consultar `IS EMPTY`/`IS NOT EMPTY`.
- Fornecedores podem usar `=`, `!=`, `IN` e `NOT IN` somente com `currentUser()`; busca por IDs e teste de ausência de observadores são recusados para evitar inferir a atividade de terceiros. O filtro permanece correlacionado ao ID do card.
- `.venv\\Scripts\\python.exe -m pytest tests/test_query_language.py tests/test_reporting_jql.py tests/test_agile_reporting.py tests/test_planning_reporting.py -q`: **44 passaram**, com um aviso conhecido de depreciação httpx/Starlette. Ruff nos módulos alterados: **All checks passed**. `git diff --check`: **passou** (avisos do Git apenas sobre conversão de LF para CRLF em arquivos já modificados).

## Função JQL `membersOf()` — 07/11/2026

- `assignee`, `creator`/`reporter` e `watcher` aceitam `IN`/`NOT IN membersOf("Nome")` ou `membersOf(id:<número>)`; só grupos e contas internas ativos participam. `creator = currentUser()` e `reporter = currentUser()` são resolvidos com a identidade autenticada. Fornecedor recebe 403 para `membersOf()`.
- `.venv\\Scripts\\python.exe -m pytest tests/test_query_language.py tests/test_reporting_jql.py tests/test_agile_reporting.py tests/test_planning_reporting.py -q`: **45 passaram**, com um aviso conhecido de depreciação httpx/Starlette. Ruff nos módulos de JQL/testes: **All checks passed**.
- Cobertura inclui nome/ID de grupo, assignee/creator/reporter/watcher, `NOT IN`, currentUser, grupo inativo e bloqueio de fornecedor. `git diff --check`: **passou**; avisos Git apenas indicam conversão CRLF em arquivos já modificados.

## Filtro JQL de anexos — 07/11/2026

- `attachments IS EMPTY`/`IS NOT EMPTY` verificam anexos vinculados ao card por consulta de existência correlacionada. Valores e operadores incompatíveis com o tipo são rejeitados.
- `.venv\\Scripts\\python.exe -m pytest tests/test_query_language.py tests/test_reporting_jql.py tests/test_agile_reporting.py tests/test_planning_reporting.py -q`: **47 passaram**, com um aviso conhecido de depreciação httpx/Starlette.
- Ruff nos módulos/testes JQL: **All checks passed**. `git diff --check`: **passou**; avisos Git apenas indicam conversão CRLF em arquivos já modificados.

## Gatilhos de automação de comentário/anexo — 07/11/2026

- `.venv\\Scripts\\python.exe -m pytest tests/test_automation.py tests/test_collaboration_automations.py tests/test_notifications.py -q`: **25 passaram**, com um aviso conhecido de depreciação httpx/Starlette.
- Testes confirmam disparo ao gravar comentário/anexo, execução única quando a regra cria comentário, metadados mínimos no evento e ausência de corpo/nome privado no registro de automação.
- A leitura multipart assíncrona do endpoint de anexo não foi exercitada nesta rodada: o fixture AnyIO do runner Windows não iniciou o corpo do teste. O helper síncrono chamado pelo endpoint foi testado; a cobertura HTTP/multipart segue pendente, conforme limitações do ambiente.
- `npm.cmd run build`: **passou** (602,99 kB no bundle principal; aviso informativo do Vite acima de 500 kB). `npm.cmd run lint`: **passou**. `npm.cmd test`: não iniciou; Vitest não conseguiu criar o token em `%LOCALAPPDATA%\Packages\sandbox...\vitest\.vitest-secret-token` nem em `frontend/node_modules/.vitest/.vitest-secret-token`, falhando antes de coletar os testes.
- Ruff nos módulos/testes Python alterados: **All checks passed**. `git diff --check`: **passou**, com avisos do Git sobre conversão de LF para CRLF em arquivos já modificados.

## Condições de automação para comentários/anexos — 07/11/2026

- `comment_contains` aceita texto literal de 1–200 caracteres e só com `comment_added`; comparação case-insensitive. `attachment_media_types` aceita um a quatro tipos únicos entre PDF, PNG, JPEG e texto simples e só com `attachment_added`.
- A mesma suíte focada passou com **25 testes**; cobertura valida conteúdo correspondente/não correspondente, tipos permitidos/não permitidos, gatilho incompatível e metadados de execução sem armazenar corpo/nome.
- `npm.cmd run build`: **passou**, bundle principal 604,20 kB (aviso informativo Vite acima de 500 kB). `npm.cmd run lint`: **passou**. `npm.cmd test` não iniciou: mesmo redirecionando `LOCALAPPDATA` para `os-manager/tmp`, Vitest falhou antes da coleta ao criar `.vitest-secret-token` no diretório temporário ou em `frontend/node_modules/.vitest`.
- Ruff nos módulos Python alterados: **All checks passed**. `git diff --check`: **passou**; persistem avisos Git de CRLF em arquivos previamente modificados.

## Campo JQL `updated` — 07/11/2026

- `updated`/`updatedDate` usam o último `Audit.created_at` correlacionado ao card, com fallback para `Task.created_at`; igualdade por data seleciona o dia UTC inteiro. O campo aceita comparações, `IN`/`NOT IN`, funções relativas existentes e ordenação.
- `.venv\\Scripts\\python.exe -m pytest tests/test_query_language.py -q`: **39 passaram**, com um aviso conhecido httpx/Starlette. Teste valida atualização por comentário/status, fallback para card sem edição, filtro por dia, intervalo relativo e ordem composta.
- Suíte combinada de JQL e relatórios (`test_query_language`, `test_reporting_jql`, `test_agile_reporting`, `test_planning_reporting`): **48 passaram**, com um aviso httpx/Starlette. Ruff nos arquivos JQL: **All checks passed**.

## JQL em relatórios operacionais e dashboard — 07/11/2026

- A consulta avançada agora filtra registros operacionais antes de calcular indicadores, séries por sprint, prévias e exportações Excel/PDF/HTML. É combinada com escopo do usuário, status, período, sprint, fornecedor, filtros de campos e filtros analíticos. O JQL geral do painel também é aplicado junto ao JQL individual de cada widget.
- `.venv\Scripts\python.exe -m pytest tests/test_reporting_jql.py tests/test_dashboard_widget_query.py tests/test_query_language.py -q`: **27 passed**, 1 aviso conhecido httpx/Starlette. A cobertura direta confirma interseção por prioridade/responsável autenticado e consulta no serviço SQL de relatórios.
- Ruff nos módulos alterados: **passou**. `npm run typecheck`, `npm run lint`, `npm run build` e Vitest (**3 arquivos, 6 testes**) passaram. Build gera aviso informativo: bundle principal 600,17 kB, acima de 500 kB.
- Uma tentativa do teste HTTP autenticado que cobre análise/dashboard/export ficou sem resposta no TestClient deste Windows por 45 segundos e foi interrompida. A cobertura HTTP permanece pendente; os resultados de serviço e frontend não são apresentados como validação HTTP.

## Busca JQL de cards ligados — 07/11/2026

- `issue IN linkedIssues("OS-123")` agora localiza os cards ligados em qualquer direção; o argumento opcional limita o tipo a `blocks`, `relates` ou `duplicates`. Aceita a chave legível `OS-<id>` ou ID numérico, sem SQL livre ou avaliação dinâmica. A busca é restrita a perfis internos e permanece subordinada ao escopo de acesso existente, evitando que fornecedores testem vínculos de cards alheios.
- `.venv\Scripts\python.exe -m pytest tests/test_query_language.py tests/test_reporting_jql.py tests/test_link_based_rules.py tests/test_dashboard_widget_query.py tests/test_agile_reporting.py tests/test_planning_reporting.py tests/test_filter_subscriptions.py -q`: **42 passed**, 1 aviso conhecido httpx/Starlette. Casos cobrem direção, filtro por tipo, negação e rejeição de sintaxe/campos inválidos em SQLite.
- A cobertura HTTP autenticada segue pendente pela limitação do TestClient/ASGI Windows registrada acima.

## Autoria e data de horas na JQL — 07/11/2026

- `worklogAuthor` aceita `=`, `!=`, `IN` e `NOT IN`, usuário autenticado (`currentUser()`) e nomes explícitos; consulta as versões persistidas de horas sem alterar apontamentos. `worklogDate` aceita data, listas e funções de data UTC já allowlisted. Fornecedores só conseguem consultar a própria autoria.
- `.venv\Scripts\python.exe -m pytest tests/test_query_language.py tests/test_reporting_jql.py tests/test_dashboard_widget_query.py -q`: **45 passaram**, 1 aviso conhecido de depreciação httpx/Starlette.
- Ruff nos módulos e testes JQL alterados: **All checks passed**. Cobertura inclui comparação de autores, listas, exclusão, identidade autenticada, data UTC por dia e intervalo e rejeição de operadores/contexto inválidos.

## Comentários versionados de apontamentos — 07/11/2026

- `HoursInput` aceita comentário opcional de até 1.000 caracteres. Cada edição cria uma nova versão imutável; `worklogComment ~ "texto"` consulta todas as versões. `GET /tasks/{id}/hours` e a seção Histórico de apontamentos exibem versões/horários/comentários com paginação de 50 (API até 200). Fornecedor vê apenas versões e comentários próprios, depois de validar que o card continua atribuído a ele.
- Migração Alembic `0026` adiciona a coluna nullable sem alterar versões anteriores; downgrade remove a coluna. Testes de migração verificam legado sem comentário, escrita, leitura e downgrade.
- `.venv\Scripts\python.exe -m pytest tests/test_query_language.py tests/test_worklog_comment_migration.py tests/test_hierarchy_privacy.py tests/test_reporting_jql.py tests/test_dashboard_widget_query.py -q`: **47 passaram**, com um aviso conhecido de depreciação httpx/Starlette. Inclui consulta por comentários históricos e garantia de que fornecedor não recebe comentário da versão atual criada por outra conta.
- Ruff nos módulos e testes tocados: **All checks passed**. `npm.cmd run typecheck`, `npm.cmd run lint` e `npm.cmd run build`: **passaram**; build Vite reportou bundle principal de 605,64 kB (aviso informativo acima de 500 kB).
- `DATABASE_URL=sqlite:///:memory: alembic upgrade head`: **passou** desde esquema vazio até a revisão `0026`; Alembic reportou dois avisos preexistentes sobre constraints CHECK sem nome nas tabelas `sprints` e `tasks`. `alembic heads`: `0026 (head)`.

## Automação condicionada a campos do card — 07/11/2026

- Automações aceitam até dez valores do schema individual; workflows podem exigir igualdade/desigualdade por ID do campo. Tipos escalares são preservados (booleano não equivale a número), campos ausentes não correspondem e valores não são gravados na auditoria. O planejamento permite configurar ambas as regras por interface; nenhum código ou expressão é executado.
- `.venv\Scripts\python.exe -m pytest tests/test_automation.py tests/test_development_automations.py tests/test_workflows.py -q`: **37 passaram**, 1 aviso conhecido httpx/Starlette. Ruff para schemas, motores de automação/workflow e testes: **All checks passed**.
- `npm.cmd run typecheck`, `npm.cmd run lint` e `npm.cmd run build`: **passaram**; bundle principal 609,03 kB (aviso informativo Vite acima de 500 kB).

## Filtros JQL por nome de usuário — 07/11/2026

- `assignee`, `creator`/`reporter` e `watcher` aceitam nomes exatos além de IDs; listas `IN`/`NOT IN` podem combinar ambos. Nome inexistente não encontra cards, e a regra de fornecedor continua limitando watcher a `currentUser()`.
- `.venv\Scripts\python.exe -m pytest backend/tests/test_query_language.py -q`: **42 passed**, 1 aviso conhecido httpx/Starlette.
- `.venv\Scripts\python.exe -m ruff check backend/app/query_language.py backend/tests/test_query_language.py`: **All checks passed**. `git diff --check`: **passou**, com avisos de normalização CRLF do Git em arquivos já alterados.

## Dashboards independentes — 07/11/2026

- Dashboards podem ser criados, renomeados e removidos quando vazios. Widgets existentes são associados ao padrão “Visão geral”; painéis compartilhados só aparecem quando há widget autorizado e são somente leitura. Fornecedores não listam nem criam widgets de relatório pela API.
- `.venv\Scripts\python.exe -m pytest backend/tests/test_dashboard_migration.py backend/tests/test_dashboard_containers.py backend/tests/test_dashboard_widget_dimensions.py backend/tests/test_dashboard_widget_order_migration.py backend/tests/test_dashboard_widget_query.py -q`: **9 passed**, 1 aviso conhecido httpx/Starlette.
- `DATABASE_URL=sqlite:///:memory: alembic upgrade head` e `alembic heads`: **passaram**, revisão `0027 (head)`. Persistem dois avisos preexistentes sobre constraints CHECK sem nome em `sprints` e `tasks`.
- Ruff nos módulos e testes alterados: **All checks passed**; `git diff --check`: **passou**, com avisos de normalização CRLF em arquivos já modificados.
- `npm.cmd run typecheck`, `npm.cmd run lint` e `npm.cmd run build`: **passaram**. Build mantém aviso Vite para bundle principal acima de 500 kB (611,75 kB).

## Capacidade por equipe — 07/11/2026

- Cadastro de capacidade aceita fornecedor, pessoa interna ou equipe. Equipe exige membros internos ativos e salva seus IDs como snapshot; a demanda é derivada dos cards ativos atribuídos aos membros do snapshot e distribuída pelos dias úteis planejados.
- `.venv\Scripts\python.exe -m pytest backend/tests/test_capacity_reporting.py backend/tests/test_team_capacity_migration.py -q`: **3 passed**, 1 aviso conhecido httpx/Starlette. Inclui remoção posterior de membro sem alterar o cálculo histórico, resource XOR e upgrade/downgrade da migração com proteção contra perda de períodos de equipe.
- `DATABASE_URL=sqlite:///:memory: alembic upgrade head` e `alembic heads`: **passaram**, `0028 (head)`. Persistem dois avisos preexistentes sobre constraints CHECK sem nome em `sprints` e `tasks`.
- Ruff nos módulos e testes alterados: **All checks passed**; `git diff --check`: **passou**, com avisos de normalização CRLF em arquivos já modificados.
- `npm.cmd run typecheck`, `npm.cmd run lint` e `npm.cmd run build`: **passaram**; bundle principal 612,35 kB (aviso Vite acima de 500 kB).

## Condições relativas de prazo em workflows — 07/11/2026

- As condições configuráveis de transição agora incluem prazo vencido e prazo nos próximos/fora dos próximos N dias. A janela é inclusiva, usa a data UTC, aceita 0–3.650 dias e considera card sem prazo fora da janela; prazo vencido ignora cards concluídos.
- `.venv\Scripts\python.exe -m pytest backend/tests/test_workflows.py -q`: **13 passed**, 1 aviso conhecido httpx/Starlette. Ruff nos módulos e testes alterados: **All checks passed**.
- `npm.cmd run typecheck`, `npm.cmd run lint` e `npm.cmd run build`: **passaram**; bundle principal 612,97 kB (aviso Vite acima de 500 kB).

## Listas e composição da sprint — 07/11/2026

- O relatório ágil separa cards concluídos e não concluídos; em sprint encerrada, título, status e estimativa são lidos do snapshot de encerramento. Também identifica cards incluídos após o início, comparando inclusões auditadas com os IDs registrados no evento de início. Não retorna tarifas ou custos.
- `.venv\\Scripts\\python.exe -m pytest tests/test_agile_reporting.py -q`: **7 passed**, 1 aviso conhecido de depreciação httpx/Starlette.
- `.venv\\Scripts\\python.exe -m ruff check app/agile_reporting.py tests/test_agile_reporting.py`: **All checks passed**.
- `npm.cmd run typecheck`, `npm.cmd run lint` e `npm.cmd run build`: **passaram**; bundle principal 613,79 kB (aviso Vite acima de 500 kB).
- `git diff --check`: **passou**; Git emitiu apenas avisos de normalização LF/CRLF em arquivos previamente modificados.

## Burndown de esforço e mudanças de escopo — 07/11/2026

- Relatório ágil passou a reconstruir horas restantes e escopo estimado por dia. A inclusão registra a estimativa do card e o início da sprint salva IDs e estimativas comprometidos; revisões posteriores são obtidas do histórico de envio de horas. Sprints antigas sem snapshot inicial usam estimativa atual aproximada, explicitada na definição do indicador.
- `.venv\\Scripts\\python.exe -m pytest tests/test_agile_reporting.py -q`: **8 passed**, 1 aviso conhecido de depreciação httpx/Starlette.
- Ruff nos módulos e testes alterados, `npm.cmd run typecheck`, `npm.cmd run lint` e `npm.cmd run build`: **passaram**; bundle principal 614,53 kB (aviso Vite acima de 500 kB).
- `git diff --check`: **passou**; Git emitiu avisos de normalização LF/CRLF em arquivos preexistentes modificados.

## Filtro de autoria de comentários — 07/11/2026

- O JQL compatível aceita `commentAuthor = currentUser()`, nomes e listas `IN`/`NOT IN`. A restrição para fornecedores bloqueia autorias de terceiros no servidor.
- `.venv\\Scripts\\python.exe -m pytest tests/test_query_language.py -q`: **43 passed**, 1 aviso conhecido de depreciação httpx/Starlette.
- `.venv\\Scripts\\python.exe -m ruff check app/query_language.py tests/test_query_language.py`: **All checks passed**. `git diff --check`: **passou**, com avisos Git de normalização LF/CRLF em arquivos previamente modificados.

## Filtros de comentários por data — 07/11/2026

- `commentDate` suporta igualdade por dia UTC, comparações, `IN`/`NOT IN` e funções relativas como `startOfWeek()`. É independente de `worklogDate`.
- `.venv\\Scripts\\python.exe -m pytest tests/test_query_language.py -q`: **43 passed**, 1 aviso conhecido de depreciação httpx/Starlette.
- `.venv\\Scripts\\python.exe -m ruff check app/query_language.py tests/test_query_language.py`: **All checks passed**; `git diff --check`: **passou**, com os avisos de normalização LF/CRLF dos arquivos já alterados.

## Ação de remover etiquetas em workflows e automações — 07/11/2026

- A ação remove pelo texto sem diferenciar caixa, preserva outras etiquetas e não grava evento se não houver alteração. Está disponível no editor de workflows e no construtor de sequências de automação.
- `.venv\\Scripts\\python.exe -m pytest tests/test_workflows.py tests/test_automation.py -q`: **38 passed**, 1 aviso conhecido de depreciação httpx/Starlette.
- `.venv\\Scripts\\python.exe -m ruff check app/schemas.py app/workflows.py app/automation.py tests/test_workflows.py tests/test_automation.py`: **All checks passed**; `npm.cmd run typecheck`, `npm.cmd run lint` e `npm.cmd run build`: **passaram**. Bundle principal 614,91 kB (aviso Vite acima de 500 kB).
- `git diff --check`: **passou**, com avisos de normalização LF/CRLF em arquivos já modificados.

## Gatilho de automação por alteração de responsável — 07/11/2026

- `assignee_changed` é acionado após edição que muda o responsável interno ou fornecedor. A mesma edição mantém o gatilho `task_updated`; ações executadas não reinvocam `assignee_changed`.
- `.venv\\Scripts\\python.exe -m pytest tests/test_automation.py -q`: **26 passed**, 1 aviso conhecido de depreciação httpx/Starlette.
- Ruff nos módulos e testes alterados, `npm.cmd run typecheck`, `npm.cmd run lint` e `npm.cmd run build`: **passaram**; bundle principal 615,06 kB (aviso Vite acima de 500 kB).

## Novos gadgets de tempo de resolução — 07/11/2026

- Dashboards agora oferecem agrupamento por mês de resolução e tempo médio até conclusão, calculados a partir da auditoria mais recente de transição para concluído; reaberturas passam a usar a conclusão mais recente. Cards sem evento de resolução auditado não contaminam os indicadores.
- `tests/test_dashboard_widget_dimensions.py tests/test_planning_foundation.py`: **14 passed**; a suíte backend completa `pytest --ignore=tests/test_deployment.py -q --show-capture=no`: **196 passed** naquele incremento.
- Frontend: `npm run typecheck`, `npm run lint`, `npm test -- --run` (**3 arquivos, 6 testes**) e `npm run build`: passaram. Build informa chunk principal de 616 kB após minificação.
- Ruff nos módulos e testes alterados: passou. `git diff --check`: passou.
- O gadget de fluxo agora compara criação e conclusão atual em linha mensal e completa meses sem atividade com zero; a métrica respeita os mesmos filtros e o escopo já aplicado ao dashboard.

## Recomendações de nivelamento de capacidade — 07/11/2026

- A previsão mantém a distribuição atual e acrescenta um cenário que desloca minutos previstos de dias sobrecarregados para dias livres dentro da janela de cada card. Cada recomendação identifica card, minutos e datas; os registros das tarefas não são alterados.
- `tests/test_capacity_reporting.py`: **3 passed**. Inclui caso em que o cenário elimina uma sobrecarga de 30 minutos e prova que as datas dos cards permanecem iguais. Ruff, `npm run typecheck` e `npm run lint`: passaram.
- `python -m pytest --ignore=tests/test_deployment.py -q --show-capture=no`: **197 passed**. Vitest (**3 arquivos, 6 testes**) e build passaram; o bundle principal ficou em 617,98 kB. Typecheck, lint, Ruff e `git diff --check` passaram.

## Aplicação versionada de nivelamento de capacidade — 07/11/2026

- Gestores com `manage_capacity` podem gravar uma redistribuição como versão auditada da previsão diária. Um contador inteiro com atualização condicional evita sobrescrever silenciosamente uma aplicação concorrente. A previsão retorna ao cálculo base e sinaliza plano desatualizado quando a capacidade, período, equipe congelada, prazo, início, estimativa ou versão de qualquer card de origem muda.
- A aplicação do plano só altera o cenário diário do registro de capacidade; prazos dos cards, horas utilizadas e custos não mudam. Cada aplicação registra autor, instante, entradas de origem e movimentos, além de evento de auditoria.
- `tests/test_capacity_reporting.py`: **3 passed**, incluindo aplicação da redistribuição, manutenção das datas e estimativas dos cards, recusa de reaplicação com versão antiga e detecção de origem desatualizada. Ruff dos arquivos Python tocados passou. Vitest completo: **5 arquivos, 19 testes passaram**.
- Typecheck, ESLint e build de produção passaram; a compilação Vite mantém o aviso conhecido do chunk principal acima de 500 kB. A suíte backend completa e o teste E2E não foram repetidos neste incremento.
- Alembic executado em banco SQLite temporário isolado: `upgrade head` → revisão **0034**, `downgrade -1` → revisão **0033**, novo `upgrade head` → revisão **0034**. As migrações antigas emitiram avisos conhecidos sobre constraints sem nome nas tabelas `sprints` e `tasks`; não impediram upgrade/downgrade.

## Exportação de calendário iCalendar — 07/11/2026

- A visualização de calendário permite baixar `.ics` com os cards atualmente visíveis. A API recebe IDs únicos limitados a 5.000, reconsulta cada atividade dentro do escopo autenticado e emite somente título, chave e data de prazo; datas são eventos de dia inteiro, texto é escapado contra injeção iCalendar e dados financeiros não são serializados.
- `tests/test_calendar_export.py`: **2 passed**. Cobertura confirma ocultação de card pertencente a outro fornecedor, exclusão de card sem prazo, escaping de delimitadores/quebras de linha e rejeição de listas duplicadas ou acima do limite. Ruff nos arquivos backend alterados passou.
- Backend `test_calendar_export.py` + `test_capacity_reporting.py`: **5 passed**. Vitest completo: **5 arquivos, 20 testes passaram**, incluindo acionamento do botão Exportar .ics. E2E com frontend/backend locais e banco SQLite descartável: **1 passed**, validando login, visualização de calendário e download `.ics`. Typecheck, ESLint e build de produção passaram; permanece o aviso conhecido do bundle principal acima de 500 kB. Não há assinatura contínua com Google/Outlook: a importação é manual e não há sincronização bidirecional.

## Gadget de tempo médio na etapa atual — 07/11/2026

- O construtor de dashboards permite agrupar a medida `avg_current_status_days` por dimensões existentes. A medida deriva o início corrente do último evento `status_changed` cujo destino coincide com o estado atual; quando não existe evento compatível, usa a criação do card. Aplica a JQL do widget/painel e o escopo de acesso antes de calcular a média, com uma casa decimal.
- `tests/test_dashboard_widget_dimensions.py`, `test_dashboard_widget_query.py` e `test_dashboard_containers.py`: **10 passed**. Inclui cálculo auditado, fallback para criação, valor agregado e efeito de filtro JQL.
- Vitest completo: **5 arquivos, 20 testes passaram**; Ruff, typecheck, ESLint e build de produção passaram. O build mantém o aviso conhecido de bundle acima de 500 kB. Não foi executado E2E específico do construtor de gadgets nesta mudança.

## Ações de workflow e automação para campos personalizados — 07/11/2026

- `set_custom_fields` valida campos escalares existentes e papel autorizado, cria uma nova versão de valores e registra o diff em auditoria e histórico normalizado. A filtragem do histórico preserva `visible_to` mesmo se a definição do campo for removida depois.
- Testes focados: `pytest tests/test_workflows.py tests/test_automation.py tests/test_audit_trail.py -k "workflow_action_versions or automation_can_version or audit_custom_field or workflow_conditions_and_actions_are_validated" -q`: **4 passed, 46 deselected**. O conjunto de workflows e automações antes do último teste de automação: **46 passed**.
- Frontend: `npm run typecheck`, ESLint e build passaram; Vitest: **3 arquivos, 6 testes passaram** após fornecer token temporário local. O build produziu bundle principal de 619,78 kB e o aviso conhecido de chunk acima de 500 kB.
- Ruff dos módulos e testes tocados passou; exibiu avisos de acesso negado apenas ao atualizar cache Ruff. `git diff --check` passou, com avisos do Git para normalização LF/CRLF.
- A execução da suíte backend completa foi iniciada, mas ficou sem saída até ser interrompida; portanto, **não está validada nesta alteração**. Os testes focados acima passaram.

## Gadget de matriz em dashboards — 07/11/2026

- Migração `0029` adiciona uma segunda dimensão opcional para widgets antigos. Widgets `matrix` exigem duas dimensões diferentes; a API retorna células cruzadas, calculadas depois dos filtros do painel, do widget e do escopo autorizado.
- `.venv\Scripts\python.exe -m pytest tests/test_dashboard_widget_dimensions.py tests/test_dashboard_widget_matrix_migration.py -q`: **6 passed**. Teste HTTP autenticado do endpoint `test_dashboard_matrix_widget_returns_filtered_cross_tab_data`: **1 passed, 9 deselected**; foi executado com permissão de rede local porque o sandbox bloqueia o socket de `TestClient`.
- Migração aplicada a um arquivo SQLite temporário isolado: `alembic upgrade head` e `alembic current` confirmaram a revisão **0029 (head)**. Alembic exibiu dois avisos sobre constraints sem nome em tabelas antigas (`sprints` e `tasks`), sem impedir a atualização.
- Frontend: typecheck, ESLint e build passaram. Vitest: **3 arquivos, 6 testes passaram**. Bundle principal 622,25 kB; permanece o aviso do Vite para chunks acima de 500 kB.
- Ruff dos módulos e testes alterados: **All checks passed** (o processo avisou que não conseguiu atualizar o cache local Ruff). A suíte backend completa não foi executada novamente neste incremento.

## Filtro JQL por categoria de status — 07/11/2026

- `statusCategory` foi adicionado à consulta allowlistada para filtros por To Do, In Progress e Done, aliases em português, `IN`/`NOT IN` e ordenação ASC/DESC. Colunas customizadas entram na categoria conforme `workflow_order` relativo à coluna `production`; `done` continua sendo a categoria de conclusão estrutural.
- `.venv\Scripts\python.exe -m pytest tests/test_query_language.py -q`: **46 passed**. Inclui coluna customizada, filtros por cada categoria, listas, negação, ordenação e rejeição de categoria/operador inválidos.
- Teste HTTP autenticado `test_tasks_api_accepts_status_category_query`: **1 passed, 10 deselected**; confirmou o filtro To Do na rota `/tasks` e a exclusão do mesmo card da categoria In Progress.
- Ruff nos arquivos Python alterados: **All checks passed** (avisos conhecidos impedem atualizar o cache Ruff dentro do sandbox). `git diff --check` passou; o Git emitiu somente avisos de normalização LF/CRLF em arquivos preexistentes.
- Frontend: `npm run typecheck`, `npm run lint`, Vitest (**3 arquivos, 6 testes**) e `npm run build` passaram. Build informa bundle principal de 622,46 kB e mantém o aviso conhecido de chunk acima de 500 kB.

## JQL `fixVersion` por nome — 07/11/2026

- A busca avançada aceita `fixVersion`/`fix_version` como alias Jira de release e preserva os filtros existentes por ID. `release` e `component` também podem ser consultados por nome exato; listas reconhecem vírgulas dentro de valores entre aspas.
- Teste SQLite `test_fixversion_jql_resolves_exact_release_names_and_keeps_id_support` cobre igualdade por nome, alias sem distinção de caixa, lista mista de nomes, ID, `NOT IN` incluindo card sem vínculo e nome inexistente.
- Marketplace continua fora do escopo, conforme decisão do usuário.

## JQL por nome de sprint — 07/11/2026

- `sprint` aceita nomes exatos e IDs em igualdade e listas, mantendo as funções de sprint já disponíveis. `NOT IN` inclui cards sem sprint correspondente.
- Teste SQLite cobre nome, lista de nomes, ID, `openSprints()` e ausência de sprint.

## Notificações opcionais por e-mail — 07/11/2026

- Adicionadas preferências de e-mail por conta e migração Alembic `0030`, com fila durável, idempotência por notificação, estado de entrega, até cinco tentativas com backoff e revalidação de acesso do destinatário no instante do envio. A interface permite alterar as preferências no painel de notificações.
- SMTP e URL pública são opcionais por ambiente (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_STARTTLS`, `SMTP_SSL`, `APP_PUBLIC_URL`). Sem SMTP configurado, as notificações internas seguem funcionando e a opção de envio fica indisponível.
- As mensagens SMTP são genéricas: não incluem chave/título do card, autor ou conteúdo; fornecedores só recebem e-mail se ainda puderem acessar a atividade. Endereços são autodeclarados e não verificados; homologação institucional deve exigir política de confirmação antes de uso real.
- `.venv\Scripts\python.exe -m pytest tests\test_email_notifications.py tests\test_email_notifications_migration.py tests\test_audit_trail.py tests\test_filter_subscriptions.py -q`: **12 passed**. `tests\test_notifications.py`: **2 passed** com sockets locais autorizados (inclui isolamento por usuário e SMTP ausente).
- `alembic upgrade head` e `alembic current` em arquivo SQLite temporário: **revisão 0030 (head)**. Alembic emitiu somente avisos preexistentes sobre constraints sem nome em `sprints` e `tasks` durante migrações históricas.
- Ruff nos módulos e migração: **All checks passed**. Typecheck e lint do frontend passaram. Vitest: 3 arquivos e 6 testes passaram. Build de produção passou; bundle principal 624,18 kB e aviso Vite acima de 500 kB.

## Regressão backend após notificações e incrementos de paridade — 07/11/2026

- `.venv\Scripts\python.exe -m pytest --ignore=tests\test_deployment.py -q --show-capture=no`: **212 passed in 48,10s**. Executado com sockets locais autorizados para os testes HTTP; o módulo de deployment foi excluído e continua sem validação nesta execução.

## Incremento de Web Push opcional — 07/11/2026

- `.venv\Scripts\python.exe -m pytest tests\test_push_notifications.py tests\test_browser_push_migration.py -vv -s`: **5 passed**; cobre allowlist de endpoints, validação de chaves, criptografia, fila idempotente, entrega, revalidação de escopo e migração reversível.
- `.venv\Scripts\python.exe -m pytest tests\test_notifications.py -q --show-capture=no`: **4 passed** com sockets locais autorizados; cobre gestão por conta, segredo não retornado, isolamento entre usuários e ausência de configuração VAPID.
- `.venv\Scripts\python.exe -m pytest --ignore=tests\test_deployment.py -q --show-capture=no`: **219 passed in 57,59s**, com sockets locais autorizados; o módulo de deployment foi excluído.
- `alembic upgrade head` em SQLite temporário vazio e `alembic current`: **0031 (head)**. Permanecem avisos históricos de constraints sem nome em tabelas migradas.
- Ruff em `backend/app`, `backend/tests` e migração nova: **All checks passed**.
- Frontend: `npm run typecheck`, `npm run lint`, Vitest (**3 arquivos, 6 testes**) e `npm run build` passaram. O bundle principal tem 627,44 kB e o Vite mantém o aviso conhecido de chunk acima de 500 kB.
- Não foi feita entrega real para serviço de push externo; o teste de envio substitui o cliente de rede. Configuração VAPID é opcional e não foi ativada no ambiente publicado.

## Categoria de status por coluna — 07/11/2026

- Testes direcionados: `test_status_category_migration.py` e `test_query_language.py`: **49 passed**; API autenticada em `test_planning_foundation.py -k "status_category or category"`: **2 passed**. Cobre backfill/reversão, JQL, alteração por gestor, independência da ordem, bloqueio da categoria `Done` em coluna não estrutural e recusa ao fornecedor.

## Limites WIP por coluna — 07/11/2026

- Frontend: `npm test -- --run`: **17 passed**; `npm run lint`: **passou**; `npm run build`: **passou**, com o aviso existente de bundle JavaScript acima de 500 kB.
- Banco: `alembic upgrade head` e `alembic downgrade 0032` em SQLite temporário: **passaram**; após downgrade, a coluna `wip_limit` não existe mais.
- `ruff check app/models.py app/schemas.py app/main.py tests/test_planning_foundation.py`: **passou**.
- Chamada direta ao handler com SQLite em memória: **passou** ao definir, remover e validar a restrição de papel do limite.
- O teste HTTP direcionado para configurar/limpar o WIP ficou bloqueado antes da execução da fixture: Starlette `TestClient` aguardou a criação de socket local no loop Windows Proactor. O mesmo bloqueio ocorreu ao tentar `WindowsSelectorEventLoopPolicy`; não registrar esse teste como validado. Rodar novamente em ambiente compatível para completar a validação HTTP.

## Ciclos em dependências de bloqueio — 07/11/2026

- Regressão de serviços Python: `pytest tests/test_dependency_cycles.py tests/test_workflows.py tests/test_agile_reporting.py tests/test_planning_reporting.py tests/test_capacity_reporting.py tests/test_query_language.py -q`: **80 passed**.
- O teste de ciclo cobre caminho transitivo, ignora relações não bloqueadoras, rejeita ciclo via handler com HTTP 409 e permite relação `relates` no sentido inverso.
- `ruff check app/services.py app/main.py tests/test_dependency_cycles.py`: **passou**.

## Conectores de dependência no Timeline — 07/11/2026

- Vitest: **5 arquivos, 19 testes passaram**. O teste de Timeline verifica geometria/conector acessível para `blocks`; o teste de serviço verifica direção e ocultação das relações fora do recorte.
- `npm run lint`: **passou**; `npm run build`: **passou**. Continua o aviso já conhecido de bundle acima de 500 kB.
- Regressão backend `.venv\Scripts\python.exe -m pytest --ignore=tests/test_deployment.py -q --show-capture=no`: **221 passed in 56,58s**, com sockets locais autorizados.
- SQLite temporário vazio: `alembic upgrade head` concluiu em **0033 (head)** após os limites WIP. Permanecem avisos preexistentes de constraints sem nome em `sprints` e `tasks`.
- Ruff: **All checks passed**. Frontend `npm run typecheck`, `npm run lint`, Vitest (**3 arquivos, 6 testes**) e `npm run build` passaram. Bundle principal: 628,06 kB; aviso Vite acima de 500 kB continua conhecido.

## Agendamento por arraste no calendário — 07/11/2026

- O teste Vitest de `CalendarView` verifica o arraste de card sem prazo para uma data e o envio do cronograma correto ao callback; suíte frontend: **3 arquivos, 7 testes passaram**.
- `npm run typecheck`, `npm run lint` e `npm run build`: **passaram**. Bundle principal: 629,54 kB; aviso de chunk acima de 500 kB permanece.

## Revalidação E2E de planejamento e Kanban — 07/11/2026

- `backend\.venv\Scripts\python.exe -u scripts/run_e2e.py --reporter=line`: **12 passed** em 30,6s, com API/Vite locais e banco SQLite temporário descartável. Inclui filtros por categoria, agendamento no calendário, transições e horas por perfil, personalização individual, relatórios, acessibilidade e filtros completos.
- Os cenários adicionados validam que a categoria To Do/In Progress pode ser configurada e consultada sem depender da ordem visual e que um card sem prazo é agendado por arraste no calendário.
- Typecheck, ESLint, Vitest (**3 arquivos, 7 testes**) e build de produção passaram. Bundle principal 629,54 kB; o aviso do Vite acima de 500 kB continua.
- O runner precisou de permissão para abrir portas locais; todos os dados foram semeados no banco temporário do script. O teste de deploy remoto após a troca do banco e `tests/test_deployment.py` não fazem parte desta validação.

## Campo JQL de data de resolução — 07/11/2026

- `resolutiondate`, `resolved` e `resolution_date` derivam da última transição auditada para Concluído. A data só é efetiva enquanto o card está concluído; reabrir limpa a resolução atual sem apagar o histórico.
- `backend\.venv\Scripts\python.exe -m pytest tests\test_query_language.py -q`: **49 passed**. Cobertura inclui igualdade e comparações por dia UTC, ordenação, aliases e ausência de resolução em card reaberto ou sem trilha auditada.
- Regressão backend `python -m pytest --ignore=tests\test_deployment.py -q --show-capture=no`: **222 passed in 55,95s**, com sockets locais autorizados.
- Ruff, typecheck, ESLint, Vitest (**3 arquivos, 7 testes**) e build de produção passaram. Bundle principal 629,65 kB; o aviso do Vite acima de 500 kB permanece.
# Comparação entre versões do histórico do card — 07/11/2026

- A aba Histórico permite escolher uma versão inicial e final para exibir diferenças líquidas entre registros, incluindo alterações de etapa. O frontend reutiliza apenas dados que o endpoint de auditoria já autorizou e filtrou.
- `frontend`: `npm run typecheck`, `npm run lint` e a suíte completa `npm test` passaram: **5 arquivos, 11 testes**. Inclui agregação, campos filtrados, mudanças revertidas e renderização/seleção da comparação.
- A comparação não inventa snapshots ausentes. Eventos antigos sem detalhes de campo podem resultar em “Nenhuma diferença de campo registrada”.

## Filtros rápidos do quadro — 07/11/2026

- O quadro apresenta filtros combináveis para atrasadas, sem fornecedor, sem sprint e aprovação pendente. A seleção integra a configuração já persistida das visualizações salvas.
- Typecheck e build de produção passaram; `npm test` passou na suíte completa (**5 arquivos, 16 testes**) e ESLint passou. Cobertura inclui estados acessíveis, alternância/limpeza e combinação com os campos do card.

## Filtros rápidos personalizáveis — 07/11/2026

- Cada visualização pode guardar até 20 filtros rápidos com nome e consulta simples allowlisted; é possível cadastrar, editar, remover e combinar os filtros. IDs ativos e definições persistem no JSON de configuração já utilizado pela API de visualizações.
- Typecheck passou; os testes focados de `ProjectViews.test.tsx` passaram (**7 testes**), incluindo validação da sintaxe, criação/edição/remoção, alternância, limpeza e combinação aplicada a cards reais.
- As consultas avançadas com agrupamentos e operadores JQL continuam na busca avançada do servidor; filtros rápidos não executam expressão ou script arbitrário.

## Aliases de campos JQL Jira — 07/11/2026

- `summary` mapeia para título (incluindo busca textual, ordenação e histórico); `issuetype`/`issue_type` mapeiam para tipo; `dueDate`/`duedate` mapeiam para prazo.
- `.venv\\Scripts\\python.exe -m pytest tests\\test_query_language.py -q`: **50 passed**. O teste novo cobre filtragem, busca por trecho, ordenação, igualdade por alias e histórico `WAS`/`CHANGED`.
- Regressão backend `python -m pytest --ignore=tests/test_deployment.py -q --show-capture=no`: **223 passed in 55,89s**. O teste de deploy segue excluído.
- A regressão precisou da instalação local de `cryptography`, `py-vapid` e `pywebpush`, já declarados no lockfile mas ausentes no ambiente virtual. Nenhum arquivo de dependência foi alterado. Permanece o aviso de depreciação do TestClient/Starlette.

## Navegação hierárquica em tabela — 07/11/2026

- A tabela permite agrupar por pai ou tipo e incluir `Card pai`/`Tipo de card` como colunas. Quando o pai não consta no resultado filtrado, a chave OS continua identificando-o sem consultar dados adicionais.
- A suíte frontend completa passou (**5 arquivos, 17 testes**); ESLint, typecheck e build de produção passaram. Permanece o aviso do bundle principal acima de 500 kB.
- O teste de interface verifica agrupamento pelo épico, rótulo do pai, subtarefa e coluna de tipo.

## Retornos configuráveis de workflow — 07/11/2026

- Retornos entre etapas padrão são bloqueados sem política habilitada para o par origem/destino; uma política ativa permite o retorno somente aos perfis configurados e registra a transição na auditoria.
- Reabrir item concluído continua exigindo gestor e justificativa; além do destino padrão em revisão, outro destino exige regra habilitada. Validações nativas de horas e aprovação permanecem ativas.
- `.venv\\Scripts\\python.exe -m pytest tests/test_acceptance.py tests/test_workflows.py -q`: **25 passed**. Ruff nos arquivos alterados passou. `git diff --check` passou.

## Control chart com percentis — 07/11/2026

- O relatório ordena pontos por data de conclusão, calcula média, faixa e P50/P85/P95 com interpolação linear e apresenta dispersão e linhas de referência; os dados continuam sujeitos ao filtro JQL da sprint.
- `.venv\\Scripts\\python.exe -m pytest tests/test_agile_reporting.py tests/test_acceptance.py tests/test_workflows.py -q`: **34 passed**. Typecheck, ESLint, 21 testes Vitest e build de produção passaram. O build reporta aviso existente de bundle principal acima de 500 kB.
- `.venv\\Scripts\\python.exe -m pytest tests/test_planning_foundation.py -q`: **14 passed**, incluindo o payload do endpoint e a restrição de acesso do fornecedor.

## Níveis de hierarquia dos cards — 07/11/2026

- API e formulário restringem relações para épico → história/tarefa/bug → subtarefa; subtarefa não aceita pai épico, e edição de tipo não pode invalidar os filhos. Relações incompatíveis preexistentes são preservadas se não forem alteradas.
- `.venv\\Scripts\\python.exe -m pytest tests/test_hierarchy_privacy.py -q`: **2 passed**. Typecheck, ESLint, 21 testes Vitest e build frontend passaram nesta atualização.
- `.venv\\Scripts\\python.exe -m pytest tests/test_hierarchy_privacy.py tests/test_planning_foundation.py -q`: **16 passed**, incluindo criação da relação épico → tarefa na API.

## Janela de ciclo configurável — 07/11/2026

- O Control Chart e o relatório de ciclo aceitam etapas inicial/final selecionadas entre as colunas existentes; ciclos múltiplos do mesmo card geram amostras distintas e ordenadas.
- `.venv\\Scripts\\python.exe -m pytest tests/test_agile_reporting.py tests/test_planning_foundation.py -q`: **23 passed**, incluindo janela customizada no serviço e seleção/validação das colunas no endpoint.
- Typecheck, ESLint, **21 testes Vitest**, build de produção e Ruff passaram. O build mantém o aviso do bundle principal acima de 500 kB.
- E2E Playwright direcionado `análise de cards mostra fases ciclos sprint backlog e exportação`: **1 passed**, incluindo seleção visual de etapa inicial/final e continuidade dos filtros e exportação.

## Gatilho de automação por campo — 07/11/2026

- O gatilho `field_changed` aceita IDs estruturais ou personalizados, com filtro de até 20 campos; avalia mudanças na API de edição do card e nos valores personalizados. Execuções registram somente nomes dos campos e não iniciam recursão a partir das próprias ações automatizadas.
- `.venv\\Scripts\\python.exe -m pytest tests/test_automation.py tests/test_planning_foundation.py -q`: **54 passed**, incluindo regras que filtram alterações nativas/personalizadas e auditoria dos nomes de campos.
- Typecheck, ESLint, **21 testes Vitest**, build de produção e Ruff passaram. O build mantém o aviso do bundle principal acima de 500 kB.

## Gatilho de escopo da sprint — 07/11/2026

- Automação `sprint_scope_changed` executa ao adicionar card e ao devolver um card não concluído para backlog no encerramento da sprint. A condição `sprint_scope_actions` permite escolher `added`, `removed` ou ambos.
- Teste direto do serviço valida as duas direções, filtros, ações e registro de ação/ID da sprint na auditoria: `.venv\Scripts\python.exe -m pytest tests/test_automation.py -q` — **42 passed**. Ruff nos módulos e teste alterados passou.
- Frontend: typecheck **0**, ESLint **0**, Vitest **21 testes aprovados**, build de produção **0**. A build conserva o aviso de chunk principal acima de 500 kB.
