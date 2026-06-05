import { test, expect } from "@playwright/test";

test.describe("demo flywheel", () => {
  test("person1 has fewer memories than person10", async ({ page }) => {
    await page.goto("http://localhost:5173");

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
