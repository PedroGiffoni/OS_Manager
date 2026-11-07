# Estudo de requisitos da Gestão de Demandas

**Versão 1.0 · 06/11/2026 · Base para validação com o setor e contratação do desenvolvimento definitivo**

## 1. Síntese executiva

Gestão de Demandas é um protótipo web funcional para experimentar como a equipe organiza solicitações, distribui trabalho entre profissionais internos e fornecedores, acompanha execução, aprova horas e analisa entregas. A intenção desta etapa é apoiar conversas e testes com o setor. O produto atual torna as regras visíveis e testáveis; este estudo organiza o que o sistema definitivo deverá atender e o que ainda depende de decisão institucional.

O núcleo funcional já cobre backlog, cards configuráveis por atividade, sprints, quadro Kanban, cadastro de fornecedores e tarifas versionadas, apontamento e aprovação de horas, histórico, indicadores, filtros e exportações. Existem controles de autenticação, autorização por permissão e isolamento de dados de fornecedor. A experiência inclui aplicação em português, desenho responsivo e referência visual do Sebrae Ceará.

O sistema ainda não está homologado para uso institucional. SQLite e o serviço gratuito atualmente usado para testes são temporários; dados da publicação gratuita podem ser perdidos. A TI ainda precisa escolher o banco e a hospedagem definitivos, e o setor precisa homologar procedimentos operacionais e financeiros. O desenvolvedor deverá tratar este documento como especificação de partida, confirmar as decisões pendentes antes de fechar arquitetura e preservar o histórico auditável.

### Decisões que devem orientar o desenvolvimento

- Um card pode ser criado sem horas previstas. Quem configura o card decide se o campo aparece e se a resposta será obrigatória.
- O fornecedor vinculado informa as horas utilizadas. Um gestor autorizado decide se aprova ou rejeita esse envio.
- Apenas horas aprovadas multiplicadas pela tarifa congelada na alocação compõem o custo consolidado.
- Fornecedores acessam somente suas próprias atividades e não têm acesso a relatórios, tarifas, custos ou dados de terceiros.
- Alterações confirmadas preservam autoria, data/hora, ação e diferenças disponíveis; registros históricos não são editáveis pela interface.
- Relatórios descrevem tempos corridos e eventos registrados. Eles não representam automaticamente jornada útil, folha, competência contábil ou pagamento.

## 2. Objetivo, público e escopo

### 2.1 Objetivo do produto

Oferecer um ambiente compartilhado para registrar demandas, planejar capacidade por sprint, conduzir atividades por etapas, recolher informações de fornecedores, aprovar apontamentos e analisar o histórico de execução. A plataforma deve ajudar o setor a testar seu processo antes de contratar a implementação institucional.

### 2.2 Público deste estudo

O documento destina-se ao responsável pelo produto, às pessoas do setor que validarão os fluxos, à TI e ao desenvolvedor terceirizado. O setor valida regras e linguagem de trabalho. A TI decide arquitetura institucional, identidade, operação e segurança. O desenvolvedor estima, especifica e implementa a solução final, registrando qualquer divergência aprovada.

### 2.3 Dentro do escopo da V1 definitiva

Gestão de usuários e permissões; fornecedores e versões de tarifa; backlog e cards; campos personalizados individuais; sprints Scrum; Kanban; horas e aprovações; histórico e auditoria; anexos e comentários; dashboards; relatórios de cards, sprint e backlog; filtros e exportações Excel, PDF e HTML; segurança de acesso; administração e operação técnica.

### 2.4 Fora do escopo confirmado

Integrações com GitLab, Power BI, sistemas corporativos, e-mail transacional, mensageria externa ou identidade federada; aplicativo móvel nativo; inteligência artificial; previsão automática de produtividade; avaliação subjetiva de profissionais; apontamento diário e gestão de folha. Qualquer inclusão exige decisão de escopo, responsável, dados envolvidos e critério de aceite.

## 3. Método de levantamento

O estudo combina a leitura da versão local do protótipo, a documentação de arquitetura, permissões, decisões, métricas, filtros, análise operacional e auditoria, o PDF “Pipeline de comunicação dos Produtos de Dados”, a skill Design do Sebrae Ceará e a organização visual do Farol Estratégico 3.0. O pipeline organiza comunicação em cinco perguntas: o que, por quê, para quem, quando e como. Aqui elas foram adaptadas para explicitar objetivo, benefício operacional, perfis, momentos do fluxo e requisitos verificáveis. As onze etapas do processo de comunicação foram usadas como referência de clareza e revisão, não como funções a serem copiadas para o produto.

O Farol Estratégico forneceu referência de hierarquia editorial: cabeçalho institucional, navegação por assunto, síntese executiva, indicadores claramente definidos, gráficos legíveis e detalhamento progressivo. Nenhum dado, regra, meta, script ou integração do Farol foi importado para Gestão de Demandas. A skill Sebrae orienta marca, tipografia, acessibilidade, cores com função, linguagem direta e leitura responsiva.

### 3.1 Situação da evidência

