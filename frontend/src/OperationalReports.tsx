import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Clock3,
  History,
  CalendarRange,
  ListTodo,
  FileSpreadsheet,
  FileText,
  X,
  ArrowRight,
  TriangleAlert,
} from "lucide-react";
import { api, download } from "./api";
import { stages, approvals, money, formatTimestamp, type Field } from "./types";
import { Label, Empty, type Run } from "./App";

type Passage = {
  status: string;
  entered_at: string | null;
  exited_at: string | null;
  duration_seconds: number | null;
  complete: boolean;
  open: boolean;
  entry_actor: string | null;
  exit_actor: string | null;
};
type Cycle = {
  kind: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  complete: boolean;
};
type Event = {
  id: number;
  action: string;
  at: string;
  actor: string;
  origin: string | null;
  destination: string | null;
  reason: string;
};
type Approval = {
  hours_version: number;
  submitted_at: string;
  submitted_by: string;
  used_minutes: number;
  state: string;
  decision_at: string | null;
  decision_by: string | null;
  waiting_seconds: number | null;
  reason: string;
};
interface Card {
  id: number;
  title: string;
  status: string;
  supplier_name: string | null;
  priority: number;
  due: string | null;
  created_at: string;
  as_of: string;
  historical: boolean;
  history_complete: boolean;
  history_issues: string[];
  age_seconds: number | null;
  current_phase_seconds: number | null;
  lead_time_seconds: number | null;
  idle_seconds: number | null;
  estimated_minutes: number | null;
  used_minutes: number;
  approved_minutes: number;
  hours_deviation_minutes: number | null;
  hours_deviation_percent: string | null;
  approval: string;
  reopen_count: number;
  rejection_count: number;
  resubmission_count: number;
  sprints_visited: number;
  deadline: { state: string; late_days: number | null };
  periods: Passage[];
  phases: { status: string; duration_seconds: number | null; visits: number }[];
  cycles: Cycle[];
  timeline: Event[];
  approval_history: Approval[];
  production_missing_fields: string[];
  fields: Field[];
  values: Record<string, unknown>;
  cost_cents?: number;
  rate_cents?: number | null;
}
interface Sprint {
  id: number;
  name: string;
  state: string;
  as_of: string;
  history_complete: boolean;
  initial_cards: number | null;
  initial_done: number | null;
  commitment_percent: string | null;
  added_after_start: number | null;
  done: number;
  pending: number;
  returned: number;
  scope_cards: number;
  estimated_minutes: number;
  used_minutes: number;
  approved_minutes: number;
  estimated_cards: number;
  cost_cents?: number;
  completion_events_by_day: { date: string; count: number }[];
}
interface Report {
  as_of: string;
  total: number;
  filters: string[];
  period_basis: string;
  items: Card[];
  backlog_oldest: Card[];
  sprints: Sprint[];
  summary: {
    cards: number;
    complete_histories: number;
    open: number;
    overdue: number;
    reopened: number;
    waiting_approval: number;
    phase_seconds: {
      status: string;
      duration_seconds: number;
      measured_cards: number;
    }[];
    backlog: {
      count: number;
      unassigned: number;
      overdue: number;
      idle_days: number;
      idle: number;
      ready: number;
      by_priority: { value: number; count: number }[];
      by_supplier: { value: number | null; count: number }[];
    };
    recorded_flow: {
      created: number;
      started: number;
      completed: number;
      returned: number;
      basis: string;
    };
  };
}
const eventNames: Record<string, string> = {
  created: "Card criado",
  edited: "Dados atualizados",
  status_changed: "Etapa alterada",
  included_in_sprint: "Incluído em sprint",
  returned_to_backlog: "Devolvido ao backlog",
  reopened: "Reabertura autorizada",
  hours_submitted: "Horas enviadas",
  hours_decided: "Horas avaliadas",
  schema_versioned: "Configuração atualizada",
  values_versioned: "Campos atualizados",
  reordered: "Prioridade alterada",
  supplier_changed: "Fornecedor alterado",
  comment_added: "Comentário adicionado",
  attachment_added: "Anexo adicionado",
};
const deadlineNames: Record<string, string> = {
  no_due: "Sem prazo",
  unknown: "Sem histórico de conclusão",
  late: "Concluído com atraso",
  on_time: "Concluído no prazo",
  overdue: "Em atraso",
  within_due: "Dentro do prazo",
};
const sprintNames: Record<string, string> = {
  planned: "Planejada",
  active: "Ativa",
  closed: "Encerrada",
};
const num = (value: number | string) =>
  new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(
    Number(value),
  );
