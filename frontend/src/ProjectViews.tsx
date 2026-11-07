import { useLayoutEffect, useRef, useState } from "react";
import type { DragEvent } from "react";
import { ArrowLeft, ArrowRight, CalendarRange, Copy, Download, Eye, KeyRound, Pencil, Plus, Save, Trash2 } from "lucide-react";
import type { Account, Sprint, Task } from "./types";

export type ViewLayout = "board" | "table" | "timeline" | "calendar";
export type SavedProjectView = {
  id: number;
  name: string;
  layout: ViewLayout;
  config: Record<string, any>;
  shared?: boolean;
  shared_roles?: string[];
  shared_group_ids?: number[];
  owner_id?: number;
  position: number;
};
export type ProjectColumn = {
  key: string;
  title: string;
  is_system: boolean;
  category: "todo" | "in_progress" | "done";
  view_order: number;
  wip_limit?: number | null;
};
export type BoardQuickFilter = { id: string; label: string; query: string };
export type TimelineDependency = { id: number; fromTaskId: number; toTaskId: number; type: string };

export function timelineDependencies(tasks: Task[]): TimelineDependency[] {
  const visible = new Set(tasks.map((task) => task.id));
  const seen = new Set<number>();
  const result: TimelineDependency[] = [];
  for (const task of tasks) for (const link of task.links ?? []) {
    if (seen.has(link.id) || !visible.has(link.task_id)) continue;
    seen.add(link.id);
    result.push({
      id: link.id,
      fromTaskId: link.direction === "outgoing" ? task.id : link.task_id,
      toTaskId: link.direction === "outgoing" ? link.task_id : task.id,
      type: link.type,
    });
  }
  return result;
}
export const boardQuickFilters: BoardQuickFilter[] = [
  { id: "overdue", label: "Atrasadas", query: "is:overdue" },
  { id: "no-supplier", label: "Sem fornecedor", query: "no:supplier" },
  { id: "no-sprint", label: "Sem sprint", query: "no:sprint" },
  { id: "pending-approval", label: "Aprovação pendente", query: "approval:pending" },
];

const filterKeys = new Set([
  "status", "state", "supplier", "fornecedor", "sprint", "priority", "label", "labels",
  "approval", "title", "due", "date", "created", "has", "no", "is",
]);
export function isQuickFilterQueryAllowed(query: string): boolean {
  if (!query.trim() || query.length > 300) return false;
  const parts = tokens(query);
  if (!parts.length) return false;
  return parts.every((raw) => {
    const token = raw.startsWith("-") ? raw.slice(1) : raw;
    if (/[()]/.test(token) || ["and", "or", "not", "order", "by"].includes(token.toLowerCase())) return false;
    const colon = token.indexOf(":");
    if (colon < 0) return !/[=<>]/.test(token);
    const key = token.slice(0, colon).toLowerCase();
    const value = token.slice(colon + 1);
    return value.length > 0 && (filterKeys.has(key) || key.startsWith("field."));
  });
}

