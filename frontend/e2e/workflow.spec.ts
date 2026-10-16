import { test, expect, type Page } from "@playwright/test";
async function login(page: Page, user: string) {
  await page.goto("/");
  await page.getByLabel("Usuário", { exact: true }).fill(user);
  await page
    .getByLabel("Senha", { exact: true })
    .fill(process.env.E2E_PASSWORD || "DemoLocal!2026");
  await page.getByRole("button", { name: /Entrar no OS/ }).click();
  await expect(
    page.getByRole("heading", { name: "Gestão de demandas" }),
  ).toBeVisible();
}
test("fluxo persistente de horas, aprovação e conclusão por perfis", async ({
  browser,
}) => {
  const adminContext = await browser.newContext();
  const vendorContext = await browser.newContext();
  const admin = await adminContext.newPage();
  const vendor = await vendorContext.newPage();
  await login(admin, "gestor");
  await admin.getByRole("link", { name: /Backlog/ }).click();
  await admin.getByRole("button", { name: "Nova atividade" }).click();
  await admin.getByLabel("Horas previstas no card").selectOption("required");
  const title = "Aceite E2E " + Date.now();
  await admin.getByLabel("Título", { exact: true }).fill(title);
  await admin
    .getByLabel("Fornecedor responsável")
    .selectOption({ label: "Ana Exemplo" });
  await admin
    .getByRole("button", { name: "Salvar atividade", exact: true })
    .click();
  await admin.getByRole("button", { name: new RegExp(title) }).click();
  await admin.getByLabel("Mover atividade").selectOption("todo");
  await expect(admin.getByRole("dialog").locator(".badge.todo")).toBeVisible();
  await admin.getByLabel("Mover atividade").focus();
  await admin.getByLabel("Mover atividade").selectOption("production");
  await expect(admin.getByRole("alertdialog")).toContainText("horas previstas");
  await expect(admin.getByRole("alertdialog")).toHaveJSProperty("open", true);
  await admin.getByRole("button", { name: "Entendi", exact: true }).click();
  await expect(admin.getByLabel("Mover atividade")).toBeFocused();
  await expect(admin.getByLabel("Mover atividade")).toHaveValue("todo");
  await login(vendor, "fornecedor");
  await vendor.getByRole("link", { name: /Minhas tarefas/ }).click();
  await vendor.getByRole("button", { name: new RegExp(title) }).click();
  await vendor.getByLabel("Horas previstas", { exact: true }).fill("10");
  await vendor.getByRole("button", { name: "Salvar Horas previstas" }).click();
  await expect(vendor.locator('.notice[role="status"]')).toContainText(
    "realizada",
  );
  await vendor.getByLabel("Mover atividade").selectOption("production");
  await expect(vendor.getByLabel("Mover atividade")).toHaveValue("production");
  await vendor.getByLabel("Mover atividade").selectOption("review");
  await expect(vendor.getByRole("alertdialog")).toContainText(
    "horas utilizadas",
  );
  await expect(vendor.getByRole("alertdialog").locator("h2")).toHaveCSS(
    "color",
    "rgb(153, 27, 27)",
  );
  await vendor.screenshot({ path: "test-results/erro-horas-modal.png" });
  await vendor.keyboard.press("Escape");
  await expect(vendor.getByRole("alertdialog")).toHaveCount(0);
  await expect(vendor.getByLabel("Mover atividade")).toHaveValue("production");
  await vendor.getByLabel("Horas utilizadas", { exact: true }).fill("8");
  await vendor.getByRole("button", { name: "Salvar Horas utilizadas" }).click();
  await expect(vendor.locator('.notice[role="status"]')).toContainText(
    "realizada",
  );
  await vendor.getByLabel("Mover atividade").selectOption("review");
  await expect(vendor.getByLabel("Mover atividade")).toHaveValue("review");
  await expect(vendor.getByText(/Tarifa congelada/)).toHaveCount(0);
  await admin.reload();
  await admin.getByRole("button", { name: new RegExp(title) }).click();
  await admin
    .getByRole("button", { name: "Aprovar horas", exact: true })
    .click();
  await expect(admin.getByRole("dialog")).toContainText("960,00");
  await admin.getByLabel("Mover atividade").selectOption("done");
  await expect(admin.getByLabel("Mover atividade")).toHaveValue("done");
  await admin.getByRole("button", { name: "Fechar atividade" }).click();
  await admin.getByRole("link", { name: /Relatórios/ }).click();
  await admin.getByLabel("Incluir custos aprovados").check();
  const file = admin.waitForEvent("download");
  await admin.getByRole("button", { name: "Exportar Excel (.xlsx)" }).click();
  expect((await file).suggestedFilename()).toBe("os-manager.xlsx");
  await adminContext.close();
  await vendorContext.close();
});
test("cadastro e personalização individual", async ({ page }) => {
  await login(page, "admin");
  await page.getByRole("link", { name: /Fornecedores/ }).click();
  await page.getByRole("button", { name: "Cadastrar fornecedor" }).click();
  const name = "Fornecedor E2E " + Date.now();
  await page.getByLabel("Nome", { exact: true }).fill(name);
  await page.getByLabel("Função", { exact: true }).fill("Teste fictício");
  await page.getByLabel("Nova tarifa por hora").fill("120");
  await page.getByRole("button", { name: "Salvar fornecedor" }).click();
  await expect(
    page.locator("td strong").getByText(name, { exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: /Backlog/ }).click();
  await page.getByRole("button", { name: /Portal de atendimento/ }).click();
  await page.getByRole("button", { name: "Construtor do card" }).click();
  await page
    .getByRole("button", { name: "+ Texto curto", exact: true })
    .click();
  await page.getByLabel("Rótulo").last().fill("Evidência E2E");
  await page.getByRole("button", { name: "Salvar configuração" }).click();
  await expect(page.locator('.notice[role="status"]')).toContainText(
    "realizada",
  );
  await page.getByRole("button", { name: "Detalhes e fluxo" }).click();
  await page.getByLabel("Evidência E2E").fill("Documento fictício");
  await page.getByRole("button", { name: "Salvar campos" }).click();
  await expect(page.locator('.notice[role="status"]')).toContainText(
    "realizada",
  );
});

test("arrastar inválido conserva a origem e interface responsiva", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await login(page, "admin");
  const me = await (await page.request.get("/api/v1/auth/me")).json();
  const title = "Drag E2E " + Date.now();
  const task = await (
    await page.request.post("/api/v1/tasks", {
      headers: { "X-CSRF-Token": me.csrf },
      data: { title, supplier_id: 1, estimate_policy: "required" },
    })
  ).json();
  await page.request.post(`/api/v1/tasks/${task.id}/move`, {
    headers: { "X-CSRF-Token": me.csrf },
    data: { version: task.version, status: "todo" },
  });
  await page.getByRole("link", { name: /Kanban/ }).click();
  const handle = page.getByRole("button", { name: "Arrastar " + title });
  const source = await handle.boundingBox();
  const destination = await page
    .locator(".kanban-column")
    .filter({ has: page.getByRole("heading", { name: /Em produção/ }) })
    .boundingBox();
  expect(source).toBeTruthy();
  expect(destination).toBeTruthy();
  await page.mouse.move(
    source!.x + source!.width / 2,
    source!.y + source!.height / 2,
  );
  await page.mouse.down();
  await page.mouse.move(source!.x + 20, source!.y + 20, { steps: 3 });
  await page.mouse.move(destination!.x + 80, destination!.y + 100, {
    steps: 15,
  });
  await page.mouse.up();
  await expect(page.getByRole("alertdialog")).toContainText("horas previstas");
  await expect(
    page
      .locator(".kanban-column")
      .filter({ has: page.getByRole("heading", { name: /A fazer/ }) })
      .getByRole("button", { name: title, exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Entendi", exact: true }).click();
  await page.screenshot({
    path: "test-results/kanban-desktop.png",
    fullPage: true,
  });
  await page.getByRole("link", { name: /Visão geral/ }).click();
  await page.screenshot({
    path: "test-results/dashboard-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("button", { name: "Sair", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/dashboard-mobile.png",
    fullPage: true,
  });
});

test("campos nativos ordenáveis continuam ligados às horas estruturais", async ({
  browser,
}) => {
  const adminContext = await browser.newContext(),
    vendorContext = await browser.newContext();
  const admin = await adminContext.newPage(),
    vendor = await vendorContext.newPage();
  await login(admin, "admin");
  const me = await (await admin.request.get("/api/v1/auth/me")).json();
  const title = "Nativos E2E " + Date.now();
  const task = await (
    await admin.request.post("/api/v1/tasks", {
      headers: { "X-CSRF-Token": me.csrf },
      data: { title, supplier_id: 1 },
    })
  ).json();
  await admin.getByRole("link", { name: /Backlog/ }).click();
  await admin.getByRole("button", { name: new RegExp(title) }).click();
  await admin.getByRole("button", { name: "Construtor do card" }).click();
  await admin
    .getByRole("button", { name: "+ Horas previstas (nativo)", exact: true })
    .click();
  await admin
    .getByRole("button", { name: "+ Horas utilizadas (nativo)", exact: true })
    .click();
  await admin.getByLabel("Resposta obrigatória de horas previstas").check();
  await admin.getByLabel("Rótulo").first().fill("Planejado nativo");
  await admin.getByLabel("Rótulo").last().fill("Realizado nativo");
  await admin
    .getByRole("button", { name: "↓ Descer", exact: true })
    .first()
    .click();
  await admin.getByRole("button", { name: "Salvar configuração" }).click();
  await expect(admin.locator('.notice[role="status"]')).toContainText(
    "realizada",
  );
  const configured = await (
    await admin.request.get(`/api/v1/tasks/${task.id}`)
  ).json();
  expect(configured.fields[0].native_key).toBe("used_minutes");
  await admin.getByRole("button", { name: "Detalhes e fluxo" }).click();
  await admin.getByLabel("Mover atividade").selectOption("todo");
  await expect(admin.getByLabel("Mover atividade")).toHaveValue("todo");
  await login(vendor, "fornecedor");
  await vendor.getByRole("link", { name: /Minhas tarefas/ }).click();
  await vendor.getByRole("button", { name: new RegExp(title) }).click();
  await vendor.getByLabel("Planejado nativo", { exact: true }).fill("10");
  await vendor
    .getByRole("button", { name: "Salvar Planejado nativo", exact: true })
    .click();
  await expect(vendor.locator('.notice[role="status"]')).toContainText(
    "realizada",
  );
  await vendor.getByLabel("Mover atividade").selectOption("production");
  await expect(vendor.getByLabel("Mover atividade")).toHaveValue("production");
  await vendor.getByLabel("Realizado nativo", { exact: true }).fill("8");
  await vendor
    .getByRole("button", { name: "Salvar Realizado nativo", exact: true })
    .click();
  await expect(vendor.locator('.notice[role="status"]')).toContainText(
    "realizada",
  );
  await vendor.getByLabel("Mover atividade").selectOption("review");
  await expect(vendor.getByLabel("Mover atividade")).toHaveValue("review");
  const persisted = await (
    await vendor.request.get(`/api/v1/tasks/${task.id}`)
  ).json();
  expect(persisted.used_minutes).toBe(480);
  expect(persisted).not.toHaveProperty("rate_cents");
  await adminContext.close();
  await vendorContext.close();
});

test("criador escolhe não incluir ou incluir horas previstas opcionais", async ({
  browser,
}) => {
  const adminContext = await browser.newContext();
  const vendorContext = await browser.newContext();
  const admin = await adminContext.newPage();
  const vendor = await vendorContext.newPage();
  await login(admin, "admin");
  await login(vendor, "fornecedor");
  for (const policy of ["absent", "optional"]) {
    await admin.getByRole("link", { name: /Backlog/ }).click();
    await admin.getByRole("button", { name: "Nova atividade" }).click();
    const title = `Estimativa ${policy} ${Date.now()}`;
    await admin.getByLabel("Título", { exact: true }).fill(title);
    await admin
      .getByLabel("Fornecedor responsável")
      .selectOption({ label: "Ana Exemplo" });
    await admin.getByLabel("Horas previstas no card").selectOption(policy);
    await admin
      .getByRole("button", { name: "Salvar atividade", exact: true })
      .click();
    await admin.getByRole("button", { name: new RegExp(title) }).click();
    await admin.getByLabel("Mover atividade").selectOption("todo");
    await expect(admin.getByLabel("Mover atividade")).toHaveValue("todo");
    await vendor.reload();
    await vendor.getByRole("link", { name: /Minhas tarefas/ }).click();
    await vendor.getByRole("button", { name: new RegExp(title) }).click();
    await expect(
      vendor.getByLabel("Horas previstas", { exact: true }),
    ).toHaveCount(policy === "absent" ? 0 : 1);
    await vendor.getByLabel("Mover atividade").selectOption("production");
    await expect(vendor.getByLabel("Mover atividade")).toHaveValue(
      "production",
    );
    await expect(vendor.getByRole("alertdialog")).toHaveCount(0);
    await vendor.getByRole("button", { name: "Fechar atividade" }).click();
    await admin.getByRole("button", { name: "Fechar atividade" }).click();
  }
  await adminContext.close();
  await vendorContext.close();
});

test("relatórios combinam campos do card e exportam o mesmo recorte", async ({
  page,
}) => {
  await login(page, "admin");
  const me = await (await page.request.get("/api/v1/auth/me")).json();
  const stamp = Date.now();
  const region = "region_" + stamp;
  const amount = "amount_" + stamp;
  const headers = { "X-CSRF-Token": me.csrf };
  const names = [
    `Relatório selecionado ${stamp}`,
    `Relatório excluído ${stamp}`,
  ];
  for (let index = 0; index < 2; index++) {
    const created = await page.request.post("/api/v1/tasks", {
      headers,
      data: { title: names[index], supplier_id: 1 },
    });
    expect(created.status()).toBe(201);
    const task = await created.json();
    const configured = await page.request.put(
      `/api/v1/tasks/${task.id}/schema`,
      {
        headers,
        data: {
          version: task.version,
          fields: [
            {
              id: region,
              label: "Regional relatório " + stamp,
              type: "select",
              options: ["Norte", "Sul"],
            },
            {
              id: amount,
              label: "Quantidade relatório " + stamp,
              type: "number",
            },
          ],
          values: { [region]: "Norte", [amount]: index === 0 ? "8" : "2" },
        },
      },
    );
    expect(configured.status()).toBe(200);
  }
  await page.getByRole("link", { name: /Relatórios/ }).click();
  await page.getByRole("button", { name: "Adicionar filtro" }).click();
  await page
    .getByLabel("Campo do filtro 1", { exact: true })
    .selectOption("field:" + region);
  await expect(
    page
      .getByLabel("Campo do filtro 1", { exact: true })
      .getByRole("option", { name: "Descrição", exact: true }),
  ).toHaveCount(0);
  await page
    .getByLabel("Valor do filtro 1", { exact: true })
    .selectOption("Norte");
  await page.getByRole("button", { name: "Adicionar filtro" }).click();
  await page
    .getByLabel("Campo do filtro 2", { exact: true })
    .selectOption("field:" + amount);
  await page
    .getByLabel("Condição do filtro 2", { exact: true })
    .selectOption("gte");
  await page.getByLabel("Valor do filtro 2", { exact: true }).fill("5");
  await page
    .getByRole("button", { name: "Aplicar filtros", exact: true })
    .click();
  await expect(
    page.getByText("1 atividade(s) encontrada(s).", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: names[0], exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: names[1], exact: true }),
  ).toHaveCount(0);
  const requestPromise = page.waitForRequest((request) =>
    request.url().includes("/exports/xlsx?"),
  );
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Exportar Excel (.xlsx)" }).click();
  const request = await requestPromise;
  const applied = JSON.parse(
    new URL(request.url()).searchParams.get("field_filters")!,
  );
  expect(applied).toHaveLength(2);
  expect(applied[1]).toMatchObject({
    field: "field:" + amount,
    op: "gte",
    value: "5",
  });
  expect((await downloadPromise).suggestedFilename()).toBe("os-manager.xlsx");
  const pdf = page.waitForEvent("download");
  await page.getByRole("button", { name: "Exportar PDF" }).click();
  expect((await pdf).suggestedFilename()).toBe("os-manager.pdf");
  await page.screenshot({
    path: "test-results/relatorio-filtros-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "test-results/relatorio-filtros-mobile.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Remover filtro 2", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Aplicar filtros", exact: true })
    .click();
  await expect(
    page.getByText("2 atividade(s) encontrada(s).", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Valor do filtro 1", { exact: true })
    .selectOption("Sul");
  await page
    .getByRole("button", { name: "Aplicar filtros", exact: true })
    .click();
  await expect(
    page.getByText("Nenhuma atividade atende aos filtros selecionados."),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Limpar filtros de campos", exact: true })
    .click();
  await expect(
    page.getByLabel("Campo do filtro 1", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("cell", { name: names[0], exact: true }),
  ).toBeVisible();
});
