import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60000,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "http://localhost:5173",
    headless: true,
  },
  webServer: [
    {
      command: "python3 -m backend.main",
      cwd: "..",
      url: "http://localhost:8000/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
      env: {
        APP_ENV: "test",
        PORT: "8000",
        GROQ_API_KEY: process.env.GROQ_API_KEY || "test-key",
      },
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 120000,
      env: {
        VITE_USE_MOCK: "false",
        VITE_API_BASE: "/api",
      },
    },
  ],
});
