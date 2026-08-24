"""Pluggable LLM client used by triage_failure.py.

Dependency-injected on purpose (an interface + two implementations),
mirroring healing/selector_suggester.ts on the TypeScript side: the
CI-gating tests must pass with zero external API calls, while the real
integration still exists and is exercised whenever ANTHROPIC_API_KEY is
set in the environment.
"""
from __future__ import annotations

import os
from typing import Protocol


class LLMClient(Protocol):
    def complete(self, prompt: str) -> str:
        """Return a short natural-language completion for `prompt`."""
        ...


class FakeClient:
    """Deterministic stand-in used in tests, and whenever no API key is
    configured. Records every prompt it was asked to complete so tests can
    assert on what would have been sent to a real model."""

    def __init__(self, canned_response: str | None = None):
        self.canned_response = canned_response
        self.prompts_seen: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts_seen.append(prompt)
        if self.canned_response is not None:
            return self.canned_response
        return "(no LLM configured - heuristic summary only)"


class AnthropicClient:
    """Real client, gated entirely behind ANTHROPIC_API_KEY. The SDK is
    imported lazily inside complete() so it is never required just to run
    this repo's tests."""

    def __init__(self, model: str = "claude-3-5-haiku-latest", api_key: str | None = None):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError("AnthropicClient requires ANTHROPIC_API_KEY to be set.")

    def complete(self, prompt: str) -> str:
        import anthropic  # noqa: PLC0415 - deliberately lazy, see class docstring

        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ]
        return "\n".join(parts).strip()


def get_client() -> LLMClient:
    """Factory: a real AnthropicClient if ANTHROPIC_API_KEY is set and the
    SDK is available, a FakeClient otherwise. Never raises - falling back
    to the fake client is always safe for a triage script."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return AnthropicClient()
        except Exception:
            return FakeClient()
    return FakeClient()