export function QuickFilters({
  filters,
  active,
  onChange,
  onFiltersChange,
}: {
  filters: BoardQuickFilter[];
  active: string[];
  onChange: (next: string[]) => void;
  onFiltersChange: (next: BoardQuickFilter[]) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [label, setLabel] = useState("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const toggle = (id: string) =>
    onChange(
      active.includes(id) ? active.filter((item) => item !== id) : [...active, id],
    );
  return (
    <nav className="project-quick-filters" aria-label="Filtros rápidos">
      <strong>Filtros rápidos</strong>
      {filters.map((filter) => (
        <button
          key={filter.id}
          type="button"
          aria-pressed={active.includes(filter.id)}
          className={active.includes(filter.id) ? "active" : ""}
          onClick={() => toggle(filter.id)}
        >
          {filter.label}
        </button>
      ))}
      <button type="button" onClick={() => { setEditing((value) => !value); setEditingId(null); setLabel(""); setQuery(""); setError(""); }}>
        {editing ? "Fechar configuração" : "Configurar filtros"}
      </button>
      {active.length > 0 && (
        <button type="button" className="project-quick-filter-clear" onClick={() => onChange([])}>
          Limpar
        </button>
      )}
      {editing && (
        <div className="project-quick-filter-editor">
          <h4>Configurar filtros rápidos</h4>
          <ul>
            {filters.map((filter) => (
              <li key={filter.id}>
                <span><strong>{filter.label}</strong><small>{filter.query}</small></span>
                <button type="button" onClick={() => { setEditingId(filter.id); setLabel(filter.label); setQuery(filter.query); setError(""); }}>Editar</button>
                <button type="button" aria-label={`Remover filtro ${filter.label}`} onClick={() => { onFiltersChange(filters.filter((item) => item.id !== filter.id)); onChange(active.filter((id) => id !== filter.id)); }}>Remover</button>
              </li>
            ))}
          </ul>
          <form onSubmit={(event) => {
            event.preventDefault();
            if (!label.trim()) { setError("Informe um nome para o filtro."); return; }
            if (!isQuickFilterQueryAllowed(query)) { setError("Use a sintaxe simples do quadro, como status:review ou is:overdue."); return; }
            if (!editingId && filters.length >= 20) { setError("Cada visualização pode ter até 20 filtros rápidos."); return; }
            const id = editingId ?? `quick-${globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`}`;
            const next = editingId
              ? filters.map((filter) => filter.id === editingId ? { id, label: label.trim(), query: query.trim() } : filter)
              : [...filters, { id, label: label.trim(), query: query.trim() }];
            onFiltersChange(next);
            setEditingId(null); setLabel(""); setQuery(""); setError("");
          }}>
            <label>Nome<input value={label} onChange={(event) => setLabel(event.target.value)} maxLength={40} /></label>
            <label>Consulta<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={'Ex.: status:review no:sprint'} maxLength={300} /></label>
            <small>As condições são combinadas (AND). Exemplos: <code>is:overdue</code>, <code>approval:pending</code>, <code>supplier:@me</code>.</small>
            {error && <p role="alert">{error}</p>}
            <button type="submit">{editingId ? "Salvar filtro" : "Adicionar filtro"}</button>
            {editingId && <button type="button" onClick={() => { setEditingId(null); setLabel(""); setQuery(""); setError(""); }}>Cancelar edição</button>}
          </form>
        </div>
      )}
    </nav>
  );
}

const tokens = (query: string) =>
  query.match(/-?[\w.-]+:(?:"[^"]*"|'[^']*'|[^\s]+)|"[^"]*"|'[^']*'|\S+/g) ?? [];
const norm = (value: unknown) => String(value ?? "").toLocaleLowerCase("pt-BR");
const present = (value: unknown) => value !== null && value !== undefined && value !== "";
const localDate = (value: Date) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
const parseLocalDate = (value: string) => new Date(`${value.slice(0, 10)}T00:00:00`);
const resolveDate = (value: string) => {
  const relative = value.match(/^@today(?:([+-])(\d+)d)?$/);
  if (!relative) return value;
  const date = new Date(); date.setHours(0, 0, 0, 0);
  if (relative[1]) date.setDate(date.getDate() + (relative[1] === "+" ? 1 : -1) * Number(relative[2]));
  return localDate(date);
};
const dateCompare = (actual: string | null | undefined, query: string) => {
  if (!actual) return false;
  actual = actual.slice(0, 10);
  const range = query.match(/^(.+)\.\.(.+)$/);
  if (range) return actual >= resolveDate(range[1]) && actual <= resolveDate(range[2]);
  const comparison = query.match(/^(>=|<=|>|<)(.+)$/);
  if (comparison) {
    const [, op, raw] = comparison; const value = resolveDate(raw);
    return op === ">" ? actual > value : op === ">=" ? actual >= value : op === "<" ? actual < value : actual <= value;
  }
  return actual === resolveDate(query);
};

/** GitHub Projects-inspired query syntax, limited to data available in this app. */
export function filterBoardTasks(
  tasks: Task[],
  query: string,
  columns: ProjectColumn[],
  suppliers: { id: number; name: string }[],
  sprints: Sprint[] = [],
  meSupplierId?: number,
) {
  const columnName = new Map(columns.map((column) => [column.key, norm(column.title)]));
  const supplierName = new Map(suppliers.map((supplier) => [String(supplier.id), norm(supplier.name)]));
  const sprintName = new Map(sprints.map((sprint) => [String(sprint.id), norm(sprint.name)]));
  const activeSprintIds = new Set(sprints.filter((sprint) => sprint.state === "active").map((sprint) => String(sprint.id)));
  return tasks.filter((task) =>
    tokens(query).every((raw) => {
      const negate = raw.startsWith("-");
      const token = negate ? raw.slice(1) : raw;
      const colon = token.indexOf(":");
      let matched: boolean;
      if (colon < 0) {
        const text = norm(token.replace(/^['"]|['"]$/g, ""));
        matched = [task.title, task.description, task.labels?.map((label) => label.text).join(" "), ...Object.values(task.values ?? {})]
          .some((value) => norm(value).includes(text));
      } else {
        const key = token.slice(0, colon).toLocaleLowerCase("en-US");
        const value = token.slice(colon + 1).replace(/^['"]|['"]$/g, "");
        const choices = value.split(",").map(norm);
        const any = (candidate: unknown) => choices.includes(norm(candidate));
        switch (key) {
          case "status": case "state":
            matched = any(task.status) || any(columnName.get(task.status)); break;
          case "supplier": case "fornecedor":
            matched = choices.some((choice) => choice === "@me" ? task.supplier_id === meSupplierId : norm(task.supplier_id) === choice || supplierName.get(String(task.supplier_id)) === choice); break;
          case "sprint": matched = choices.some((choice) => choice === "@current" ? activeSprintIds.has(String(task.sprint_id)) : norm(task.sprint_id) === choice || sprintName.get(String(task.sprint_id)) === choice); break;
          case "priority": matched = choices.some((choice) => {
            const range = choice.match(/^(\d*)\.\.(\d*)$/);
            if (range) return task.priority >= (range[1] ? Number(range[1]) : Number.NEGATIVE_INFINITY) && task.priority <= (range[2] ? Number(range[2]) : Number.POSITIVE_INFINITY);
            const comparison = choice.match(/^(>=|<=|>|<)(\d+)$/);
            if (!comparison) return task.priority === Number(choice);
            const [, operator, raw] = comparison; const value = Number(raw);
            return operator === ">" ? task.priority > value : operator === ">=" ? task.priority >= value : operator === "<" ? task.priority < value : task.priority <= value;
          }); break;
          case "label": case "labels": matched = (task.labels ?? []).some((label) => any(label.text)); break;
          case "approval": matched = any(task.approval); break;
          case "title": matched = norm(task.title).includes(norm(value)); break;
          case "due": case "date": matched = dateCompare(task.due, value); break;
          case "created": matched = dateCompare(task.created_at, value); break;
          case "has":
            matched = value === "supplier" ? task.supplier_id !== null : value === "sprint" ? task.sprint_id !== null : value === "label" ? !!task.labels?.length : value === "due" ? !!task.due : present(task.values?.[value]); break;
          case "no":
            matched = value === "supplier" ? task.supplier_id === null : value === "sprint" ? task.sprint_id === null : value === "label" ? !task.labels?.length : value === "due" ? !task.due : task.values?.[value] == null || task.values?.[value] === ""; break;
          case "is": matched = value === "closed" ? task.status === "done" : value === "open" ? task.status !== "done" : value === "overdue" ? !!task.due && task.due < new Date().toISOString().slice(0, 10) && task.status !== "done" : false; break;
          default:
            matched = key.startsWith("field.")
              ? any(task.values?.[key.slice(6)])
              : false;
        }
      }
      return negate ? !matched : matched;
    }),
  );
}

export function ViewTools({
  views, activeId, currentUserId, layout, query, advancedQuery, groupBy, sortBy, zoom, fields, visibleFields, sliceBy, sliceValue, sliceOptions, sumBy, descending, financial, shared, sharedRoles, sharedGroupIds, groups, canShare,
  onSelect, onLayout, onQuery, onAdvancedQuery, onGroup, onSort, onZoom, onToggleField, onMoveField, onSliceBy, onSliceValue, onSum, onDirection, onRename, onMoveView, onShared, onSharedRoles, onSharedGroupIds,
  onSave, onDuplicate, onDelete,
}: {
  views: SavedProjectView[]; activeId: number | null; currentUserId: number; layout: ViewLayout; query: string; advancedQuery: string;
  groupBy: string; sortBy: string; zoom: "month" | "quarter" | "year";
  sliceBy: string; sliceValue: string; sliceOptions: { value: string; label: string }[]; sumBy: string; descending: boolean; financial: boolean; shared: boolean; sharedRoles: string[]; sharedGroupIds: number[]; groups: { id: number; name: string }[]; canShare: boolean;
  fields: { key: string; label: string }[]; visibleFields: string[];
  onMoveField: (key: string, direction: number) => void;
  onSelect: (view: SavedProjectView | null) => void; onLayout: (value: ViewLayout) => void;
  onQuery: (value: string) => void; onAdvancedQuery: (value: string) => void; onGroup: (value: string) => void; onSort: (value: string) => void;
  onZoom: (value: "month" | "quarter" | "year") => void; onToggleField: (value: string) => void;
  onSliceBy: (value: string) => void; onSliceValue: (value: string) => void; onSum: (value: string) => void; onDirection: () => void;
  onShared: (value: boolean) => void;
  onSharedRoles: (value: string[]) => void;
  onSharedGroupIds: (value: number[]) => void;
  onRename: () => void; onMoveView: (identity: number, direction: number) => void;
  onSave: (name?: string) => void; onDuplicate: () => void; onDelete: () => void;
}) {
  const [open, setOpen] = useState(true);
  const [newName, setNewName] = useState("");
  const activeOwned = views.find((view) => view.id === activeId)?.owner_id === currentUserId;
  const ownedViews = views.filter((view) => view.owner_id === currentUserId);
  return (
    <section className="project-view-tools" aria-label="Visualizações e filtros">
      <div className="project-view-heading">
        <button className="project-view-toggle" onClick={() => setOpen(!open)} aria-expanded={open}>
          <Eye size={18} aria-hidden="true" /> Views <span>{open ? "−" : "+"}</span>
        </button>
        {views.map((view) => (
          <div className="view-tab-wrap" key={view.id}>
            <button className={activeId === view.id ? "view-tab active" : "view-tab"} onClick={() => onSelect(view)}>{view.name}</button>
            {view.owner_id === currentUserId && <><button className="view-tab-move" aria-label={`Mover visualização ${view.name} para a esquerda`} disabled={ownedViews.findIndex((item) => item.id === view.id) === 0} onClick={() => onMoveView(view.id, -1)}><ArrowLeft size={13} /></button>
            <button className="view-tab-move" aria-label={`Mover visualização ${view.name} para a direita`} disabled={ownedViews.findIndex((item) => item.id === view.id) === ownedViews.length - 1} onClick={() => onMoveView(view.id, 1)}><ArrowRight size={13} /></button></>}
          </div>
        ))}
        {activeId !== null && <button className="view-tab" onClick={() => onSelect(null)}>+ Quadro padrão</button>}
      </div>
      {open && <>
        <div className="project-view-controls">
          <label>Visualização
            <select value={layout} onChange={(event) => onLayout(event.target.value as ViewLayout)}>
              <option value="board">Quadro</option><option value="table">Tabela</option><option value="timeline">Linha do tempo</option><option value="calendar">Calendário</option>
            </select>
          </label>
          <label className="project-filter-search">Filtros
            <input value={query} onChange={(event) => onQuery(event.target.value)} placeholder={'Ex.: status:"Em produção" supplier:3 no:due'} />
          </label>
          <label className="project-filter-search">Consulta avançada (servidor)
            <input value={advancedQuery} onChange={(event) => onAdvancedQuery(event.target.value)} placeholder={'status = "review" OR (type = bug AND priority <= 5)'} />
          </label>
          <small className="project-query-help">Use AND/OR, parênteses, comparações, IN/NOT IN, IS EMPTY e ORDER BY. <code>statusCategory</code> aceita To Do, In Progress e Done; <code>resolutiondate</code> filtra e ordena pela última conclusão auditada, ficando vazio quando o card está reaberto. A busca respeita seu acesso e pode ser salva na visualização.</small>
          <label>Agrupar por
            <select value={groupBy} onChange={(event) => onGroup(event.target.value)}>
              <option value="">Sem agrupamento</option><option value="status">Status</option><option value="supplier">Fornecedor</option><option value="sprint">Sprint</option><option value="priority">Prioridade</option><option value="approval">Aprovação</option><option value="parent">Card pai</option><option value="work_type">Tipo</option>
            </select>
          </label>
          <label>Ordenar por
            <select value={sortBy} onChange={(event) => onSort(event.target.value)}>
              <option value="">Ordem do quadro</option><option value="priority">Prioridade</option><option value="title">Título</option><option value="due">Prazo</option><option value="created_at">Criação</option><option value="supplier">Fornecedor</option>
            </select>
          </label>
          <button className="project-sort-direction" onClick={onDirection} aria-label={descending ? "Ordenação decrescente" : "Ordenação crescente"}>{descending ? "↓ Decrescente" : "↑ Crescente"}</button>
          <label>Recortar por
            <select value={sliceBy} onChange={(event) => { onSliceBy(event.target.value); onSliceValue(""); }}>
              <option value="">Sem recorte</option><option value="status">Status</option><option value="supplier">Fornecedor</option><option value="sprint">Sprint</option><option value="priority">Prioridade</option><option value="approval">Aprovação</option><option value="label">Etiqueta</option>
            </select>
          </label>
          {sliceBy && <label>Valor do recorte
            <select value={sliceValue} onChange={(event) => onSliceValue(event.target.value)}><option value="">Todos</option>{sliceOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select>
          </label>}
          <label>Totalizar
            <select value={sumBy} onChange={(event) => onSum(event.target.value)}><option value="">Sem total</option><option value="count">Quantidade de cards</option><option value="estimated_minutes">Horas previstas</option><option value="used_minutes">Horas utilizadas</option>{financial && <option value="cost_cents">Custo aprovado</option>}</select>
          </label>
          {layout === "timeline" && <label>Escala
            <select value={zoom} onChange={(event) => onZoom(event.target.value as "month" | "quarter" | "year")}>
              <option value="month">Mês</option><option value="quarter">Trimestre</option><option value="year">Ano</option>
            </select>
          </label>}
        </div>
        <details className="project-field-picker"><summary>Campos visíveis na tabela</summary>
          <div>{fields.map((field) => <label key={field.key} className="project-field-option"><input type="checkbox" checked={visibleFields.includes(field.key)} onChange={() => onToggleField(field.key)} /> {field.label}
            {visibleFields.includes(field.key) && <span><button type="button" aria-label={`Mover ${field.label} para antes`} disabled={visibleFields.indexOf(field.key) === 0} onClick={(event) => { event.preventDefault(); event.stopPropagation(); onMoveField(field.key, -1); }}><ArrowLeft size={12} /></button><button type="button" aria-label={`Mover ${field.label} para depois`} disabled={visibleFields.indexOf(field.key) === visibleFields.length - 1} onClick={(event) => { event.preventDefault(); event.stopPropagation(); onMoveField(field.key, 1); }}><ArrowRight size={12} /></button></span>}
          </label>)}</div>
        </details>
        <p className="project-filter-help">Filtros rápidos: texto livre, status, supplier, sprint, priority, label, approval, due, created, has/no e field.ID. Use vírgulas para opções alternativas e “-” para excluir. A consulta avançada usa JQL reduzida no servidor e pode ser salva em uma visualização compartilhada. Ex.: <code>status:review,-label:urgente,due:2026-11-01..2026-12-31</code></p>
        <div className="project-view-save">
          <label aria-label="Nome da visualização"><input value={newName} onChange={(event) => setNewName(event.target.value)} placeholder="Nome da nova visualização" /></label>
          {canShare && <div className="share-view-option"><label><input type="checkbox" checked={shared} onChange={(event) => onShared(event.target.checked)} /> Compartilhar visualização</label>{shared && <div className="share-role-options" aria-label="Públicos com acesso"><span>Perfis internos:</span>{(["admin", "manager", "internal"] as const).map((role) => <label key={role}><input type="checkbox" checked={sharedRoles.includes(role)} onChange={(event) => onSharedRoles(event.target.checked ? [...sharedRoles, role] : sharedRoles.filter((item) => item !== role))} />{{admin:"Administradores",manager:"Gestores",internal:"Equipe interna"}[role]}</label>)}{groups.length > 0 && <><span>Grupos:</span>{groups.map((group) => <label key={group.id}><input type="checkbox" checked={sharedGroupIds.includes(group.id)} onChange={(event) => onSharedGroupIds(event.target.checked ? [...sharedGroupIds, group.id] : sharedGroupIds.filter((id) => id !== group.id))} />{group.name}</label>)}</>}</div>}</div>}
          <button onClick={() => { onSave(newName.trim() || undefined); setNewName(""); }}><Plus size={15} /> Salvar como nova</button>
          {activeId !== null && <>{activeOwned && <><button onClick={() => onSave()}><Save size={15} /> Salvar alterações</button><button onClick={onRename}><Pencil size={15} /> Renomear</button><button className="danger" onClick={onDelete}><Trash2 size={15} /> Excluir</button></>}<button onClick={onDuplicate}><Copy size={15} /> Duplicar</button></>}
        </div>
      </>}
    </section>
  );
}

export function ProjectTable({ tasks, columns, suppliers, fields, visibleFields, groupBy, sumBy, open }: {
  tasks: Task[]; columns: ProjectColumn[]; suppliers: { id: number; name: string }[];
  fields: { key: string; label: string }[]; visibleFields: string[]; groupBy: string; sumBy: string; open: (task: Task) => void;
}) {
  const get = (task: Task, key: string): string => {
    if (key === "title") return `OS-${task.id} · ${task.title}`;
    if (key === "status") return columns.find((column) => column.key === task.status)?.title ?? task.status_title ?? task.status;
    if (key === "supplier") return suppliers.find((row) => row.id === task.supplier_id)?.name ?? "Não atribuído";
    if (key === "sprint") return task.sprint_id ? `Sprint ${task.sprint_id}` : "Sem sprint";
    if (key === "labels") return task.labels?.map((label) => label.text).join(", ") || "—";
    if (key === "due") return task.due ?? "Sem prazo";
    if (key === "priority") return String(task.priority);
    if (key === "approval") return task.approval;
    if (key === "parent") {
      if (!task.parent_id) return "Sem card pai";
      const parent = tasks.find((row) => row.id === task.parent_id);
      return parent ? `OS-${parent.id} · ${parent.title}` : `OS-${task.parent_id}`;
    }
    if (key === "work_type") {
      return ({ epic: "Épico", story: "História", task: "Tarefa", bug: "Bug", subtask: "Subtarefa" } as Record<string, string>)[task.work_type ?? "task"] ?? "Tarefa";
    }
    if (key === "cost_cents") return task.cost_cents == null ? "—" : new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(task.cost_cents / 100);
    if (key === "description") return task.description || "—";
    if (key === "created_at") return task.created_at?.slice(0, 10) ?? "—";
    if (key === "estimated_minutes") return `${(task.estimated_minutes / 60).toFixed(1)} h`;
    if (key === "used_minutes") return `${(task.used_minutes / 60).toFixed(1)} h`;
    return String(task.values?.[key] ?? "—");
  };
  const selectedFields = visibleFields.map((key) => fields.find((field) => field.key === key)).filter((field): field is { key: string; label: string } => !!field);
  const groups = new Map<string, Task[]>();
  for (const task of tasks) {
    const value = groupBy ? get(task, groupBy) : "Todos os cards";
    groups.set(value, [...(groups.get(value) ?? []), task]);
  }
  return <div className="project-table-wrap"><table className="project-table"><thead><tr>{selectedFields.map((field) => <th key={field.key}>{field.label}</th>)}</tr></thead>
    {Array.from(groups.entries()).map(([group, rows]) => <tbody key={group}>{groupBy && <tr className="project-table-group"><th colSpan={selectedFields.length}>{group} <span>{sumBy === "estimated_minutes" ? `${(rows.reduce((sum, task) => sum + task.estimated_minutes, 0) / 60).toFixed(1)} h previstas` : sumBy === "used_minutes" ? `${(rows.reduce((sum, task) => sum + task.used_minutes, 0) / 60).toFixed(1)} h utilizadas` : sumBy === "cost_cents" ? new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(rows.reduce((sum, task) => sum + (task.cost_cents ?? 0), 0) / 100) : `${rows.length} cards`}</span></th></tr>}
      {rows.map((task) => <tr key={task.id}>{selectedFields.map((field) => <td key={field.key}>{field.key === "title" ? <button className="link" onClick={() => open(task)}>{get(task, field.key)}</button> : get(task, field.key)}</td>)}</tr>)}
    </tbody>)}</table>{tasks.length === 0 && <p className="empty">Nenhum card corresponde aos filtros.</p>}</div>;
}

export function TimelineView({ tasks, columns, suppliers, sprints, zoom, account, saveSchedule, open }: {
  tasks: Task[]; columns: ProjectColumn[]; suppliers: { id: number; name: string }[]; zoom: "month" | "quarter" | "year";
  sprints: Sprint[]; account: Account; saveSchedule: (task: Task, plannedStart: string, due: string) => void; open: (task: Task) => void;
}) {
  const timelineRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ taskId: number; startX: number; trackWidth: number; deltaDays: number } | null>(null);
  const [dragPreview, setDragPreview] = useState<{ taskId: number; deltaDays: number } | null>(null);
  const [dependencyPaths, setDependencyPaths] = useState<{ id: number; type: string; path: string; label: string }[]>([]);
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const start = new Date(today.getFullYear(), today.getMonth(), 1);
  if (zoom === "quarter") start.setMonth(Math.floor(start.getMonth() / 3) * 3);
  if (zoom === "year") start.setMonth(0);
  const end = new Date(start);
  if (zoom === "month") end.setMonth(end.getMonth() + 1);
  else if (zoom === "quarter") end.setMonth(end.getMonth() + 3);
  else end.setFullYear(end.getFullYear() + 1);
  const days = (end.getTime() - start.getTime()) / 86400000;
  const startIso = localDate(start);
  const endIso = localDate(end);
  const canSchedule = account.permissions.includes("create_tasks") || account.role === "admin";
  const dependencies = timelineDependencies(tasks);
  const dependencyKey = JSON.stringify(dependencies);
  const taskLayoutKey = tasks.map((task) => `${task.id}:${task.planned_start ?? ""}:${task.due ?? ""}`).join("|");
  useLayoutEffect(() => {
    const root = timelineRef.current;
    const currentDependencies: TimelineDependency[] = JSON.parse(dependencyKey);
    if (!root || !currentDependencies.length) { setDependencyPaths([]); return; }
    const measure = () => {
      const rootRect = root.getBoundingClientRect();
      const paths = currentDependencies.flatMap((link) => {
        const from = root.querySelector<HTMLElement>(`[data-timeline-bar-id="${link.fromTaskId}"]`);
        const to = root.querySelector<HTMLElement>(`[data-timeline-bar-id="${link.toTaskId}"]`);
        if (!from || !to) return [];
        const fromRect = from.getBoundingClientRect();
        const toRect = to.getBoundingClientRect();
        const fromBeforeTo = fromRect.left <= toRect.left;
        const startX = (fromBeforeTo ? fromRect.right : fromRect.left) - rootRect.left + root.scrollLeft;
        const endX = (fromBeforeTo ? toRect.left : toRect.right) - rootRect.left + root.scrollLeft;
        const startY = fromRect.top - rootRect.top + root.scrollTop + fromRect.height / 2;
        const endY = toRect.top - rootRect.top + root.scrollTop + toRect.height / 2;
        const curve = Math.max(24, Math.abs(endX - startX) * 0.4);
        const path = `M ${startX} ${startY} C ${startX + curve} ${startY}, ${endX - curve} ${endY}, ${endX} ${endY}`;
        return [{ id: link.id, type: link.type, path, label: `OS-${link.fromTaskId} ${link.type === "blocks" ? "bloqueia" : link.type === "duplicates" ? "duplica" : "relaciona-se com"} OS-${link.toTaskId}` }];
      });
      setDependencyPaths(paths);
    };
    let frame = 0;
    const cancelMeasure = () => {
      if (typeof window.cancelAnimationFrame === "function") window.cancelAnimationFrame(frame);
      else window.clearTimeout(frame);
    };
    const scheduleMeasure = () => {
      cancelMeasure();
      frame = typeof window.requestAnimationFrame === "function"
        ? window.requestAnimationFrame(measure)
        : window.setTimeout(measure, 0);
    };
    scheduleMeasure();
    root.addEventListener("scroll", scheduleMeasure, { passive: true });
    window.addEventListener("resize", scheduleMeasure);
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(scheduleMeasure);
    observer?.observe(root);
    return () => {
      cancelMeasure();
      root.removeEventListener("scroll", scheduleMeasure);
      window.removeEventListener("resize", scheduleMeasure);
      observer?.disconnect();
    };
  }, [dependencyKey, taskLayoutKey, zoom, dragPreview]);
  return <div ref={timelineRef} className="timeline-view">
    <div className="timeline-header"><strong>Atividade</strong><div><CalendarRange size={16} /> {start.toLocaleDateString("pt-BR")} — {end.toLocaleDateString("pt-BR")} · {zoom === "month" ? "Mês" : zoom === "quarter" ? "Trimestre" : "Ano"}</div></div>
    {tasks.map((task) => {
      const planned = task.planned_start ?? task.created_at?.slice(0, 10) ?? startIso;
      const due = task.due ?? planned;
      const daysFromStart = (parseLocalDate(planned).getTime() - start.getTime()) / 86400000;
      const duration = Math.max(1, (parseLocalDate(due).getTime() - parseLocalDate(planned).getTime()) / 86400000 + 1);
      const left = Math.max(0, Math.min(100, (daysFromStart / days) * 100));
      const width = Math.max(1.4, Math.min(100 - left, (duration / days) * 100));
      const shifted = dragPreview?.taskId === task.id ? (dragPreview.deltaDays / days) * 100 : 0;
      const shiftDate = (value: string, offset: number) => { const date = parseLocalDate(value); date.setDate(date.getDate() + offset); return localDate(date); };
      return <div className="timeline-row" key={task.id}>
        <div className="timeline-label"><button className="link" onClick={() => open(task)}>OS-{task.id} · {task.title}</button><small>{suppliers.find((row) => row.id === task.supplier_id)?.name ?? "Não atribuído"} · {columns.find((column) => column.key === task.status)?.title ?? task.status_title ?? task.status}</small>
          <div className="timeline-dates"><label>Início<input type="date" disabled={!canSchedule} value={task.planned_start ?? ""} onChange={(event) => saveSchedule(task, event.target.value, task.due ?? "")} /></label><label>Prazo<input type="date" disabled={!canSchedule} value={task.due ?? ""} onChange={(event) => saveSchedule(task, task.planned_start ?? "", event.target.value)} /></label></div>
        </div>
        <div className="timeline-track" aria-label={`Período planejado de ${task.title}`}>
          {sprints.flatMap((sprint) => [[sprint.starts, `${sprint.name} · início`], [sprint.ends, `${sprint.name} · término`]] as [string, string][]).filter(([date]) => date >= startIso && date <= endIso).map(([date, label]) => <span key={`${task.id}-${label}`} className="timeline-marker" style={{ left: `${((parseLocalDate(date).getTime() - start.getTime()) / 86400000 / days) * 100}%` }} title={`${label}: ${date}`} />)}
          <div data-timeline-bar-id={task.id} className={task.status === "done" ? "timeline-bar done" : "timeline-bar"} style={{ left: `${left + shifted}%`, width: `${width}%` }} title={`${planned} até ${due}`} onPointerDown={(event) => {
            if (!canSchedule || task.status === "done") return;
            const track = event.currentTarget.parentElement;
            if (!track) return;
            const bounds = track.getBoundingClientRect();
            dragRef.current = { taskId: task.id, startX: event.clientX, trackWidth: bounds.width, deltaDays: 0 };
            event.currentTarget.setPointerCapture(event.pointerId);
            event.preventDefault();
          }} onPointerMove={(event) => {
            const drag = dragRef.current;
            if (!drag || drag.taskId !== task.id || drag.trackWidth <= 0) return;
            drag.deltaDays = Math.round(((event.clientX - drag.startX) / drag.trackWidth) * days);
            setDragPreview({ taskId: task.id, deltaDays: drag.deltaDays });
          }} onPointerUp={() => {
            const drag = dragRef.current;
            if (!drag || drag.taskId !== task.id) return;
            dragRef.current = null; setDragPreview(null);
            if (drag.deltaDays) saveSchedule(task, shiftDate(task.planned_start ?? task.created_at?.slice(0, 10) ?? startIso, drag.deltaDays), task.due ? shiftDate(task.due, drag.deltaDays) : "");
          }} onPointerCancel={() => { dragRef.current = null; setDragPreview(null); }} />
        </div>
      </div>;
    })}
    {dependencyPaths.length > 0 && <svg className="timeline-dependency-overlay" aria-label="Dependências entre cards" width={timelineRef.current?.scrollWidth ?? 0} height={timelineRef.current?.scrollHeight ?? 0} viewBox={`0 0 ${timelineRef.current?.scrollWidth ?? 1} ${timelineRef.current?.scrollHeight ?? 1}`}>
      <defs><marker id="timeline-blocks-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M 0 0 L 8 4 L 0 8 z" /></marker><marker id="timeline-duplicates-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M 0 0 L 8 4 L 0 8 z" /></marker></defs>
      {dependencyPaths.map((edge) => <path key={edge.id} className={`timeline-dependency ${edge.type}`} d={edge.path} markerEnd={edge.type === "blocks" ? "url(#timeline-blocks-arrow)" : edge.type === "duplicates" ? "url(#timeline-duplicates-arrow)" : undefined}><title>{edge.label}</title></path>)}
    </svg>}
    {!tasks.length && <p className="empty">Nenhum card corresponde aos filtros.</p>}
  </div>;
}

export function CalendarView({ tasks, open, canSchedule = false, saveSchedule, onExportCalendar, calendarFeedActive, calendarFeedLoading = false, calendarFeedUrl, calendarFeedSecret, onCreateCalendarFeed, onRevokeCalendarFeed, onCopyCalendarFeedUrl, onCopyCalendarFeedSecret }: {
  tasks: Task[];
  open: (task: Task) => void;
  canSchedule?: boolean;
  saveSchedule?: (task: Task, plannedStart: string, due: string) => void;
  onExportCalendar?: () => void;
  calendarFeedActive?: boolean;
  calendarFeedLoading?: boolean;
  calendarFeedUrl?: string;
  calendarFeedSecret?: string;
  onCreateCalendarFeed?: () => void;
  onRevokeCalendarFeed?: () => void;
  onCopyCalendarFeedUrl?: () => void;
  onCopyCalendarFeedSecret?: () => void;
}) {
  const [month, setMonth] = useState(() => {
    const value = new Date();
    return new Date(value.getFullYear(), value.getMonth(), 1);
  });
  const firstDay = new Date(month.getFullYear(), month.getMonth(), 1);
  const mondayOffset = (firstDay.getDay() + 6) % 7;
  const start = new Date(firstDay);
  start.setDate(firstDay.getDate() - mondayOffset);
  const days = Array.from({ length: 42 }, (_, index) => {
    const value = new Date(start);
    value.setDate(start.getDate() + index);
    return value;
  });
  const byDate = new Map<string, Task[]>();
  for (const task of tasks) {
    if (!task.due) continue;
    byDate.set(task.due.slice(0, 10), [...(byDate.get(task.due.slice(0, 10)) ?? []), task]);
  }
  const label = new Intl.DateTimeFormat("pt-BR", { month: "long", year: "numeric" }).format(month);
  const dropTask = (event: DragEvent<HTMLDivElement>, date: string) => {
    event.preventDefault();
    if (!canSchedule || !saveSchedule) return;
    const identity = Number(event.dataTransfer.getData("text/plain"));
    const task = tasks.find((row) => row.id === identity);
    if (!task || task.status === "done") return;
    const startDate = task.planned_start && task.planned_start <= date ? task.planned_start : task.planned_start ? date : "";
    if (task.due !== date || task.planned_start !== startDate) saveSchedule(task, startDate, date);
  };
  return <section className="project-calendar" aria-label={`Calendário de ${label}`}>
    <div className="calendar-toolbar">
      <h3>{label}</h3>
      <div><button onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}>Anterior</button><button onClick={() => { const now = new Date(); setMonth(new Date(now.getFullYear(), now.getMonth(), 1)); }}>Hoje</button><button onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}>Próximo</button>{onExportCalendar && <button type="button" onClick={onExportCalendar}><Download size={15} /> Exportar .ics</button>}</div>
    </div>
    {onCreateCalendarFeed && <section className="calendar-feed panel" aria-label="Assinatura de calendário">
      <div><strong>Sincronizar com outro calendário</strong><p className="muted">Use uma assinatura iCalendar somente leitura. Os eventos são atualizados conforme seus cards com prazo mudam.</p></div>
      <div className="calendar-feed-actions">
        <button type="button" disabled={calendarFeedLoading} onClick={onCreateCalendarFeed}><KeyRound size={15} />{calendarFeedLoading ? "Verificando feed…" : calendarFeedActive ? "Gerar nova chave" : "Criar assinatura"}</button>
        {calendarFeedActive && onRevokeCalendarFeed && <button type="button" className="danger" onClick={onRevokeCalendarFeed}>Revogar assinatura</button>}
      </div>
      {calendarFeedActive && <p className="calendar-feed-help">Feed ativo. O endereço não contém a chave; informe o usuário <code>calendar</code> e a chave como senha nas configurações do calendário. Se perdeu a chave, gere outra para substituir a anterior.</p>}
      {calendarFeedSecret && <div className="calendar-feed-credentials">
        <label>Endereço do feed<input readOnly value={calendarFeedUrl ?? ""} /></label>
        <button type="button" onClick={onCopyCalendarFeedUrl}><Copy size={14} />Copiar endereço</button>
        <label>Chave de acesso — exibida somente agora<input readOnly value={calendarFeedSecret} /></label>
        <button type="button" onClick={onCopyCalendarFeedSecret}><Copy size={14} />Copiar chave</button>
        <small>Guarde a chave como uma senha. Ela não pode ser recuperada; você pode gerar uma nova a qualquer momento.</small>
      </div>}
    </section>}
    {canSchedule && <p className="muted">Arraste um card para outro dia para ajustar o prazo. Pelo teclado, abra o card e edite o cronograma.</p>}
    <div className="calendar-content">
    <div className="calendar-grid">
      {["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"].map((day) => <strong key={day}>{day}</strong>)}
      {days.map((day) => {
        const key = localDate(day);
        return <div className={day.getMonth() === month.getMonth() ? "calendar-day" : "calendar-day outside"} key={key} data-date={key} aria-label={canSchedule ? `Soltar card no dia ${key}` : undefined} onDragOver={canSchedule ? (event) => { event.preventDefault(); event.dataTransfer.dropEffect = "move"; } : undefined} onDrop={canSchedule ? (event) => dropTask(event, key) : undefined}>
          <time dateTime={key}>{day.getDate()}</time>
          {(byDate.get(key) ?? []).map((task) => <button className="calendar-task" key={task.id} title={task.title} draggable={canSchedule && task.status !== "done"} onDragStart={(event) => { event.dataTransfer.effectAllowed = "move"; event.dataTransfer.setData("text/plain", String(task.id)); }} onClick={() => open(task)}>OS-{task.id} · {task.title}</button>)}
        </div>;
      })}
    </div>
    {canSchedule && <aside className="calendar-unplanned" aria-label="Cards sem prazo">
      <h4>Sem prazo</h4>
      <p className="muted">Arraste um card para o dia desejado.</p>
      {tasks.filter((task) => !task.due).map((task) => <button key={task.id} className="calendar-task" title={task.title} draggable={task.status !== "done"} onDragStart={(event) => { event.dataTransfer.effectAllowed = "move"; event.dataTransfer.setData("text/plain", String(task.id)); }} onClick={() => open(task)}>OS-{task.id} · {task.title}</button>)}
      {!tasks.some((task) => !task.due) && <small className="muted">Nenhum card sem prazo.</small>}
    </aside>}
    </div>
    {!tasks.some((task) => task.due?.slice(0, 7) === localDate(month).slice(0, 7)) && <p className="calendar-empty">Nenhum card com prazo neste mês.</p>}
  </section>;
}
