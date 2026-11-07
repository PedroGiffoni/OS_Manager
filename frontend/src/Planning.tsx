import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Archive, CalendarPlus, Layers3, Plus, Rocket, X } from "lucide-react";
import { api } from "./api";
import { Empty, Label, type Run } from "./App";
import type { Supplier } from "./types";

type Release = { id: number; name: string; description: string; starts: string | null; due: string | null; released_at: string | null; archived: boolean; version: number };
type Component = { id: number; name: string; description: string; owner_id: number | null; active: boolean };
type CapacityDay = { date: string; demand_minutes: number; suggested_demand_minutes: number; capacity_minutes: number; task_count: number; overload_minutes: number; suggested_overload_minutes: number };
type CapacityShift = { task_id: number; title: string; from_date: string; to_date: string; minutes: number };
type Capacity = { id: number; supplier_id: number | null; user_id: number | null; group_id: number | null; group_name: string | null; group_member_count: number | null; starts: string; ends: string; minutes: number; notes: string; demand_minutes: number; demand_tasks: number; unplanned_tasks: number; utilization_percent: number | null; overload_minutes: number; suggested_overload_minutes: number; levelable_minutes: number; suggested_shift_count: number; suggested_shifts: CapacityShift[]; daily: CapacityDay[]; leveling_plan_version: number; leveling_plan_active: boolean; leveling_plan_stale: boolean; leveling_plan_applied_at: string | null };
type CapacityUser = { id: number; username: string; role: string };
type CapacityGroup = { id: number; name: string; member_count: number };
type WorkType = "epic" | "story" | "task" | "bug" | "subtask";
type TypeRule = { enabled: boolean; roles: string[]; required_fields: string[]; conditions: WorkflowCondition[]; actions: WorkflowAction[] };
type WorkflowCondition = { field: "approval" | "work_type" | "priority" | "supplier_assigned" | "label" | "due_set" | "due_overdue" | "due_within_days" | "parent_set" | "assignee" | "release_assigned" | "component_assigned" | "blocked" | "custom_field_equals"; operator: "eq" | "not_eq" | "gte" | "lte"; value: string | number | boolean; custom_field_id?: string };
type WorkflowAction = { action: "set_priority" | "add_label" | "remove_label" | "add_comment" | "set_due_after_days" | "assign_internal_user" | "add_watcher" | "set_custom_fields"; config: Record<string, unknown> };
type Transition = { id: number; source: string; target: string; enabled: boolean; roles: string[]; work_types: string[]; required_fields: string[]; type_rules: Partial<Record<WorkType, TypeRule>>; conditions: WorkflowCondition[]; actions: WorkflowAction[] };
type Rule = { id: number; name: string; trigger: string; schedule_time: string | null; schedule_frequency: "daily" | "weekly"; schedule_weekdays: number[]; conditions: Record<string, unknown>; action: string; config: Record<string, any>; actions: WorkflowAction[]; enabled: boolean };
type AutomationRun = { id: number; created_at: string; rule_id: number | null; rule_name: string; trigger: string; task_id: number; task_key: string; task_title: string; actor_name: string; changed_fields: string[]; comments_added: number; watchers_added: number; skipped_actions: number };
const conditionSummary = (condition: WorkflowCondition, users: CapacityUser[] = []) => {
  if (condition.field === "due_overdue") return `prazo vencido ${condition.value ? "sim" : "não"}`;
  if (condition.field === "due_within_days") return `${condition.operator === "not_eq" ? "fora dos próximos" : "nos próximos"} ${condition.value} dias`;
  const label = ({ approval: "aprovação", work_type: "tipo", priority: "prioridade", supplier_assigned: "fornecedor atribuído", label: "etiqueta", due_set: "prazo definido", parent_set: "card filho", assignee: "responsável", release_assigned: "release vinculada", component_assigned: "componente vinculado", blocked: "bloqueado por dependência", custom_field_equals: `campo ${condition.custom_field_id}` } as const)[condition.field];
  return `${label} ${{ eq: "=", not_eq: "≠", gte: "≥", lte: "≤" }[condition.operator]} ${condition.field === "assignee" ? users.find((user) => user.id === condition.value)?.username ?? `#${condition.value}` : JSON.stringify(condition.value)}`;
};
const actionSummary = (action: WorkflowAction, users: CapacityUser[] = []) => action.action === "set_priority" ? `prioridade ${action.config.priority}` : action.action === "add_label" ? `adicionar etiqueta ${action.config.text}` : action.action === "remove_label" ? `remover etiqueta ${action.config.text}` : action.action === "set_due_after_days" ? `prazo ${action.config.days} dias após criação` : action.action === "assign_internal_user" ? `responsável ${users.find((user) => user.id === action.config.user_id)?.username ?? `#${action.config.user_id}`}` : action.action === "add_watcher" ? `observador ${users.find((user) => user.id === action.config.user_id)?.username ?? `#${action.config.user_id}`}` : action.action === "set_custom_fields" ? `atualizar campos ${Object.keys((action.config.values as Record<string, unknown>) ?? {}).join(", ")}` : `comentário “${action.config.body}”`;
const automationActionSummary = actionSummary;
const weekdayOptions = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];
const dateToday = () => new Date().toISOString().slice(0, 10);
const validCustomFieldValues = (raw: string) => {
  try {
    const value: unknown = JSON.parse(raw);
    return !!value && typeof value === "object" && !Array.isArray(value)
      && Object.keys(value).length > 0 && Object.keys(value).length <= 10
      && Object.entries(value).every(([key, item]) => /^[a-zA-Z][a-zA-Z0-9_]{0,79}$/.test(key)
        && (item === null || typeof item === "string" && item.length <= 10000
          || typeof item === "boolean" || typeof item === "number" && Number.isFinite(item)));
  } catch { return false; }
};

