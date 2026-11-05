# Análise operacional de demandas

Entrega aprovada na branch atualizacao-os-manager: relatórios reais de cards, sprints e backlog, com os mesmos filtros de campos do card, exceto descrição. A exportação analítica Excel/PDF respeita filtros, escopo e permissões financeiras.

## Definições

- Tempo por fase: soma das permanências registradas, em segundos corridos UTC, incluindo a permanência aberta até a consulta. Concluído não acumula trabalho. Não representa horas úteis nem horas apontadas.
- Lead time: criação até primeira conclusão. Cycle time: início da produção até conclusão; uma reabertura inicia outro ciclo, sem somar o intervalo em Concluído.
- Aging: idade do card e da fase atual. Reaberturas, retornos, histórico de movimentações e decisões de horas aparecem no detalhe.
- Desvio: horas utilizadas menos previstas; sem estimativa positiva, comparação indisponível. Custo mantém a regra de horas aprovadas vezes tarifa congelada e só aparece para autorizados.
- Sprint: compromisso inicial, entradas posteriores, concluídos, pendentes, devolvidos, taxa de conclusão e evolução diária. O denominador zero não produz porcentagem fictícia. Indicadores refletem o recorte filtrado, não necessariamente toda a sprint.
- Backlog: quantidade, idade, distribuição, itens mais antigos, entradas/saídas no período e prontidão dos campos visíveis para planejamento. Prontidão não cria novas validações de transição.

## Integridade e limitações

Históricos incompletos são sinalizados; durações sem evidência ficam indisponíveis. Nenhum evento antigo é inventado. Sprints encerradas usam corte histórico e preservam seu snapshot, sem incluir tempo posterior ao encerramento. Novos eventos de início registram o compromisso inicial explicitamente. Registros antigos podem ter menos informações.

Os filtros de período selecionam o conjunto de cards conforme os relatórios existentes; o resumo de entradas/saídas usa eventos dentro da janela e desse conjunto. Prazos sem informação não contam como atraso. O histórico não reconstrói alterações antigas de prazo que não tenham sido registradas.

APIs: GET /api/v1/reports/analysis e GET /api/v1/reports/cards/{id}; exports usam analysis=true. Permissões e escopo são aplicados no servidor, inclusive na consulta direta por ID. Strings em planilhas são texto para impedir interpretação como fórmulas.

Burndown avançado, percentis/previsões e metas institucionais ficam para avaliação posterior. A consulta deriva informações do histórico e pode exigir otimização para volumes institucionais. O SQLite gratuito no Render continua descartável, como autorizado para testes.

## Validação executada antes da publicação

Em 05/11/2026: pytest 50 testes aprovados (um aviso de depreciação Starlette/httpx); Vitest 5 aprovados; Playwright 8 aprovados com banco temporário; build/typecheck, ESLint e Prettier aprovados. Inclui métricas com relógio controlado, histórico incompleto, reabertura, congelamento de sprint, filtros, escopo e exportações.

## Relatório visual portátil HTML

A exportação HTML usa o mesmo recorte e autorização da análise operacional. Inclui KPIs, gráficos de distribuição e permanência, sprint, backlog, cards e detalhes expansíveis. Marca oficial, tokens, Figtree e Lato seguem a skill Sebrae CE. Logo, fontes, estilos e dados incorporados: abre sem internet, sem CDN ou telemetria. O arquivo é um retrato estático, sem atualização automática.

API: GET /api/v1/exports/html gera análise operacional mesmo sem analysis=true. Na interface, Exportar HTML fica junto a Excel/PDF. Datas pt-BR no fuso configurado e durações legíveis. O PDF analítico também ganhou KPIs, gráficos estáticos e fontes incorporadas.

Motion: entrada e barras em 500 ms, sem repetição contínua. Botão Pausar animações, prefers-reduced-motion e impressão desativam movimento. Não se anima o logo. O documento permanece legível sem JavaScript; o botão de impressão e a alternância manual de motion dependem dele.

Segurança: textos/atributos escapados, sem payload bruto. CSP bloqueia rede, formulários e scripts não autorizados. Script fixo com hash SHA-256; dados de usuário não entram em JavaScript. Exportações de fornecedor continuam sem custos/tarifas e sem tarefas de terceiros. Compartilhar o arquivo somente com pessoas autorizadas.

Decisão aprovada: relatórios são exclusivos de usuários internos. Fornecedores não consultam /reports/* nem exportam Excel, PDF ou HTML, mesmo das próprias atividades. API retorna 403 e a página não aparece no menu.
