import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  ListTodo,
  CalendarRange,
  Columns3,
  UsersRound,
  ChartNoAxesCombined,
  Settings2,
  ClipboardCheck,
  Menu,
  X,
  Moon,
  Sun,
  LogOut,
  Search,
  PanelLeftClose,
  PanelLeftOpen,
  Layers3,
  ShieldCheck,
  ChevronRight,
  Bell,
  Filter,
  Rocket,
  Gauge,
  GitBranch,
  Zap,
} from "lucide-react";
import type { Account } from "./types";
import { useTheme } from "./useTheme";
import { api } from "./api";
import { pushEndpointDigest, vapidKeyToUint8Array } from "./push";

type Notice = { id: number; task_id: number; task_title: string; action: string; source_label?: string | null; actor: string; created_at: string; read: boolean };
type NotificationPreferences = { email: string; email_enabled: boolean; email_delivery_configured: boolean };
type PushConfiguration = { available: boolean; public_key: string | null; device_count: number; device_limit: number; active_on_this_browser: boolean };
const actionLabels: Record<string, string> = {
  status_changed: "alterou a etapa",
  hours_submitted: "enviou horas",
  hours_approved: "aprovou as horas",
  hours_rejected: "rejeitou as horas",
  task_updated: "atualizou a atividade",
  task_created: "criou a atividade",
  watch_started: "começou a acompanhar",
  watch_stopped: "parou de acompanhar",
  hours_decided: "registrou uma decisão sobre as horas",
  dependency_added: "adicionou uma dependência",
  dependency_removed: "removeu uma dependência",
  schedule_changed: "alterou o planejamento",
  archived: "arquivou a atividade",
  filter_match: "encontrou uma nova atividade no filtro salvo",
};

