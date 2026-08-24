import { test, expect } from "@playwright/test";
import { LocatorHealer, byTestIdWithFallback } from "../../healing/locator_healer";

/**
 * Proves the self-healing layer works end-to-end using nothing but the
 * heuristic tiers — no ANTHROPIC_API_KEY, no network access. Every
 * `data-testid` queried below is deliberately wrong/stale (the real ones
 * live in tests/ui/pages/LoginPage.ts); the healer must fall through to a
 * label- or role-based strategy and still complete a real login.
 */
test.describe("Self-healing locators", () => {
  test("recovers from stale data-testids via label/role fallbacks and logs in", async ({ page }) => {
    await page.goto("/");

    const healer = new LocatorHealer(page);

    const emailField = byTestIdWithFallback("email-field", "email-input-STALE", [
      { name: "label", resolve: (p) => p.getByLabel("Email") },
    ]);
    const passwordField = byTestIdWithFallback("password-field", "password-input-STALE", [
      { name: "label", resolve: (p) => p.getByLabel("Password") },
    ]);
    const loginButton = byTestIdWithFallback("login-button", "login-btn-STALE", [
      { name: "role+name", resolve: (p) => p.getByRole("button", { name: "Sign in" }) },
    ]);

    const email = await healer.resolve(emailField);
    const password = await healer.resolve(passwordField);
    const submit = await healer.resolve(loginButton);

    await email.fill("patient@example.com");
    await password.fill("Patient123!");
    await submit.click();

    await expect(page.getByTestId("welcome-text")).toHaveText("Welcome, Jordan Lee");

    // All three lookups should have healed, since the primary testId
    // strategy was deliberately broken for each.
    expect(healer.healedEvents).toHaveLength(3);
    expect(healer.healedEvents.map((e) => e.strategyUsed)).toEqual(["label", "label", "role+name"]);
    expect(healer.healedEvents.every((e) => e.descriptorName && e.timestamp)).toBe(true);
  });

  test("does not report healing when the primary locator still works", async ({ page }) => {
    await page.goto("/");

    const healer = new LocatorHealer(page);
    const emailField = byTestIdWithFallback("email-field", "email-input", [
      { name: "label", resolve: (p) => p.getByLabel("Email") },
    ]);

    await healer.resolve(emailField);

    expect(healer.healedEvents).toHaveLength(0);
  });

  test("throws a clear error when no strategy resolves", async ({ page }) => {
    await page.goto("/");
    const healer = new LocatorHealer(page);

    const nonexistent = byTestIdWithFallback("nonexistent-widget", "does-not-exist", [
      {
        name: "role",
        resolve: (p) => p.getByRole("button", { name: "Definitely Not On This Page" }),
      },
    ]);

    await expect(healer.resolve(nonexistent)).rejects.toThrow(/exhausted/);
  });
});
