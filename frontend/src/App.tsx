import { useEffect, useState, useRef, type ReactNode } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import { OperationalReports } from "./OperationalReports";
import { AppShell } from "./AppShell";
import { useTheme } from "./useTheme";
import {
  Moon,
  Sun,
  ArrowRight,
  ArrowUp,
  ArrowDown,
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
import { api, setActiveBoardId, setCsrf } from "./api";
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
import { Sprints, Suppliers, Administration, BoardAdministration } from "./Management";
import { Planning } from "./Planning";
import { FilterSubscriptions } from "./FilterSubscriptions";
export type Run = (action: () => Promise<unknown>) => Promise<void>;
type SavedFilter = { id: number; name: string; query: string; shared: boolean; shared_roles: string[]; shared_group_ids: number[]; owner_id: number; updated_at: string };
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
  const [jqlDraft, setJqlDraft] = useState("");
  const [jqlApplied, setJqlApplied] = useState("");
  const [selectedSavedFilterId, setSelectedSavedFilterId] = useState("");
  const [savingFilter, setSavingFilter] = useState(false);
  const [savedFilterDraft, setSavedFilterDraft] = useState({ name: "", shared: false, shared_roles: [] as string[], shared_group_ids: [] as number[] });
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
        let user: Account;
        try {
          user = await api<Account>("/auth/me");
        } catch {
          setActiveBoardId(null);
          user = await api<Account>("/auth/me");
        }
        setCsrf(user.csrf);
        setActiveBoardId(user.active_board_id ?? 1);
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
  const selectSavedFilter = (identity: string) => {
    setSelectedSavedFilterId(identity);
    const selected = savedFilters.data?.find((item) => String(item.id) === identity);
    if (!selected) return;
    setJqlDraft(selected.query);
    setJqlApplied(selected.query);
    setSavedFilterDraft({
      name: selected.owner_id === account?.id ? selected.name : "",
      shared: selected.owner_id === account?.id && selected.shared,
      shared_roles: selected.owner_id === account?.id ? selected.shared_roles : [],
      shared_group_ids: selected.owner_id === account?.id ? selected.shared_group_ids : [],
    });
    setSavingFilter(false);
  };
  const saveCurrentFilter = () => run(async () => {
    const existing = savedFilters.data?.find(
      (item) => String(item.id) === selectedSavedFilterId && item.owner_id === account?.id,
    );
    const payload = {
      ...savedFilterDraft,
      name: savedFilterDraft.name.trim(),
      query: jqlDraft.trim(),
      shared_roles: savedFilterDraft.shared ? savedFilterDraft.shared_roles : [],
      shared_group_ids: savedFilterDraft.shared ? savedFilterDraft.shared_group_ids : [],
    };
    const result = await api<SavedFilter>(
      existing ? `/saved-filters/${existing.id}` : "/saved-filters",
      existing ? "PUT" : "POST",
      payload,
    );
    setJqlApplied(result.query);
    setJqlDraft(result.query);
    setSelectedSavedFilterId(String(result.id));
    setSavingFilter(false);
  });
  const deleteSelectedFilter = () => run(async () => {
    await api(`/saved-filters/${selectedSavedFilterId}`, "DELETE");
    setSelectedSavedFilterId("");
    setSavedFilterDraft({ name: "", shared: false, shared_roles: [], shared_group_ids: [] });
    setSavingFilter(false);
  });
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
  const savedFilters = useQuery({
    queryKey: ["saved-filters"],
    queryFn: () => api<SavedFilter[]>("/saved-filters"),
    enabled: !!account,
  });
  const savedFilterGroups = useQuery({
    queryKey: ["saved-filter-groups"],
    queryFn: () => api<{ id: number; name: string }[]>("/directory/groups"),
    enabled: !!account?.permissions.includes("manage_planning"),
  });
  const sprints = useQuery({
    queryKey: ["sprints"],
    queryFn: () => api<Sprint[]>("/sprints"),
    enabled: !!account,
  });
  const params = new URLSearchParams(
    Object.entries(filters).filter(([, value]) => value),
  );
  if (jqlApplied.trim()) params.set("jql", jqlApplied.trim());
  if (session.isPending) return <Empty>Carregando sessão…</Empty>;
  if (!account)
    return (
      <Login
        onLogin={(user) => {
          setCsrf(user.csrf);
          setActiveBoardId(user.active_board_id ?? 1);
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
            setActiveBoardId(null);
            setJqlDraft("");
            setJqlApplied("");
            setSelectedSavedFilterId("");
            setSavingFilter(false);
            setSavedFilterDraft({ name: "", shared: false, shared_roles: [], shared_group_ids: [] });
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
            <Label title="Filtro salvo reutilizável">
              <select value={selectedSavedFilterId} onChange={(event) => selectSavedFilter(event.target.value)}>
                <option value="">Selecionar filtro salvo…</option>
                {savedFilters.data?.map((filter) => <option key={filter.id} value={filter.id}>{filter.name}{filter.owner_id !== account.id ? " · compartilhado" : ""}</option>)}
              </select>
            </Label>
            <Label title="Consulta avançada dos cards">
              <input
                maxLength={1000}
                value={jqlDraft}
                onChange={(event) => setJqlDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    setJqlApplied(jqlDraft.trim());
                  }
                }}
                placeholder="Ex.: issue in linkedIssues('OS-123', 'blocks')"
                aria-describedby="global-jql-help"
              />
            </Label>
            <div className="actions">
              <button type="button" className="primary" onClick={() => setJqlApplied(jqlDraft.trim())}>
                Aplicar consulta
              </button>
              <button type="button" disabled={!jqlDraft.trim() || savedFilters.isPending} onClick={() => {
                const selected = savedFilters.data?.find((item) => String(item.id) === selectedSavedFilterId && item.owner_id === account.id);
                if (selected) setSavedFilterDraft({ name: selected.name, shared: selected.shared, shared_roles: selected.shared_roles, shared_group_ids: selected.shared_group_ids });
                else setSavedFilterDraft({ name: "", shared: false, shared_roles: [], shared_group_ids: [] });
                setSavingFilter((value) => !value);
              }}>{savingFilter ? "Fechar salvamento" : "Salvar filtro…"}</button>
              {selectedSavedFilterId && savedFilters.data?.some((item) => String(item.id) === selectedSavedFilterId && item.owner_id === account.id) && <button type="button" className="danger" onClick={deleteSelectedFilter}>Excluir filtro</button>}
              {(jqlDraft || jqlApplied) && (
                <button type="button" onClick={() => { setJqlDraft(""); setJqlApplied(""); setSelectedSavedFilterId(""); setSavingFilter(false); }}>
                  Limpar consulta
                </button>
              )}
            </div>
            {savingFilter && <div className="saved-filter-editor">
              <Label title="Nome do filtro"><input autoFocus maxLength={100} value={savedFilterDraft.name} onChange={(event) => setSavedFilterDraft({ ...savedFilterDraft, name: event.target.value })} placeholder="Ex.: Itens atrasados da sprint" /></Label>
              {can("manage_planning") && <div className="share-role-options">
                <label><input type="checkbox" checked={savedFilterDraft.shared} onChange={(event) => setSavedFilterDraft({ ...savedFilterDraft, shared: event.target.checked, shared_roles: event.target.checked ? (savedFilterDraft.shared_roles.length ? savedFilterDraft.shared_roles : ["admin", "manager", "internal"]) : [], shared_group_ids: event.target.checked ? savedFilterDraft.shared_group_ids : [] })} /> Compartilhar filtro com equipe interna</label>
                {savedFilterDraft.shared && <><span>Perfis:</span>{(["admin", "manager", "internal"] as const).map((role) => <label key={role}><input type="checkbox" checked={savedFilterDraft.shared_roles.includes(role)} onChange={(event) => setSavedFilterDraft({ ...savedFilterDraft, shared_roles: event.target.checked ? [...savedFilterDraft.shared_roles, role] : savedFilterDraft.shared_roles.filter((item) => item !== role) })} />{{ admin: "Administradores", manager: "Gestores", internal: "Equipe interna" }[role]}</label>)}{(savedFilterGroups.data ?? []).length > 0 && <><span>Grupos:</span>{savedFilterGroups.data?.map((group) => <label key={group.id}><input type="checkbox" checked={savedFilterDraft.shared_group_ids.includes(group.id)} onChange={(event) => setSavedFilterDraft({ ...savedFilterDraft, shared_group_ids: event.target.checked ? [...savedFilterDraft.shared_group_ids, group.id] : savedFilterDraft.shared_group_ids.filter((id) => id !== group.id) })} />{group.name}</label>)}</>}</>}
              </div>}
              <button type="button" className="primary" disabled={!savedFilterDraft.name.trim() || !jqlDraft.trim() || (savedFilterDraft.shared && !savedFilterDraft.shared_roles.length && !savedFilterDraft.shared_group_ids.length)} onClick={saveCurrentFilter}>{savedFilters.data?.some((item) => String(item.id) === selectedSavedFilterId && item.owner_id === account.id) ? "Atualizar filtro" : "Salvar filtro"}</button>
              <small>Filtros compartilhados respeitam as permissões e o escopo dos cards de cada pessoa.</small>
            </div>}
            <small id="global-jql-help" className="muted">
              Exemplos: <code>assignee = currentUser()</code> e <code>issue in linkedIssues('OS-123', 'blocks')</code>. Combina com os filtros acima e atualiza painel, quadro e relatórios.
            </small>
          </fieldset>
          <Routes>
            <Route path="/" element={<Dashboard query={params.toString()} account={account} run={run} />} />
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
                    ...(jqlApplied ? { jql: jqlApplied } : {}),
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
                <Board
                  query={params.toString()}
                  suppliers={suppliers.data ?? []}
                  sprints={sprints.data ?? []}
                  account={account}
                  run={run}
                  open={setOpened}
                />
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
            <Route path="/planejamento" element={<Planning suppliers={suppliers.data ?? []} canPlan={account.role !== "supplier"} canCapacity={account.role !== "supplier"} canWorkflow={account.role !== "supplier"} canAutomation={account.role !== "supplier"} run={run} />} />
            <Route path="/filtros-salvos" element={<FilterSubscriptions run={run} />} />
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
                            setJqlDraft("");
                            setJqlApplied("");
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
            <Route path="/quadros" element={account.role === "admin" ? <BoardAdministration run={run} /> : <Empty>Acesso restrito a administradores.</Empty>} />
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

type DashboardWidget = { id: number; name: string; jql: string; group_by: string; group_by_secondary: string | null; measure: string; chart: string; result_columns: string[]; max_results: number; shared: boolean; shared_roles: string[]; shared_group_ids: number[]; position: number; owner_id: number; dashboard_id: number };
type DashboardRecord = { id: number; name: string; owner_id: number; owner_name: string | null; is_default: boolean; read_only: boolean };
const dashboardColors = ["#2459bd", "#3983c7", "#63a6db", "#0e7d62", "#df9d16", "#9b59b6", "#e16b55"];

function Dashboard({ query, account, run }: { query: string; account: Account; run: Run }) {
  const supplierNames = useQueryClient().getQueryData<Supplier[]>(["suppliers"]) ?? [];
  const dashboards = useQuery({ queryKey: ["dashboard-dashboards"], queryFn: () => api<DashboardRecord[]>("/dashboard/dashboards"), enabled: account.role !== "supplier" });
  const storageKey = `gestao-dashboard:${account.id}`;
  const [selectedDashboardId, setSelectedDashboardId] = useState<number | null>(() => {
    const saved = Number(localStorage.getItem(storageKey));
    return Number.isSafeInteger(saved) && saved > 0 ? saved : null;
  });
  const [addingDashboard, setAddingDashboard] = useState(false);
  const [dashboardName, setDashboardName] = useState("");
  const [renamingDashboard, setRenamingDashboard] = useState(false);
  const [renameDraft, setRenameDraft] = useState("");
  const selectedDashboard = dashboards.data?.find((item) => item.id === selectedDashboardId) ?? dashboards.data?.find((item) => item.is_default) ?? dashboards.data?.[0];
  const dashboardId = selectedDashboard?.id;
  useEffect(() => {
    if (selectedDashboard && selectedDashboard.id !== selectedDashboardId) setSelectedDashboardId(selectedDashboard.id);
  }, [selectedDashboard, selectedDashboardId]);
  useEffect(() => {
    if (dashboardId) localStorage.setItem(storageKey, String(dashboardId));
  }, [dashboardId, storageKey]);
  const widgets = useQuery({ queryKey: ["dashboard-widgets", dashboardId], queryFn: () => api<DashboardWidget[]>(`/dashboard/widgets?dashboard_id=${dashboardId}`), enabled: dashboardId !== undefined });
  const shareGroups = useQuery({ queryKey: ["share-groups"], queryFn: () => api<{ id: number; name: string }[]>("/directory/groups"), enabled: account.permissions.includes("manage_planning") });
  const [addingWidget, setAddingWidget] = useState(false);
  const defaultResultColumns = ["key", "summary", "status", "priority", "assignee", "due"];
  const [widgetDraft, setWidgetDraft] = useState({ name: "", dashboard_id: null as number | null, jql: "", group_by: "status", group_by_secondary: null as string | null, measure: "count", chart: "bar", result_columns: defaultResultColumns, max_results: 50, shared: false, shared_roles: [] as string[], shared_group_ids: [] as number[] });
  const moveWidget = (index: number, direction: -1 | 1) => {
    const current = [...(widgets.data ?? [])];
    const nextIndex = index + direction;
    if (nextIndex < 0 || nextIndex >= current.length) return;
    [current[index], current[nextIndex]] = [current[nextIndex], current[index]];
    void run(() => api("/dashboard/widgets/order", "PUT", { dashboard_id: dashboardId, ids: current.map((widget) => widget.id) }));
  };
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
      {account.role !== "supplier" && <section className="panel dashboard-customize">
        <div className="dashboard-toolbar">
          <Label title="Dashboard"><select aria-label="Dashboard" value={dashboardId ?? ""} onChange={(event) => setSelectedDashboardId(Number(event.target.value))}>{(dashboards.data ?? []).map((item) => <option value={item.id} key={item.id}>{item.name}{item.read_only ? ` · compartilhado por ${item.owner_name ?? "equipe"}` : ""}</option>)}</select></Label>
          <button onClick={() => setAddingDashboard((value) => !value)}>{addingDashboard ? "Fechar" : "+ Novo dashboard"}</button>
          {selectedDashboard && !selectedDashboard.read_only && !selectedDashboard.is_default && <button onClick={() => { setRenameDraft(selectedDashboard.name); setRenamingDashboard((value) => !value); }}>Renomear</button>}
          {selectedDashboard && !selectedDashboard.read_only && !selectedDashboard.is_default && <button className="danger" disabled={!!widgets.data?.length} title={widgets.data?.length ? "Remova os widgets antes de excluir" : "Excluir dashboard vazio"} onClick={() => { if (window.confirm(`Excluir o dashboard vazio “${selectedDashboard.name}”?`)) void run(() => api(`/dashboard/dashboards/${selectedDashboard.id}`, "DELETE")); }}>Excluir</button>}
        </div>
        {addingDashboard && <div className="dashboard-create"><Label title="Nome do dashboard"><input value={dashboardName} onChange={(event) => setDashboardName(event.target.value)} maxLength={100} placeholder="Ex.: Acompanhamento de entregas" /></Label><button className="primary" disabled={!dashboardName.trim()} onClick={() => run(async () => { const created = await api<DashboardRecord>("/dashboard/dashboards", "POST", { name: dashboardName }); setDashboardName(""); setAddingDashboard(false); setSelectedDashboardId(created.id); })}>Criar dashboard</button></div>}
        {renamingDashboard && selectedDashboard && <div className="dashboard-create"><Label title="Novo nome"><input value={renameDraft} onChange={(event) => setRenameDraft(event.target.value)} maxLength={100} /></Label><button className="primary" disabled={!renameDraft.trim()} onClick={() => run(async () => { await api(`/dashboard/dashboards/${selectedDashboard.id}`, "PUT", { name: renameDraft }); setRenamingDashboard(false); })}>Salvar nome</button><button onClick={() => setRenamingDashboard(false)}>Cancelar</button></div>}
        <div className="section-title"><h3>Widgets de {selectedDashboard?.name ?? "dashboard"}</h3><button disabled={!selectedDashboard || selectedDashboard.read_only} onClick={() => { setWidgetDraft({ name: "", dashboard_id: dashboardId ?? null, jql: "", group_by: "status", group_by_secondary: null, measure: "count", chart: "bar", result_columns: defaultResultColumns, max_results: 50, shared: false, shared_roles: [], shared_group_ids: [] }); setAddingWidget((value) => !value); }}>{addingWidget ? "Fechar" : "+ Adicionar widget"}</button></div>
        {selectedDashboard?.read_only && <p className="muted">Este dashboard é compartilhado; você pode consultar e reorganizar seus widgets, mas não alterar o painel original.</p>}
        {addingWidget && <div className="form-grid">
          <Label title="Título"><input value={widgetDraft.name} onChange={(e) => setWidgetDraft({ ...widgetDraft, name: e.target.value })} placeholder="Ex.: Cards por status" /></Label>
          <Label title="Filtro avançado (opcional)"><textarea value={widgetDraft.jql} onChange={(e) => setWidgetDraft({ ...widgetDraft, jql: e.target.value })} maxLength={1000} rows={2} placeholder={'Ex.: priority >= 2 AND status != done'} /><small className="muted">Usa a sintaxe do quadro e refina os filtros do painel. Para widgets compartilhados, não use `text ~` nem campos personalizados.</small></Label>
          <Label title="Agrupar por"><select disabled={widgetDraft.measure === "created_vs_resolved" || widgetDraft.chart === "filter_results"} value={widgetDraft.group_by} onChange={(e) => setWidgetDraft({ ...widgetDraft, group_by: e.target.value, ...(e.target.value === widgetDraft.group_by_secondary ? { group_by_secondary: null, chart: "bar" } : {}) })}><option value="status">Status</option><option value="priority">Prioridade</option><option value="supplier">Fornecedor</option><option value="assignee">Responsável interno</option><option value="sprint">Sprint</option><option value="work_type">Tipo de card</option><option value="approval">Aprovação de horas</option><option value="release">Release</option><option value="component">Componente</option><option value="parent">Card pai</option><option value="due_month">Mês do prazo</option><option value="created_month">Mês de criação</option><option value="resolved_month">Mês de resolução</option><option value="overdue">Situação do prazo</option></select></Label>
          {widgetDraft.chart === "matrix" && <Label title="Cruzar também com"><select value={widgetDraft.group_by_secondary ?? "priority"} onChange={(event) => setWidgetDraft({ ...widgetDraft, group_by_secondary: event.target.value })}><option value="status">Status</option><option value="priority">Prioridade</option><option value="supplier">Fornecedor</option><option value="assignee">Responsável interno</option><option value="sprint">Sprint</option><option value="work_type">Tipo de card</option><option value="approval">Aprovação de horas</option><option value="release">Release</option><option value="component">Componente</option><option value="parent">Card pai</option><option value="due_month">Mês do prazo</option><option value="created_month">Mês de criação</option><option value="resolved_month">Mês de resolução</option><option value="overdue">Situação do prazo</option></select></Label>}
          <Label title="Medida"><select disabled={widgetDraft.chart === "filter_results"} value={widgetDraft.measure} onChange={(e) => { const measure = e.target.value; setWidgetDraft({ ...widgetDraft, measure, ...(measure === "created_vs_resolved" ? { group_by: "created_month", group_by_secondary: null, chart: "line" } : {}) }); }}><option value="count">Quantidade de cards</option><option value="estimated_minutes">Horas previstas</option><option value="used_minutes">Horas utilizadas</option><option value="remaining_minutes">Saldo estimado restante</option><option value="avg_open_age_days">Idade média de cards abertos (dias)</option><option value="avg_current_status_days">Tempo médio na etapa atual (dias)</option><option value="avg_resolution_days">Tempo médio até conclusão (dias)</option><option value="created_vs_resolved">Cards criados × concluídos</option>{account.permissions.includes("view_financial") && <option value="cost_cents">Custo aprovado</option>}</select></Label>
          <Label title="Apresentação"><select disabled={widgetDraft.measure === "created_vs_resolved"} value={widgetDraft.chart} onChange={(e) => { const chart = e.target.value; setWidgetDraft({ ...widgetDraft, chart, measure: chart === "filter_results" ? "count" : widgetDraft.measure, group_by_secondary: chart === "matrix" ? (widgetDraft.group_by === "priority" ? "status" : "priority") : null }); }}><option value="bar">Barras</option><option value="line">Linha</option><option value="pie">Pizza</option><option value="metric">Lista</option><option value="matrix">Matriz 2D</option><option value="filter_results">Resultados (tabela)</option></select></Label>
          {widgetDraft.chart === "filter_results" && <div className="dashboard-result-options"><strong>Colunas do resultado</strong><div>{[["key", "Chave"], ["summary", "Resumo"], ["status", "Etapa"], ["priority", "Prioridade"], ["assignee", "Responsável"], ["supplier", "Fornecedor"], ["sprint", "Sprint"], ["due", "Prazo"], ["created_at", "Criado em"], ["work_type", "Tipo"]].map(([key, label]) => <label key={key}><input type="checkbox" checked={widgetDraft.result_columns.includes(key)} onChange={(e) => setWidgetDraft({ ...widgetDraft, result_columns: e.target.checked ? [...widgetDraft.result_columns, key] : widgetDraft.result_columns.filter((item) => item !== key) })} />{label}</label>)}</div><Label title="Máximo de cards"><input type="number" min={1} max={100} value={widgetDraft.max_results} onChange={(e) => setWidgetDraft({ ...widgetDraft, max_results: Number(e.target.value) })} /></Label></div>}
          {account.permissions.includes("manage_planning") && <div className="share-role-options"><label><input type="checkbox" checked={widgetDraft.shared} onChange={(e) => setWidgetDraft({ ...widgetDraft, shared: e.target.checked, shared_roles: e.target.checked ? ["admin", "manager", "internal"] : [], shared_group_ids: e.target.checked ? widgetDraft.shared_group_ids : [] })} /> Compartilhar widget</label>{widgetDraft.shared && <><span>Perfis internos:</span>{(["admin", "manager", "internal"] as const).map((role) => <label key={role}><input type="checkbox" checked={widgetDraft.shared_roles.includes(role)} onChange={(e) => setWidgetDraft({ ...widgetDraft, shared_roles: e.target.checked ? [...widgetDraft.shared_roles, role] : widgetDraft.shared_roles.filter((item) => item !== role) })} />{{admin:"Administradores",manager:"Gestores",internal:"Equipe interna"}[role]}</label>)}{(shareGroups.data ?? []).length > 0 && <><span>Grupos internos:</span>{shareGroups.data?.map((group) => <label key={group.id}><input type="checkbox" checked={widgetDraft.shared_group_ids.includes(group.id)} onChange={(e) => setWidgetDraft({ ...widgetDraft, shared_group_ids: e.target.checked ? [...widgetDraft.shared_group_ids, group.id] : widgetDraft.shared_group_ids.filter((id) => id !== group.id) })} />{group.name}</label>)}</>}</>}</div>}
          <button className="primary" disabled={!widgetDraft.name.trim() || (widgetDraft.chart === "filter_results" && !widgetDraft.result_columns.length)} onClick={() => run(async () => { await api("/dashboard/widgets", "POST", { ...widgetDraft, dashboard_id: dashboardId }); setWidgetDraft({ name: "", dashboard_id: dashboardId ?? null, jql: "", group_by: "status", group_by_secondary: null, measure: "count", chart: "bar", result_columns: defaultResultColumns, max_results: 50, shared: false, shared_roles: [], shared_group_ids: [] }); setAddingWidget(false); })}>Salvar widget</button>
        </div>}
        {widgets.isError && <p role="alert">{widgets.error.message}</p>}
        {!!widgets.data?.length && <div className="dashboard-widgets">{widgets.data.map((widget, index) => <DashboardGadget key={widget.id} widget={widget} query={query} canDelete={widget.owner_id === account.id} canMoveUp={index > 0} canMoveDown={index < widgets.data!.length - 1} moveUp={() => moveWidget(index, -1)} moveDown={() => moveWidget(index, 1)} remove={() => run(() => api(`/dashboard/widgets/${widget.id}`, "DELETE"))} />)}</div>}
        {!widgets.isPending && !widgets.data?.length && <p className="muted">Adicione gráficos ou indicadores pessoais. Gestores autorizados podem compartilhar widgets com usuários internos.</p>}
      </section>}
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
                label: row.label ?? stages[row.status] ?? row.status,
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

type WidgetDatum = { name?: string; row?: string; column?: string; value?: number; created?: number; resolved?: number; [key: string]: string | number | undefined };
const resultColumnLabels: Record<string, string> = { key: "Chave", summary: "Resumo", status: "Etapa", priority: "Prioridade", assignee: "Responsável", supplier: "Fornecedor", sprint: "Sprint", due: "Prazo", created_at: "Criado em", work_type: "Tipo" };
function DashboardFilterResults({ data, columns, total }: { data: WidgetDatum[]; columns: string[]; total: number }) {
  return <div className="dashboard-results-wrap"><table className="dashboard-results"><caption className="sr-only">Cards correspondentes aos filtros do widget</caption><thead><tr>{columns.map((column) => <th scope="col" key={column}>{resultColumnLabels[column] ?? column}</th>)}</tr></thead><tbody>{data.map((row, index) => <tr key={String(row.key ?? index)}>{columns.map((column) => <td key={column}>{row[column] === undefined || row[column] === null || row[column] === "" ? "—" : String(row[column])}</td>)}</tr>)}</tbody></table><p className="dashboard-results-count">Mostrando {data.length} de {total} {total === 1 ? "card" : "cards"}</p></div>;
}
function DashboardMatrix({ data, rowLabel, columnLabel }: { data: WidgetDatum[]; rowLabel: string; columnLabel: string }) {
  const rows = [...new Set(data.map((item) => item.row ?? ""))].sort((a, b) => a.localeCompare(b, "pt-BR", { numeric: true }));
  const columns = [...new Set(data.map((item) => item.column ?? ""))].sort((a, b) => a.localeCompare(b, "pt-BR", { numeric: true }));
  return <div className="gadget-matrix-wrap"><table className="gadget-matrix"><caption>{rowLabel} por {columnLabel}</caption><thead><tr><th scope="col">{rowLabel} ↓ / {columnLabel} →</th>{columns.map((column) => <th scope="col" key={column}>{column}</th>)}</tr></thead><tbody>{rows.map((row) => <tr key={row}><th scope="row">{row}</th>{columns.map((column) => <td key={column}>{(data.find((item) => item.row === row && item.column === column)?.value ?? 0).toLocaleString("pt-BR")}</td>)}</tr>)}</tbody></table></div>;
}

function DashboardGadget({ widget, query, canDelete, canMoveUp, canMoveDown, moveUp, moveDown, remove }: { widget: DashboardWidget; query: string; canDelete: boolean; canMoveUp: boolean; canMoveDown: boolean; moveUp: () => void; moveDown: () => void; remove: () => void }) {
  const result = useQuery({ queryKey: ["dashboard-widget-data", widget.id, query], queryFn: () => api<{ name: string; measure: string; chart: string; data: WidgetDatum[]; result_columns?: string[]; max_results?: number; total?: number }>(`/dashboard/widgets/${widget.id}/data?${query}`) });
  const measureLabel = widget.measure === "cost_cents" ? "centavos" : widget.measure.endsWith("minutes") ? "minutos" : widget.measure === "avg_open_age_days" ? "dias (média de abertos)" : widget.measure === "avg_current_status_days" ? "dias (média na etapa atual)" : widget.measure === "avg_resolution_days" ? "dias (média até conclusão)" : widget.measure === "created_vs_resolved" ? "criados × concluídos" : "cards";
  const groupLabel: Record<string, string> = { status: "Status", priority: "Prioridade", supplier: "Fornecedor", sprint: "Sprint", approval: "Aprovação", work_type: "Tipo de card", assignee: "Responsável", release: "Release", component: "Componente", parent: "Card pai", due_month: "Mês do prazo", created_month: "Mês de criação", resolved_month: "Mês de resolução", overdue: "Situação do prazo" };
  return <article className="dashboard-gadget"><header><div><strong>{widget.name}</strong><small>{widget.chart === "filter_results" ? `Resultados · até ${widget.max_results} cards` : `${groupLabel[widget.group_by] ?? widget.group_by}${widget.group_by_secondary ? ` × ${groupLabel[widget.group_by_secondary] ?? widget.group_by_secondary}` : ""} · ${measureLabel}`}{widget.shared ? " · Compartilhado" : ""}</small>{widget.jql && <small title={widget.jql}>Filtro: <code>{widget.jql}</code></small>}</div><div className="dashboard-gadget-actions"><button type="button" aria-label={`Mover ${widget.name} para cima`} title="Mover para cima" disabled={!canMoveUp} onClick={moveUp}><ArrowUp size={15} /></button><button type="button" aria-label={`Mover ${widget.name} para baixo`} title="Mover para baixo" disabled={!canMoveDown} onClick={moveDown}><ArrowDown size={15} /></button>{canDelete && <button type="button" aria-label={`Excluir widget ${widget.name}`} onClick={remove}>×</button>}</div></header>
    {result.isPending ? <Empty>Carregando indicador…</Empty> : result.isError ? <p role="alert">{result.error.message}</p> : !result.data.data.length ? <Empty>Sem dados no recorte atual.</Empty> : widget.chart === "filter_results" ? <DashboardFilterResults data={result.data.data} columns={result.data.result_columns ?? widget.result_columns} total={result.data.total ?? result.data.data.length} /> : widget.chart === "matrix" ? <DashboardMatrix data={result.data.data} rowLabel={groupLabel[widget.group_by] ?? widget.group_by} columnLabel={groupLabel[widget.group_by_secondary ?? ""] ?? widget.group_by_secondary ?? "Dimensão"} /> : widget.chart === "metric" ? <ul className="gadget-list">{result.data.data.map((item) => <li key={item.name}><span>{item.name}</span><strong>{item.value}</strong></li>)}</ul> : <div className="gadget-chart"><ResponsiveContainer width="100%" height={230}>{widget.chart === "pie" ? <PieChart><Pie data={result.data.data} dataKey="value" nameKey="name" outerRadius={82} label>{result.data.data.map((entry, index) => <Cell key={entry.name} fill={dashboardColors[index % dashboardColors.length]} />)}</Pie><Tooltip /></PieChart> : widget.chart === "line" ? <LineChart data={result.data.data}><XAxis dataKey="name" tick={{ fontSize: 11 }} /><YAxis allowDecimals={widget.measure.startsWith("avg_")} /><Tooltip />{widget.measure === "created_vs_resolved" ? <><Legend /><Line type="monotone" dataKey="created" name="Criados" stroke="#2459bd" strokeWidth={3} dot /><Line type="monotone" dataKey="resolved" name="Concluídos" stroke="#367d68" strokeWidth={3} dot /></> : <Line type="monotone" dataKey="value" name={measureLabel} stroke="#2459bd" strokeWidth={3} dot />}</LineChart> : <BarChart data={result.data.data}><XAxis dataKey="name" tick={{ fontSize: 11 }} /><YAxis allowDecimals={widget.measure.startsWith("avg_")} /><Tooltip /><Bar dataKey="value" fill="#2459bd" radius={[5,5,0,0]} /></BarChart>}</ResponsiveContainer></div>}
  </article>;
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
      <AgileReports />
      <PlanningReports />
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

type AgileReportData = {
  sprint: { id: number; name: string; starts: string; ends: string; state: string };
  filter: { jql: string };
  summary: { committed_cards: number; completed_cards: number; completion_percent: number; planned_hours: number; completed_planned_hours: number };
  issues: {
    completed: { task_id: number; title: string; status: string; estimated_hours: number }[];
    not_completed: { task_id: number; title: string; status: string; estimated_hours: number }[];
    added_during_sprint: { task_id: number; title: string; status: string; estimated_hours: number }[];
  };
  burndown: { date: string; remaining: number }[];
  effort_burndown: { date: string; remaining_hours: number; scope_hours: number }[];
  burnup: { date: string; completed: number }[];
  cumulative_flow: { date: string; [status: string]: number | string }[];
  cycle_times: { task_id: number; started_on: string; completed_on: string; cycle_number: number; days: number }[];
  cycle_window: { start_status: string; end_status: string };
  control_chart: { sample_count: number; average_days: number | null; p50_days: number | null; p85_days: number | null; p95_days: number | null; minimum_days: number | null; maximum_days: number | null };
  velocity: { sprint: string; planned_hours: number; completed_hours: number }[];
  forecast: {
    status: "ready" | "insufficient_history" | "zero_lower_velocity" | "no_remaining_work";
    history_sprints: number;
    remaining_planned_hours: number;
    median_completed_hours_per_sprint: number | null;
    p25_completed_hours_per_sprint: number | null;
    p75_completed_hours_per_sprint: number | null;
    expected_sprints: number | null;
    minimum_sprints: number | null;
    maximum_sprints: number | null;
    method: string;
  };
  definitions: Record<string, string>;
};

function AgileReports() {
  const sprints = useQuery({ queryKey: ["agile-report-sprints"], queryFn: () => api<Sprint[]>("/sprints?limit=100") });
  const [selection, setSelection] = useState("");
  const [queryDraft, setQueryDraft] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [cycleStartStatus, setCycleStartStatus] = useState("production");
  const [cycleEndStatus, setCycleEndStatus] = useState("done");
  const available = sprints.data ?? [];
  const selected = selection || String(available.find((row) => row.state === "active")?.id ?? available[0]?.id ?? "");
  const boardColumns = useQuery({ queryKey: ["board-columns", "agile-report"], queryFn: () => api<{ key: string; title: string }[]>("/board/columns") });
  const report = useQuery({
    queryKey: ["agile-report", selected, appliedQuery, cycleStartStatus, cycleEndStatus],
    enabled: Boolean(selected),
    queryFn: () => {
      const params = new URLSearchParams();
      if (appliedQuery) params.set("jql", appliedQuery);
      params.set("cycle_start_status", cycleStartStatus);
      params.set("cycle_end_status", cycleEndStatus);
      return api<AgileReportData>(`/reports/agile/${selected}?${params.toString()}`);
    },
  });
  const colors: Record<string, string> = { backlog: "#8b95a7", todo: "#4c76c8", production: "#7654bd", review: "#d18432", done: "#3a8d69" };
  const flowStatuses = report.data?.cumulative_flow[0]
    ? Object.keys(report.data.cumulative_flow[0]).filter((key) => key !== "date")
    : [];
  return <section className="panel agile-reports">
    <div className="section-title"><div><span className="eyebrow">ANÁLISES ÁGEIS</span><h2>Relatórios da sprint</h2><p className="muted">Burndown, fluxo cumulativo, ciclo e velocidade por horas planejadas.</p></div>
      <Label title="Sprint analisada"><select value={selected} onChange={(event) => setSelection(event.target.value)}><option value="">Selecione uma sprint</option>{available.map((row) => <option key={row.id} value={row.id}>{row.name} · {row.state === "closed" ? "Encerrada" : row.state === "active" ? "Ativa" : "Planejada"}</option>)}</select></Label>
    </div>
    <form className="agile-report-filter" onSubmit={(event) => { event.preventDefault(); setAppliedQuery(queryDraft.trim()); }}>
      <Label title="Filtro avançado (JQL compatível)"><input value={queryDraft} onChange={(event) => setQueryDraft(event.target.value)} placeholder={'Ex.: priority >= 2 AND status != done'} aria-describedby="agile-jql-help" /></Label>
      <button type="submit">Aplicar filtro</button>
      {appliedQuery && <button type="button" className="secondary" onClick={() => { setQueryDraft(""); setAppliedQuery(""); }}>Limpar</button>}
      <small id="agile-jql-help" className="muted">O filtro afeta os cards da sprint e a velocidade histórica. Use a sintaxe de consulta avançada disponível no quadro.</small>
    </form>
    {sprints.isPending ? <Empty>Carregando sprints…</Empty> : !selected ? <Empty>Cadastre uma sprint para gerar os relatórios.</Empty> : report.isPending ? <Empty>Carregando análise…</Empty> : report.isError ? <p role="alert" className="rejection">{report.error.message}</p> : report.data && <>
      <p className="muted">{report.data.sprint.starts} — {report.data.sprint.ends} · As séries usam o histórico registrado e respeitam as tarefas vinculadas à sprint.</p>
      <div className="agile-summary-grid"><article><small>Cards comprometidos</small><strong>{report.data.summary.committed_cards}</strong></article><article><small>Cards concluídos</small><strong>{report.data.summary.completed_cards}</strong></article><article><small>Conclusão</small><strong>{report.data.summary.completion_percent}%</strong></article><article><small>Horas planejadas concluídas</small><strong>{report.data.summary.completed_planned_hours}h / {report.data.summary.planned_hours}h</strong></article></div>
      <div className="agile-chart-grid agile-issue-groups">
        {([ ["completed", "Concluídos"], ["not_completed", "Não concluídos"], ["added_during_sprint", "Adicionados durante a sprint"] ] as const).map(([key, heading]) => <article className="panel" key={key}>
          <div className="section-title"><h3>{heading}</h3><span className="badge">{report.data.issues[key].length}</span></div>
          {report.data.issues[key].length ? <ul className="gadget-list">{report.data.issues[key].map((issue) => <li key={issue.task_id}><span><strong>OS-{issue.task_id}</strong> · {issue.title}<small className="muted">{stages[issue.status] ?? issue.status} · {issue.estimated_hours}h planejadas</small></span></li>)}</ul> : <Empty>Nenhum card nesta lista.</Empty>}
        </article>)}
      </div>
      <article className="panel agile-forecast" aria-label="Previsão de capacidade">
        <div className="section-title"><div><h3>Previsão por velocidade histórica</h3><p className="muted">Estimativa de sprints para concluir o trabalho planejado restante; não projeta uma data de entrega.</p></div><span className={`badge ${report.data.forecast.status === "ready" || report.data.forecast.status === "no_remaining_work" ? "done" : "review"}`}>{report.data.forecast.status === "no_remaining_work" ? "Sem trabalho restante" : report.data.forecast.status === "ready" ? "Histórico suficiente" : "Histórico insuficiente"}</span></div>
        {report.data.forecast.expected_sprints !== null ? <div className="agile-summary-grid"><article><small>Faixa provável</small><strong>{report.data.forecast.minimum_sprints}–{report.data.forecast.maximum_sprints} sprints</strong></article><article><small>Estimativa central</small><strong>{report.data.forecast.expected_sprints} sprints</strong></article><article><small>Trabalho planejado restante</small><strong>{report.data.forecast.remaining_planned_hours}h</strong></article><article><small>Velocidade mediana</small><strong>{report.data.forecast.median_completed_hours_per_sprint ?? 0}h / sprint</strong></article></div> : <p role="status" className="muted">{report.data.forecast.status === "zero_lower_velocity" ? "Não foi possível calcular um limite conservador porque a velocidade histórica inclui sprints sem horas concluídas." : `São necessárias pelo menos três sprints encerradas anteriores; há ${report.data.forecast.history_sprints}.`}</p>}
        <p className="muted">{report.data.forecast.method} A faixa usa os percentis 25 e 75; a estimativa central usa a mediana. Base: {report.data.forecast.history_sprints} sprint(s).</p>
      </article>
      <div className="agile-chart-grid">
        <article className="panel"><h3>Burndown de cards</h3><p className="muted">{report.data.definitions.burndown}</p>{report.data.burndown.length ? <ResponsiveContainer width="100%" height={240}><LineChart data={report.data.burndown}><XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={24} /><YAxis allowDecimals={false} /><Tooltip /><Line type="monotone" dataKey="remaining" name="Pendentes" stroke="#2459bd" strokeWidth={3} dot={false} /></LineChart></ResponsiveContainer> : <Empty>Sem dias registrados nesta sprint.</Empty>}</article>
        <article className="panel"><h3>Burndown de esforço e escopo</h3><p className="muted">{report.data.definitions.effort_burndown}</p>{report.data.effort_burndown.length ? <ResponsiveContainer width="100%" height={240}><LineChart data={report.data.effort_burndown}><XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={24} /><YAxis /><Tooltip formatter={(value) => [`${value}h`, "Horas"]} /><Line type="monotone" dataKey="remaining_hours" name="Horas restantes" stroke="#2459bd" strokeWidth={3} dot={false} /><Line type="monotone" dataKey="scope_hours" name="Escopo estimado" stroke="#d18432" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer> : <Empty>Sem dias registrados nesta sprint.</Empty>}</article>
        <article className="panel"><h3>Burnup de cards</h3><p className="muted">{report.data.definitions.burnup}</p>{report.data.burnup.length ? <ResponsiveContainer width="100%" height={240}><LineChart data={report.data.burnup}><XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={24} /><YAxis allowDecimals={false} /><Tooltip /><Line type="monotone" dataKey="completed" name="Concluídos" stroke="#367d68" strokeWidth={3} dot={false} /></LineChart></ResponsiveContainer> : <Empty>Sem dias registrados nesta sprint.</Empty>}</article>
        <article className="panel"><h3>Fluxo cumulativo</h3><p className="muted">Contagem diária por coluna, reconstruída das transições auditadas.</p>{report.data.cumulative_flow.length ? <ResponsiveContainer width="100%" height={240}><LineChart data={report.data.cumulative_flow}><XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={24} /><YAxis allowDecimals={false} /><Tooltip />{flowStatuses.map((key, index) => <Line key={key} type="monotone" dataKey={key} name={stages[key] ?? key} stroke={colors[key] ?? dashboardColors[index % dashboardColors.length]} dot={false} />)}</LineChart></ResponsiveContainer> : <Empty>Sem histórico para mostrar.</Empty>}</article>
        <article className="panel"><h3>Velocidade recente</h3><p className="muted">{report.data.definitions.velocity}</p>{report.data.velocity.length ? <ResponsiveContainer width="100%" height={230}><BarChart data={report.data.velocity}><XAxis dataKey="sprint" tick={{ fontSize: 10 }} /><YAxis /><Tooltip /><Bar dataKey="planned_hours" name="Planejado (h)" fill="#9aa5b5" /><Bar dataKey="completed_hours" name="Concluído (h)" fill="#367d68" /></BarChart></ResponsiveContainer> : <Empty>Encerre sprints para formar histórico de velocidade.</Empty>}</article>
        <article className="panel"><h3>Tempo de ciclo</h3><p className="muted">{report.data.definitions.cycle_time}</p>{report.data.cycle_times.length ? <ul className="gadget-list">{report.data.cycle_times.map((item) => <li key={`${item.task_id}-${item.cycle_number}`}><span>OS-{item.task_id}<small className="muted">Ciclo {item.cycle_number} · {item.started_on} → {item.completed_on}</small></span><strong>{item.days} dias</strong></li>)}</ul> : <Empty>Nenhum ciclo atende às etapas selecionadas.</Empty>}</article>
        <article className="panel"><div className="section-title"><div><h3>Control chart</h3><p className="muted">{report.data.definitions.control_chart}</p></div></div>
          <div className="form-grid"><Label title="Início do ciclo"><select value={cycleStartStatus} onChange={(event) => setCycleStartStatus(event.target.value)}>{(boardColumns.data ?? []).filter((column) => column.key !== cycleEndStatus).map((column) => <option key={column.key} value={column.key}>{column.title}</option>)}</select></Label><Label title="Fim do ciclo"><select value={cycleEndStatus} onChange={(event) => setCycleEndStatus(event.target.value)}>{(boardColumns.data ?? []).filter((column) => column.key !== cycleStartStatus).map((column) => <option key={column.key} value={column.key}>{column.title}</option>)}</select></Label></div>
          {report.data.cycle_times.length ? <>
          <div className="agile-summary-grid"><article><small>Média</small><strong>{report.data.control_chart.average_days} dias</strong></article><article><small>Mediana · P50</small><strong>{report.data.control_chart.p50_days} dias</strong></article><article><small>P85</small><strong>{report.data.control_chart.p85_days} dias</strong></article><article><small>P95</small><strong>{report.data.control_chart.p95_days} dias</strong></article></div>
          <ResponsiveContainer width="100%" height={260}><ScatterChart margin={{ top: 18, right: 20, bottom: 8, left: 0 }}><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" dataKey="cycle_number" name="Conclusão" domain={[1, Math.max(1, report.data.control_chart.sample_count)]} tickFormatter={(value) => report.data.cycle_times[Number(value) - 1]?.completed_on.slice(5) ?? ""} tick={{ fontSize: 10 }} label={{ value: "Conclusões em ordem temporal", position: "insideBottom", offset: -2, fontSize: 10 }} /><YAxis type="number" dataKey="days" name="Ciclo" unit=" d" /><Tooltip formatter={(value) => [`${value} dias`, "Tempo de ciclo"]} labelFormatter={(value) => { const point = report.data?.cycle_times[Number(value) - 1]; return point ? `OS-${point.task_id} · ${point.completed_on}` : "Ciclo"; }} /><ReferenceLine y={report.data.control_chart.p50_days ?? undefined} stroke="#2459bd" strokeDasharray="5 4" label="P50" /><ReferenceLine y={report.data.control_chart.p85_days ?? undefined} stroke="#d18432" strokeDasharray="5 4" label="P85" /><ReferenceLine y={report.data.control_chart.p95_days ?? undefined} stroke="#b44848" strokeDasharray="5 4" label="P95" /><Scatter name="Ciclos" data={report.data.cycle_times} fill="#7654bd" /></ScatterChart></ResponsiveContainer>
          <small className="muted">{report.data.control_chart.sample_count} ciclos · faixa observada: {report.data.control_chart.minimum_days}–{report.data.control_chart.maximum_days} dias.</small>
        </> : <Empty>Sem ciclos concluídos entre as etapas selecionadas.</Empty>}</article>
      </div>
    </>}
  </section>;
}

type PlanningReportData = {
  container: { kind: string; id: number; name: string; starts?: string | null; due?: string | null; released_at?: string | null };
  summary: { cards: number; completed: number; completion_percent: number; estimated_hours: number };
  by_status: { status: string; cards: number }[];
  tasks: { id: number; title: string; work_type: string; parent_id: number | null; status: string; priority: number; due: string | null; estimated_minutes: number; components: string[] }[];
  definition: string;
};
type ReleaseChoice = { id: number; name: string; starts: string | null; due: string | null; released_at: string | null };

function PlanningReports() {
  const [kind, setKind] = useState<"release" | "epic">("release");
  const [identity, setIdentity] = useState("");
  const [queryDraft, setQueryDraft] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const releases = useQuery({ queryKey: ["planning-report-releases"], queryFn: () => api<ReleaseChoice[]>("/releases") });
  const epics = useQuery({ queryKey: ["planning-report-epics"], queryFn: () => api<Task[]>("/tasks?limit=200&jql=type%20%3D%20epic") });
  const choices = kind === "release" ? releases.data ?? [] : (epics.data ?? []).map((row) => ({ id: row.id, name: row.title }));
  const selected = choices.some((row) => String(row.id) === identity) ? identity : String(choices[0]?.id ?? "");
  const report = useQuery({
    queryKey: ["planning-report", kind, selected, appliedQuery],
    enabled: Boolean(selected),
    queryFn: () => api<PlanningReportData>(`/reports/planning/${kind}/${selected}${appliedQuery ? `?jql=${encodeURIComponent(appliedQuery)}` : ""}`),
  });
  return <section className="panel planning-reports">
    <div className="section-title"><div><span className="eyebrow">ACOMPANHAMENTO DE ENTREGA</span><h2>Relatório de release ou épico</h2><p className="muted">Progresso atual, distribuição por status e estimativas, sem valores financeiros.</p></div>
      <div className="form-grid"><Label title="Agrupar por"><select value={kind} onChange={(event) => { setKind(event.target.value as "release" | "epic"); setIdentity(""); }}><option value="release">Release</option><option value="epic">Épico</option></select></Label><Label title={kind === "release" ? "Release" : "Épico"}><select value={selected} onChange={(event) => setIdentity(event.target.value)}><option value="">Selecione</option>{choices.map((row) => <option key={row.id} value={row.id}>{kind === "epic" ? `OS-${row.id} · ` : ""}{row.name}</option>)}</select></Label></div>
    </div>
    <form className="agile-report-filter" onSubmit={(event) => { event.preventDefault(); setAppliedQuery(queryDraft.trim()); }}>
      <Label title="Filtro avançado (JQL compatível)"><input value={queryDraft} onChange={(event) => setQueryDraft(event.target.value)} placeholder={'Ex.: priority >= 2 AND status != done'} aria-describedby="planning-jql-help" /></Label>
      <button type="submit">Aplicar filtro</button>
      {appliedQuery && <button type="button" className="secondary" onClick={() => { setQueryDraft(""); setAppliedQuery(""); }}>Limpar</button>}
      <small id="planning-jql-help" className="muted">Aplica a consulta aos cards e indicadores desta release ou épico.</small>
    </form>
    {!selected ? <Empty>{kind === "release" ? "Cadastre uma release e associe cards." : "Crie um épico e associe atividades filhas."}</Empty> : report.isPending ? <Empty>Carregando relatório…</Empty> : report.isError ? <p role="alert" className="rejection">{report.error.message}</p> : report.data && <>
      <p className="muted">{report.data.container.starts || ""}{report.data.container.due ? ` — ${report.data.container.due}` : ""}{report.data.container.released_at ? ` · Publicada em ${report.data.container.released_at}` : ""}</p>
      <div className="agile-summary-grid"><article><small>Cards associados</small><strong>{report.data.summary.cards}</strong></article><article><small>Concluídos</small><strong>{report.data.summary.completed}</strong></article><article><small>Progresso</small><strong>{report.data.summary.completion_percent}%</strong></article><article><small>Horas estimadas</small><strong>{report.data.summary.estimated_hours}h</strong></article></div>
      <p className="muted">{report.data.definition}</p>
      {report.data.by_status.length > 0 && <ResponsiveContainer width="100%" height={230}><BarChart data={report.data.by_status}><XAxis dataKey="status" tickFormatter={(value) => stages[value] ?? value} /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="cards" name="Cards" fill="#2459bd" radius={[5,5,0,0]} /></BarChart></ResponsiveContainer>}
      <div className="table-wrap"><table><thead><tr><th>Card</th><th>Tipo</th><th>Card pai</th><th>Status</th><th>Prioridade</th><th>Prazo</th><th>Estimativa</th><th>Componentes</th></tr></thead><tbody>{report.data.tasks.map((task) => <tr key={task.id}><td>OS-{task.id} · {task.title}</td><td>{task.work_type === "subtask" ? "Subtarefa" : task.work_type === "epic" ? "Épico" : "Tarefa"}</td><td>{task.parent_id ? `OS-${task.parent_id}` : "—"}</td><td>{stages[task.status] ?? task.status}</td><td>{task.priority}</td><td>{task.due ?? "—"}</td><td>{(task.estimated_minutes / 60).toLocaleString("pt-BR")}h</td><td>{task.components.join(", ") || "—"}</td></tr>)}</tbody></table></div>
    </>}
  </section>;
}
