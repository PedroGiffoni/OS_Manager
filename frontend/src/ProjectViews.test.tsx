import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { boardQuickFilters, CalendarView, filterBoardTasks, isQuickFilterQueryAllowed, ProjectTable, QuickFilters, TimelineView, timelineDependencies, ViewTools } from "./ProjectViews";
import type { Account, Task } from "./types";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("calendário de demandas", () => {
  it("permite agendar um card sem prazo por arrastar e preserva o início viável", () => {
    const today = new Date();
    const due = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
    const task = { id: 42, title: "Revisar calendário", status: "backlog", due: null, planned_start: null } as Task;
    const saveSchedule = vi.fn();
    render(<CalendarView tasks={[task]} open={vi.fn()} canSchedule saveSchedule={saveSchedule} />);

    const card = screen.getByRole("button", { name: /OS-42/ });
    fireEvent.dragStart(card, { dataTransfer: { setData: vi.fn(), effectAllowed: "" } });
    fireEvent.drop(screen.getByLabelText(`Soltar card no dia ${due}`), {
      dataTransfer: { getData: () => "42" },
    });

    expect(saveSchedule).toHaveBeenCalledWith(task, "", due);
  });

  it("oferece exportação do calendário no formato iCalendar", () => {
    const onExportCalendar = vi.fn();
    render(<CalendarView tasks={[]} open={vi.fn()} onExportCalendar={onExportCalendar} />);

    fireEvent.click(screen.getByRole("button", { name: "Exportar .ics" }));

    expect(onExportCalendar).toHaveBeenCalledOnce();
  });

  it("mostra endereço e chave de feed pessoal e oferece ações de cópia/revogação", () => {
    const onCopyUrl = vi.fn();
    const onCopySecret = vi.fn();
    const onRevoke = vi.fn();
    render(<CalendarView
      tasks={[]}
      open={vi.fn()}
      calendarFeedActive
      calendarFeedUrl="https://app.example.test/api/v1/calendar/feed.ics"
      calendarFeedSecret="chave-unica-de-teste"
      onCreateCalendarFeed={vi.fn()}
      onRevokeCalendarFeed={onRevoke}
      onCopyCalendarFeedUrl={onCopyUrl}
      onCopyCalendarFeedSecret={onCopySecret}
    />);

    expect(screen.getByLabelText("Endereço do feed")).toHaveValue("https://app.example.test/api/v1/calendar/feed.ics");
    expect(screen.getByLabelText("Chave de acesso — exibida somente agora")).toHaveValue("chave-unica-de-teste");
    fireEvent.click(screen.getByRole("button", { name: "Copiar endereço" }));
    fireEvent.click(screen.getByRole("button", { name: "Copiar chave" }));
    fireEvent.click(screen.getByRole("button", { name: "Revogar assinatura" }));
    expect(onCopyUrl).toHaveBeenCalledOnce();
    expect(onCopySecret).toHaveBeenCalledOnce();
    expect(onRevoke).toHaveBeenCalledOnce();
  });
});

