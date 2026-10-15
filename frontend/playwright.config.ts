import { defineConfig } from "@playwright/test";
const remoteURL = process.env.E2E_BASE_URL;
export default defineConfig({
  timeout: remoteURL ? 90000 : 30000,
  expect: { timeout: remoteURL ? 20000 : 5000 },
  testDir: "e2e",
  use: {
    baseURL: remoteURL || "http://127.0.0.1:5174",
    headless: true,
    locale: "pt-BR",
    timezoneId: "America/Sao_Paulo",
    trace: remoteURL ? "off" : "retain-on-failure",
  },
  workers: 1,
  reporter: "list",
  webServer: remoteURL
    ? undefined
    : {
        command: "npm run dev -- --port 5174 --strictPort",
        url: "http://127.0.0.1:5174",
        reuseExistingServer: false,
      },
});
