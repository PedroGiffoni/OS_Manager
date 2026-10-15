# Estado da publicação — 15/10/2026

- Repositório definido pelo usuário: https://github.com/PedroGiffoni/OS_Manager (público, confirmado vazio antes do primeiro envio).
- Projeto Vercel criado: `os-manager`, ID `prj_PKwsor6tp6P45rl95susS2X6ysm4`, conta `pedro-giffoni-s-projects`.
- Painel: https://vercel.com/pedro-giffoni-s-projects/os-manager
- Autenticação CLI concluída; `vercel project inspect` confirmou nome, proprietário e configuração Vite.
- A integração Vercel criou o projeto, mas sua consulta com teamId recebeu HTTP 403. Fallback CLI autenticado funcionou; não é necessário recriar o projeto.
- Deployment e domínio publicados: ainda inexistentes; não há URL funcional confirmada.
- Backend Render: não criado. Falta escolher se os dados SQLite de teste podem ser descartados em reinícios e autenticar o provedor.
- Nenhum recurso pago criado; nenhum banco local ou arquivo de credenciais incluído no envio.
- Testes locais: 35 pytest, 4 E2E, build e lint passaram. Validação remota de API/login/exports continua pendente.

## Envio confirmado ao GitHub

- Primeiro commit `9b2bd77f9b1dac742cd766e8364f48f7c61d310e` enviado à branch `main`.
- `git ls-remote origin refs/heads/main` confirmou esse SHA remoto.
- Git local acompanha `origin/main`; código, testes, migrações e documentação publicados.
- Root Directory do projeto Vercel atualizado para `frontend` pela CLI; nenhum deploy iniciado.