describe("filtros avançados das views", () => {
  it("expõe a consulta avançada e encaminha a edição", () => {
    const onAdvancedQuery = vi.fn();
    render(
      <ViewTools
        views={[]}
        activeId={null}
        currentUserId={1}
        layout="board"
        query=""
        advancedQuery=""
        groupBy=""
        sortBy=""
        zoom="quarter"
        fields={[]}
        visibleFields={[]}
        sliceBy=""
        sliceValue=""
        sliceOptions={[]}
        sumBy=""
        descending={false}
        financial={false}
        shared={false}
        sharedRoles={[]}
        sharedGroupIds={[]}
        groups={[]}
        canShare={false}
        onSelect={vi.fn()}
        onLayout={vi.fn()}
        onQuery={vi.fn()}
        onAdvancedQuery={onAdvancedQuery}
        onGroup={vi.fn()}
        onSort={vi.fn()}
        onZoom={vi.fn()}
        onToggleField={vi.fn()}
        onMoveField={vi.fn()}
        onSliceBy={vi.fn()}
        onSliceValue={vi.fn()}
        onSum={vi.fn()}
        onDirection={vi.fn()}
        onShared={vi.fn()}
        onSharedRoles={vi.fn()}
        onSharedGroupIds={vi.fn()}
        onRename={vi.fn()}
        onMoveView={vi.fn()}
        onSave={vi.fn()}
        onDuplicate={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    const filtersToggle = screen.getByRole("button", { name: /Visualizações e filtros/ });
    expect(filtersToggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByLabelText("Consulta avançada (servidor)")).not.toBeVisible();
    fireEvent.click(filtersToggle);
    expect(filtersToggle).toHaveAttribute("aria-expanded", "true");

    const input = screen.getByLabelText("Consulta avançada (servidor)");
    fireEvent.change(input, {
      target: { value: 'status = "review" ORDER BY due ASC' },
    });

    expect(onAdvancedQuery).toHaveBeenCalledWith(
      'status = "review" ORDER BY due ASC',
    );
    expect(screen.getByText(/Use AND\/OR, parênteses/)).toBeInTheDocument();
  });
});

describe("filtros rápidos do quadro", () => {
  it("aceita somente consultas simples permitidas para o quadro", () => {
    expect(isQuickFilterQueryAllowed('status:"Em produção" no:sprint')).toBe(true);
    expect(isQuickFilterQueryAllowed('status = "production"')).toBe(false);
    expect(isQuickFilterQueryAllowed("status:review OR status:done")).toBe(false);
    expect(isQuickFilterQueryAllowed("priority:>=4")).toBe(true);
    expect(isQuickFilterQueryAllowed("")).toBe(false);
  });

  it("ativa e remove filtros por botões acessíveis", () => {
    const onChange = vi.fn();
    const onFiltersChange = vi.fn();
    const { rerender } = render(<QuickFilters filters={boardQuickFilters} active={[]} onChange={onChange} onFiltersChange={onFiltersChange} />);
    const overdue = screen.getByRole("button", { name: "Atrasadas" });
    expect(overdue).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(overdue);
    expect(onChange).toHaveBeenCalledWith(["overdue"]);

    rerender(<QuickFilters filters={boardQuickFilters} active={["overdue", "no-sprint"]} onChange={onChange} onFiltersChange={onFiltersChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Atrasadas" }));
    expect(onChange).toHaveBeenLastCalledWith(["no-sprint"]);
    fireEvent.click(screen.getByRole("button", { name: "Limpar" }));
    expect(onChange).toHaveBeenLastCalledWith([]);
  });

  it("combina filtros rápidos com os campos reais do card", () => {
    const overdue: Task = {
      id: 1,
      title: "Pendência antiga",
      description: "",
      status: "backlog",
      priority: 3,
      due: "2020-01-01",
      supplier_id: null,
      sprint_id: null,
      estimated_minutes: 0,
      used_minutes: 0,
      hours_version: 0,
      approval: "pending",
      version: 1,
      fields: [],
      labels: [],
      values: {},
    };
    const scheduled = {
      ...overdue,
      id: 2,
      title: "Com sprint",
      due: "2099-01-01",
      supplier_id: 7,
      sprint_id: 4,
    };
    expect(
      filterBoardTasks(
        [overdue, scheduled],
        "is:overdue no:supplier no:sprint approval:pending",
        [],
        [],
      ).map((task) => task.id),
    ).toEqual([1]);
  });

  it("permite cadastrar uma consulta nomeada na configuração da visualização", () => {
    const onChange = vi.fn();
    const onFiltersChange = vi.fn();
    render(<QuickFilters filters={boardQuickFilters} active={[]} onChange={onChange} onFiltersChange={onFiltersChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Configurar filtros" }));
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Revisões sem sprint" } });
    fireEvent.change(screen.getByLabelText("Consulta"), { target: { value: "status:review no:sprint" } });
    fireEvent.click(screen.getByRole("button", { name: "Adicionar filtro" }));
    expect(onFiltersChange).toHaveBeenCalledWith([
      ...boardQuickFilters,
      expect.objectContaining({ label: "Revisões sem sprint", query: "status:review no:sprint" }),
    ]);
  });

  it("permite editar e remover um filtro configurado", () => {
    const onChange = vi.fn();
    const onFiltersChange = vi.fn();
    const { rerender } = render(<QuickFilters filters={boardQuickFilters} active={["overdue"]} onChange={onChange} onFiltersChange={onFiltersChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Configurar filtros" }));
    fireEvent.click(screen.getAllByRole("button", { name: "Editar" })[0]);
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Vencidas" } });
    fireEvent.change(screen.getByLabelText("Consulta"), { target: { value: "is:overdue" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar filtro" }));
    const renamed = [{ ...boardQuickFilters[0], label: "Vencidas" }, ...boardQuickFilters.slice(1)];
    expect(onFiltersChange).toHaveBeenCalledWith(renamed);

    rerender(<QuickFilters filters={renamed} active={["overdue"]} onChange={onChange} onFiltersChange={onFiltersChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Remover filtro Vencidas" }));
    expect(onFiltersChange).toHaveBeenLastCalledWith(boardQuickFilters.slice(1));
    expect(onChange).toHaveBeenLastCalledWith([]);
  });
});

describe("agrupamento hierárquico na tabela", () => {
  it("agrupa atividades pelo card pai e expõe o tipo na tabela", () => {
    const parent: Task = {
      id: 10, title: "Épico Portal", description: "", work_type: "epic", parent_id: null,
      status: "backlog", priority: 1, due: null, supplier_id: null, sprint_id: null,
      estimated_minutes: 0, used_minutes: 0, hours_version: 0, approval: "pending",
      version: 1, fields: [], values: {},
    };
    const child: Task = {
      ...parent, id: 11, title: "Subtarefa de acesso", work_type: "subtask", parent_id: 10,
    };
    const columns = [{ key: "backlog", title: "Backlog", is_system: true, category: "todo" as const, view_order: 0 }];
    render(
      <ProjectTable
        tasks={[parent, child]}
        columns={columns}
        suppliers={[]}
        fields={[{ key: "title", label: "Card" }, { key: "parent", label: "Card pai" }, { key: "work_type", label: "Tipo de card" }]}
        visibleFields={["title", "parent", "work_type"]}
        groupBy="parent"
        sumBy="count"
        open={vi.fn()}
      />,
    );

    const table = screen.getByRole("table");
    expect(within(table).getAllByText("Sem card pai")).toHaveLength(2);
    expect(within(table).getAllByText("OS-10 · Épico Portal")).toHaveLength(3);
    expect(within(table).getByText("Subtarefa")).toBeInTheDocument();
    expect(within(table).getByText("OS-11 · Subtarefa de acesso")).toBeInTheDocument();
  });
});

describe("dependências no cronograma", () => {
  it("orienta bloqueios e mostra apenas relações cujos dois cards estão no recorte", () => {
    const blocked = { id: 1, title: "Bloqueador", links: [{ id: 11, task_id: 2, direction: "outgoing", type: "blocks" }] } as Task;
    const blockedTask = { id: 2, title: "Bloqueada", links: [{ id: 11, task_id: 1, direction: "incoming", type: "blocks" }] } as Task;
    const related = { id: 3, title: "Relacionado", links: [{ id: 12, task_id: 1, direction: "incoming", type: "relates" }] } as Task;
    expect(timelineDependencies([blocked, blockedTask, related])).toEqual([
      { id: 11, fromTaskId: 1, toTaskId: 2, type: "blocks" },
      { id: 12, fromTaskId: 1, toTaskId: 3, type: "relates" },
    ]);
    expect(timelineDependencies([blocked])).toEqual([]);
  });

  it("desenha um conector acessível entre os cards bloqueador e bloqueado", async () => {
    const first = { id: 1, title: "Bloqueador", status: "backlog", due: "2026-11-10", planned_start: "2026-11-08", links: [{ id: 11, task_id: 2, direction: "outgoing", type: "blocks" }] } as Task;
    const second = { ...first, id: 2, title: "Bloqueada", planned_start: "2026-11-12", due: "2026-11-15", links: [] } as Task;
    const geometry = vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
      const identity = this.dataset.timelineBarId;
      if (identity === "1") return { left: 400, right: 440, top: 140, bottom: 164, width: 40, height: 24, x: 400, y: 140, toJSON: () => ({}) } as DOMRect;
      if (identity === "2") return { left: 600, right: 680, top: 250, bottom: 274, width: 80, height: 24, x: 600, y: 250, toJSON: () => ({}) } as DOMRect;
      return { left: 100, right: 1000, top: 100, bottom: 600, width: 900, height: 500, x: 100, y: 100, toJSON: () => ({}) } as DOMRect;
    });
    render(<TimelineView tasks={[first, second]} columns={[]} suppliers={[]} sprints={[]} zoom="quarter" account={{ id: 1, username: "gestor", role: "manager", permissions: ["create_tasks"] } as Account} saveSchedule={vi.fn()} open={vi.fn()} />);

    await waitFor(() => expect(document.querySelector(".timeline-dependency title")?.textContent).toBe("OS-1 bloqueia OS-2"));
    expect(screen.getByLabelText("Dependências entre cards")).toBeInTheDocument();
    geometry.mockRestore();
  });
});
