# Atualização visual Gestão de Demandas

Branch: atualizacao-os-manager. Nome de produto e título da aba: Gestão de Demandas. Identificadores técnicos de repositório, banco, URLs e recursos de nuvem foram preservados. Publicação solicitada a partir desta branch; o status deve ser confirmado nos serviços de hospedagem.

## Fonte e aplicação

Skill usada: sebrae-ce-design/SKILL.md, fornecida pelo usuário em sebrae-ce-design.zip. Foram lidos os fundamentos, marca, acessibilidade, webwriting, templates e trechos de componentes (cards, filtros, tabelas, modais, KPIs). Logos SVG positivo/branco foram copiados sem alterar geometria, cores ou proporções. Tokens :root e .dark vêm do arquivo oficial do anexo; a aplicação existente permanece em React com CSS puro, adaptação permitida pela skill.

Layout com header institucional, navegação por grupos, busca de páginas, sidebar recolhível no desktop, drawer nativo com foco contido no celular, rodapé institucional e login revisado. Temas claro e escuro com escolha explícita persistida localmente; sem troca automática pelo sistema operacional. Fontes Figtree e Lato são servidas pelo próprio projeto via @fontsource. Campuni usa o fallback Figtree previsto na skill, pois seu binário não está incluído no anexo. Ícones Lucide, foco visível, campos de 44px, estados escritos e tratamento do vermelho do modal de horas foram preservados.

O cálculo de contraste identificou o token sidebar-muted claro com 4,31:1 e texto branco sobre primary escuro com 4,22:1. Foram usadas composições de tokens semânticos para elevar o contraste do texto pequeno, preservando os tokens oficiais originais. A revisão mede combinações relevantes e testa teclado/390px; não representa certificação integral de acessibilidade do produto.

## Validação

Build/typecheck, lint e formatação do frontend executados. Vitest: 5 testes passaram. Playwright: 8 fluxos passaram na rodada final, incluindo login, campos individuais, fornecedor, horas, aprovação, Kanban, relatórios/exports, marca, alternância/persistência de tema, menu móvel, fechamento por Esc, retorno de foco e ausência de overflow horizontal em 390px. As asserções de contraste de texto pequeno na navegação clara/escura também passaram.

Os 5 testes de integração de relatórios/exportação do backend passaram após a mudança do nome na API e nos documentos exportados. Não foram alteradas regras de negócio do backend nesta atualização.

Auditoria de dependências de produção identificou uma ocorrência alta preexistente em zod 3.24.3 (GHSA-mrhx-c7xc-m3w5). A correção sugerida muda para Zod 4 e exige validar compatibilidade com os formulários; não foi aplicada atualização forçada de dependências fora desta mudança visual. As dependências novas de fonte/ícones não aparecem nessa ocorrência.

## Análise operacional aprovada e implementada

A entrega inicial aprovada está descrita em OPERATIONAL_ANALYTICS.md. Foram implementados tempo por fase, ciclos, aging, histórico, indicadores de sprints e backlog, filtros e exportações analíticas. A validação final do backend passou com 50 testes. O texto anterior de validação visual descreve a etapa anterior à inclusão dessas regras.
