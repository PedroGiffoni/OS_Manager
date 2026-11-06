import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import { formatTimestamp } from "./types";

type Change = {
  field: string;
  label?: string;
  kind?: string;
  before: unknown;
  after: unknown;
};
type Entry = {
  id: number;
  actor_id: number;
  actor_name: string;
  action: string;
  created_at: string;
  details: Record<string, unknown> & {
    changes?: Change[];
    operation?: string;
    hours_version?: number;
  };
};
const actions: Record<string, string> = {
  created: "Card criado",
  edited: "Dados do card editados",
  assignment_changed: "Fornecedor alterado",
  hours_submitted: "Apontamento de horas registrado",
  hours_decided: "Horas avaliadas",
  schema_versioned: "Configuração do card versionada",
  values_versioned: "Campos do card preenchidos ou editados",
  status_changed: "Etapa alterada",
  reopened: "Card reaberto",
  reordered: "Prioridade ou posição alterada",
  included_in_sprint: "Card incluído em sprint",
  returned_to_backlog: "Card devolvido ao backlog",
  comment_added: "Comentário adicionado",
  attachment_added: "Anexo adicionado",
  archived: "Card arquivado",
};
const labels: Record<string, string> = {
  estimated_minutes: "Horas previstas",
  used_minutes: "Horas utilizadas",
  title: "Título",
  description: "Descrição",
  labels: "Etiquetas",
  text: "Texto",
  color: "Cor",
  priority: "Prioridade",
  due: "Prazo",
  supplier_id: "Fornecedor (ID)",
  previous_supplier_id: "Fornecedor anterior (ID)",
  origin: "Etapa anterior",
  destination: "Nova etapa",
  reason: "Justificativa",
  approved: "Aprovado",
  approval: "Situação das horas",
  previous_approval: "Situação anterior das horas",
  schema_version: "Versão da configuração",
  hours_version: "Versão das horas",
  previous_hours_version: "Versão anterior das horas",
  task_version: "Versão do card",
  sprint_id: "Sprint (ID)",
  previous_priority: "Prioridade anterior",
  comment_id: "Comentário (ID)",
  body: "Comentário",
  attachment_id: "Anexo (ID)",
  name: "Nome",
  size: "Tamanho em bytes",
  sha256: "Integridade SHA-256",
  status: "Etapa",
  estimate_policy: "Política de estimativa",
  backlog: "Backlog",
  todo: "A fazer",
  production: "Em produção",
  review: "Em revisão",
  done: "Concluído",
  pending: "Aguardando aprovação",
  approved_value: "Aprovado",
  rejected: "Rejeitado",
  resubmitted: "Reapresentado",
  required: "Obrigatória",
  absent: "Não incluída",
  optional: "Opcional",
  id: "Identificador",
  label: "Rótulo",
  type: "Tipo",
  options: "Opções",
  required_for: "Obrigatório nas etapas",
  visible_to: "Visível para",
  editable_by: "Editável por",
  native_key: "Campo nativo",
};
function value(field: string, item: unknown): string {
  if (item === null || item === undefined || item === "")
    return "Não preenchido / não registrado";
  if (typeof item === "boolean") return item ? "Sim" : "Não";
  if (field.endsWith("_minutes") && typeof item === "number")
    return `${Math.floor(item / 60)}h ${item % 60}min`;
  if (Array.isArray(item))
    return item.map((entry) => value(field, entry)).join(", ") || "Nenhum";
  if (typeof item === "object")
    return Object.entries(item)
      .map(([key, item]) => `${labels[key] ?? key}: ${value(key, item)}`)
      .join(" · ");
  const text = String(item);
  return labels[text === "approved" ? "approved_value" : text] ?? text;
}
export function HistoryTimeline({ identity }: { identity: number }) {
  const data = useQuery({
    queryKey: ["history", identity],
    queryFn: () => api<Entry[]>(`/audit?entity=task&identity=${identity}`),
  });
  return (
    <section aria-label="Histórico de versões do card">
      <h3>Histórico de versões</h3>
      <p>
        Cada registro identifica quem realizou a ação, quando ocorreu e quais
        dados foram alterados. Alterações antigas sem comparação registrada são
        sinalizadas.
      </p>
      {data.isPending && <p role="status">Carregando histórico…</p>}
      {data.isError && <p role="alert">{data.error.message}</p>}
      {data.data?.length === 0 && <p>Nenhum evento registrado.</p>}
      <ol className="timeline">
        {data.data?.map((row) => (
          <li key={row.id}>
            <strong>
              {row.action === "hours_submitted" && row.details.operation
                ? row.details.operation === "filled"
                  ? "Horas preenchidas"
                  : "Horas editadas / reapresentadas"
                : (actions[row.action] ?? row.action)}
            </strong>
            <small>
              Registro #{row.id} ·{" "}
              {row.actor_name || `Usuário #${row.actor_id}`} ·{" "}
              <time dateTime={row.created_at} title={row.created_at}>
                {formatTimestamp(row.created_at)}:
                {String(new Date(row.created_at).getUTCSeconds()).padStart(
                  2,
                  "0",
                )}
              </time>
            </small>
            {row.details.changes?.length ? (
              <div className="table-scroll">
                <table>
                  <caption>
                    Comparação da alteração · registro #{row.id}
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">Campo</th>
                      <th scope="col">Antes</th>
                      <th scope="col">Depois</th>
                    </tr>
                  </thead>
                  <tbody>
                    {row.details.changes.map((change, index) => (
                      <tr key={`${change.field}:${change.kind}:${index}`}>
                        <th scope="row">
                          {change.label ?? labels[change.field] ?? change.field}
                          {change.kind === "configuration"
                            ? " · configuração"
                            : ""}
                        </th>
                        <td>{value(change.field, change.before)}</td>
                        <td>{value(change.field, change.after)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              [
                "edited",
                "hours_submitted",
                "schema_versioned",
                "values_versioned",
              ].includes(row.action) && (
                <p>Comparação de valores não registrada nesta alteração.</p>
              )
            )}
            <dl className="audit-details">
              {Object.entries(row.details)
                .filter(
                  ([key]) =>
                    !["changes", "actor_name", "operation"].includes(key),
                )
                .map(([key, item]) => (
                  <div key={key}>
                    <dt>{labels[key] ?? key}</dt>
                    <dd>{value(key, item)}</dd>
                  </div>
                ))}
            </dl>
          </li>
        ))}
      </ol>
    </section>
  );
}
