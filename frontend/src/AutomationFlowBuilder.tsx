import { useState, type Dispatch, type SetStateAction } from "react";
import { ArrowDown, ArrowLeft, ArrowUp, CalendarClock, Check, CircleHelp, GitBranch, GripVertical, ListChecks, Plus, Settings2, Trash2, X, Zap } from "lucide-react";
import type { AutomationRuleDraft, CapacityUser, WorkflowAction } from "./automationTypes";

type Pane = "trigger" | "conditions" | "action" | "details" | null;
type Props = {
  rule: AutomationRuleDraft;
  setRule: Dispatch<SetStateAction<AutomationRuleDraft>>;
  actions: WorkflowAction[];
  setActions: Dispatch<SetStateAction<WorkflowAction[]>>;
  enabled: boolean;
  setEnabled: Dispatch<SetStateAction<boolean>>;
  actionDraftDirty: boolean;
  setActionDraftDirty: Dispatch<SetStateAction<boolean>>;
  customFieldsJson: string;
  setCustomFieldsJson: Dispatch<SetStateAction<string>>;
  users: CapacityUser[];
  editingId: number | null;
  onSave: () => void;
  onCancel: () => void;
};

const triggerOptions = [
  ["card_created", "Card criado"], ["task_updated", "Card editado"], ["field_changed", "Valor do campo alterado"],
  ["assignee_changed", "Responsável ou fornecedor alterado"], ["due_changed", "Prazo alterado"],
  ["priority_changed", "Prioridade alterada"], ["status_changed", "Card transicionado"],
  ["comment_added", "Comentário adicionado"], ["attachment_added", "Anexo adicionado"],
  ["link_added", "Relação entre cards criada"], ["link_removed", "Relação entre cards removida"],
  ["hours_submitted", "Horas enviadas"], ["hours_decided", "Horas aprovadas ou rejeitadas"],
  ["sprint_started", "Sprint iniciada"], ["sprint_completed", "Sprint encerrada"],
  ["sprint_scope_changed", "Card adicionado ou removido da sprint"],
  ["development_event", "Evento de desenvolvimento"], ["scheduled_daily", "Agendamento recorrente"],
] as const;

const actionOptions: Array<[WorkflowAction["action"], string]> = [
  ["set_priority", "Definir prioridade"], ["add_label", "Adicionar etiqueta"], ["remove_label", "Remover etiqueta"],
  ["add_comment", "Adicionar comentário"], ["set_due_after_days", "Definir prazo após criação"],
  ["assign_internal_user", "Atribuir responsável interno"], ["add_watcher", "Adicionar observador interno"],
  ["set_custom_fields", "Atualizar campos personalizados"],
];

const actionTitle = (action: WorkflowAction, users: CapacityUser[]) => {
  const config = action.config;
  if (action.action === "set_priority") return `Definir prioridade para ${config.priority}`;
  if (action.action === "add_label") return `Adicionar etiqueta “${config.text}”`;
  if (action.action === "remove_label") return `Remover etiqueta “${config.text}”`;
  if (action.action === "set_due_after_days") return `Definir prazo em ${config.days} dias`;
  if (action.action === "assign_internal_user" || action.action === "add_watcher") {
    const person = users.find((user) => user.id === Number(config.user_id));
    return `${action.action === "add_watcher" ? "Adicionar observador" : "Atribuir responsável"}${person ? ` · ${person.username}` : ""}`;
  }
  if (action.action === "set_custom_fields") return `Atualizar ${Object.keys((config.values as Record<string, unknown>) ?? {}).length} campo(s)`;
  return `Adicionar comentário · ${String(config.body ?? "").slice(0, 58) || "sem texto"}`;
};

const conditionCount = (rule: AutomationRuleDraft, customFieldsJson: string) => [
  rule.statuses, rule.work_types, rule.approval_states, rule.priority_min, rule.priority_max, rule.labels,
  rule.due_set, rule.assignee_filter, rule.due_window, rule.overdue, rule.release_assigned,
  rule.component_assigned, rule.blocked, rule.development_providers, rule.development_event_types,
  rule.development_states, rule.comment_contains, rule.attachment_media_types, rule.link_types,
  rule.changed_fields, rule.sprint_scope_action, customFieldsJson.trim() && customFieldsJson !== "{}",
].filter((value) => value !== "" && value !== false).length;

