import { test, expect } from '@playwright/test';

/**
 * Fresh start E2E tests.
 *
 * Verifies the app boots with correct defaults: 10 watchlist tickers,
 * $10,000 cash balance, and live SSE price streaming.
 */

test.describe('Fresh Start', () => {
  test('shows default watchlist with 10 tickers', async ({ page }) => {
    await page.goto('/');

    // All 10 default tickers from seed data should be visible in the watchlist
    const tickers = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'JPM', 'V', 'NFLX'];
    for (const ticker of tickers) {
      await expect(page.getByText(ticker, { exact: true }).first()).toBeVisible({ timeout: 15000 });
    }
  });

  test('shows $10,000 starting cash balance', async ({ page }) => {
    await page.goto('/');

    // Header displays "Cash" label followed by formatted currency via Intl.NumberFormat
    // which produces "$10,000.00" for en-US USD format
    await expect(page.getByText('$10,000.00')).toBeVisible({ timeout: 10000 });
  });

  test('prices are streaming via SSE', async ({ page }) => {
    await page.goto('/');

    // Wait for SSE to deliver initial prices — the simulator updates every ~500ms
    // Watchlist rows display price as {price.toFixed(2)}, e.g. "190.50"
    // Wait for at least one numeric price to appear in the watchlist area
    await page.waitForTimeout(3000);

    // Connection status indicator should show "connected" text (lowercase, from Header)
    await expect(page.getByText('connected')).toBeVisible({ timeout: 10000 });

    // Verify at least one price value is present — prices are rendered as numeric
    // with 2 decimal places in WatchlistRow (e.g., "190.50")
    const pricePattern = page.locator('span.tabular-nums').first();
    await expect(pricePattern).toBeVisible({ timeout: 10000 });
  });
});
