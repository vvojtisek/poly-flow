import { defineConfig, devices } from "@playwright/test";

// E2E against a running stack (docker compose in CI). The spec needs a fresh database
// (first-run setup) with the core100 lexicon seeded.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    locale: "cs-CZ",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    // Sandboxes with a preinstalled Chromium can point at it instead of downloading one.
    launchOptions: process.env.PW_CHROMIUM_PATH ? { executablePath: process.env.PW_CHROMIUM_PATH } : {},
  },
  projects: [{ name: "mobile-chromium", use: { ...devices["Pixel 7"] } }],
});
