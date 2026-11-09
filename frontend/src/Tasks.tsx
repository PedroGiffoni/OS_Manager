import { HistoryTimeline } from "./HistoryTimeline";
import { hourInput } from "./types";
import { ArrowLeft, ArrowRight, Eye, EyeOff, GripVertical, Plus, Trash2, X } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  DndContext,
  DragOverlay,
  pointerWithin,
  closestCorners,
  useDroppable,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragEndEvent,
} from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import {
  useSortable,
  SortableContext,
  arrayMove,
  verticalListSortingStrategy,
  sortableKeyboardCoordinates,
} from "@dnd-kit/sortable";
import { api, downloadPost } from "./api";
import {
  stages,
  approvals,
  money,
  decimalToUnits,
  type Account,
  type Task,
  type TaskLabel,
  type Supplier,
  type Sprint,
  type DevelopmentEvent,
} from "./types";
import { Label, Empty, type Run } from "./App";
import { FieldBuilder, FieldValueForm } from "./Fields";
import { Collaboration } from "./Collaboration";
import { CalendarView, ProjectTable, QuickFilters, TimelineView, ViewTools, boardQuickFilters, filterBoardTasks, isQuickFilterQueryAllowed, type BoardQuickFilter, type ProjectColumn, type SavedProjectView, type ViewLayout } from "./ProjectViews";
export function TaskList({
  query,
  suppliers,
  canCreate,
  run,
  open,
}: {
  query: string;
  suppliers: Supplier[];
  canCreate: boolean;
  run: Run;
  open: (task: Task) => void;
}) {
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [advanced, setAdvanced] = useState(false);
  const [jql, setJql] = useState("");
  const [creating, setCreating] = useState(false);
  const rows = useQuery({
    queryKey: ["tasks", query, page, search, jql],
    queryFn: () =>
      api<Task[]>(
        `/tasks?${query}&q=${encodeURIComponent(search)}&jql=${encodeURIComponent(jql)}&offset=${page * 25}&limit=25`,
      ),
  });
  return (
    <section className="panel">
      <div className="section-title">
        <h2>Atividades</h2>
        {canCreate && (
          <button className="primary" onClick={() => setCreating(!creating)}>
            + Nova atividade
          </button>
        )}
      </div>
      {creating && (
        <TaskForm
          suppliers={suppliers}
          submit={(values) =>
            run(async () => {
              await api("/tasks", "POST", values);
              setCreating(false);
            })
          }
        />
      )}
      <Label title="Buscar atividades">
        <input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(0);
          }}
          placeholder="Buscar por título…"
        />
      </Label>
      <button className="link" aria-expanded={advanced} onClick={() => setAdvanced((value) => !value)}>
        {advanced ? "Ocultar busca avançada" : "Busca avançada"}
      </button>
      {advanced && <Label title="Consulta avançada">
        <input value={jql} onChange={(event) => { setJql(event.target.value); setPage(0); }} placeholder={'status = "review" OR (type = bug AND priority <= 5) ORDER BY due ASC'} />
      </Label>}
      {advanced && <small>Consulta segura no servidor: AND/OR, comparações, IN/NOT IN, IS EMPTY, ORDER BY, <code>statusCategory</code> (To Do/In Progress/Done), pai, responsável, sprint, release/componente por ID ou nome exato (<code>fixVersion</code> é alias de release). O histórico CHANGED/WAS aceita campos estruturais e valores de campos personalizados no formato field_ID, com autor e período. Ex.: field_area CHANGED FROM "Operações" TO "Produtos" BY pedro AFTER "2026-11-01".</small>}
      {rows.isPending ? (
        <Empty>Carregando atividades…</Empty>
      ) : rows.isError ? (
        <Empty>{rows.error.message}</Empty>
      ) : (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Atividade</th>
                  <th>Etapa</th>
                  <th>Fornecedor</th>
                  <th>Previstas / utilizadas</th>
                  <th>Aprovação</th>
                </tr>
              </thead>
              <tbody>
                {rows.data.map((task) => (
                  <tr key={task.id}>
                    <td>
                      <button className="link" onClick={() => open(task)}>
                        #{task.id} · {task.title}
                      </button>
                      <small>
                        {task.due
                          ? "Prazo " +
                            new Date(task.due + "T12:00:00").toLocaleDateString(
                              "pt-BR",
                            )
                          : "Sem prazo definido"}
                      </small>
                    </td>
                    <td>
                      <span className={"badge " + task.status}>
                        {stages[task.status] ?? task.status_title ?? task.status}
                      </span>
                    </td>
                    <td>
                      {suppliers.find((row) => row.id === task.supplier_id)
                        ?.name ?? "Não atribuído"}
                    </td>
                    <td>
                      {task.fields.some(
                        (field) => field.native_key === "estimated_minutes",
                      )
                        ? `${task.estimated_minutes / 60}h / `
                        : "— / "}
                      {task.used_minutes / 60}h
                    </td>
                    <td>{approvals[task.approval]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!rows.data.length && <Empty>Nenhuma atividade encontrada.</Empty>}
          <div className="actions">
            <button disabled={!page} onClick={() => setPage(page - 1)}>
              Anterior
            </button>
            <span>Página {page + 1}</span>
            <button
              disabled={rows.data.length < 25}
              onClick={() => setPage(page + 1)}
            >
              Próxima
            </button>
          </div>
        </>
      )}
    </section>
  );
}
const taskSchema = z.object({
  title: z.string().min(1, "Informe o título.").max(240),
  description: z.string().max(10000),
  supplier_id: z.string(),
  assignee_user_id: z.string(),
  due: z.string(),
  priority: z.coerce.number().int(),
  work_type: z.enum(["epic", "story", "task", "bug", "subtask"]),
  parent_id: z.string(),
});
function TaskForm({
  suppliers,
  task,
  submit,
}: {
  suppliers: Supplier[];
  task?: Task;
  submit: (values: any) => Promise<void>;
}) {
  const [estimatePolicy, setEstimatePolicy] = useState("absent");
  const [labels, setLabels] = useState<TaskLabel[]>(task?.labels ?? []);
  const parents = useQuery({ queryKey: ["task-parent-options"], queryFn: () => api<Task[]>("/tasks?limit=200") });
  const assignees = useQuery({ queryKey: ["task-assignees"], queryFn: () => api<{ id: number; username: string; role: string }[]>("/directory/assignees") });
  useEffect(() => setLabels(task?.labels ?? []), [task?.id, task?.version]);
  const {
    register,
    watch,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof taskSchema>>({
    resolver: zodResolver(taskSchema),
    defaultValues: {
      title: task?.title ?? "",
      description: task?.description ?? "",
      supplier_id: task?.supplier_id?.toString() ?? "",
      assignee_user_id: task?.assignee_user_id?.toString() ?? "",
      due: task?.due ?? "",
      priority: task?.priority ?? 0,
      work_type: task?.work_type ?? "task",
      parent_id: task?.parent_id?.toString() ?? "",
    },
  });
  const selectedWorkType = watch("work_type");
  const eligibleParentType = (type: Task["work_type"]) => selectedWorkType === "subtask"
    ? ["story", "task", "bug"].includes(type ?? "task")
    : type === "epic";
  return (
    <form
      className="inline-form"
      onSubmit={handleSubmit((values) =>
        submit({
          ...values,
          supplier_id: values.supplier_id ? Number(values.supplier_id) : null,
          assignee_user_id: values.assignee_user_id ? Number(values.assignee_user_id) : null,
          due: values.due || null,
          parent_id: values.parent_id ? Number(values.parent_id) : null,
          labels,
          ...(task
            ? { version: task.version }
            : { estimate_policy: estimatePolicy }),
        }),
      )}
    >
      <Label title="Título">
        <input {...register("title")} />
      </Label>
      {errors.title && <small role="alert">{errors.title.message}</small>}
      {!task && (
        <Label title="Horas previstas no card">
          <select
            value={estimatePolicy}
            onChange={(event) => setEstimatePolicy(event.target.value)}
          >
            <option value="absent">Não incluir</option>
            <option value="optional">Incluir · resposta opcional</option>
            <option value="required">
              Incluir · obrigatório antes de Em produção
            </option>
          </select>
        </Label>
      )}
      <Label title="Descrição">
        <textarea {...register("description")} />
      </Label>
      <fieldset className="label-builder">
        <legend>Etiquetas do card</legend>
        {labels.map((label, index) => (
          <div className="label-editor-row" key={index}>
            <Label title={`Texto da etiqueta ${index + 1}`}>
              <input
                maxLength={40}
                value={label.text}
                onChange={(event) =>
                  setLabels((current) =>
                    current.map((item, itemIndex) =>
                      itemIndex === index
                        ? { ...item, text: event.target.value }
                        : item,
                    ),
                  )
                }
              />
            </Label>
            <Label title="Cor da etiqueta">
              <input
                type="color"
                value={label.color}
                onChange={(event) =>
                  setLabels((current) =>
                    current.map((item, itemIndex) =>
                      itemIndex === index
                        ? { ...item, color: event.target.value }
                        : item,
                    ),
                  )
                }
              />
            </Label>
            <button
              type="button"
              className="label-remove"
              aria-label={`Remover etiqueta ${label.text || index + 1}`}
              onClick={() =>
                setLabels((current) => current.filter((_, i) => i !== index))
              }
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
        ))}
        <button
          type="button"
          className="label-add"
          disabled={labels.length >= 8}
          onClick={() =>
            setLabels((current) => [
              ...current,
              { text: "", color: "#2B4EDA" },
            ])
          }
        >
          + Adicionar etiqueta
        </button>
        <small>Até 8 etiquetas por card. Escolha o texto e a cor.</small>
      </fieldset>
      <div className="form-grid">
        <Label title="Tipo de trabalho">
          <select {...register("work_type")}>
            <option value="epic">Épico</option><option value="story">História</option><option value="task">Tarefa</option><option value="bug">Bug</option><option value="subtask">Subtarefa</option>
          </select>
        </Label>
        <Label title="Card pai">
          <select {...register("parent_id")}>
            <option value="">Sem card pai</option>
            {parents.data?.filter((row) => row.id !== task?.id && (eligibleParentType(row.work_type) || row.id === task?.parent_id)).map((row) => <option value={row.id} key={row.id}>OS-{row.id} · {row.title}{eligibleParentType(row.work_type) ? "" : " · vínculo existente"}</option>)}
          </select>
        </Label>
        <Label title="Fornecedor responsável">
          <select {...register("supplier_id")}>
            <option value="">Não atribuído</option>
            {suppliers
              .filter((row) => row.active || row.id === task?.supplier_id)
              .map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
          </select>
        </Label>
        <Label title="Responsável interno (opcional)">
          <select {...register("assignee_user_id")}>
            <option value="">Não atribuído</option>
            {assignees.data?.map((row) => (
              <option key={row.id} value={row.id}>
                {row.username} · {row.role}
              </option>
            ))}
          </select>
        </Label>
        <Label title="Prazo">
          <input type="date" {...register("due")} />
        </Label>
        <Label title="Prioridade (menor aparece primeiro)">
          <input type="number" {...register("priority")} />
        </Label>
      </div>
      <button
        className="primary"
        disabled={isSubmitting || labels.some((label) => !label.text.trim())}
      >
        Salvar atividade
      </button>
    </form>
  );
}
function tagForeground(color: string) {
  const safeColor = /^#[0-9a-f]{6}$/i.test(color) ? color : "#2B4EDA";
  const rgb = [1, 3, 5].map((offset) =>
    parseInt(safeColor.slice(offset, offset + 2), 16) / 255,
  );
  const channels = rgb.map((channel) =>
    channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4,
  );
  const luminance =
    0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
  return { backgroundColor: safeColor, color: luminance > 0.42 ? "#14213D" : "#FFFFFF" };
}

function TaskLabels({ labels }: { labels?: TaskLabel[] }) {
  if (!labels?.length) return null;
  return (
    <div className="task-labels" aria-label="Etiquetas do card">
      {labels.map((label, index) => (
        <span key={index} style={tagForeground(label.color)}>
          {label.text}
        </span>
      ))}
    </div>
  );
}

function DraggableTask({
  task,
  suppliers,
  open,
}: {
  task: Task;
  suppliers: Supplier[];
  open: (task: Task) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useSortable({
    id: task.id,
  });
  return (
    <article
      ref={setNodeRef}
      className={"kanban-card" + (isDragging ? " kanban-card-source-dragging" : "")}
      style={{ transform: CSS.Translate.toString(transform) }}
    >
      <div className="card-top">
        <small>OS-{task.id}</small>
        <button
          {...listeners}
          {...attributes}
          aria-label={"Arrastar " + task.title}
        >
          <GripVertical size={18} aria-hidden="true" />
        </button>
      </div>
      <button className="card-title" onClick={() => open(task)}>
        {task.title}
      </button>
      <small className="card-supplier">
        Fornecedor responsável: {suppliers.find((row) => row.id === task.supplier_id)?.name ?? "Não atribuído"}
      </small>
      <TaskLabels labels={task.labels} />
      <p>{task.description.slice(0, 95)}</p>
      <div>
        {task.fields.some(
          (field) => field.native_key === "estimated_minutes",
        ) && (
          <span className="badge">
            {task.estimated_minutes / 60}h previstas
          </span>
        )}
        {task.approval === "rejected" && (
          <span className="rejection">Corrigir horas</span>
        )}
      </div>
      <small>{task.due ? "Prazo " + task.due : "Sem prazo"}</small>
    </article>
  );
}
function Column({
  status,
  title,
  category,
  wipLimit,
  children,
  count,
  summary,
  canManage,
  isFirst,
  isLast,
  onRename,
  onCategory,
  onWipLimit,
  onDelete,
  onMove,
  onDragStart,
  onDrop,
  editing,
  onEdit,
}: {
  status: string;
  title: string;
  category: "todo" | "in_progress" | "done";
  wipLimit?: number | null;
  children: React.ReactNode;
  count: number;
  summary: string;
  canManage: boolean;
  isFirst: boolean;
  isLast: boolean;
  onRename: (title: string) => void;
  onCategory: (category: "todo" | "in_progress") => void;
  onWipLimit: (limit: number | null) => void;
  onDelete: () => void;
  onMove: (delta: number) => void;
  onDragStart: () => void;
  onDrop: () => void;
  editing: boolean;
  onEdit: () => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  const [draft, setDraft] = useState(title);
  const [wipDraft, setWipDraft] = useState(wipLimit?.toString() ?? "");
  useEffect(() => setDraft(title), [title]);
  useEffect(() => setWipDraft(wipLimit?.toString() ?? ""), [wipLimit]);
  const commitWip = () => {
    const normalized = wipDraft.trim();
    if (!normalized) { if (wipLimit != null) onWipLimit(null); return; }
    const value = Number(normalized);
    if (Number.isInteger(value) && value >= 1 && value <= 10000 && value !== wipLimit) onWipLimit(value);
    else setWipDraft(wipLimit?.toString() ?? "");
  };
  return (
    <section
      ref={setNodeRef}
      className={"kanban-column " + (isOver ? "over" : "")}
    >
      <header className="kanban-column-header" draggable={canManage} onDragStart={(event) => { event.dataTransfer.effectAllowed = "move"; event.dataTransfer.setData("text/plain", status); onDragStart(); }} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); onDrop(); }}>
        <div className="kanban-column-heading">
          <i className={status} />
          {editing ? <input aria-label="Título da coluna" autoFocus value={draft} onChange={(event) => setDraft(event.target.value)} onBlur={() => onRename(draft)} onKeyDown={(event) => { if (event.key === "Enter") event.currentTarget.blur(); if (event.key === "Escape") { setDraft(title); event.currentTarget.blur(); } }} /> : <h3><button className="kanban-column-title" onClick={() => canManage && onEdit()}>{title}</button></h3>}
          <span className={wipLimit && count > wipLimit ? "kanban-wip-count exceeded" : "kanban-wip-count"} aria-label={wipLimit ? `${count} cards visíveis; limite WIP ${wipLimit}` : `${count} cards visíveis`}>
            {count}{wipLimit ? ` / ${wipLimit}` : ""}
          </span>
        </div>
        {(canManage || summary) && <div className="kanban-column-controls">
          {canManage && <>
            <select className="kanban-column-category" aria-label={`Categoria da coluna ${title}`} value={category === "done" ? "done" : category} disabled={status === "done"} onChange={(event) => onCategory(event.target.value as "todo" | "in_progress")}>
              <option value="todo">A fazer</option><option value="in_progress">Em andamento</option>{status === "done" && <option value="done">Concluído</option>}
            </select>
            <div className="kanban-column-tools">
              <label className="kanban-wip-editor" title="Limite de trabalho em andamento (WIP)">
                WIP
                <input aria-label={`Limite WIP de ${title}`} type="number" min="1" max="10000" placeholder="—" value={wipDraft} onChange={(event) => setWipDraft(event.target.value)} onBlur={commitWip} onKeyDown={(event) => { if (event.key === "Enter") event.currentTarget.blur(); if (event.key === "Escape") setWipDraft(wipLimit?.toString() ?? ""); }} />
              </label>
              <button aria-label={`Mover ${title} para a esquerda`} disabled={isFirst} onClick={() => onMove(-1)}><ArrowLeft size={14} aria-hidden="true" /></button>
              <button aria-label={`Mover ${title} para a direita`} disabled={isLast} onClick={() => onMove(1)}><ArrowRight size={14} aria-hidden="true" /></button>
              {status.startsWith("custom_") && <><button aria-label={`Editar ${title}`} onClick={onEdit}>✎</button><button aria-label={`Excluir ${title}`} onClick={onDelete}><Trash2 size={13} aria-hidden="true" /></button></>}
            </div>
          </>}
          {summary && <small className="kanban-column-sum">{summary}</small>}
        </div>}
      </header>
      {children}
    </section>
  );
}
export function Board({
  query,
  suppliers = [],
  sprints = [],
  account,
  run,
  open,
}: {
  query: string;
  suppliers?: Supplier[];
  sprints?: Sprint[];
  account: Account;
  run: Run;
  open: (task: Task) => void;
}) {
  const [advancedQuery, setAdvancedQuery] = useState("");
  const [appliedAdvancedQuery, setAppliedAdvancedQuery] = useState("");
  useEffect(() => {
    const timer = window.setTimeout(() => setAppliedAdvancedQuery(advancedQuery), 300);
    return () => window.clearTimeout(timer);
  }, [advancedQuery]);
  const rows = useQuery({
    queryKey: ["board", query, appliedAdvancedQuery],
    queryFn: async () => {
      const all: Task[] = [];
      let offset = 0;
      while (true) {
        const params = new URLSearchParams(query);
        params.set("limit", "200");
        params.set("offset", String(offset));
        if (appliedAdvancedQuery.trim()) params.set("jql", appliedAdvancedQuery.trim());
        else params.delete("jql");
        const page = await api<Task[]>(`/tasks?${params.toString()}`);
        all.push(...page);
        if (page.length < 200) return all;
        offset += page.length;
      }
    },
  });
  const columnQuery = useQuery({ queryKey: ["board-columns"], queryFn: () => api<ProjectColumn[]>("/board/columns") });
  const viewQuery = useQuery({ queryKey: ["board-views"], queryFn: () => api<SavedProjectView[]>("/board/views") });
  const shareGroups = useQuery({ queryKey: ["share-groups"], queryFn: () => api<{ id: number; name: string }[]>("/directory/groups"), enabled: account.permissions.includes("manage_planning") });
  const defaults: ProjectColumn[] = Object.entries(stages).map(([key, title], view_order) => ({ key, title, is_system: true, category: key === "done" ? "done" : key === "backlog" || key === "todo" ? "todo" : "in_progress", view_order }));
  const columns = [...(columnQuery.data?.length ? columnQuery.data : defaults)].sort((a, b) => a.view_order - b.view_order);
  const [activeViewId, setActiveViewId] = useState<number | null>(null);
  const [layout, setLayout] = useState<ViewLayout>("board");
  const [calendarFeedSecret, setCalendarFeedSecret] = useState("");
  const calendarFeed = useQuery({
    queryKey: ["calendar-feed"],
    queryFn: () => api<{ enabled: boolean; created_at: string | null }>("/me/calendar-feed"),
    enabled: layout === "calendar",
  });
  const calendarFeedUrl = `${window.location.origin}/api/v1/calendar/feed.ics`;
  const createCalendarFeed = () => run(async () => {
    if (calendarFeed.data?.enabled && !window.confirm("Gerar uma nova chave invalida o endereço de assinatura atual. Continuar?")) return;
    const issued = await api<{ token: string }>("/me/calendar-feed", "POST", {});
    setCalendarFeedSecret(issued.token);
    await calendarFeed.refetch();
  });
  const revokeCalendarFeed = () => run(async () => {
    if (!window.confirm("Revogar o feed interrompe a sincronização em todos os calendários conectados. Continuar?")) return;
    await api("/me/calendar-feed", "DELETE");
    setCalendarFeedSecret("");
    await calendarFeed.refetch();
  });
  const [filterQuery, setFilterQuery] = useState("");
  const [quickFilterIds, setQuickFilterIds] = useState<string[]>([]);
  const [quickFilterDefinitions, setQuickFilterDefinitions] = useState<BoardQuickFilter[]>(boardQuickFilters);
  const [groupBy, setGroupBy] = useState("");
  const [sortBy, setSortBy] = useState("");
  const [zoom, setZoom] = useState<"month" | "quarter" | "year">("quarter");
  const [sliceBy, setSliceBy] = useState("");
  const [sliceValue, setSliceValue] = useState("");
  const [sumBy, setSumBy] = useState("");
  const [descending, setDescending] = useState(false);
  const [visibleFields, setVisibleFields] = useState<string[]>([]);
  const [sharedView, setSharedView] = useState(false);
  const [sharedRoles, setSharedRoles] = useState<string[]>([]);
  const [sharedGroupIds, setSharedGroupIds] = useState<number[]>([]);
  const [editingColumn, setEditingColumn] = useState<string | null>(null);
  const [draggedColumn, setDraggedColumn] = useState<string | null>(null);
  const canManage = account.role === "admin" || account.role === "manager";
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );
  const onDragEnd = (event: DragEndEvent) => {
    setActiveTask(null);
    const task = rows.data?.find((row) => row.id === event.active.id);
    if (!task || !event.over) return;
    const target = rows.data?.find((row) => row.id === event.over!.id);
    if (
      target &&
      target.status === task.status &&
      target.sprint_id === task.sprint_id
    ) {
      const column = rows.data!.filter(
        (row) => row.status === task.status && row.sprint_id === task.sprint_id,
      );
      const ordered = arrayMove(
        column,
        column.findIndex((row) => row.id === task.id),
        column.findIndex((row) => row.id === target.id),
      );
      run(() =>
        api(
          "/tasks/reorder",
          "POST",
          ordered.map((row) => ({ id: row.id, version: row.version })),
        ),
      );
    } else
      run(() =>
        api(`/tasks/${task.id}/move`, "POST", {
          version: task.version,
          status: target?.status ?? String(event.over!.id),
          priority: target?.priority ?? task.priority,
        }),
      );
  };
  const onDragStart = (event: DragStartEvent) => {
    setActiveTask(rows.data?.find((row) => row.id === event.active.id) ?? null);
  };
  const selectView = (view: SavedProjectView | null) => {
    setActiveViewId(view?.id ?? null);
    setSharedView(Boolean(view?.shared));
    setSharedRoles(view?.shared_roles ?? []);
    setSharedGroupIds(view?.shared_group_ids ?? []);
    const config = view?.config ?? {};
    setLayout(view?.layout ?? "board");
    setFilterQuery(String(config.query ?? ""));
    const definitions = Array.isArray(config.quickFilterDefinitions)
      ? config.quickFilterDefinitions.filter((filter: unknown): filter is BoardQuickFilter =>
          typeof filter === "object" && filter !== null &&
          typeof (filter as BoardQuickFilter).id === "string" &&
          (filter as BoardQuickFilter).id.length > 0 && (filter as BoardQuickFilter).id.length <= 80 &&
          typeof (filter as BoardQuickFilter).label === "string" &&
          (filter as BoardQuickFilter).label.trim().length > 0 && (filter as BoardQuickFilter).label.length <= 40 &&
          typeof (filter as BoardQuickFilter).query === "string" &&
          (filter as BoardQuickFilter).query.length <= 300 &&
          isQuickFilterQueryAllowed((filter as BoardQuickFilter).query),
        ).slice(0, 20)
      : boardQuickFilters;
    setQuickFilterDefinitions(definitions);
    setQuickFilterIds(Array.isArray(config.quickFilters) ? config.quickFilters.filter((id: unknown): id is string => typeof id === "string" && definitions.some((item) => item.id === id)) : []);
    setAdvancedQuery(String(config.jql ?? ""));
    setGroupBy(String(config.groupBy ?? ""));
    setSortBy(String(config.sortBy ?? ""));
    setZoom(config.zoom === "month" || config.zoom === "year" ? config.zoom : "quarter");
    setSliceBy(String(config.sliceBy ?? ""));
    setSliceValue(String(config.sliceValue ?? ""));
    setSumBy(config.sumBy === "cost_cents" && !(account.role !== "supplier" && account.permissions.includes("view_financial")) ? "" : String(config.sumBy ?? ""));
    setDescending(Boolean(config.descending));
    setVisibleFields(Array.isArray(config.visibleFields) ? config.visibleFields : []);
    if (!view) { setQuickFilterIds([]); setSliceBy(""); setSliceValue(""); setSumBy(""); setDescending(false); }
  };
  const viewConfig = () => ({ query: filterQuery, quickFilters: quickFilterIds, quickFilterDefinitions, jql: advancedQuery, groupBy, sortBy, zoom, visibleFields, sliceBy, sliceValue, sumBy, descending });
  const saveView = (name?: string) => run(async () => {
    if (!name && activeViewId === null) return;
    if (name) {
      const view = await api<SavedProjectView>("/board/views", "POST", { name, layout, config: viewConfig(), shared: sharedView, shared_roles: sharedRoles, shared_group_ids: sharedGroupIds, position: viewQuery.data?.length ?? 0 });
      setActiveViewId(view.id);
    } else {
      await api(`/board/views/${activeViewId}`, "PUT", { name: viewQuery.data?.find((view) => view.id === activeViewId)?.name ?? "Visualização", layout, config: viewConfig(), shared: sharedView, shared_roles: sharedRoles, shared_group_ids: sharedGroupIds, position: viewQuery.data?.find((view) => view.id === activeViewId)?.position ?? 0 });
    }
  });
  const duplicateView = () => run(async () => {
    const current = viewQuery.data?.find((view) => view.id === activeViewId);
    const name = window.prompt("Nome da cópia", current ? `${current.name} (cópia)` : "Nova visualização");
    if (!name?.trim()) return;
    const view = await api<SavedProjectView>("/board/views", "POST", { name: name.trim(), layout, config: viewConfig(), shared: false, shared_roles: [], shared_group_ids: [], position: viewQuery.data?.length ?? 0 });
    setActiveViewId(view.id);
  });
  const renameView = () => run(async () => {
    const current = viewQuery.data?.find((view) => view.id === activeViewId);
    if (!current) return;
    const name = window.prompt("Novo nome da visualização", current.name);
    if (!name?.trim() || name.trim() === current.name) return;
    await api(`/board/views/${current.id}`, "PUT", { name: name.trim(), layout: current.layout, config: current.config, shared: current.shared ?? false, shared_roles: current.shared_roles ?? [], shared_group_ids: current.shared_group_ids ?? [], position: current.position });
  });
  const moveView = (identity: number, delta: number) => run(async () => {
    const current = [...(viewQuery.data ?? [])].filter((view) => view.owner_id === account.id).sort((a, b) => a.position - b.position);
    const from = current.findIndex((view) => view.id === identity); const to = from + delta;
    if (from < 0 || to < 0 || to >= current.length) return;
    [current[from], current[to]] = [current[to], current[from]];
    await api("/board/views/order", "PUT", { ids: current.map((view) => view.id) });
  });
  const deleteView = () => run(async () => {
    if (activeViewId === null || !window.confirm("Excluir esta visualização salva?")) return;
    await api(`/board/views/${activeViewId}`, "DELETE");
    setActiveViewId(null);
    setLayout("board"); setFilterQuery(""); setQuickFilterIds([]); setQuickFilterDefinitions(boardQuickFilters); setAdvancedQuery(""); setGroupBy(""); setSortBy(""); setSliceBy(""); setSliceValue(""); setSumBy(""); setVisibleFields([]); setDescending(false);
  });
  const updateColumnOrder = (ordered: ProjectColumn[]) => run(() => api("/board/columns/order", "PUT", { keys: ordered.map((column) => column.key) }));
  const addColumn = () => run(async () => {
    const created = await api<ProjectColumn>("/board/columns", "POST", { title: "Título coluna" });
    setEditingColumn(created.key);
  });
  const renameColumn = (column: ProjectColumn, title: string) => {
    setEditingColumn(null);
    if (title.trim() && title.trim() !== column.title) void run(() => api(`/board/columns/${column.key}`, "PUT", { title: title.trim() }));
  };
  const changeColumnCategory = (column: ProjectColumn, category: "todo" | "in_progress") => run(() => api(`/board/columns/${column.key}`, "PUT", { category }));
  const changeColumnWipLimit = (column: ProjectColumn, wip_limit: number | null) => run(() => api(`/board/columns/${column.key}`, "PUT", { wip_limit }));
  const removeColumn = (column: ProjectColumn) => run(async () => {
    if (window.confirm(`Excluir a coluna “${column.title}”? Ela precisa estar vazia.`)) await api(`/board/columns/${column.key}`, "DELETE");
  });
  const allTasks = rows.data ?? [];
  const meSupplierId = suppliers.find((supplier) => supplier.user_id === account.id)?.id;
  const quickFilterQuery = quickFilterDefinitions.filter((filter) => quickFilterIds.includes(filter.id)).map((filter) => filter.query).join(" ");
  let filteredTasks = filterBoardTasks(allTasks, [filterQuery, quickFilterQuery].filter(Boolean).join(" "), columns, suppliers, sprints, meSupplierId);
  if (sliceBy && sliceValue) filteredTasks = filteredTasks.filter((task) => {
    const value = sliceBy === "status" ? task.status : sliceBy === "supplier" ? task.supplier_id : sliceBy === "sprint" ? task.sprint_id : sliceBy === "priority" ? task.priority : sliceBy === "approval" ? task.approval : task.labels?.map((label) => label.text).includes(sliceValue) ? sliceValue : null;
    return String(value ?? "") === sliceValue;
  });
  const getSortValue = (task: Task) => sortBy === "title" ? task.title.toLocaleLowerCase("pt-BR") : sortBy === "priority" ? task.priority : sortBy === "due" ? task.due ?? "9999" : sortBy === "created_at" ? task.created_at ?? "" : sortBy === "supplier" ? suppliers.find((supplier) => supplier.id === task.supplier_id)?.name ?? "" : groupBy === "supplier" ? suppliers.find((supplier) => supplier.id === task.supplier_id)?.name ?? "" : groupBy === "priority" ? task.priority : groupBy === "sprint" ? task.sprint_id ?? 0 : groupBy === "approval" ? task.approval : groupBy === "status" ? task.status_title ?? task.status : groupBy === "parent" ? task.parent_id ?? 0 : groupBy === "work_type" ? task.work_type ?? "task" : task.priority;
  if (sortBy || groupBy) filteredTasks = [...filteredTasks].sort((a, b) => (String(getSortValue(a)).localeCompare(String(getSortValue(b)), "pt-BR", { numeric: true })) * (descending ? -1 : 1));
  const exportCalendar = () => run(async () => {
    if (filteredTasks.length > 5000) throw new Error("Exporte até 5.000 cards por vez; refine os filtros do calendário.");
    await downloadPost("/calendar.ics", { task_ids: filteredTasks.map((task) => task.id) });
  });
  const sliceOptions = sliceBy === "status" ? columns.map((column) => ({ value: column.key, label: column.title })) : sliceBy === "supplier" ? suppliers.map((supplier) => ({ value: String(supplier.id), label: supplier.name })) : sliceBy === "sprint" ? Array.from(new Set(allTasks.map((task) => task.sprint_id).filter((id): id is number => id !== null))).map((id) => ({ value: String(id), label: `Sprint ${id}` })) : sliceBy === "priority" ? Array.from(new Set(allTasks.map((task) => task.priority))).map((priority) => ({ value: String(priority), label: `Prioridade ${priority}` })) : sliceBy === "approval" ? Array.from(new Set(allTasks.map((task) => task.approval))).map((approval) => ({ value: approval, label: approval })) : sliceBy === "label" ? Array.from(new Set(allTasks.flatMap((task) => task.labels?.map((label) => label.text) ?? []))).map((label) => ({ value: label, label })) : [];
  const customFieldMap = new Map<string, { key: string; label: string }>();
  for (const task of allTasks) for (const field of task.fields) customFieldMap.set(field.id, { key: field.id, label: field.label });
  const availableFields: { key: string; label: string }[] = [
    { key: "title", label: "Card" }, { key: "status", label: "Status" }, { key: "supplier", label: "Fornecedor" }, { key: "sprint", label: "Sprint" },
    { key: "priority", label: "Prioridade" }, { key: "labels", label: "Etiquetas" }, { key: "due", label: "Prazo" }, { key: "approval", label: "Aprovação" },
    { key: "created_at", label: "Criado em" }, { key: "description", label: "Descrição" }, { key: "estimated_minutes", label: "Horas previstas" }, { key: "used_minutes", label: "Horas utilizadas" },
    { key: "parent", label: "Card pai" }, { key: "work_type", label: "Tipo de card" },
    ...customFieldMap.values(),
    ...(account.role !== "supplier" && account.permissions.includes("view_financial") ? [{ key: "cost_cents", label: "Custo aprovado" }] : []),
  ];
  const displayedFields = visibleFields.length ? visibleFields : availableFields.slice(0, 8).map((field) => field.key);
  const saveSchedule = (task: Task, planned_start: string, due: string) => run(() => api(`/tasks/${task.id}/schedule`, "PUT", { version: task.version, planned_start: planned_start || null, due: due || null }));
  return (
    <>
      <div className="section-title">
        <h2>Quadro Kanban</h2>
        <span>Arraste pela alça ou abra o card para mover pelo menu.</span>
      </div>
      <ViewTools views={viewQuery.data ?? []} activeId={activeViewId} currentUserId={account.id} layout={layout} query={filterQuery} advancedQuery={advancedQuery} groupBy={groupBy} sortBy={sortBy} zoom={zoom} fields={availableFields} visibleFields={displayedFields} sliceBy={sliceBy} sliceValue={sliceValue} sliceOptions={sliceOptions} sumBy={sumBy} descending={descending} financial={account.role !== "supplier" && account.permissions.includes("view_financial")} shared={sharedView} sharedRoles={sharedRoles} sharedGroupIds={sharedGroupIds} groups={shareGroups.data ?? []} canShare={account.permissions.includes("manage_planning")}
          onSelect={selectView} onLayout={setLayout} onQuery={setFilterQuery} onAdvancedQuery={setAdvancedQuery} onGroup={setGroupBy} onSort={setSortBy} onZoom={setZoom}
          onSliceBy={setSliceBy} onSliceValue={setSliceValue} onSum={setSumBy} onDirection={() => setDescending((current) => !current)} onShared={(value) => { setSharedView(value); setSharedRoles(value ? ["admin", "manager", "internal"] : []); if (!value) setSharedGroupIds([]); }} onSharedRoles={setSharedRoles} onSharedGroupIds={setSharedGroupIds}
          onToggleField={(field) => setVisibleFields(() => displayedFields.includes(field) ? displayedFields.filter((key) => key !== field) : [...displayedFields, field])}
          onMoveField={(field, delta) => setVisibleFields(() => { const next = [...displayedFields]; const from = next.indexOf(field); const to = from + delta; if (to >= 0 && to < next.length) [next[from], next[to]] = [next[to], next[from]]; return next; })}
          onSave={saveView} onDuplicate={duplicateView} onDelete={deleteView} onRename={renameView} onMoveView={moveView} />
      {layout === "board" && <QuickFilters filters={quickFilterDefinitions} active={quickFilterIds} onChange={setQuickFilterIds} onFiltersChange={setQuickFilterDefinitions} />}
      {rows.isPending ? (
        <Empty>Carregando quadro…</Empty>
      ) : rows.isError ? (
        <Empty>{rows.error.message}</Empty>
      ) : (
        <>
        {layout === "table" ? <ProjectTable tasks={filteredTasks} columns={columns} suppliers={suppliers} fields={availableFields} visibleFields={displayedFields} groupBy={groupBy} sumBy={sumBy} open={open} /> : layout === "timeline" ? <TimelineView tasks={filteredTasks} columns={columns} suppliers={suppliers} sprints={sprints} zoom={zoom} account={account} saveSchedule={saveSchedule} open={open} /> : layout === "calendar" ? <CalendarView tasks={filteredTasks} open={open} canSchedule={account.permissions.includes("create_tasks")} saveSchedule={saveSchedule} onExportCalendar={exportCalendar} calendarFeedActive={calendarFeed.data?.enabled ?? false} calendarFeedLoading={calendarFeed.isPending} calendarFeedUrl={calendarFeedUrl} calendarFeedSecret={calendarFeedSecret} onCreateCalendarFeed={createCalendarFeed} onRevokeCalendarFeed={revokeCalendarFeed} onCopyCalendarFeedUrl={() => run(() => navigator.clipboard.writeText(calendarFeedUrl))} onCopyCalendarFeedSecret={() => run(() => navigator.clipboard.writeText(calendarFeedSecret))} /> : <DndContext
          sensors={sensors}
          collisionDetection={(args) => {
            const scoped = {
              ...args,
              droppableContainers: args.droppableContainers.filter(
                (container) => container.id !== args.active.id,
              ),
            };
            const direct = pointerWithin(scoped);
            return direct.length ? direct : closestCorners(scoped);
          }}
          onDragEnd={onDragEnd}
          onDragStart={onDragStart}
          onDragCancel={() => setActiveTask(null)}
        >
          <div className="kanban">
            {columns.map((column, columnIndex) => (
              <Column
                key={column.key}
                status={column.key}
                title={column.title}
                category={column.category ?? (column.key === "done" ? "done" : "in_progress")}
                wipLimit={column.wip_limit}
                canManage={canManage}
                isFirst={columnIndex === 0}
                isLast={columnIndex === columns.length - 1}
                editing={editingColumn === column.key}
                onEdit={() => setEditingColumn(column.key)}
                onRename={(title) => renameColumn(column, title)}
                onCategory={(category) => changeColumnCategory(column, category)}
                onWipLimit={(limit) => changeColumnWipLimit(column, limit)}
                onDelete={() => removeColumn(column)}
                onMove={(delta) => {
                  const next = [...columns]; const target = columnIndex + delta;
                  if (target < 0 || target >= next.length) return;
                  [next[columnIndex], next[target]] = [next[target], next[columnIndex]];
                  updateColumnOrder(next);
                }}
                onDragStart={() => setDraggedColumn(column.key)}
                onDrop={() => {
                  if (!draggedColumn || draggedColumn === column.key) return;
                  const next = [...columns]; const from = next.findIndex((item) => item.key === draggedColumn); const to = next.findIndex((item) => item.key === column.key);
                  next.splice(to, 0, next.splice(from, 1)[0]); setDraggedColumn(null); updateColumnOrder(next);
                }}
                count={
                  filteredTasks.filter((task) => task.status === column.key).length
                }
                summary={sumBy === "estimated_minutes" ? `${(filteredTasks.filter((task) => task.status === column.key).reduce((sum, task) => sum + task.estimated_minutes, 0) / 60).toFixed(1)} h previstas` : sumBy === "used_minutes" ? `${(filteredTasks.filter((task) => task.status === column.key).reduce((sum, task) => sum + task.used_minutes, 0) / 60).toFixed(1)} h utilizadas` : sumBy === "cost_cents" && account.role !== "supplier" && account.permissions.includes("view_financial") ? new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(filteredTasks.filter((task) => task.status === column.key).reduce((sum, task) => sum + (task.cost_cents ?? 0), 0) / 100) : sumBy === "count" ? `${filteredTasks.filter((task) => task.status === column.key).length} cards` : ""}
              >
                {
                  <SortableContext
                    items={filteredTasks
                      .filter((task) => task.status === column.key)
                      .map((task) => task.id)}
                    strategy={verticalListSortingStrategy}
                  >
                    {filteredTasks
                      .filter((task) => task.status === column.key)
                      .map((task) => (
                        <DraggableTask
                          key={task.id}
                          task={task}
                          suppliers={suppliers}
                          open={open}
                        />
                      ))}
                  </SortableContext>
                }
              </Column>
            ))}
            {canManage && <button className="kanban-add-column" aria-label="Adicionar coluna ao Kanban" title="Adicionar coluna" onClick={addColumn}><Plus size={22} aria-hidden="true" /></button>}
          </div>
          <DragOverlay dropAnimation={{ duration: 180, easing: "cubic-bezier(0.18, 0.67, 0.6, 1.22)" }}>
            {activeTask ? (
              <article className="kanban-card kanban-card-overlay" aria-hidden="true">
                <div className="card-top"><small>OS-{activeTask.id}</small><GripVertical size={18} aria-hidden="true" /></div>
                <div className="card-title">{activeTask.title}</div>
                <small className="card-supplier">
                  Fornecedor responsável: {suppliers.find((row) => row.id === activeTask.supplier_id)?.name ?? "Não atribuído"}
                </small>
                <TaskLabels labels={activeTask.labels} />
                <p>{activeTask.description.slice(0, 95)}</p>
                <div>
                  {activeTask.fields.some((field) => field.native_key === "estimated_minutes") && (
                    <span className="badge">{activeTask.estimated_minutes / 60}h previstas</span>
                  )}
                  {activeTask.approval === "rejected" && <span className="rejection">Corrigir horas</span>}
                </div>
                <small>{activeTask.due ? "Prazo " + activeTask.due : "Sem prazo"}</small>
              </article>
            ) : null}
          </DragOverlay>
        </DndContext>}
        </>
      )}
    </>
  );
}
export function TaskDetail({
  identity,
  account,
  suppliers,
  run,
  close,
}: {
  identity: number;
  account: Account;
  suppliers: Supplier[];
  run: Run;
  close: () => void;
}) {
  const detail = useQuery({
    queryKey: ["task", identity],
    queryFn: () => api<Task>("/tasks/" + identity),
  });
  const watchState = useQuery({
    queryKey: ["task-watch", identity],
    queryFn: () => api<{ watching: boolean }>(`/tasks/${identity}/watch`),
  });
  const [tab, setTab] = useState("activity");
  const [pendingCompletion, setPendingCompletion] = useState(false);
  const [resolutionDraft, setResolutionDraft] = useState<NonNullable<Task["resolution"]>>("Done");
  useEffect(() => {
    const element = document.activeElement as HTMLElement;
    return () => element?.focus();
  }, []);
  if (!detail.data)
    return (
      <div className="modal">
        <section className="dialog">
          <button onClick={close}>Fechar</button>
          <Empty>{detail.error?.message ?? "Carregando card…"}</Empty>
        </section>
      </div>
    );
  const task = detail.data;
  const canConfigure =
    account.permissions.includes("configure_cards") ||
    account.permissions.includes("create_tasks");
  return (
    <div
      className="modal"
      onClick={(event) => {
        if (event.target === event.currentTarget) close();
      }}
    >
      <section
        className="dialog"
        onKeyDown={(event) => {
          if (event.key === "Escape") close();
          if (event.key === "Tab") {
            const nodes = event.currentTarget.querySelectorAll<HTMLElement>(
              "button:not(:disabled),a,input:not(:disabled),select:not(:disabled),textarea:not(:disabled),summary",
            );
            const first = nodes[0],
              last = nodes[nodes.length - 1];
            if (event.shiftKey && document.activeElement === first) {
              event.preventDefault();
              last?.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
              event.preventDefault();
              first?.focus();
            }
          }
        }}
        role="dialog"
        aria-modal="true"
        aria-label={"Atividade " + task.title}
      >
        <div className="section-title">
          <span className="eyebrow">ATIVIDADE OS-{task.id}</span>
          <div className="actions">
            <button
              disabled={watchState.isFetching}
              aria-pressed={watchState.data?.watching ?? false}
              onClick={() => run(async () => {
                await api(`/tasks/${identity}/watch`, watchState.data?.watching ? "DELETE" : "PUT");
                await watchState.refetch();
              })}
            >
              {watchState.data?.watching ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
              {watchState.data?.watching ? "Parar de acompanhar" : "Acompanhar atividade"}
            </button>
            <button onClick={close} autoFocus aria-label="Fechar atividade">
              <X size={18} aria-hidden="true" /> Fechar
            </button>
          </div>
        </div>
        <h2>{task.title}</h2>
        {task.resolution && <p className="muted">Resolução: {{ "Done": "Concluído", "Fixed": "Corrigido", "Duplicate": "Duplicado", "Won't Do": "Não será feito", "Cannot Reproduce": "Não reproduzido", "Other": "Outro" }[task.resolution]}</p>}
        <div className="tabs">
          <button
            aria-pressed={tab === "activity"}
            onClick={() => setTab("activity")}
          >
            Detalhes e fluxo
          </button>
          {canConfigure && (
            <button
              aria-pressed={tab === "schema"}
              onClick={() => setTab("schema")}
            >
              Construtor do card
            </button>
          )}
          {account.role !== "supplier" && (
            <button
              aria-pressed={tab === "history"}
              onClick={() => setTab("history")}
            >
              Histórico
            </button>
          )}
        </div>
        {tab === "schema" ? (
          <FieldBuilder key={task.version} task={task} run={run} />
        ) : tab === "history" ? (
          <HistoryTimeline identity={identity} />
        ) : (
          <>
            <span className={"badge " + task.status}>
              {stages[task.status] ?? task.status_title ?? task.status}
            </span>
            <p>{task.description}</p>
            <TaskLabels labels={task.labels} />
            <p className={task.approval === "rejected" ? "rejection" : "muted"}>
              {approvals[task.approval]}{" "}
              {task.approval_reason && "— " + task.approval_reason}
            </p>
            {task.cost_cents != null && (
              <p>
                Tarifa congelada:{" "}
                {task.rate_cents === null
                  ? "Sem tarifa"
                  : money(task.rate_cents ?? 0) + "/h"}{" "}
                · Custo aprovado: <strong>{money(task.cost_cents)}</strong>
              </p>
            )}
            {account.permissions.includes("manage_planning") && <CardPlanning task={task} run={run} />}
            <div className="actions">
              <Label title="Mover atividade">
                <select
                  value={task.status}
                  onChange={(e) => {
                    const status = e.target.value;
                    if (status === "done" && account.role !== "supplier") {
                      setResolutionDraft(task.resolution ?? "Done");
                      setPendingCompletion(true);
                      return;
                    }
                    const reason =
                      task.status === "done"
                        ? window.prompt("Justificativa da reabertura")
                        : "";
                    if (reason === null) return;
                    run(() =>
                      api(`/tasks/${identity}/move`, "POST", {
                        version: task.version,
                        status,
                        priority: task.priority,
                        reason,
                      }),
                    );
                  }}
                >
                  {Object.entries(stages).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </Label>
            </div>
            {account.role === "supplier" &&
              !task.fields.some(
                (field) =>
                  field.type === "native" &&
                  ["estimated_minutes", "used_minutes"].includes(
                    field.native_key ?? "",
                  ),
              ) && <HoursForm key={task.id} task={task} run={run} />}
            <p className="formula">
              Horas previstas seguem a configuração individual do card. Horas
              utilizadas são exigidas para revisão. Conclusão exige gestor e
              aprovação.
            </p>
            {account.permissions.includes("approve_hours") &&
              task.status === "review" && (
                <div className="approval-box">
                  <h3>Aprovação de horas</h3>
                  <p>
                    Versão {task.hours_version} · {task.used_minutes / 60} horas
                    utilizadas
                  </p>
                  <div className="actions">
                    <button
                      className="primary"
                      disabled={task.approval === "approved"}
                      onClick={() =>
                        run(() =>
                          api(`/tasks/${identity}/approval`, "POST", {
                            version: task.version,
                            hours_version: task.hours_version,
                            approved: true,
                            reason: "",
                          }),
                        )
                      }
                    >
                      Aprovar horas
                    </button>
                    <button
                      disabled={task.approval === "approved"}
                      onClick={() => {
                        const reason = window.prompt(
                          "Justificativa obrigatória da rejeição",
                        );
                        if (reason)
                          run(() =>
                            api(`/tasks/${identity}/approval`, "POST", {
                              version: task.version,
                              hours_version: task.hours_version,
                              approved: false,
                              reason,
                            }),
                          );
                      }}
                    >
                      Rejeitar horas
                    </button>
                  </div>
                </div>
              )}
            <Collaboration
              identity={task.id}
              readOnly={task.status === "done"}
              run={run}
            />
            <FieldValueForm
              key={"values" + task.version}
              task={task}
              account={account}
              run={run}
            />
            <TaskDevelopmentEvents identity={task.id} />
            {account.permissions.includes("create_tasks") &&
              task.status !== "done" && (
                <details>
                  <summary>Editar campos estruturais</summary>
                  <TaskForm
                    suppliers={suppliers}
                    task={task}
                    submit={(values) =>
                      run(() => api("/tasks/" + identity, "PUT", values))
                    }
                  />
                </details>
              )}
            {account.permissions.includes("create_tasks") &&
              task.status === "backlog" &&
              !task.sprint_id &&
              !task.hours_version && (
                <button
                  onClick={() => {
                    if (
                      window.confirm(
                        "Arquivar esta atividade sem apagar o histórico?",
                      )
                    )
                      run(async () => {
                        await api(
                          `/tasks/${identity}?expected_version=${task.version}`,
                          "DELETE",
                        );
                        close();
                      });
                  }}
                >
                  Arquivar atividade
                </button>
              )}
          </>
        )}
      </section>
      {pendingCompletion && <div className="resolution-overlay" onClick={(event) => { if (event.target === event.currentTarget) setPendingCompletion(false); }}>
        <section className="resolution-dialog panel" role="dialog" aria-modal="true" aria-labelledby="resolution-title">
          <span className="eyebrow">ENCERRAMENTO DO CARD</span>
          <h2 id="resolution-title">Registrar resolução</h2>
          <p>Escolha o resultado que ficará no histórico e poderá ser consultado nos filtros e relatórios.</p>
          <Label title="Resolução"><select autoFocus value={resolutionDraft} onChange={(event) => setResolutionDraft(event.target.value as NonNullable<Task["resolution"]>)}>
            <option value="Done">Concluído</option><option value="Fixed">Corrigido</option><option value="Duplicate">Duplicado</option><option value="Won't Do">Não será feito</option><option value="Cannot Reproduce">Não reproduzido</option><option value="Other">Outro</option>
          </select></Label>
          <div className="actions"><button type="button" onClick={() => setPendingCompletion(false)}>Cancelar</button><button type="button" className="primary" onClick={() => {
            setPendingCompletion(false);
            run(() => api(`/tasks/${identity}/move`, "POST", { version: task.version, status: "done", priority: task.priority, resolution: resolutionDraft }));
          }}>Concluir card</button></div>
        </section>
      </div>}
    </div>
  );
}

function TaskDevelopmentEvents({ identity }: { identity: number }) {
  const events = useQuery({
    queryKey: ["development-events", identity],
    queryFn: () => api<DevelopmentEvent[]>(`/tasks/${identity}/development`),
  });
  return (
    <section className="development-events" aria-labelledby="development-events-title">
      <div className="section-title">
        <div>
          <h3 id="development-events-title">Atividade de desenvolvimento</h3>
          <p className="muted">Pull requests, commits e implantações vinculados a este card.</p>
        </div>
      </div>
      {events.isPending ? <p className="muted">Carregando eventos…</p> : events.error ? (
        <p role="alert" className="rejection">{events.error.message}</p>
      ) : events.data?.length ? (
        <ul className="development-event-list">
          {events.data.map((event) => (
            <li key={event.id}>
              <span className={`development-provider ${event.provider}`}>{event.provider}</span>
              <div>
                <strong>{event.summary}</strong>
                <small>
                  {event.actor ? `${event.actor} · ` : ""}
                  {new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(event.received_at))}
                </small>
                {!!Object.values(event.metadata ?? {}).length && <small className="development-event-details">
                  {[event.metadata.repository, event.metadata.branch && `branch ${event.metadata.branch}`, event.metadata.commit && `commit ${event.metadata.commit.slice(0, 12)}`, event.metadata.pull_request && `PR #${event.metadata.pull_request}`, event.metadata.state, event.metadata.environment].filter(Boolean).join(" · ")}
                </small>}
              </div>
              {event.url && <a href={event.url} target="_blank" rel="noopener noreferrer">Abrir ↗</a>}
            </li>
          ))}
        </ul>
      ) : <p className="muted">Nenhum evento integrado para este card.</p>}
    </section>
  );
}

function CardPlanning({ task, run }: { task: Task; run: Run }) {
  const releases = useQuery({ queryKey: ["releases"], queryFn: () => api<{ id: number; name: string; released_at: string | null }[]>("/releases") });
  const components = useQuery({ queryKey: ["components"], queryFn: () => api<{ id: number; name: string }[]>("/components") });
  const [releaseIds, setReleaseIds] = useState<number[]>(task.release_ids ?? []);
  const [componentIds, setComponentIds] = useState<number[]>(task.component_ids ?? []);
  const [target, setTarget] = useState("");
  const [linkType, setLinkType] = useState("blocks");
  useEffect(() => { setReleaseIds(task.release_ids ?? []); setComponentIds(task.component_ids ?? []); }, [task.id, task.version, task.release_ids, task.component_ids]);
  return <section className="card-planning panel">
    <h3>Planejamento e relações</h3>
    <div className="form-grid">
      <Label title="Versões / releases"><select multiple value={releaseIds.map(String)} onChange={(event) => setReleaseIds(Array.from(event.target.selectedOptions, (item) => Number(item.value)))}>{(releases.data ?? []).map((row) => <option key={row.id} value={row.id}>{row.name}{row.released_at ? " · Publicada" : ""}</option>)}</select></Label>
      <Label title="Componentes"><select multiple value={componentIds.map(String)} onChange={(event) => setComponentIds(Array.from(event.target.selectedOptions, (item) => Number(item.value)))}>{(components.data ?? []).map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></Label>
    </div>
    <button onClick={() => run(() => api(`/tasks/${task.id}/planning-links?${new URLSearchParams([...releaseIds.map((id) => ["releases", String(id)] as [string,string]), ...componentIds.map((id) => ["components", String(id)] as [string,string])]).toString()}`, "PUT"))}>Salvar versões e componentes</button>
    <div className="planning-links">
      <strong>Dependências</strong>
      {(task.links ?? []).map((link) => <div key={link.id}>OS-{link.task_id} · {link.direction === "outgoing" ? link.type : link.type === "blocks" ? "bloqueia este card" : link.type}<button className="link" onClick={() => run(() => api(`/tasks/${task.id}/links/${link.id}`, "DELETE"))}>Remover</button></div>)}
      <div className="form-grid"><Label title="ID do card relacionado"><input type="number" min="1" value={target} onChange={(event) => setTarget(event.target.value)} placeholder="Ex.: 42" /></Label><Label title="Relação"><select value={linkType} onChange={(event) => setLinkType(event.target.value)}><option value="blocks">Este card bloqueia o outro</option><option value="relates">Relacionado a</option><option value="duplicates">Duplica</option></select></Label><button disabled={!target} onClick={() => run(async () => { await api(`/tasks/${task.id}/links`, "POST", { target_task_id: Number(target), link_type: linkType }); setTarget(""); })}>Adicionar relação</button></div>
    </div>
  </section>;
}
function HoursForm({ task, run }: { task: Task; run: Run }) {
  const history = useInfiniteQuery({
    queryKey: ["task-hours-history", task.id, task.hours_version],
    initialPageParam: 0,
    queryFn: ({ pageParam }) => api<{ items: { version: number; estimated_minutes: number; used_minutes: number; comment: string; author: string; created_at: string }[]; total: number; offset: number; limit: number }>(`/tasks/${task.id}/hours?offset=${pageParam}&limit=50`),
    getNextPageParam: (lastPage) => lastPage.offset + lastPage.items.length < lastPage.total ? lastPage.offset + lastPage.items.length : undefined,
  });
  const [used, setUsed] = useState(hourInput(task.used_minutes));
  const [comment, setComment] = useState(task.worklog_comment ?? "");
  const [editing, setEditing] = useState(task.used_minutes === 0);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const locked = task.status === "done" || task.approval === "approved";
  useEffect(() => {
    if (!editing) setUsed(hourInput(task.used_minutes));
    if (!editing) setComment(task.worklog_comment ?? "");
  }, [task.used_minutes, task.worklog_comment, editing]);
  return (
    <form
      className="inline-form"
      onSubmit={(event) => {
        event.preventDefault();
        if (!editing || locked || saving) return;
        setSaving(true);
        setSaved(false);
        run(async () => {
          try {
            await api(`/tasks/${task.id}/hours`, "PUT", {
              version: task.version,
              estimated_minutes: task.estimated_minutes,
              used_minutes: decimalToUnits(used, 60),
              comment,
            });
            setEditing(false);
            setSaved(true);
          } finally {
            setSaving(false);
          }
        });
      }}
    >
      <h3>Apontamento do fornecedor</h3>
      <div className="form-grid">
        <Label title="Horas utilizadas (total)">
          <input
            ref={input}
            inputMode="decimal"
            value={used}
            readOnly={!editing || locked}
            disabled={saving}
            onChange={(event) => setUsed(event.target.value)}
          />
        </Label>
        <Label title="Comentário do apontamento">
          <textarea
            value={comment}
            maxLength={1000}
            readOnly={!editing || locked}
            disabled={saving}
            onChange={(event) => setComment(event.target.value)}
            placeholder="Opcional: detalhe o que foi realizado nesta versão de horas"
          />
        </Label>
      </div>
      <div className="actions">
        {editing ? (
          <button className="primary" disabled={locked || saving}>
            {saving ? "Salvando…" : "Salvar / reapresentar horas"}
          </button>
        ) : (
          <button
            type="button"
            disabled={locked || saving}
            onClick={(event) => {
              event.preventDefault();
              setSaved(false);
              setEditing(true);
              input.current?.focus();
            }}
          >
            Editar horas
          </button>
        )}
        <small className="hours-saved" role="status" aria-live="polite">
          {saved ? "✓ Horas salvas" : ""}
        </small>
      </div>
      <details className="hours-history">
        <summary>Histórico de apontamentos ({history.data?.pages[0]?.total ?? 0})</summary>
        {history.isLoading ? <p className="muted">Carregando versões…</p> : null}
        {history.error ? <p role="alert">Não foi possível carregar o histórico de horas.</p> : null}
        {history.data?.pages[0]?.total ? (
          <ol>
            {history.data.pages.flatMap((page) => page.items).map((entry) => (
              <li key={entry.version}>
                <div><strong>Versão {entry.version}</strong><span>{entry.author} · {new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(entry.created_at))}</span></div>
                <p>{entry.used_minutes / 60} h utilizadas · {entry.estimated_minutes / 60} h previstas</p>
                {entry.comment ? <blockquote>{entry.comment}</blockquote> : <p className="muted">Sem comentário</p>}
              </li>
            ))}
          </ol>
        ) : !history.isLoading && !history.error ? <p className="muted">Nenhum apontamento registrado.</p> : null}
        {history.hasNextPage ? <button type="button" disabled={history.isFetchingNextPage} onClick={() => void history.fetchNextPage()}>{history.isFetchingNextPage ? "Carregando…" : "Carregar versões anteriores"}</button> : null}
      </details>
    </form>
  );
}
