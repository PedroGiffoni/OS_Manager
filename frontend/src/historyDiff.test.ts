import { describe, expect, it } from "vitest";
import { compareHistoryVersions, type HistoryEntry } from "./historyDiff";

const entries: HistoryEntry[] = [
  { id: 1, action: "created", details: {} },
  {
    id: 2,
    action: "edited",
    details: {
      changes: [
        { field: "title", before: "Rascunho", after: "Demanda A" },
        { field: "secret_rate", before: 120, after: 150 },
      ],
    },
  },
  {
    id: 3,
    action: "status_changed",
    details: { origin: "backlog", destination: "todo" },
  },
  {
    id: 4,
    action: "edited",
    details: {
      changes: [{ field: "title", before: "Demanda A", after: "Demanda B" }],
    },
  },
];

describe("comparação entre versões do card", () => {
  it("compõe o valor inicial e final e inclui a transição de etapa", () => {
    expect(compareHistoryVersions(entries, 1, 4)).toEqual([
      { field: "title", before: "Rascunho", after: "Demanda B" },
      { field: "secret_rate", before: 120, after: 150 },
      {
        field: "status",
        label: "Etapa",
        before: "backlog",
        after: "todo",
      },
    ]);
  });

  it("não mostra campos removidos pela filtragem de autorização da API", () => {
    const authorized = entries.map((entry) => ({
      ...entry,
      details: {
        ...entry.details,
        changes: entry.details.changes?.filter(
          (change) => change.field !== "secret_rate",
        ),
      },
    }));
    expect(compareHistoryVersions(authorized, 1, 4).map((item) => item.field)).toEqual([
      "title",
      "status",
    ]);
  });

  it("ignora mudanças que foram revertidas dentro do intervalo", () => {
    const reverted: HistoryEntry[] = [
      { id: 1, action: "created", details: {} },
      {
        id: 2,
        action: "edited",
        details: { changes: [{ field: "title", before: "A", after: "B" }] },
      },
      {
        id: 3,
        action: "edited",
        details: { changes: [{ field: "title", before: "B", after: "A" }] },
      },
    ];
    expect(compareHistoryVersions(reverted, 1, 3)).toEqual([]);
  });
});
