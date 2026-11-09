<div align="center">

# Gestão de Demandas

### Do backlog à entrega. Cada etapa visível, cada decisão registrada.

**Demandas · Scrum · Kanban · Fornecedores · Horas · Análises**

## 🌐 [ABRIR A APLICAÇÃO → os-manager-phi.vercel.app](https://os-manager-phi.vercel.app)

[![Aplicação online](https://img.shields.io/badge/ABRIR_APLICAÇÃO-005EB8?style=for-the-badge&logo=vercel&logoColor=white)](https://os-manager-phi.vercel.app)
[![Documentação da API](https://img.shields.io/badge/EXPLORAR_API-102A43?style=for-the-badge&logo=fastapi&logoColor=white)](https://os-manager-api.onrender.com/api/docs)
[![Guia local](https://img.shields.io/badge/EXECUTAR_LOCALMENTE-00856A?style=for-the-badge&logo=windowsterminal&logoColor=white)](#-comece-em-poucos-passos)

<br>

![Tour animado da interface: visão geral, Kanban, relatórios, análise de card e tema escuro](docs/media/product-tour.gif)

<sub>Tour animado feito com capturas reais da aplicação em testes locais. Dados inteiramente fictícios. [Ver as imagens estáticas](#-por-dentro-da-aplicação).</sub>

<br><br>

![React 19](https://img.shields.io/badge/React-19-149ECA?style=flat-square&logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/Banco-PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Interface em português](https://img.shields.io/badge/Interface-pt--BR-005EB8?style=flat-square)

**[Conheça](#-o-que-você-pode-fazer) · [Explore as telas](#-por-dentro-da-aplicação) · [Instale](#-comece-em-poucos-passos) · [Validação](#-qualidade-verificada-nesta-versão-de-trabalho) · [Consulte os guias](#-mapa-da-documentação)**

</div>

---

> [!IMPORTANT]
> **O ambiente publicado é uma demonstração para testes.** O backend usa PostgreSQL Free no Render, com expiração informada pelo provedor em **06/12/2026**. Utilize apenas dados fictícios e exporte o que precisar antes dessa data. A primeira resposta pode demorar quando o serviço estiver suspenso.
>
> Este README descreve a versão de trabalho da branch `paridade-jira-v1-0`, incluindo a separação por quadros e o uso de PostgreSQL local. O link público acima pode estar em uma versão anterior até que as alterações desta branch sejam enviadas e implantadas; a URL estável, por si só, não confirma que recebeu esta versão.

## ✦ Uma visão compartilhada do trabalho

Gestão de Demandas reúne planejamento, execução e acompanhamento em uma aplicação web em português. A equipe organiza o backlog, personaliza cada card, planeja sprints e acompanha o Kanban. O fornecedor acessa suas atividades e informa horas; o gestor autorizado revisa os apontamentos e acompanha as entregas.

Os relatórios conectam esse fluxo ao histórico: **quanto tempo um card passou em cada fase, quando foi movimentado, quantos ciclos teve e como a sprint evoluiu**. Informações financeiras seguem permissões específicas no servidor.

A experiência visual segue a referência Sebrae Ceará fornecida para o projeto: identidade institucional, fontes locais, temas claro e escuro e navegação adaptada ao celular.

## 🧭 O que você pode fazer

| Planejar | Executar | Entender |
| :--- | :--- | :--- |
| **Quadros independentes** — admin cria quadros e libera acesso por pessoa | **Kanban configurável** — drag and drop, colunas adicionais, etiquetas e WIP indicativo | **Relatórios de cards** — lead time, tempo por etapa, ciclos e histórico |
| **Backlog e hierarquia** — busca, prioridade, prazo, épicos, histórias, tarefas e subtarefas | **Cards individuais** — campos, opções, visibilidade e obrigatoriedade por etapa | **Relatórios de sprint e backlog** — evolução, previsões, pendências e idade |
| **Sprints Scrum** — planejar, iniciar, encerrar e reabrir com autorização | **Horas e aprovação** — envio pelo fornecedor, rejeição, correção e decisão registrada | **Análises ágeis** — burndown, burnup, fluxo cumulativo, ciclo e control chart |
| **Fornecedores** — cadastro individual, tarifas versionadas e tarifa congelada por alocação | **Colaboração** — comentários, anexos, observadores, notificações e feed de atividade | **Filtros e dashboards** — consultas salvas, widgets e métricas operacionais |
| **Permissões granulares** — papel, concessões e acesso por quadro | **Views** — quadro, tabela, linha do tempo e calendário; filtros persistidos | **Exportações** — Excel, PDF e HTML, seguindo filtros e permissões |
| **Planejamento** — releases, componentes, dependências e capacidade de equipe | **Workflows e automações** — regras visuais, gatilhos, condições, ações e auditoria | **Histórico auditável** — autoria, instante e diferenças por alteração de negócio |

### Um fluxo, diferentes responsabilidades

```mermaid
flowchart LR
    A[Backlog] --> B[A fazer]
    B --> C[Em produção]
    C --> D[Em revisão]
    D --> E[Concluído]
    E -. Reabertura autorizada .-> D
    D -. Horas rejeitadas: corrigir e reenviar .-> D
```

- **Quem cria o card** escolhe incluir horas previstas e se a resposta será obrigatória.
- **O fornecedor responsável** informa as horas; horas utilizadas positivas são exigidas para revisão.
- **O gestor com `approve_hours`** aprova ou rejeita a versão enviada. Somente gestor conclui, após aprovação.
- **O backend** valida escopo, transição, campos e versão antes de persistir qualquer alteração.

## 🗂️ Quadros separados por equipe

A aplicação pode manter vários quadros independentes para, por exemplo, demandas internas e trabalho de fornecedores. **Somente administradores** criam quadros e gerenciam quais contas têm acesso. O administrador vê todos os quadros; os demais usuários veem os quadros em que foram incluídos. Gestores e usuários internos não podem conceder acesso por conta própria.

Cada quadro isola tarefas, sprints, colunas, views, filtros, releases, componentes, capacidade, workflows, automações, dashboards e eventos de desenvolvimento. A seleção do quadro é enviada à API, que aplica o escopo no servidor em consultas, alterações e arquivos exportados. Ser membro de um quadro não amplia as permissões do papel: **fornecedores continuam vendo apenas atividades atribuídas a eles**, sem tarifas, custos, relatórios ou auditoria interna.

O primeiro quadro preserva os dados anteriores à separação. A migração `0041` acrescenta `board_id` às entidades do escopo e mantém as informações existentes nesse quadro.

## 🧰 Funcionalidades da versão atual

### Operação dos cards

- Cadastro, edição, arquivamento auditado, prioridades ordenáveis, busca, filtros, prazo, fornecedor responsável e responsável interno opcional.
- Tipos de trabalho: épico, história, tarefa, bug e subtarefa; relação pai-filho e dependências tipadas, como bloqueia, relaciona e duplica.
- Etiquetas por card com texto e cor escolhidos por quem cria/edita, até oito por card.
- Campos individuais por card: texto curto/longo, número, data, seleção, checkbox, usuário, fornecedor, horas previstas/utilizadas e anexos. Rótulo, ordem, opções, visibilidade, permissões e obrigatoriedade são configuráveis; alterações são versionadas e não removem valores silenciosamente.
- Horas previstas não são incluídas por padrão. Ao criar o card, o autor escolhe não incluir, incluir como opcional ou exigir antes da produção. Horas utilizadas positivas continuam necessárias para envio à revisão.
- Comentários, anexos com limite de 5 MiB por arquivo e histórico por atividade. O histórico registra quem alterou o card, horas, campos, relações, status, sprint, aprovações e colaboração, com instante UTC e diferenças disponíveis.

### Kanban, views e consultas

- Fluxo nativo sequencial: Backlog → A fazer → Em produção → Em revisão → Concluído. Pulos e retornos não autorizados são bloqueados no servidor.
- Arrastar cards com prévia que acompanha o cursor; também é possível mover por menu/teclado. A ordem e a etapa são persistidas com controle de concorrência.
- Administradores e gestores podem adicionar, renomear e reordenar colunas adicionais. Colunas nativas não podem ser removidas ou renomeadas; colunas extras não dispensam regras de horas e aprovação.
- Views pessoais por quadro: **Quadro, Tabela, Linha do tempo e Calendário**. É possível criar, renomear, ordenar e remover views próprias.
- Filtros rápidos salvos e consulta avançada segura, com operadores lógicos, comparações, `IN`, valores vazios, ordenação e funções allowlistadas, incluindo `currentUser()`, `openSprints()`, `closedSprints()` e `linkedIssues()`.
- Agrupamento, ordenação, recorte e totalização em views compatíveis; tabela de resultados permite escolher colunas. Filtros rápidos são uma sintaxe simples local, não a reprodução completa da linguagem JQL do Jira.
- Limites WIP por coluna são alertas visuais baseados nos cards que passam pelos filtros. Não impedem a movimentação.

### Sprints e planejamento

- CRUD de sprints com nome, objetivo, responsável e datas; inclusão de cards elegíveis e proteção contra participação simultânea em sprints ativas.
- Encerrar congela os indicadores e devolve ao Backlog as tarefas não concluídas, sem apagar horas, anexos, campos ou histórico; reabertura formal exige permissão e motivo.
- Releases/versões com datas e publicação; componentes; épicos e hierarquia; links entre cards e dependências.
- Capacidade de equipe por período, com membros internos e fornecedores, carga estimada em dias úteis, visualização diária e sugestão de redistribuição versionada. A previsão depende do histórico e não promete data de entrega.
- Linha do tempo com início planejado, prazo e relações de dependência. Calendário tem exportação `.ics` e feed pessoal somente leitura com chave revogável.

### Workflows e automações

- Gestores com concessão específica configuram transições e condições por tipo de card, prioridade, fornecedor, etiqueta, hierarquia, aprovação e situação do prazo. Regras nativas de segurança e horas não podem ser desativadas.
- Automações por eventos de criação/edição, mudança de etapa, responsável, fornecedor, prioridade ou prazo, comentário, anexo, relação, horas, aprovação, sprint e eventos de desenvolvimento; também podem rodar diariamente ou em dias selecionados da semana, em UTC.
- Condições usam valores permitidos, atraso, janela de vencimento, release/componente, dependências e tipo de relação. Ações seguras incluem editar campos personalizados escalares, prioridade, etiqueta, comentário, prazo relativo à criação, responsável interno e observador.
- Cada regra aceita até dez ações configuradas; execuções são idempotentes por regra/data e têm log consultável. Não há scripts arbitrários.
- Webhooks assinados opcionais para GitHub, GitLab e Bitbucket registram metadados de branch, commit, PR, estado e ambiente e podem iniciar regras. Não buscam dados diretamente nas APIs externas.

### Dashboards e relatórios

- Dashboards pessoais com widgets de barras, linha, pizza, métrica, matriz 2D ou tabela de resultados; filtros JQL, dimensões e medidas de cards, prioridade, fornecedor, responsável, sprint, aprovação, release, componente, hierarquia, datas, atraso, horas e custo quando autorizado.
- Relatórios operacionais de **Cards, Sprints e Backlog**, com período, sprint, fornecedor, status, campos nativos e campos individuais como filtros. Descrição não é filtro. A opção de relatório completo limpa os filtros gerais e de campos para administradores.
- Análise de card: tempo acumulado e atual em cada etapa, datas de entrada/saída, ciclos de produção e reabertura, lead time, idade, mudanças, relações e dados permitidos do card.
- Análise ágil por sprint: burndown de cards e esforço, burnup, fluxo cumulativo, tempo de ciclo, control chart com dispersão e percentis, velocidade em horas planejadas, progresso e snapshot de encerramento.
- Relatórios de release e épico incluem cards, status, prazo, esforço, componentes e hierarquia; filtros aplicados restringem tanto a tabela quanto os indicadores.
- Exportação real em **XLSX, PDF e HTML** respeita filtros, quadro, escopo do usuário e permissões financeiras. Fornecedores não têm menu, rota API ou exportação de relatórios.
- Métricas descrevem contagens, tempos corridos e horas registradas. Percentis de ciclo não são metas/SLA; idade média considera cards abertos. Custos consolidados usam horas aprovadas e snapshot tarifário.

### Usuários, contatos e notificações

- Papéis: administrador, gestor, usuário interno e fornecedor. Concessões explícitas controlam ações como gestão de usuários, quadros, fornecedores, tarifas, sprints, workflows, automações, capacidade, aprovação, finanças e exportações.
- Perfil próprio com edição de nome/contatos e fotografia, tema claro/escuro e preferências pessoais.
- Observadores por card, notificações internas e assinaturas diárias/semanais de filtros. E-mail e Web Push são opcionais e exigem configuração; mensagens externas são genéricas.
- Fornecedor consulta somente cards atribuídos a sua conta no quadro autorizado, informa/edita horas e acompanha a decisão de aprovação. Não acessa fornecedor/tarifa, custos, relatórios, dashboards de gestão ou auditoria interna.

### O que não faz parte desta versão

Marketplace de plugins foi retirado do escopo. Também não há paridade integral com Jira, execução de scripts de usuário, integração bidirecional com APIs GitHub/GitLab/Bitbucket, pagamento/competência contábil, login institucional SSO/MFA, aplicativo móvel nativo ou promessa de hospedagem institucional. Consulte [limitações conhecidas](docs/KNOWN_LIMITATIONS.md) para os limites funcionais e técnicos completos.

## 📸 Por dentro da aplicação

<details open>
<summary><strong>01 · Visão geral — indicadores para acompanhar as entregas</strong></summary>

<br>

![Dashboard claro com tarefas planejadas, concluídas, pendentes, horas e distribuição por etapa](docs/media/dashboard-light.png)

Filtros por sprint, fornecedor, status e período. Os indicadores vêm do banco; custos aparecem somente para quem tem autorização financeira.

</details>

<details>
<summary><strong>02 · Kanban — trabalho visível em cada fase</strong></summary>

<br>

![Quadro Kanban real com colunas e cards de demonstração](docs/media/kanban.png)

Drag and drop com persistência e alternativa por menu. Uma transição recusada mantém o card na origem; pendências de horas recebem aviso vermelho em modal sobreposto.

![Modal vermelho com orientação de preenchimento de horas](docs/media/hours-alert.png)

</details>

<details>
<summary><strong>03 · Relatórios — do filtro ao histórico do card</strong></summary>

<br>

![Relatórios com filtros combináveis e análise operacional](docs/media/reports.png)

Combine os campos disponíveis no card, exceto descrição. Explore as abas **Cards**, **Sprints** e **Backlog**, abra o detalhe e exporte o mesmo recorte.

![Detalhe de um card com tempos acumulados e histórico das fases](docs/media/card-analysis.png)

> Capturas de testes automatizados podem mostrar tempos de poucos segundos e títulos técnicos. Tempos de permanência são corridos; não equivalem a horas trabalhadas. Históricos incompletos são identificados como indisponíveis.

</details>

<details>
<summary><strong>04 · Tema escuro — preferência visual persistida</strong></summary>

<br>

![Dashboard com o tema escuro da aplicação](docs/media/dashboard-dark.png)

O usuário escolhe o tema; a preferência fica salva no navegador. As fontes são servidas pelo próprio projeto.

</details>

<details>
<summary><strong>05 · No celular — a mesma operação em uma navegação adaptada</strong></summary>

<br>

<p align="center">
  <img src="docs/media/mobile-light.png" width="280" alt="Visão geral no celular em tema claro">
  &nbsp;&nbsp;
  <img src="docs/media/mobile-dark.png" width="280" alt="Visão geral no celular em tema escuro">
</p>

Menu móvel com fechamento por Escape, foco contido e retorno ao controle de origem. Quadros e tabelas mantêm rolagem quando necessária.

</details>

## 🚀 Comece em poucos passos

**Requisitos locais:** Docker Desktop com Compose, Python **3.12+**, Node.js **22.12+**, npm e Git. Desenvolvimento local, Compose e publicação usam PostgreSQL. O banco local roda no container Compose e persiste em volume; não é necessário conectar ao banco do Render.

### 1. Obtenha a versão desta atualização

```powershell
git clone --branch paridade-jira-v1-0 https://github.com/PedroGiffoni/OS_Manager.git
cd OS_Manager
```

### 2. Prepare o ambiente com dados fictícios

```powershell
.\scripts\Setup-Local.ps1 -Demo
```

### 3. Inicie em dois terminais PowerShell

```powershell
# Terminal 1 — API
.\scripts\Start-Backend.ps1
```

```powershell
# Terminal 2 — interface
.\scripts\Start-Frontend.ps1
```

| Serviço | Endereço local |
| :--- | :--- |
| **Aplicação** | [127.0.0.1:5173](http://127.0.0.1:5173) |
| **API interativa / Swagger** | [127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs) |
| **OpenAPI JSON** | [127.0.0.1:8000/api/openapi.json](http://127.0.0.1:8000/api/openapi.json) |
| **Health check** | [127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health) |

<details>
<summary><strong>Instalação manual / política de scripts restrita</strong></summary>

Não é necessário alterar a política global de execução do Windows. Na raiz do repositório:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.lock.txt
docker compose up -d postgres
cd backend
../.venv/Scripts/python.exe -m alembic upgrade head
$env:OS_MANAGER_ALLOW_DEMO_SEED='true'
../.venv/Scripts/python.exe -m app.seed
Remove-Item Env:OS_MANAGER_ALLOW_DEMO_SEED
../.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Em outro terminal, na raiz:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Em Linux/macOS, substitua os executáveis do virtualenv por `.venv/bin/python` e `npm.cmd` por `npm`; exporte as variáveis com a sintaxe do seu shell. Os scripts `.ps1` são para PowerShell.

</details>

## 🔑 Explore com contas de demonstração

**Somente no ambiente local**, a senha padrão do seed é `DemoLocal!2026`.

| Usuário | Experiência disponível |
| :--- | :--- |
| `admin` | Administração e todas as permissões |
| `gestor` | Demandas, sprints, fornecedores/tarifas, aprovação e acesso financeiro |
| `gestor_sem_aprovacao` | Gestão operacional; sem aprovação de horas e sem finanças |
| `interno` | Criação de tarefas, configuração de cards, sprints e exportações operacionais |
| `fornecedor` | Ana Exemplo: tarefas próprias e horas; sem acesso a relatórios |
| `fornecedor2` | Bruno Exemplo: mesmo isolamento, sem relatórios nem acesso às tarefas de Ana |

> [!NOTE]
> **No site publicado, a senha é privada e diferente da senha local.** O responsável pelo ambiente pode consultá-la na variável `OS_MANAGER_DEMO_PASSWORD` no [painel do Render](https://dashboard.render.com/web/srv-db8irum89jmc73dttfl0/env). Não publique esse valor no repositório.

O seed exige `OS_MANAGER_ALLOW_DEMO_SEED=true` e recusa modificar um banco que já tenha usuários. As contas, tarifas e demandas são fictícias; não são credenciais de produção.

## 🎬 Experimente o fluxo completo

1. **Prepare a equipe.** Entre como `admin` ou `gestor`; consulte o fornecedor fictício e sua tarifa.
2. **Crie a demanda.** No Backlog, atribua o fornecedor. Em horas previstas, escolha não incluir, incluir como opcional ou exigir resposta. Salvar o card sem estimativa é permitido.
3. **Personalize.** Abra o construtor individual, adicione campos, configure opções, ordem e obrigatoriedade por etapa; salve a configuração.
4. **Planeje a sprint.** Crie uma sprint, inclua o card e inicie. O vínculo leva a atividade a A fazer.
5. **Execute como fornecedor.** Entre como `fornecedor`. Se a estimativa foi configurada como obrigatória, informe-a antes da produção. Informe o total utilizado antes de enviar à revisão.
6. **Revise como gestor.** Rejeite com justificativa, veja a sinalização ao fornecedor e faça uma nova submissão. Aprove como gestor autorizado e conclua o card.
7. **Analise.** Em Relatórios, filtre a atividade, consulte fases/ciclos, abra o histórico e exporte Excel, PDF ou HTML. Custos dependem das permissões financeiras.
8. **Feche o ciclo.** Encerre a sprint com outra tarefa pendente: ela volta ao backlog, preservando horas, configuração e histórico da sprint encerrada.

### Uma regra financeira que preserva o passado

```text
Tarifa na alocação       R$ 120,00/h
Reajuste posterior      R$ 150,00/h
Horas utilizadas        8 horas aprovadas
Custo consolidado       8 × R$ 120,00 = R$ 960,00
```

A alocação guarda a tarifa vigente naquele momento. Reajustes não reescrevem custos históricos. Horas previstas são planejamento; horas não aprovadas não entram no total consolidado. Dinheiro é armazenado em centavos e horas em minutos; o cálculo usa `Decimal` e arredondamento `ROUND_HALF_UP`.

## 🏗️ Como o projeto se organiza

```mermaid
flowchart TB
    U[Equipe e fornecedores] --> UI[React + TypeScript · Vite]
    UI -->|REST /api/v1 · sessão + CSRF| API[FastAPI · Pydantic]
    API --> ACL[Permissões e escopo no servidor]
    ACL --> SVC[Serviços e regras de negócio]
    SVC --> DB[SQLAlchemy + PostgreSQL]
    MIG[Alembic · migrações] --> DB
    SVC --> R[Análises · XLSX · PDF · HTML]
```

| Camada | Tecnologias e responsabilidade |
| :--- | :--- |
| **Interface** | React 19, TypeScript, Vite, React Router, TanStack Query |
| **Interação** | React Hook Form + Zod, dnd-kit, Recharts, Lucide, CSS com tokens semânticos |
| **Backend** | FastAPI, Pydantic, serviços, repositórios e persistência SQLAlchemy |
| **Dados** | PostgreSQL 16, SQLAlchemy, Alembic, integridade referencial e versões de concorrência |
| **Verificação** | pytest, Vitest/Testing Library, Playwright, Ruff, ESLint, Prettier |
| **Execução** | PostgreSQL no Compose local; API e interface no host ou stack completa via Compose |

```text
OS_Manager/
├── backend/
│   ├── app/              # API, segurança, regras, persistência e análises
│   ├── migrations/       # Evolução do esquema via Alembic
│   ├── tests/            # Regras, API, autorização e integridade
│   ├── postgres-init/    # Criação do banco PostgreSQL dedicado de E2E
│   └── requirements.lock.txt
├── frontend/
│   ├── src/              # Páginas, componentes, temas e testes
│   ├── public/marca/     # Identidade visual
│   └── e2e/              # Fluxos de navegador
├── docs/
│   └── media/            # Prints reais e tour animado deste README
├── scripts/              # Setup, inicialização e runner de testes
├── docker-compose.yml
└── render.yaml
```

### Segurança e integridade

Sessões usam cookie **HttpOnly**, com `Secure` em HTTPS; mutações exigem proteção CSRF. Autorização e isolamento de fornecedores são aplicados na API, inclusive nos detalhes por ID, anexos e exportações. Tarifas e custos não são enviados ao fornecedor. Configurações de card, transições, decisões de horas e mudanças relevantes têm trilha de auditoria.

Papel e permissão são distintos: um gestor sem concessão explícita não aprova horas nem acessa finanças. Conflitos de versão exigem recarregar antes de tentar novamente. Consulte a [matriz de permissões](docs/PERMISSIONS.md) e as [decisões de negócio](docs/DECISIONS.md).

## ⚙️ Configuração e banco local

| Variável | Padrão / finalidade |
| :--- | :--- |
| `DATABASE_URL` | `postgresql+psycopg://os_manager:os_manager@localhost:5432/os_manager` |
| `COOKIE_SECURE` | `false` em HTTP local; `true` em HTTPS |
| `APP_TIMEZONE` | `America/Sao_Paulo` para apresentação |
| `TRUSTED_ORIGINS` | Origens frontend autorizadas; ver `.env.example` |
| `OS_MANAGER_ALLOW_DEMO_SEED` | Opt-in explícito para dados fictícios |
| `OS_MANAGER_DEMO_PASSWORD` | Senha privada obrigatória no seed de nuvem |
| `CLOUD_DEPLOYMENT` | Ativa exigências da configuração de nuvem |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` | SMTP opcional para notificações genéricas; sem essas configurações, somente avisos internos ficam ativos |
| `SMTP_STARTTLS`, `SMTP_SSL`, `APP_PUBLIC_URL` | Transporte SMTP e endereço usado no link dos e-mails; exemplos em `.env.example` |
| `PUSH_VAPID_PUBLIC_KEY`, `PUSH_VAPID_PRIVATE_KEY`, `PUSH_VAPID_SUBJECT` | Web Push opcional; configure um par VAPID e assunto `mailto:` ou URL HTTPS |
| `PUSH_SUBSCRIPTION_FERNET_KEY` | Chave independente para criptografar assinaturas push; não reutilize chaves de sessão |

O script `Setup-Local.ps1` inicia o PostgreSQL local pelo Docker Compose antes de aplicar as migrações. A persistência fica no volume `postgres-data`; o banco `os_manager_e2e` é separado para fluxos automatizados. A estrutura é aplicada por migrações Alembic.

As variáveis devem ser definidas no ambiente do processo. O Python não carrega `.env` implicitamente; o arquivo de exemplo documenta a configuração. Nunca versione senhas, tokens, banco ou anexos locais.

Push requer navegador compatível e HTTPS (localhost é aceito para desenvolvimento). As preferências são individuais no menu de notificações; sem VAPID configurado, avisos internos continuam funcionando. O conteúdo entregue ao navegador é genérico e não inclui título, chave ou campos do card.

> [!IMPORTANT]
> A aplicação usa PostgreSQL em todos os ambientes. Testes unitários legados ainda usam SQLite em memória como fixture isolada; esse banco não armazena dados da aplicação. A implantação institucional ainda exige avaliação de segurança, operação, backup e homologação pela TI.

<details>
<summary><strong>🐳 Alternativa: Docker Compose</strong></summary>

Com Docker Desktop em modo Linux e daemon ativo:

```powershell
docker compose up --build
```

Para criar os dados fictícios em um banco vazio:

```powershell
docker compose exec -e OS_MANAGER_ALLOW_DEMO_SEED=true backend python -m app.seed
```

Acesse **[localhost:8080](http://localhost:8080)**. O volume `postgres-data` preserva o banco local. `docker compose down -v` apaga esse volume e os dados locais.

**Estado de validação:** arquivos e health checks fornecidos; Docker Compose local não foi homologado neste ambiente porque o daemon estava indisponível. O build Docker do backend foi executado no Render. Veja [limitações conhecidas](docs/KNOWN_LIMITATIONS.md).

</details>

## ✅ Qualidade verificada nesta versão de trabalho

**Verificações executadas em 09/11/2026** sobre a árvore local desta branch:

| Verificação | Resultado |
| :--- | :--- |
| Backend · `test_database_url`, `test_board_scope`, `test_automation` | **46 passaram**; um aviso de depreciação do Starlette/httpx |
| Configuração do Docker Compose | `docker compose config --quiet`: **passou** |
| Sintaxe do runner E2E PostgreSQL | **Válida** |
| `git diff --check` | **Passou**; Git apenas avisou sobre conversão LF/CRLF |
| PostgreSQL local, migração e fluxo E2E PostgreSQL | **Não executados**: daemon do Docker Desktop indisponível nesta máquina |
| Implantação pública destas alterações | **Pendente**; a árvore atual inclui alterações ainda não publicadas |

Os 46 testes focados não substituem a suíte completa nem o E2E no PostgreSQL. Fixtures unitárias legadas ainda usam SQLite em memória. A configuração operacional e o runner E2E usam PostgreSQL. Os resultados de rodadas anteriores estão datados em [VALIDATION.md](docs/VALIDATION.md) e não são apresentados como validação desta versão.

<details>
<summary><strong>Reproduzir testes e verificações</strong></summary>

```powershell
# A partir da raiz
cd backend
../.venv/Scripts/python.exe -m pytest -q
../.venv/Scripts/python.exe -m ruff check app tests
../.venv/Scripts/python.exe -m ruff format --check app tests
cd ../frontend
npm.cmd run test
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
npm.cmd run format:check
```

Instale o Chromium uma vez e execute o runner isolado:

```powershell
# Na pasta frontend
npx.cmd playwright install chromium
cd ..
.venv/Scripts/python.exe scripts/run_e2e.py
```

O runner exige o banco dedicado PostgreSQL `os_manager_e2e`, limpa somente o schema desse banco, aplica migrações, executa seed e usa API em **8001** e Vite em **5174**. O Compose cria esse banco junto do PostgreSQL local. Nunca aponte `E2E_DATABASE_URL` para o banco de desenvolvimento, o banco hospedado ou produção.

Para revisar dependências:

```powershell
# Em frontend
npm.cmd audit
# Na raiz, com pip-audit instalado no virtualenv
.venv/Scripts/python.exe -m pip_audit --local
```

Auditorias de dependências não foram executadas nesta rodada; os resultados anteriores podem estar defasados em relação à árvore atual.

</details>

## 📚 Mapa da documentação

| Quero entender… | Documento |
| :--- | :--- |
| Arquitetura e organização | [ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Papéis, permissões e escopo | [PERMISSIONS.md](docs/PERMISSIONS.md) |
| Decisões e regras adotadas | [DECISIONS.md](docs/DECISIONS.md) |
| Endpoints e contratos | [API.md](docs/API.md) · [OpenAPI online](https://os-manager-api.onrender.com/api/docs) |
| Fórmulas de indicadores | [METRICS.md](docs/METRICS.md) |
| Filtros de campos do card | [REPORT_FILTERS.md](docs/REPORT_FILTERS.md) |
| Tempos, ciclos, sprint e backlog | [OPERATIONAL_ANALYTICS.md](docs/OPERATIONAL_ANALYTICS.md) |
| Histórico de alterações dos cards | [AUDIT_TRAIL.md](docs/AUDIT_TRAIL.md) |
| Limites de paridade com Jira | [KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) · [plano de paridade](docs/JIRA_FEATURE_PARITY_PLAN.md) |
| Plano e marcos de implementação | [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) |
| Identidade visual e acessibilidade | [DESIGN_UPDATE.md](docs/DESIGN_UPDATE.md) |
| Deploy e configuração de nuvem | [DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| Registros anteriores de publicação | [DEPLOYMENT_STATUS.md](docs/DEPLOYMENT_STATUS.md) |
| Evolução futura do banco | [DATABASE_MIGRATION.md](docs/DATABASE_MIGRATION.md) |
| Validação e limites do protótipo | [VALIDATION.md](docs/VALIDATION.md) · [KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) |

## 🛠️ Estado atual e próximos cuidados

- [x] Persistência, autenticação e permissões no backend.
- [x] Backlog, sprints, Kanban, cards individuais e colaboração.
- [x] Horas previstas configuráveis; horas utilizadas, aprovação e custo histórico.
- [x] Relatórios de cards, sprint e backlog, filtros e exportações XLSX/PDF/HTML.
- [x] Views, releases, componentes, relações, capacidade, workflows e automações seguras.
- [x] Quadros múltiplos com isolamento e controle de acesso administrado.
- [x] PostgreSQL como banco operacional local, E2E e hospedado.
- [x] Interface responsiva com temas claro/escuro e publicação de testes.
- [ ] Homologar infraestrutura, banco e políticas para uso institucional.
- [ ] Validar carga, volumes maiores e paginação dos seletores/quadros.
- [ ] Avaliar atualização de dependências e medidas institucionais como SSO/MFA.
- [ ] Evoluir previsões, percentis e burndown avançado após validação de escopo.

Retornos de etapa seguem uma matriz conservadora; troca de fornecedor em execução é bloqueada para preservar o histórico. Não há avaliação subjetiva de produtividade nem integrações corporativas externas nesta versão. Os limites completos estão documentados, sem promessa de prontidão institucional.

---

<div align="center">

### Planeje com clareza. Acompanhe com contexto. Entregue com histórico.

**[🌐 Acessar demonstração pública](https://os-manager-phi.vercel.app)** &nbsp;·&nbsp; **[Código no GitHub · branch paridade-jira-v1-0](https://github.com/PedroGiffoni/OS_Manager/tree/paridade-jira-v1-0)** &nbsp;·&nbsp; **[Voltar ao início ↑](#gestão-de-demandas)**

<sub>Projeto anteriormente denominado OS Manager. Identificadores técnicos do repositório e da infraestrutura foram preservados.</sub>

</div>