“Implementado” identifica uma função encontrada na aplicação ou na base técnica consultada. “Parcial” identifica função com limites documentados ou lacunas de homologação. “A validar” identifica regra que o setor, a TI ou a área financeira precisa confirmar. O conteúdo descreve o diretório de trabalho local em 06/11/2026, na branch melhorias-relatorios. Algumas alterações recentes de histórico, experiência de horas e diagramação de relatórios estão no diretório local e ainda não foram publicadas. Portanto, este retrato não deve ser confundido com a versão pública atualmente implantada.

## 4. Contexto de uso e resultado esperado

Uma demanda nasce no backlog, recebe responsável e prioridade, pode ser configurada com campos próprios e entra em uma sprint quando a equipe planeja sua execução. Dentro da sprint, o card percorre Backlog, A fazer, Em produção, Em revisão e Concluído. O fornecedor responsável preenche os dados e as horas pertinentes; o gestor com permissão avalia a entrega e o apontamento. A equipe consulta os eventos e indicadores para entender o fluxo e preparar o próximo ciclo.

### 4.1 Cinco perguntas do produto

| Pergunta | Resposta do estudo |
| --- | --- |
| O que o sistema organiza? | Demandas de trabalho, execução em cards, planejamento por sprint e evidências de conclusão. |
| Por que o setor o utiliza? | Para compartilhar estado, responsável, histórico e critérios de aceite e reduzir controles dispersos. O ganho esperado ainda será medido pelo setor. |
| Para quem? | Administradores, gestores, usuários internos autorizados e fornecedores vinculados a atividades. |
| Quando? | Na entrada e priorização de demandas, no planejamento da sprint, durante a execução, na revisão e na análise após entregas ou fechamento. |
| Como? | Fluxos autenticados no navegador, validação das regras no servidor, histórico persistido e análises com escopo autorizado. |

## 5. Retrato funcional da versão de teste

| Módulo | Evidência no protótipo local | Limite conhecido para a versão definitiva |
| --- | --- | --- |
| Acesso | Login por conta individual, sessão em cookie, proteção CSRF e permissões verificadas no servidor. | Homologar política de senha, MFA/SSO, recuperação de conta, retenção e provisionamento. |
| Usuários | Contas com papéis administrador, gestor, interno ou fornecedor e concessões específicas. | A matriz institucional e o ciclo de vida das contas precisam de aprovação da TI. |
| Fornecedores | Cadastro, ativo/inativo, função e versões de tarifa; vínculo opcional com conta. | Troca de responsável em atividade em andamento está bloqueada até aprovação de fluxo. |
| Cards | Dados estruturais, prioridade, prazo, fornecedor, comentários, anexos e campos individuais versionados. | Validar campos mínimos, vocabulário, tamanho dos anexos e retenção. |
| Horas previstas | Configuráveis por card como ausentes, opcionais ou obrigatórias antes de produção. | O setor deve confirmar em quais tipos de demanda a estimativa será usada. |
| Kanban e sprint | Movimento sequencial, ordem persistida, controle de concorrência e fechamento com retorno de pendentes. | Confirmar calendário, feriados, capacidade, critérios de entrada e política de reabertura. |
| Horas e revisão | Versões de apontamento, aprovação/rejeição vinculada à versão e custo pela tarifa congelada. | Confirmar se correções após aprovação exigem reabertura, nova decisão ou lançamento de ajuste. |
| Histórico | Eventos de negócio, autor, data/hora e comparações quando registradas. Atualização local amplia o histórico de horas e campos. | Ainda não é uma trilha criptográfica imutável; definir retenção, consulta administrativa e auditoria institucional. |
| Análise e exportação | Indicadores de cards, tempos por fase, sprint e backlog; Excel/PDF/HTML com recorte. | Relatórios são internos; homologar fórmulas, fuso, semântica financeira e acessibilidade dos arquivos. |
| Infraestrutura | FastAPI, React, SQLite local, migrações Alembic, Compose opcional. Publicação gratuita para testes. | Banco, hosting, backup, monitoramento e capacidade da produção institucional não foram aprovados. |

## 6. Perfis e permissões

O papel identifica o tipo geral de conta. A permissão específica autoriza uma ação. As duas condições são verificadas no backend em cada operação. A concessão financeira não transforma o fornecedor em usuário interno. Usuários devem receber apenas o acesso necessário à sua função.

| Perfil | Responsabilidades esperadas | Restrições centrais |
| --- | --- | --- |
| Administrador | Gerenciar usuários, papéis/concessões e cadastros; operar todas as funções administrativas autorizadas. | Acesso privilegiado deve ficar restrito e auditado. |
| Gestor | Organizar demandas, fornecedores e sprints; acompanhar execução; revisar apontamentos conforme concessão. | approve_hours, view_financial, export_data e export_financial são permissões distintas. |
| Usuário interno autorizado | Criar/configurar cards e operar sprints, consultas ou exportações conforme concessões. | Não ganha aprovação ou dados financeiros somente por ser interno. |
| Fornecedor | Consultar atividades atualmente atribuídas, preencher campos permitidos e informar horas. | Sem tarefas de terceiros, tarifas, custos, auditoria interna, relatórios ou exportações. |

### 6.1 Permissões a manter explícitas

