import { formatTimestamp } from "./types";
import { useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import {
  money,
  decimalToUnits,
  type Task,
  type Supplier,
  type Sprint,
} from "./types";
import { Label, Empty, type Run } from "./App";
export function Sprints({
  rows,
  canManage,
  canReopen,
  run,
}: {
  rows: Sprint[];
  canManage: boolean;
  canReopen: boolean;
  run: Run;
}) {
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Sprint | null>(null);
  const [assigning, setAssigning] = useState<Sprint | null>(null);
  const [historyId, setHistoryId] = useState<number | null>(null);
  const historyRows = useQuery({
    queryKey: ["sprint-history", historyId],
    queryFn: () => api<Task[]>(`/sprints/${historyId}/history`),
    enabled: historyId !== null,
  });
  const backlog = useQuery({
    queryKey: ["eligible"],
    queryFn: () => api<Task[]>("/tasks?status=backlog&limit=200"),
    enabled: canManage,
  });
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    run(async () => {
      await api(
        "/sprints" +
          (editing ? `/${editing.id}?expected_version=${editing.version}` : ""),
        editing ? "PUT" : "POST",
        data,
      );
      setCreating(false);
      setEditing(null);
    });
  };
  return (
    <section className="panel">
      <div className="section-title">
        <h2>Sprints</h2>
        {canManage && (
          <button
            className="primary"
            onClick={() => {
              setEditing(null);
              setCreating(!creating);
            }}
          >
            + Nova sprint
          </button>
        )}
      </div>
      {creating && (
        <form
          key={editing?.id ?? "new"}
          className="inline-form"
          onSubmit={submit}
        >
          <Label title="Nome">
            <input name="name" defaultValue={editing?.name} required />
          </Label>
          <Label title="Objetivo">
            <textarea
              name="objective"
              defaultValue={editing?.objective}
              required
            />
          </Label>
          <div className="form-grid">
            <Label title="Início">
              <input
                type="date"
                name="starts"
                defaultValue={editing?.starts}
                required
              />
            </Label>
            <Label title="Término">
              <input
                type="date"
                name="ends"
                defaultValue={editing?.ends}
                required
              />
            </Label>
          </div>
          <button className="primary">
            {editing ? "Salvar sprint" : "Criar sprint"}
          </button>
        </form>
      )}
      {rows.map((row) => (
        <article className="sprint-row" key={row.id}>
          <div>
            <span className="badge">
              {
                { planned: "Planejada", active: "Ativa", closed: "Encerrada" }[
                  row.state
                ]
              }
            </span>
            <h3>{row.name}</h3>
            <p>{row.objective}</p>
            <small>
              {row.starts} → {row.ends}
            </small>
          </div>
          <button
            onClick={() => setHistoryId(historyId === row.id ? null : row.id)}
          >
            Consultar histórico
          </button>
          {canManage && (
            <div className="actions">
              {row.state !== "closed" && (
                <button
                  onClick={() =>
                    setAssigning(assigning?.id === row.id ? null : row)
                  }
                >
                  Adicionar do backlog
                </button>
              )}
              {row.state === "planned" && (
                <>
                  <button
                    onClick={() => {
                      setEditing(row);
                      setCreating(true);
                    }}
                  >
                    Editar sprint
                  </button>
                  <button
                    onClick={() => {
                      if (
                        window.confirm(
                          "Arquivar sprint planejada sem vínculos?",
                        )
                      )
                        run(() =>
                          api(
                            `/sprints/${row.id}?expected_version=${row.version}`,
                            "DELETE",
                          ),
                        );
                    }}
                  >
                    Arquivar sprint
                  </button>
                </>
              )}
              {row.state === "planned" && (
                <button
                  onClick={() =>
                    run(() =>
                      api(`/sprints/${row.id}/action`, "POST", {
                        version: row.version,
                        action: "start",
                      }),
                    )
                  }
                >
                  Iniciar sprint
                </button>
              )}
              {row.state === "active" && (
                <button
                  onClick={() => {
                    if (
                      window.confirm(
                        "Encerrar sprint e devolver tarefas pendentes ao backlog?",
                      )
                    )
                      run(() =>
                        api(`/sprints/${row.id}/action`, "POST", {
                          version: row.version,
                          action: "close",
                        }),
                      );
                  }}
                >
                  Encerrar sprint
                </button>
              )}
              {row.state === "closed" && canReopen && (
                <button
                  onClick={() => {
                    const reason = window.prompt("Justificativa da reabertura");
                    if (reason)
                      run(() =>
                        api(`/sprints/${row.id}/action`, "POST", {
                          version: row.version,
                          action: "reopen",
                          reason,
                        }),
                      );
                  }}
                >
                  Reabrir formalmente
                </button>
              )}
            </div>
          )}
          {assigning?.id === row.id && (
            <div className="inline-form">
              {backlog.data
                ?.filter((task) => !task.sprint_id)
                .map((task) => (
                  <button
                    key={task.id}
                    onClick={() =>
                      run(async () => {
                        const current = rows.find(
                          (item) => item.id === row.id,
                        )!;
                        await api(`/sprints/${row.id}/tasks`, "POST", {
                          version: current.version,
                          task_id: task.id,
                          task_version: task.version,
                        });
                      })
                    }
                  >
                    + #{task.id} {task.title}
                  </button>
                ))}
              {!backlog.data?.some((task) => !task.sprint_id) && (
                <p>Nenhuma atividade elegível.</p>
              )}
            </div>
          )}
        </article>
      ))}
      {historyId && (
        <section className="inline-form">
          <h3>Histórico da sprint #{historyId}</h3>
          <p>
            Somente leitura. Sprints encerradas preservam o retrato do
            encerramento.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Atividade</th>
                  <th>Etapa no retrato</th>
                  <th>Previstas / utilizadas</th>
                  <th>Aprovação</th>
                </tr>
              </thead>
              <tbody>
                {historyRows.data?.map((task) => (
                  <tr key={task.id}>
                    <td>{task.title}</td>
                    <td>{task.status}</td>
                    <td>
                      {task.estimated_minutes / 60}h / {task.used_minutes / 60}h
                    </td>
                    <td>{task.approval}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {historyRows.error && <p>{historyRows.error.message}</p>}
        </section>
      )}
      {!rows.length && <Empty>Nenhuma sprint disponível.</Empty>}
    </section>
  );
}
export function Suppliers({
  rows,
  canManage,
  canRate,
  financial,
  run,
}: {
  rows: Supplier[];
  canManage: boolean;
  canRate: boolean;
  financial: boolean;
  run: Run;
}) {
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Supplier | null>(null);
  const [creating, setCreating] = useState(false);
  const [history, setHistory] = useState<number | null>(null);
  const rates = useQuery({
    queryKey: ["rates", history],
    queryFn: () => api<any[]>(`/suppliers/${history}/rates`),
    enabled: history !== null && financial,
  });
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    run(async () => {
      const payload = {
        name: data.get("name"),
        function: data.get("function"),
        user_id:
          editing?.user_id ??
          (data.get("user_id") ? Number(data.get("user_id")) : null),
        active: editing?.active ?? canRate,
        ...(!editing
          ? {
              initial_rate_cents: data.get("rate")
                ? decimalToUnits(String(data.get("rate")), 100)
                : null,
            }
          : {}),
      };
      const supplier = await api<Supplier>(
        "/suppliers" + (editing ? "/" + editing.id : ""),
        editing ? "PUT" : "POST",
        payload,
      );
      if (editing && data.get("rate"))
        await api(`/suppliers/${supplier.id}/rates`, "POST", {
          cents: decimalToUnits(String(data.get("rate")), 100),
          reason: String(data.get("reason") ?? ""),
        });
      setCreating(false);
      setEditing(null);
    });
  };
  return (
    <section className="panel">
      <div className="section-title">
        <h2>Fornecedores</h2>
        {canManage && (
          <button
            className="primary"
            onClick={() => {
              setCreating(!creating);
              setEditing(null);
            }}
          >
            + Cadastrar fornecedor
          </button>
        )}
      </div>
      <Label title="Pesquisar fornecedor">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Nome ou função"
        />
      </Label>
      {(creating || editing) && (
        <form
          key={editing?.id ?? "new"}
          className="inline-form"
          onSubmit={submit}
        >
          <div className="form-grid">
            <Label title="Nome">
              <input name="name" defaultValue={editing?.name} required />
            </Label>
            <Label title="Função">
              <input
                name="function"
                defaultValue={editing?.function}
                required
              />
            </Label>
            {!editing && (
              <Label title="ID da conta de fornecedor (opcional)">
                <input type="number" name="user_id" />
              </Label>
            )}
            {canRate && (
              <Label title="Nova tarifa por hora (R$)">
                <input inputMode="decimal" name="rate" required={!editing} />
              </Label>
            )}
          </div>
          {canRate && (
            <Label title="Motivo do reajuste">
              <input name="reason" />
            </Label>
          )}
          <div className="actions">
            <button className="primary">Salvar fornecedor</button>
            <button
              type="button"
              onClick={() => {
                setCreating(false);
                setEditing(null);
              }}
            >
              Cancelar
            </button>
          </div>
        </form>
      )}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Fornecedor</th>
              <th>Função</th>
              <th>Situação</th>
              {financial && <th>Valor / hora</th>}
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {rows
              .filter((row) =>
                (row.name + " " + row.function)
                  .toLowerCase()
                  .includes(search.toLowerCase()),
              )
              .map((row) => (
                <tr key={row.id}>
                  <td>
                    <strong>{row.name}</strong>
                    <small>FOR-{row.id}</small>
                  </td>
                  <td>{row.function}</td>
                  <td>
                    <span className="badge">
                      {row.active ? "Ativo" : "Inativo"}
                    </span>
                  </td>
                  {financial && (
                    <td>
                      {row.rate_cents ? money(row.rate_cents) : "Sem tarifa"}
                    </td>
                  )}
                  <td>
                    <div className="actions">
                      {canManage && (
                        <>
                          <button
                            onClick={() => {
                              setEditing(row);
                              setCreating(false);
                            }}
                          >
                            Editar
                          </button>
                          <button
                            onClick={() =>
                              run(() =>
                                api("/suppliers/" + row.id, "PUT", {
                                  name: row.name,
                                  function: row.function,
                                  user_id: row.user_id,
                                  active: !row.active,
                                }),
                              )
                            }
                          >
                            {row.active ? "Desativar" : "Ativar"}
                          </button>
                        </>
                      )}
                      {financial && (
                        <button
                          onClick={() =>
                            setHistory(history === row.id ? null : row.id)
                          }
                        >
                          Tarifas
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
      {history && (
        <section className="inline-form">
          <h3>Histórico de tarifas · FOR-{history}</h3>
          {rates.data?.map((row) => (
            <p key={row.id}>
              {money(row.cents)}/h · {formatTimestamp(row.created_at)} ·{" "}
              {row.reason}
            </p>
          ))}
        </section>
      )}
    </section>
  );
}
export function Administration({ run }: { run: Run }) {
  const users = useQuery({
    queryKey: ["users"],
    queryFn: () => api<any[]>("/users"),
  });
  const permissions = useQuery({
    queryKey: ["permissions"],
    queryFn: () => api<string[]>("/permissions"),
  });
  const [role, setRole] = useState("supplier");
  const [selected, setSelected] = useState<string[]>([]);
  const [editing, setEditing] = useState<any>(null);
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    run(async () => {
      if (editing) await api(`/users/${editing.id}/grants`, "PUT", selected);
      else
        await api("/users", "POST", {
          ...values,
          role,
          grants: role === "supplier" ? [] : selected,
        });
      setEditing(null);
      setSelected([]);
    });
  };
  return (
    <section className="panel">
      <h2>Administração e permissões</h2>
      <p>
        Papel e autorização são independentes. Gestor precisa de concessão
        explícita para aprovar horas e consultar finanças.
      </p>
      <form className="inline-form" onSubmit={submit}>
        <h3>
          {editing
            ? "Permissões de " + editing.username
            : "Criar conta individual"}
        </h3>
        {!editing && (
          <div className="form-grid">
            <Label title="Usuário">
              <input
                name="username"
                minLength={3}
                required
                autoComplete="off"
              />
            </Label>
            <Label title="Senha inicial (mínimo 12 caracteres)">
              <input
                type="password"
                name="password"
                minLength={12}
                required
                autoComplete="new-password"
              />
            </Label>
            <Label title="Perfil">
              <select
                value={role}
                onChange={(event) => setRole(event.target.value)}
              >
                {["supplier", "internal", "manager", "admin"].map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </select>
            </Label>
          </div>
        )}
        {(editing || role !== "supplier") && (
          <fieldset>
            <legend>Permissões explícitas</legend>
            <div className="permissions">
              {permissions.data?.map((permission) => (
                <Label key={permission} title={permission}>
                  <input
                    type="checkbox"
                    checked={selected.includes(permission)}
                    onChange={(event) =>
                      setSelected(
                        event.target.checked
                          ? [...selected, permission]
                          : selected.filter((value) => value !== permission),
                      )
                    }
                  />
                </Label>
              ))}
            </div>
          </fieldset>
        )}
        <button className="primary">
          {editing ? "Salvar permissões" : "Criar usuário"}
        </button>
        {editing && (
          <button type="button" onClick={() => setEditing(null)}>
            Cancelar
          </button>
        )}
      </form>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Conta</th>
              <th>Perfil</th>
              <th>Concessões</th>
              <th>Ação</th>
            </tr>
          </thead>
          <tbody>
            {users.data?.map((user) => (
              <tr key={user.id}>
                <td>
                  #{user.id} {user.username}
                </td>
                <td>{user.role}</td>
                <td>
                  {user.grants.join(", ") || "Nenhuma concessão adicional"}
                </td>
                <td>
                  {user.role !== "supplier" && (
                    <button
                      onClick={() => {
                        setEditing(user);
                        setSelected(user.grants);
                      }}
                    >
                      Configurar acesso
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
