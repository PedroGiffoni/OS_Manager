# Histórico de versões do card

## O que é registrado

Cada alteração de negócio confirmada guarda autor (ID e nome de usuário no instante da ação), instante UTC, tipo de evento e referência ao card. A interface apresenta data/hora local, número do registro e comparação antes/depois quando disponível.

- Criação: dados estruturais iniciais e política de estimativa.
- Edição do card: título, descrição, prazo, prioridade e fornecedor antes/depois.
- Horas: cada submissão mantém sua versão, horas previstas/utilizadas, valores anteriores/novos, autor e situação de aprovação. Preenchimento, edição e reapresentação não sobrescrevem as versões anteriores da tabela task_hours.
- Campos/configuração: versões do schema e diferenças de configuração/valores por campo.
- Fluxo: movimentação, reabertura com motivo, ordenação, alocação, inclusão em sprint e devolução ao backlog.
- Aprovação/rejeição: decisão, motivo e versão das horas avaliada.
- Colaboração: comentário com conteúdo/ID; anexo com ID, nome, tamanho e SHA-256, sem duplicar seu binário no log.
- Arquivamento: registro do evento preservado.

A ação e sua auditoria são confirmadas na mesma transação. Requisições recusadas não geram uma falsa versão de alteração concluída. Cliques, rascunhos não salvos e digitação não são versões de negócio; não há gravação de tela nem monitoramento de teclado.

## Consulta e proteção

Aba Histórico do card: linha do tempo com autor, instante e comparação por evento. Usuários internos também podem selecionar dois registros e ver a diferença líquida entre eles (valores inicial/final e etapa), incluindo mudanças revertidas dentro do intervalo somente quando o resultado final for diferente. A comparação usa exclusivamente os detalhes devolvidos pela API com as permissões do usuário. GET /api/v1/audit?entity=task&identity=ID permanece restrito a usuários internos. Fornecedores continuam podendo preencher horas, mas não recebem acesso à auditoria interna nem aos relatórios.

Campos privados respeitam tanto a visibilidade registrada no evento como a configuração atual. Informações financeiras seguem permissões próprias, inclusive em estruturas aninhadas. Textos são exibidos como conteúdo React, sem HTML executável. Não existem endpoints para alterar ou excluir eventos de auditoria.

A comparação com GitHub é uma referência de experiência: autoria, sequência e diferenças. Não é controle de versões Git nem assinatura criptográfica inviolável; administradores com acesso direto ao banco precisam de governança própria.

## Histórico anterior e infraestrutura

Eventos anteriores permanecem intactos. A comparação entre registros agrega diferenças auditadas; eventos antigos sem detalhes de alteração não permitem reconstruir campos que não foram registrados e são apresentados como sem diferença registrada. Não se inventam valores retroativos. As versões de horas já existentes na tabela task_hours são preservadas. Não foi necessário alterar o esquema físico: detalhes usam JSON e tabelas versionadas existentes.

O histórico reside no mesmo SQLite da aplicação. Em execução local/Compose com volume ele acompanha a persistência do banco. No Render Free configurado para testes descartáveis, banco e histórico podem desaparecer em suspensão, reinício ou redeploy. Persistência institucional e retenção exigem uma decisão de infraestrutura e homologação; não estão garantidas pelo ambiente gratuito atual.
