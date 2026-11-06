import { useRef, useState } from "react";
import { ArrowLeft, ArrowRight, CalendarRange, Copy, Eye, Pencil, Plus, Save, Trash2 } from "lucide-react";
import type { Account, Sprint, Task } from "./types";

export type ViewLayout = "board" | "table" | "timeline";
export type SavedProjectView = {
  id: number;
  name: string;
  layout: ViewLayout;
  config: Record<string, any>;
  position: number;
};
export type ProjectColumn = {
  key: string;
  title: string;
  is_system: boolean;
  view_order: number;
};

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
  views, activeId, layout, query, groupBy, sortBy, zoom, fields, visibleFields, sliceBy, sliceValue, sliceOptions, sumBy, descending, financial,
  onSelect, onLayout, onQuery, onGroup, onSort, onZoom, onToggleField, onMoveField, onSliceBy, onSliceValue, onSum, onDirection, onRename, onMoveView,
  onSave, onDuplicate, onDelete,
}: {
  views: SavedProjectView[]; activeId: number | null; layout: ViewLayout; query: string;
  groupBy: string; sortBy: string; zoom: "month" | "quarter" | "year";
  sliceBy: string; sliceValue: string; sliceOptions: { value: string; label: string }[]; sumBy: string; descending: boolean; financial: boolean;
  fields: { key: string; label: string }[]; visibleFields: string[];
  onMoveField: (key: string, direction: number) => void;
  onSelect: (view: SavedProjectView | null) => void; onLayout: (value: ViewLayout) => void;
  onQuery: (value: string) => void; onGroup: (value: string) => void; onSort: (value: string) => void;
  onZoom: (value: "month" | "quarter" | "year") => void; onToggleField: (value: string) => void;
  onSliceBy: (value: string) => void; onSliceValue: (value: string) => void; onSum: (value: string) => void; onDirection: () => void;
  onRename: () => void; onMoveView: (identity: number, direction: number) => void;
  onSave: (name?: string) => void; onDuplicate: () => void; onDelete: () => void;
}) {
  const [open, setOpen] = useState(true);
  const [newName, setNewName] = useState("");
  return (
    <section className="project-view-tools" aria-label="Visualizações e filtros">
      <div className="project-view-heading">
        <button className="project-view-toggle" onClick={() => setOpen(!open)} aria-expanded={open}>
          <Eye size={18} aria-hidden="true" /> Views <span>{open ? "−" : "+"}</span>
        </button>
        {views.map((view, index) => (
          <div className="view-tab-wrap" key={view.id}>
            <button className={activeId === view.id ? "view-tab active" : "view-tab"} onClick={() => onSelect(view)}>{view.name}</button>
            <button className="view-tab-move" aria-label={`Mover visualização ${view.name} para a esquerda`} disabled={index === 0} onClick={() => onMoveView(view.id, -1)}><ArrowLeft size={13} /></button>
            <button className="view-tab-move" aria-label={`Mover visualização ${view.name} para a direita`} disabled={index === views.length - 1} onClick={() => onMoveView(view.id, 1)}><ArrowRight size={13} /></button>
          </div>
        ))}
        {activeId !== null && <button className="view-tab" onClick={() => onSelect(null)}>+ Quadro padrão</button>}
      </div>
      {open && <>
        <div className="project-view-controls">
          <label>Visualização
            <select value={layout} onChange={(event) => onLayout(event.target.value as ViewLayout)}>
              <option value="board">Quadro</option><option value="table">Tabela</option><option value="timeline">Linha do tempo</option>
            </select>
          </label>
          <label className="project-filter-search">Filtros
            <input value={query} onChange={(event) => onQuery(event.target.value)} placeholder={'Ex.: status:"Em produção" supplier:3 no:due'} />
          </label>
          <label>Agrupar por
            <select value={groupBy} onChange={(event) => onGroup(event.target.value)}>
              <option value="">Sem agrupamento</option><option value="status">Status</option><option value="supplier">Fornecedor</option><option value="sprint">Sprint</option><option value="priority">Prioridade</option><option value="approval">Aprovação</option>
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
        <p className="project-filter-help">Filtros: texto livre, status, supplier, sprint, priority, label, approval, due, created, has/no e field.ID. Use vírgulas para opções alternativas e “-” para excluir. Ex.: <code>status:review,-label:urgente,due:2026-11-01..2026-12-31</code></p>
        <div className="project-view-save">
          <label aria-label="Nome da visualização"><input value={newName} onChange={(event) => setNewName(event.target.value)} placeholder="Nome da nova visualização" /></label>
          <button onClick={() => { onSave(newName.trim() || undefined); setNewName(""); }}><Plus size={15} /> Salvar como nova</button>
          {activeId !== null && <><button onClick={() => onSave()}><Save size={15} /> Salvar alterações</button><button onClick={onRename}><Pencil size={15} /> Renomear</button><button onClick={onDuplicate}><Copy size={15} /> Duplicar</button><button className="danger" onClick={onDelete}><Trash2 size={15} /> Excluir</button></>}
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
  const dragRef = useRef<{ taskId: number; startX: number; trackWidth: number; deltaDays: number } | null>(null);
  const [dragPreview, setDragPreview] = useState<{ taskId: number; deltaDays: number } | null>(null);
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
  return <div className="timeline-view">
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
          <div className={task.status === "done" ? "timeline-bar done" : "timeline-bar"} style={{ left: `${left + shifted}%`, width: `${width}%` }} title={`${planned} até ${due}`} onPointerDown={(event) => {
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
    {!tasks.length && <p className="empty">Nenhum card corresponde aos filtros.</p>}
  </div>;
}
