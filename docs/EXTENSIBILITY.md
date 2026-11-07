# Extensibilidade segura

O Gestão de Demandas oferece pontos de extensão por configuração e por código confiável. Extensões não executam JavaScript, HTML, SQL ou expressões fornecidas por usuários.

## Pontos disponíveis

- **Campos por card:** definições tipadas, validação, visibilidade e edição controladas pelo backend.
- **Widgets:** agrupamentos e medidas allowlisted, com filtros atuais, autorização financeira e compartilhamento por papel interno.
- **Workflows:** políticas podem ser distintas por tipo de card e incluem condições tipadas sobre aprovação, tipo, prioridade, alocação de fornecedor, etiquetas, prazo e hierarquia, com ações enumeradas pós-transição; cada operador/ação nova exige implementação, teste e migração compatível no servidor.
- **Automações:** gatilhos de criação/edição, mudança de responsável/fornecedor, prazo/prioridade, movimentação, comentário/anexo, criação/remoção de relações, horas, aprovação, sprint, evento GitHub/GitLab/Bitbucket e agenda diária ou semanal UTC idempotente. Eventos podem filtrar metadados allowlisted; as relações aceitam `blocks`, `relates` e `duplicates`. As ações allowlist incluem prioridade, adicionar/remover etiqueta, comentário, prazo, responsável interno, observador interno e atualização de campos personalizados existentes. Cada novo gatilho ou ação exige implementação e teste no servidor.
- **Condições de automação por campos:** até dez valores escalares JSON tipados são comparados com os campos do schema atual de cada card. A configuração não avalia código, e logs não copiam valores filtrados.
- **Workflows por campos:** condições de transição podem exigir igualdade/desigualdade tipada por identificador do campo individual do card; condição ausente no schema sempre bloqueia a correspondência.
- **Integrações de desenvolvimento:** adapters registrados em `backend/app/integrations.py` normalizam autenticação, identificação de evento, resumo e metadados limitados de repositório, branch, commit, pull request, estado e ambiente. Payloads brutos externos não são salvos.

## Adicionar um adapter de webhook

Um adapter é código Python instalado e revisado junto com o backend. Ele deve declarar o nome do provedor, a variável de ambiente do segredo, um verificador de assinatura/token, como obter tipo/ID de entrega e como resumir o payload. O registro é feito por `register_webhook_adapter(WebhookAdapter(...))`; duplicatas e identificadores inválidos são rejeitados. A rota comum limita payloads a 1 MiB, exige entrega identificável, deduplica eventos, extrai apenas chaves `OS-<id>`, filtra links para HTTPS e só mostra eventos depois da autorização normal do card.

Não se deve carregar código de plugin enviado pela interface ou dinamicamente a partir de repositórios externos. Marketplace, galeria e instalação de plugins pela interface estão fora do escopo solicitado. Os adapters permanecem extensões de código confiável, revisadas e implantadas junto com o backend; execução de código de terceiros não é suportada.

## Compartilhamento e escopo

Visualizações do Kanban e widgets podem ser compartilhados com papéis internos específicos. O backend verifica a propriedade/papel em cada listagem e em cada consulta de dados. Fornecedores não recebem conteúdo compartilhado interno. Widgets financeiros continuam sujeitos às concessões `view_financial` e `manage_planning`.
