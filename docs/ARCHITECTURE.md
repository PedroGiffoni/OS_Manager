# Arquitetura

## Componentes

React/TypeScript e Vite renderizam a aplicação em pt-BR. React Router organiza páginas; TanStack Query mantém consultas e invalida o cache após mutações; React Hook Form/Zod validam formulários; dnd-kit oferece movimento/ordenação e suporte a teclado; Recharts apresenta indicadores. Estilos CSS locais mantêm o design responsivo sem serviço externo ou fontes remotas. Os componentes usam labels, botões e selects nativos e foco visível.

FastAPI publica REST `/api/v1` e OpenAPI em `/api/docs`. `main.py` trata transporte, permissões por ação e coordenação transacional; `security.py` concentra sessão/RBAC; `schemas.py` valida entradas; `services.py` concentra regras e serialização por perfil; `repositories.py` concentra filtros; `reporting.py` deriva indicadores; `exports.py` gera arquivos; `collaboration.py` trata comentários/anexos. `db.py` é a fronteira SQLAlchemy e isola PRAGMAs SQLite. Nenhuma regra depende de React.

Todas as consultas de atividades passam por escopo no servidor. O fornecedor é resolvido por vínculo com a conta. Consultas por ID de atividade alheia retornam 404; permissões de ação recusadas retornam 403. Tarifas/custos são adicionados explicitamente apenas a payloads de administrador/gestor com autorização financeira. Exports operacionais não serializam valores financeiros.

## Persistência e transações

Alembic é o único caminho operacional de alteração de esquema. Migrações têm operações explícitas e não importam modelos mutáveis. `create_all` não é usado na inicialização da aplicação. Modelos incluem usuários/papéis/permissões/concessões JSON, fornecedores, versões de tarifa, atividades, alocações com snapshot, vínculos de sprint, schema/valores versionados, horas, aprovações, auditoria, comentários e anexos.

Valores financeiros são inteiros em centavos; esforço é inteiro em minutos. Custo é calculado com Decimal e ROUND_HALF_UP ao centavo. Não se aceita tarifa/custo de tarefa no payload de edição. A alocação aponta para uma versão de tarifa e guarda seu snapshot. Aprovações apontam para alocação e versão de horas, com chave estrangeira composta e unicidade. Snapshots fechados de sprint preservam o retrato de seus indicadores e os fechamentos anteriores.

Task e Sprint usam versão otimista no SQLAlchemy. Mutações exigem versão do cliente. Atualizações obsoletas ou violações de vínculos retornam 409; uma transação recusada não é confirmada. Aprovação repetida da mesma versão/decisão/justificativa é idempotente, sem segundo lançamento. WAL, foreign_keys e busy_timeout são configurados na infraestrutura. SQLite tem um escritor por vez e pode retornar indisponibilidade em contenção; não substitui o dimensionamento de um banco institucional.

## Autenticação e segurança

Senha com Argon2id; token aleatório de sessão armazenado somente como SHA-256 no banco; cookie HttpOnly/SameSite=Strict com validade de 8 horas. Secure é configurável e deve ser ligado sob HTTPS. Token CSRF de sessão é exigido em mutações autenticadas. Origem é validada contra a origem da API e TRUSTED_ORIGINS. Logout remove sessão; concessões são lidas novamente por requisição. Login tem limitação local por combinação de origem/conta e mensagens genéricas.

Erros de validação não ecoam valores de entrada. SQLAlchemy usa parâmetros; React renderiza texto; campos não executam HTML/scripts/expressões. XLSX força células de texto para não executar fórmulas de usuário. PDF escapa conteúdo e quebra linhas. Anexos de até 5 MiB ficam em BLOB com hash; tipos/magic bytes são verificados e downloads forçados para attachment, sempre após autorização da tarefa. Requisições de upload exigem Content-Length e são limitadas antes do parser. Não há análise antimalware externa.

Auditoria registra ator/instante e eventos de tarifa, alocação, schema, horas, decisões, transições, sprints, arquivamento, exportação e ações autenticadas negadas com 403. Logs estruturados têm método, caminho sem query, status e duração; não incluem corpos, cookies, senhas, tarifas ou custos. Histórico de status está registrado nos eventos de auditoria, em vez de tabela redundante.

## Execução

Desenvolvimento: API 8000, Vite 5173 com proxy `/api`. Docker: Nginx 8080 com proxy para API, volume persistente SQLite e health checks. Um único processo de API é o padrão local. Bibliotecas não exigem telemetria externa, provedores de identidade ou contas em nuvem.