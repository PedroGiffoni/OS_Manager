import { expect, request as playwrightRequest, test } from "@playwright/test";
import type { APIRequestContext, Page } from "@playwright/test";

async function login(page: Page) {
  await page.goto("/");
  await page.getByLabel("Usuário", { exact: true }).fill("admin");
  await page
    .getByLabel("Senha", { exact: true })
    .fill(process.env.E2E_PASSWORD || "DemoLocal!2026");
  await page
    .getByRole("button", { name: /Entrar na Gestão de Demandas/ })
    .click();
  await expect(
    page.getByRole("button", { name: "Sair", exact: true }),
  ).toBeVisible();
}

async function csrf(request: APIRequestContext) {
  const response = await request.get("/api/v1/auth/me");
  expect(response.ok()).toBeTruthy();
  return (await response.json()).csrf as string;
}

test("categoria configurável filtra cards independentemente da ordem visual", async ({
  page,
}) => {
  await login(page);
  const request = page.request;
  const token = await csrf(request);
  const title = `Categoria E2E ${Date.now()}`;
  const created = await request.post("/api/v1/tasks", {
    headers: { "X-CSRF-Token": token },
    data: { title },
  });
  expect(created.status()).toBe(201);
  const task = await created.json();

  try {
    await page.getByRole("link", { name: /Kanban/ }).click();
    await page
      .getByLabel("Categoria da coluna Backlog", { exact: true })
      .selectOption("in_progress");
    await expect(
      page.getByLabel("Categoria da coluna Backlog", { exact: true }),
    ).toHaveValue("in_progress");

    const progress = await request.get("/api/v1/tasks", {
      params: {
        jql: 'key = "OS-' + task.id + '" AND statusCategory = "In Progress"',
      },
    });
    const todo = await request.get("/api/v1/tasks", {
      params: {
        jql: 'key = "OS-' + task.id + '" AND statusCategory = "To Do"',
      },
    });
    expect(
      (await progress.json()).map((row: { id: number }) => row.id),
    ).toContain(task.id);
    expect(
      (await todo.json()).map((row: { id: number }) => row.id),
    ).not.toContain(task.id);
  } finally {
    await request
      .put("/api/v1/board/columns/backlog", {
        headers: { "X-CSRF-Token": token },
        data: { category: "todo" },
      })
      .catch(() => undefined);
    await request
      .delete(`/api/v1/tasks/${task.id}`, {
        headers: { "X-CSRF-Token": token },
      })
      .catch(() => undefined);
  }
});

test("calendário agenda card sem prazo por arraste", async ({ page }) => {
  test.setTimeout(60000);
  await login(page);
  const request = page.request;
  const token = await csrf(request);
  const title = `Calendário E2E ${Date.now()}`;
  const created = await request.post("/api/v1/tasks", {
    headers: { "X-CSRF-Token": token },
    data: { title },
  });
  expect(created.status()).toBe(201);
  const task = await created.json();

  try {
    await page.getByRole("link", { name: /Kanban/ }).click();
    const layout = page.locator(".project-view-controls select").first();
    await layout.selectOption("calendar");
    await expect(layout).toHaveValue("calendar");
    await expect(
      page.getByRole("region", { name: /Calendário de/ }),
    ).toBeVisible();
    const date = await page.evaluate(() => {
      const now = new Date();
      return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
    });
    const card = page.getByRole("button", {
      name: new RegExp(`OS-${task.id} · ${title}`),
    });
    await expect(card).toBeVisible();
    await card.dragTo(
      page.getByLabel(`Soltar card no dia ${date}`, { exact: true }),
    );

    await expect
      .poll(
        async () =>
          (await (await request.get(`/api/v1/tasks/${task.id}`)).json()).due,
      )
      .toBe(date);
    await expect(
      page
        .locator(`[data-date="${date}"]`)
        .getByRole("button", { name: new RegExp(title) }),
    ).toBeVisible();
  } finally {
    await request
      .delete(`/api/v1/tasks/${task.id}`, {
        headers: { "X-CSRF-Token": token },
      })
      .catch(() => undefined);
  }
});

