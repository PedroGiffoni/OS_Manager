# Publicação de testes: Vercel e backend gratuito

## Estado atual

**Publicado e testado:** https://os-manager-phi.vercel.app (frontend) e https://os-manager-api.onrender.com (API). Usuário escolheu My Workspace e aceitou dados fictícios descartáveis no Render Free. Código em https://github.com/PedroGiffoni/OS_Manager. A CLI Vercel autenticada realizou o deploy; 4 E2E passaram no domínio estável. Contas, senha no painel e resultados: DEPLOYMENT_STATUS.md. Este guia descreve como reproduzir a configuração.

## Escolha de armazenamento antes do deploy

O `render.yaml` configura somente um backend **Free**. Não cria banco pago, PostgreSQL ou disco. O SQLite continua em arquivo, sem mudar o modelo aprovado. No Render Free, o filesystem é efêmero: SQLite, anexos e sessões são perdidos em restart, redeploy ou suspensão por inatividade. O serviço suspende após 15 minutos sem tráfego; a retomada pode levar aproximadamente um minuto. O seed opcional recria apenas os exemplos iniciais; NÃO recupera alterações feitas durante o teste.

Esse caminho serve para uma demonstração descartável, depois de aceitar essa perda. Se os testes precisarem preservar registros, não publique usando esse perfil. Será necessário confirmar outro provedor com disco persistente gratuito ou rever o orçamento/requisito de banco com autorização explícita. Não foi autorizada nem implementada troca para outro SGBD.

Vercel Hobby restringe uso a projetos pessoais e não comerciais; valide a elegibilidade da demonstração. Este guia não constitui implantação institucional de produção.

