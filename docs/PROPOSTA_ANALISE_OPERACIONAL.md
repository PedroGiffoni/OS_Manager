# Proposta de análise de cards sprints e backlog

Status: proposta para validação do responsável do produto. Os novos relatórios não foram implementados. Identidade do produto alterada para Gestão de Demandas na branch atualizacao-os-manager; repositório, banco, credenciais, URLs e recursos de nuvem mantêm seus identificadores técnicos atuais.

## Organização da área

Ampliar Relatórios com quatro visões: Cards, Sprints, Backlog e Fluxo. Cada card deve abrir uma linha do tempo e uma tabela de entradas/saídas de fase. Manter filtros existentes por campos de card, exceto descrição, além de período, sprint, fornecedor e etapa. Acrescentar filtros de duração, atraso, reabertura e aprovação conforme aprovação desta proposta. A exportação deve respeitar o recorte, as colunas aprovadas e as permissões. Fornecedor vê somente seus cards e nunca recebe custos, tarifas ou métricas de outras pessoas; acesso financeiro mantém as concessões atuais.

## Indicadores sugeridos para cards

| ID | Informação | Definição proposta |
| C01 | Identificação e contexto | ID, título, prioridade, etapa, prazo, criador, fornecedor, sprint, criação, conclusão e campos personalizados visíveis. |
| C02 | Linha do tempo | Movimentação, origem/destino, ator, instante e motivo, incluindo devolução ao backlog e reabertura. |
| C03 | Tempo em cada fase | Entrada, saída, duração de cada passagem e soma por fase. Para passagem ainda aberta, calcular até o instante de referência e identificar que está em andamento. |
| C04 | Idade do card | Tempo desde a criação e tempo desde a entrada na etapa atual, apresentados separadamente. |
| C05 | Tempo total de entrega | Lead time da criação à conclusão; exibir também cards ainda não concluídos como idade, sem misturar os dois grupos. |
| C06 | Tempo de execução do fluxo | Cycle time do início de Em produção à conclusão. Diferenciar duração de calendário das horas apontadas; revisão faz parte do ciclo. |
| C07 | Espera e gargalos | Tempo em A fazer, tempo Em revisão e quantidade acumulada por fase. Esses tempos indicam espera potencial, não comprovam inatividade de uma pessoa. |
| C08 | Horas e estimativa | Previstas, utilizadas, aprovadas, diferença absoluta e percentual apenas quando há estimativa positiva. Sem estimativa: não se aplica. |
| C09 | Aprovações | Intervalo entre submissão e decisão, rejeições, reapresentações, autor e justificativas. Separar cada versão. |
| C10 | Prazo | Em dia/atrasado, dias de atraso e conclusão dentro/fora do prazo; sem prazo é categoria própria. |
| C11 | Retrabalho e replanejamento | Quantidade e motivos de reaberturas, rejeições e sprints pelas quais o card passou. Não usar como score subjetivo de produtividade. |
| C12 | Financeiro autorizado | Tarifa da alocação, custo consolidado e histórico de aprovações, somente a quem já pode acessar esses dados. |

## Indicadores sugeridos para sprints

| ID | Informação | Definição proposta |
| S01 | Compromisso e resultado | Cards presentes no início, cards concluídos, pendentes e devolvidos ao backlog. |
| S02 | Alteração de escopo | Cards adicionados após início, retirados e replanejados, com instante e autor. |
| S03 | Previsibilidade | Cards do compromisso inicial concluídos / compromisso inicial. Informar separadamente a conclusão do escopo final, pois entradas posteriores mudam o denominador. |
| S04 | Ritmo de entrega | Cards concluídos por dia/semana/sprint, com série histórica e quantidade observada. |
| S05 | Burndown e burnup | Evolução diária de cards restantes e entregues com linha de escopo. Recomenda-se começar por quantidade de cards; horas estimadas não são obrigatórias para todos. |
| S06 | Esforço e custo | Horas previstas quando disponíveis, utilizadas, aprovadas e custo autorizado; informar cobertura das estimativas. Não chamar isso de capacidade sem registrar disponibilidade. |
| S07 | Duração e atraso | Mediana e percentis dos tempos de ciclo, fases mais demoradas, cards em atraso e reaberturas, com tamanho da amostra. |
| S08 | Comparação entre sprints | Entregas, previsibilidade, ciclo, pendências e custo autorizado, preservando o retrato de cada encerramento. |