test("calendário exporta os cards visíveis como arquivo iCalendar", async ({ page }) => {
  await login(page);
  const request = page.request;
  const token = await csrf(request);
  const title = `Exportação ICS ${Date.now()}`;
  const today = new Date();
  today.setDate(today.getDate() + 7);
  const due = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  const created = await request.post("/api/v1/tasks", {
    headers: { "X-CSRF-Token": token },
    data: { title, due },
  });
  expect(created.status()).toBe(201);
  const task = await created.json();

  try {
    await page.getByRole("link", { name: /Kanban/ }).click();
    await page.locator(".project-view-controls select").first().selectOption("calendar");
    await expect(page.getByRole("button", { name: new RegExp(`OS-${task.id}`) })).toBeVisible();
    const downloadEvent = page.waitForEvent("download");
    await page.getByRole("button", { name: "Exportar .ics" }).click();
    const download = await downloadEvent;
    expect(download.suggestedFilename()).toBe("gestao-de-demandas.ics");
  } finally {
    await request
      .delete(`/api/v1/tasks/${task.id}`, {
        headers: { "X-CSRF-Token": token },
      })
      .catch(() => undefined);
  }
});

test("filtro JQL salvo pode ser compartilhado e aplicado por outra pessoa interna", async ({ page }) => {
  test.setTimeout(90000);
  const cleanupContext = await playwrightRequest.newContext({
    baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:5174",
  });
  const cleanupLogin = await cleanupContext.post("/api/v1/auth/login", {
    data: {
      username: "admin",
      password: process.env.E2E_PASSWORD || "DemoLocal!2026",
    },
  });
  expect(cleanupLogin.status()).toBe(200);
  const cleanupToken = (await cleanupLogin.json()).csrf as string;
  await login(page);
  const request = page.request;
  const token = await csrf(request);
  const title = `Filtro compartilhado E2E ${Date.now()}`;
  const created = await request.post("/api/v1/tasks", {
    headers: { "X-CSRF-Token": token },
    data: { title },
  });
  expect(created.status()).toBe(201);
  const task = await created.json();
  let savedFilterId: number | null = null;
  const filterName = `Filtro E2E ${Date.now()}`;
  const query = `key = "OS-${task.id}"`;

  try {
    await page.getByLabel("Consulta avançada dos cards", { exact: true }).fill(query);
    await page.getByRole("button", { name: "Aplicar consulta" }).click();
    await page.getByRole("button", { name: "Salvar filtro…" }).click();
    await page.getByLabel("Nome do filtro", { exact: true }).fill(filterName);
    await page.getByLabel("Compartilhar filtro com equipe interna", { exact: true }).check();
    await page.getByRole("button", { name: "Salvar filtro", exact: true }).click();

    await expect
      .poll(async () => {
        const response = await request.get("/api/v1/saved-filters");
        const filters = await response.json();
        const saved = filters.find((row: { name: string }) => row.name === filterName);
        savedFilterId = saved?.id ?? null;
        return savedFilterId;
      })
      .not.toBeNull();

    await page.getByRole("button", { name: "Sair", exact: true }).click();
    await loginAs(page, "interno");
    const savedFilterSelect = page.getByRole("combobox", { name: "Filtro salvo reutilizável" });
    await expect(savedFilterSelect.locator("option").filter({ hasText: filterName })).toHaveCount(1);
    await savedFilterSelect.selectOption(String(savedFilterId));
    await expect(page.getByLabel("Consulta avançada dos cards", { exact: true })).toHaveValue(query);
    const applied = await request.get("/api/v1/tasks", { params: { jql: query } });
    expect((await applied.json()).map((row: { id: number }) => row.id)).toContain(task.id);

    await page.getByRole("button", { name: "Sair", exact: true }).click();
    await loginAs(page, "fornecedor");
    const supplierFilters = await request.get("/api/v1/saved-filters");
    expect((await supplierFilters.json()).map((row: { id: number }) => row.id)).not.toContain(savedFilterId);
  } finally {
    if (savedFilterId) {
      await cleanupContext.delete(`/api/v1/saved-filters/${savedFilterId}`, {
        headers: { "X-CSRF-Token": cleanupToken },
      }).catch(() => undefined);
    }
    await cleanupContext.delete(`/api/v1/tasks/${task.id}`, {
      headers: { "X-CSRF-Token": cleanupToken },
    }).catch(() => undefined);
    await cleanupContext.dispose();
  }
});

async function loginAs(page: Page, username: string) {
  await page.goto("/");
  await page.getByLabel("Usuário", { exact: true }).fill(username);
  await page.getByLabel("Senha", { exact: true }).fill(process.env.E2E_PASSWORD || "DemoLocal!2026");
  await page.getByRole("button", { name: /Entrar na Gestão de Demandas/ }).click();
  await expect(page.getByRole("button", { name: "Sair", exact: true })).toBeVisible();
}
