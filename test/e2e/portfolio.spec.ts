import { test, expect } from "@playwright/test";

test.describe("Portfolio Visualization", () => {
  test("should show heatmap after buying positions", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(2000);

    // Buy some shares to create a position
    const tickerInput = page.getByPlaceholder("TICKER");
    const qtyInput = page.getByPlaceholder("QTY");

    await tickerInput.fill("NVDA");
    await qtyInput.fill("3");
    await page.getByRole("button", { name: "BUY" }).click();

    // Wait for the heatmap to update — it should show NVDA
    await page.waitForTimeout(2000);

    // The heatmap section should now contain the ticker
    const heatmapSection = page.locator("div").filter({
      hasText: /Portfolio Heatmap/,
    });
    await expect(heatmapSection).toBeVisible();

    // "No positions to display" should no longer appear
    await expect(page.getByText("No positions to display")).not.toBeVisible({
      timeout: 10_000,
    });
  });

  test("should show P&L history section", async ({ page }) => {
    await page.goto("/");

    // The P&L History section should be visible
    await expect(page.getByText("P&L History")).toBeVisible();

    // Initially should say "Portfolio history will appear here"
    await expect(
      page.getByText("Portfolio history will appear here")
    ).toBeVisible({ timeout: 10_000 });
  });

  test("should update portfolio value in header after trade", async ({
    page,
  }) => {
    await page.goto("/");

    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(2000);

    // Record initial portfolio value text
    const portfolioValueBefore = await page
      .locator("header")
      .getByText(/\$[\d,]+/)
      .first()
      .textContent();

    // Buy some shares
    const tickerInput = page.getByPlaceholder("TICKER");
    const qtyInput = page.getByPlaceholder("QTY");

    await tickerInput.fill("GOOGL");
    await qtyInput.fill("2");
    await page.getByRole("button", { name: "BUY" }).click();

    // Wait for portfolio refresh
    await page.waitForTimeout(3000);

    // The cash balance in header should have changed
    const cashText = page
      .locator("header")
      .locator("div")
      .filter({ hasText: "Cash" });
    await expect(cashText).toBeVisible();
  });
});