const timestamp = (value: string | null) =>
  value ? formatTimestamp(value) : "Indisponível";
export function duration(value: number | null | undefined): string {
  if (value == null) return "Indisponível";
  const days = Math.floor(value / 86400),
    hours = Math.floor((value % 86400) / 3600),
    minutes = Math.floor((value % 3600) / 60),
    seconds = Math.floor(value % 60);
  return [
    days ? `${num(days)}d` : "",
    hours ? `${hours}h` : "",
    minutes ? `${minutes}min` : "",
    !days && !hours && !minutes ? `${seconds}s` : "",
  ]
    .filter(Boolean)
    .join(" ");
}
const hours = (value: number | null) =>
  value == null ? "Não informadas" : `${num(value / 60)} h`;
function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <article className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      {hint && <small>{hint}</small>}
    </article>
  );
}
function CardAnalysis({
  identity,
  sprintId,
  close,
}: {
  identity: number;
  sprintId: string | null;
  close: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const result = useQuery({
    queryKey: ["card-analysis", identity, sprintId],
    queryFn: () =>
      api<Card>(
        `/reports/cards/${identity}` +
          (sprintId ? `?sprint_id=${sprintId}` : ""),
      ),
  });
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const element = dialog.current!;
    element.showModal();
    return () => {
      element.close();
      if (previous?.isConnected) previous.focus();
    };
  }, []);
  const card = result.data;
  return (
    <dialog
      ref={dialog}
      className="analysis-detail"
      aria-labelledby="analysis-card-title"
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
    >
      <div className="section-title">
        <div>
          <span className="eyebrow">Análise do card OS-{identity}</span>
          <h2 id="analysis-card-title">
            {card?.title ?? "Carregando análise"}
          </h2>
        </div>
        <button autoFocus aria-label="Fechar análise do card" onClick={close}>
          <X size={18} aria-hidden="true" />
          Fechar
        </button>
      </div>
      {result.isPending && <p role="status">Carregando histórico…</p>}
      {result.isError && <p role="alert">{result.error.message}</p>}
      {card && (
        <>
          <p>
            {stages[card.status]} · {card.supplier_name ?? "Não atribuído"} ·
            Criado em {timestamp(card.created_at)}
          </p>
          <p className="formula">
            Observado até {timestamp(card.as_of)}.{" "}
            {card.historical
              ? "Retrato da sprint encerrada."
              : "Horários corridos, incluindo noites e fins de semana."}{" "}
            Permanência em uma etapa não equivale a horas trabalhadas.
          </p>
          {!card.history_complete && (
            <div className="analysis-warning" role="status">
              <TriangleAlert size={20} aria-hidden="true" />
              <div>
                <strong>Histórico parcial</strong>
                <ul>
                  {card.history_issues.map((issue) => (
                    <li key={issue}>{issue}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
          <div className="metrics analysis-metrics">
            <Stat
              label="Idade do registro"
              value={duration(card.age_seconds)}
            />
            <Stat
              label="Na etapa atual"
              value={
                card.status === "done"
                  ? "Etapa terminal"
                  : duration(card.current_phase_seconds)
              }
            />
            <Stat
              label="Criação até primeira conclusão"
              value={duration(card.lead_time_seconds)}
            />
            <Stat
              label="Último ciclo"
              value={duration(card.cycles.at(-1)?.duration_seconds)}
            />
          </div>
          <h3>Tempo acumulado em cada fase</h3>
          <div className="analysis-phase-grid">
            {card.phases.map((phase) => (
              <div key={phase.status}>
                <span>{stages[phase.status]}</span>
                <strong>
                  {phase.status === "done"
                    ? "Terminal"
                    : !phase.visits && card.history_complete
                      ? "Sem passagem"
                      : duration(phase.duration_seconds)}
                </strong>
                <small>{phase.visits} passagem(ns) registrada(s)</small>
              </div>
            ))}
          </div>
          <h3>Passagens pelas fases</h3>
          <div
            className="table-wrap"
            tabIndex={0}
            role="region"
            aria-label="Passagens pelas fases"
          >
            <table>
              <caption>Entrada e saída de cada passagem</caption>
              <thead>
                <tr>
                  <th scope="col">Etapa</th>
                  <th scope="col">Entrada</th>
                  <th scope="col">Saída</th>
                  <th scope="col">Duração</th>
                  <th scope="col">Responsáveis</th>
                </tr>
              </thead>
              <tbody>
                {card.periods.map((period, index) => (
                  <tr key={index}>
                    <td>{stages[period.status]}</td>
                    <td>{timestamp(period.entered_at)}</td>
                    <td>
                      {period.open
                        ? "Em aberto no corte"
                        : timestamp(period.exited_at)}
                    </td>
                    <td>
                      {period.status === "done"
                        ? "Não integra o ciclo ativo"
                        : duration(period.duration_seconds)}
                      {!period.complete && (
                        <small>Intervalo não comprovado</small>
                      )}
                    </td>
                    <td>
                      {period.entry_actor ?? "Indisponível"}
                      {period.exit_actor && ` / ${period.exit_actor}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h3>Ciclos de execução e reabertura</h3>
          {card.cycles.length ? (
            <div className="table-wrap">
              <table>
                <caption>Ciclos preservados separadamente</caption>
                <thead>
                  <tr>
                    <th scope="col">Ciclo</th>
                    <th scope="col">Início</th>
                    <th scope="col">Conclusão</th>
                    <th scope="col">Duração</th>
                  </tr>
                </thead>
                <tbody>
                  {card.cycles.map((cycle, index) => (
                    <tr key={index}>
                      <td>
                        {cycle.kind === "reopening" ? "Reabertura" : "Produção"}{" "}
                        {index + 1}
                      </td>
                      <td>{timestamp(cycle.started_at)}</td>
                      <td>
                        {cycle.completed_at
                          ? timestamp(cycle.completed_at)
                          : "Em andamento"}
                      </td>
                      <td>{duration(cycle.duration_seconds)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p>Sem ciclo de produção comprovado.</p>
          )}
          <h3>Horas prazo e retrabalho</h3>
          <dl className="totals">
            <div>
              <dt>Horas previstas</dt>
              <dd>{hours(card.estimated_minutes)}</dd>
            </div>
            <div>
              <dt>Horas utilizadas / aprovadas</dt>
              <dd>
                {hours(card.used_minutes)} / {hours(card.approved_minutes)}
              </dd>
            </div>
            <div>
              <dt>Desvio de horas</dt>
              <dd>
                {card.hours_deviation_minutes == null
                  ? "Não se aplica sem estimativa"
                  : `${hours(card.hours_deviation_minutes)} (${num(card.hours_deviation_percent!)}%)`}
              </dd>
            </div>
            <div>
              <dt>Prazo</dt>
              <dd>
                {deadlineNames[card.deadline.state]}
                {card.deadline.late_days
                  ? ` · ${card.deadline.late_days} dia(s)`
                  : ""}
              </dd>
            </div>
            <div>
              <dt>Reaberturas / rejeições / reapresentações registradas</dt>
              <dd>
                {card.reopen_count} / {card.rejection_count} /{" "}
                {card.resubmission_count}
              </dd>
            </div>
            <div>
              <dt>Sprints visitadas no histórico</dt>
              <dd>{card.sprints_visited}</dd>
            </div>
            {card.cost_cents !== undefined && (
              <div>
                <dt>Custo consolidado / tarifa congelada</dt>
                <dd>
                  {money(card.cost_cents)} /{" "}
                  {card.rate_cents == null
                    ? "Indisponível"
                    : `${money(card.rate_cents)}/h`}
                </dd>
              </div>
            )}
          </dl>
          <h3>Submissões e decisões de horas</h3>
          {card.approval_history.length ? (
            <div className="table-wrap">
              <table>
                <caption>Espera de cada versão enviada</caption>
                <thead>
                  <tr>
                    <th scope="col">Versão</th>
                    <th scope="col">Envio</th>
                    <th scope="col">Decisão</th>
                    <th scope="col">Espera</th>
                    <th scope="col">Autor decisão</th>
                    <th scope="col">Justificativa</th>
                  </tr>
                </thead>
                <tbody>
                  {card.approval_history.map((entry) => (
                    <tr key={entry.hours_version}>
                      <td>{entry.hours_version}</td>
                      <td>
                        {timestamp(entry.submitted_at)}
                        <small>{entry.submitted_by}</small>
                      </td>
                      <td>
                        {approvals[entry.state]}
                        <small>{timestamp(entry.decision_at)}</small>
                      </td>
                      <td>{duration(entry.waiting_seconds)}</td>
                      <td>{entry.decision_by ?? "Aguardando decisão"}</td>
                      <td>{entry.reason || "Sem justificativa"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p>Nenhuma submissão de horas registrada.</p>
          )}
          <h3>Linha do tempo</h3>
          {card.timeline.length ? (
            <ol className="analysis-timeline">
              {card.timeline.map((event) => (
                <li key={event.id}>
                  <History size={18} aria-hidden="true" />
                  <div>
                    <strong>
                      {eventNames[event.action] ?? "Atualização registrada"}
                    </strong>
                    <small>
                      {timestamp(event.at)} · {event.actor}
                    </small>
                    {event.origin && event.destination && (
                      <p>
                        {stages[event.origin]}{" "}
                        <ArrowRight size={14} aria-hidden="true" />{" "}
                        {stages[event.destination]}
                      </p>
                    )}
                    {event.reason && <p>{event.reason}</p>}
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <p>Não há eventos suficientes para reconstruir a linha do tempo.</p>
          )}
          {card.fields.some((field) => field.type !== "native") && (
            <>
              <h3>Campos personalizados visíveis</h3>
              <dl className="totals">
                {card.fields
                  .filter((field) => field.type !== "native")
                  .map((field) => (
                    <div key={field.id}>
                      <dt>{field.label}</dt>
                      <dd>
                        {typeof card.values[field.id] === "boolean"
                          ? card.values[field.id]
                            ? "Sim"
                            : "Não"
                          : Array.isArray(card.values[field.id])
                            ? (card.values[field.id] as unknown[]).join(", ")
                            : String(card.values[field.id] ?? "Não preenchido")}
                      </dd>
                    </div>
                  ))}
              </dl>
            </>
          )}
        </>
      )}
    </dialog>
  );
}
export function OperationalReports({
  query,
  financialExport,
  run,
}: {
  query: string;
  financialExport: boolean;
  run: Run;
}) {
  const [section, setSection] = useState("cards"),
    [page, setPage] = useState(0),
    [selected, setSelected] = useState<number | null>(null),
    [include, setInclude] = useState(false);
  const [filters, setFilters] = useState({
    min_phase_hours: "",
    overdue_only: false,
    only_reopened: false,
    approval_state: "",
    idle_days: "7",
  });
  const [applied, setApplied] = useState(filters);
  const params = new URLSearchParams(query);
  Object.entries(applied).forEach(([key, value]) => {
    if (value !== "" && value !== false) params.set(key, String(value));
  });
  const reportQuery = params.toString();
  const response = useQuery({
    queryKey: ["operational-report", reportQuery, page],
    queryFn: () =>
      api<Report>(`/reports/analysis?${reportQuery}&offset=${page * 25}`),
  });
  const data = response.data;
  const sections = [
    { key: "cards", label: "Cards", icon: Clock3 },
    { key: "sprints", label: "Sprints", icon: CalendarRange },
    { key: "backlog", label: "Backlog", icon: ListTodo },
  ];
  return (
    <>
      <section className="panel">
        <div className="section-title">
          <div>
            <span className="eyebrow">Análise operacional</span>
            <h2>Cards sprints e backlog</h2>
          </div>
          <span>Tempos em horas corridas</span>
        </div>
        <form
          className="analysis-filters"
          onSubmit={(event) => {
            event.preventDefault();
            setApplied(filters);
            setPage(0);
          }}
        >
          <Label title="Tempo mínimo na fase atual (horas)">
            <input
              inputMode="decimal"
              value={filters.min_phase_hours}
              onChange={(event) =>
                setFilters({ ...filters, min_phase_hours: event.target.value })
              }
              placeholder="Ex.: 24"
            />
          </Label>
          <Label title="Situação das horas">
            <select
              value={filters.approval_state}
              onChange={(event) =>
                setFilters({ ...filters, approval_state: event.target.value })
              }
            >
              <option value="">Todas as situações</option>
              {Object.entries(approvals).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </Label>
          <Label title="Parado há pelo menos (dias)">
            <input
              type="number"
              min="1"
              max="3650"
              required
              value={filters.idle_days}
              onChange={(event) =>
                setFilters({ ...filters, idle_days: event.target.value })
              }
            />
          </Label>
          <Label title="Somente com atraso">
            <input
              type="checkbox"
              checked={filters.overdue_only}
              onChange={(event) =>
                setFilters({ ...filters, overdue_only: event.target.checked })
              }
            />
          </Label>
          <Label title="Somente reabertos">
            <input
              type="checkbox"
              checked={filters.only_reopened}
              onChange={(event) =>
                setFilters({ ...filters, only_reopened: event.target.checked })
              }
            />
          </Label>
          <button className="primary">Aplicar análise</button>
        </form>
        <p className="formula">
          Período filtra a criação UTC dos cards. As durações abrangem o
          histórico até o corte mostrado. Tempo de permanência não representa
          horas trabalhadas; Concluído é uma etapa terminal. O limite de dias
          parados classifica os cards do backlog.
        </p>
      </section>
      {response.isPending && (
        <p role="status">Calculando análise operacional…</p>
      )}
      {response.isError && <p role="alert">{response.error.message}</p>}
      {data && (
        <>
          <p className="analysis-reference">
            Observado em {timestamp(data.as_of)} ·{" "}
            {num(data.summary.complete_histories)} de {num(data.total)}{" "}
            histórico(s) completo(s).
          </p>
          <div className="metrics analysis-metrics">
            <Stat label="Cards no recorte" value={num(data.total)} />
            <Stat label="Cards em aberto" value={num(data.summary.open)} />
            <Stat label="Em atraso" value={num(data.summary.overdue)} />
            <Stat
              label="Aguardando aprovação"
              value={num(data.summary.waiting_approval)}
            />
          </div>
          <section className="panel">
            <div
              className="analysis-tabs"
              role="tablist"
              aria-label="Visões da análise"
              onKeyDown={(event) => {
                if (
                  !["ArrowRight", "ArrowLeft", "Home", "End"].includes(
                    event.key,
                  )
                )
                  return;
                event.preventDefault();
                let index = sections.findIndex((item) => item.key === section);
                index =
                  event.key === "Home"
                    ? 0
                    : event.key === "End"
                      ? sections.length - 1
                      : (index +
                          (event.key === "ArrowRight" ? 1 : -1) +
                          sections.length) %
                        sections.length;
                setSection(sections[index].key);
                document
                  .getElementById("analysis-tab-" + sections[index].key)
                  ?.focus();
              }}
            >
              {sections.map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  id={"analysis-tab-" + key}
                  role="tab"
                  aria-selected={section === key}
                  aria-controls="analysis-panel"
                  tabIndex={section === key ? 0 : -1}
                  onClick={() => setSection(key)}
                >
                  <Icon size={18} aria-hidden="true" />
                  {label}
                </button>
              ))}
            </div>
            <div
              id="analysis-panel"
              role="tabpanel"
              aria-labelledby={"analysis-tab-" + section}
            >
              {section === "cards" && (
                <>
                  <h2>Prévia do relatório de cards</h2>
                  <p role="status">{data.total} atividade(s) encontrada(s).</p>
                  {data.filters.length > 0 && (
                    <ul aria-label="Filtros aplicados">
                      {data.filters.map((value, index) => (
                        <li key={index}>{value}</li>
                      ))}
                    </ul>
                  )}
                  {data.total === 0 ? (
                    <Empty>
                      Nenhuma atividade atende aos filtros selecionados.
                    </Empty>
                  ) : (
                    <div
                      className="table-wrap"
                      tabIndex={0}
                      role="region"
                      aria-label="Análise dos cards"
                    >
                      <table>
                        <caption>
                          Selecione o código de um card para abrir os tempos e a
                          linha do tempo
                        </caption>
                        <thead>
                          <tr>
                            {[
                              "ID",
                              "Título",
                              "Etapa",
                              "Fornecedor",
                              "Fase atual",
                              "Idade do registro",
                              "Criação até 1ª conclusão",
                              "Último ciclo",
                              "Prazo",
                              "Histórico",
                            ].map((label) => (
                              <th key={label} scope="col">
                                {label}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {data.items.map((card) => (
                            <tr key={card.id}>
                              <td>
                                <button
                                  className="link"
                                  aria-label={`Analisar card OS-${card.id}`}
                                  onClick={() => setSelected(card.id)}
                                >
                                  OS-{card.id}
                                </button>
                              </td>
                              <td>{card.title}</td>
                              <td>
                                <span className={"badge " + card.status}>
                                  {stages[card.status]}
                                </span>
                              </td>
                              <td>{card.supplier_name ?? "Não atribuído"}</td>
                              <td>
                                {card.status === "done"
                                  ? "Terminal"
                                  : duration(card.current_phase_seconds)}
                              </td>
                              <td>{duration(card.age_seconds)}</td>
                              <td>{duration(card.lead_time_seconds)}</td>
                              <td>
                                {duration(card.cycles.at(-1)?.duration_seconds)}
                              </td>
                              <td>{deadlineNames[card.deadline.state]}</td>
                              <td>
                                {card.history_complete ? "Completo" : "Parcial"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <div className="actions">
                    <button
                      disabled={page === 0}
                      onClick={() => setPage(page - 1)}
                    >
                      Página anterior
                    </button>
                    <span>Página {page + 1}</span>
                    <button
                      disabled={(page + 1) * 25 >= data.total}
                      onClick={() => setPage(page + 1)}
                    >
                      Próxima página
                    </button>
                  </div>
                </>
              )}
              {section === "sprints" && (
                <>
                  <h2>Resumo de sprints</h2>
                  <p>
                    Valores referentes aos cards deste recorte. Sprints
                    encerradas preservam os dados do encerramento.
                  </p>
                  {!data.sprints.length ? (
                    <Empty>Nenhuma sprint com cards neste recorte.</Empty>
                  ) : (
                    data.sprints.map((sprint) => (
                      <article className="analysis-sprint" key={sprint.id}>
                        <div className="section-title">
                          <h3>{sprint.name}</h3>
                          <span className="badge">
                            {sprintNames[sprint.state]}
                          </span>
                        </div>
                        <p>
                          Observado até {timestamp(sprint.as_of)}
                          {!sprint.history_complete &&
                            " · Base histórica parcial"}
                        </p>
                        <dl className="totals">
                          <div>
                            <dt>Cards iniciais / iniciais concluídos</dt>
                            <dd>
                              {sprint.initial_cards ?? "Indisponível"} /{" "}
                              {sprint.initial_done ?? "Indisponível"}
                            </dd>
                          </div>
                          <div>
                            <dt>Cumprimento do compromisso inicial</dt>
                            <dd>
                              {sprint.commitment_percent == null
                                ? "Sem base de cálculo"
                                : num(sprint.commitment_percent) + "%"}
                            </dd>
                          </div>
                          <div>
                            <dt>Adicionados após o início</dt>
                            <dd>
                              {sprint.added_after_start ?? "Indisponível"}
                            </dd>
                          </div>
                          <div>
                            <dt>Concluídos / pendentes / devolvidos</dt>
                            <dd>
                              {sprint.done} / {sprint.pending} /{" "}
                              {sprint.returned}
                            </dd>
                          </div>
                          <div>
                            <dt>Horas previstas / utilizadas / aprovadas</dt>
                            <dd>
                              {hours(sprint.estimated_minutes)} /{" "}
                              {hours(sprint.used_minutes)} /{" "}
                              {hours(sprint.approved_minutes)}
                            </dd>
                          </div>
                          <div>
                            <dt>Cards com estimativa</dt>
                            <dd>
                              {sprint.estimated_cards} de {sprint.scope_cards}
                            </dd>
                          </div>
                          {sprint.cost_cents !== undefined && (
                            <div>
                              <dt>Custo consolidado</dt>
                              <dd>{money(sprint.cost_cents)}</dd>
                            </div>
                          )}
                        </dl>
                        <h3>Conclusões registradas por dia</h3>
                        <p className="formula">
                          Eventos de conclusão no intervalo da sprint. Uma
                          reabertura pode gerar uma nova conclusão do mesmo
                          card.
                        </p>
                        {sprint.completion_events_by_day.length ? (
                          <ul>
                            {sprint.completion_events_by_day.map((day) => (
                              <li key={day.date}>
                                {new Date(
                                  day.date + "T12:00:00",
                                ).toLocaleDateString("pt-BR")}
                                : {day.count} conclusão(ões)
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p>
                            Sem eventos de conclusão no intervalo observado.
                          </p>
                        )}
                      </article>
                    ))
                  )}
                </>
              )}
              {section === "backlog" && (
                <>
                  <h2>Análise do backlog</h2>
                  <div className="metrics analysis-metrics">
                    <Stat
                      label="No backlog"
                      value={data.summary.backlog.count}
                    />
                    <Stat
                      label="Sem fornecedor"
                      value={data.summary.backlog.unassigned}
                    />
                    <Stat
                      label={`Parados há ${data.summary.backlog.idle_days} dias`}
                      value={data.summary.backlog.idle}
                    />
                    <Stat
                      label="Sem pendência visível para produção"
                      value={data.summary.backlog.ready}
                    />
                  </div>
                  <p className="formula">
                    Prontidão considera o fornecedor e os campos visíveis
                    exigidos para A fazer ou Em produção. A autorização final
                    continua validada pelo servidor. Histórico incompleto pode
                    impedir medir inatividade.
                  </p>
                  <h3>Cards mais antigos no backlog</h3>
                  {data.backlog_oldest.length ? (
                    <div className="table-wrap">
                      <table>
                        <caption>Até 10 cards mais antigos do recorte</caption>
                        <thead>
                          <tr>
                            <th scope="col">Card</th>
                            <th scope="col">Idade</th>
                            <th scope="col">Permanência atual</th>
                            <th scope="col">Sem alteração observada</th>
                            <th scope="col">Pendências visíveis</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.backlog_oldest.map((card) => (
                            <tr key={card.id}>
                              <td>
                                <button
                                  className="link"
                                  onClick={() => setSelected(card.id)}
                                >
                                  {card.title}
                                </button>
                              </td>
                              <td>{duration(card.age_seconds)}</td>
                              <td>{duration(card.current_phase_seconds)}</td>
                              <td>{duration(card.idle_seconds)}</td>
                              <td>
                                {card.production_missing_fields.join(", ") ||
                                  "Nenhuma pendência visível"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <Empty>Nenhum card no backlog para este recorte.</Empty>
                  )}
                  <div className="dashboard-grid">
                    <div>
                      <h3>Distribuição por prioridade</h3>
                      <ul>
                        {data.summary.backlog.by_priority.map((group) => (
                          <li key={group.value}>
                            Prioridade {group.value}: {group.count} card(s)
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h3>Distribuição por fornecedor</h3>
                      <ul>
                        {data.summary.backlog.by_supplier.map((group) => (
                          <li key={String(group.value)}>
                            {group.value == null
                              ? "Não atribuído"
                              : `Fornecedor #${group.value}`}
                            : {group.count} card(s)
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                  <h3>Entradas e saídas registradas</h3>
                  <p className="formula">{data.summary.recorded_flow.basis}</p>
                  <dl className="totals">
                    <div>
                      <dt>Criações / inícios de produção</dt>
                      <dd>
                        {data.summary.recorded_flow.created} /{" "}
                        {data.summary.recorded_flow.started}
                      </dd>
                    </div>
                    <div>
                      <dt>Conclusões / retornos ao backlog</dt>
                      <dd>
                        {data.summary.recorded_flow.completed} /{" "}
                        {data.summary.recorded_flow.returned}
                      </dd>
                    </div>
                  </dl>
                </>
              )}
            </div>
          </section>
        </>
      )}
      <section className="panel">
        <h2>Exportar relatório</h2>
        <p>
          Excel inclui cards, fases, linha do tempo, aprovações, sprints e
          backlog. PDF apresenta o mesmo recorte com seus históricos. Durações
          exportadas em segundos corridos.
        </p>
        {financialExport && (
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
            disabled={!data || response.isFetching || response.isError}
            onClick={() =>
              run(() =>
                download(
                  `/exports/xlsx?${reportQuery}&analysis=true&financial=${include}`,
                ),
              )
            }
          >
            <FileSpreadsheet size={18} aria-hidden="true" />
            Exportar Excel (.xlsx)
          </button>
          <button
            disabled={!data || response.isFetching || response.isError}
            onClick={() =>
              run(() =>
                download(
                  `/exports/pdf?${reportQuery}&analysis=true&financial=${include}`,
                ),
              )
            }
          >
            <FileText size={18} aria-hidden="true" />
            Exportar PDF
          </button>
        </div>
      </section>
      {selected !== null && (
        <CardAnalysis
          key={selected}
          identity={selected}
          sprintId={params.get("sprint_id")}
          close={() => setSelected(null)}
        />
      )}
    </>
  );
}
