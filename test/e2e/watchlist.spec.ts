import { test, expect } from '@playwright/test';

/**
 * Watchlist CRUD E2E tests.
 *
 * Verifies adding a new ticker to the watchlist and removing a ticker,
 * using the actual UI controls: input with placeholder "TICKER",
 * "Add" button, and the "x" remove button with aria-label.
 */

test.describe('Watchlist Management', () => {
  test('add a ticker to the watchlist', async ({ page }) => {
    await page.goto('/');

    // Wait for watchlist to load with default tickers
    await expect(page.getByText('AAPL', { exact: true }).first()).toBeVisible({ timeout: 15000 });

    // The watchlist has an input with placeholder "TICKER" and an "Add" button
    // There are two TICKER inputs (watchlist and trade bar) — use the one near the "Add" button
    const addInput = page.locator('input[placeholder="TICKER"]').first();
    await addInput.fill('DIS');

    await page.getByRole('button', { name: 'Add' }).click();

    // Wait for API response and re-render
    await expect(page.getByText('DIS', { exact: true }).first()).toBeVisible({ timeout: 10000 });
  });

  test('remove a ticker from the watchlist', async ({ page }) => {
    await page.goto('/');

    // Wait for watchlist to load
    await expect(page.getByText('NFLX', { exact: true }).first()).toBeVisible({ timeout: 15000 });

    // Each watchlist row has a remove button with aria-label="Remove {ticker}"
    await page.getByLabel('Remove NFLX').click();

    // Verify NFLX is no longer visible in the watchlist
    // Use a tight locator to avoid matching other text — check the bold ticker span
    await expect(page.getByLabel('Remove NFLX')).toBeHidden({ timeout: 10000 });
  });
});
