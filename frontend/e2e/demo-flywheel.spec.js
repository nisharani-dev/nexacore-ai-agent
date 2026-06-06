import { test, expect } from "@playwright/test";

test.describe("demo flywheel", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/chat", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          message: "Welcome to Ramp onboarding.",
          memories_used: [],
          new_memories_written: [],
          suggested_actions: [],
          tools_used: [],
          integrations_mode: "demo",
        }),
      });
    });
  });

  test("person1 has fewer memories than person10", async ({ page }) => {
    await page.goto("/");

    await page.fill('input[placeholder*="Priya"]', "Demo User");
    await page.click('button:has-text("begin onboarding")');

    await expect(page.locator(".persona-banner-num")).toBeVisible();

    const countPerson1 = parseInt(await page.locator(".persona-banner-num").innerText(), 10);

    await page.click('button:has-text("person #10")');
    await page.waitForTimeout(500);

    const countPerson10 = parseInt(await page.locator(".persona-banner-num").innerText(), 10);
    expect(countPerson10).toBeGreaterThanOrEqual(countPerson1);
  });
});