create_tasks, configure_cards, manage_sprints, reopen_sprints, manage_suppliers, change_rates, approve_hours, view_financial, export_data, export_financial e manage_users. O cadastro de usuários e alteração de concessões ficam com administrador na regra atual. A lista definitiva, os responsáveis por concessões e os casos de delegação serão homologados pela TI e pelo dono do processo.

## 7. Requisitos funcionais

Os requisitos abaixo descrevem o comportamento esperado da V1 definitiva. A coluna “estado atual” registra o retrato local e não substitui o critério de aceite da nova contratação.

### 7.1 Acesso, usuários e autorização

| ID | Requisito | Prioridade | Estado atual |
| --- | --- | --- | --- |
| RF-01 | Autenticar cada pessoa com conta individual e permitir encerrar a sessão com segurança. | Obrigatório | Implementado; política institucional pendente. |
| RF-02 | Administrador cadastrar, ativar/desativar e conceder permissões às contas, com registro de autoria. | Obrigatório | Parcial; avaliar revisão de concessões e recuperação de conta. |
| RF-03 | Validar papel, permissão, escopo e vínculo com fornecedor no servidor em todas as operações. | Obrigatório | Implementado no protótipo e coberto por testes de autorização documentados. |
| RF-04 | Restringir fornecedor às próprias atividades e impedir leitura de tarifa, custo, relatório ou informação de terceiros por API, ID, filtro, arquivo ou mensagem. | Obrigatório | Implementado. |
| RF-05 | Separar permissão de aprovação de horas, acesso financeiro, exportação e administração. | Obrigatório | Implementado. |

### 7.2 Fornecedores e valores

| ID | Requisito | Prioridade | Estado atual |
| --- | --- | --- | --- |
| RF-06 | Cadastrar, pesquisar, filtrar, editar e desativar fornecedor sem exigir dado pessoal não necessário. | Obrigatório | Implementado para campos de nome e função. |
| RF-07 | Vincular conta de fornecedor ao cadastro profissional sem misturar identidade de login e cadastro de negócio. | Obrigatório | Implementado; vínculo não é transferível na V1. |
| RF-08 | Criar histórico de tarifa com valor exato, início, autor e justificativa opcional. | Obrigatório | Implementado em centavos inteiros. |
| RF-09 | Ao alocar o fornecedor, congelar versão e valor da tarifa vigentes; preservar alocações anteriores. | Obrigatório | Implementado para nova alocação. |
| RF-10 | Trocar fornecedor com histórico e sem recalcular custos aprovados de forma retroativa. | Obrigatório | Parcial; troca em execução bloqueada. |

### 7.3 Backlog, cards e colaboração

| ID | Requisito | Prioridade | Estado atual |
| --- | --- | --- | --- |
| RF-11 | Criar, editar, buscar, filtrar, priorizar e arquivar demandas com identificador, título e estado nativos. | Obrigatório | Implementado. |
| RF-12 | Configurar campos adicionais para cada card individualmente, sem depender de template global. | Obrigatório | Implementado. |
| RF-13 | Configurar tipo, rótulo, ordem, opções, visibilidade, permissão de edição e obrigatoriedade por transição. | Obrigatório | Implementado com validação no servidor. |
| RF-14 | Permitir salvar card antes de preencher campos obrigatórios de fases posteriores. | Obrigatório | Implementado. |
| RF-15 | Manter dados nativos de horas e custos separados dos campos personalizados. | Obrigatório | Implementado. |
| RF-16 | Versionar schema e valores; ao alterar configuração, preservar valor anterior e tornar a mudança auditável. | Obrigatório | Implementado; revisão lado a lado ainda não existe. |
| RF-17 | Permitir comentário e anexo associados ao card e respeitar seu escopo de acesso. | Desejável para validação do processo | Implementado, com limite de anexo documentado. |

### 7.4 Sprints e fluxo Kanban

| ID | Requisito | Prioridade | Estado atual |
| --- | --- | --- | --- |
| RF-18 | Criar sprint com nome, objetivo, datas válidas, responsável e estado planejada/ativa/encerrada. | Obrigatório | Implementado. |
| RF-19 | Incluir atividade elegível em sprint e impedir vínculo simultâneo em duas sprints ativas. | Obrigatório | Implementado com transação e restrição. |
| RF-20 | Exibir quadro por etapa e permitir mover/ordenar cards com mouse e alternativa de teclado/menu. | Obrigatório | Implementado. |
| RF-21 | Validar no servidor permissão, campos obrigatórios, sequência, versão e estado da sprint antes de mover. | Obrigatório | Implementado. |
| RF-22 | Em erro, manter origem/ordem e informar claramente o que falta; horas previstas aparecem como alerta vermelho sobreposto quando exigidas. | Obrigatório | Implementado. |
| RF-23 | Encerrar sprint registrando responsável e momento, congelando visão histórica e devolvendo pendentes ao backlog. | Obrigatório | Implementado. |
| RF-24 | Reabrir sprint somente com permissão específica e justificativa, preservando fechamentos anteriores. | Obrigatório | Implementado. |
| RF-25 | Manter sprints encerradas em leitura, salvo reabertura auditada. | Obrigatório | Implementado. |

### 7.5 Apontamento, aprovação e custos

