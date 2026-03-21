import { test, expect } from "@playwright/test";

test.describe("SSE Resilience", () => {
  test("should show connected status when SSE is active", async ({ page }) => {
    await page.goto("/");

    // Wait for SSE connection to establish
    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });
  });

  test("should recover from SSE disconnection", async ({ page }) => {
    await page.goto("/");

    // Wait for initial connection
    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });

    // Simulate SSE disconnection by blocking the stream endpoint
    await page.route("**/api/stream/prices", (route) => route.abort());

    // Wait for the status to change from "Live"
    await expect(
      page
        .getByText("Reconnecting...")
        .or(page.getByText("Disconnected"))
    ).toBeVisible({ timeout: 15_000 });

    // Unblock the route to allow reconnection
    await page.unroute("**/api/stream/prices");

    // EventSource should auto-reconnect — status should return to "Live"
    await expect(page.getByText("Live")).toBeVisible({ timeout: 30_000 });
  });

  test("should continue showing prices after reconnection", async ({
    page,
  }) => {
    await page.goto("/");

    await expect(page.getByText("Live")).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(2000);

    // Verify prices are showing
    const pricesBefore = page.locator("text=/\\$\\d+\\.\\d{2}/");
    await expect(pricesBefore.first()).toBeVisible();

    // Brief disconnection
    await page.route("**/api/stream/prices", (route) => route.abort());
    await page.waitForTimeout(3000);
    await page.unroute("**/api/stream/prices");

    // Wait for reconnection
    await expect(page.getByText("Live")).toBeVisible({ timeout: 30_000 });

    // Prices should still be displayed
    await page.waitForTimeout(2000);
    const pricesAfter = page.locator("text=/\\$\\d+\\.\\d{2}/");
    await expect(pricesAfter.first()).toBeVisible();
  });
});
