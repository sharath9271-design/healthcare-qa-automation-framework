from __future__ import annotations

import json
from pathlib import Path

import pytest

import triage_failure
from llm_client import FakeClient

FIXTURE_PATH = Path(__file__).parent / "testdata" / "sample_playwright_report.json"


@pytest.fixture()
def sample_report() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


def test_parse_failed_tests_skips_passed_and_finds_nested_failures(sample_report):
    failed = triage_failure.parse_failed_tests(sample_report)

    titles = {t.title for t in failed}
    assert titles == {
        "throws a clear error when no strategy resolves",
        "booking with a missing reason is rejected",
    }
    # The passing healing spec must not show up.
    assert "recovers from stale data-testids via label/role fallbacks and logs in" not in titles


def test_parse_failed_tests_captures_error_message_and_file(sample_report):
    failed = triage_failure.parse_failed_tests(sample_report)
    strict_mode = next(t for t in failed if "booking" in t.title)

    assert strict_mode.file == "tests/ui/appointments.spec.ts"
    assert "strict mode violation" in strict_mode.error_message


def test_parse_failed_tests_on_all_passing_report_returns_empty():
    all_passing = {
        "suites": [
            {
                "title": "x.spec.ts",
                "specs": [
                    {
                        "title": "a passing test",
                        "file": "x.spec.ts",
                        "tests": [{"projectName": "chromium", "results": [{"status": "passed"}]}],
                    }
                ],
                "suites": [],
            }
        ]
    }
    assert triage_failure.parse_failed_tests(all_passing) == []


@pytest.mark.parametrize(
    "error_message,expected_fragment",
    [
        ("Timeout 30000ms exceeded while waiting for locator", "never appeared"),
        ("Error: strict mode violation: getByTestId resolved to 2 elements", "matches more than one element"),
        ("net::ERR_CONNECTION_REFUSED at https://hapi.fhir.org", "dependent service"),
        ("Element is not visible", "isn't visible"),
        ("expect(received).toHaveText(expected)", "assertion mismatch"),
        ("some totally novel error nobody has seen before", "No known failure pattern"),
    ],
)
def test_heuristic_summary_matches_known_patterns(error_message, expected_fragment):
    assert expected_fragment in triage_failure.heuristic_summary(error_message)


def test_triage_with_no_failures_reports_all_clear():
    report_md = triage_failure.triage([], FakeClient(), use_llm=False)
    assert "nothing to triage" in report_md.lower()


def test_triage_heuristic_mode_includes_each_failure_and_full_error(sample_report):
    failed = triage_failure.parse_failed_tests(sample_report)
    report_md = triage_failure.triage(failed, FakeClient(), use_llm=False)

    assert "heuristic" in report_md
    for test in failed:
        assert test.title in report_md
        assert test.error_message.strip() in report_md


def test_triage_llm_mode_calls_client_with_a_prompt_per_failure(sample_report):
    failed = triage_failure.parse_failed_tests(sample_report)
    client = FakeClient(canned_response="Likely a real regression; investigate the diff.")

    report_md = triage_failure.triage(failed, client, use_llm=True)

    assert len(client.prompts_seen) == len(failed)
    assert "Likely a real regression; investigate the diff." in report_md
    assert "LLM-assisted" in report_md
    # The prompt sent to the client should carry the actual test context.
    assert any(failed[0].title in prompt for prompt in client.prompts_seen)


def test_main_end_to_end_writes_heuristic_report(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    output_path = tmp_path / "triage-report.md"

    exit_code = triage_failure.main(["--input", str(FIXTURE_PATH), "--output", str(output_path)])

    assert exit_code == 0
    content = output_path.read_text()
    assert "2 failing test(s)" in content
    assert "heuristic" in content


def test_main_writes_placeholder_when_no_report_file_exists(tmp_path):
    missing_input = tmp_path / "does-not-exist.json"
    output_path = tmp_path / "triage-report.md"

    exit_code = triage_failure.main(["--input", str(missing_input), "--output", str(output_path)])

    assert exit_code == 0
    assert "No Playwright report found" in output_path.read_text()