| ID | Requisito | Prioridade | Estado atual |
| --- | --- | --- | --- |
| RF-26 | Permitir ao responsável criar card sem estimativa prevista quando o schema não exigir esse campo. | Obrigatório | Implementado. |
| RF-27 | Quando estimativa estiver configurada como obrigatória, exigir valor positivo antes de iniciar produção. | Obrigatório | Implementado. |
| RF-28 | Somente o fornecedor atribuído informa ou edita horas utilizadas; o sistema confirma gravação e oferece edição posterior. | Obrigatório | Implementado; melhorias locais registram autoria/diferença no histórico. |
| RF-29 | Exigir horas utilizadas positivas para envio à revisão. | Obrigatório | Implementado. |
| RF-30 | Gestor/admin com approve_hours aprovar ou rejeitar uma versão e registrar instante, autor e justificativa. | Obrigatório | Implementado. |
| RF-31 | Rejeição mantém o card em revisão e permite corrigir e reenviar uma nova versão. | Obrigatório | Implementado. |
| RF-32 | Somente gestor/admin autorizado conclui card após aprovação da versão corrente. | Obrigatório | Implementado. |
| RF-33 | Calcular consolidado somente com horas aprovadas vigentes e tarifa congelada da alocação. | Obrigatório | Implementado em centavos/minutos inteiros e Decimal. |
| RF-34 | Reabrir concluído somente por gestor/admin com motivo; retirar a aprovação do consolidado atual sem apagar decisão anterior. | Obrigatório | Implementado. |

### 7.6 Histórico, relatórios e administração

| ID | Requisito | Prioridade | Estado atual |
| --- | --- | --- | --- |
| RF-35 | Registrar eventos de negócio com ator, data/hora UTC, entidade, ação, identificador e diferenças disponíveis. | Obrigatório | Implementado; atualização local amplia eventos de horas e alterações de card. |
| RF-36 | Disponibilizar histórico interno do card com sequência temporal, autor, valores anteriores/novos e justificativas. | Obrigatório | Implementado localmente; confirmar publicação e política de retenção. |
| RF-37 | Bloquear edição ou exclusão de evento pela interface e proteger dados privados/financeiros por permissão. | Obrigatório | Implementado no protótipo; acesso direto ao banco exige controles operacionais futuros. |
| RF-38 | Exibir dashboard derivado de dados persistidos com filtros por período, sprint, fornecedor e estado. | Obrigatório | Implementado. |
| RF-39 | Analisar cards, fases/ciclos, sprint e backlog, identificando lacunas históricas. | Obrigatório | Implementado; tempos são corridos e podem ser indisponíveis em registros sem eventos. |
| RF-40 | Permitir campos visíveis do card como filtros tipados, exceto descrição, combinados por E. | Obrigatório | Implementado. |
| RF-41 | Oferecer ao administrador atalho “Relatório completo” para limpar todos os filtros. | Desejável | Implementado localmente no produto. |
| RF-42 | Exportar recorte autorizado para Excel, PDF e HTML; custos apenas com permissões financeiras próprias. | Obrigatório | Implementado; nova diagramação HTML/PDF no diretório local. |
| RF-43 | Impedir relatório e exportação de qualquer formato para fornecedor, inclusive por URL direta. | Obrigatório | Implementado no servidor e navegação. |

## 8. Regras de negócio

| ID | Regra |
| --- | --- |
| RN-01 | O fluxo base segue esta ordem: Backlog, A fazer, Em produção, Em revisão e Concluído. Não se pode pular etapas. |
| RN-02 | Retornos comuns são bloqueados. A única exceção implementada é reabrir Concluído para Em revisão por gestor/admin, com justificativa. |
| RN-03 | Estimativa prevista é opcional por padrão e configurável por card. Se configurada como obrigatória, deve ser positiva antes de Em produção. |
| RN-04 | Horas utilizadas precisam ser positivas antes de enviar para revisão. O total informado não exige apontamento diário na V1. |
| RN-05 | Só a conta vinculada ao fornecedor atualmente atribuído pode criar e editar o apontamento do card. |
| RN-06 | Uma aprovação sempre se refere a uma versão específica das horas. Reenvio cria nova versão; aprovação repetida da mesma decisão é idempotente. |
| RN-07 | Rejeição exige motivo, mantém o card Em revisão e sinaliza correção ao fornecedor. |
| RN-08 | Conclusão exige aprovação da versão atual. Fornecedor não conclui e gestor sem approve_hours não aprova. |
| RN-09 | Custo atual elegível = horas utilizadas aprovadas da versão vigente × tarifa em vigor congelada na alocação. |
| RN-10 | Horas previstas não entram em custo; apontamento não aprovado ou rejeitado não entra no consolidado. |
| RN-11 | Valores monetários permanecem exatos em centavos; horas são armazenadas em minutos. Apresentação financeira usa duas casas e arredondamento ROUND_HALF_UP. |
| RN-12 | Reabertura preserva a aprovação anterior como registro, mas a remove do consolidado corrente até nova submissão e aprovação. |
| RN-13 | Reajuste de tarifa não altera alocações ou custos históricos já congelados. |
| RN-14 | Troca de fornecedor em execução não é liberada automaticamente; depende de fluxo institucional para encerrar alocação preservando apontamentos e custos. |
| RN-15 | Uma atividade só pode ter um vínculo ativo com sprint por vez. |
| RN-16 | Ao encerrar sprint, tarefas concluídas mantêm o vínculo histórico e tarefas pendentes voltam visualmente ao backlog, com fase anterior preservada no histórico. |
| RN-17 | Reabrir sprint não recolhe tarefas já devolvidas ou replanejadas; apenas reativa vínculos que ainda pertencem a ela. |
| RN-18 | Arquivamento auditado substitui exclusão operacional. Tarefa com execução/apontamentos/sprint e sprint com vínculos não são apagadas pela interface. |
| RN-19 | Período de relatório usa data de criação UTC do card. Esse recorte não define competência financeira ou pagamento. |
| RN-20 | Duração por fase é tempo corrido entre eventos, incluindo noite/fim de semana. Não equivale a horas trabalhadas. |
| RN-21 | Lead time vai da criação à primeira conclusão; cycle time vai do início da produção à conclusão. Reabertura inicia um novo ciclo. |
| RN-22 | Data ausente não classifica o card como atrasado; denominador zero gera 0%/estado vazio, sem divisão inválida. |
| RN-23 | Campo personalizado só se aplica a cards cujo schema o contém. Campos com mesmo rótulo e IDs diferentes são filtros distintos. |
| RN-24 | Campo de descrição não entra no catálogo de filtros. Filtros combinam por E e validam tipo, visibilidade, escopo e permissão no servidor. |
| RN-25 | Fornecedor não recebe relatório, tarifa, custo, auditoria interna ou dados de outra pessoa. O bloqueio vale para endpoint, filtro, exportação e URL. |

