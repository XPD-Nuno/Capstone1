import { defineConfig, devices } from "@playwright/test";

const port = Number(process.env.E2E_PORT ?? 8765);
const python = process.env.PYTHON ?? "python3";

// Runs against the real FastAPI backend serving the built SPA (`npm run build` first),
// with a fresh in-memory database seeded with the synthetic demo leads.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `${python} -m lead_desk serve-api --seed-demo --db :memory: --port ${port}`,
    cwd: "..",
    url: `http://127.0.0.1:${port}/api/health`,
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
