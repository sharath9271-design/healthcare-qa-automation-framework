import { test, expect } from "@playwright/test";
import { LoginPage } from "./pages/LoginPage";
import { PatientPortalPage } from "./pages/PatientPortalPage";

test.describe("Appointments", () => {
  test.beforeEach(async ({ page }) => {
    const login = new LoginPage(page);
    await login.goto();
    await login.login("patient@example.com", "Patient123!");
  });

  test("seeded appointments are visible on load", async ({ page }) => {
    const portal = new PatientPortalPage(page);
    await expect(await portal.appointmentCount()).toBe(2);
    await expect(portal.appointmentsList).toContainText("General Practice");
    await expect(portal.appointmentsList).toContainText("Cardiology");
  });

  test("booking a new appointment adds it to the list", async ({ page }) => {
    const portal = new PatientPortalPage(page);

    await portal.bookAppointment(
      "Dr. Liam Chen — Dermatology",
      "2026-10-01",
      "Skin check"
    );

    await portal.expectConfirmation("Dr. Liam Chen — Dermatology");
    await expect(await portal.appointmentCount()).toBe(3);
    await expect(portal.appointmentsList).toContainText("Skin check");
  });

  test("booking with a missing reason is rejected", async ({ page }) => {
    const portal = new PatientPortalPage(page);

    await portal.doctorSelect.selectOption({ label: "Dr. Amara Osei — Cardiology" });
    await portal.dateInput.fill("2026-10-05");
    await portal.bookButton.click();

    await expect(portal.bookingError).toBeVisible();
    await expect(portal.bookingError).toHaveText("Doctor, date, and reason are all required.");
    await expect(await portal.appointmentCount()).toBe(2);
  });
});
