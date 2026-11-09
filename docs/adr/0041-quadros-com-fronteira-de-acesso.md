# ADR 0041: Quadros como fronteiras de acesso

## Estado

Aceito

## Contexto

A aplicação precisa permitir espaços de trabalho distintos para operação interna e fornecedores, com associação explícita de usuários. O modelo atual guarda tarefas e configurações de planejamento em tabelas globais. Filtrar apenas na interface permitiria acesso horizontal por API e misturaria dashboards, filtros, sprints e regras.

## Decisão

- Cada quadro é uma unidade de dados e de autorização.
- Cards, sprints e configurações de planejamento recebem `board_id`; consultas autenticadas são limitadas ao quadro ativo no servidor.
- A associação usuário/quadro é explícita. Administradores acessam todos os quadros e são os únicos que os criam e administram seus membros.
- Fornecedores também precisam de acesso ao quadro e continuam limitados a cards atribuídos a eles.
- Migração preserva os registros existentes em um quadro principal, sem apagar ou reescrever histórico de cards.
- A interface deste marco não oferece exclusão de quadros; dados e histórico permanecem preservados.
- O downgrade da migração é permitido somente enquanto existir o quadro principal; após a criação de outros quadros, uma consolidação explícita é necessária para evitar perda de configuração.

## Consequências

- Toda rota que consulta dados de quadro deve usar o escopo de sessão no backend, inclusive consultas por ID, agregações, notificações e exports.
- Jobs assíncronos sem sessão de usuário percorrem os quadros explicitamente.
- Relações entre cards e sprints de quadros diferentes são inválidas.
- Dashboard e filtros permanecem por usuário, mas vinculados ao quadro onde foram criados.
