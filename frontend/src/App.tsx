import { useState, useRef, type ReactNode } from "react";
import { NavLink, Routes, Route, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { ReportFilters, type ReportCondition } from "./ReportFilters";
import { HoursErrorDialog } from "./HoursErrorDialog";
import { api, download, setCsrf } from "./api";
import {
  stages,
  money,
  setTimezone,
  type Account,
  type Task,
  type Supplier,
  type Sprint,
} from "./types";
import { TaskList, Board, TaskDetail } from "./Tasks";
import { Sprints, Suppliers, Administration } from "./Management";
export type Run = (action: () => Promise<unknown>) => Promise<void>;
export function Label({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <label>
      <span>{title}</span>
      {children}
    </label>
  );
}
export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}
const loginSchema = z.object({
  username: z.string().min(1, "Informe o usuário."),
  password: z.string().min(1, "Informe a senha."),
});
export function Login({ onLogin }: { onLogin: (user: Account) => void }) {
  const [error, setError] = useState("");
  const {
    register,
    handleSubmit,
    formState: { isSubmitting, errors },
  } = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
  });
  return (
    <main className="login">
      <section className="login-brand">
        <div className="brand-mark">
          OS<span>Manager</span>
        </div>
        <h1>
          Planejar.
          <br />
          Acompanhar.
          <br />
          Entregar.
        </h1>
        <p>Demandas, pessoas e resultados conectados em um só lugar.</p>
        <small>GESTÃO DE OPERAÇÕES · V1</small>
      </section>
      <form
        onSubmit={handleSubmit(async (values) => {
          try {
            onLogin(await api<Account>("/auth/login", "POST", values));
          } catch (e) {
            setError((e as Error).message);
          }
        })}
      >
        <span className="eyebrow">BEM-VINDO AO OS MANAGER</span>
        <h2>Acesse seu espaço</h2>
        <p>Use suas credenciais individuais para continuar.</p>
        <Label title="Usuário">
          <input autoComplete="username" {...register("username")} />
        </Label>
        {errors.username && (
          <small role="alert">{errors.username.message}</small>
        )}
        <Label title="Senha">
          <input
            type="password"
            autoComplete="current-password"
            {...register("password")}
          />
        </Label>
        {errors.password && (
          <small role="alert">{errors.password.message}</small>
        )}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button className="primary" disabled={isSubmitting}>
          {isSubmitting ? "Entrando…" : "Entrar no OS Manager →"}
        </button>
      </form>
    </main>
  );
}
export default function App() {
  const client = useQueryClient();
  const [account, setAccount] = useState<Account | null>(null);
  const [notice, setNotice] = useState("");
  const [hoursError, setHoursError] = useState("");
  const hoursErrorTrigger = useRef<HTMLElement | null>(null);
  const [busy, setBusy] = useState(false);
  const [opened, setOpened] = useState<Task | null>(null);
  const [filters, setFilters] = useState({
    sprint_id: "",
    supplier_id: "",
    status: "",
    starts: "",
    ends: "",
  });
  const navigate = useNavigate();
  const session = useQuery({
    queryKey: ["session"],
    queryFn: async () => {
      try {
        const user = await api<Account>("/auth/me");
        setCsrf(user.csrf);
        setAccount(user);
        return user;
      } catch {
        return null;
      }
    },
    retry: false,
  });
  const run: Run = async (action) => {
    const trigger = document.activeElement as HTMLElement | null;
    setBusy(true);
    setNotice("");
    try {
      await action();
      await client.invalidateQueries({
        predicate: (query) => query.queryKey[0] !== "session",
      });
      setNotice("Operação realizada.");
    } catch (error) {
      const message = (error as Error).message;
      if (/Preencha as horas (previstas|utilizadas)/i.test(message)) {
        hoursErrorTrigger.current = trigger;
        setHoursError(message);
      } else {
        setNotice(message);
      }
    } finally {
      setBusy(false);
    }
  };
  const can = (permission: string) =>
    account?.permissions.includes(permission) ?? false;
  useQuery({
    queryKey: ["config"],
    queryFn: async () => {
      const config = await api<{ timezone: string }>("/config");
      setTimezone(config.timezone);
      return config;
    },
    enabled: !!account,
  });
  const suppliers = useQuery({
    queryKey: ["suppliers"],
    queryFn: () => api<Supplier[]>("/suppliers"),
    enabled: !!account,
  });
  const sprints = useQuery({
    queryKey: ["sprints"],
    queryFn: () => api<Sprint[]>("/sprints"),
    enabled: !!account,
  });
  const params = new URLSearchParams(
    Object.entries(filters).filter(([, value]) => value),
  );
  if (session.isPending) return <Empty>Carregando sessão…</Empty>;
  if (!account)
    return (
      <Login
        onLogin={(user) => {
          setCsrf(user.csrf);
          setAccount(user);
          client.invalidateQueries();
          navigate("/");
        }}
      />
    );
  return (
    <div className="shell" aria-busy={busy}>
      <aside>
        <div className="brand-mark">
          OS<span>Manager</span>
        </div>
        <div className="workspace">
          ESPAÇO DE TRABALHO
          <br />
          <strong>Gestão de demandas</strong>
        </div>
        <nav>
          <NavLink to="/" end>
            ◈ Visão geral
          </NavLink>
          <NavLink to="/backlog">
            ≡ {account.role === "supplier" ? "Minhas tarefas" : "Backlog"}
          </NavLink>
          <NavLink to="/sprints">▣ Sprints</NavLink>
          <NavLink to="/kanban">▤ Kanban</NavLink>
          {can("approve_hours") && (
            <NavLink to="/aprovacoes">✓ Aprovações de horas</NavLink>
          )}
          {account.role !== "supplier" && (
            <NavLink to="/fornecedores">♙ Fornecedores</NavLink>
          )}
          <NavLink to="/relatorios">▥ Relatórios</NavLink>
          {can("manage_users") && (
            <NavLink to="/administracao">⚙ Administração</NavLink>
          )}
        </nav>
        <div className="aside-bottom">
          <span className="avatar">
            {account.username.slice(0, 2).toUpperCase()}
          </span>
          <strong>{account.username}</strong>
          <small>
            {
              (
                {
                  admin: "Administrador",
                  manager: "Gestor",
                  internal: "Usuário interno",
                  supplier: "Fornecedor",
                } as Record<string, string>
              )[account.role]
            }
          </small>
          <button
            onClick={() =>
              run(async () => {
                await api("/auth/logout", "POST");
                setAccount(null);
                client.clear();
              })
            }
          >
            Sair
          </button>
        </div>
      </aside>
      <div className="content">
        <header>
          <span>OPERAÇÕES / OS MANAGER</span>
          <span className="environment">● Ambiente local</span>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <span className="eyebrow">SEU TRABALHO EM PERSPECTIVA</span>
              <h1>Gestão de demandas</h1>
              <p>Organize entregas e acompanhe cada etapa do trabalho.</p>
            </div>
            <span className="date">
              {new Intl.DateTimeFormat("pt-BR", { dateStyle: "long" }).format(
                new Date(),
              )}
            </span>
          </div>
          {hoursError && (
            <HoursErrorDialog
              message={hoursError}
              returnFocus={hoursErrorTrigger.current}
              onDismiss={() => setHoursError("")}
            />
          )}
          {notice && (
            <div className="notice" role="status">
              {notice}
              <button aria-label="Fechar aviso" onClick={() => setNotice("")}>
                ×
              </button>
            </div>
          )}
          <fieldset className="filters">
            <legend>Filtros de acompanhamento</legend>
            <Label title="Sprint">
              <select
                value={filters.sprint_id}
                onChange={(e) =>
                  setFilters({ ...filters, sprint_id: e.target.value })
                }
              >
                <option value="">Todas as sprints</option>
                {sprints.data?.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </select>
            </Label>
            <Label title="Fornecedor">
              <select
                value={filters.supplier_id}
                onChange={(e) =>
                  setFilters({ ...filters, supplier_id: e.target.value })
                }
              >
                <option value="">Todos os fornecedores</option>
                {suppliers.data?.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </select>
            </Label>
            <Label title="Status">
              <select
                value={filters.status}
                onChange={(e) =>
                  setFilters({ ...filters, status: e.target.value })
                }
              >
                <option value="">Todos os status</option>
                {Object.entries(stages).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </Label>
            <Label title="De">
              <input
                type="date"
                value={filters.starts}
                onChange={(e) =>
                  setFilters({ ...filters, starts: e.target.value })
                }
              />
            </Label>
            <Label title="Até">
              <input
                type="date"
                value={filters.ends}
                onChange={(e) =>
                  setFilters({ ...filters, ends: e.target.value })
                }
              />
            </Label>
          </fieldset>
          <Routes>
            <Route path="/" element={<Dashboard query={params.toString()} />} />
            <Route
              path="/backlog"
              element={
                <TaskList
                  query={params.toString()}
                  suppliers={suppliers.data ?? []}
                  canCreate={can("create_tasks")}
                  run={run}
                  open={setOpened}
                />
              }
            />
            <Route
              path="/aprovacoes"
              element={
                <TaskList
                  query={new URLSearchParams({
                    ...filters,
                    status: "review",
                  }).toString()}
                  suppliers={suppliers.data ?? []}
                  canCreate={false}
                  run={run}
                  open={setOpened}
                />
              }
            />
            <Route
              path="/kanban"
              element={
                <Board query={params.toString()} run={run} open={setOpened} />
              }
            />
            <Route
              path="/sprints"
              element={
                <Sprints
                  rows={sprints.data ?? []}
                  canManage={can("manage_sprints")}
                  canReopen={can("reopen_sprints")}
                  run={run}
                />
              }
            />
            <Route
              path="/fornecedores"
              element={
                <Suppliers
                  rows={suppliers.data ?? []}
                  canManage={can("manage_suppliers")}
                  canRate={can("change_rates")}
                  financial={can("view_financial")}
                  run={run}
                />
              }
            />
            <Route
              path="/relatorios"
              element={
                <Reports
                  key={filters.sprint_id}
                  query={params.toString()}
                  financial={can("export_financial") && can("view_financial")}
                  run={run}
                />
              }
            />
            <Route
              path="/administracao"
              element={
                can("manage_users") ? (
                  <Administration run={run} />
                ) : (
                  <Empty>Acesso restrito.</Empty>
                )
              }
            />
            <Route path="*" element={<Empty>Página não encontrada.</Empty>} />
          </Routes>
        </main>
        <footer>
          OS Manager{" "}
          <span>Planejamento com clareza. Execução com rastreabilidade.</span>
        </footer>
      </div>
      {opened && (
        <TaskDetail
          identity={opened.id}
          account={account}
          suppliers={suppliers.data ?? []}
          run={run}
          close={() => setOpened(null)}
        />
      )}
    </div>
  );
}
function Dashboard({ query }: { query: string }) {
  const supplierNames =
    useQueryClient().getQueryData<Supplier[]>(["suppliers"]) ?? [];
  const data = useQuery({
    queryKey: ["dashboard", query],
    queryFn: () => api("/dashboard?" + query),
  });
  if (data.isPending) return <Empty>Carregando indicadores…</Empty>;
  if (data.isError) return <Empty>{data.error.message}</Empty>;
  const d = data.data;
  return (
    <>
      <div className="section-title">
        <h2>Visão geral</h2>
        <span>Dados do banco local</span>
      </div>
      <div className="metrics">
        {[
          ["Tarefas planejadas", d.planned, "No escopo selecionado"],
          ["Concluídas", d.done, `${d.completion_percent}% de conclusão`],
          ["Pendentes", d.pending, "Entregas em andamento"],
          ["Em atraso", d.overdue, "Com prazo vencido"],
        ].map(([label, value, hint]) => (
          <article className="metric" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{hint}</small>
          </article>
        ))}
      </div>
      <div className="dashboard-grid">
        <section className="panel">
          <h3>Distribuição das atividades</h3>
          <p>Quantidade por etapa do fluxo</p>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart
              data={d.by_status.map((row: any) => ({
                ...row,
                label: stages[row.status],
              }))}
            >
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar
                dataKey="count"
                name="Atividades"
                fill="#237e85"
                radius={[5, 5, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </section>
        <section className="panel">
          <h3>Esforço e acompanhamento</h3>
          <dl className="totals">
            <div>
              <dt>Horas previstas</dt>
              <dd>{(d.estimated_minutes / 60).toLocaleString("pt-BR")}</dd>
            </div>
            <div>
              <dt>Horas utilizadas</dt>
              <dd>{(d.used_minutes / 60).toLocaleString("pt-BR")}</dd>
            </div>
            <div>
              <dt>Desvio em horas</dt>
              <dd>{(d.deviation_minutes / 60).toLocaleString("pt-BR")}</dd>
            </div>
            {d.cost_cents !== undefined && (
              <div>
                <dt>Custo consolidado</dt>
                <dd>{money(d.cost_cents)}</dd>
              </div>
            )}
          </dl>
          <p className="formula">
            Conclusão = concluídas ÷ planejadas × 100.
            <br />
            Desvio = utilizadas − previstas.
            <br />
            Pontualidade = concluídas no prazo ÷ concluídas com prazo × 100:{" "}
            {d.on_time_percent}%.
            <br />
            Sem prazo: não classificada em atraso.
            <br />
            Custos incluem apenas horas aprovadas.
          </p>
        </section>
      </div>
      {d.sprint_evolution?.length > 0 && (
        <section className="panel">
          <h3>Evolução das sprints</h3>
          <p>
            Planejadas e concluídas por sprint. Sprints encerradas usam o
            retrato do encerramento.
          </p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={d.sprint_evolution}>
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="planned" name="Planejadas" fill="#b3cccc" />
              <Bar dataKey="done" name="Concluídas" fill="#237e85" />
            </BarChart>
          </ResponsiveContainer>
        </section>
      )}
      {d.by_supplier?.length > 0 && (
        <section className="panel">
          <h3>Custos consolidados por fornecedor</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Fornecedor</th>
                  <th>Custo aprovado</th>
                </tr>
              </thead>
              <tbody>
                {d.by_supplier.map(
                  (row: { supplier_id: number; cost_cents: number }) => (
                    <tr key={row.supplier_id}>
                      <td>
                        {supplierNames.find(
                          (supplier) => supplier.id === row.supplier_id,
                        )?.name ?? `Fornecedor #${row.supplier_id}`}
                      </td>
                      <td>{money(row.cost_cents)}</td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}
      {d.planned === 0 && (
        <Empty>Nenhuma atividade para os filtros selecionados.</Empty>
      )}
    </>
  );
}
function Reports({
  query,
  financial,
  run,
}: {
  query: string;
  financial: boolean;
  run: Run;
}) {
  const [include, setInclude] = useState(false);
  const [conditions, setConditions] = useState<ReportCondition[]>([]);
  const [paging, setPaging] = useState({ query: "", index: 0 });
  const params = new URLSearchParams(query);
  if (conditions.length)
    params.set("field_filters", JSON.stringify(conditions));
  const reportQuery = params.toString();
  const page = paging.query === reportQuery ? paging.index : 0;
  const preview = useQuery({
    queryKey: ["report-preview", reportQuery, page],
    queryFn: () =>
      api<{ total: number; filters: string[]; items: Task[] }>(
        `/reports/preview?${reportQuery}&offset=${page * 25}`,
      ),
  });
  return (
    <>
      <ReportFilters
        sprintId={params.get("sprint_id")}
        onApply={(rows) => {
          setConditions(rows);
          setPaging({ query: "", index: 0 });
        }}
      />
      <Dashboard query={reportQuery} />
      <section className="panel">
        <h2>Prévia do relatório</h2>
        {preview.isPending && <p role="status">Carregando atividades…</p>}
        {preview.isError && <p role="alert">{preview.error.message}</p>}
        {preview.data && (
          <>
            <p role="status">
              {preview.data.total} atividade(s) encontrada(s).
            </p>
            {preview.data.filters.length > 0 && (
              <ul aria-label="Filtros aplicados">
                {preview.data.filters.map((filter, index) => (
                  <li key={index}>{filter}</li>
                ))}
              </ul>
            )}
            {preview.data.total === 0 ? (
              <Empty>Nenhuma atividade atende aos filtros selecionados.</Empty>
            ) : (
              <div className="table-wrap">
                <table>
                  <caption>
                    Atividades que atendem aos filtros aplicados
                  </caption>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Título</th>
                      <th>Etapa</th>
                      <th>Horas previstas</th>
                      <th>Horas utilizadas</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.data.items.map((task) => (
                      <tr key={task.id}>
                        <td>OS-{task.id}</td>
                        <td>{task.title}</td>
                        <td>{stages[task.status]}</td>
                        <td>{task.estimated_minutes / 60} h</td>
                        <td>{task.used_minutes / 60} h</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="actions">
              <button
                disabled={page === 0}
                onClick={() =>
                  setPaging({ query: reportQuery, index: page - 1 })
                }
              >
                Página anterior
              </button>
              <span>Página {page + 1}</span>
              <button
                disabled={(page + 1) * 25 >= preview.data.total}
                onClick={() =>
                  setPaging({ query: reportQuery, index: page + 1 })
                }
              >
                Próxima página
              </button>
            </div>
          </>
        )}
      </section>
      <section className="panel">
        <h2>Exportar relatório</h2>
        <p>
          Os filtros aplicados acima se aplicam ao arquivo. Fornecedores recebem
          somente suas próprias atividades.
        </p>
        {financial && (
          <Label title="Incluir custos aprovados">
            <input
              type="checkbox"
              checked={include}
              onChange={(event) => setInclude(event.target.checked)}
            />
          </Label>
        )}
        <div className="actions">
          <button
            className="primary"
            disabled={!preview.data || preview.isFetching || preview.isError}
            onClick={() =>
              run(() =>
                download(`/exports/xlsx?${reportQuery}&financial=${include}`),
              )
            }
          >
            Exportar Excel (.xlsx)
          </button>
          <button
            disabled={!preview.data || preview.isFetching || preview.isError}
            onClick={() =>
              run(() =>
                download(`/exports/pdf?${reportQuery}&financial=${include}`),
              )
            }
          >
            Exportar PDF
          </button>
        </div>
      </section>
    </>
  );
}
