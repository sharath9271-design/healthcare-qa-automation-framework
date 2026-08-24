# Healthcare QA Automation Framework

A production-shaped test automation framework built around a small, self-contained
"patient portal" app: **Playwright + TypeScript** for UI, **Python + PyTest** for API
testing against a real FHIR R4 server, and a **sharded GitHub Actions** pipeline tying
both suites together.

It's designed to demonstrate how a healthcare-domain QA automation framework is
actually structured day to day — Page Object Model, data-driven fixtures, negative-path
API coverage, and CI that shards the UI suite across parallel jobs — rather than a
single toy test file.

## Why it's built this way

- **No real patient data, ever.** The UI app is a static demo with in-memory state and
  a hardcoded demo login. The API suite talks to
  [HAPI FHIR's public R4 test server](https://hapi.fhir.org/baseR4), a sandbox the HL7
  community runs specifically for demos and automated testing.
- **UI and API are tested independently.** The Playwright suite never depends on the
  live FHIR server, and the API suite never depends on a browser — each can run, fail,
  and report on its own.
- **Every API test cleans up after itself**, using a per-run unique synthetic surname so
  repeated runs against the shared public sandbox don't collide or accumulate junk data.

## Architecture

```
app/                     Static "patient portal" demo app (HTML/CSS/JS, no backend)
tests/ui/                Playwright + TypeScript UI suite (Page Object Model)
  pages/                 LoginPage, PatientPortalPage
tests/api/                Python + PyTest API suite against a live FHIR R4 server
  fhir_client.py          Thin requests-based FHIR client (base URL is configurable)
  test_patient_api.py      Positive-path: create / read / search / required fields
  test_patient_negative.py Negative-path: malformed input, 404s, empty search results
  test_fhir_client_unit.py Offline unit tests for the client itself (mocked, no network)
fixtures/synthetic_patients.json  Fabricated FHIR Patient payloads used by the API suite
.github/workflows/ci.yml  Sharded UI job + separate API job, both on every push/PR
```

## Tech stack

Playwright · TypeScript · Python · PyTest · `requests` · FHIR R4 · GitHub Actions ·
`http-server`

## Running it locally

### UI suite (Playwright)

```bash
npm install
npx playwright install chromium
npm test                 # runs the full UI suite headless
npm run report            # opens the last HTML report
```

The Playwright config starts the demo app itself (`app/`) on `http://127.0.0.1:4173`
before the suite runs — no separate terminal needed.

### API suite (PyTest against live FHIR)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest tests/api                                # full suite, hits hapi.fhir.org
pytest tests/api/test_fhir_client_unit.py       # offline-only subset, no network needed
```

Point the suite at a different FHIR R4 server (e.g. a local HAPI FHIR Docker instance)
by setting `FHIR_BASE_URL` before running `pytest`.

## CI

Every push and pull request to `main` runs two independent jobs:

- **`ui-tests`** — the Playwright suite split across 2 parallel shards
  (`playwright test --shard=N/2`), each uploading its own HTML report as a build
  artifact.
- **`api-tests`** — the full PyTest suite against the live FHIR sandbox, uploading a
  self-contained HTML report.

## What this is not

This isn't a claim that a real healthcare product's QA suite looks exactly like this —
it's a deliberately compact, fully working example of the patterns (POM, fixtures,
data-driven and negative-path API testing, sharded CI) that scale up to one.