const roleNames: Record<string, string> = {
  admin: "Administrador",
  manager: "Gestor",
  internal: "Usuário interno",
  supplier: "Fornecedor",
};
function Navigation({
  account,
  collapsed = false,
  onNavigate,
}: {
  account: Account;
  collapsed?: boolean;
  onNavigate?: () => void;
}) {
  const [search, setSearch] = useState("");
  const location = useLocation();
  const activePlanningTab = new URLSearchParams(location.search).get("aba") ?? "releases";
  const items = [
    {
      to: "/",
      label: "Visão geral",
      icon: LayoutDashboard,
      group: "Operação",
      visible: true,
    },
    {
      to: "/backlog",
      label: account.role === "supplier" ? "Minhas tarefas" : "Backlog",
      icon: ListTodo,
      group: "Operação",
      visible: true,
    },
    {
      to: "/sprints",
      label: "Sprints",
      icon: CalendarRange,
      group: "Operação",
      visible: true,
    },
    {
      to: "/kanban",
      label: "Kanban",
      icon: Columns3,
      group: "Operação",
      visible: true,
    },
    {
      to: "/filtros-salvos",
      label: "Assinaturas de filtros",
      icon: Filter,
      group: "Operação",
      visible: true,
    },
    {
      to: "/planejamento?aba=releases",
      label: "Releases e versões",
      icon: Rocket,
      group: "Configuração",
      visible: account.permissions.includes("manage_planning"),
    },
    {
      to: "/planejamento?aba=components",
      label: "Componentes",
      icon: Layers3,
      group: "Configuração",
      visible: account.permissions.includes("manage_planning"),
    },
    {
      to: "/planejamento?aba=capacity",
      label: "Capacidade da equipe",
      icon: Gauge,
      group: "Configuração",
      visible: account.permissions.includes("manage_capacity"),
    },
    {
      to: "/planejamento?aba=workflow",
      label: "Fluxos de trabalho",
      icon: GitBranch,
      group: "Configuração",
      visible: account.permissions.includes("manage_workflows"),
    },
    {
      to: "/planejamento?aba=automations",
      label: "Automações",
      icon: Zap,
      group: "Configuração",
      visible: account.permissions.includes("manage_automation"),
    },
    {
      to: "/aprovacoes",
      label: "Aprovações de horas",
      icon: ClipboardCheck,
      group: "Gestão",
      visible: account.permissions.includes("approve_hours"),
    },
    {
      to: "/fornecedores",
      label: "Fornecedores",
      icon: UsersRound,
      group: "Gestão",
      visible: account.role !== "supplier",
    },
    {
      to: "/relatorios",
      label: "Relatórios",
      icon: ChartNoAxesCombined,
      group: "Gestão",
      visible: account.role !== "supplier",
    },
    {
      to: "/administracao",
      label: "Administração",
      icon: Settings2,
      group: "Gestão",
      visible: account.permissions.includes("manage_users"),
    },
  ].filter(
    (item) =>
      item.visible &&
      item.label
        .toLocaleLowerCase("pt-BR")
        .includes(search.toLocaleLowerCase("pt-BR")),
  );
  return (
    <>
      {!collapsed && (
        <div className="sidebar-search">
          <Search size={18} aria-hidden="true" />
          <input
            type="search"
            aria-label="Buscar no menu"
            placeholder="Buscar no menu"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
      )}
      <nav aria-label="Menu principal">
        {["Operação", "Gestão", "Configuração"].map((group) => (
          <div className="nav-group" key={group}>
            {!collapsed && items.some((item) => item.group === group) && (
              <p className="nav-group-label">{group}</p>
            )}
            {items
              .filter((item) => item.group === group)
              .map(({ to, label, icon: Icon }) => (
                <NavLink
                  end={to === "/" || to.startsWith("/planejamento?")}
                  key={to}
                  to={to}
                  className={({ isActive }) => {
                    if (to.startsWith("/planejamento?")) {
                      const targetTab = new URLSearchParams(to.split("?")[1]).get("aba");
                      return location.pathname === "/planejamento" && activePlanningTab === targetTab ? "active" : undefined;
                    }
                    return isActive ? "active" : undefined;
                  }}
                  onClick={onNavigate}
                  title={collapsed ? label : undefined}
                  aria-label={collapsed ? label : undefined}
                >
                  <Icon size={20} aria-hidden="true" />
                  <span className={collapsed ? "sr-only" : ""}>{label}</span>
                  <ChevronRight
                    className="nav-arrow"
                    size={14}
                    aria-hidden="true"
                  />
                </NavLink>
              ))}
          </div>
        ))}
        {items.length === 0 && (
          <p className="sidebar-empty">Nenhuma página encontrada.</p>
        )}
      </nav>
    </>
  );
}
export function AppShell({
  account,
  busy,
  onLogout,
  children,
}: {
  account: Account;
  busy: boolean;
  onLogout: () => void;
  children: ReactNode;
}) {
  const [dark, toggleTheme] = useTheme();
  const [collapsed, setCollapsed] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [noticesOpen, setNoticesOpen] = useState(false);
  const [notices, setNotices] = useState<Notice[]>([]);
  const [notificationPreferences, setNotificationPreferences] = useState<NotificationPreferences | null>(null);
  const [notificationPreferencesError, setNotificationPreferencesError] = useState("");
  const [notificationPreferencesSaved, setNotificationPreferencesSaved] = useState(false);
  const [pushConfiguration, setPushConfiguration] = useState<PushConfiguration | null>(null);
  const [pushEnabled, setPushEnabled] = useState(false);
  const [pushBusy, setPushBusy] = useState(false);
  const [pushError, setPushError] = useState("");
  const drawer = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    let active = true;
    const load = () => api<Notice[]>("/notifications?limit=30").then((rows) => { if (active) setNotices(rows); }).catch(() => {});
    void load();
    void api<NotificationPreferences>("/me/notification-preferences").then((value) => { if (active) setNotificationPreferences(value); }).catch(() => {});
    void (async () => {
      try {
        let config = await api<PushConfiguration>("/me/push-configuration");
        if (config.available && window.isSecureContext && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window && Notification.permission === "granted") {
          const registration = await navigator.serviceWorker.register("/push-worker.js");
          const subscription = await registration.pushManager.getSubscription();
          if (subscription) {
            const digest = await pushEndpointDigest(subscription.endpoint);
            config = await api<PushConfiguration>(`/me/push-configuration?endpoint_identity=${digest}`);
          }
        }
        if (active) {
          setPushConfiguration(config);
          setPushEnabled(config.active_on_this_browser);
        }
      } catch {
        if (active) setPushConfiguration(null);
      }
    })();
    const timer = window.setInterval(load, 60_000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);
  const loadNotices = async () => {
    const rows = await api<Notice[]>("/notifications?limit=30");
    setNotices(rows);
    setNoticesOpen((open) => !open);
  };
  const saveNotificationPreferences = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!notificationPreferences) return;
    setNotificationPreferencesError("");
    setNotificationPreferencesSaved(false);
    try {
      const saved = await api<NotificationPreferences>("/me/notification-preferences", "PUT", {
        email: notificationPreferences.email || null,
        email_enabled: notificationPreferences.email_enabled,
      });
      setNotificationPreferences(saved);
      setNotificationPreferencesSaved(true);
    } catch (error) {
      setNotificationPreferencesError(error instanceof Error ? error.message : "Não foi possível salvar as preferências.");
    }
  };
  const togglePushNotifications = async () => {
    if (!pushConfiguration?.available || !pushConfiguration.public_key) return;
    setPushBusy(true);
    setPushError("");
    try {
      if (!window.isSecureContext || !("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
        throw new Error("Este navegador precisa de HTTPS e suporte a notificações push.");
      }
      const registration = await navigator.serviceWorker.register("/push-worker.js");
      let subscription = await registration.pushManager.getSubscription();
      if (pushEnabled) {
        if (subscription) {
          const digest = await pushEndpointDigest(subscription.endpoint);
          await api(`/me/push-subscriptions/${digest}`, "DELETE");
          await subscription.unsubscribe();
        }
        setPushEnabled(false);
        setPushConfiguration((current) => current ? { ...current, active_on_this_browser: false, device_count: Math.max(0, current.device_count - 1) } : current);
      } else {
        if (Notification.permission !== "granted") {
          const permission = await Notification.requestPermission();
          if (permission !== "granted") throw new Error("Permita notificações neste navegador para ativar o push.");
        }
        subscription ??= await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: vapidKeyToUint8Array(pushConfiguration.public_key),
        });
        const saved = await api<{ device_count: number }>("/me/push-subscriptions", "POST", subscription.toJSON());
        setPushEnabled(true);
        setPushConfiguration((current) => current ? { ...current, active_on_this_browser: true, device_count: saved.device_count } : current);
      }
    } catch (error) {
      setPushError(error instanceof Error ? error.message : "Não foi possível atualizar as notificações push.");
    } finally {
      setPushBusy(false);
    }
  };
  const revokeAllPushNotifications = async () => {
    if (!window.confirm("Remover notificações push de todos os seus dispositivos?")) return;
    setPushBusy(true);
    setPushError("");
    try {
      await api("/me/push-subscriptions", "DELETE");
      if ("serviceWorker" in navigator) {
        const registration = await navigator.serviceWorker.getRegistration("/");
        const subscription = await registration?.pushManager.getSubscription();
        await subscription?.unsubscribe();
      }
      setPushEnabled(false);
      setPushConfiguration((current) => current ? { ...current, device_count: 0, active_on_this_browser: false } : current);
    } catch (error) {
      setPushError(error instanceof Error ? error.message : "Não foi possível remover os dispositivos push.");
    } finally {
      setPushBusy(false);
    }
  };
  useEffect(() => {
    const element = drawer.current!;
    if (menuOpen && !element.open) element.showModal();
    if (!menuOpen && element.open) element.close();
  }, [menuOpen]);
  return (
    <div className="shell" data-collapsed={collapsed} aria-busy={busy}>
      <a className="skip-link" href="#conteudo">
        Pular para o conteúdo
      </a>
      <header className="institutional-header">
        <div className="institutional-brand">
          <button
            className="header-icon mobile-menu-trigger"
            aria-label="Abrir menu"
            aria-expanded={menuOpen}
            aria-controls="mobile-navigation"
            onClick={() => setMenuOpen(true)}
          >
            <Menu size={22} aria-hidden="true" />
          </button>
          <NavLink
            to="/"
            className="official-logo"
            aria-label="Sebrae página inicial"
          >
            <img
              src="/marca/sebrae-white.svg"
              alt="Sebrae"
              width="100"
              height="56"
            />
          </NavLink>
          <div className="header-product">
            <strong>Gestão de Demandas</strong>
            <span>Sebrae Ceará</span>
          </div>
        </div>
        <div className="header-actions">
          <button className="header-icon notification-trigger" aria-label={`Notificações, ${notices.filter((notice) => !notice.read).length} não lidas`} aria-expanded={noticesOpen} onClick={() => void loadNotices().catch(() => {})}>
            <Bell size={20} aria-hidden="true" />
            {notices.some((notice) => !notice.read) && <span className="notification-count">{notices.filter((notice) => !notice.read).length}</span>}
          </button>
          <button
            className="header-icon"
            onClick={toggleTheme}
            aria-label={dark ? "Ativar modo claro" : "Ativar modo escuro"}
          >
            {dark ? (
              <Sun size={20} aria-hidden="true" />
            ) : (
              <Moon size={20} aria-hidden="true" />
            )}
          </button>
          <div className="header-account">
            <span className="avatar">
              {account.username.slice(0, 2).toUpperCase()}
            </span>
            <div>
              <strong>{account.username}</strong>
              <small>{roleNames[account.role]}</small>
            </div>
          </div>
          <button
            className="header-icon logout-button"
            aria-label="Sair"
            onClick={onLogout}
            disabled={busy}
          >
            <LogOut size={18} aria-hidden="true" />
            <span>Sair</span>
          </button>
        </div>
      </header>
      {noticesOpen && <section className="notification-popover" aria-label="Notificações">
        <div className="section-title"><strong>Notificações</strong><button onClick={() => setNoticesOpen(false)}>Fechar</button></div>
        {notices.length === 0 ? <p className="muted">Você ainda não tem notificações.</p> : notices.map((notice) => <article className={notice.read ? "notice read" : "notice"} key={notice.id}>
          <div><strong>OS-{notice.task_id} · {notice.task_title}</strong><p>{notice.actor} {actionLabels[notice.action] ?? "registrou uma atualização"}{notice.action === "filter_match" && notice.source_label ? ` “${notice.source_label}”` : ""}.</p><small>{new Date(notice.created_at).toLocaleString("pt-BR")}</small></div>
          {!notice.read && <button onClick={() => api(`/notifications/${notice.id}/read`, "PUT").then(() => setNotices((current) => current.map((row) => row.id === notice.id ? { ...row, read: true } : row))).catch(() => {})}>Marcar como lida</button>}
        </article>)}
        <form className="notification-email-preferences" onSubmit={(event) => void saveNotificationPreferences(event)}>
          <strong>Receber avisos por e-mail</strong>
          <label className="field-label">Seu e-mail<input type="email" maxLength={254} autoComplete="email" value={notificationPreferences?.email ?? ""} disabled={!notificationPreferences} onChange={(event) => { setNotificationPreferences((current) => current ? { ...current, email: event.target.value } : current); setNotificationPreferencesSaved(false); }} placeholder="nome@empresa.com.br" /></label>
          <label className="notification-email-toggle"><input type="checkbox" checked={notificationPreferences?.email_enabled ?? false} disabled={!notificationPreferences?.email_delivery_configured && !notificationPreferences?.email_enabled} onChange={(event) => { setNotificationPreferences((current) => current ? { ...current, email_enabled: event.target.checked } : current); setNotificationPreferencesSaved(false); }} /> Ativar notificações por e-mail</label>
          <small className="muted">O e-mail contém apenas um aviso genérico e um link para entrar na aplicação. Os detalhes do card aparecem depois do login, conforme suas permissões.{notificationPreferences && !notificationPreferences.email_delivery_configured ? " O envio ainda não foi configurado neste ambiente." : ""}</small>
          {notificationPreferencesError && <small className="rejection" role="alert">{notificationPreferencesError}</small>}
          {notificationPreferencesSaved && <small className="success-message" role="status">Preferências salvas.</small>}
          <button type="submit" disabled={!notificationPreferences}>Salvar preferências</button>
        </form>
        <section className="notification-push-preferences" aria-label="Notificações push">
          <strong>Notificações neste navegador</strong>
          <small className="muted">{pushConfiguration?.available ? `${pushConfiguration.device_count} de ${pushConfiguration.device_limit} dispositivos configurados.` : "Push indisponível neste ambiente até que as chaves VAPID sejam configuradas."} Os avisos são genéricos e não mostram dados do card.</small>
          {pushError && <small className="rejection" role="alert">{pushError}</small>}
          <button type="button" disabled={!pushConfiguration?.available || pushBusy} onClick={() => void togglePushNotifications()}>{pushBusy ? "Atualizando…" : pushEnabled ? "Desativar neste navegador" : "Ativar neste navegador"}</button>
          {(pushConfiguration?.device_count ?? 0) > 0 && <button type="button" disabled={pushBusy} onClick={() => void revokeAllPushNotifications()}>Remover de todos os dispositivos</button>}
        </section>
      </section>}
      <aside className="desktop-sidebar">
        <div className="sidebar-heading">
          <Layers3 size={22} aria-hidden="true" />
          {!collapsed && (
            <div>
              <strong>Área de trabalho</strong>
              <small>Demandas e entregas</small>
            </div>
          )}
          <button
            className="sidebar-icon"
            aria-label={collapsed ? "Expandir menu" : "Recolher menu"}
            onClick={() => setCollapsed(!collapsed)}
          >
            {collapsed ? (
              <PanelLeftOpen size={20} aria-hidden="true" />
            ) : (
              <PanelLeftClose size={20} aria-hidden="true" />
            )}
          </button>
        </div>
        <Navigation account={account} collapsed={collapsed} />
        <div className="sidebar-footnote">
          <ShieldCheck size={20} aria-hidden="true" />
          {!collapsed && (
            <span>
              Acesso por perfil
              <br />
              <strong>{roleNames[account.role]}</strong>
            </span>
          )}
        </div>
      </aside>
      <dialog
        id="mobile-navigation"
        ref={drawer}
        className="mobile-navigation"
        aria-label="Menu principal"
        onCancel={(event) => {
          event.preventDefault();
          setMenuOpen(false);
        }}
        onClick={(event) => {
          if (event.target === event.currentTarget) {
            const bounds = event.currentTarget.getBoundingClientRect();
            if (event.clientX > bounds.right) setMenuOpen(false);
          }
        }}
      >
        <div className="sidebar-heading">
          <strong>Navegar no sistema</strong>
          <button
            className="sidebar-icon"
            aria-label="Fechar menu"
            onClick={() => setMenuOpen(false)}
          >
            <X size={22} aria-hidden="true" />
          </button>
        </div>
        <Navigation account={account} onNavigate={() => setMenuOpen(false)} />
      </dialog>
      <div className="content">
        {children}
        <footer className="institutional-footer">
          <div>
            <img
              src={dark ? "/marca/sebrae-white.svg" : "/marca/sebrae-cor.svg"}
              alt="Sebrae"
              width="88"
              height="50"
            />
            <span>
              Gestão de Demandas<small>Sebrae Ceará</small>
            </span>
          </div>
          <span>Versão 1.0</span>
        </footer>
      </div>
    </div>
  );
}
