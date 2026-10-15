import { useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  arrayMove,
  verticalListSortingStrategy,
  sortableKeyboardCoordinates,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { api } from "./api";
import {
  stages,
  approvals,
  decimalToUnits,
  hourInput,
  type Account,
  type Task,
  type Field,
} from "./types";
import { Label, type Run } from "./App";
const nativeLabels: Record<string, string> = {
  id: "Identificador",
  title: "Título",
  status: "Etapa",
  supplier_id: "Fornecedor responsável",
  sprint_id: "Sprint",
  estimated_minutes: "Horas previstas",
  used_minutes: "Horas utilizadas",
  approval: "Aprovação de horas",
};
const fieldTypes: Record<string, string> = {
  short_text: "Texto curto",
  long_text: "Texto longo",
  number: "Número",
  date: "Data",
  select: "Seleção",
  checkbox: "Checkbox",
  user: "Usuário",
  supplier: "Fornecedor",
  attachment: "Anexo",
};
function nativeDefinition(key: NonNullable<Field["native_key"]>): Field {
  return {
    id: "native_" + key,
    label: nativeLabels[key],
    type: "native",
    native_key: key,
    options: [],
    required_for: [],
    visible_to: ["admin", "manager", "internal", "supplier"],
    editable_by: ["estimated_minutes", "used_minutes"].includes(key)
      ? ["supplier"]
      : [],
  };
}
export function FieldValueForm({
  task,
  account,
  run,
}: {
  task: Task;
  account: Account;
  run: Run;
}) {
  const [values, setValues] = useState(task.values);
  if (!task.fields.length) return null;
  const fields = [...task.fields];
  const hasNativeHours = fields.some(
    (field) =>
      field.type === "native" &&
      ["estimated_minutes", "used_minutes"].includes(field.native_key ?? ""),
  );
  if (hasNativeHours && account.role === "supplier")
    for (const key of ["estimated_minutes", "used_minutes"] as const)
      if (
        !fields.some(
          (field) => field.type === "native" && field.native_key === key,
        )
      )
        fields.push(nativeDefinition(key));
  const formId = "values-form-" + task.id;
  return (
    <section className="inline-form">
      <h3>Campos do card</h3>
      {fields.map((field) =>
        field.type === "native" ? (
          <NativeField
            key={field.id}
            field={field}
            task={task}
            account={account}
            run={run}
          />
        ) : (
          <Label
            key={field.id}
            title={
              field.label +
              (field.required_for.length
                ? " · obrigatório em " +
                  field.required_for.map((status) => stages[status]).join(", ")
                : "")
            }
          >
            <FieldInput
              field={field}
              value={values[field.id]}
              formId={formId}
              taskId={task.id}
              disabled={
                !field.editable_by.includes(account.role) ||
                task.status === "done"
              }
              change={(value) => setValues({ ...values, [field.id]: value })}
            />
          </Label>
        ),
      )}
      <form
        id={formId}
        onSubmit={(event) => {
          event.preventDefault();
          const editable = Object.fromEntries(
            Object.entries(values).filter(([id]) => {
              const field = task.fields.find((row) => row.id === id);
              return (
                field &&
                field.type !== "native" &&
                field.editable_by.includes(account.role)
              );
            }),
          );
          run(() =>
            api(`/tasks/${task.id}/values`, "PUT", {
              version: task.version,
              values: editable,
            }),
          );
        }}
      >
        <button
          disabled={
            task.status === "done" ||
            !task.fields.some(
              (field) =>
                field.type !== "native" &&
                field.editable_by.includes(account.role),
            )
          }
        >
          Salvar campos
        </button>
      </form>
    </section>
  );
}
function NativeField({
  field,
  task,
  account,
  run,
}: {
  field: Field;
  task: Task;
  account: Account;
  run: Run;
}) {
  const key = field.native_key;
  const isHours = key === "estimated_minutes" || key === "used_minutes";
  const [value, setValue] = useState(isHours ? hourInput(task[key]) : "");
  if (isHours && account.role === "supplier")
    return (
      <form
        className="native-field"
        onSubmit={(event) => {
          event.preventDefault();
          run(() =>
            api(`/tasks/${task.id}/hours`, "PUT", {
              version: task.version,
              estimated_minutes:
                key === "estimated_minutes"
                  ? decimalToUnits(value, 60)
                  : task.estimated_minutes,
              used_minutes:
                key === "used_minutes"
                  ? decimalToUnits(value, 60)
                  : task.used_minutes,
            }),
          );
        }}
      >
        <Label title={field.label}>
          <input
            value={value}
            inputMode="decimal"
            onChange={(event) => setValue(event.target.value)}
            disabled={task.status === "done" || task.approval === "approved"}
          />
        </Label>
        <small>
          Campo nativo · horas decimais ou HH:MM · preenchimento exclusivo do
          fornecedor.
        </small>
        <button
          disabled={task.status === "done" || task.approval === "approved"}
        >
          Salvar {field.label}
        </button>
      </form>
    );
  const raw = key ? task[key] : "";
  const display =
    key === "status"
      ? stages[String(raw)]
      : key === "approval"
        ? approvals[String(raw)]
        : isHours
          ? String(Number(raw) / 60) + " h"
          : (raw ?? "Não definido");
  return (
    <Label title={field.label + " · nativo"}>
      <input value={String(display)} readOnly />
      <small>Alteração controlada pelo fluxo ou edição estrutural.</small>
    </Label>
  );
}
function FieldInput({
  field,
  value,
  disabled,
  change,
  taskId,
  formId,
}: {
  field: Field;
  value: any;
  disabled?: boolean;
  taskId?: number;
  formId?: string;
  change: (value: any) => void;
}) {
  const refs = useQuery({
    queryKey: ["fieldrefs", field.type, taskId],
    queryFn: () =>
      api<any[]>(
        field.type === "user"
          ? "/directory/users"
          : field.type === "supplier"
            ? "/suppliers"
            : `/tasks/${taskId}/attachments`,
      ),
    enabled:
      ["user", "supplier", "attachment"].includes(field.type) && !!taskId,
  });
  if (field.type === "native")
    return <input value={value ?? ""} readOnly disabled />;
  if (["user", "supplier", "attachment"].includes(field.type))
    return (
      <select
        form={formId}
        disabled={disabled}
        multiple={field.type === "attachment"}
        value={
          field.type === "attachment"
            ? (value ?? []).map(String)
            : String(value ?? "")
        }
        onChange={(event) =>
          change(
            field.type === "attachment"
              ? Array.from(event.target.selectedOptions, (option) =>
                  Number(option.value),
                )
              : event.target.value
                ? Number(event.target.value)
                : null,
          )
        }
      >
        {field.type !== "attachment" && <option value="">Selecione</option>}
        {refs.data?.map((row) => (
          <option key={row.id} value={row.id}>
            {row.name}
          </option>
        ))}
      </select>
    );
  if (field.type === "select")
    return (
      <select
        form={formId}
        disabled={disabled}
        value={value ?? ""}
        onChange={(event) => change(event.target.value)}
      >
        <option value="">Selecione</option>
        {field.options.map((option) => (
          <option key={option}>{option}</option>
        ))}
      </select>
    );
  if (field.type === "long_text")
    return (
      <textarea
        form={formId}
        disabled={disabled}
        value={value ?? ""}
        onChange={(event) => change(event.target.value)}
      />
    );
  return (
    <input
      form={formId}
      disabled={disabled}
      type={
        field.type === "checkbox"
          ? "checkbox"
          : field.type === "date"
            ? "date"
            : field.type === "number"
              ? "number"
              : "text"
      }
      checked={field.type === "checkbox" ? !!value : undefined}
      value={field.type === "checkbox" ? undefined : (value ?? "")}
      onChange={(event) =>
        change(
          field.type === "checkbox" ? event.target.checked : event.target.value,
        )
      }
    />
  );
}
function SortableField({
  field,
  children,
}: {
  field: Field;
  children: ReactNode;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({ id: field.id });
  return (
    <article
      className="builder-field"
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
    >
      <button
        {...attributes}
        {...listeners}
        aria-label={"Reordenar " + field.label}
      >
        ⠿
      </button>
      {children}
    </article>
  );
}
export function FieldBuilder({ task, run }: { task: Task; run: Run }) {
  const [fields, setFields] = useState<Field[]>(task.fields);
  const [preview, setPreview] = useState(false);
  const schemaQuery = useQuery({
    queryKey: ["card-schema", task.id, task.version],
    queryFn: async () => {
      const schema = await api<{ fields: Field[] }>(`/tasks/${task.id}/schema`);
      setFields(schema.fields);
      return schema;
    },
  });
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );
  if (schemaQuery.isPending)
    return <p role="status">Carregando configuração do card…</p>;
  if (schemaQuery.isError)
    return (
      <div role="alert">
        <p>{schemaQuery.error.message}</p>
        <button onClick={() => schemaQuery.refetch()}>Tentar novamente</button>
      </div>
    );
  function update(id: string, patch: Partial<Field>) {
    setFields(
      fields.map((field) => (field.id === id ? { ...field, ...patch } : field)),
    );
  }
  function add(key: string) {
    if (key.startsWith("native:")) {
      const nativeKey = key.slice(7) as NonNullable<Field["native_key"]>;
      if (
        !nativeLabels[nativeKey] ||
        fields.some(
          (field) => field.type === "native" && field.native_key === nativeKey,
        )
      )
        return;
      setFields([...fields, nativeDefinition(nativeKey)]);
    } else if (fieldTypes[key])
      setFields([
        ...fields,
        {
          id: "field_" + crypto.randomUUID().replaceAll("-", "").slice(0, 12),
          label: fieldTypes[key],
          type: key,
          options: [],
          required_for: [],
          visible_to: ["admin", "manager", "internal", "supplier"],
          editable_by: ["admin", "manager", "internal", "supplier"],
        },
      ]);
  }
  function libraryButton(key: string, label: string) {
    return (
      <button
        key={key}
        draggable
        onDragStart={(event) =>
          event.dataTransfer.setData("application/os-manager-field", key)
        }
        onClick={() => add(key)}
      >
        + {label}
      </button>
    );
  }
  return (
    <div
      className="builder"
      onDragOver={(event) => {
        if (event.dataTransfer.types.includes("application/os-manager-field"))
          event.preventDefault();
      }}
      onDrop={(event) => {
        const type = event.dataTransfer.getData("application/os-manager-field");
        if (type) {
          event.preventDefault();
          add(type);
        }
      }}
    >
      <p>
        Arraste um campo da biblioteca para esta área ou use os botões. Reordene
        pelo ícone ⠿ ou pelas ações Subir/Descer.
      </p>
      <div className="formula">
        Campos nativos continuam ligados aos registros estruturais. Sua
        presença, rótulo ou posição no card não desabilita horas, aprovação e
        autorização obrigatórias.
      </div>
      <h3>Biblioteca de campos adicionais</h3>
      <div className="field-library">
        {Object.entries(fieldTypes).map(([key, label]) =>
          libraryButton(key, label),
        )}
      </div>
      <h3>Campos nativos protegidos</h3>
      <div className="field-library">
        {Object.entries(nativeLabels).map(([key, label]) =>
          libraryButton("native:" + key, label + " (nativo)"),
        )}
      </div>
      <div className="actions">
        <button onClick={() => setPreview(!preview)}>
          {preview ? "Editar configuração" : "Pré-visualizar"}
        </button>
        <button
          className="primary"
          onClick={() =>
            run(() =>
              api(`/tasks/${task.id}/schema`, "PUT", {
                version: task.version,
                fields,
                values: {},
              }),
            )
          }
        >
          Salvar configuração
        </button>
      </div>
      {preview ? (
        fields.map((field) => (
          <Label key={field.id} title={field.label}>
            <FieldInput
              field={field}
              value={
                field.type === "native" && field.native_key
                  ? task[field.native_key]
                  : task.values[field.id]
              }
              change={() => {}}
              disabled
              taskId={task.id}
            />
          </Label>
        ))
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={(args) =>
            closestCenter({
              ...args,
              droppableContainers: args.droppableContainers.filter(
                (container) => container.id !== args.active.id,
              ),
            })
          }
          onDragEnd={({ active, over }) => {
            if (over && active.id !== over.id)
              setFields(
                arrayMove(
                  fields,
                  fields.findIndex((field) => field.id === active.id),
                  fields.findIndex((field) => field.id === over.id),
                ),
              );
          }}
        >
          <SortableContext
            items={fields.map((field) => field.id)}
            strategy={verticalListSortingStrategy}
          >
            {fields.map((field, index) => (
              <SortableField field={field} key={field.id}>
                <div>
                  <Label title="Rótulo">
                    <input
                      value={field.label}
                      onChange={(event) =>
                        update(field.id, { label: event.target.value })
                      }
                    />
                  </Label>
                  <small>
                    {field.type === "native"
                      ? "Nativo · " + field.native_key
                      : field.type}{" "}
                    · {field.id}
                  </small>
                  {field.type === "select" && (
                    <Label title="Opções separadas por vírgula">
                      <input
                        value={field.options.join(",")}
                        onChange={(event) =>
                          update(field.id, {
                            options: event.target.value.split(","),
                          })
                        }
                      />
                    </Label>
                  )}
                  <Label title="Obrigatório ao entrar em">
                    <select
                      multiple
                      value={field.required_for}
                      onChange={(event) =>
                        update(field.id, {
                          required_for: Array.from(
                            event.target.selectedOptions,
                            (option) => option.value,
                          ),
                        })
                      }
                    >
                      {Object.entries(stages).map(([id, label]) => (
                        <option key={id} value={id}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </Label>
                  <div className="form-grid">
                    {(["visible_to", "editable_by"] as const).map(
                      (property) => (
                        <Label
                          key={property}
                          title={
                            property === "visible_to"
                              ? "Perfis com visibilidade"
                              : "Perfis com edição"
                          }
                        >
                          <select
                            multiple
                            disabled={
                              field.type === "native" &&
                              property === "editable_by"
                            }
                            value={field[property]}
                            onChange={(event) =>
                              update(field.id, {
                                [property]: Array.from(
                                  event.target.selectedOptions,
                                  (option) => option.value,
                                ),
                              })
                            }
                          >
                            {["admin", "manager", "internal", "supplier"].map(
                              (role) => (
                                <option key={role}>{role}</option>
                              ),
                            )}
                          </select>
                        </Label>
                      ),
                    )}
                  </div>
                  <div className="actions">
                    <button
                      disabled={index === 0}
                      onClick={() =>
                        setFields(arrayMove(fields, index, index - 1))
                      }
                    >
                      ↑ Subir
                    </button>
                    <button
                      disabled={index === fields.length - 1}
                      onClick={() =>
                        setFields(arrayMove(fields, index, index + 1))
                      }
                    >
                      ↓ Descer
                    </button>
                    <button
                      onClick={() =>
                        setFields(fields.filter((row) => row.id !== field.id))
                      }
                    >
                      Remover campo
                    </button>
                  </div>
                </div>
              </SortableField>
            ))}
          </SortableContext>
        </DndContext>
      )}
    </div>
  );
}