## 9. Fluxos operacionais principais

### 9.1 Demanda até execução

1. Usuário interno autorizado cria card com título, descrição e dados estruturais disponíveis.
2. O criador define fornecedor, prioridade, prazo, campos próprios e política de estimativa prevista.
3. O fornecedor entra em uma sprint ativa ou permanece no backlog, conforme planejamento.
4. A equipe move o card ao longo do fluxo; cada transição valida regra, permissão e versão do registro.
5. O servidor registra a mudança e atualiza indicadores derivados do histórico.

### 9.2 Horas, revisão e encerramento

1. Se a estimativa for obrigatória no card, o fornecedor informa horas previstas antes da produção.
2. Antes da revisão, o fornecedor salva horas utilizadas. A tela confirma “salvo” e permite editar ou reapresentar conforme o estado.
3. Gestor autorizado abre a fila de revisão. Aprovação ou rejeição registra autor, hora, versão e motivo.
4. Na rejeição, o card permanece em revisão. O fornecedor corrige e cria nova versão do apontamento.
5. Após aprovação da versão corrente, gestor autorizado conclui. O custo elegível usa a tarifa congelada na alocação.
6. Reabertura exige motivo e preserva a decisão anterior, retirando-a do custo consolidado corrente enquanto não houver nova aprovação.

### 9.3 Ciclo de sprint

Gestor ou usuário interno com manage_sprints planeja a sprint e associa cards elegíveis. O início define compromisso e estado. O fechamento grava autor, instante e snapshot. Pendentes voltam ao backlog; concluídos ficam associados ao histórico da sprint. Reabertura formal registra motivo e não reverte replanejamentos posteriores.

## 10. Modelo de informação

| Entidade | Conteúdo principal | Integridade esperada |
| --- | --- | --- |
| Usuário, sessão, papel e permissão | Conta, hash da senha, concessões e sessão segura. | Nome de usuário único; sessão revogável; concessões efetivas no servidor. |
| Fornecedor e tarifa | Cadastro, conta vinculada e histórico de valores. | Tarifa positiva, com autor e vínculo à versão histórica. |
| Atividade/card | Título, descrição, estado, prioridade, prazo, criador, fornecedor e concorrência. | Estado permitido, versão otimista e referência preservada. |
| Alocação | Card, fornecedor, versão/valor da tarifa congelada e vigência da alocação. | Um vínculo ativo; trocar não reescreve alocações anteriores. |
| Sprint e vínculo | Período, objetivo, responsável, estado e relação de cards. | Datas válidas; um vínculo ativo por card; snapshots de fechamento. |
| Schema/valores do card | Campos, opções, visibilidade, obrigatoriedade e valores por versão. | Validação tipada; nenhuma exclusão silenciosa de valor. |
| Horas | Versão, minutos previstos/utilizados, autor e instante. | Uma submissão por versão; fornecedor atribuído como autor. |
| Aprovação | Decisão, justificativa, autor, versão de horas, alocação e sprint de referência. | Não aprovar versão inexistente nem recalcular com tarifa corrente. |
| Auditoria | Ator, instante, objeto, ação, comparação e metadados mínimos. | Sem edição/exclusão pela UI; transação alinhada ao evento de negócio. |
| Comentário/anexo | Conteúdo ou metadados, objeto, autor e instante. | Escopo do card; limite/tipo do arquivo; hash de integridade. |

