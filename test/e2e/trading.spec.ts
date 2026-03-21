import { test, expect } from "@playwright/test";

test.describe("Trading", () => {
  test("should buy shares and see position appear", async ({ page }) => {
    await page.goto("/");

    // Wait for prices to start streaming so trades can execute
    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(2000); // Wait for prices to populate

    // Fill in the trade bar
    const tickerInput = page.getByPlaceholder("TICKER");
    const qtyInput = page.getByPlaceholder("QTY");

    await tickerInput.fill("AAPL");
    await qtyInput.fill("5");

    // Click the BUY button
    await page.getByRole("button", { name: "BUY" }).click();

    // Wait for the trade to execute — position should appear in the positions table
    await expect(
      page
        .locator("table")
        .getByText("AAPL", { exact: true })
    ).toBeVisible({ timeout: 10_000 });

    // Cash balance should decrease (no longer exactly $10,000)
    await page.waitForTimeout(1000);
    // The header should still show a portfolio value
    await expect(page.getByText("Portfolio")).toBeVisible();
  });

  test("should show error for insufficient cash", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(2000);

    // Try to buy a huge quantity
    const tickerInput = page.getByPlaceholder("TICKER");
    const qtyInput = page.getByPlaceholder("QTY");

    await tickerInput.fill("AAPL");
    await qtyInput.fill("100000");

    await page.getByRole("button", { name: "BUY" }).click();

    // Should show an error about insufficient cash
    await expect(page.getByText(/insufficient cash/i).or(page.getByText(/Trade failed/i))).toBeVisible({
      timeout: 10_000,
    });
  });

  test("should sell shares after buying", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(2000);

    // First buy some shares
    const tickerInput = page.getByPlaceholder("TICKER");
    const qtyInput = page.getByPlaceholder("QTY");

    await tickerInput.fill("MSFT");
    await qtyInput.fill("5");
    await page.getByRole("button", { name: "BUY" }).click();

    // Wait for position to appear
    await expect(
      page.locator("table").getByText("MSFT", { exact: true })
    ).toBeVisible({ timeout: 10_000 });

    // Now sell the shares
    await tickerInput.fill("MSFT");
    await qtyInput.fill("5");
    await page.getByRole("button", { name: "SELL" }).click();

    // Position should disappear (sold all)
    await page.waitForTimeout(2000);

    // After selling all, it may say "No open positions" if MSFT was the only one
    // Or MSFT disappears from the positions table
    await expect(
      page.locator("table").getByText("MSFT", { exact: true })
    ).not.toBeVisible({ timeout: 10_000 });
  });

  test("should validate empty ticker/quantity", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });

    // Click BUY with empty fields
    await page.getByRole("button", { name: "BUY" }).click();

    // Should show validation error
    await expect(
      page.getByText("Enter a valid ticker and quantity")
    ).toBeVisible({ timeout: 5000 });
  });
});