export function Planning({ suppliers, canPlan, canCapacity, canWorkflow, canAutomation, run }: { suppliers: Supplier[]; canPlan: boolean; canCapacity: boolean; canWorkflow: boolean; canAutomation: boolean; run: Run }) {
  const [tab, setTab] = useState<"releases" | "components" | "capacity" | "workflow" | "automations">("releases");
  const [release, setRelease] = useState({ name: "", description: "", starts: "", due: "" });
  const [component, setComponent] = useState({ name: "", description: "" });
  const [capacity, setCapacity] = useState({ resource_type: "supplier", resource_id: "", starts: dateToday(), ends: dateToday(), hours: "40", notes: "" });
  const [transition, setTransition] = useState({ source: "todo", target: "production", roles: "admin,manager,internal", work_types: [] as string[], required_fields: "", type_rules: {} as Partial<Record<WorkType, TypeRule>>, conditions: [] as WorkflowCondition[], actions: [] as WorkflowAction[] });
  const [editingTransitionId, setEditingTransitionId] = useState<number | null>(null);
  const [typeRuleDraft, setTypeRuleDraft] = useState({ type: "bug" as WorkType, enabled: true, roles: "", required_fields: "" });
  const [conditionDraft, setConditionDraft] = useState<WorkflowCondition>({ field: "approval", operator: "eq", value: "approved" });
  const [workflowCustomFieldDraft, setWorkflowCustomFieldDraft] = useState({ id: "", value: '""' });
  const [actionDraft, setActionDraft] = useState({ action: "add_comment" as WorkflowAction["action"], value: "", color: "#2B4EDA", custom_field_values: "{}" });
  const [rule, setRule] = useState({ name: "", trigger: "status_changed", schedule_time: "09:00", schedule_frequency: "daily" as "daily" | "weekly", schedule_weekdays: [] as number[], action: "set_priority", priority: "0", label: "", comment: "", due_days: "14", assignee_user: "", custom_field_values: "{}", assignee_filter: "", due_window: "", overdue: "", color: "#2B4EDA", statuses: "", work_types: "", approval_states: "", priority_min: "", priority_max: "", labels: "", due_set: "", release_assigned: "", component_assigned: "", blocked: "", development_providers: "", development_event_types: "", development_states: "", comment_contains: "", attachment_media_types: "", link_types: "", changed_fields: "", sprint_scope_action: "" });
  const [automationActions, setAutomationActions] = useState<WorkflowAction[]>([]);
  const [customFieldsJson, setCustomFieldsJson] = useState("");
  const [actionDraftDirty, setActionDraftDirty] = useState(false);
  const [editingAutomationId, setEditingAutomationId] = useState<number | null>(null);
  const [automationEnabled, setAutomationEnabled] = useState(true);
  const [automationRunOffset, setAutomationRunOffset] = useState(0);
  const releases = useQuery({ queryKey: ["releases"], queryFn: () => api<Release[]>("/releases") });
  const components = useQuery({ queryKey: ["components"], queryFn: () => api<Component[]>("/components") });
  const capacities = useQuery({ queryKey: ["capacity"], queryFn: () => api<Capacity[]>("/capacity"), enabled: canCapacity });
  const capacityUsers = useQuery({ queryKey: ["capacity-users"], queryFn: () => api<CapacityUser[]>("/directory/users"), enabled: canCapacity });
  const capacityGroups = useQuery({ queryKey: ["capacity-groups"], queryFn: () => api<CapacityGroup[]>("/capacity/groups"), enabled: canCapacity });
  const workflowAssignees = useQuery({ queryKey: ["workflow-assignees"], queryFn: () => api<CapacityUser[]>("/directory/workflow-assignees"), enabled: canWorkflow || canAutomation });
  const transitions = useQuery({ queryKey: ["workflow-transitions"], queryFn: () => api<Transition[]>("/workflows/transitions"), enabled: canWorkflow });
  const automations = useQuery({ queryKey: ["automation-rules"], queryFn: () => api<Rule[]>("/automations"), enabled: canAutomation });
  const automationRuns = useQuery({ queryKey: ["automation-runs", automationRunOffset], queryFn: () => api<AutomationRun[]>(`/automations/runs?limit=25&offset=${automationRunOffset}`), enabled: canAutomation && tab === "automations", refetchInterval: 15000 });
  const boardColumns = useQuery({ queryKey: ["board-columns"], queryFn: () => api<{ key: string; title: string }[]>("/board/columns"), enabled: canWorkflow });
  const saveRelease = () => run(async () => {
    await api("/releases", "POST", { ...release, starts: release.starts || null, due: release.due || null });
    setRelease({ name: "", description: "", starts: "", due: "" });
  });
  const saveComponent = () => run(async () => {
    await api("/components", "POST", component);
    setComponent({ name: "", description: "" });
  });
  const saveCapacity = () => run(async () => {
    const hours = Number(capacity.hours.replace(",", "."));
    if (!Number.isFinite(hours) || hours < 0 || !Number.isInteger(hours * 60)) throw new Error("Informe horas válidas, em incrementos de minutos.");
    await api("/capacity", "POST", { supplier_id: capacity.resource_type === "supplier" ? Number(capacity.resource_id) : null, user_id: capacity.resource_type === "user" ? Number(capacity.resource_id) : null, group_id: capacity.resource_type === "group" ? Number(capacity.resource_id) : null, starts: capacity.starts, ends: capacity.ends, minutes: Math.round(hours * 60), notes: capacity.notes });
    setCapacity((current) => ({ ...current, notes: "" }));
  });
  const applyLeveling = (row: Capacity) => run(async () => {
    if (!window.confirm("Aplicar esta redistribuição à previsão diária de capacidade? Os prazos, horas apontadas e custos dos cards não serão alterados.")) return;
    await api(`/capacity/${row.id}/level`, "POST", { expected_plan_version: row.leveling_plan_version });
  });
  const saveTransition = () => run(async () => {
    const payload = {
      source: transition.source,
      target: transition.target,
      enabled: true,
      roles: transition.roles.split(",").map((value) => value.trim()).filter(Boolean),
      work_types: transition.work_types,
      required_fields: transition.required_fields.split(",").map((value) => value.trim()).filter(Boolean),
      type_rules: transition.type_rules,
      conditions: transition.conditions,
      actions: transition.actions,
    };
    await api(editingTransitionId ? `/workflows/transitions/${editingTransitionId}` : "/workflows/transitions", editingTransitionId ? "PUT" : "POST", payload);
    setEditingTransitionId(null);
    setTransition((current) => ({ ...current, roles: "admin,manager,internal", work_types: [], required_fields: "", type_rules: {}, conditions: [], actions: [] }));
  });
  const editTransition = (row: Transition) => {
    setTransition({ source: row.source, target: row.target, roles: row.roles.join(","), work_types: row.work_types, required_fields: row.required_fields.join(","), type_rules: row.type_rules ?? {}, conditions: row.conditions ?? [], actions: row.actions ?? [] });
    const firstType = Object.keys(row.type_rules ?? {})[0] as WorkType | undefined;
    const firstRule = firstType ? row.type_rules[firstType] : undefined;
    setTypeRuleDraft({ type: firstType ?? "bug", enabled: firstRule?.enabled ?? true, roles: firstRule?.roles.join(",") ?? "", required_fields: firstRule?.required_fields.join(",") ?? "" });
    setEditingTransitionId(row.id);
  };
  const buildWorkflowAction = (): WorkflowAction => {
    let config: WorkflowAction["config"];
    if (actionDraft.action === "add_label") config = { text: actionDraft.value, color: actionDraft.color };
    else if (actionDraft.action === "remove_label") config = { text: actionDraft.value };
    else if (actionDraft.action === "set_priority") config = { priority: Number(actionDraft.value) };
    else if (actionDraft.action === "set_due_after_days") config = { days: Number(actionDraft.value) };
    else if (actionDraft.action === "assign_internal_user" || actionDraft.action === "add_watcher") config = { user_id: Number(actionDraft.value) };
    else if (actionDraft.action === "set_custom_fields") config = { values: JSON.parse(actionDraft.custom_field_values) as Record<string, unknown> };
    else config = { body: actionDraft.value };
    return { action: actionDraft.action, config };
  };
  const workflowActionValid = actionDraft.action === "set_custom_fields"
    ? validCustomFieldValues(actionDraft.custom_field_values)
    : !!actionDraft.value.trim() && (!["assign_internal_user", "add_watcher"].includes(actionDraft.action) || Number(actionDraft.value) > 0);
  const addWorkflowAction = () => setTransition((current) => ({ ...current, actions: [...current.actions, buildWorkflowAction()] }));
  const buildWorkflowCondition = (): WorkflowCondition => conditionDraft.field === "custom_field_equals"
    ? { ...conditionDraft, custom_field_id: workflowCustomFieldDraft.id.trim(), value: JSON.parse(workflowCustomFieldDraft.value) as string | number | boolean }
    : conditionDraft;
  const workflowConditionValid = conditionDraft.field === "due_within_days"
    ? Number.isInteger(Number(conditionDraft.value)) && Number(conditionDraft.value) >= 0 && Number(conditionDraft.value) <= 3650
    : conditionDraft.field !== "custom_field_equals" || (() => {
    if (!/^[a-zA-Z][a-zA-Z0-9_]{0,79}$/.test(workflowCustomFieldDraft.id.trim())) return false;
    try {
      const value: unknown = JSON.parse(workflowCustomFieldDraft.value);
      return typeof value === "string" && value.length <= 1000 || typeof value === "boolean" || typeof value === "number" && Number.isFinite(value);
    } catch { return false; }
  })();
  const addTypeCondition = () => setTransition((current) => {
    const existing = current.type_rules[typeRuleDraft.type] ?? { enabled: true, roles: [], required_fields: [], conditions: [], actions: [] };
    return { ...current, type_rules: { ...current.type_rules, [typeRuleDraft.type]: { ...existing, conditions: [...(existing.conditions ?? []), buildWorkflowCondition()] } } };
  });
  const addTypeWorkflowAction = () => setTransition((current) => {
    const existing = current.type_rules[typeRuleDraft.type] ?? { enabled: true, roles: [], required_fields: [], conditions: [], actions: [] };
    return { ...current, type_rules: { ...current.type_rules, [typeRuleDraft.type]: { ...existing, actions: [...(existing.actions ?? []), buildWorkflowAction()] } } };
  });
  const buildAutomationAction = (): WorkflowAction => ({
    action: rule.action as WorkflowAction["action"],
    config: rule.action === "set_priority" ? { priority: Number(rule.priority) } : rule.action === "add_label" ? { text: rule.label, color: rule.color } : rule.action === "remove_label" ? { text: rule.label } : rule.action === "set_due_after_days" ? { days: Number(rule.due_days) } : rule.action === "assign_internal_user" || rule.action === "add_watcher" ? { user_id: Number(rule.assignee_user) } : rule.action === "set_custom_fields" ? { values: JSON.parse(rule.custom_field_values) as Record<string, unknown> } : { body: rule.comment },
  });
  const appendAutomationAction = () => {
    setAutomationActions((current) => [...current, buildAutomationAction()]);
    setActionDraftDirty(false);
  };
  const removeAutomationAction = (index: number) => setAutomationActions((current) => current.filter((_, itemIndex) => itemIndex !== index));
  const saveAutomation = () => run(async () => {
    if (rule.trigger === "scheduled_daily" && rule.schedule_frequency === "weekly" && !rule.schedule_weekdays.length) throw new Error("Selecione ao menos um dia para a recorrência semanal.");
    const actions = [...automationActions];
    if (actionDraftDirty || (actions.length === 0 && !editingAutomationId)) actions.push(buildAutomationAction());
    if (!actions.length) throw new Error("Adicione ao menos uma ação à automação.");
    const conditions = {
      ...(rule.statuses.trim() ? { statuses: rule.statuses.split(",").map((x) => x.trim()).filter(Boolean) } : {}),
      ...(rule.work_types.trim() ? { work_types: rule.work_types.split(",").map((x) => x.trim()).filter(Boolean) } : {}),
      ...(rule.approval_states.trim() ? { approval_states: rule.approval_states.split(",").map((x) => x.trim()).filter(Boolean) } : {}),
      ...(rule.priority_min.trim() ? { priority_min: Number(rule.priority_min) } : {}),
      ...(rule.priority_max.trim() ? { priority_max: Number(rule.priority_max) } : {}),
      ...(rule.labels.trim() ? { labels: rule.labels.split(",").map((x) => x.trim()).filter(Boolean) } : {}),
      ...(rule.due_set !== "" ? { due_set: rule.due_set === "true" } : {}),
      ...(rule.assignee_filter !== "" ? { assignee_user_ids: [Number(rule.assignee_filter)] } : {}),
      ...(rule.due_window !== "" ? { due_within_days: Number(rule.due_window) } : {}),
      ...(rule.overdue !== "" ? { overdue: rule.overdue === "true" } : {}),
      ...(rule.release_assigned !== "" ? { release_assigned: rule.release_assigned === "true" } : {}),
      ...(rule.component_assigned !== "" ? { component_assigned: rule.component_assigned === "true" } : {}),
      ...(rule.blocked !== "" ? { blocked: rule.blocked === "true" } : {}),
      ...(rule.development_providers.trim() ? { development_providers: rule.development_providers.split(",").map((x) => x.trim()).filter(Boolean) } : {}),
      ...(rule.development_event_types.trim() ? { development_event_types: rule.development_event_types.split(",").map((x) => x.trim()).filter(Boolean) } : {}),
      ...(rule.development_states.trim() ? { development_states: rule.development_states.split(",").map((x) => x.trim()).filter(Boolean) } : {}),
      ...(rule.trigger === "comment_added" && rule.comment_contains.trim() ? { comment_contains: rule.comment_contains.trim() } : {}),
      ...(rule.trigger === "attachment_added" && rule.attachment_media_types.trim() ? { attachment_media_types: rule.attachment_media_types.split(",").map((x) => x.trim()).filter(Boolean) } : {}),
      ...(["link_added", "link_removed"].includes(rule.trigger) && rule.link_types.trim() ? { link_types: rule.link_types.split(",").map((x) => x.trim()).filter(Boolean) } : {}),
      ...(rule.trigger === "field_changed" && rule.changed_fields.trim() ? { changed_fields: rule.changed_fields.split(",").map((x) => x.trim()).filter(Boolean) } : {}),
      ...(rule.trigger === "sprint_scope_changed" && rule.sprint_scope_action ? { sprint_scope_actions: [rule.sprint_scope_action] } : {}),
      ...(customFieldsJson.trim() ? { custom_field_equals: JSON.parse(customFieldsJson) } : {}),
    };
    const payload = {
      name: rule.name,
      trigger: rule.trigger,
      schedule_time: rule.trigger === "scheduled_daily" ? rule.schedule_time : null,
      schedule_frequency: rule.trigger === "scheduled_daily" ? rule.schedule_frequency : "daily",
      schedule_weekdays: rule.trigger === "scheduled_daily" && rule.schedule_frequency === "weekly" ? rule.schedule_weekdays : [],
      action: actions[0].action,
      actions,
      conditions,
      config: actions[0].config,
      enabled: automationEnabled,
    };
    await api(editingAutomationId ? `/automations/${editingAutomationId}` : "/automations", editingAutomationId ? "PUT" : "POST", payload);
    setEditingAutomationId(null);
    setAutomationEnabled(true);
    setAutomationActions([]);
    setCustomFieldsJson("");
    setActionDraftDirty(false);
    setRule({ name: "", trigger: "status_changed", schedule_time: "09:00", schedule_frequency: "daily", schedule_weekdays: [], action: "set_priority", priority: "0", label: "", comment: "", due_days: "14", assignee_user: "", custom_field_values: "{}", assignee_filter: "", due_window: "", overdue: "", color: "#2B4EDA", statuses: "", work_types: "", approval_states: "", priority_min: "", priority_max: "", labels: "", due_set: "", release_assigned: "", component_assigned: "", blocked: "", development_providers: "", development_event_types: "", development_states: "", comment_contains: "", attachment_media_types: "", link_types: "", changed_fields: "", sprint_scope_action: "" });
  });
  const editAutomation = (row: Rule) => {
    const list = (key: string) => Array.isArray(row.conditions[key]) ? (row.conditions[key] as string[]).join(",") : "";
    setAutomationActions(row.actions?.length ? row.actions : [{ action: row.action as WorkflowAction["action"], config: row.config }]);
    setCustomFieldsJson(JSON.stringify(row.conditions.custom_field_equals ?? {}, null, 2));
    setActionDraftDirty(false);
    setRule({
      name: row.name,
      trigger: row.trigger,
      schedule_time: row.schedule_time ?? "09:00",
      schedule_frequency: row.schedule_frequency ?? "daily",
      schedule_weekdays: row.schedule_weekdays ?? [],
      action: row.actions?.at(-1)?.action ?? row.action,
      priority: String(row.config.priority ?? 0),
      label: String(row.config.text ?? ""),
      comment: String(row.config.body ?? ""),
      due_days: String(row.actions?.at(-1)?.config.days ?? 14),
      assignee_user: String(row.actions?.at(-1)?.config.user_id ?? ""),
      custom_field_values: JSON.stringify(row.actions?.at(-1)?.config.values ?? {}, null, 2),
      color: String(row.config.color ?? "#2B4EDA"),
      statuses: list("statuses"),
      work_types: list("work_types"),
      approval_states: list("approval_states"),
      priority_min: row.conditions.priority_min == null ? "" : String(row.conditions.priority_min),
      priority_max: row.conditions.priority_max == null ? "" : String(row.conditions.priority_max),
      labels: list("labels"),
      due_set: typeof row.conditions.due_set === "boolean" ? String(row.conditions.due_set) : "",
      assignee_filter: Array.isArray(row.conditions.assignee_user_ids) ? String(row.conditions.assignee_user_ids[0] ?? "") : "",
      due_window: row.conditions.due_within_days == null ? "" : String(row.conditions.due_within_days),
      overdue: typeof row.conditions.overdue === "boolean" ? String(row.conditions.overdue) : "",
      release_assigned: typeof row.conditions.release_assigned === "boolean" ? String(row.conditions.release_assigned) : "",
      component_assigned: typeof row.conditions.component_assigned === "boolean" ? String(row.conditions.component_assigned) : "",
      blocked: typeof row.conditions.blocked === "boolean" ? String(row.conditions.blocked) : "",
      development_providers: list("development_providers"),
      development_event_types: list("development_event_types"),
      development_states: list("development_states"),
      comment_contains: String(row.conditions.comment_contains ?? ""),
      attachment_media_types: list("attachment_media_types"),
      link_types: list("link_types"),
      changed_fields: list("changed_fields"),
      sprint_scope_action: list("sprint_scope_actions")[0] ?? "",
    });
    const lastAction = row.actions?.at(-1) ?? { action: row.action, config: row.config };
    if (lastAction.action === "set_priority") setRule((current) => ({ ...current, priority: String(lastAction.config.priority ?? 0) }));
    if (lastAction.action === "add_label") setRule((current) => ({ ...current, label: String(lastAction.config.text ?? ""), color: String(lastAction.config.color ?? "#2B4EDA") }));
    if (lastAction.action === "add_comment") setRule((current) => ({ ...current, comment: String(lastAction.config.body ?? "") }));
    if (lastAction.action === "set_due_after_days") setRule((current) => ({ ...current, due_days: String(lastAction.config.days ?? 14) }));
    if (lastAction.action === "assign_internal_user" || lastAction.action === "add_watcher") setRule((current) => ({ ...current, assignee_user: String(lastAction.config.user_id ?? "") }));
    setAutomationEnabled(row.enabled);
    setEditingAutomationId(row.id);
  };
  const actionsAllowed = canPlan || canCapacity || canWorkflow || canAutomation;
  return <section className="planning-page">
    <div className="section-title"><div><span className="eyebrow">Planejamento ampliado</span><h2>Releases, componentes e capacidade</h2></div><span>Versões de entrega e disponibilidade de recursos</span></div>
    <nav className="tabs" aria-label="Áreas do planejamento">
      <button aria-pressed={tab === "releases"} onClick={() => setTab("releases")}><Rocket size={16} /> Releases</button>
      <button aria-pressed={tab === "components"} onClick={() => setTab("components")}><Layers3 size={16} /> Componentes</button>
      {canCapacity && <button aria-pressed={tab === "capacity"} onClick={() => setTab("capacity")}><CalendarPlus size={16} /> Capacidade</button>}
      {canWorkflow && <button aria-pressed={tab === "workflow"} onClick={() => setTab("workflow")}>Fluxos</button>}
      {canAutomation && <button aria-pressed={tab === "automations"} onClick={() => setTab("automations")}>Automações</button>}
    </nav>
    {!actionsAllowed && <Empty>Você não tem permissão para administrar este planejamento.</Empty>}
    {tab === "releases" && <div className="planning-layout">
      <section className="panel"><h3>Versões e entregas</h3><p>Associe cards a uma entrega e registre o período previsto. Uma versão publicada fica somente leitura.</p>
        {canPlan && <div className="form-grid"><Label title="Nome da versão"><input value={release.name} onChange={(e) => setRelease({ ...release, name: e.target.value })} placeholder="Ex.: Entrega 1.0" /></Label><Label title="Descrição"><input value={release.description} onChange={(e) => setRelease({ ...release, description: e.target.value })} /></Label><Label title="Início"><input type="date" value={release.starts} onChange={(e) => setRelease({ ...release, starts: e.target.value })} /></Label><Label title="Prazo previsto"><input type="date" value={release.due} onChange={(e) => setRelease({ ...release, due: e.target.value })} /></Label><button className="primary" disabled={!release.name.trim()} onClick={saveRelease}><Plus size={16} /> Criar versão</button></div>}
      </section>
      {releases.isPending ? <Empty>Carregando versões…</Empty> : releases.isError ? <Empty>{releases.error.message}</Empty> : !releases.data.length ? <Empty>Nenhuma versão cadastrada.</Empty> : <div className="planning-list">{releases.data.map((row) => <article className="planning-item panel" key={row.id}><div><strong>{row.name}</strong><p>{row.description || "Sem descrição"}</p><small>{row.starts || "Sem início"} → {row.due || "Sem prazo"}</small><span className={row.released_at ? "badge done" : "badge todo"}>{row.released_at ? "Publicada" : "Planejada"}</span></div>{canPlan && <div className="actions">{!row.released_at && <button onClick={() => run(() => api(`/releases/${row.id}/publish?expected_version=${row.version}`, "POST"))}><Rocket size={15} /> Publicar</button>}<button className="danger" onClick={() => run(() => api(`/releases/${row.id}?expected_version=${row.version}`, "DELETE"))}><Archive size={15} /> Arquivar</button></div>}</article>)}</div>}
    </div>}
    {tab === "components" && <div className="planning-layout">
      {canPlan && <section className="panel"><h3>Novo componente</h3><div className="form-grid"><Label title="Nome"><input value={component.name} onChange={(e) => setComponent({ ...component, name: e.target.value })} /></Label><Label title="Descrição"><input value={component.description} onChange={(e) => setComponent({ ...component, description: e.target.value })} /></Label><button className="primary" disabled={!component.name.trim()} onClick={saveComponent}><Plus size={16} /> Criar componente</button></div></section>}
      {components.isPending ? <Empty>Carregando componentes…</Empty> : components.isError ? <Empty>{components.error.message}</Empty> : !components.data.length ? <Empty>Nenhum componente ativo.</Empty> : <div className="planning-list">{components.data.map((row) => <article className="planning-item panel" key={row.id}><div><strong>{row.name}</strong><p>{row.description || "Sem descrição"}</p></div>{canPlan && <button className="danger" onClick={() => run(() => api(`/components/${row.id}`, "PUT", { ...row, active: false }))}><X size={15} /> Desativar</button>}</article>)}</div>}
    </div>}
    {tab === "capacity" && canCapacity && <div className="planning-layout">
      <section className="panel"><h3>Disponibilidade planejada</h3><p>Planeje minutos disponíveis por fornecedor, pessoa interna ou equipe. A equipe usa uma cópia dos membros internos ativos no momento do cadastro, preservando a previsão histórica. A carga estimada dos cards é distribuída uniformemente pelos dias úteis entre início e prazo; a disponibilidade também é repartida igualmente no período. Se o intervalo não contiver dias úteis, são usados os dias corridos. Ao aplicar uma redistribuição, o sistema salva uma alocação diária versionada neste plano de capacidade, sem mudar prazos, horas apontadas ou custos dos cards.</p><div className="form-grid"><Label title="Tipo de recurso"><select value={capacity.resource_type} onChange={(e) => setCapacity({ ...capacity, resource_type: e.target.value, resource_id: "" })}><option value="supplier">Fornecedor</option><option value="user">Pessoa interna</option><option value="group">Equipe interna</option></select></Label><Label title={capacity.resource_type === "supplier" ? "Fornecedor" : capacity.resource_type === "user" ? "Pessoa interna" : "Equipe interna"}><select value={capacity.resource_id} onChange={(e) => setCapacity({ ...capacity, resource_id: e.target.value })}><option value="">Selecione</option>{capacity.resource_type === "supplier" ? suppliers.filter((s) => s.active).map((s) => <option value={s.id} key={s.id}>{s.name}</option>) : capacity.resource_type === "user" ? (capacityUsers.data ?? []).map((row) => <option value={row.id} key={row.id}>{row.username} · {row.role}</option>) : (capacityGroups.data ?? []).map((group) => <option value={group.id} key={group.id}>{group.name} · {group.member_count} pessoas</option>)}</select></Label><Label title="Início"><input type="date" value={capacity.starts} onChange={(e) => setCapacity({ ...capacity, starts: e.target.value })} /></Label><Label title="Término"><input type="date" value={capacity.ends} onChange={(e) => setCapacity({ ...capacity, ends: e.target.value })} /></Label><Label title="Horas disponíveis"><input type="number" min="0" step="0.25" value={capacity.hours} onChange={(e) => setCapacity({ ...capacity, hours: e.target.value })} /></Label><Label title="Observação"><input value={capacity.notes} onChange={(e) => setCapacity({ ...capacity, notes: e.target.value })} /></Label><button className="primary" disabled={!capacity.resource_id} onClick={saveCapacity}><Plus size={16} /> Registrar capacidade</button></div></section>
      {capacities.isPending ? <Empty>Carregando capacidade…</Empty> : capacities.isError ? <Empty>{capacities.error.message}</Empty> : !capacities.data.length ? <Empty>Nenhuma capacidade planejada.</Empty> : <div className="planning-list">{capacities.data.map((row) => <article className="planning-item panel" key={row.id}>
        <div>
          <strong>{row.group_id != null ? `${row.group_name ?? `Equipe ${row.group_id}`} · ${row.group_member_count ?? 0} pessoas` : row.supplier_id != null ? suppliers.find((supplier) => supplier.id === row.supplier_id)?.name ?? `Fornecedor ${row.supplier_id}` : (capacityUsers.data ?? []).find((person) => person.id === row.user_id)?.username ?? `Usuário ${row.user_id}`}</strong>
          <p>{row.starts} → {row.ends}</p>
          <small>Disponível {(row.minutes / 60).toLocaleString("pt-BR")} h · Alocado {(row.demand_minutes / 60).toLocaleString("pt-BR")} h · {row.utilization_percent == null ? "capacidade zero" : `${row.utilization_percent}% utilizado`} · {row.demand_tasks} cards</small>
          {row.leveling_plan_active && <p role="status" className="notice">Redistribuição aplicada à previsão em {new Date(row.leveling_plan_applied_at ?? "").toLocaleString("pt-BR")} · versão {row.leveling_plan_version}</p>}
          {row.leveling_plan_stale && <p role="status" className="error">A previsão aplicada ficou desatualizada após mudanças nos cards ou na capacidade. As recomendações abaixo usam os dados atuais.</p>}
          {row.overload_minutes > 0 && <p className="error" role="status">Sobrecarga atual: {(row.overload_minutes / 60).toLocaleString("pt-BR")} h · após a redistribuição sugerida: {(row.suggested_overload_minutes / 60).toLocaleString("pt-BR")} h</p>}
          {row.unplanned_tasks > 0 && <small>{row.unplanned_tasks} card(s) atribuído(s) sem período planejado, fora do cálculo de carga.</small>}
          {row.notes && <small>{row.notes}</small>}
          <div className="capacity-days" aria-label="Carga e disponibilidade por dia">
            {row.daily.map((day) => {
              const ratio = day.capacity_minutes ? Math.min(100, day.demand_minutes * 100 / day.capacity_minutes) : day.demand_minutes ? 100 : 0;
              return <div className={`capacity-day${day.overload_minutes ? " overloaded" : ""}`} key={day.date} title={`${day.date}: ${(day.demand_minutes / 60).toLocaleString("pt-BR")} h estimadas / ${(day.capacity_minutes / 60).toLocaleString("pt-BR")} h disponíveis`}>
                <small>{new Date(`${day.date}T12:00:00`).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" })}</small>
                <div className="capacity-day-track"><span style={{ width: `${ratio}%` }} /></div>
                <small>{(day.demand_minutes / 60).toLocaleString("pt-BR")} / {(day.capacity_minutes / 60).toLocaleString("pt-BR")} h · {day.task_count} cards</small>
                {day.suggested_demand_minutes !== day.demand_minutes && <small>Simulação: {(day.suggested_demand_minutes / 60).toLocaleString("pt-BR")} h</small>}
                {day.overload_minutes > 0 && <small className="error">+{(day.overload_minutes / 60).toLocaleString("pt-BR")} h</small>}
              </div>;
            })}
          </div>
          {!!row.suggested_shifts.length && <section className="capacity-recommendations" aria-label="Sugestões de redistribuição de carga">
            <strong>Cenário de redistribuição · não altera os cards</strong>
            <ul>{row.suggested_shifts.slice(0, 10).map((shift, index) => <li key={`${shift.task_id}-${shift.from_date}-${shift.to_date}-${index}`}><span>OS-{shift.task_id} · {shift.title}</span><span>{(shift.minutes / 60).toLocaleString("pt-BR")} h · {new Date(`${shift.from_date}T12:00:00`).toLocaleDateString("pt-BR")} → {new Date(`${shift.to_date}T12:00:00`).toLocaleDateString("pt-BR")}</span></li>)}</ul>
            {row.suggested_shift_count > 10 && <small>Mais {row.suggested_shift_count - 10} recomendações não exibidas nesta lista.</small>}
            {!!row.levelable_minutes && <small>Total que cabe em dias com disponibilidade dentro das janelas planejadas: {(row.levelable_minutes / 60).toLocaleString("pt-BR")} h.</small>}
            <button type="button" className="primary" onClick={() => applyLeveling(row)}>Aplicar redistribuição à previsão</button>
          </section>}
        </div>
        <button className="danger" onClick={() => run(() => api(`/capacity/${row.id}`, "DELETE"))}><X size={15} /> Remover</button>
      </article>)}</div>}
    </div>}
    {tab === "workflow" && canWorkflow && <div className="planning-layout">
      <section className="panel">
        <h3>{editingTransitionId ? "Editar transição" : "Regra adicional de transição"}</h3>
        <p>Defina a regra base e políticas específicas por tipo. A política do tipo pode substituir perfis, acrescentar campos, condições e ações; desativá-la bloqueia o tipo. Use “ao tipo selecionado” para anexar a condição/ação atual à regra do tipo escolhido. Validações nativas de horas, aprovação e permissões continuam obrigatórias.</p>
        <div className="form-grid">
          <Label title="Origem"><select value={transition.source} onChange={(e) => setTransition({ ...transition, source: e.target.value })}>{(boardColumns.data ?? []).map((column) => <option key={column.key} value={column.key}>{column.title}</option>)}</select></Label>
          <Label title="Destino"><select value={transition.target} onChange={(e) => setTransition({ ...transition, target: e.target.value })}>{(boardColumns.data ?? []).map((column) => <option key={column.key} value={column.key}>{column.title}</option>)}</select></Label>
          <Label title="Tipos atingidos pela regra base (vazio = todos)"><select multiple value={transition.work_types} onChange={(e) => setTransition({ ...transition, work_types: Array.from(e.target.selectedOptions, (option) => option.value) })}><option value="epic">Épico</option><option value="story">História</option><option value="task">Tarefa</option><option value="bug">Bug</option><option value="subtask">Subtarefa</option></select></Label>
          <Label title="Perfis permitidos na regra base (vírgulas)"><input value={transition.roles} onChange={(e) => setTransition({ ...transition, roles: e.target.value })} placeholder="admin,manager" /></Label>
          <Label title="Campos adicionais exigidos na regra base (IDs, vírgulas)"><input value={transition.required_fields} onChange={(e) => setTransition({ ...transition, required_fields: e.target.value })} placeholder="responsavel,validacao" /></Label>
        </div>
        <fieldset className="panel">
          <legend>Política específica por tipo de card</legend>
          <div className="form-grid">
            <Label title="Tipo"><select value={typeRuleDraft.type} onChange={(e) => { const type = e.target.value as WorkType; const existing = transition.type_rules[type]; setTypeRuleDraft({ type, enabled: existing?.enabled ?? true, roles: existing?.roles.join(",") ?? "", required_fields: existing?.required_fields.join(",") ?? "" }); }}><option value="epic">Épico</option><option value="story">História</option><option value="task">Tarefa</option><option value="bug">Bug</option><option value="subtask">Subtarefa</option></select></Label>
            <Label title="Perfis permitidos para este tipo (vírgulas; vazio mantém regra base)"><input value={typeRuleDraft.roles} onChange={(e) => setTypeRuleDraft({ ...typeRuleDraft, roles: e.target.value })} placeholder="admin,manager" /></Label>
            <Label title="Campos exigidos para este tipo (IDs, vírgulas)"><input value={typeRuleDraft.required_fields} onChange={(e) => setTypeRuleDraft({ ...typeRuleDraft, required_fields: e.target.value })} placeholder="criterio_aceite" /></Label>
            <label><input type="checkbox" checked={typeRuleDraft.enabled} onChange={(e) => setTypeRuleDraft({ ...typeRuleDraft, enabled: e.target.checked })} /> Permitir transição para este tipo</label>
            <button type="button" onClick={() => setTransition((current) => { const previous = current.type_rules[typeRuleDraft.type]; return { ...current, type_rules: { ...current.type_rules, [typeRuleDraft.type]: { enabled: typeRuleDraft.enabled, roles: typeRuleDraft.roles.split(",").map((value) => value.trim()).filter(Boolean), required_fields: typeRuleDraft.required_fields.split(",").map((value) => value.trim()).filter(Boolean), conditions: previous?.conditions ?? [], actions: previous?.actions ?? [] } } }; })}><Plus size={16} /> Adicionar/atualizar tipo</button>
          </div>
          {Object.entries(transition.type_rules).length > 0 && <ul>{Object.entries(transition.type_rules).map(([type, policy]) => <li key={type}>{type}: {policy?.enabled ? "permitida" : "bloqueada"} · perfis {policy?.roles.length ? policy.roles.join(", ") : "base"} · campos {policy?.required_fields.join(", ") || "nenhum"} · condições {policy?.conditions?.map((condition) => conditionSummary(condition, workflowAssignees.data ?? [])).join("; ") || "nenhuma"} · ações {policy?.actions?.map((action) => actionSummary(action, workflowAssignees.data ?? [])).join("; ") || "nenhuma"} <button type="button" onClick={() => setTransition((current) => { const type_rules = { ...current.type_rules }; delete type_rules[type as WorkType]; return { ...current, type_rules }; })}>Remover</button></li>)}</ul>}
        </fieldset>
        <fieldset className="panel">
          <legend>Condições da transição</legend>
          <p>O card só avança quando todas as condições abaixo forem verdadeiras. As validações nativas de horas e aprovação continuam valendo.</p>
          <div className="form-grid">
            <Label title="Campo"><select value={conditionDraft.field} onChange={(event) => { const field = event.target.value as WorkflowCondition["field"]; const value = field === "approval" ? "approved" : field === "work_type" ? "task" : field === "priority" ? 0 : field === "label" ? "Urgente" : field === "assignee" ? Number(workflowAssignees.data?.[0]?.id ?? 0) : field === "due_within_days" ? 7 : field === "custom_field_equals" ? "" : true; if (field === "custom_field_equals") setWorkflowCustomFieldDraft({ id: "", value: '""' }); setConditionDraft({ field, operator: "eq", value, ...(field === "custom_field_equals" ? { custom_field_id: "" } : {}) }); }}><option value="approval">Aprovação</option><option value="work_type">Tipo de card</option><option value="priority">Prioridade</option><option value="supplier_assigned">Fornecedor atribuído</option><option value="label">Etiqueta</option><option value="due_set">Prazo definido</option><option value="due_overdue">Prazo vencido</option><option value="due_within_days">Prazo nos próximos dias</option><option value="parent_set">Card filho</option><option value="assignee">Responsável interno</option><option value="release_assigned">Release vinculada</option><option value="component_assigned">Componente vinculado</option><option value="blocked">Bloqueado por dependência ativa</option><option value="custom_field_equals">Campo personalizado</option></select></Label>
            <Label title="Regra"><select value={conditionDraft.operator} onChange={(event) => setConditionDraft({ ...conditionDraft, operator: event.target.value as WorkflowCondition["operator"] })}><option value="eq">É igual a</option><option value="not_eq">É diferente de</option>{conditionDraft.field === "priority" && <><option value="gte">Maior ou igual</option><option value="lte">Menor ou igual</option></>}</select></Label>
            <Label title="Valor">{conditionDraft.field === "custom_field_equals" ? <div className="form-grid"><input aria-label="ID do campo personalizado" value={workflowCustomFieldDraft.id} onChange={(event) => { const id = event.target.value; setWorkflowCustomFieldDraft((current) => ({ ...current, id })); setConditionDraft((current) => ({ ...current, custom_field_id: id })); }} placeholder="Ex.: area" /><input aria-label="Valor esperado em JSON" value={workflowCustomFieldDraft.value} onChange={(event) => setWorkflowCustomFieldDraft((current) => ({ ...current, value: event.target.value }))} placeholder={'"Operações", true ou 8'} /><small>Valor JSON simples: texto entre aspas, número ou booleano. Campos inexistentes no card não permitem a transição.</small></div> : conditionDraft.field === "approval" ? <select value={String(conditionDraft.value)} onChange={(event) => setConditionDraft({ ...conditionDraft, value: event.target.value })}><option value="pending">Pendente</option><option value="approved">Aprovada</option><option value="rejected">Rejeitada</option><option value="resubmitted">Reapresentada</option></select> : conditionDraft.field === "work_type" ? <select value={String(conditionDraft.value)} onChange={(event) => setConditionDraft({ ...conditionDraft, value: event.target.value })}><option value="epic">Épico</option><option value="story">História</option><option value="task">Tarefa</option><option value="bug">Bug</option><option value="subtask">Subtarefa</option></select> : conditionDraft.field === "due_within_days" ? <input type="number" min="0" max="3650" step="1" value={Number(conditionDraft.value)} onChange={(event) => setConditionDraft({ ...conditionDraft, value: Number(event.target.value) })} /> : conditionDraft.field === "priority" ? <input type="number" value={Number(conditionDraft.value)} onChange={(event) => setConditionDraft({ ...conditionDraft, value: Number(event.target.value) })} /> : conditionDraft.field === "label" ? <input maxLength={40} value={String(conditionDraft.value)} onChange={(event) => setConditionDraft({ ...conditionDraft, value: event.target.value })} /> : conditionDraft.field === "assignee" ? <select value={String(conditionDraft.value)} onChange={(event) => setConditionDraft({ ...conditionDraft, value: Number(event.target.value) })}><option value="0">Selecione uma pessoa</option>{(workflowAssignees.data ?? []).map((person) => <option key={person.id} value={person.id}>{person.username}</option>)}</select> : <select value={String(conditionDraft.value)} onChange={(event) => setConditionDraft({ ...conditionDraft, value: event.target.value === "true" })}><option value="true">Sim</option><option value="false">Não</option></select>}</Label>
            <button type="button" disabled={!workflowConditionValid || (conditionDraft.field === "assignee" && Number(conditionDraft.value) <= 0)} onClick={() => setTransition((current) => ({ ...current, conditions: [...current.conditions, buildWorkflowCondition()] }))}><Plus size={16} /> Adicionar condição base</button>
            <button type="button" disabled={!workflowConditionValid || !transition.type_rules[typeRuleDraft.type] || (conditionDraft.field === "assignee" && Number(conditionDraft.value) <= 0)} onClick={addTypeCondition}><Plus size={16} /> Adicionar ao tipo selecionado</button>
          </div>
          {transition.conditions.length > 0 && <ul>{transition.conditions.map((condition, index) => <li key={`${condition.field}-${index}`}>{conditionSummary(condition, workflowAssignees.data ?? [])} <button type="button" onClick={() => setTransition((current) => ({ ...current, conditions: current.conditions.filter((_, itemIndex) => itemIndex !== index) }))}>Remover</button></li>)}</ul>}
        </fieldset>
        <fieldset className="panel">
          <legend>Ações após a transição</legend>
          <div className="form-grid">
            <Label title="Ação"><select value={actionDraft.action} onChange={(event) => setActionDraft({ ...actionDraft, action: event.target.value as WorkflowAction["action"] })}><option value="add_comment">Adicionar comentário</option><option value="add_label">Adicionar etiqueta</option><option value="remove_label">Remover etiqueta</option><option value="set_priority">Definir prioridade</option><option value="set_due_after_days">Definir prazo após criação</option><option value="assign_internal_user">Atribuir responsável interno</option><option value="add_watcher">Adicionar observador interno</option><option value="set_custom_fields">Definir campos personalizados</option></select></Label>
            {actionDraft.action === "add_label" || actionDraft.action === "remove_label" ? <Label title="Texto da etiqueta"><input maxLength={40} value={actionDraft.value} onChange={(event) => setActionDraft({ ...actionDraft, value: event.target.value })} /></Label> : null}
            {actionDraft.action === "add_label" && <Label title="Cor da etiqueta"><input type="color" value={actionDraft.color} onChange={(event) => setActionDraft({ ...actionDraft, color: event.target.value })} /></Label>}
            {actionDraft.action === "add_comment" && <Label title="Comentário"><textarea maxLength={1000} rows={3} value={actionDraft.value} onChange={(event) => setActionDraft({ ...actionDraft, value: event.target.value })} /></Label>}
            {actionDraft.action === "set_priority" && <Label title="Prioridade numérica"><input type="number" value={actionDraft.value} onChange={(event) => setActionDraft({ ...actionDraft, value: event.target.value })} /></Label>}
            {actionDraft.action === "set_due_after_days" && <Label title="Dias corridos após a criação (0 a 3.650)"><input type="number" min="0" max="3650" value={actionDraft.value} onChange={(event) => setActionDraft({ ...actionDraft, value: event.target.value })} /></Label>}
            {(actionDraft.action === "assign_internal_user" || actionDraft.action === "add_watcher") && <Label title={actionDraft.action === "add_watcher" ? "Observador interno" : "Responsável interno"}><select value={actionDraft.value} onChange={(event) => setActionDraft({ ...actionDraft, value: event.target.value })}><option value="">Selecione uma pessoa</option>{(workflowAssignees.data ?? []).map((person) => <option key={person.id} value={person.id}>{person.username}</option>)}</select></Label>}
            {actionDraft.action === "set_custom_fields" && <Label title="Valores por ID do campo (JSON)"><textarea rows={4} value={actionDraft.custom_field_values} onChange={(event) => setActionDraft({ ...actionDraft, custom_field_values: event.target.value })} placeholder={'{"area": "Operações"}'} /><small>Atualiza somente campos simples já configurados e editáveis. A mudança cria uma nova versão do card e entra no histórico de auditoria.</small></Label>}
            <button type="button" disabled={!workflowActionValid} onClick={addWorkflowAction}><Plus size={16} /> Adicionar ação base</button>
            <button type="button" disabled={!workflowActionValid || !transition.type_rules[typeRuleDraft.type]} onClick={addTypeWorkflowAction}><Plus size={16} /> Adicionar ao tipo selecionado</button>
          </div>
          {transition.actions.length > 0 && <ul>{transition.actions.map((action, index) => <li key={`${action.action}-${index}`}>{actionSummary(action, workflowAssignees.data ?? [])} <button type="button" onClick={() => setTransition((current) => ({ ...current, actions: current.actions.filter((_, itemIndex) => itemIndex !== index) }))}>Remover</button></li>)}</ul>}
        </fieldset>
        <div className="actions"><button className="primary" onClick={saveTransition}><Plus size={16} /> {editingTransitionId ? "Salvar transição" : "Adicionar transição"}</button>{editingTransitionId && <button onClick={() => setEditingTransitionId(null)}>Cancelar edição</button>}</div>
      </section>
      {transitions.isPending ? <Empty>Carregando transições…</Empty> : transitions.isError ? <Empty>{transitions.error.message}</Empty> : <div className="planning-list">{transitions.data.map((row) => <article className="planning-item panel" key={row.id}><div><strong>{row.source} → {row.target}</strong><p>Regra base · perfis: {row.roles.length ? row.roles.join(", ") : "fluxo padrão"} · tipos: {row.work_types.length ? row.work_types.join(", ") : "todos"}</p><small>Campos base: {row.required_fields.join(", ") || "nenhum"} · condições: {row.conditions?.length ?? 0} · ações: {row.actions?.length ?? 0}</small>{Object.entries(row.type_rules ?? {}).map(([type, policy]) => <small key={type}>{type}: {policy.enabled ? "permitida" : "bloqueada"} · perfis {policy.roles.join(", ") || "base"} · campos {policy.required_fields.join(", ") || "nenhum"}</small>)}</div><div className="actions"><button onClick={() => editTransition(row)}>Editar</button><button onClick={() => run(() => api(`/workflows/transitions/${row.id}`, "PUT", { ...row, enabled: !row.enabled }))}>{row.enabled ? "Desativar" : "Ativar"}</button><button className="danger" onClick={() => run(() => api(`/workflows/transitions/${row.id}`, "DELETE"))}><X size={15} /> Remover</button></div></article>)}</div>}
    </div>}
    {tab === "automations" && canAutomation && <div className="planning-layout">
      <section className="panel">
        <h3>{editingAutomationId ? "Editar automação" : "Criar automação"}</h3>
        <p>Regras seguras rodam em eventos de cards e sprints (incluindo entrada e retorno ao backlog) ou diariamente no horário UTC definido. Comentários podem ser filtrados por trecho de texto e anexos por tipo de mídia. Os filtros gerais também consideram status, aprovação, prioridade, responsável, release, componente e dependências bloqueadoras. Cada regra pode encadear até dez ações ordenadas.</p>
        <div className="form-grid">
          <Label title="Nome"><input value={rule.name} onChange={(e) => setRule({ ...rule, name: e.target.value })} /></Label>
          <Label title="Gatilho"><select value={rule.trigger} onChange={(e) => setRule({ ...rule, trigger: e.target.value })}><option value="card_created">Card criado</option><option value="task_updated">Card editado</option><option value="field_changed">Campo específico alterado</option><option value="assignee_changed">Responsável ou fornecedor alterado</option><option value="due_changed">Prazo alterado</option><option value="priority_changed">Prioridade alterada</option><option value="status_changed">Etapa alterada</option><option value="comment_added">Comentário adicionado</option><option value="attachment_added">Anexo adicionado</option><option value="link_added">Relação entre cards criada</option><option value="link_removed">Relação entre cards removida</option><option value="hours_submitted">Horas enviadas</option><option value="hours_decided">Horas aprovadas/rejeitadas</option><option value="sprint_started">Sprint iniciada</option><option value="sprint_completed">Sprint encerrada</option><option value="sprint_scope_changed">Card adicionado/removido da sprint</option><option value="development_event">Evento de GitHub, GitLab ou Bitbucket</option><option value="scheduled_daily">Agendamento recorrente</option></select></Label>
          {rule.trigger === "sprint_scope_changed" && <Label title="Filtrar mudança de escopo"><select value={rule.sprint_scope_action} onChange={(e) => setRule({ ...rule, sprint_scope_action: e.target.value })}><option value="">Adicionada ou removida</option><option value="added">Adicionada</option><option value="removed">Removida</option></select></Label>}
          {rule.trigger === "field_changed" && <Label title="Campos que disparam (opcional; separados por vírgula)"><input value={rule.changed_fields} onChange={(e) => setRule({ ...rule, changed_fields: e.target.value })} placeholder="priority, due, area" /><small>Use IDs de campos estruturais ou personalizados. Vazio significa qualquer campo alterado.</small></Label>}
          {rule.trigger === "comment_added" && <Label title="Executar somente se o comentário contiver (opcional)"><input maxLength={200} value={rule.comment_contains} onChange={(e) => setRule({ ...rule, comment_contains: e.target.value })} placeholder="Ex.: urgente" /></Label>}
          {rule.trigger === "attachment_added" && <Label title="Tipos de mídia permitidos (opcional, separados por vírgula)"><input value={rule.attachment_media_types} onChange={(e) => setRule({ ...rule, attachment_media_types: e.target.value })} placeholder="application/pdf, image/png" /><small>Permitidos: PDF, PNG, JPEG e texto simples.</small></Label>}
          {["link_added", "link_removed"].includes(rule.trigger) && <Label title="Tipos de relação (opcional, separados por vírgula)"><input value={rule.link_types} onChange={(e) => setRule({ ...rule, link_types: e.target.value })} placeholder="blocks, relates, duplicates" /><small>Use: blocks, relates ou duplicates.</small></Label>}
          {rule.trigger === "scheduled_daily" && <Label title="Horário da rotina (UTC)"><input type="time" value={rule.schedule_time} onChange={(e) => setRule({ ...rule, schedule_time: e.target.value })} /></Label>}
          {rule.trigger === "scheduled_daily" && <Label title="Recorrência"><select value={rule.schedule_frequency} onChange={(e) => setRule({ ...rule, schedule_frequency: e.target.value as "daily" | "weekly", schedule_weekdays: e.target.value === "weekly" ? rule.schedule_weekdays : [] })}><option value="daily">Todos os dias</option><option value="weekly">Semanalmente</option></select></Label>}
          {rule.trigger === "scheduled_daily" && rule.schedule_frequency === "weekly" && <fieldset className="automation-weekdays"><legend>Executar nestes dias (UTC)</legend>{weekdayOptions.map((day, index) => <label key={day}><input type="checkbox" checked={rule.schedule_weekdays.includes(index)} onChange={(event) => setRule({ ...rule, schedule_weekdays: event.target.checked ? [...rule.schedule_weekdays, index].sort() : rule.schedule_weekdays.filter((value) => value !== index) })} />{day}</label>)}</fieldset>}
          {rule.trigger === "development_event" && <>
            <Label title="Provedores (opcional; separados por vírgula)"><input value={rule.development_providers} onChange={(e) => setRule({ ...rule, development_providers: e.target.value })} placeholder="github, gitlab, bitbucket" /></Label>
            <Label title="Tipos de evento (opcional; separados por vírgula)"><input value={rule.development_event_types} onChange={(e) => setRule({ ...rule, development_event_types: e.target.value })} placeholder="push, pull_request, workflow_run" /></Label>
            <Label title="Estados (opcional; separados por vírgula)"><input value={rule.development_states} onChange={(e) => setRule({ ...rule, development_states: e.target.value })} placeholder="success, failure, merged" /></Label>
          </>}
          <Label title="Ação que está sendo configurada"><select value={rule.action} onChange={(e) => { setRule({ ...rule, action: e.target.value }); setActionDraftDirty(true); }}><option value="set_priority">Definir prioridade</option><option value="add_label">Adicionar etiqueta</option><option value="remove_label">Remover etiqueta</option><option value="add_comment">Adicionar comentário</option><option value="set_due_after_days">Definir prazo após criação</option><option value="assign_internal_user">Atribuir responsável interno</option><option value="add_watcher">Adicionar observador interno</option><option value="set_custom_fields">Definir campos personalizados</option></select></Label>
          {rule.action === "set_custom_fields" ? <Label title="Valores por ID do campo (JSON)"><textarea rows={4} value={rule.custom_field_values} onChange={(e) => { setRule({ ...rule, custom_field_values: e.target.value }); setActionDraftDirty(true); }} placeholder={'{"area": "Operações"}'} /><small>Atualiza campos simples existentes e permitidos para o perfil da regra. Cada alteração fica versionada e auditada.</small></Label> : rule.action === "set_priority" ? <Label title="Prioridade numérica"><input type="number" value={rule.priority} onChange={(e) => { setRule({ ...rule, priority: e.target.value }); setActionDraftDirty(true); }} /></Label> : rule.action === "add_label" || rule.action === "remove_label" ? <><Label title="Texto da etiqueta"><input maxLength={40} value={rule.label} onChange={(e) => { setRule({ ...rule, label: e.target.value }); setActionDraftDirty(true); }} /></Label>{rule.action === "add_label" && <Label title="Cor"><input type="color" value={rule.color} onChange={(e) => { setRule({ ...rule, color: e.target.value }); setActionDraftDirty(true); }} /></Label>}</> : rule.action === "set_due_after_days" ? <Label title="Dias corridos após a criação (0 a 3.650)"><input type="number" min="0" max="3650" value={rule.due_days} onChange={(e) => { setRule({ ...rule, due_days: e.target.value }); setActionDraftDirty(true); }} /></Label> : rule.action === "assign_internal_user" || rule.action === "add_watcher" ? <Label title={rule.action === "add_watcher" ? "Observador interno" : "Responsável interno"}><select value={rule.assignee_user} onChange={(e) => { setRule({ ...rule, assignee_user: e.target.value }); setActionDraftDirty(true); }}><option value="">Selecione uma pessoa</option>{(workflowAssignees.data ?? []).map((person) => <option key={person.id} value={person.id}>{person.username}</option>)}</select></Label> : <Label title="Comentário automático"><textarea maxLength={1000} rows={3} value={rule.comment} onChange={(e) => { setRule({ ...rule, comment: e.target.value }); setActionDraftDirty(true); }} /></Label>}
          <section className="automation-action-sequence" aria-label="Sequência de ações">
            <strong>Sequência da regra · {automationActions.length} ação(ões)</strong>
            {automationActions.length > 0 && <ol>{automationActions.map((action, index) => <li key={`${action.action}-${index}`}>{index + 1}. {automationActionSummary(action, workflowAssignees.data ?? [])} <button type="button" onClick={() => removeAutomationAction(index)}>Remover</button></li>)}</ol>}
            <button type="button" disabled={(!actionDraftDirty && automationActions.length > 0) || (rule.action === "set_custom_fields" ? !validCustomFieldValues(rule.custom_field_values) : (["assign_internal_user", "add_watcher"].includes(rule.action) && !rule.assignee_user))} onClick={appendAutomationAction}><Plus size={16} /> Adicionar ação configurada à sequência</button>
          </section>
          <Label title="Somente nestes status (opcional, vírgulas)"><input value={rule.statuses} onChange={(e) => setRule({ ...rule, statuses: e.target.value })} placeholder="todo,production" /></Label>
          <Label title="Somente nestes tipos (opcional, vírgulas)"><input value={rule.work_types} onChange={(e) => setRule({ ...rule, work_types: e.target.value })} placeholder="bug,task" /></Label>
          <Label title="Somente nestes estados de aprovação (opcional)"><input value={rule.approval_states} onChange={(e) => setRule({ ...rule, approval_states: e.target.value })} placeholder="approved,rejected" /></Label>
          <Label title="Prioridade mínima (opcional)"><input type="number" value={rule.priority_min} onChange={(e) => setRule({ ...rule, priority_min: e.target.value })} /></Label>
          <Label title="Prioridade máxima (opcional)"><input type="number" value={rule.priority_max} onChange={(e) => setRule({ ...rule, priority_max: e.target.value })} /></Label>
          <Label title="Exige uma destas etiquetas (opcional, vírgulas)"><input value={rule.labels} onChange={(e) => setRule({ ...rule, labels: e.target.value })} placeholder="Urgente, UX" /></Label>
          <Label title="Filtro de prazo"><select value={rule.due_set} onChange={(e) => setRule({ ...rule, due_set: e.target.value })}><option value="">Com ou sem prazo</option><option value="true">Somente cards com prazo</option><option value="false">Somente cards sem prazo</option></select></Label>
          <Label title="Prazo nos próximos dias (UTC, opcional)"><input type="number" min="0" max="3650" value={rule.due_window} onChange={(e) => setRule({ ...rule, due_window: e.target.value })} placeholder="Ex.: 7" /></Label>
          <Label title="Situação de atraso"><select value={rule.overdue} onChange={(e) => setRule({ ...rule, overdue: e.target.value })}><option value="">Qualquer situação</option><option value="true">Somente atrasados</option><option value="false">Somente não atrasados</option></select></Label>
          <Label title="Filtro de release"><select value={rule.release_assigned} onChange={(e) => setRule({ ...rule, release_assigned: e.target.value })}><option value="">Com ou sem release</option><option value="true">Somente cards vinculados a release</option><option value="false">Somente cards sem release</option></select></Label>
          <Label title="Filtro de componente"><select value={rule.component_assigned} onChange={(e) => setRule({ ...rule, component_assigned: e.target.value })}><option value="">Com ou sem componente</option><option value="true">Somente cards com componente</option><option value="false">Somente cards sem componente</option></select></Label>
          <Label title="Filtro de dependência"><select value={rule.blocked} onChange={(e) => setRule({ ...rule, blocked: e.target.value })}><option value="">Bloqueados ou não</option><option value="true">Somente bloqueados por item pendente</option><option value="false">Somente não bloqueados</option></select></Label>
          <Label title="Campos personalizados por ID e valor (JSON, opcional)"><textarea rows={3} value={customFieldsJson} onChange={(event) => setCustomFieldsJson(event.target.value)} placeholder={'{"area": "Operações", "urgente": true}'} /><small>Use até 10 campos já definidos no card. Os valores são comparados por tipo e não são incluídos na auditoria da automação.</small></Label>
          <Label title="Filtrar por responsável interno"><select value={rule.assignee_filter} onChange={(e) => setRule({ ...rule, assignee_filter: e.target.value })}><option value="">Qualquer responsável</option>{(workflowAssignees.data ?? []).map((person) => <option key={person.id} value={person.id}>{person.username}</option>)}</select></Label>
          <button className="primary" disabled={!rule.name.trim() || (!!editingAutomationId && !automationActions.length && !actionDraftDirty)} onClick={saveAutomation}><Plus size={16} /> {editingAutomationId ? "Salvar alterações" : "Criar automação"}</button>
          {editingAutomationId && <button type="button" onClick={() => { setCustomFieldsJson(""); setEditingAutomationId(null); setAutomationEnabled(true); setAutomationActions([]); setActionDraftDirty(false); setRule({ name: "", trigger: "status_changed", schedule_time: "09:00", schedule_frequency: "daily", schedule_weekdays: [], action: "set_priority", priority: "0", label: "", comment: "", due_days: "14", assignee_user: "", custom_field_values: "{}", assignee_filter: "", due_window: "", overdue: "", color: "#2B4EDA", statuses: "", work_types: "", approval_states: "", priority_min: "", priority_max: "", labels: "", due_set: "", release_assigned: "", component_assigned: "", blocked: "", development_providers: "", development_event_types: "", development_states: "", comment_contains: "", attachment_media_types: "", link_types: "", changed_fields: "", sprint_scope_action: "" }); }}>Cancelar edição</button>}
        </div>
      </section>
      <section className="panel automation-run-log">
        <div className="section-heading"><div><h3>Histórico de execuções</h3><p>Registro recente das ações automáticas, atualizado periodicamente. Valores de campos e comentários não são exibidos.</p></div></div>
        {automationRuns.isPending ? <Empty>Carregando execuções…</Empty> : automationRuns.isError ? <Empty>{automationRuns.error.message}</Empty> : !automationRuns.data.length ? <Empty>Nenhuma execução registrada ainda.</Empty> : <div className="planning-list">{automationRuns.data.map((entry) => <article className="planning-item" key={entry.id}><div><strong>{entry.rule_name} · {entry.task_key}</strong><p>{entry.task_title}</p><small>{new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(entry.created_at))} · {entry.actor_name} · gatilho: {entry.trigger}</small><small>{entry.changed_fields.length ? `Campos alterados: ${entry.changed_fields.join(", ")}` : "Sem alteração de campo"}{entry.comments_added ? ` · ${entry.comments_added} comentário(s)` : ""}{entry.watchers_added ? ` · ${entry.watchers_added} observador(es)` : ""}{entry.skipped_actions ? ` · ${entry.skipped_actions} ação(ões) ignorada(s)` : ""}</small></div></article>)}</div>}
        <div className="actions"><button disabled={automationRunOffset === 0} onClick={() => setAutomationRunOffset((value) => Math.max(0, value - 25))}>Mais recentes</button><button disabled={!automationRuns.data || automationRuns.data.length < 25} onClick={() => setAutomationRunOffset((value) => value + 25)}>Anteriores</button></div>
      </section>
        {automations.isPending ? <Empty>Carregando automações…</Empty> : automations.isError ? <Empty>{automations.error.message}</Empty> : !automations.data.length ? <Empty>Nenhuma automação configurada.</Empty> : <div className="planning-list">{automations.data.map((row) => <article className="planning-item panel" key={row.id}><div><strong>{row.name}</strong><p>{{card_created:"Card criado",task_updated:"Card editado",field_changed:"Campo específico alterado",assignee_changed:"Responsável ou fornecedor alterado",due_changed:"Prazo alterado",priority_changed:"Prioridade alterada",status_changed:"Etapa alterada",comment_added:"Comentário adicionado",attachment_added:"Anexo adicionado",link_added:"Relação criada",link_removed:"Relação removida",hours_submitted:"Horas enviadas",hours_decided:"Horas decididas",sprint_started:"Sprint iniciada",sprint_completed:"Sprint encerrada",sprint_scope_changed:"Card adicionado/removido da sprint",development_event:"Evento de desenvolvimento",scheduled_daily:row.schedule_frequency === "weekly" ? `Semanal às ${row.schedule_time ?? "--:--"} UTC · ${(row.schedule_weekdays ?? []).map((day) => weekdayOptions[day]).join(", ")}` : `Diária às ${row.schedule_time ?? "--:--"} UTC`}[row.trigger] ?? row.trigger} · {(row.actions?.length ? row.actions : [{ action: row.action as WorkflowAction["action"], config: row.config }]).map((action) => automationActionSummary(action, workflowAssignees.data ?? [])).join(" → ")}</p><small>{row.enabled ? "Ativa" : "Desativada"}</small></div><div className="actions"><button onClick={() => editAutomation(row)}>Editar</button><button onClick={() => run(() => api(`/automations/${row.id}`, "PUT", { ...row, enabled: !row.enabled }))}>{row.enabled ? "Desativar" : "Ativar"}</button><button className="danger" onClick={() => run(() => api(`/automations/${row.id}`, "DELETE"))}><X size={15} /> Remover</button></div></article>)}</div>}
    </div>}
  </section>;
}
