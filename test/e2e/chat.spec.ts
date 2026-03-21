import { test, expect } from "@playwright/test";

test.describe("AI Chat (Mocked)", () => {
  test("should show chat panel with AI Assistant heading", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("AI Assistant")).toBeVisible();
    await expect(
      page.getByText("Ask about your portfolio")
    ).toBeVisible();
  });

  test("should send a message and receive a response", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(2000);

    // Type a message in the chat input
    const chatInput = page.getByPlaceholder("Ask about your portfolio...");
    await chatInput.fill("How is my portfolio doing?");

    // Click Send
    await page.getByRole("button", { name: "Send" }).click();

    // The user message should appear
    await expect(
      page.getByText("How is my portfolio doing?")
    ).toBeVisible();

    // Should show "Thinking..." loading state
    // Then the mock response should appear
    await expect(
      page.getByText(/Mock:.*portfolio.*diversified/i).or(
        page.getByText(/Mock:/)
      )
    ).toBeVisible({ timeout: 15_000 });
  });

  test("should execute a buy trade via chat", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(2000);

    // Send a buy command via chat
    const chatInput = page.getByPlaceholder("Ask about your portfolio...");
    await chatInput.fill("Buy 5 AAPL");
    await page.getByRole("button", { name: "Send" }).click();

    // The mock handler should respond with a buy action
    // Look for "Executed" trade confirmation inline
    await expect(
      page.getByText(/Executed.*BUY.*5.*AAPL/i).or(
        page.getByText(/Mock:.*Buying.*5.*shares.*AAPL/i)
      )
    ).toBeVisible({ timeout: 15_000 });
  });

  test("should execute a sell trade via chat after buying", async ({
    page,
  }) => {
    await page.goto("/");

    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(2000);

    // First buy via trade bar
    const tickerInput = page.getByPlaceholder("TICKER");
    const qtyInput = page.getByPlaceholder("QTY");
    await tickerInput.fill("TSLA");
    await qtyInput.fill("10");
    await page.getByRole("button", { name: "BUY" }).click();

    // Wait for position
    await expect(
      page.locator("table").getByText("TSLA", { exact: true })
    ).toBeVisible({ timeout: 10_000 });

    // Now sell via chat
    const chatInput = page.getByPlaceholder("Ask about your portfolio...");
    await chatInput.fill("Sell 5 TSLA");
    await page.getByRole("button", { name: "Send" }).click();

    // Should see the mock sell response
    await expect(
      page.getByText(/Mock:.*Selling.*5.*shares.*TSLA/i).or(
        page.getByText(/Executed.*SELL.*5.*TSLA/i)
      )
    ).toBeVisible({ timeout: 15_000 });
  });

  test("should show watchlist changes via chat", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(2000);

    // Ask to add a ticker to watchlist via chat
    const chatInput = page.getByPlaceholder("Ask about your portfolio...");
    await chatInput.fill("Add PYPL to my watchlist");
    await page.getByRole("button", { name: "Send" }).click();

    // Should see the watchlist change confirmation
    await expect(
      page.getByText(/Added.*PYPL.*watchlist/i).or(
        page.getByText(/Mock:.*Adding.*PYPL/i)
      )
    ).toBeVisible({ timeout: 15_000 });
  });

  test("should minimize and restore chat panel", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("AI Assistant")).toBeVisible();

    // Click Minimize
    await page.getByText("Minimize").click();

    // AI Assistant heading should disappear
    await expect(page.getByText("AI Assistant")).not.toBeVisible();

    // "AI Chat" button should appear to restore
    await expect(page.getByText("AI Chat")).toBeVisible();

    // Click to restore
    await page.getByText("AI Chat").click();

    // AI Assistant heading should be back
    await expect(page.getByText("AI Assistant")).toBeVisible();
  });
});
