# API REST

Base `/api/v1`. Esquema OpenAPI em `/api/openapi.json` e interface `/api/docs` no backend ou pelo proxy frontend. Entradas desconhecidas são recusadas; identificadores/horas/centavos em JSON são inteiros estritos. Datas usam ISO 8601. Sessão em cookie HttpOnly e mutações com cabeçalho `X-CSRF-Token` retornado pelo login/me.

| Método | Rota | Uso |
| --- | --- | --- |
| POST | /auth/login, /auth/logout | Entrada individual e revogação da sessão |
| GET | /auth/me, /config | Conta, permissões atuais, CSRF e timezone |
| GET/POST | /users | Administração de contas |
| GET | /permissions | Catálogo de concessões |
| PUT | /users/{id}/grants | Conceder/revogar acessos, administrador |
| GET/POST | /suppliers | Consulta paginada e cadastro com tarifa inicial atômica |
| PUT | /suppliers/{id} | Nome/função/situação, com auditoria |
| GET/POST | /suppliers/{id}/rates | Histórico financeiro e nova versão imutável |
| GET/POST | /tasks | Consulta paginada e criação |
| GET/PUT/DELETE | /tasks/{id} | Detalhe, edição versionada e arquivamento conservador |
| POST | /tasks/{id}/move | Transição com validação nativa e campos obrigatórios |
| POST | /tasks/reorder | Ordem transacional com versões de todos os cards enviados |
| PUT | /tasks/{id}/hours | Somente fornecedor responsável, totais em minutos |
| POST | /tasks/{id}/approval | Decisão para versão específica de horas, idempotente |
| GET/PUT | /tasks/{id}/schema | Configuração individual versionada |
| PUT | /tasks/{id}/values | Valores tipados e permissões por campo |
| GET/POST | /sprints | Consulta e planejamento |
| PUT/DELETE | /sprints/{id} | Edição/arquivamento de planejamento com expected_version |
| POST | /sprints/{id}/tasks | Inclusão elegível e vínculo ativo único |
| POST | /sprints/{id}/action | start, close, reopen, com versão/motivo |
| GET | /sprints/{id}/history | Consulta de retrato histórico sem mutações |
| GET | /audit | entity + identity; dados financeiros filtrados |
| GET | /dashboard | Indicadores derivados e evolução de sprints |
| GET | /exports/xlsx, /exports/pdf | Mesmos filtros, financial=true exige concessões financeiras |
| GET | /directory/users | Referências de conta com escopo |
| GET/POST | /tasks/{id}/comments | Colaboração auditada |
| GET/POST | /tasks/{id}/attachments | Lista e upload multipart limitado a 5 MiB |
| GET | /attachments/{id} | Download autorizado pelo escopo da tarefa |
| GET | /health | Prontidão de conexão/esquema |

Filtros operacionais: q, status, sprint_id, supplier_id, starts/ends (criação UTC), offset e limit (até 200). Ordenação de tarefas por prioridade e ID. Fornecedores aceitam busca q, active, offset e limit. Relatórios usam status/sprint/fornecedor/período e aplicam escopo antes da exportação.

Mutações de tarefa exigem `version`. Aprovação exige também `hours_version`. Inclusão em sprint exige versão de sprint e task_version. Falhas 401/403/404/409/422/429/503 contêm detalhe padronizado sem valores de entrada sensíveis. Conflito exige recarregar antes de tentar novamente; a interface não confirma movimento recusado. Consulte OpenAPI para todos os payloads e limites.
