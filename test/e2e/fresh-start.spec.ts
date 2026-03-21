import { test, expect } from "@playwright/test";

test.describe("Fresh Start", () => {
  test("should display the FinAlly header with branding", async ({ page }) => {
    await page.goto("/");

    // FinAlly branding is visible
    await expect(page.getByText("FinAlly")).toBeVisible();
    await expect(page.getByText("AI Trading Workstation")).toBeVisible();
  });

  test("should show $10,000 initial balance", async ({ page }) => {
    await page.goto("/");

    // Wait for portfolio data to load — look for cash display
    await expect(page.getByText("$10,000")).toBeVisible({ timeout: 15_000 });
  });

  test("should display default watchlist with 10 tickers", async ({
    page,
  }) => {
    await page.goto("/");

    // The watchlist heading should be visible
    await expect(page.getByText("Watchlist")).toBeVisible();

    // Default tickers from PLAN.md seed data
    const defaultTickers = [
      "AAPL",
      "GOOGL",
      "MSFT",
      "AMZN",
      "TSLA",
      "NVDA",
      "META",
      "JPM",
      "V",
      "NFLX",
    ];

    for (const ticker of defaultTickers) {
      await expect(page.getByText(ticker, { exact: true }).first()).toBeVisible(
        { timeout: 15_000 }
      );
    }
  });

  test("should receive SSE price updates (prices streaming)", async ({
    page,
  }) => {
    await page.goto("/");

    // Wait for SSE to connect — connection status should show "Live"
    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });

    // At least one ticker should show a numeric price (not "--")
    // The price format is like "$190.42" — look for a dollar amount in the watchlist area
    await page.waitForTimeout(3000); // Give SSE time to push some data

    // Check that at least one price is rendered (a number with $ prefix)
    const priceElements = page.locator("text=/\\$\\d+\\.\\d{2}/");
    await expect(priceElements.first()).toBeVisible({ timeout: 10_000 });
  });

  test("should show connection status indicator", async ({ page }) => {
    await page.goto("/");

    // Should show the connection status — either "Live", "Reconnecting...", or "Disconnected"
    const statusText = page
      .getByText("Live")
      .or(page.getByText("Reconnecting..."))
      .or(page.getByText("Disconnected"));
    await expect(statusText.first()).toBeVisible({ timeout: 15_000 });
  });

  test("should show UI sections: positions, heatmap, P&L, chat", async ({
    page,
  }) => {
    await page.goto("/");

    await expect(page.getByText("Positions")).toBeVisible();
    await expect(page.getByText("Portfolio Heatmap")).toBeVisible();
    await expect(page.getByText("P&L History")).toBeVisible();
    await expect(page.getByText("AI Assistant")).toBeVisible();
  });

  test("should show empty positions message initially", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("No open positions")).toBeVisible({
      timeout: 10_000,
    });
  });
});
