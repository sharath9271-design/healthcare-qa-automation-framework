// MedPortal — a small, self-contained demo "patient portal" used as the
// system-under-test for the Playwright UI suite in this repository.
// No backend, no real patient data: all state lives in memory and resets
// on every page load, which keeps UI tests fast and fully isolated.

const DEMO_USER = {
  email: "patient@example.com",
  password: "Patient123!",
  name: "Jordan Lee",
};

let appointments = [];

function seedAppointments() {
  appointments = [
    { doctor: "Dr. Priya Nair — General Practice", date: "2026-09-02", reason: "Annual physical" },
    { doctor: "Dr. Amara Osei — Cardiology", date: "2026-09-15", reason: "Follow-up consultation" },
  ];
}

function renderAppointments() {
  const list = document.getElementById("appointments-list");
  list.innerHTML = "";
  appointments.forEach((appt) => {
    const li = document.createElement("li");
    li.className = "appointment-item";
    li.textContent = `${appt.date} — ${appt.doctor} (${appt.reason})`;
    list.appendChild(li);
  });
}

function showDashboard() {
  document.getElementById("login-view").classList.add("hidden");
  document.getElementById("dashboard-view").classList.remove("hidden");
  document.getElementById("nav-logged-in").classList.remove("hidden");
  document.getElementById("welcome-text").textContent = `Welcome, ${DEMO_USER.name}`;
  renderAppointments();
}

function showLogin() {
  document.getElementById("dashboard-view").classList.add("hidden");
  document.getElementById("nav-logged-in").classList.add("hidden");
  document.getElementById("login-view").classList.remove("hidden");
  document.getElementById("login-form").reset();
  document.getElementById("login-error").classList.add("hidden");
}

document.getElementById("login-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const errorEl = document.getElementById("login-error");

  if (!email || !password) {
    errorEl.textContent = "Email and password are required.";
    errorEl.classList.remove("hidden");
    return;
  }

  if (email === DEMO_USER.email && password === DEMO_USER.password) {
    errorEl.classList.add("hidden");
    seedAppointments();
    showDashboard();
  } else {
    errorEl.textContent = "Invalid email or password.";
    errorEl.classList.remove("hidden");
  }
});

document.getElementById("logout-btn").addEventListener("click", () => {
  showLogin();
});

document.getElementById("booking-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const doctor = document.getElementById("doctor").value;
  const date = document.getElementById("appointment-date").value;
  const reason = document.getElementById("reason").value.trim();
  const errorEl = document.getElementById("booking-error");
  const confirmEl = document.getElementById("booking-confirmation");

  confirmEl.classList.add("hidden");

  if (!doctor || !date || !reason) {
    errorEl.textContent = "Doctor, date, and reason are all required.";
    errorEl.classList.remove("hidden");
    return;
  }

  errorEl.classList.add("hidden");
  appointments.push({ doctor, date, reason });
  renderAppointments();

  confirmEl.textContent = `Appointment booked with ${doctor} on ${date}.`;
  confirmEl.classList.remove("hidden");
  document.getElementById("booking-form").reset();
});
