import { test, expect } from '@playwright/test';

/**
 * AI Chat E2E tests.
 *
 * Verifies sending a message to the mocked AI assistant and receiving
 * a response with inline trade confirmation. Uses LLM_MOCK=true which
 * returns deterministic responses based on keywords.
 *
 * ChatPanel has: input[placeholder="Ask your AI assistant..."],
 * "Send" button, "Thinking..." loading indicator, and inline action
 * confirmations (e.g., "Bought 10 AAPL at $X").
 */

test.describe('AI Chat', () => {
  test('send a message and receive AI response', async ({ page }) => {
    await page.goto('/');

    // Wait for SSE connection so prices are available for mock trades
    await expect(page.getByText('connected')).toBeVisible({ timeout: 15000 });

    // Type a generic message (no buy/sell/add/remove keywords)
    // Mock returns: "Your portfolio is well-diversified across tech and finance sectors..."
    const chatInput = page.getByPlaceholder('Ask your AI assistant...');
    await chatInput.fill('How is my portfolio doing?');

    await page.getByRole('button', { name: 'Send' }).click();

    // Loading indicator should appear briefly
    // Note: "Thinking..." may disappear quickly with mock mode, so use a short timeout
    // The user message should appear
    await expect(page.getByText('How is my portfolio doing?')).toBeVisible({ timeout: 5000 });

    // Mock response text: "Your portfolio is well-diversified across tech and finance sectors."
    await expect(
      page.getByText('Your portfolio is well-diversified')
    ).toBeVisible({ timeout: 15000 });
  });

  test('chat trade execution appears inline', async ({ page }) => {
    await page.goto('/');

    // Wait for SSE connection
    await expect(page.getByText('connected')).toBeVisible({ timeout: 15000 });

    // Send a message containing "buy" — mock returns:
    // message: "I've placed a buy order for 10 shares of AAPL."
    // trades: [{ticker: "AAPL", side: "buy", quantity: 10}]
    const chatInput = page.getByPlaceholder('Ask your AI assistant...');
    await chatInput.fill('Please buy some AAPL');

    await page.getByRole('button', { name: 'Send' }).click();

    // Wait for AI response message
    await expect(
      page.getByText("I've placed a buy order for 10 shares of AAPL")
    ).toBeVisible({ timeout: 15000 });

    // Inline trade confirmation should appear — ChatPanel renders:
    // "Bought 10 AAPL at $X.XX" in a green-bordered div
    await expect(
      page.getByText(/Bought 10 AAPL at \$/)
    ).toBeVisible({ timeout: 10000 });
  });
});
