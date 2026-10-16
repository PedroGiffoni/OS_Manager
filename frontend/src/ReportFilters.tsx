import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api";
import { Label } from "./App";

export interface ReportCondition {
  field: string;
  op: string;
  value: string;
  value_to: string;
}
interface Definition {
  key: string;
  label: string;
  type: string;
  source: string;
  operators: string[];
  options: { value: string; label: string }[];
}
const operators: Record<string, string> = {
  contains: "Contém",
  eq: "Igual a",
  gte: "Maior ou igual / a partir de",
  lte: "Menor ou igual / até",
  between: "Entre",
  empty: "Não preenchido",
  not_empty: "Preenchido",
};
export function ReportFilters({
  sprintId,
  onApply,
}: {
  sprintId: string | null;
  onApply: (conditions: ReportCondition[]) => void;
}) {
  const [conditions, setConditions] = useState<
    (ReportCondition & { id: string })[]
  >([]);
  const catalogue = useQuery({
    queryKey: ["report-fields", sprintId],
    queryFn: () =>
      api<Definition[]>(
        "/reports/fields" + (sprintId ? `?sprint_id=${sprintId}` : ""),
      ),
  });
  function update(id: string, patch: Partial<ReportCondition>) {
    setConditions((current) =>
      current.map((row) => (row.id === id ? { ...row, ...patch } : row)),
    );
  }
  return (
    <section className="panel report-filter-panel">
      <h2>Filtros por campos do card</h2>
      <p>
        Combine os itens desejados. A atividade deve atender a todos os filtros.
        A descrição não é usada como filtro.
      </p>
      <p className="formula">
        Horas em horas decimais; valores monetários em reais. Campos
        personalizados pertencem aos cards onde foram configurados. Campos com o
        mesmo nome são identificados pelo card.
      </p>
      {catalogue.isPending && (
        <p role="status">Carregando campos disponíveis…</p>
      )}
      {catalogue.isError && (
        <div role="alert">
          <p>{catalogue.error.message}</p>
          <button onClick={() => catalogue.refetch()}>Tentar novamente</button>
        </div>
      )}
      {catalogue.data && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            onApply(
              conditions.map(({ field, op, value, value_to }) => ({
                field,
                op,
                value,
                value_to,
              })),
            );
          }}
        >
          {conditions.length === 0 && (
            <p>
              Nenhum filtro de campo selecionado. Serão usados os filtros de
              acompanhamento acima.
            </p>
          )}
          {conditions.map((row, index) => {
            const field = catalogue.data.find(
              (item) => item.key === row.field,
            )!;
            if (!field)
              return (
                <fieldset key={row.id} className="report-condition">
                  <legend>Filtro {index + 1}</legend>
                  <p role="alert">
                    Campo não está mais disponível. Remova este filtro.
                  </p>
                  <button
                    type="button"
                    onClick={() =>
                      setConditions((current) =>
                        current.filter((item) => item.id !== row.id),
                      )
                    }
                  >
                    Remover filtro {index + 1}
                  </button>
                </fieldset>
              );
            const unary = ["empty", "not_empty"].includes(row.op);
            const selection = [
              "select",
              "checkbox",
              "user",
              "supplier",
              "sprint",
            ].includes(field.type);
            const valueInput = (final: boolean) => (
              <Label
                title={
                  (final ? "Valor final do filtro " : "Valor do filtro ") +
                  (index + 1)
                }
              >
                {selection ? (
                  <select
                    aria-label={"Valor do filtro " + (index + 1)}
                    required
                    value={row.value}
                    onChange={(event) =>
                      update(row.id, { value: event.target.value })
                    }
                  >
                    <option value="">Selecione</option>
                    {field.options.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    aria-label={
                      (final ? "Valor final do filtro " : "Valor do filtro ") +
                      (index + 1)
                    }
                    required
                    maxLength={2000}
                    type={field.type === "date" ? "date" : "text"}
                    inputMode={
                      ["number", "hours", "money"].includes(field.type)
                        ? "decimal"
                        : undefined
                    }
                    placeholder={
                      field.type === "hours"
                        ? "Ex.: 8 ou 1,5"
                        : field.type === "attachment"
                          ? "Nome do arquivo"
                          : undefined
                    }
                    value={final ? row.value_to : row.value}
                    onChange={(event) =>
                      update(
                        row.id,
                        final
                          ? { value_to: event.target.value }
                          : { value: event.target.value },
                      )
                    }
                  />
                )}
              </Label>
            );
            return (
              <fieldset key={row.id} className="report-condition">
                <legend>Filtro {index + 1}</legend>
                <div className="report-condition-grid">
                  <Label title={"Campo do filtro " + (index + 1)}>
                    <select
                      aria-label={"Campo do filtro " + (index + 1)}
                      value={row.field}
                      onChange={(event) => {
                        const chosen = catalogue.data.find(
                          (item) => item.key === event.target.value,
                        )!;
                        update(row.id, {
                          field: chosen.key,
                          op: chosen.operators[0],
                          value: "",
                          value_to: "",
                        });
                      }}
                    >
                      {["native", "custom"].map((source) => (
                        <optgroup
                          key={source}
                          label={
                            source === "native"
                              ? "Campos nativos"
                              : "Campos personalizados dos cards"
                          }
                        >
                          {catalogue.data
                            .filter((item) => item.source === source)
                            .map((item) => (
                              <option key={item.key} value={item.key}>
                                {item.label}
                              </option>
                            ))}
                        </optgroup>
                      ))}
                    </select>
                  </Label>
                  <Label title={"Condição do filtro " + (index + 1)}>
                    <select
                      aria-label={"Condição do filtro " + (index + 1)}
                      value={row.op}
                      onChange={(event) =>
                        update(row.id, { op: event.target.value })
                      }
                    >
                      {field.operators.map((op) => (
                        <option key={op} value={op}>
                          {operators[op]}
                        </option>
                      ))}
                    </select>
                  </Label>
                  {!unary && valueInput(false)}
                  {!unary && row.op === "between" && valueInput(true)}
                  <button
                    type="button"
                    aria-label={"Remover filtro " + (index + 1)}
                    onClick={() =>
                      setConditions((current) =>
                        current.filter((item) => item.id !== row.id),
                      )
                    }
                  >
                    Remover
                  </button>
                </div>
              </fieldset>
            );
          })}
          <div className="actions">
            <button
              type="button"
              disabled={conditions.length >= 30}
              onClick={() =>
                setConditions((current) => [
                  ...current,
                  {
                    id: crypto.randomUUID(),
                    field: "native:title",
                    op: "contains",
                    value: "",
                    value_to: "",
                  },
                ])
              }
            >
              + Adicionar filtro
            </button>
            <button
              type="submit"
              className="primary"
              disabled={conditions.some(
                (row) => !catalogue.data.some((item) => item.key === row.field),
              )}
            >
              Aplicar filtros
            </button>
            <button
              type="button"
              onClick={() => {
                setConditions([]);
                onApply([]);
              }}
            >
              Limpar filtros de campos
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
