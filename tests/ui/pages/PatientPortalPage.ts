import { Page, Locator, expect } from "@playwright/test";

/** Page Object for the post-login dashboard: appointment list + booking form. */
export class PatientPortalPage {
  readonly page: Page;
  readonly welcomeText: Locator;
  readonly logoutButton: Locator;
  readonly appointmentsList: Locator;
  readonly doctorSelect: Locator;
  readonly dateInput: Locator;
  readonly reasonInput: Locator;
  readonly bookButton: Locator;
  readonly bookingError: Locator;
  readonly bookingConfirmation: Locator;

  constructor(page: Page) {
    this.page = page;
    this.welcomeText = page.getByTestId("welcome-text");
    this.logoutButton = page.getByTestId("logout-btn");
    this.appointmentsList = page.getByTestId("appointments-list");
    this.doctorSelect = page.getByTestId("doctor-select");
    this.dateInput = page.getByTestId("date-input");
    this.reasonInput = page.getByTestId("reason-input");
    this.bookButton = page.getByTestId("book-btn");
    this.bookingError = page.getByTestId("booking-error");
    this.bookingConfirmation = page.getByTestId("booking-confirmation");
  }

  async appointmentCount(): Promise<number> {
    return this.appointmentsList.locator("li").count();
  }

  async bookAppointment(doctor: string, date: string, reason: string) {
    await this.doctorSelect.selectOption({ label: doctor });
    await this.dateInput.fill(date);
    await this.reasonInput.fill(reason);
    await this.bookButton.click();
  }

  async logout() {
    await this.logoutButton.click();
  }

  async expectConfirmation(text: string | RegExp) {
    await expect(this.bookingConfirmation).toBeVisible();
    await expect(this.bookingConfirmation).toContainText(text);
  }
}
