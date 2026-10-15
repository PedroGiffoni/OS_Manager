# Limitações e validações pendentes

- Docker Compose foi fornecido, mas não pôde ser executado: o Docker Desktop não disponibilizou `dockerDesktopLinuxEngine`. Validar build, health checks, restart e persistência do volume em máquina com daemon ativo antes de considerar esse caminho homologado.
- SQLite é temporário. Não houve teste de carga institucional, HA, banco corporativo, SSO ou implantação de produção. Uso local de um processo é o padrão validado.
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

- Publicação remota ainda pendente de autenticação e escolha de persistência. Render Free perde SQLite/anexos/sessões ao reiniciar, redeployar ou suspender; o Blueprint é apenas para teste descartável autorizado. Ver DEPLOYMENT.md. O build Docker remoto e a integração Vercel/Render ainda não foram executados.
