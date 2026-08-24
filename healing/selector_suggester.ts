import { Page } from "@playwright/test";

/**
 * Pluggable "tier 3" locator suggester.
 *
 * The `LocatorHealer` (see locator_healer.ts) already recovers from most
 * real-world breakage using ordinary heuristic fallbacks: role+name, label
 * text, visible text. Those tiers need zero external services and are what
 * actually keeps healing.spec.ts green in CI.
 *
 * This interface is the *optional* next tier: when every heuristic fails,
 * a suggester gets one last look at the page and can propose a fresh
 * selector. Returning `null` means "no suggestion" and is treated exactly
 * like this tier not being wired up at all — so the framework's core
 * self-healing works with zero external dependencies, and nothing in CI
 * ever depends on a suggester returning a real answer.
 */
export interface SelectorSuggester {
  suggest(page: Page, descriptorName: string): Promise<string | null>;
}

/** Default suggester: always declines. Used whenever no LLM is configured. */
export class NullSuggester implements SelectorSuggester {
  async suggest(_page: Page, _descriptorName: string): Promise<string | null> {
    return null;
  }
}

/**
 * Real LLM-backed suggester. Only makes a network call when
 * `ANTHROPIC_API_KEY` is set in the environment; otherwise it behaves
 * identically to `NullSuggester`. This is what makes the "AI-assisted"
 * claim real rather than aspirational, while keeping it fully opt-in:
 * no test in this repo requires an API key to pass.
 *
 * Deliberately simple (single prompt, no retries, no schema validation
 * beyond "did we get a non-empty string back") — this demonstrates the
 * integration point, not a production-grade resilience system.
 */
export class AnthropicSuggester implements SelectorSuggester {
  constructor(private readonly model: string = "claude-3-5-haiku-latest") {}

  async suggest(page: Page, descriptorName: string): Promise<string | null> {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) return null;

    let html: string;
    try {
      html = await page.content();
    } catch {
      return null;
    }
    const trimmed = html.length > 20_000 ? html.slice(0, 20_000) : html;

    try {
      const response = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-api-key": apiKey,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({
          model: this.model,
          max_tokens: 200,
          messages: [
            {
              role: "user",
              content:
                `A Playwright UI test is looking for the element described as ` +
                `"${descriptorName}", but every known selector for it has stopped ` +
                `matching — the page markup likely changed. Given the HTML below, ` +
                `reply with ONLY a single CSS selector that would match that exact ` +
                `element today. No explanation, no markdown, just the selector.\n\n` +
                `HTML:\n${trimmed}`,
            },
          ],
        }),
      });
      if (!response.ok) return null;

      const data = (await response.json()) as {
        content?: { type: string; text?: string }[];
      };
      const text = data.content?.find((block) => block.type === "text")?.text?.trim();
      return text && text.length > 0 ? text : null;
    } catch {
      // Network error, timeout, malformed response, etc. — treat exactly
      // like "no suggestion," never let the suggester crash the test run.
      return null;
    }
  }
}