A modelagem atual centraliza acesso SQLAlchemy, usa Alembic para alterações e SQLite em arquivo temporário. Para a produção, a TI definirá o SGBD. O desenvolvedor deverá testar tipos, índices, constraints, isolamento, transações, concorrência e migrações no SGBD homologado. A migração de SQLite não é automática.

## 11. Relatórios, indicadores e exportações

### 11.1 Cards e fluxo

O relatório deve oferecer etapa atual, responsável, prioridade, prazo, idade do card, idade da etapa, primeira conclusão, último ciclo, passagens, reaberturas, aprovações e histórico disponível. Tempos por fase derivam das datas de transição. Se faltar evidência, o relatório apresenta “indisponível” ou o período observado, sem reconstrução inventada.

### 11.2 Sprint e backlog

Para sprint: compromisso inicial, entradas posteriores, planejados, concluídos, pendentes, devolvidos, taxa de conclusão, evolução ao longo da sprint e snapshot do encerramento. Para backlog: volume, distribuição de prioridade/idade/estado, entradas e saídas no período e prontidão dos campos visíveis. A definição atual considera parado um card sem atualização por sete dias, limiar indicativo e ajustável; o setor precisa validar esse parâmetro.

### 11.3 Métricas objetivas

- Taxa de conclusão = concluídas ÷ planejadas × 100.
- Pendentes = planejadas − concluídas.
- Em atraso = pendentes com prazo anterior à data corrente no fuso configurado.
- Horas previstas/utilizadas = soma de minutos ÷ 60. Desvio = utilizadas − previstas.
- Pontualidade = cards concluídos no prazo ÷ concluídos com prazo × 100.
- Lead time e cycle time usam os marcos descritos na RN-21.
- Custo consolidado = minutos aprovados × centavos/hora congelados ÷ 60, com arredondamento definido.

Métricas devem mostrar período, filtros, unidade e fórmula acessível. Não classificar produtividade individual com score subjetivo. A inclusão de custos é opcional e depende de view_financial e export_financial.

### 11.4 Apresentação dos arquivos

Excel deve preservar os filtros e evitar execução de fórmulas inseridas como texto. PDF deve ser pesquisável e legível, com capítulos, cabeçalho/rodapé, paginação e tabelas que não cortem linhas. HTML é retrato estático, offline e com dados incorporados; só usuários internos podem gerar os arquivos. A aplicação atual utiliza modelo visual editorial inspirado no Farol, sem reutilizar dados ou código daquele produto.

## 12. Requisitos não funcionais

| ID | Requisito de qualidade |
| --- | --- |
| RNF-01 Segurança | Hash forte de senha, sessão HttpOnly, SameSite e Secure sob HTTPS, proteção CSRF/origem, rate limit e erros sem dados sensíveis. Homologar MFA/SSO com a TI. |
| RNF-02 Autorização | Verificar papel, concessão e escopo no backend em consultas, mutações, URLs, anexos, lotes, dashboards e exportações. Testar IDOR horizontal e vertical. |
| RNF-03 Privacidade | Minimizar dados pessoais; mascarar/omitir tarifa e custo sem autorização, inclusive em HTML, metadados, log e resposta de erro. Definir aviso, retenção e descarte institucional. |
| RNF-04 Integridade | Usar transações, chaves estrangeiras, constraints e controle de concorrência/idempotência em transições, sprints e aprovações. |
| RNF-05 Exatidão | Não usar ponto flutuante para dinheiro. Armazenar centavos/minutos inteiros ou tipos exatos homologados. Guardar timestamps em UTC e apresentar em fuso configurável. |
| RNF-06 Evolução | Separar interface, API, regras e persistência; usar migrações reversíveis quando viável. Não amarrar regra de negócio a React nem a SQL específico de SQLite. |
| RNF-07 Acessibilidade | Navegação por teclado, foco visível, labels, contraste AA, avisos anunciados por leitor de tela, alvos operáveis e ausência de overflow a 390 px. |
| RNF-08 Usabilidade | Interface pt-BR, formatos locais, carregamento/vazio/erro claros, transição inválida sem mover card e confirmação visível ao salvar horas. |
| RNF-09 Desempenho | Definir metas com volume esperado do setor. Testar consultas, filtros, relatórios, anexos e exportação sob carga antes de homologar. Não há SLO institucional definido. |
| RNF-10 Disponibilidade | Produção precisa de backup e recuperação testados, monitoramento e plano de incidente. Hospedagem gratuita de testes não satisfaz requisito de disponibilidade. |
| RNF-11 Observabilidade | Registrar evento técnico sem senha, cookie, corpo financeiro ou conteúdo sensível. Separar log operacional do histórico funcional. |
| RNF-12 Compatibilidade | Homologar navegadores, leitor de tela, dispositivos e SGBD corporativo com a TI. Aplicação web responsiva é a V1. |
| RNF-13 Portabilidade | Validar plano de exportação, integridade e rollback após escolha do banco; não prometer conversão automática do SQLite. |
| RNF-14 Retenção | Definir prazos para contas, auditoria, anexos, comentários, aprovações e dados financeiros com as áreas responsáveis. |

## 13. Segurança, privacidade e auditoria