export function AutomationFlowBuilder({ rule, setRule, actions, setActions, enabled, setEnabled, actionDraftDirty, setActionDraftDirty, customFieldsJson, setCustomFieldsJson, users, editingId, onSave, onCancel }: Props) {
  const [pane, setPane] = useState<Pane>(() => editingId === null ? "trigger" : null);
  const [editingAction, setEditingAction] = useState<number | null>(null);
  const [triggerSearch, setTriggerSearch] = useState("");
  const [actionSearch, setActionSearch] = useState("");
  const [jsonError, setJsonError] = useState("");
  const conditions = conditionCount(rule, customFieldsJson);
  const update = (key: keyof AutomationRuleDraft, value: string | number | number[] | "daily" | "weekly") => setRule((current) => ({ ...current, [key]: value }));

  const openNewAction = () => {
    setEditingAction(null);
    setRule((current) => ({ ...current, action: "add_comment", comment: "", label: "", assignee_user: "", custom_field_values: "{}" }));
    setActionDraftDirty(true);
    setPane("action");
  };
  const openAction = (index: number) => {
    const row = actions[index];
    setEditingAction(index);
    const config = row.config;
    setRule((current) => ({
      ...current,
      action: row.action,
      priority: String(config.priority ?? 0),
      label: String(config.text ?? ""),
      comment: String(config.body ?? ""),
      due_days: String(config.days ?? 14),
      assignee_user: String(config.user_id ?? ""),
      custom_field_values: JSON.stringify(config.values ?? {}, null, 2),
      color: String(config.color ?? "#2B4EDA"),
    }));
    setActionDraftDirty(false);
    setJsonError("");
    setPane("action");
  };
  const buildAction = (): WorkflowAction => {
    const config: WorkflowAction["config"] = rule.action === "set_priority" ? { priority: Number(rule.priority) }
      : rule.action === "add_label" ? { text: rule.label.trim(), color: rule.color }
        : rule.action === "remove_label" ? { text: rule.label.trim() }
          : rule.action === "set_due_after_days" ? { days: Number(rule.due_days) }
            : rule.action === "assign_internal_user" || rule.action === "add_watcher" ? { user_id: Number(rule.assignee_user) }
              : rule.action === "set_custom_fields" ? { values: JSON.parse(rule.custom_field_values) as Record<string, unknown> }
                : { body: rule.comment.trim() };
    return { action: rule.action, config };
  };
  const commitAction = () => {
    if (rule.action === "set_custom_fields") {
      try { JSON.parse(rule.custom_field_values); setJsonError(""); } catch { setJsonError("Informe um JSON válido antes de adicionar a ação."); return; }
    }
    if (["add_label", "remove_label"].includes(rule.action) && !rule.label.trim()) return;
    if (rule.action === "add_comment" && !rule.comment.trim()) return;
    if (["assign_internal_user", "add_watcher"].includes(rule.action) && !rule.assignee_user) return;
    if (rule.action === "set_due_after_days" && (!Number.isInteger(Number(rule.due_days)) || Number(rule.due_days) < 0 || Number(rule.due_days) > 3650)) return;
    const next = buildAction();
    if (editingAction === null && actions.length >= 10) return;
    setActions((current) => editingAction === null ? [...current, next] : current.map((item, index) => index === editingAction ? next : item));
    setActionDraftDirty(false);
    setEditingAction(null);
    setPane(null);
  };
  const moveAction = (index: number, direction: -1 | 1) => setActions((current) => {
    const target = index + direction;
    if (target < 0 || target >= current.length) return current;
    const next = [...current];
    [next[index], next[target]] = [next[target], next[index]];
    return next;
  });
  const reorderAction = (from: number, to: number) => setActions((current) => {
    if (from < 0 || from >= current.length || to < 0 || to >= current.length || from === to) return current;
    const next = [...current];
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    return next;
  });

  return <div className="automation-studio">
    <header className="automation-studio-header">
      <button type="button" className="quiet-button automation-back" onClick={onCancel} aria-label="Voltar para automações"><ArrowLeft size={18} /> Automações</button>
      <div className="automation-title-input"><Zap size={18} /><input aria-label="Nome da automação" value={rule.name} onChange={(event) => update("name", event.target.value)} placeholder={editingId ? "Nome do fluxo" : "Fluxo sem título"} maxLength={120} /></div>
      <button type="button" className="quiet-button" onClick={() => setPane("details")}><Settings2 size={17} /> Detalhes</button>
      <label className="automation-enabled-switch"><input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} /> Ativa</label>
      <button type="button" className="primary automation-save" onClick={onSave} disabled={!rule.name.trim() || !actions.length || actionDraftDirty || (rule.trigger === "scheduled_daily" && rule.schedule_frequency === "weekly" && !rule.schedule_weekdays.length)}>{enabled ? "Salvar e ativar" : "Salvar desativada"}</button>
    </header>

    <div className="automation-studio-workspace">
      <main className="automation-flow-canvas" aria-label="Fluxo da automação">
        <div className="automation-flow-column">
          <button type="button" className="automation-flow-node trigger" onClick={() => setPane("trigger")}>
            <span className="automation-node-icon"><Zap size={18} /></span><span><small>QUANDO</small><strong>{triggerOptions.find(([key]) => key === rule.trigger)?.[1] ?? "Escolher gatilho"}</strong>{rule.trigger === "scheduled_daily" && <em>{rule.schedule_frequency === "weekly" ? "Semanal" : "Diariamente"} · {rule.schedule_time} UTC</em>}</span><Settings2 size={16} className="automation-node-edit" />
          </button>
          <div className="automation-flow-connector" />
          <button type="button" className={`automation-flow-node condition${conditions ? " configured" : " empty"}`} onClick={() => setPane("conditions")}>
            <span className="automation-node-icon"><ListChecks size={18} /></span><span><small>SE (OPCIONAL)</small><strong>{conditions ? `${conditions} condição(ões) configurada(s)` : "Adicionar condições"}</strong><em>{conditions ? "Os cards só seguem se atenderem aos filtros." : "Filtre por status, tipo, prioridade e outros campos."}</em></span><Settings2 size={16} className="automation-node-edit" />
          </button>
          <div className="automation-flow-connector" />
          {actions.map((action, index) => <div className="automation-action-node-wrap" key={`${action.action}-${index}`}>
            <button type="button" className="automation-flow-node action" draggable onDragStart={(event) => { event.dataTransfer.effectAllowed = "move"; event.dataTransfer.setData("text/plain", String(index)); }} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); reorderAction(Number(event.dataTransfer.getData("text/plain")), index); }} onClick={() => openAction(index)}>
              <span className="automation-node-icon"><Check size={18} /></span><span><small>{index === 0 ? "ENTÃO" : "E DEPOIS"}</small><strong>{actionTitle(action, users)}</strong></span><GripVertical size={17} className="automation-node-edit" aria-hidden="true" /><Settings2 size={16} className="automation-node-edit" />
            </button>
            <div className="automation-node-order"><button type="button" aria-label={`Mover ação ${index + 1} para cima`} disabled={index === 0} onClick={() => moveAction(index, -1)}><ArrowUp size={15} /></button><button type="button" aria-label={`Mover ação ${index + 1} para baixo`} disabled={index === actions.length - 1} onClick={() => moveAction(index, 1)}><ArrowDown size={15} /></button><button type="button" aria-label={`Remover ação ${index + 1}`} onClick={() => setActions((current) => current.filter((_, itemIndex) => index !== itemIndex))}><Trash2 size={15} /></button></div>
            {index < actions.length - 1 && <div className="automation-flow-connector" />}
          </div>)}
          <button type="button" className="automation-add-step" onClick={openNewAction} disabled={actions.length >= 10}><Plus size={17} /> Adicionar ação</button>
          <p className="automation-flow-hint"><CircleHelp size={14} /> As etapas são executadas de cima para baixo. Cada regra aceita até 10 ações.</p>
        </div>
        <div className="automation-canvas-zoom" aria-hidden="true"><button type="button">−</button><span>100%</span><button type="button">＋</button></div>
      </main>

      {pane && <aside className="automation-config-panel" aria-label="Configurar etapa">
        <header><div><small>{pane === "trigger" ? "ETAPA 1" : pane === "conditions" ? "FILTROS DO FLUXO" : pane === "action" ? "ETAPA DE AÇÃO" : "CONFIGURAÇÕES"}</small><h3>{pane === "trigger" ? "Adicionar gatilho" : pane === "conditions" ? "Adicionar condições" : pane === "action" ? (editingAction === null ? "Adicionar ação" : "Editar ação") : "Detalhes do fluxo"}</h3></div><button type="button" className="header-icon" onClick={() => setPane(null)} aria-label="Fechar painel"><X size={18} /></button></header>
        <div className="automation-config-scroll">
          {pane === "trigger" && <>
            <p className="automation-panel-intro">Um evento inicia a execução desta automação. Escolha o gatilho e, se necessário, ajuste seus detalhes.</p>
            <label className="field-label">Pesquisar gatilhos<input type="search" placeholder="Ex.: card criado" value={triggerSearch} onChange={(event) => setTriggerSearch(event.target.value)} /></label>
            <fieldset className="automation-trigger-list"><legend>Gatilhos de cards e sprints</legend>{triggerOptions.filter(([, label]) => label.toLocaleLowerCase("pt-BR").includes(triggerSearch.toLocaleLowerCase("pt-BR"))).map(([key, label]) => <button type="button" className={`automation-trigger-option${rule.trigger === key ? " selected" : ""}`} key={key} onClick={() => { update("trigger", key); setTriggerSearch(""); }}><span>{key === "scheduled_daily" ? <CalendarClock size={17} /> : key === "development_event" ? <GitBranch size={17} /> : <Zap size={17} />}</span><strong>{label}</strong>{rule.trigger === key && <Check size={16} />}</button>)}</fieldset>
            {rule.trigger === "scheduled_daily" && <section className="automation-config-section"><h4>Agendamento</h4><label className="field-label">Horário (UTC)<input type="time" value={rule.schedule_time} onChange={(event) => update("schedule_time", event.target.value)} /></label><label className="field-label">Frequência<select value={rule.schedule_frequency} onChange={(event) => { update("schedule_frequency", event.target.value as "daily" | "weekly"); if (event.target.value === "daily") update("schedule_weekdays", []); }}><option value="daily">Todos os dias</option><option value="weekly">Semanalmente</option></select></label>{rule.schedule_frequency === "weekly" && <fieldset className="automation-weekdays"><legend>Executar nestes dias (UTC)</legend>{["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"].map((day, index) => <label key={day}><input type="checkbox" checked={rule.schedule_weekdays.includes(index)} onChange={(event) => update("schedule_weekdays", event.target.checked ? [...rule.schedule_weekdays, index].sort() : rule.schedule_weekdays.filter((value) => value !== index))} />{day}</label>)}</fieldset>}</section>}
            {rule.trigger === "sprint_scope_changed" && <label className="field-label">Mudança do escopo<select value={rule.sprint_scope_action} onChange={(event) => update("sprint_scope_action", event.target.value)}><option value="">Adicionada ou removida</option><option value="added">Card adicionado</option><option value="removed">Card removido</option></select></label>}
            {rule.trigger === "field_changed" && <label className="field-label">Campos monitorados<input value={rule.changed_fields} onChange={(event) => update("changed_fields", event.target.value)} placeholder="priority, due, area" /><small>IDs estruturais ou personalizados, separados por vírgula. Vazio monitora qualquer campo.</small></label>}
            {rule.trigger === "comment_added" && <label className="field-label">Comentário contém<input maxLength={200} value={rule.comment_contains} onChange={(event) => update("comment_contains", event.target.value)} placeholder="Opcional · trecho de texto" /></label>}
            {rule.trigger === "attachment_added" && <label className="field-label">Tipos de mídia<input value={rule.attachment_media_types} onChange={(event) => update("attachment_media_types", event.target.value)} placeholder="application/pdf, image/png" /><small>PDF, PNG, JPEG ou texto simples.</small></label>}
            {(["link_added", "link_removed"] as string[]).includes(rule.trigger) && <label className="field-label">Tipos de relação<input value={rule.link_types} onChange={(event) => update("link_types", event.target.value)} placeholder="blocks, relates, duplicates" /></label>}
            {rule.trigger === "development_event" && <section className="automation-config-section"><h4>Eventos de desenvolvimento</h4><label className="field-label">Provedores<input value={rule.development_providers} onChange={(event) => update("development_providers", event.target.value)} placeholder="github, gitlab, bitbucket" /></label><label className="field-label">Tipos de evento<input value={rule.development_event_types} onChange={(event) => update("development_event_types", event.target.value)} placeholder="push, pull_request, workflow_run" /></label><label className="field-label">Estados<input value={rule.development_states} onChange={(event) => update("development_states", event.target.value)} placeholder="success, failure, merged" /></label></section>}
          </>}

          {pane === "conditions" && <>
            <p className="automation-panel-intro">Defina critérios para que o fluxo continue somente quando os cards corresponderem. Todos os filtros configurados são combinados com E.</p>
            <section className="automation-config-section"><h4>Card</h4><label className="field-label">Status<input value={rule.statuses} onChange={(event) => update("statuses", event.target.value)} placeholder="Ex.: todo, production" /><small>Use a chave das etapas, separadas por vírgula.</small></label><label className="field-label">Tipos de card<input value={rule.work_types} onChange={(event) => update("work_types", event.target.value)} placeholder="Ex.: bug, task" /></label><label className="field-label">Estado da aprovação<input value={rule.approval_states} onChange={(event) => update("approval_states", event.target.value)} placeholder="approved, rejected" /></label><label className="field-label">Responsável interno<select value={rule.assignee_filter} onChange={(event) => update("assignee_filter", event.target.value)}><option value="">Qualquer responsável</option>{users.map((person) => <option key={person.id} value={person.id}>{person.username}</option>)}</select></label><label className="field-label">Prioridade mínima<input type="number" value={rule.priority_min} onChange={(event) => update("priority_min", event.target.value)} /></label><label className="field-label">Prioridade máxima<input type="number" value={rule.priority_max} onChange={(event) => update("priority_max", event.target.value)} /></label><label className="field-label">Etiquetas necessárias<input value={rule.labels} onChange={(event) => update("labels", event.target.value)} placeholder="Urgente, UX" /></label></section>
            <section className="automation-config-section"><h4>Prazo e planejamento</h4><label className="field-label">Prazo<select value={rule.due_set} onChange={(event) => update("due_set", event.target.value)}><option value="">Com ou sem prazo</option><option value="true">Somente cards com prazo</option><option value="false">Somente cards sem prazo</option></select></label><label className="field-label">Prazo nos próximos dias<input type="number" min="0" max="3650" value={rule.due_window} onChange={(event) => update("due_window", event.target.value)} placeholder="Opcional" /></label><label className="field-label">Atraso<select value={rule.overdue} onChange={(event) => update("overdue", event.target.value)}><option value="">Qualquer situação</option><option value="true">Somente atrasados</option><option value="false">Somente não atrasados</option></select></label><label className="field-label">Release<select value={rule.release_assigned} onChange={(event) => update("release_assigned", event.target.value)}><option value="">Com ou sem release</option><option value="true">Com release</option><option value="false">Sem release</option></select></label><label className="field-label">Componente<select value={rule.component_assigned} onChange={(event) => update("component_assigned", event.target.value)}><option value="">Com ou sem componente</option><option value="true">Com componente</option><option value="false">Sem componente</option></select></label><label className="field-label">Dependências<select value={rule.blocked} onChange={(event) => update("blocked", event.target.value)}><option value="">Bloqueado ou não</option><option value="true">Bloqueado por card pendente</option><option value="false">Não bloqueado</option></select></label></section>
            <section className="automation-config-section"><h4>Campos personalizados</h4><label className="field-label">Comparar IDs e valores (JSON)<textarea rows={5} value={customFieldsJson} onChange={(event) => setCustomFieldsJson(event.target.value)} placeholder={'{"area": "Operações", "urgente": true}'} /><small>Até 10 campos existentes. Os valores são comparados por tipo e não aparecem na auditoria.</small></label></section>
          </>}

          {pane === "action" && <>
            <p className="automation-panel-intro">As ações são executadas na ordem em que aparecem no fluxo.</p>
            <label className="field-label">Pesquisar ações<input type="search" placeholder="Ex.: prioridade" value={actionSearch} onChange={(event) => setActionSearch(event.target.value)} /></label>
            <fieldset className="automation-trigger-list"><legend>Ações disponíveis</legend>{actionOptions.filter(([, label]) => label.toLocaleLowerCase("pt-BR").includes(actionSearch.toLocaleLowerCase("pt-BR"))).map(([key, label]) => <button type="button" className={`automation-trigger-option automation-action-option${rule.action === key ? " selected" : ""}`} key={key} onClick={() => { update("action", key); setActionDraftDirty(true); setJsonError(""); setActionSearch(""); }}><span><Check size={16} /></span><strong>{label}</strong>{rule.action === key && <Check size={16} />}</button>)}</fieldset>
            {rule.action === "set_custom_fields" ? <label className="field-label">Valores dos campos (JSON)<textarea rows={6} value={rule.custom_field_values} onChange={(event) => { update("custom_field_values", event.target.value); setActionDraftDirty(true); setJsonError(""); }} placeholder={'{"area": "Operações"}'} /><small>Atualiza campos simples existentes, respeitando as permissões do sistema.</small></label>
              : rule.action === "set_priority" ? <label className="field-label">Prioridade numérica<input type="number" value={rule.priority} onChange={(event) => { update("priority", event.target.value); setActionDraftDirty(true); }} /></label>
                : rule.action === "add_label" || rule.action === "remove_label" ? <><label className="field-label">Texto da etiqueta<input maxLength={40} value={rule.label} onChange={(event) => { update("label", event.target.value); setActionDraftDirty(true); }} /></label>{rule.action === "add_label" && <label className="field-label">Cor da etiqueta<input type="color" value={rule.color} onChange={(event) => { update("color", event.target.value); setActionDraftDirty(true); }} /></label>}</>
                  : rule.action === "set_due_after_days" ? <label className="field-label">Dias após a criação (0–3.650)<input type="number" min="0" max="3650" value={rule.due_days} onChange={(event) => { update("due_days", event.target.value); setActionDraftDirty(true); }} /></label>
                    : rule.action === "assign_internal_user" || rule.action === "add_watcher" ? <label className="field-label">Pessoa interna<select value={rule.assignee_user} onChange={(event) => { update("assignee_user", event.target.value); setActionDraftDirty(true); }}><option value="">Selecione uma pessoa</option>{users.map((person) => <option key={person.id} value={person.id}>{person.username}</option>)}</select></label>
                      : <label className="field-label">Comentário automático<textarea maxLength={1000} rows={4} value={rule.comment} onChange={(event) => { update("comment", event.target.value); setActionDraftDirty(true); }} placeholder="Escreva o comentário que será adicionado ao card" /></label>}
            {jsonError && <p className="rejection" role="alert">{jsonError}</p>}
          </>}

          {pane === "details" && <><p className="automation-panel-intro">Dê um nome ao fluxo e escolha se ele ficará ativo assim que for salvo.</p><label className="field-label">Nome do fluxo<input autoFocus value={rule.name} onChange={(event) => update("name", event.target.value)} maxLength={120} placeholder="Ex.: Avisar quando um card ficar atrasado" /></label><label className="automation-detail-toggle"><input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} /><span><strong>Ativar fluxo ao salvar</strong><small>Quando ativo, os eventos correspondentes executam as etapas configuradas.</small></span></label><div className="automation-detail-note"><Zap size={16} /> As automações são executadas com o usuário de sistema e registradas no histórico de auditoria.</div></>}
        </div>
        <footer className="automation-config-footer">
          {pane === "action" ? <><button type="button" className="quiet-button" onClick={() => { setPane(null); setEditingAction(null); setActionDraftDirty(false); }}>Cancelar</button><button type="button" className="primary" onClick={commitAction} disabled={rule.action === "set_priority" && !Number.isFinite(Number(rule.priority)) || ["add_label", "remove_label"].includes(rule.action) && !rule.label.trim() || rule.action === "add_comment" && !rule.comment.trim() || ["assign_internal_user", "add_watcher"].includes(rule.action) && !rule.assignee_user || rule.action === "set_custom_fields" && !!jsonError || editingAction === null && actions.length >= 10}><Plus size={16} /> {editingAction === null ? "Adicionar ao fluxo" : "Salvar ação"}</button></>
            : <button type="button" className="primary" onClick={() => setPane(null)}><Check size={16} /> Concluído</button>}
        </footer>
      </aside>}
    </div>
  </div>;
}
