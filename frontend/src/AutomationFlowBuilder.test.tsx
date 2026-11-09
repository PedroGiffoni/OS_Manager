import { useState } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AutomationFlowBuilder } from "./AutomationFlowBuilder";
import type { AutomationRuleDraft, WorkflowAction } from "./automationTypes";

afterEach(cleanup);

const initialRule: AutomationRuleDraft = {
  name: "", trigger: "status_changed", schedule_time: "09:00", schedule_frequency: "daily", schedule_weekdays: [],
  action: "set_priority", priority: "0", label: "", comment: "", due_days: "14", assignee_user: "",
  custom_field_values: "{}", assignee_filter: "", due_window: "", overdue: "", color: "#2B4EDA",
  statuses: "", work_types: "", approval_states: "", priority_min: "", priority_max: "", labels: "", due_set: "",
  release_assigned: "", component_assigned: "", blocked: "", development_providers: "", development_event_types: "",
  development_states: "", comment_contains: "", attachment_media_types: "", link_types: "", changed_fields: "", sprint_scope_action: "",
};

function BuilderHarness({ onSave }: { onSave: () => void }) {
  const [rule, setRule] = useState(initialRule);
  const [actions, setActions] = useState<WorkflowAction[]>([]);
  const [enabled, setEnabled] = useState(true);
  const [dirty, setDirty] = useState(false);
  const [customFieldsJson, setCustomFieldsJson] = useState("");
  return <AutomationFlowBuilder rule={rule} setRule={setRule} actions={actions} setActions={setActions} enabled={enabled} setEnabled={setEnabled} actionDraftDirty={dirty} setActionDraftDirty={setDirty} customFieldsJson={customFieldsJson} setCustomFieldsJson={setCustomFieldsJson} users={[]} editingId={null} onSave={onSave} onCancel={vi.fn()} />;
}

describe("construtor visual de automações", () => {
  it("monta fluxo por gatilho, condição e ação antes de salvar", () => {
    const onSave = vi.fn();
    render(<BuilderHarness onSave={onSave} />);

    expect(screen.getByRole("heading", { name: "Adicionar gatilho" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Card criado/ }));
    fireEvent.click(screen.getByRole("button", { name: "Concluído" }));
    expect(screen.getByText("Card criado")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Adicionar condições/ }));
    fireEvent.change(screen.getByLabelText(/Status/), { target: { value: "production" } });
    fireEvent.click(screen.getByRole("button", { name: "Concluído" }));
    expect(screen.getByText("1 condição(ões) configurada(s)")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Adicionar ação" }));
    fireEvent.change(screen.getByLabelText("Comentário automático"), { target: { value: "Card pronto para revisão" } });
    fireEvent.click(screen.getByRole("button", { name: "Adicionar ao fluxo" }));
    expect(screen.getByText(/Adicionar comentário/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Nome da automação"), { target: { value: "Avisar sobre cards em produção" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar e ativar" }));
    expect(onSave).toHaveBeenCalledOnce();
  });
});
