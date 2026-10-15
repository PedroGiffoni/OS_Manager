import { formatTimestamp, hourInput } from "./types";
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  DndContext,
  pointerWithin,
  closestCorners,
  useDroppable,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
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
import { api } from "./api";
import {
  stages,
  approvals,
  money,
  decimalToUnits,
  type Account,
  type Task,
  type Supplier,
} from "./types";
import { Label, Empty, type Run } from "./App";
import { FieldBuilder, FieldValueForm } from "./Fields";
import { Collaboration } from "./Collaboration";
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
  const [creating, setCreating] = useState(false);
  const rows = useQuery({
    queryKey: ["tasks", query, page, search],
    queryFn: () =>
      api<Task[]>(
        `/tasks?${query}&q=${encodeURIComponent(search)}&offset=${page * 25}&limit=25`,
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
                        {stages[task.status]}
                      </span>
                    </td>
                    <td>
                      {suppliers.find((row) => row.id === task.supplier_id)
                        ?.name ?? "Não atribuído"}
                    </td>
                    <td>
                      {task.estimated_minutes / 60}h / {task.used_minutes / 60}h
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
  due: z.string(),
  priority: z.coerce.number().int(),
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
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof taskSchema>>({
    resolver: zodResolver(taskSchema),
    defaultValues: {
      title: task?.title ?? "",
      description: task?.description ?? "",
      supplier_id: task?.supplier_id?.toString() ?? "",
      due: task?.due ?? "",
      priority: task?.priority ?? 0,
    },
  });
  return (
    <form
      className="inline-form"
      onSubmit={handleSubmit((values) =>
        submit({
          ...values,
          supplier_id: values.supplier_id ? Number(values.supplier_id) : null,
          due: values.due || null,
          ...(task ? { version: task.version } : {}),
        }),
      )}
    >
      <Label title="Título">
        <input {...register("title")} />
      </Label>
      {errors.title && <small role="alert">{errors.title.message}</small>}
      <Label title="Descrição">
        <textarea {...register("description")} />
      </Label>
      <div className="form-grid">
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
        <Label title="Prazo">
          <input type="date" {...register("due")} />
        </Label>
        <Label title="Prioridade (menor aparece primeiro)">
          <input type="number" {...register("priority")} />
        </Label>
      </div>
      <button className="primary" disabled={isSubmitting}>
        Salvar atividade
      </button>
    </form>
  );
}
function DraggableTask({
  task,
  open,
}: {
  task: Task;
  open: (task: Task) => void;
}) {
  const { attributes, listeners, setNodeRef, transform } = useSortable({
    id: task.id,
  });
  return (
    <article
      ref={setNodeRef}
      className="kanban-card"
      style={{ transform: CSS.Translate.toString(transform) }}
    >
      <div className="card-top">
        <small>OS-{task.id}</small>
        <button
          {...listeners}
          {...attributes}
          aria-label={"Arrastar " + task.title}
        >
          ⠿
        </button>
      </div>
      <button className="card-title" onClick={() => open(task)}>
        {task.title}
      </button>
      <p>{task.description.slice(0, 95)}</p>
      <div>
        <span className="badge">{task.estimated_minutes / 60}h previstas</span>
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
  children,
  count,
}: {
  status: string;
  children: React.ReactNode;
  count: number;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  return (
    <section
      ref={setNodeRef}
      className={"kanban-column " + (isOver ? "over" : "")}
    >
      <h3>
        <i className={status} />
        {stages[status]}
        <span>{count}</span>
      </h3>
      {children}
    </section>
  );
}
export function Board({
  query,
  run,
  open,
}: {
  query: string;
  run: Run;
  open: (task: Task) => void;
}) {
  const rows = useQuery({
    queryKey: ["board", query],
    queryFn: () => api<Task[]>("/tasks?limit=200&" + query),
  });
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );
  const onDragEnd = (event: DragEndEvent) => {
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
  return (
    <>
      <div className="section-title">
        <h2>Quadro Kanban</h2>
        <span>Arraste pelo ícone ⠿ ou abra o card para mover pelo menu.</span>
      </div>
      {rows.isPending ? (
        <Empty>Carregando quadro…</Empty>
      ) : rows.isError ? (
        <Empty>{rows.error.message}</Empty>
      ) : (
        <DndContext
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
        >
          <div className="kanban">
            {Object.keys(stages).map((status) => (
              <Column
                key={status}
                status={status}
                count={
                  rows.data.filter((task) => task.status === status).length
                }
              >
                {
                  <SortableContext
                    items={rows.data
                      .filter((task) => task.status === status)
                      .map((task) => task.id)}
                    strategy={verticalListSortingStrategy}
                  >
                    {rows.data
                      .filter((task) => task.status === status)
                      .map((task) => (
                        <DraggableTask key={task.id} task={task} open={open} />
                      ))}
                  </SortableContext>
                }
              </Column>
            ))}
          </div>
        </DndContext>
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
  const [tab, setTab] = useState("activity");
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
          <button onClick={close} autoFocus aria-label="Fechar atividade">
            × Fechar
          </button>
        </div>
        <h2>{task.title}</h2>
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
          <History identity={identity} />
        ) : (
          <>
            <span className={"badge " + task.status}>
              {stages[task.status]}
            </span>
            <p>{task.description}</p>
            <p className={task.approval === "rejected" ? "rejection" : "muted"}>
              {approvals[task.approval]}{" "}
              {task.approval_reason && "— " + task.approval_reason}
            </p>
            {task.cost_cents !== undefined && (
              <p>
                Tarifa congelada:{" "}
                {task.rate_cents === null
                  ? "Sem tarifa"
                  : money(task.rate_cents ?? 0) + "/h"}{" "}
                · Custo aprovado: <strong>{money(task.cost_cents)}</strong>
              </p>
            )}
            <div className="actions">
              <Label title="Mover atividade">
                <select
                  value={task.status}
                  onChange={(e) => {
                    const status = e.target.value;
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
              ) && <HoursForm key={task.version} task={task} run={run} />}
            <p className="formula">
              Horas previstas são exigidas para produção. Horas utilizadas são
              exigidas para revisão. Conclusão exige gestor e aprovação.
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
    </div>
  );
}
function HoursForm({ task, run }: { task: Task; run: Run }) {
  const [estimated, setEstimated] = useState(hourInput(task.estimated_minutes));
  const [used, setUsed] = useState(hourInput(task.used_minutes));
  return (
    <form
      className="inline-form"
      onSubmit={(event) => {
        event.preventDefault();
        run(() =>
          api(`/tasks/${task.id}/hours`, "PUT", {
            version: task.version,
            estimated_minutes: decimalToUnits(estimated, 60),
            used_minutes: decimalToUnits(used, 60),
          }),
        );
      }}
    >
      <h3>Apontamento do fornecedor</h3>
      <div className="form-grid">
        <Label title="Horas previstas">
          <input
            inputMode="decimal"
            value={estimated}
            onChange={(event) => setEstimated(event.target.value)}
          />
        </Label>
        <Label title="Horas utilizadas (total)">
          <input
            inputMode="decimal"
            value={used}
            onChange={(event) => setUsed(event.target.value)}
          />
        </Label>
      </div>
      <button
        className="primary"
        disabled={task.status === "done" || task.approval === "approved"}
      >
        Salvar / reapresentar horas
      </button>
    </form>
  );
}
function History({ identity }: { identity: number }) {
  const data = useQuery({
    queryKey: ["history", identity],
    queryFn: () => api<any[]>(`/audit?entity=task&identity=${identity}`),
  });
  return (
    <ol className="timeline">
      {data.data?.map((row) => (
        <li key={row.id}>
          <strong>{row.action}</strong>
          <small>
            {formatTimestamp(row.created_at)} · usuário {row.actor_id}
          </small>
          <pre>{JSON.stringify(row.details, null, 2)}</pre>
        </li>
      ))}
      {data.isError && <p>{data.error.message}</p>}
    </ol>
  );
}