O servidor é a fronteira de confiança. A interface pode ocultar ações, mas a API sempre revalida o escopo. Tentativas diretas de consultar cards alheios devem retornar sem informação identificável. Exportação reutiliza filtros e autorização da consulta. Custos não devem aparecer em HTML ou PDF sem permissão, inclusive em texto extraído, detalhes colapsados e metadados.

O histórico registra ações confirmadas, não digitação, cliques nem rascunhos. Autoria e instante são preservados; valores financeiros e campos ocultos obedecem à permissão e visibilidade. Comparações que não existiam antes da gravação não podem ser inventadas. A implementação atual guarda a auditoria no mesmo banco transacional. A V1 definitiva deve definir como limitar alteração direta por administradores de banco, exportar trilha para guarda independente, reter evidências e responder a solicitações de acesso/eliminação.

## 14. Critérios mínimos de aceite

| ID | Cenário de aceitação | Resultado esperado |
| --- | --- | --- |
| CA-01 | Criar card com horas previstas ausentes e campo não configurado. | Card salva; pode seguir conforme demais validações. |
| CA-02 | Tornar horas previstas obrigatórias e tentar iniciar sem valor. | Servidor bloqueia a transição, mantém origem/ordem e mostra aviso claro em vermelho. |
| CA-03 | Fornecedor atribuído grava horas utilizadas, fecha e reabre o card. | Interface mostra confirmação de salvo, muda para Editar e mantém versão anterior no histórico com ator/hora/diferença. |
| CA-04 | Fornecedor tenta atualizar hora de card de terceiro por ID. | API nega sem revelar existência ou dados da atividade. |
| CA-05 | Gestor sem approve_hours tenta aprovar. | API retorna não autorizado; estado e custo não mudam. |
| CA-06 | Gestor autorizado rejeita apontamento com motivo. | Card permanece Em revisão; motivo aparece para responsável; correção cria nova versão. |
| CA-07 | Aprovar 8 horas com tarifa congelada de R$ 120/h após reajuste para R$ 150/h. | Custo permanece R$ 960,00. |
| CA-08 | Concluir com horas pendentes/rejeitadas ou por fornecedor. | Operação é bloqueada; card fica Em revisão. |
| CA-09 | Reabrir tarefa concluída. | Exige gestor e justificativa; histórico anterior persiste; custo corrente deixa de incluir aprovação até novo aceite. |
| CA-10 | Encerrar sprint com tarefa pendente. | Tarefa retorna ao backlog, conserva histórico/fase, valores, horas, anexo e vínculo histórico. |
| CA-11 | Vincular uma atividade simultaneamente a duas sprints ativas. | Transação é recusada e integridade permanece válida. |
| CA-12 | Alterar schema do card com valores já preenchidos. | Nova versão preserva dados e regras nativas; nenhuma perda silenciosa. |
| CA-13 | Fornecedor chama relatório, exportação ou rota de análise por URL. | API nega em todos os formatos; menu não oferece a função. |
| CA-14 | Usuário interno sem permissão financeira exporta relatório filtrado. | Arquivo não contém tarifa/custo em dados, abas, metadados ou texto oculto. |
| CA-15 | Alterar dois cards em concorrência ou repetir aprovação da mesma versão. | Conflito retorna resposta controlada; não duplica movimento/aprovação/custo. |
| CA-16 | Consultar duração de card com histórico incompleto ou sem prazo. | Sistema indica indisponibilidade/ausência e não inventa duração nem atraso. |

## 15. Plano de validação com o setor

Os participantes devem executar os fluxos como usuários reais, com dados fictícios. Para cada cenário, registrar exemplo observado, decisão, exceção e pessoa responsável por homologar. O teste deve priorizar regras com impacto financeiro ou de acesso.

| Sessão | Tema | Questões para fechar |
| --- | --- | --- |
| 1 | Entrada e priorização | Quem pode criar? Que campos são mínimos? Como a prioridade é ordenada? Como arquivar duplicidades? |
| 2 | Campos do card | Quais campos são úteis? Quem pode alterar? Quais transições exigem resposta? O que fazer com valores quando um campo deixa de aparecer? |
| 3 | Sprint e Kanban | Qual evento inicia sprint? Como tratar cancelamento, atraso e retorno de etapa? O que significa “parado”? |
| 4 | Fornecedor e horas | Quem aprova tarifa e alocação? Como trocar profissional em andamento? Como corrigir hora já aprovada? Há teto ou unidade mínima? |
| 5 | Custos e relatórios | O filtro por criação UTC atende? Qual visão financeira cada perfil precisa? Que indicadores serão usados na rotina? |
| 6 | TI, segurança e operação | SGBD, hosting, SSO/MFA, backups, recuperação, logs, retenção, suporte, acessibilidade e níveis de serviço. |

Ao final, o responsável pelo produto aprova os fluxos funcionais. A área financeira aprova fórmula, arredondamento, período e correções. A TI aprova identidade, infraestrutura, banco, segurança, backup e suporte. Decisões devem ficar datadas em ata e em versão atualizada do documento.

## 16. Decisões pendentes e riscos