## Indicadores sugeridos para backlog

| ID | Informação | Definição proposta |
| B01 | Inventário | Total de cards por prioridade, fornecedor, prazo, campo personalizado e situação de atribuição. |
| B02 | Entradas e saídas | Criados, iniciados e concluídos por período, com saldo e tendência de crescimento. |
| B03 | Envelhecimento | Idade desde criação e permanência contínua no backlog, incluindo nova entrada após devolução de sprint. |
| B04 | Itens parados | Mais antigos, sem movimentação recente, sem fornecedor ou com prazo vencido; limiar de dias configurável e visível. |
| B05 | Prontidão para execução | Campos exigidos para a próxima transição ainda não preenchidos. Estimativa só entra se o card a exigir. |
| B06 | Replanejamento | Frequência de retorno ao backlog e histórico de prioridades, quando houver registros suficientes. |

## Gráficos adicionais

Fluxo acumulado por etapa (CFD), trabalho em andamento (Em produção + Em revisão), gargalos por fase, distribuição e tendência do tempo de ciclo e comparação de medianas/percentis. Capacidade, metas de SLA, tempo bloqueado, dependências e story points são possibilidades futuras que exigem validar novos campos ou eventos; não devem ser inferidos a partir dos dados atuais.

## Regras de medição a validar

1. Usar horas corridas inicialmente. Horas úteis exigem jornada, fins de semana, feriados e fuso configurados; não descontar períodos silenciosamente.
2. Reentrada em uma etapa cria nova passagem. Somar passagens por fase e permitir consultar cada uma. Para reabertura, preservar o ciclo original e registrar o novo, sem sobrescrever a primeira conclusão.
3. A fase Concluído é terminal: não somar o tempo parado nela ao esforço ou ao ciclo ativo. Mostrar a data e o tempo desde conclusão, se útil, como informação separada.
4. Exibir intervalo observado, instante de referência, datas de corte e amostra. Em filtros de período, distinguir cards selecionados pela criação/conclusão dos eventos ocorridos dentro do intervalo. Não misturar essas bases no mesmo indicador sem rótulo.
5. Auditar a completude do histórico antes de calcular o passado. Evento ausente implica dado indisponível/incompleto; nunca preencher duração com zero nem inventar timestamps. Encerramento e retorno automático ao backlog também devem integrar o histórico de fases.
6. Sem estimativa ou prazo, mostrar não informado/não se aplica. Taxas com denominador zero precisam ter estado explícito. Dias de calendário não equivalem a horas faturáveis.
7. Tempo bloqueado, calendário útil, capacidade e SLA precisam de nova captura/configuração. Histórico completo de alteração de prazo, prioridade, atribuição e escopo também precisa ser verificado e, onde faltar, registrado antes de prometer métricas retroativas.
8. Não criar ranking subjetivo individual nem atribuir a um fornecedor toda a espera por revisão/aprovação. Comparações devem informar volume, contexto e campos ausentes.

## Sequência recomendada para aprovação

Primeira entrega: C01–C11, C12 autorizado, S01–S04 e S06, B01–B05, detalhe do card e exportações. Foco principal: tempo por fase, tempo total/ciclo, idade atual, horas, aprovação e atraso.
Segunda entrega: S05, S07–S08, B06 e gráficos de fluxo/tendência, após validar consistência do histórico.
Evoluções com novos dados: bloqueios, calendário útil, capacidade/disponibilidade, SLA, dependências e story points, mediante autorização específica.

## Referências

Relatórios de ciclo, fluxo acumulado e sprints foram usados como inspiração; a lista acima é uma proposta para este produto, não promessa de equivalência integral ao Jira.
- https://support.atlassian.com/jira-software-cloud/docs/generate-a-report/
- https://support.atlassian.com/jira-software-cloud/docs/view-and-understand-the-control-chart/
- https://support.atlassian.com/jira-software-cloud/docs/what-is-the-cumulative-flow-diagram/
