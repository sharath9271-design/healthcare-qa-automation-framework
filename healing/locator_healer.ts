import { Page, Locator } from "@playwright/test";
import { SelectorSuggester, NullSuggester } from "./selector_suggester";

/** One way to try to find an element. Strategies are tried in order. */
export interface LocatorStrategy {
  /** Short label used in healing logs/events, e.g. "role+name". */
  name: string;
  resolve: (page: Page) => Locator;
}

/** A named element with an ordered list of strategies to find it. */
export interface ElementDescriptor {
  /** Human-readable identifier used in logs, e.g. "login-button". */
  name: string;
  /** Ordered, most-specific/most-trusted first. */
  strategies: LocatorStrategy[];
}

export interface HealEvent {
  descriptorName: string;
  strategyUsed: string;
  /** True when the FIRST strategy (the "expected" one) did not resolve. */
  healed: boolean;
  timestamp: string;
}

/**
 * Resolves ElementDescriptors against a live page, falling back through
 * each strategy in order until one matches exactly one element.
 *
 * This is the core of the "self-healing" story: a test written against
 * `data-testid="login-btn"` keeps passing even if that attribute is
 * renamed or removed, as long as a later strategy (role, label, text...)
 * still uniquely identifies the element. Every fallback that fires is
 * recorded as a HealEvent so a suite-level report can surface which
 * locators are drifting and should be fixed at the source.
 *
 * The optional `suggester` is a further, LLM-backed tier consulted only
 * after every heuristic strategy has failed — see selector_suggester.ts.
 * It defaults to a no-op, so this class needs no external service or API
 * key to do its job.
 */
export class LocatorHealer {
  readonly events: HealEvent[] = [];

  constructor(
    private readonly page: Page,
    private readonly suggester: SelectorSuggester = new NullSuggester()
  ) {}

  async resolve(descriptor: ElementDescriptor): Promise<Locator> {
    if (descriptor.strategies.length === 0) {
      throw new Error(`LocatorHealer: descriptor "${descriptor.name}" has no strategies.`);
    }

    for (let i = 0; i < descriptor.strategies.length; i++) {
      const strategy = descriptor.strategies[i];
      const locator = strategy.resolve(this.page);
      const count = await locator.count().catch(() => 0);
      if (count === 1) {
        this.record(descriptor.name, strategy.name, i > 0);
        return locator;
      }
    }

    const suggestion = await this.suggester.suggest(this.page, descriptor.name);
    if (suggestion) {
      const locator = this.page.locator(suggestion);
      const count = await locator.count().catch(() => 0);
      if (count === 1) {
        this.record(descriptor.name, `llm-suggested:${suggestion}`, true);
        return locator;
      }
    }

    throw new Error(
      `LocatorHealer: exhausted ${descriptor.strategies.length} strategy(ies)` +
        `${suggestion ? " + a suggester tier" : ""} for "${descriptor.name}"; ` +
        `none resolved to exactly one element.`
    );
  }

  /** Events where a fallback strategy (not the first/expected one) had to be used. */
  get healedEvents(): HealEvent[] {
    return this.events.filter((e) => e.healed);
  }

  private record(descriptorName: string, strategyUsed: string, healed: boolean) {
    this.events.push({
      descriptorName,
      strategyUsed,
      healed,
      timestamp: new Date().toISOString(),
    });
    if (healed) {
      // eslint-disable-next-line no-console
      console.log(`[self-heal] "${descriptorName}" recovered via strategy "${strategyUsed}"`);
    }
  }
}

/**
 * Convenience builder for the common case: a primary `data-testid`
 * strategy plus one or more fallback strategies.
 */
export function byTestIdWithFallback(
  name: string,
  testId: string,
  fallbacks: LocatorStrategy[]
): ElementDescriptor {
  return {
    name,
    strategies: [
      { name: `testId:${testId}`, resolve: (page) => page.getByTestId(testId) },
      ...fallbacks,
    ],
  };
}
