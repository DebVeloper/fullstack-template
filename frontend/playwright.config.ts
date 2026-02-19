import { defineConfig } from "@playwright/test";

const defaultBaseURL = "http://127.0.0.1:3000";
const evidenceRoot = "../.sisyphus/evidence";

export default defineConfig({
  testDir: "./e2e",
  outputDir: `${evidenceRoot}/task-24-playwright-results`,
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: `${evidenceRoot}/task-24-playwright-report` }]
  ],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? defaultBaseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure"
  },
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : {
      command: "pnpm dev --hostname 127.0.0.1 --port 3000",
      url: defaultBaseURL,
      reuseExistingServer:
        process.env.AUTH_TEST_MODE === "true" ? false : !process.env.CI,
      env: {
        ...process.env,
        AUTH_TEST_MODE: process.env.AUTH_TEST_MODE ?? "false",
          AUTH_TEST_SECRET: process.env.AUTH_TEST_SECRET ?? ""
        }
      }
});
