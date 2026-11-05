import { useEffect, useRef, useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
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
} from "lucide-react";
import type { Account } from "./types";
import { useTheme } from "./useTheme";

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
        {["Operação", "Gestão"].map((group) => (
          <div className="nav-group" key={group}>
            {!collapsed && items.some((item) => item.group === group) && (
              <p className="nav-group-label">{group}</p>
            )}
            {items
              .filter((item) => item.group === group)
              .map(({ to, label, icon: Icon }) => (
                <NavLink
                  end={to === "/"}
                  key={to}
                  to={to}
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
  const drawer = useRef<HTMLDialogElement>(null);
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