| Tema | Posição observada | Decisão/validação necessária |
| --- | --- | --- |
| Banco e hospedagem | SQLite local e serviço gratuito servem apenas a testes. | TI define tecnologia, segregação de ambiente, retenção, backup e recuperação. |
| Persistência de testes | Render Free pode apagar banco/anexos/sessões em suspensão ou novo deploy. | Continuar com dados descartáveis ou selecionar ambiente persistente autorizado para piloto. |
| Identidade | Login local com hash de senha, cookie e CSRF. | TI decide diretório corporativo, SSO, MFA, senha, recuperação e desligamento de conta. |
| Retenção de auditoria | Histórico segue no banco operacional; sem cadeia criptográfica externa. | Compliance/TI definem prazo, acesso administrativo e guarda independente. |
| Troca de fornecedor | Bloqueada em execução e após submissões de hora. | Desenhar liquidação parcial e atribuição de períodos/horas. |
| Correção aprovada | Reabertura remove aprovação da projeção atual e preserva histórico. | Financeiro determina aditivo, estorno, substituição ou reconciliação. |
| Competência financeira | Filtro atual usa data de criação do card. | Financeiro decide período de relatório e eventual competência da aprovação. |
| Calendário de trabalho | Duração usa horas corridas. | Setor decide se precisa expediente, feriados ou calendário institucional. |
| SLA e capacidade | Sem meta de performance ou volume definida. | Dono do produto fornece usuários, cards ativos, anexos, concorrência e expectativas. |
| Notificações | Sem serviço externo; fornecedor consulta o estado no card. | Setor decide se aviso interno é suficiente ou se uma integração é requisito futuro. |
| Acessibilidade dos relatórios | HTML e interface usam movimento reduzido; PDF é validado visualmente. | TI deve definir a avaliação formal de acessibilidade dos arquivos exportados. |

## 17. Arquitetura e orientação para o desenvolvedor

### 17.1 Base técnica do protótipo

Frontend React + TypeScript + Vite consome API REST FastAPI em /api/v1. SQLAlchemy 2 concentra modelos e persistência. Alembic controla o esquema. SQLite é o banco local atual. Excel, PDF e HTML são gerados no backend após aplicação de filtros e escopo. Pytest, Vitest/Testing Library e Playwright exercitam as camadas.

### 17.2 Diretrizes para a plataforma oficial

1. Preserve contratos de negócio enquanto a TI seleciona SGBD e identidade. Separe adaptações de infraestrutura das regras da aplicação.
2. Produza diagramas de contexto, componentes, implantação e dados com os limites de confiança e fluxos financeiros.
3. Defina APIs versionadas, autorização centralizada e resposta padronizada para conflito, transição inválida e acesso negado.
4. Use migrações versionadas, backup e restauração testados, observabilidade sem segredo e segregação entre desenvolvimento, homologação e produção.
5. Implemente testes de regras, autorização, integração, exportação e E2E para os cenários de aceite antes de pedir homologação.
6. Documente decisões que alterem uma regra deste estudo e peça aceite do responsável pela regra antes de divergir.

### 17.3 Critério de conclusão do desenvolvimento

A equipe do setor percorre o fluxo completo com perfis distintos e dados fictícios; a TI aprova arquitetura e controles; os cenários CA-01 a CA-16 passam em ambiente de homologação; as áreas donas aprovam métricas e custos; e o responsável pelo produto confirma que documentação, migrações, operação, suporte e treinamento acompanham a entrega.

## 18. Referências usadas

- “Pipeline de comunicação dos Produtos de Dados”, Sebrae/CE, arquivo PDF fornecido nesta conversa, 20 páginas, nov. 2026. Usado para estrutura de propósito, público, momento, linguagem e validação.
- Skill Design System SEBRAE-CE fornecida no projeto. Usada para marca, linguagem, tipografia, contraste e acessibilidade.
- Farol Estratégico 3.0, arquivo HTML fornecido anteriormente. Usado somente como referência visual de hierarquia editorial e navegação de relatório.
- Código e documentação local do projeto Gestão de Demandas, branch melhorias-relatorios, verificação em 06/11/2026: README.md, ARCHITECTURE.md, PERMISSIONS.md, DECISIONS.md, METRICS.md, REPORT_FILTERS.md, OPERATIONAL_ANALYTICS.md, AUDIT_TRAIL.md, KNOWN_LIMITATIONS.md, modelos, rotas e componentes da aplicação.

## Apêndice A. Vocabulário

| Termo | Definição neste estudo |
| --- | --- |
| Card/atividade | Registro de uma demanda de trabalho com dados, estado, responsável e histórico. |
| Alocação | Vínculo histórico entre card e fornecedor com tarifa congelada. |
| Horas previstas | Estimativa de planejamento. Opcional por card, exceto quando configurada como obrigatória. |
| Horas utilizadas | Total informado pelo fornecedor para a atividade e submetido à revisão. |
| Aprovação vigente | Decisão aceita que corresponde à versão atual considerada no custo consolidado. |
| Snapshot | Retrato de dados/indicadores capturado em um evento, como fechamento de sprint. |
| Tempo por fase | Durações corridas entre mudanças de estado registradas; não é folha de ponto. |
| IDOR | Acesso indevido a objeto de outra pessoa alterando um identificador em URL ou requisição. |
