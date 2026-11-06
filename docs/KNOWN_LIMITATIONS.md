# Limitações e validações pendentes

- Docker Compose foi fornecido, mas não pôde ser executado: o Docker Desktop não disponibilizou `dockerDesktopLinuxEngine`. Validar build, health checks, restart e persistência do volume em máquina com daemon ativo antes de considerar esse caminho homologado.
- O ambiente local usa SQLite. O Render de teste usa PostgreSQL Free 16 de 1 GB, que expira em 06/12/2026 e não inclui backups automáticos; nenhum teste institucional de carga, HA, SGBD corporativo, SSO ou produção foi realizado.
- Login usa limitação em memória por origem/conta; reiniciar o processo limpa a janela. Implantação com múltiplos workers exige mecanismo compartilhado e política institucional de autenticação. Não há recuperação automática de senha ou MFA na V1.
- Sessão local usa cookie sem Secure porque o endereço de desenvolvimento é HTTP. HTTPS, Secure, origens permitidas, gestão de credenciais e política de expiração precisam ser configurados antes de qualquer publicação.
- Quadros/listas de seleção carregam até 200 atividades e o seletor de fornecedores até 100 por consulta. A lista de atividades possui paginação. Volumes maiores exigem ampliar paginação dos seletores e do quadro.
- Troca de fornecedor em execução é deliberadamente bloqueada. Exige um fluxo adicional de encerramento parcial/alocação e homologação, em vez de reescrever horas ou custos existentes.
- Retornos de etapa, exceto reabertura formal de Concluído para Em revisão, são bloqueados pela regra conservadora adotada. Não há metas subjetivas ou pontuação individual.
- Período financeiro filtra criação UTC da atividade; não implementa competência contábil, pagamento ou lançamento de aditivos. A regra aparece na documentação/exportação e deve ser homologada para uso institucional.
- O histórico de alteração de schema/horas e aprovações é persistente. A interface mostra eventos de auditoria e a versão atual; não há comparador visual de todas as versões lado a lado.
- Anexos não passam por serviço antimalware; tipos/tamanho são limitados e o download é forçado. Não há integração externa de notificações: o fornecedor vê o estado e a justificativa da rejeição no card.
- O papel de administrador é de autoridade total e deve ser restrito. Gestão de credenciais de produção e vinculação posterior/troca de login de fornecedor não foram ampliadas silenciosamente.

Os testes executados e seus resultados constam em VALIDATION.md. Limitações não são declaração de homologação institucional.
- A suíte Python emite aviso de depreciação da integração httpx/Starlette TestClient. Os testes passam; uma futura troca para httpx2 deve ser validada separadamente.

- Publicação de testes executada em Vercel/Render; quatro E2E passaram antes da troca do banco. PostgreSQL foi conectado e inicializado no Render; deploy e health foram verificados, mas o E2E ainda não foi repetido no banco novo. Ver DEPLOYMENT_STATUS.md. Docker local continua sem daemon validado.
