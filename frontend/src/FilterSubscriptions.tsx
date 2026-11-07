import { useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { BellRing, Pencil, Play, Plus, Trash2, X } from "lucide-react";
import { api } from "./api";
import { Empty, Label, type Run } from "./App";

type FilterSubscription = {
  id: number;
  name: string;
  query: string;
  frequency: "daily" | "weekly";
  active: boolean;
  match_count: number;
  next_run_at: string;
  last_run_at: string | null;
  last_error: string;
  created_at: string;
};
type Draft = Pick<FilterSubscription, "name" | "query" | "frequency" | "active">;
const emptyDraft: Draft = { name: "", query: "", frequency: "daily", active: true };

function formatDate(value: string | null) {
  return value
    ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value))
    : "Ainda não executada";
}

export function FilterSubscriptions({ run }: { run: Run }) {
  const subscriptions = useQuery({
    queryKey: ["filter-subscriptions"],
    queryFn: () => api<FilterSubscription[]>("/filter-subscriptions"),
  });
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [editing, setEditing] = useState<number | null>(null);

  const reset = () => {
    setDraft(emptyDraft);
    setEditing(null);
  };
  const save = (event: FormEvent) => {
    event.preventDefault();
    void run(async () => {
      if (editing === null) await api("/filter-subscriptions", "POST", draft);
      else await api(`/filter-subscriptions/${editing}`, "PUT", draft);
      reset();
    });
  };
  const edit = (row: FilterSubscription) => {
    setEditing(row.id);
    setDraft({ name: row.name, query: row.query, frequency: row.frequency, active: row.active });
  };
  const update = (row: FilterSubscription, active: boolean) =>
    run(() => api(`/filter-subscriptions/${row.id}`, "PUT", { name: row.name, query: row.query, frequency: row.frequency, active }));

  return (
    <section className="filter-subscriptions">
      <div className="section-title">
        <div>
          <span className="eyebrow">BUSCA E ACOMPANHAMENTO</span>
          <h2>Assinaturas de filtros</h2>
          <p className="muted">Receba avisos internos quando novas atividades entrarem nos resultados da sua consulta.</p>
        </div>
        <BellRing size={24} aria-hidden="true" />
      </div>

      <section className="panel">
        <h3>{editing === null ? "Criar assinatura" : "Editar assinatura"}</h3>
        <p className="muted">A assinatura registra os resultados atuais como ponto inicial. Você recebe avisos de novas correspondências; cards já encontrados não geram alerta ao criar ou editar.</p>
        <form className="form-grid" onSubmit={save}>
          <Label title="Nome"><input maxLength={100} required value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} placeholder="Ex.: Itens aguardando revisão" /></Label>
          <Label title="Periodicidade"><select value={draft.frequency} onChange={(event) => setDraft({ ...draft, frequency: event.target.value as Draft["frequency"] })}><option value="daily">Diária</option><option value="weekly">Semanal</option></select></Label>
          <Label title="Consulta avançada"><textarea required maxLength={1000} rows={3} value={draft.query} onChange={(event) => setDraft({ ...draft, query: event.target.value })} placeholder={'status = "review" AND due IS EMPTY'} /></Label>
          <p className="muted">A consulta usa a sintaxe avançada disponível no quadro, como status, prioridade, fornecedor, sprint, prazo, etiquetas e campos personalizados. Cada conta mantém até 20 assinaturas.</p>
          <div className="actions">
            <button className="primary" type="submit" disabled={!draft.name.trim() || !draft.query.trim() || (editing === null && (subscriptions.data?.length ?? 0) >= 20)}><Plus size={16} /> {editing === null ? "Criar assinatura" : "Salvar alterações"}</button>
            {editing !== null && <button type="button" onClick={reset}><X size={16} /> Cancelar edição</button>}
          </div>
        </form>
      </section>

      <section className="panel">
        <div className="section-title"><h3>Filtros acompanhados</h3><span>{subscriptions.data?.length ?? 0} de 20</span></div>
        {subscriptions.isPending ? <Empty>Carregando assinaturas…</Empty> : subscriptions.isError ? <p role="alert" className="rejection">{subscriptions.error.message}</p> : !subscriptions.data?.length ? <Empty>Nenhuma assinatura criada.</Empty> : <div className="subscription-list">
          {subscriptions.data.map((row) => <article className="subscription-card" key={row.id}>
            <div className="section-title"><div><h4>{row.name}</h4><span className={`badge ${row.active ? "done" : "review"}`}>{row.active ? "Ativa" : "Pausada"} · {row.frequency === "daily" ? "diária" : "semanal"}</span></div><div className="actions"><button type="button" aria-label={`Editar assinatura ${row.name}`} onClick={() => edit(row)}><Pencil size={15} /> Editar</button><button type="button" onClick={() => void update(row, !row.active)}>{row.active ? "Pausar" : <><Play size={15} /> Retomar</>}</button><button className="danger" type="button" aria-label={`Excluir assinatura ${row.name}`} onClick={() => { if (window.confirm(`Excluir a assinatura “${row.name}”?`)) void run(() => api(`/filter-subscriptions/${row.id}`, "DELETE")); }}><Trash2 size={15} /> Excluir</button></div></div>
            <code className="subscription-query">{row.query}</code>
            <div className="subscription-meta"><span>{row.match_count} correspondência(s) na última verificação</span><span>Próxima verificação: {formatDate(row.next_run_at)}</span><span>Última verificação: {formatDate(row.last_run_at)}</span></div>
            {row.last_error && <p className="rejection" role="alert">{row.last_error}</p>}
          </article>)}
        </div>}
      </section>
      <p className="muted">Os avisos aparecem na central de notificações da aplicação. Envio de e-mail ou notificações push não é necessário e não está incluído nesta assinatura.</p>
    </section>
  );
}
