# Estado da publicação — 06/11/2026

## Endereços confirmados

- Aplicação: **https://os-manager-phi.vercel.app**
- Health pelo frontend/proxy: https://os-manager-phi.vercel.app/api/v1/health
- Backend: https://os-manager-api.onrender.com
- Health direto: https://os-manager-api.onrender.com/api/v1/health
- Código publicado no Render: https://github.com/PedroGiffoni/OS_Manager — branch `melhorias-relatorios`, commit `98acf38`.
- Painel Vercel: https://vercel.com/pedro-giffoni-s-projects/os-manager
- Painel Render: https://dashboard.render.com/web/srv-db8irum89jmc73dttfl0

## Configuração efetivamente publicada

Render Free, região Ohio, Docker construído a partir de `backend/Dockerfile`, PostgreSQL 16 Free de 1 GB (`os-manager-test-db`) e um worker. Workspace `My Workspace`, escolhido pelo usuário. O banco expira em **06/12/2026** e não tem backups automáticos. Só há dados fictícios. A regra temporária de acesso externo usada na configuração foi removida após a conexão do serviço; o backend usa a URL interna. O antigo arquivo SQLite local foi preservado como legado, mas a aplicação não o abre nem depende dele. O serviço FoodSnap preexistente não foi alterado.

Vercel projeto `os-manager`, ID `prj_PKwsor6tp6P45rl95susS2X6ysm4`, Root Directory `frontend`, Node 24, build Vite. Proxy `/api` aponta ao endereço real do Render. GitHub conectado para atualizações do frontend. O backend está com auto deploy desligado: atualizar manualmente no Render quando puder reiniciar os testes.

A integração Vercel criou o projeto, mas suas consultas ao escopo retornaram 403. O fallback CLI foi autenticado, confirmou o proprietário e realizou build, deploy e promoção. Não foi necessário desabilitar proteção de deployments. O domínio estável respondeu ao health por requisição comum e foi usado pelos testes reais no navegador.

Deployment Vercel inicial verificado: `dpl_5sjHVDQnBH5njuQw9qc3ib11V35R`, READY e promovido. Backend deploy `dep-db8ivehsrm7s73eggk00`, live. Os identificadores registram a primeira verificação; deploys posteriores do Git podem substituí-los.

## Contas fictícias

`admin`, `gestor`, `gestor_sem_aprovacao`, `interno`, `fornecedor`, `fornecedor2`. Papéis e permissões: PERMISSIONS.md. A senha privada dessas contas foi gerada aleatoriamente e está no painel Render, variável **OS_MANAGER_DEMO_PASSWORD**. A senha local do README não funciona na demonstração publicada. Nenhuma senha, token, sessão, arquivo `.env.local` ou banco local foi enviado ao GitHub.

O seed fictício foi criado no PostgreSQL durante o primeiro deploy desta troca. Ele cria os exemplos se o banco estiver vazio; não copia o arquivo local legado. Não usar dados reais. O plano gratuito compartilha franquias com outros serviços do workspace; consultar o painel para disponibilidade e limites atuais.

## Verificações executadas

- Render construiu o contêiner no commit `98acf38`; deploy `dep-dbms02jbc2fs73app1lg` live.
- Logs do startup confirmam Alembic, seed fictício e Uvicorn inicializados após a conexão PostgreSQL.
- Health direto: HTTP 200, JSON `status=ok`; log de erro de aplicação vazio após o deploy.
- A conexão PostgreSQL foi restringida para tráfego interno do Render. A consulta SQL hospedada não foi executada porque o Render MCP não consegue acessar bancos com todas as conexões públicas bloqueadas.
- Vercel build: npm ci, TypeScript e Vite passaram; npm audit do build informou 0 vulnerabilidades.
- Playwright no domínio publicado: **4 passed (51.3s)**. Fluxo gestor/fornecedor, horas, bloqueios de movimentação, aprovação, custo fictício R$ 960,00, conclusão, Excel, cadastro, campos individuais, drag and drop inválido, responsividade e vínculo das horas nativas.
- Consulta aos logs de aplicação do Render com nível error: nenhum resultado retornado no momento da verificação.
- Testes locais anteriores: 35 pytest, 4 E2E, build e lint aprovados. Detalhes em VALIDATION.md.

## Repetir testes remotos

Somente na demonstração descartável: os testes criam registros fictícios e alteram cards de exemplo. Não executar contra dados que precisem ser preservados.

```powershell
.\.venv\Scripts\python.exe scripts/run_remote_e2e.py --base-url https://os-manager-phi.vercel.app
```

O runner pede a senha com entrada oculta; não a passe como argumento. Define E2E_BASE_URL/E2E_PASSWORD apenas no ambiente do processo filho e desativa traces remotos para não armazenar credenciais. Testes locais usam `scripts/run_e2e.py` com o banco PostgreSQL dedicado `os_manager_e2e`.

## Limites reais

O PostgreSQL Free expira em 06/12/2026, tem limite de 1 GB e não oferece backups automáticos. Exporte ou descarte os dados fictícios antes do prazo. A retomada do backend gratuito pode demorar; o primeiro acesso pode precisar de nova tentativa. Essa configuração foi autorizada somente para testes, sem homologação institucional. A suíte E2E registrada anteriormente exercitou o backend SQLite antes da troca; após a troca foram confirmados deploy, inicialização e health, mas não foi repetido o fluxo E2E nem login contra PostgreSQL. O runner E2E atual usa um banco PostgreSQL dedicado.

Docker local continua sem daemon validado; o build Docker remoto no Render foi executado com sucesso. Não houve teste de carga ou indisponibilidade prolongada. Health HTTP foi conferido externamente; a criação direta via integração Render usou o health check de porta padrão do provedor, pois não expõe edição de healthCheckPath. O Blueprint oferece `/api/v1/health` para configurações futuras via Dashboard/Blueprint.
