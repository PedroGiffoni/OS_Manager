# Indicadores e fórmulas

Todas as métricas são derivadas de registros persistidos e do escopo autorizado. Filtros: sprint, fornecedor, estado e período de criação UTC da atividade. Sem filtros de período, todas as atividades não arquivadas no escopo são consideradas. A seleção de sprint inclui o vínculo histórico; se encerrada, usa os valores congelados no último encerramento.

- Planejadas: quantidade de atividades no escopo selecionado. Sem filtro de sprint, inclui backlog; não é compromisso contratado.
- Concluídas: status Concluído. Pendentes = planejadas − concluídas. A identidade concluídas + pendentes = planejadas é preservada.
- Atrasadas: pendentes com prazo anterior à data corrente em APP_TIMEZONE (America/Sao_Paulo por padrão). Sem prazo não é atraso.
- Taxa de conclusão = concluídas ÷ planejadas × 100. Denominador zero resulta em 0 e estado vazio na interface.
- Previstas/utilizadas: soma de minutos e conversão de apresentação para horas. Utilizadas ainda não aprovadas continuam sendo esforço operacional informado.
- Desvio = utilizadas − previstas; sinal negativo indica menor esforço informado, sem atribuir avaliação subjetiva.
- Pontualidade = concluídas cuja última conclusão ocorreu até o prazo ÷ concluídas com prazo × 100. Sem denominador resulta em 0; sem prazo não compõe esse denominador.
- Evolução das sprints: comparativo de planejadas e concluídas por sprint, ordenado pela data de início, sem inventar meta ou score individual.
- Custo consolidado atual em centavos = ROUND_HALF_UP(minutos utilizados da aprovação vigente × centavos/hora congelados ÷ 60). Exemplo: 480 × 12000 ÷ 60 = 96000 centavos (R$ 960,00). Horas previstas não entram na fórmula. Pendência/rejeição/reabertura não integram esse consolidado.
- Custo por fornecedor: soma do custo elegível das tarefas do fornecedor. Por tarefa: valor individual. Por sprint: aplicar filtro de sprint; encerradas usam snapshot. Por período: aplicar filtro de criação da atividade, não data de pagamento/aprovação.

O relatório financeiro usa centavos inteiros nas tabelas de exportação para preservar exatidão. A interface converte somente para exibição monetária. Dados sem aprovação não entram em valores financeiros. O dashboard expõe definições operacionais; não há avaliação subjetiva de desempenho ou metas institucionais presumidas.
Cada aprovação registra a sprint atual. O custo por sprint considera essa referência, e replanejar sem alterar horas/aprovação não cria nova atribuição financeira. Aprovações sem sprint compõem o total global e o custo da tarefa/fornecedor, mas não o de uma sprint posterior. Snapshots anteriores à revisão 0004 não são reescritos; aprovações legadas sem essa referência exigem reconciliação antes de atribuição institucional por sprint.
