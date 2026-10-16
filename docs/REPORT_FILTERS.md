# Filtros dos relatórios

Na aba Relatórios, use **Adicionar filtro**, escolha o campo, a condição e o valor. Combine condições e pressione **Aplicar filtros**. A prévia paginada, os indicadores e os botões Excel/PDF usam exatamente as condições aplicadas, juntamente com período de criação, sprint, fornecedor e status do topo da página. Alterar uma condição sem aplicar mantém o relatório anterior. Remover uma condição exige aplicar novamente; Limpar filtros de campos aplica a limpeza imediatamente, preservando os filtros do topo. Trocar a sprint reinicia os filtros de campos, pois os schemas históricos podem ser diferentes.

## Campos e condições

- Nativos: identificador, título, etapa, prioridade, prazo, criação, fornecedor, sprint, criador, horas previstas, horas utilizadas, aprovação e anexos. Descrição não é um filtro.
- Financeiros: tarifa congelada e custo aprovado, somente para administrador/gestor com view_financial. Exportar um recorte filtrado por dados financeiros também exige export_financial, mesmo sem incluir colunas financeiras no arquivo.
- Personalizados: todos os campos efetivamente configurados nos cards visíveis, incluindo texto curto/longo, número, data, seleção, checkbox, usuário, fornecedor e anexo.
- Texto: contém ou igualdade, sem distinção de maiúsculas/minúsculas, preservando acentos. Não executa expressões, HTML ou scripts.
- Número, horas, dinheiro e data: igualdade, limite mínimo, máximo ou intervalo inclusivo. Horas são informadas em horas decimais (1,5 = 90 minutos); dinheiro em reais. Conversões e comparações usam Decimal no servidor. Datas de criação são comparadas em UTC; prazo/campos de data usam data civil.
- Seleção, usuário, fornecedor, sprint e checkbox: igualdade por opção/ID. Checkbox distingue explicitamente Sim, Não e não preenchido. Números iguais a zero são valores preenchidos; horas zero representam não informadas.
- Anexos: nome de arquivo contém/igual, preenchido ou não preenchido. Não pesquisa o conteúdo dos arquivos.
- Todos os tipos: preenchido/não preenchido. Campos personalizados só selecionam cards que possuem aquele campo visível no schema, inclusive na pesquisa por não preenchido.

As condições são combinadas por **E** (todas precisam ser verdadeiras). Intervalos incluem os dois limites. Campos individuais não são unidos apenas por terem o mesmo rótulo: IDs diferentes continuam sendo campos distintos e rótulos repetidos recebem identificação dos cards. Seletores de referência mostram opções presentes nos cards do escopo do usuário. Se não há dados compatíveis, é possível usar a condição não preenchido. O catálogo não inclui campos ocultos ou campos de tarefas de outro fornecedor. Filtros desconhecidos ou sem permissão são rejeitados pelo servidor. O número máximo é 30 condições e 12.000 caracteres no parâmetro serializado.

## Histórico e API

Com sprint encerrada selecionada, usa o snapshot de etapa/horas/custos e a versão do schema/valores do encerramento. Edições posteriores não alteram esse recorte histórico. Anexos usam os nomes dos arquivos atualmente preservados na atividade (não existe versionamento histórico de nome de anexo). Para encerramentos antigos sem snapshot de tarifa, a tarifa histórica é tratada como não disponível em vez de usar a tarifa atual.

- `GET /api/v1/reports/fields?sprint_id=...`: catálogo por escopo; descrição e dados sem autorização são omitidos.
- `GET /api/v1/reports/preview`: total, itens paginados e resumo dos filtros, com `offset` e `limit` (25 por padrão, máximo 100).
- `GET /api/v1/dashboard` e `GET /api/v1/exports/{xlsx|pdf}`: aceitam o mesmo parâmetro `field_filters`.

`field_filters` é uma lista JSON de objetos com `field`, `op`, `value`, `value_to`; valores são strings. Exemplo: `[{"field":"native:estimated_minutes","op":"between","value":"1.5","value_to":"8"}]`. Campos personalizados usam `field:<id>`; nativos usam `native:<chave>`. Operadores: contains, eq, gte, lte, between, empty, not_empty. O servidor valida operadores, tipos, limites e autorização antes de filtrar. Consultas e exports não dependem de autorização apenas no React. Exportações mantêm as colunas operacionais existentes e registram as condições aplicadas; seleção de colunas não faz parte desta mudança.

## Validação e limites

Testes de integração cobrem todos os tipos, combinação de filtros, preview, custos exatos, autorização financeira/horizontal, campos ocultos, datas/números inválidos, limites, paginação, Excel/PDF e schema histórico. O fluxo Playwright valida escolha de campos, combinação, remoção, estados vazios e os dois downloads.

A V1 filtra os registros já autorizados em memória, mantendo portabilidade do SQLite e a lógica de snapshots. A paginação limita a resposta, não o custo de cálculo do conjunto. Para grandes volumes institucionais, avaliar índices, consultas específicas para o SGBD homologado e testes de carga antes de implantação; não há comprovação de capacidade institucional por estes testes funcionais.
