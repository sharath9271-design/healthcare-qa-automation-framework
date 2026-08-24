"""Parses Playwright's JSON reporter output and writes a short,
human-readable triage report for any failed tests.

Two modes, chosen automatically by llm_client.get_client():
  - No ANTHROPIC_API_KEY set (the default, including this repo's own CI):
    falls back to a heuristic, pattern-matched summary per failure.
  - ANTHROPIC_API_KEY set: asks the configured LLMClient for a short
    root-cause guess and next step per failure.

Either way this always writes an output file, so the CI step that uploads
it as an artifact never has to know which mode ran, and a pull request
comment step can always find something to post.

Usage:
    python scripts/triage_failure.py --input playwright-report/results.json \\
        --output triage-report.md
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from llm_client import FakeClient, LLMClient, get_client


@dataclass
class FailedTest:
    title: str
    file: str
    error_message: str
    project: str = "chromium"


# Ordered (first match wins) heuristic guesses for common Playwright
# failure signatures. This is what keeps triage useful even with zero LLM
# access - it's deliberately simple pattern matching, not a model.
HEURISTICS: list[tuple[str, str]] = [
    (
        "Timeout",
        "Element likely never appeared, or a selector no longer matches the "
        "page. Check for locator/markup drift before assuming a real regression.",
    ),
    (
        "strict mode violation",
        "The locator now matches more than one element - markup likely "
        "changed to add a duplicate. Tighten the selector or scope it further.",
    ),
    (
        "net::ERR",
        "A network request failed at the browser level. Check whether a "
        "dependent service was reachable during this run.",
    ),
    (
        "Element is not visible",
        "The element exists in the DOM but isn't visible. Check for a "
        "missing wait, an overlapping element, or a CSS regression.",
    ),
    (
        "expect(received)",
        "An assertion mismatch. Compare received vs. expected in the error "
        "text below; this is usually a genuine behavior change worth investigating.",
    ),
]


def heuristic_summary(error_message: str) -> str:
    for needle, guess in HEURISTICS:
        if needle.lower() in error_message.lower():
            return guess
    return "No known failure pattern matched; read the full error below."


def _walk_suites(suites: list[dict]) -> list[FailedTest]:
    """Playwright nests suites (one per describe block, recursively) inside
    suites. Walk the whole tree and collect every non-passing result."""
    failed: list[FailedTest] = []
    for suite in suites:
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                project = test.get("projectName", "chromium")
                for result in test.get("results", []):
                    if result.get("status") in ("failed", "timedOut"):
                        errors = result.get("errors") or (
                            [result["error"]] if result.get("error") else []
                        )
                        message = (
                            "\n".join(e.get("message", "") for e in errors if e)
                            or "(no error message captured)"
                        )
                        failed.append(
                            FailedTest(
                                title=spec.get("title", "(untitled test)"),
                                file=spec.get("file", "(unknown file)"),
                                error_message=message,
                                project=project,
                            )
                        )
        failed.extend(_walk_suites(suite.get("suites", [])))
    return failed


def parse_failed_tests(report: dict) -> list[FailedTest]:
    return _walk_suites(report.get("suites", []))


def build_prompt(test: FailedTest) -> str:
    return (
        "You are triaging a failed Playwright end-to-end test in a healthcare "
        "patient-portal QA framework. In 2-3 sentences, give your best guess "
        "at the root cause and one concrete next step for the engineer.\n\n"
        f"Test: {test.title}\n"
        f"File: {test.file}\n"
        f"Error:\n{test.error_message}\n"
    )


def triage(failed_tests: list[FailedTest], client: LLMClient, use_llm: bool) -> str:
    if not failed_tests:
        return "# Failure Triage Report\n\nAll tests passed - nothing to triage.\n"

    mode = "LLM-assisted" if use_llm else "heuristic (no ANTHROPIC_API_KEY set)"
    lines = [
        "# Failure Triage Report",
        "",
        f"{len(failed_tests)} failing test(s). Mode: {mode}.",
        "",
    ]
    for i, test in enumerate(failed_tests, start=1):
        summary = client.complete(build_prompt(test)) if use_llm else heuristic_summary(test.error_message)
        lines += [
            f"## {i}. {test.title}",
            f"- **File:** `{test.file}`",
            f"- **Project:** {test.project}",
            "",
            f"**Triage:** {summary}",
            "",
            "<details><summary>Full error</summary>",
            "",
            "```",
            test.error_message.strip(),
            "```",
            "</details>",
            "",
        ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", default="playwright-report/results.json", help="Playwright JSON reporter output"
    )
    parser.add_argument("--output", default="triage-report.md", help="Where to write the markdown report")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"triage_failure: no report found at {input_path}, nothing to do.", file=sys.stderr)
        Path(args.output).write_text("# Failure Triage Report\n\nNo Playwright report found at the expected path.\n")
        return 0

    report = json.loads(input_path.read_text())
    failed_tests = parse_failed_tests(report)

    client = get_client()
    use_llm = not isinstance(client, FakeClient)

    report_md = triage(failed_tests, client, use_llm)
    Path(args.output).write_text(report_md)

    mode = "llm" if use_llm else "heuristic"
    print(f"triage_failure: wrote {args.output} ({len(failed_tests)} failing test(s), mode={mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
