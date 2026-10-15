# Validação executada

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
