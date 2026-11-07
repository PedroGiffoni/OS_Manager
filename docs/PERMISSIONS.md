# Permissões

Papel não concede automaticamente poderes financeiros ao gestor. Administrador é a autoridade de configuração; os demais perfis dependem das concessões e das restrições de papel/escopo do servidor.

| Ação | Regra |
| --- | --- |
| Criar/editar/arquivar tarefa sem execução | create_tasks, usuário interno |
| Configurar card individual | create_tasks ou configure_cards |
| Gerenciar sprint | manage_sprints, usuário interno |
| Reabrir sprint | manage_sprints e reopen_sprints, com justificativa |
| Cadastrar/editar fornecedor | admin/manager e manage_suppliers |
| Criar versão de tarifa | admin/manager e change_rates |
| Ver tarifa/custo | admin/manager e view_financial |
| Aprovar/rejeitar horas | admin/manager e approve_hours |
| Exportar operacional | usuário interno com export_data; fornecedor não consulta nem exporta relatórios |
| Exportar financeiro | admin/manager, export_data, view_financial e export_financial |
| Gerenciar concessões/criar usuários | somente administrador; listagens exigem manage_users |
| Criar releases, componentes, dependências e capacidade | manage_planning e manage_capacity; concessões explícitas para gestores |
| Configurar transições e automações | manage_workflows e manage_automation; validações nativas não são removíveis |
| Atribuir responsável em regra automática | manage_workflows ou manage_automation; somente contas internas ativas, sem mudar a atribuição do fornecedor |
| Criar widgets pessoais | usuário autenticado; fornecedor recebe apenas dados do próprio escopo |
| Compartilhar visualização/widget | manage_planning; compartilhamento não concede acesso a custos |
| Gerenciar grupos de compartilhamento | somente administrador; membros precisam ser contas internas ativas. Acesso por grupo não contorna escopo financeiro nem inclui fornecedores |
| Acompanhar atividade/receber notificações | somente atividades visíveis no escopo atual; notificações revalidam acesso em cada consulta |
| Gerenciar assinatura de filtro | usuário autenticado administra somente as próprias assinaturas; resultados e notificações usam o escopo atual, inclusive fornecedor |
| Informar horas | somente conta supplier vinculada ao fornecedor atualmente atribuído |
| Mover cards | gestor/administrador ou fornecedor atribuído; regras nativas permanecem obrigatórias |
| Concluir/reabrir tarefa concluída | somente gestor/administrador; conclusão exige aprovação atual; reabertura exige justificativa |

Concessões financeiras em um perfil internal não removem as restrições de papel. Editar campos personalizados também exige o perfil em editable_by e visible_to; as regras nativas nunca são configuráveis. Fornecedor não recebe schemas/valores ocultos para seu perfil. Campos de referência são validados no servidor, incluindo anexos pertencentes ao mesmo card.

Revogar concessão afeta a próxima requisição, inclusive de sessão já autenticada. A interface pode exigir recarregamento para atualizar a navegação; o servidor já recusa a operação. Arquivos baixados anteriormente não podem ser revogados retroativamente.
Fornecedor não acessa /reports/* ou /exports/*, em nenhum formato, nem por URL direta. A navegação oculta Relatórios; o backend retorna 403 inclusive para cards próprios. A visão geral e as tarefas próprias continuam disponíveis.
