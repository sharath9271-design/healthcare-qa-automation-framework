import { test, expect } from "@playwright/test";
import { LoginPage } from "./pages/LoginPage";
import { PatientPortalPage } from "./pages/PatientPortalPage";

test.describe("Sign in", () => {
  test("valid credentials land on the dashboard", async ({ page }) => {
    const login = new LoginPage(page);
    const portal = new PatientPortalPage(page);

    await login.goto();
    await login.login("patient@example.com", "Patient123!");

    await expect(portal.welcomeText).toHaveText("Welcome, Jordan Lee");
    await expect(page.getByRole("heading", { name: "Your appointments" })).toBeVisible();
  });

  test("invalid password shows an error and stays on the login screen", async ({ page }) => {
    const login = new LoginPage(page);

    await login.goto();
    await login.login("patient@example.com", "wrong-password");

    await login.expectError("Invalid email or password.");
    await expect(page.getByRole("heading", { name: "Sign in to your account" })).toBeVisible();
  });

  test("empty fields are rejected client-side", async ({ page }) => {
    const login = new LoginPage(page);

    await login.goto();
    await login.loginButton.click();

    await login.expectError("Email and password are required.");
  });

  test("logout returns to the sign-in screen", async ({ page }) => {
    const login = new LoginPage(page);
    const portal = new PatientPortalPage(page);

    await login.goto();
    await login.login("patient@example.com", "Patient123!");
    await expect(portal.welcomeText).toBeVisible();

    await portal.logout();

    await expect(page.getByRole("heading", { name: "Sign in to your account" })).toBeVisible();
  });
});
