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
