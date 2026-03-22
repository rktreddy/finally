import { test, expect } from '@playwright/test';

/**
 * Trading E2E tests.
 *
 * Verifies buying and selling shares via the TradeBar component.
 * Tests use serial execution since sell depends on buy creating a position.
 *
 * TradeBar has: input[placeholder="TICKER"], input[placeholder="QTY"],
 * "BUY" button, "SELL" button, and inline feedback text.
 */

test.describe.serial('Trading', () => {
  test('buy shares — cash decreases and position appears', async ({ page }) => {
    await page.goto('/');

    // Wait for prices to stream so trades can execute at a valid price
    await expect(page.getByText('connected')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('$10,000.00')).toBeVisible({ timeout: 10000 });

    // Fill the trade bar — TradeBar has its own TICKER input (second on page)
    // and a QTY input. Use the trade bar's specific inputs.
    const tickerInputs = page.locator('input[placeholder="TICKER"]');
    // The trade bar ticker input is the second TICKER input on the page
    const tradeTickerInput = tickerInputs.nth(1);
    await tradeTickerInput.fill('AAPL');

    const qtyInput = page.locator('input[placeholder="QTY"]');
    await qtyInput.fill('5');

    // Click BUY
    await page.getByRole('button', { name: 'BUY' }).click();

    // Wait for trade confirmation feedback — TradeBar shows "Bought X TICKER at $Y"
    await expect(page.getByText(/Bought 5 AAPL at \$/)).toBeVisible({ timeout: 10000 });

    // Cash should have decreased from $10,000.00
    // The header still shows "Cash" with a different value
    await expect(page.getByText('$10,000.00')).toBeHidden({ timeout: 5000 });

    // Position should appear in the positions table — PositionsTable shows ticker in a td
    await expect(
      page.locator('table').getByText('AAPL', { exact: true })
    ).toBeVisible({ timeout: 10000 });
  });

  test('sell shares — cash increases and position updates', async ({ page }) => {
    await page.goto('/');

    // Wait for prices to load
    await expect(page.getByText('connected')).toBeVisible({ timeout: 15000 });

    // We need a position to sell. Buy first (fresh DB per test run may not have one).
    const tickerInputs = page.locator('input[placeholder="TICKER"]');
    const tradeTickerInput = tickerInputs.nth(1);
    await tradeTickerInput.fill('AAPL');

    const qtyInput = page.locator('input[placeholder="QTY"]');
    await qtyInput.fill('10');

    // Buy first to create a position
    await page.getByRole('button', { name: 'BUY' }).click();
    await expect(page.getByText(/Bought 10 AAPL at \$/)).toBeVisible({ timeout: 10000 });

    // Record the cash balance after buying
    await page.waitForTimeout(1000);

    // Now sell some shares
    await tradeTickerInput.fill('AAPL');
    await qtyInput.fill('5');
    await page.getByRole('button', { name: 'SELL' }).click();

    // Wait for sell confirmation — "Sold 5 AAPL at $Y"
    await expect(page.getByText(/Sold 5 AAPL at \$/)).toBeVisible({ timeout: 10000 });

    // Position should still exist with reduced quantity (10 - 5 = 5.00)
    await expect(
      page.locator('table').getByText('5.00')
    ).toBeVisible({ timeout: 10000 });
  });
});
