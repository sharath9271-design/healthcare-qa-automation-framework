# Healthcare QA Automation Framework

A production-shaped test automation framework built around a small, self-contained
"patient portal" app: **Playwright + TypeScript** for UI, **Python + PyTest** for API
testing against a real FHIR R4 server, a **self-healing locator layer** with an optional
LLM-assisted fallback tier, an **AI-assisted CI failure-triage step**, and a **sharded
GitHub Actions** pipeline tying it all together.

It's designed to demonstrate how a healthcare-domain QA automation framework is
actually structured day to day — Page Object Model, data-driven fixtures, negative-path
API coverage, resilient locators, and CI that shards the UI suite across parallel jobs —
rather than a single toy test file.

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
- **Self-healing locators degrade gracefully, in a fixed order.** `healing/locator_healer.ts`
  tries `data-testid` first, then role/label/text fallbacks, and only then an optional
  LLM-suggested selector — so the framework's core resilience needs zero external
  services, and the LLM tier is a bonus, not a dependency.
- **The AI pieces are opt-in everywhere, never a CI dependency.** Both the selector
  suggester and the failure-triage script fall back to deterministic, dependency-free
  behavior (`NullSuggester`, a pattern-matched heuristic summary) unless
  `ANTHROPIC_API_KEY` is set — so this repo's own CI, which sets no such key, proves the
  non-LLM path every run, while the LLM-backed path is real, tested code rather than a
  stub.

## Architecture

```
app/                     Static "patient portal" demo app (HTML/CSS/JS, no backend)
tests/ui/                Playwright + TypeScript UI suite (Page Object Model)
  pages/                 LoginPage, PatientPortalPage
  healing.spec.ts        Proves self-healing recovers from stale data-testids
healing/                 Self-healing locator layer
  locator_healer.ts       Ordered strategy fallback (testId -> role/label/text -> LLM tier)
  selector_suggester.ts   Pluggable "tier 3": NullSuggester (default) / AnthropicSuggester
tests/api/                Python + PyTest API suite against a live FHIR R4 server
  fhir_client.py          Thin requests-based FHIR client (base URL is configurable)
  test_patient_api.py      Positive-path: create / read / search / required fields
  test_patient_negative.py Negative-path: malformed input, 404s, empty search results
  test_fhir_client_unit.py Offline unit tests for the client itself (mocked, no network)
scripts/                 AI-assisted CI failure triage
  llm_client.py           Pluggable LLMClient: FakeClient (tests/no key) / AnthropicClient
  triage_failure.py        Parses Playwright's JSON report -> triage-report.md
  test_triage_failure.py   Tests the parser + both triage modes against a sample report
fixtures/synthetic_patients.json  Fabricated FHIR Patient payloads used by the API suite
.github/workflows/ci.yml  Sharded UI job (+ failure triage) and a separate API job
```

## Tech stack

Playwright · TypeScript · Python · PyTest · `requests` · FHIR R4 · GitHub Actions ·
`http-server` · Anthropic API (optional, self-healing + failure-triage tiers)

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

### AI-assisted self-healing

`tests/ui/healing.spec.ts` is the proof: it deliberately queries three
**wrong/stale `data-testid`s** for the login form and asserts that
`LocatorHealer` still resolves each one — via a label or role/name fallback — and
completes a real login. It's part of `npm test`, and it needs no API key:

```bash
npx playwright test tests/ui/healing.spec.ts
```

The optional third tier (`AnthropicSuggester`) only activates when `ANTHROPIC_API_KEY`
is set; without it, `LocatorHealer` is built with the default `NullSuggester` and simply
raises a clear error once the heuristic tiers are exhausted.

### AI-assisted failure triage

`scripts/triage_failure.py` reads Playwright's JSON reporter output
(`playwright-report/results.json`, produced by the `json` reporter configured in
`playwright.config.ts`) and writes `triage-report.md`: one entry per failing test with a
root-cause guess and the full error. Run it after any local Playwright run:

```bash
npx playwright test                                            # writes results.json
python3 scripts/triage_failure.py --input playwright-report/results.json
```

Without `ANTHROPIC_API_KEY` it falls back to a small pattern-matched heuristic (timeout,
strict-mode violation, network error, assertion mismatch, ...); with it, each failure is
sent to Claude for a short root-cause guess instead. `scripts/test_triage_failure.py`
exercises both modes against a fixed sample report (`scripts/testdata/`), so this logic
is covered by the same `pytest` run as the API suite — no live CI failure required.

## CI

Every push and pull request to `main` runs two independent jobs:

- **`ui-tests`** — the Playwright suite split across 2 parallel shards
  (`playwright test --shard=N/2`), each uploading its own HTML report as a build
  artifact. After each shard, `scripts/triage_failure.py` runs unconditionally and its
  `triage-report.md` is uploaded as an artifact; on a `pull_request` run with at least
  one failure, the report is also posted as a PR comment via `actions/github-script`
  (using the workflow's built-in `GITHUB_TOKEN` — no extra secret needed).
- **`api-tests`** — the full PyTest suite (API tests + the triage-script's own tests)
  against the live FHIR sandbox, uploading a self-contained HTML report.

No job in this repo's CI sets `ANTHROPIC_API_KEY`, so every run exercises — and proves —
the fully offline heuristic paths in both the self-healing layer and the triage script.

## What this is not

This isn't a claim that a real healthcare product's QA suite looks exactly like this —
it's a deliberately compact, fully working example of the patterns (POM, fixtures,
data-driven and negative-path API testing, sharded CI) that scale up to one.
