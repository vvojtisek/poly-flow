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
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3001",
    locale: "cs-CZ",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    // Sandboxes with a preinstalled Chromium can point at it instead of downloading one.
    launchOptions: process.env.PW_CHROMIUM_PATH ? { executablePath: process.env.PW_CHROMIUM_PATH } : {},
  },
  projects: [
    { name: "mobile-chromium", testIgnore: /desktop/, use: { ...devices["Pixel 7"] } },
    {
      name: "desktop-chromium",
      testMatch: /desktop/,
      dependencies: ["mobile-chromium"], // signs in with the admin account the mobile spec sets up
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
  ],
});