Fontes consultadas em 15/10/2026: [Render Free](https://render.com/docs/free), [Blueprint](https://render.com/docs/blueprint-spec), [Vercel Hobby](https://vercel.com/docs/plans/hobby), [rewrites Vercel](https://vercel.com/docs/routing/rewrites).

## 1. Disponibilizar somente o código

O repositório informado pelo usuário é `PedroGiffoni/OS_Manager`, público, com a raiz em `os-manager` (NÃO a pasta de instalação do Pen). Somente o código deve ser enviado. O provedor precisa ter acesso ao repositório. Vercel CLI autenticada; backend publicado no Render Free.

O `.gitignore` exclui o SQLite, `.env`, `.venv`, dependências, resultados e credenciais locais da Vercel. O `.dockerignore` do backend exclui os dados e arquivos `.env`. Não envie o banco local: a publicação usa outro banco, criado por migrações.

## 2. Definir o domínio estável do frontend

Na Vercel, crie/importe o projeto com **Root Directory = frontend**, Framework = Vite, Build = `npm run build`, Output = `dist`. Anote a URL estável atribuída ao projeto. As URLs neste guia são exemplos, não endereços já publicados. Finalize o proxy do passo 4 antes de considerar o frontend funcional.

## 3. Backend Render Free

No Render, importe o repositório como Blueprint e use `render.yaml`. Confirme explicitamente **Free** e revise o resumo antes de criar. O build ocorre no próprio Render com `backend/Dockerfile`; Docker local não é necessário. Este build remoto ainda precisa ser executado e verificado.

Configure os valores abaixo no painel, sem aspas adicionais:

| Variável | Valor |
| --- | --- |
| `DATABASE_URL` | `sqlite:///./data/os_manager.db` |
| `CLOUD_DEPLOYMENT` | `true` |
| `COOKIE_SECURE` | `true` |
| `TRUSTED_ORIGINS` | origem HTTPS exata e estável da Vercel, sem barra final |
| `APP_TIMEZONE` | `America/Sao_Paulo` |
| `OS_MANAGER_ALLOW_DEMO_SEED` | permanece `false`; mudar para `true` SOMENTE para teste descartável autorizado |
| `OS_MANAGER_DEMO_PASSWORD` | senha privada aleatória com pelo menos 16 caracteres, definida como segredo no painel |

Não configure `PORT` manualmente: a inicialização aceita o valor fornecido pelo Render. O processo aplica Alembic antes de iniciar um único worker Uvicorn. Se o seed estiver explicitamente habilitado, cria contas fictícias somente se não houver usuários. Com o seed desabilitado e banco vazio, não haverá conta para login; para esta demonstração, a inicialização das contas requer o seed autorizado. A senha local conhecida `DemoLocal!2026` é recusada no modo de nuvem.

Contas criadas: `admin`, `gestor`, `gestor_sem_aprovacao`, `interno`, `fornecedor`, `fornecedor2`. Todas recebem a senha privada definida no painel; permissões permanecem as documentadas em PERMISSIONS.md. Não compartilhe a senha administrativa em página pública. Em filesystem efêmero, manter o flag habilitado recria os exemplos depois da perda do arquivo. Desabilitá-lo impede essa recriação e deixa o próximo banco vazio sem contas.

Health check: `/api/v1/health`. Quando o deploy estiver saudável, anote a URL real do backend.

## 4. Gerar o proxy e publicar frontend

Da raiz `os-manager`, substitua pelo domínio REAL do backend:

```powershell
.\.venv\Scripts\python.exe scripts/configure_vercel.py --backend-url https://SEU-BACKEND.onrender.com
```

O comando cria `frontend/vercel.json`, com configurações Vite, proxy `/api/*` e fallback das rotas React. A API mantém `/api/v1` e não cai no HTML da SPA. Inclua esse arquivo no repositório antes do deploy da Vercel. Não configure `VITE_API_TARGET` em produção: essa variável atende somente ao servidor local Vite.

Também é possível publicar com CLI autenticada, a partir de `frontend`:

```powershell
vercel login
vercel --prod
```

Revise a conta/projeto e mantenha o plano gratuito elegível. Ao finalizar, confirme que a origem estável efetiva consta em `TRUSTED_ORIGINS` do backend e reinicie-o se necessário. A lista aceita origens HTTPS exatas separadas por vírgula; previews só funcionam se autorizados individualmente. Não use `*`.

O navegador chama `https://SEU-FRONTEND.vercel.app/api/v1/...`; a Vercel encaminha à API externa. Isso conserva cookie host-only HttpOnly/Secure/SameSite=Strict, downloads e CSRF no mesmo domínio do navegador. Respostas da API não devem ser armazenadas em cache. Não aponte o browser diretamente para o Render nem enfraqueça os cookies para contornar CORS.

## 5. Verificação obrigatória após publicação

1. Abrir `/api/v1/health` pelo domínio Vercel e conferir JSON `status=ok`, não HTML.
2. Abrir uma rota interna diretamente (por exemplo `/backlog`) e conferir carregamento React.
3. Fazer login com as contas privadas de teste; recarregar a página e confirmar sessão; sair e confirmar bloqueio posterior.
4. Validar cadastro → card → sprint → horas do fornecedor → aprovação do gestor → conclusão → dashboards → downloads Excel/PDF.
5. Confirmar no navegador cookie Secure/HttpOnly/SameSite, CSRF e `Cache-Control: no-store`; fornecedor não recebe tarifas, custos ou tarefas alheias.
6. Testar acesso móvel e anexo fictício pequeno; conferir logs de falhas sem credenciais.
7. No perfil descartável, após aceitar perda dos dados, verificar suspensão/retomada: exemplos voltam, alterações e sessões anteriores não. Não simular restart de um banco que precise preservar.

Execute novamente os testes locais após qualquer ajuste. Evidência local não substitui a verificação do domínio publicado. Na publicação registrada em DEPLOYMENT_STATUS.md, os endereços foram verificados e os quatro fluxos do navegador passaram. Não foi realizado teste deliberado de suspensão/perda de dados; a limitação está documentada e foi aceita para testes.

## Atualização, interrupção e dados

Auto deploy do Render está desabilitado no Blueprint para que um commit não reinicie acidentalmente a demonstração. Atualize manualmente quando puder reiniciar os testes. Para encerrar o teste, suspenda/exclua somente os serviços criados para essa demonstração nos painéis; isso não altera o banco local. Não há backup remoto automático neste perfil gratuito. Excel/PDF são relatórios, não backup integral do banco.
