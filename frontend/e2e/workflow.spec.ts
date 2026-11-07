import { test, expect, type Page } from "@playwright/test";
async function login(page: Page, user: string) {
  await page.goto("/");
  await expect(page).toHaveTitle("Gestão de Demandas");
  await page.getByLabel("Usuário", { exact: true }).fill(user);
  await page
    .getByLabel("Senha", { exact: true })
    .fill(process.env.E2E_PASSWORD || "DemoLocal!2026");
  await page
    .getByRole("button", { name: /Entrar na Gestão de Demandas/ })
    .click();
  await expect(
    page.getByRole("button", { name: "Sair", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Gestão de Demandas" }),
  ).toBeVisible();
}
async function textContrast(
  page: Page,
  textSelector: string,
  surfaceSelector: string,
) {
  return page.evaluate(
    ({ textSelector, surfaceSelector }) => {
      const foreground = getComputedStyle(
        document.querySelector(textSelector)!,
      ).color;
      const surfaceStyle = getComputedStyle(
        document.querySelector(surfaceSelector)!,
      );
      const background = surfaceStyle.backgroundColor;
      const gradientColors =
        surfaceStyle.backgroundImage.match(
          /rgba?\([^)]*\)|#[0-9a-fA-F]{3,8}/g,
        ) ?? [];
      const canvas = document.createElement("canvas");
      canvas.width = canvas.height = 1;
      const context = canvas.getContext("2d")!;
      function luminance(color: string) {
        context.fillStyle = color;
        context.fillRect(0, 0, 1, 1);
        const channels = Array.from(context.getImageData(0, 0, 1, 1).data)
          .slice(0, 3)
          .map((value) => {
            const channel = value / 255;
            return channel <= 0.04045
              ? channel / 12.92
              : ((channel + 0.055) / 1.055) ** 2.4;
          });
        return (
          channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722
        );
      }
      const backgrounds = gradientColors.length ? gradientColors : [background];
      return Math.min(
        ...backgrounds.map((color) => {
          const values = [luminance(foreground), luminance(color)].sort(
            (a, b) => b - a,
          );
          return (values[0] + 0.05) / (values[1] + 0.05);
        }),
      );
    },
    { textSelector, surfaceSelector },
  );
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
  const errorColor = await vendor
    .getByRole("alertdialog")
    .locator("h2")
    .evaluate((element) => getComputedStyle(element).color);
  const channels = errorColor.match(/[\d.]+/g)!.map(Number);
  expect(channels[0]).toBeGreaterThan(channels[1] * 2);
  expect(channels[0]).toBeGreaterThan(channels[2] * 2);
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
  const resolutionDialog = admin.getByRole("dialog", { name: "Registrar resolução" });
  await expect(resolutionDialog).toBeVisible();
  await resolutionDialog.getByLabel("Resolução").selectOption("Fixed");
  await resolutionDialog.getByRole("button", { name: "Concluir card" }).click();
  await expect(admin.getByLabel("Mover atividade")).toHaveValue("done");
  await expect(admin.getByText("Resolução: Corrigido")).toBeVisible();
  await admin.getByRole("button", { name: "Fechar atividade" }).click();
  await admin.getByRole("link", { name: /Relatórios/ }).click();
  await admin.getByLabel("Incluir custos aprovados").check();
  const file = admin.waitForEvent("download");
  await admin.getByRole("button", { name: "Exportar Excel (.xlsx)" }).click();
  expect((await file).suggestedFilename()).toBe("os-manager.xlsx");
  const htmlDownload = admin.waitForEvent("download");
  await admin
    .getByRole("button", { name: "Exportar HTML", exact: true })
    .click();
  const htmlFile = await htmlDownload;
  expect(htmlFile.suggestedFilename()).toBe("os-manager.html");
  const htmlPath = test.info().outputPath("report.html");
  await htmlFile.saveAs(htmlPath);
  const offline = await browser.newContext({
    offline: true,
    reducedMotion: "reduce",
  });
  const document = await offline.newPage();
  await document.goto("file:///" + htmlPath.replace(/\\/g, "/"));
  await expect(
    document.getByRole("heading", { name: "Entregas em perspectiva" }),
  ).toBeVisible();
  await expect(
    document.getByRole("heading", { name: "Ritmo das sprints" }),
  ).toBeVisible();
  expect(
    await document
      .locator(".track span")
      .first()
      .evaluate((node) => getComputedStyle(node).animationName),
  ).toBe("none");
  await document
    .getByRole("button", { name: "Pausar animações", exact: true })
    .click();
  await expect(
    document.getByRole("button", { name: "Ativar animações", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await document.screenshot({
    path: "test-results/relatorio-html-desktop.png",
    fullPage: true,
  });
  await document.setViewportSize({ width: 390, height: 844 });
  expect(
    await document.evaluate(
      () => window.document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await document.screenshot({
    path: "test-results/relatorio-html-mobile.png",
    fullPage: true,
  });
  await offline.close();
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
  const target = page
    .locator(".kanban-column")
    .filter({ has: page.getByRole("heading", { name: /Em produção/ }) });
  await handle.scrollIntoViewIfNeeded();
  const source = await handle.boundingBox();
  const destination = await target.boundingBox();
  expect(source).toBeTruthy();
  expect(destination).toBeTruthy();
  const viewport = await page.evaluate(() => ({
    width: innerWidth,
    height: innerHeight,
  }));
  const dropPoint = {
    x: Math.min(viewport.width - 20, Math.max(20, destination!.x + 80)),
    y: Math.min(viewport.height - 20, Math.max(20, destination!.y + 100)),
  };
  expect(
    await page.evaluate(
      ({ x, y }) =>
        Boolean(
          document
            .elementFromPoint(x, y)
            ?.closest(".kanban-column")
            ?.querySelector(".kanban-column-title")
            ?.textContent?.includes("Em produção"),
        ),
      dropPoint,
    ),
  ).toBe(true);
  await page.mouse.move(
    source!.x + source!.width / 2,
    source!.y + source!.height / 2,
  );
  await page.mouse.down();
  await page.mouse.move(dropPoint.x, dropPoint.y, { steps: 20 });
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
    .getByRole("button", { name: "Descer", exact: true })
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

test("identidade Sebrae temas e navegação acessível no celular", async ({
  page,
}) => {
  await page.goto("/");
  await page.evaluate(() => document.fonts.ready);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Gestão de Demandas",
  );
  await page.screenshot({
    path: "test-results/sebrae-login-claro.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Ativar modo escuro" }).click();
  await expect(page.locator("html")).toHaveClass("dark");
  await page.screenshot({
    path: "test-results/sebrae-login-escuro.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Ativar modo claro" }).click();
  await login(page, "admin");
  await expect(
    page.getByRole("img", { name: "Sebrae", exact: true }).first(),
  ).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  await expect(page.locator(".metrics .metric")).toHaveCount(4);
  await page.screenshot({
    path: "test-results/sebrae-dashboard-claro.png",
    fullPage: true,
  });
  expect(
    await textContrast(
      page,
      ".desktop-sidebar .nav-group-label",
      ".desktop-sidebar",
    ),
  ).toBeGreaterThanOrEqual(4.5);
  await page.getByRole("button", { name: "Recolher menu" }).click();
  await expect(
    page.getByRole("button", { name: "Expandir menu" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Expandir menu" }).click();
  await page.getByRole("button", { name: "Ativar modo escuro" }).click();
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Ativar modo claro" }),
  ).toBeVisible();
  await expect(page.locator("html")).toHaveClass("dark");
  await expect(page.locator(".metrics .metric")).toHaveCount(4);
  expect(
    await textContrast(
      page,
      ".desktop-sidebar a.active",
      ".desktop-sidebar a.active",
    ),
  ).toBeGreaterThanOrEqual(4.5);
  await page.screenshot({
    path: "test-results/sebrae-dashboard-escuro.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Abrir menu", exact: true }).click();
  const drawer = page.getByRole("dialog", {
    name: "Menu principal",
    exact: true,
  });
  await expect(drawer).toBeVisible();
  await page.screenshot({
    path: "test-results/sebrae-menu-mobile.png",
    fullPage: true,
  });
  await page.keyboard.press("Escape");
  await expect(drawer).not.toBeVisible();
  await expect(
    page.getByRole("button", { name: "Abrir menu", exact: true }),
  ).toBeFocused();
  for (const label of ["Backlog", "Kanban", "Relatórios", "Visão geral"]) {
    await page.getByRole("button", { name: "Abrir menu", exact: true }).click();
    await drawer.getByRole("link", { name: label, exact: true }).click();
    await expect(drawer).not.toBeVisible();
    const size = await page.evaluate(() => ({
      viewport: innerWidth,
      content: document.documentElement.scrollWidth,
    }));
    expect(size.content).toBeLessThanOrEqual(size.viewport + 1);
    await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
  }
  await page.screenshot({
    path: "test-results/sebrae-dashboard-mobile-escuro.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Ativar modo claro" }).click();
  await page.screenshot({
    path: "test-results/sebrae-dashboard-mobile-claro.png",
    fullPage: true,
  });
});

test("análise de cards mostra fases ciclos sprint backlog e exportação", async ({
  browser,
}) => {
  const adminContext = await browser.newContext();
  const vendorContext = await browser.newContext();
  const admin = await adminContext.newPage();
  const vendor = await vendorContext.newPage();
  await login(admin, "admin");
  await login(vendor, "fornecedor");
  const adminMe = await (await admin.request.get("/api/v1/auth/me")).json();
  const vendorMe = await (await vendor.request.get("/api/v1/auth/me")).json();
  const headers = { "X-CSRF-Token": adminMe.csrf };
  const title = "Análise operacional " + Date.now();
  let task = await (
    await admin.request.post("/api/v1/tasks", {
      headers,
      data: { title, supplier_id: 1 },
    })
  ).json();
  const sprint = await (
    await admin.request.post("/api/v1/sprints", {
      headers,
      data: {
        name: title,
        objective: "Aceite de análise",
        starts: "2026-01-01",
        ends: "2026-01-15",
      },
    })
  ).json();
  task = await (
    await admin.request.post(`/api/v1/sprints/${sprint.id}/tasks`, {
      headers,
      data: { version: 1, task_id: task.id, task_version: task.version },
    })
  ).json();
  expect(
    (
      await admin.request.post(`/api/v1/sprints/${sprint.id}/action`, {
        headers,
        data: { version: 2, action: "start" },
      })
    ).status(),
  ).toBe(200);
  task = await (
    await admin.request.post(`/api/v1/tasks/${task.id}/move`, {
      headers,
      data: { version: task.version, status: "production" },
    })
  ).json();
  task = await (
    await vendor.request.put(`/api/v1/tasks/${task.id}/hours`, {
      headers: { "X-CSRF-Token": vendorMe.csrf },
      data: { version: task.version, estimated_minutes: 0, used_minutes: 120 },
    })
  ).json();
  task = await (
    await admin.request.post(`/api/v1/tasks/${task.id}/move`, {
      headers,
      data: { version: task.version, status: "review" },
    })
  ).json();
  task = await (
    await admin.request.post(`/api/v1/tasks/${task.id}/approval`, {
      headers,
      data: {
        version: task.version,
        hours_version: task.hours_version,
        approved: true,
        reason: "",
      },
    })
  ).json();
  task = await (
    await admin.request.post(`/api/v1/tasks/${task.id}/move`, {
      headers,
      data: { version: task.version, status: "done" },
    })
  ).json();
  expect(task.status).toBe("done");
  expect(
    (
      await admin.request.post(`/api/v1/sprints/${sprint.id}/action`, {
        headers,
        data: { version: 3, action: "close" },
      })
    ).status(),
  ).toBe(200);
  expect(
    (
      await admin.request.post("/api/v1/tasks", {
        headers,
        data: { title: title + " pendente", supplier_id: 1 },
      })
    ).status(),
  ).toBe(201);
  await admin.getByRole("link", { name: "Relatórios", exact: true }).click();
  await expect(admin).toHaveURL(/\/relatorios$/);
  const cycleStart = admin.getByRole("combobox", { name: "Início do ciclo", exact: true });
  const cycleEnd = admin.getByRole("combobox", { name: "Fim do ciclo", exact: true });
  await expect(cycleStart).toHaveValue("production");
  await cycleStart.selectOption("todo");
  await cycleEnd.selectOption("review");
  await expect(cycleStart).toHaveValue("todo");
  await expect(cycleEnd).toHaveValue("review");
  await admin.getByRole("button", { name: "Adicionar filtro" }).click();
  await admin.getByLabel("Valor do filtro 1", { exact: true }).fill(title);
  await admin
    .getByRole("button", { name: "Aplicar filtros", exact: true })
    .click();
  await expect(
    admin.getByText("2 atividade(s) encontrada(s).", { exact: true }),
  ).toBeVisible();
  const detailButton = admin.getByRole("button", {
    name: `Analisar card OS-${task.id}`,
    exact: true,
  });
  await detailButton.click();
  const dialog = admin.getByRole("dialog", { name: title, exact: true });
  await expect(dialog).toBeVisible();
  await expect(
    dialog.getByRole("heading", {
      name: "Tempo acumulado em cada fase",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    dialog.getByRole("heading", { name: "Linha do tempo", exact: true }),
  ).toBeVisible();
  await expect(
    dialog.getByText("Histórico parcial", { exact: true }),
  ).toHaveCount(0);
  await expect(
    dialog.getByText("Não se aplica sem estimativa", { exact: true }),
  ).toBeVisible();
  await admin.screenshot({ path: "test-results/analise-card-desktop.png" });
  await admin.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(detailButton).toBeFocused();
  await admin.getByRole("tab", { name: "Sprints", exact: true }).click();
  await expect(
    admin.getByRole("heading", { name: "Resumo de sprints", exact: true }),
  ).toBeVisible();
  await expect(admin.locator(".analysis-sprint")).toContainText("100%");
  await admin.getByRole("tab", { name: "Backlog", exact: true }).click();
  await expect(
    admin.getByRole("heading", { name: "Análise do backlog", exact: true }),
  ).toBeVisible();
  await expect(
    admin.getByRole("button", { name: title + " pendente", exact: true }),
  ).toBeVisible();
  await admin.getByRole("tab", { name: "Cards", exact: true }).click();
  await admin.getByLabel("Somente reabertos", { exact: true }).check();
  await admin
    .getByRole("button", { name: "Aplicar análise", exact: true })
    .click();
  await expect(
    admin.getByText("Nenhuma atividade atende aos filtros selecionados."),
  ).toBeVisible();
  await admin.getByLabel("Somente reabertos", { exact: true }).uncheck();
  await admin
    .getByRole("button", { name: "Aplicar análise", exact: true })
    .click();
  await expect(
    admin.getByText("2 atividade(s) encontrada(s).", { exact: true }),
  ).toBeVisible();
  await admin.screenshot({
    path: "test-results/analise-cards-desktop.png",
    fullPage: true,
  });
  await admin.setViewportSize({ width: 390, height: 844 });
  await detailButton.click();
  await expect(dialog).toBeVisible();
  expect(
    await dialog.evaluate((element) => element.getBoundingClientRect().width),
  ).toBeLessThan(390);
  await admin.screenshot({ path: "test-results/analise-card-mobile.png" });
  await admin
    .getByRole("button", { name: "Fechar análise do card", exact: true })
    .click();
  const file = admin.waitForEvent("download");
  await admin
    .getByRole("button", { name: "Exportar Excel (.xlsx)", exact: true })
    .click();
  expect((await file).suggestedFilename()).toBe("os-manager.xlsx");
  await expect(
    vendor.getByRole("link", { name: "Relatórios", exact: true }),
  ).toHaveCount(0);
  const blocked = await vendor.request.get(`/api/v1/reports/cards/${task.id}`);
  expect(blocked.status()).toBe(403);
  await vendor.goto("/relatorios");
  await expect(
    vendor.getByText("Acesso restrito a usuários internos.", { exact: true }),
  ).toBeVisible();
  await expect(
    vendor.getByRole("button", { name: "Exportar HTML", exact: true }),
  ).toHaveCount(0);
  await adminContext.close();
  await vendorContext.close();
});

test("administrador limpa todos os filtros para emitir relatório completo", async ({
  page,
}) => {
  await login(page, "admin");
  await page.getByRole("link", { name: "Relatórios", exact: true }).click();
  const total = (
    await (await page.request.get("/api/v1/reports/analysis")).json()
  ).total;
  await page
    .getByRole("combobox", { name: "Status", exact: true })
    .selectOption("production");
  await page
    .getByRole("combobox", { name: "Fornecedor", exact: true })
    .selectOption("1");
  await page.getByLabel("De", { exact: true }).fill("2026-01-01");
  await page.getByLabel("Até", { exact: true }).fill("2026-01-02");
  await page
    .getByRole("button", { name: "+ Adicionar filtro", exact: true })
    .click();
  await page
    .getByLabel("Valor do filtro 1", { exact: true })
    .fill("SEM RESULTADO");
  await page
    .getByRole("button", { name: "Aplicar filtros", exact: true })
    .click();
  await page.getByLabel("Somente reabertos", { exact: true }).check();
  await page.getByLabel("Somente com atraso", { exact: true }).check();
  await page.getByLabel("Tempo mínimo na fase atual (horas)").fill("999");
  await page
    .getByRole("button", { name: "Aplicar análise", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Relatório completo — limpar todos os filtros",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("combobox", { name: "Status", exact: true }),
  ).toHaveValue("");
  await expect(
    page.getByRole("combobox", { name: "Fornecedor", exact: true }),
  ).toHaveValue("");
  await expect(page.getByLabel("De", { exact: true })).toHaveValue("");
  await expect(page.getByLabel("Até", { exact: true })).toHaveValue("");
  await expect(
    page.getByLabel("Valor do filtro 1", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByLabel("Somente reabertos", { exact: true }),
  ).not.toBeChecked();
  await expect(
    page.getByLabel("Somente com atraso", { exact: true }),
  ).not.toBeChecked();
  await expect(
    page.getByLabel("Tempo mínimo na fase atual (horas)"),
  ).toHaveValue("");
  await expect(
    page.getByText(`${total} atividade(s) encontrada(s).`, { exact: true }),
  ).toBeVisible();
  const request = page.waitForRequest((request) =>
    request.url().includes("/exports/html?"),
  );
  await page
    .getByRole("button", { name: "Exportar HTML", exact: true })
    .click();
  const params = new URL((await request).url()).searchParams;
  for (const field of [
    "status",
    "supplier_id",
    "sprint_id",
    "starts",
    "ends",
    "field_filters",
    "only_reopened",
    "overdue_only",
    "min_phase_hours",
  ]) {
    expect(params.has(field)).toBe(false);
  }
});

test("fornecedor recebe confirmação e pode editar horas salvas", async ({
  browser,
}) => {
  const adminContext = await browser.newContext();
  const supplierContext = await browser.newContext();
  const admin = await adminContext.newPage();
  const supplier = await supplierContext.newPage();
  await login(admin, "admin");
  const me = await (await admin.request.get("/api/v1/auth/me")).json();
  const title = "Confirmação de horas " + Date.now();
  const task = await (
    await admin.request.post("/api/v1/tasks", {
      headers: { "X-CSRF-Token": me.csrf },
      data: { title, supplier_id: 1 },
    })
  ).json();
  let current = task;
  for (const status of ["todo", "production"]) {
    const moved = await admin.request.post(`/api/v1/tasks/${task.id}/move`, {
      headers: { "X-CSRF-Token": me.csrf },
      data: { version: current.version, status },
    });
    expect(moved.ok()).toBe(true);
    current = await moved.json();
  }
  await login(supplier, "fornecedor");
  await supplier
    .getByRole("link", { name: "Minhas tarefas", exact: true })
    .click();
  await supplier.getByRole("button", { name: new RegExp(title) }).click();
  const input = supplier.getByLabel("Horas utilizadas (total)", {
    exact: true,
  });
  await input.fill("12");
  await supplier.route(`**/api/v1/tasks/${task.id}/hours`, (route) =>
    route.fulfill({
      status: 422,
      contentType: "application/json",
      body: JSON.stringify({
        detail: { message: "Falha de gravação para teste." },
      }),
    }),
  );
  await supplier
    .getByRole("button", { name: "Salvar / reapresentar horas", exact: true })
    .click();
  await expect(
    supplier.getByText("Falha de gravação para teste.", { exact: true }),
  ).toBeVisible();
  await expect(
    supplier.getByText("✓ Horas salvas", { exact: true }),
  ).toHaveCount(0);
  await expect(input).toHaveValue("12");
  await supplier.unroute(`**/api/v1/tasks/${task.id}/hours`);
  await supplier
    .getByRole("button", { name: "Salvar / reapresentar horas", exact: true })
    .click();
  await expect(
    supplier.getByText("✓ Horas salvas", { exact: true }),
  ).toBeVisible();
  await expect(
    supplier.getByRole("button", { name: "Editar horas", exact: true }),
  ).toBeEnabled();
  await expect(input).toHaveAttribute("readonly", "");
  await expect(input).toHaveValue("12");
  await supplier
    .getByRole("button", { name: "Editar horas", exact: true })
    .click();
  await expect(input).toBeFocused();
  await expect(input).not.toHaveAttribute("readonly", "");
  await input.fill("10");
  await supplier
    .getByRole("button", { name: "Salvar / reapresentar horas", exact: true })
    .click();
  await expect(
    supplier.getByText("✓ Horas salvas", { exact: true }),
  ).toBeVisible();
  await expect(
    supplier.getByRole("button", { name: "Editar horas", exact: true }),
  ).toBeEnabled();
  expect(
    (await (await supplier.request.get(`/api/v1/tasks/${task.id}`)).json())
      .used_minutes,
  ).toBe(600);
  await admin.getByRole("link", { name: "Backlog", exact: true }).click();
  await admin.getByRole("button", { name: new RegExp(title) }).click();
  await admin.getByRole("button", { name: "Histórico", exact: true }).click();
  await expect(
    admin.getByRole("heading", { name: "Histórico de versões", exact: true }),
  ).toBeVisible();
  await expect(
    admin.getByText("Horas editadas / reapresentadas", { exact: true }),
  ).toBeVisible();
  const comparison = admin
    .getByRole("table", { name: /Comparação da alteração/ })
    .last();
  await expect(comparison).toContainText("Horas utilizadas");
  await expect(comparison).toContainText("12h 0min");
  await expect(comparison).toContainText("10h 0min");
  await expect(admin.locator(".timeline")).toContainText("fornecedor");
  await admin.screenshot({
    path: "test-results/historico-horas.png",
    fullPage: true,
  });
  await adminContext.close();
  await supplierContext.close();
});
