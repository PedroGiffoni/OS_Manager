import { useState, useRef, type ReactNode } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";
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
import { OperationalReports } from "./OperationalReports";
import { AppShell } from "./AppShell";
import { useTheme } from "./useTheme";
import {
  Moon,
  Sun,
  ArrowRight,
  ShieldCheck,
  Layers3,
  CalendarRange,
  ClipboardCheck,
  ClipboardList,
  CircleCheck,
  Clock3,
  TriangleAlert,
  X,
  CalendarDays,
} from "lucide-react";
import { ReportFilters, type ReportCondition } from "./ReportFilters";
import { HoursErrorDialog } from "./HoursErrorDialog";
import { api, setCsrf } from "./api";
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
  const [dark, toggleTheme] = useTheme();
  return (
    <main className="login">
      <section className="login-form-panel">
        <button
          className="icon-button login-theme"
          onClick={toggleTheme}
          aria-label={dark ? "Ativar modo claro" : "Ativar modo escuro"}
        >
          {dark ? (
            <Sun aria-hidden="true" size={20} />
          ) : (
            <Moon aria-hidden="true" size={20} />
          )}
        </button>
        <div className="login-identity">
          <img
            src={dark ? "/marca/sebrae-white.svg" : "/marca/sebrae-cor.svg"}
            alt="Sebrae"
            width="128"
            height="72"
          />
          <span>Sebrae Ceará</span>
        </div>
        <span className="eyebrow">Gestão do trabalho</span>
        <h1>Gestão de Demandas</h1>
        <p>Um espaço para organizar demandas e acompanhar suas entregas.</p>
        <form
          onSubmit={handleSubmit(async (values) => {
            try {
              onLogin(await api<Account>("/auth/login", "POST", values));
            } catch (e) {
              setError((e as Error).message);
            }
          })}
        >
          <h2>Acesse seu espaço</h2>
          <p>Entre com suas credenciais individuais.</p>
          <Label title="Usuário">
            <input
              autoComplete="username"
              placeholder="Informe seu usuário"
              aria-invalid={!!errors.username}
              aria-describedby={errors.username ? "username-error" : undefined}
              {...register("username")}
            />
          </Label>
          {errors.username && (
            <small id="username-error" role="alert" className="error">
              {errors.username.message}
            </small>
          )}
          <Label title="Senha">
            <input
              type="password"
              autoComplete="current-password"
              placeholder="Informe sua senha"
              aria-invalid={!!errors.password}
              aria-describedby={errors.password ? "password-error" : undefined}
              {...register("password")}
            />
          </Label>
          {errors.password && (
            <small id="password-error" role="alert" className="error">
              {errors.password.message}
            </small>
          )}
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <button className="primary" disabled={isSubmitting}>
            {isSubmitting ? "Entrando…" : "Entrar na Gestão de Demandas"}
            <ArrowRight size={18} aria-hidden="true" />
          </button>
          <div className="login-security">
            <ShieldCheck size={18} aria-hidden="true" />
            <span>Seu acesso é individual e protegido por permissões.</span>
          </div>
        </form>
        <p className="login-footer">Sebrae Ceará · Gestão de Demandas</p>
      </section>
      <section className="login-visual" aria-label="Sobre o sistema">
        <span className="eyebrow">Planejamento e acompanhamento</span>
        <h2>
          Mais clareza
          <br />
          em cada entrega.
        </h2>
        <p>
          Conecte o planejamento à execução e acompanhe o trabalho em um só
          lugar.
        </p>
        <div className="login-features">
          <div>
            <Layers3 size={24} aria-hidden="true" />
            <span>
              <strong>Demandas organizadas</strong>
              <small>Cards e fluxos de trabalho por atividade.</small>
            </span>
          </div>
          <div>
            <CalendarRange size={24} aria-hidden="true" />
            <span>
              <strong>Entregas acompanhadas</strong>
              <small>Backlog, sprints e quadro Kanban.</small>
            </span>
          </div>
          <div>
            <ClipboardCheck size={24} aria-hidden="true" />
            <span>
              <strong>Gestão com rastreabilidade</strong>
              <small>Horas, aprovações e relatórios da operação.</small>
            </span>
          </div>
        </div>
        <div className="login-visual-signature">
          <img
            src="/marca/sebrae-white.svg"
            alt="Sebrae"
            width="100"
            height="56"
          />
          <span>Ao lado de quem faz acontecer.</span>
        </div>
      </section>
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
  const [reportReset, setReportReset] = useState(0);
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
    <>
      <AppShell
        account={account}
        busy={busy}
        onLogout={() =>
          run(async () => {
            await api("/auth/logout", "POST");
            setAccount(null);
            client.clear();
          })
        }
      >
        <main id="conteudo" tabIndex={-1}>
          <div className="page-heading">
            <div>
              <span className="eyebrow">Painel de operações</span>
              <h1>Gestão de Demandas</h1>
              <p>Organize entregas e acompanhe cada etapa do trabalho.</p>
            </div>
            <span className="date">
              <CalendarDays size={16} aria-hidden="true" />
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
                <X size={18} aria-hidden="true" />
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
                account.role !== "supplier" ? (
                  <Reports
                    key={`${filters.sprint_id}:${reportReset}`}
                    query={params.toString()}
                    onCompleteReport={
                      account.role === "admin"
                        ? () => {
                            setFilters({
                              sprint_id: "",
                              supplier_id: "",
                              status: "",
                              starts: "",
                              ends: "",
                            });
                            setReportReset((value) => value + 1);
                            setNotice(
                              "Relatório completo: todos os dados disponíveis, sem filtros de seleção.",
                            );
                          }
                        : undefined
                    }
                    financial={can("export_financial") && can("view_financial")}
                    run={run}
                  />
                ) : (
                  <Empty>Acesso restrito a usuários internos.</Empty>
                )
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
      </AppShell>
      {opened && (
        <TaskDetail
          identity={opened.id}
          account={account}
          suppliers={suppliers.data ?? []}
          run={run}
          close={() => setOpened(null)}
        />
      )}
    </>
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
        <span>Indicadores do período selecionado</span>
      </div>
      <div className="metrics">
        {[
          {
            label: "Tarefas planejadas",
            value: d.planned,
            hint: "No escopo selecionado",
            icon: ClipboardList,
            tone: "info",
          },
          {
            label: "Concluídas",
            value: d.done,
            hint: `${new Intl.NumberFormat("pt-BR").format(Number(d.completion_percent))}% de conclusão`,
            icon: CircleCheck,
            tone: "success",
          },
          {
            label: "Pendentes",
            value: d.pending,
            hint: "Entregas em andamento",
            icon: Clock3,
            tone: "warning",
          },
          {
            label: "Em atraso",
            value: d.overdue,
            hint: "Com prazo vencido",
            icon: TriangleAlert,
            tone: "error",
          },
        ].map(({ label, value, hint, icon: Icon, tone }) => (
          <article className="metric" key={label} data-tone={tone}>
            <div className="metric-heading">
              <span>{label}</span>
              <span className="metric-icon">
                <Icon size={20} aria-hidden="true" />
              </span>
            </div>
            <strong>{new Intl.NumberFormat("pt-BR").format(value)}</strong>
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
              <XAxis
                dataKey="label"
                tick={{ fontSize: 13, fill: "hsl(var(--muted-foreground))" }}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fill: "hsl(var(--muted-foreground))" }}
              />
              <Tooltip
                contentStyle={{
                  background: "hsl(var(--card))",
                  color: "hsl(var(--foreground))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 8,
                }}
                labelStyle={{ color: "hsl(var(--foreground))" }}
              />
              <Bar
                isAnimationActive={false}
                dataKey="count"
                name="Atividades"
                fill="hsl(var(--primary))"
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
              <XAxis
                dataKey="name"
                tick={{ fontSize: 13, fill: "hsl(var(--muted-foreground))" }}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fill: "hsl(var(--muted-foreground))" }}
              />
              <Tooltip
                contentStyle={{
                  background: "hsl(var(--card))",
                  color: "hsl(var(--foreground))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 8,
                }}
                labelStyle={{ color: "hsl(var(--foreground))" }}
              />
              <Bar
                dataKey="planned"
                name="Planejadas"
                fill="hsl(var(--secondary))"
                isAnimationActive={false}
              />
              <Bar
                isAnimationActive={false}
                dataKey="done"
                name="Concluídas"
                fill="hsl(var(--primary))"
              />
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
  onCompleteReport,
}: {
  query: string;
  financial: boolean;
  run: Run;
  onCompleteReport?: () => void;
}) {
  const [conditions, setConditions] = useState<ReportCondition[]>([]);
  const params = new URLSearchParams(query);
  if (conditions.length)
    params.set("field_filters", JSON.stringify(conditions));
  const reportQuery = params.toString();
  return (
    <>
      {onCompleteReport && (
        <section className="panel">
          <h2>Relatório completo</h2>
          <p>
            Inclua todos os cards, fornecedores, sprints e períodos disponíveis.
            Esta opção limpa os filtros de acompanhamento, de campos do card e
            da análise. A inclusão de custos continua sendo uma escolha na
            exportação.
          </p>
          <button type="button" onClick={onCompleteReport}>
            Relatório completo — limpar todos os filtros
          </button>
        </section>
      )}
      <ReportFilters
        sprintId={params.get("sprint_id")}
        onApply={setConditions}
      />
      <OperationalReports
        key={reportQuery}
        query={reportQuery}
        financialExport={financial}
        run={run}
      />
    </>
  );
}
