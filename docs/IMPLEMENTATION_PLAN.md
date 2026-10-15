# Plano e acompanhamento OS Manager

Arquitetura implementada: React/TypeScript/Vite com Router, TanStack Query, RHF/Zod, dnd-kit e Recharts; FastAPI /api/v1; SQLAlchemy 2/Alembic; SQLite local. Centavos e minutos inteiros, custo com Decimal/ROUND_HALF_UP; sessão HttpOnly com CSRF; RBAC e escopo aplicados no servidor. Código novo isolado em os-manager, preservando a instalação preexistente do Pen.

## Marcos

- [x] Fundação local: backend/frontend, configuração, SQLite, migrações, autenticação, RBAC, testes e scripts.
- [x] Fornecedores: cadastro atômico com tarifa, versões, restrições financeiras e alocação com snapshot.
- [x] Backlog/sprints: criação/edição/arquivamento, prioridade, vínculo único, histórico, encerramento e retorno ao backlog.
- [x] Kanban/cards: arraste e alternativa por menu/teclado, ordenação com versão, biblioteca arrastável, campos adicionais/nativos ordenáveis, preview, schema versionado e validação por transição.
- [x] Horas/aprovações: fornecedor exclusivo, rejeição/reenvio, aprovação, conclusão, custo exato, reabertura auditável e atribuição à sprint da aprovação.
- [x] Dashboards/exports: filtros, indicadores derivados, evolução das sprints, custos por fornecedor/tarefa/sprint, Excel/PDF com autorização.
- [x] Qualidade local: 17 testes Python, 5 Vitest/RTL, 4 Playwright; lint, typecheck, build, auditoria de dependências, documentação e seed fictício.
- [ ] Validar execução Docker: configuração passou; daemon Docker Desktop indisponível neste ambiente.

Cada marco foi validado incrementalmente; falhas encontradas foram corrigidas antes dos resultados finais. Saídas reais, escopo dos testes, aviso de depreciação e bloqueio Docker estão em [VALIDATION.md](VALIDATION.md). Limites operacionais e decisões conservadoras estão em [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) e [DECISIONS.md](DECISIONS.md).

SQLite permanece temporário para desenvolvimento e testes. Não houve homologação de produção, teste de carga institucional nem migração para SGBD corporativo.

## Solicitação posterior: publicação gratuita para testes

- [x] Verificar limites atuais do Render Free e Vercel Hobby nas fontes oficiais.
- [x] Preparar Blueprint gratuito, porta dinâmica, migrações no startup e guarda de configuração HTTPS.
- [x] Preparar proxy Vercel por domínio real, sem cache personalizado e sem quebrar cookies/CSRF.
- [x] Seed de teste privado opcional e idempotente; banco local excluído do envio.
- [x] Documentar deploy e executar backend/build/E2E locais (VALIDATION.md).
- [ ] Definir com o usuário se o SQLite pode ser descartado em reinícios.
- [x] Autenticar Vercel CLI e enviar código ao repositório público informado pelo usuário.
- [x] Configurar Root Directory Vercel = frontend.
- [ ] Autenticar o provedor de backend após definir persistência.
- [ ] Publicar backend e frontend e registrar URLs reais.
- [ ] Validar fluxo completo, cookies, exports e autorização nos domínios públicos.
