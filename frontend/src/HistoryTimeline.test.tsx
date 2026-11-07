import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";
import { HistoryTimeline } from "./HistoryTimeline";

vi.mock("./api", () => ({ api: vi.fn() }));

const rows = [
  {
    id: 10,
    actor_id: 2,
    actor_name: "Ana",
    action: "created",
    created_at: "2026-11-07T10:00:00Z",
    details: {},
  },
  {
    id: 11,
    actor_id: 2,
    actor_name: "Ana",
    action: "edited",
    created_at: "2026-11-07T11:00:00Z",
    details: { changes: [{ field: "title", before: "Rascunho", after: "Demanda" }] },
  },
  {
    id: 12,
    actor_id: 3,
    actor_name: "Bia",
    action: "status_changed",
    created_at: "2026-11-07T12:00:00Z",
    details: { origin: "backlog", destination: "todo" },
  },
];

describe("comparação visual do histórico", () => {
  beforeEach(() => {
    vi.mocked(api).mockResolvedValue(rows);
  });

  it("mostra diferenças de campo e etapa entre os registros selecionados", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <HistoryTimeline identity={42} />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(screen.getByText("Demanda")).toBeTruthy());
    expect(screen.getByRole("table", { name: /Diferenças entre os registros #10 e #12/i })).toBeTruthy();
    const comparison = screen.getByRole("table", {
      name: /Diferenças entre os registros #10 e #12/i,
    });
    expect(within(comparison).getByRole("cell", { name: "Rascunho" })).toBeTruthy();
    expect(within(comparison).getByRole("cell", { name: "Backlog" })).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Versão final"), { target: { value: "11" } });
    await waitFor(() =>
      expect(screen.getByText("Diferenças entre os registros #10 e #11")).toBeTruthy(),
    );
    const updatedComparison = screen.getByRole("table", {
      name: /Diferenças entre os registros #10 e #11/i,
    });
    expect(within(updatedComparison).queryByText("Etapa")).toBeNull();
  });
});
