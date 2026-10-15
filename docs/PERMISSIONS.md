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
| Exportar operacional | export_data; fornecedor exporta somente seu escopo |
| Exportar financeiro | admin/manager, export_data, view_financial e export_financial |
| Gerenciar concessões/criar usuários | somente administrador; listagens exigem manage_users |
| Informar horas | somente conta supplier vinculada ao fornecedor atualmente atribuído |
| Mover cards | gestor/administrador ou fornecedor atribuído; regras nativas permanecem obrigatórias |
| Concluir/reabrir tarefa concluída | somente gestor/administrador; conclusão exige aprovação atual; reabertura exige justificativa |

Concessões financeiras em um perfil internal não removem as restrições de papel. Editar campos personalizados também exige o perfil em editable_by e visible_to; as regras nativas nunca são configuráveis. Fornecedor não recebe schemas/valores ocultos para seu perfil. Campos de referência são validados no servidor, incluindo anexos pertencentes ao mesmo card.

Revogar concessão afeta a próxima requisição, inclusive de sessão já autenticada. A interface pode exigir recarregamento para atualizar a navegação; o servidor já recusa a operação. Arquivos baixados anteriormente não podem ser revogados retroativamente.