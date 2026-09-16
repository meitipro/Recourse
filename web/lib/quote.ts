/**
 * The demo seller's response and the buyer's three checks, ported line for
 * line from seller/main.py build_body and agent/checks.py and agent/run.py
 * read_promise_bounds, so /app misbehaves and checks exactly the way the demo
 * does. tests/direct/test_design.py holds the ports to their sources.
 *
 * The checks never call a model. The judgment belongs to the committee.
 */

export const MODES = ["correct", "stale", "hollow", "substituted"] as const;
export type Mode = (typeof MODES)[number];

/** seller/main.py BOOK: a fixed book, because the failure shown is freshness and completeness, not the price. */
export const BOOK: Record<string, number> = { "ETH-USD": 4182.1, "BTC-USD": 118400.0, "SOL-USD": 214.8 };

/** seller/main.py STALE_HOURS. */
export const STALE_HOURS = 9;

const stamp = (moment: Date) => moment.toISOString().replace(/\.\d{3}Z$/, "Z");

/** seller/main.py build_body, for a pair the book carries. */
export function buildBody(pair: string, mode: Mode, now: Date = new Date()): Record<string, unknown> {
  if (mode === "hollow") return { pair, results: [], count: 0 };
  if (mode === "substituted") {
    const other = pair !== "BTC-USD" ? "BTC-USD" : "ETH-USD";
    return { pair: other, price: BOOK[other], sources: 3, ts: stamp(now) };
  }
  if (mode === "stale") {
    const old = new Date(now.getTime() - STALE_HOURS * 3600 * 1000);
    return { pair, price: BOOK[pair], sources: 3, ts: stamp(old) };
  }
  return { pair, price: BOOK[pair], sources: 3, ts: stamp(now) };
}

/**
 * The response exactly as shared/canonical.py serializes it and the chain
 * freezes it: sorted keys, no spaces. A price is a Python float there, so a
 * whole one is written 118400.0, which JSON.stringify alone would write 118400.
 */
export function serialize(body: Record<string, unknown>): string {
  const value = (key: string, v: unknown) => (key === "price" && typeof v === "number" && Number.isInteger(v) ? `${v}.0` : JSON.stringify(v));
  return "{" + Object.keys(body).sort().map((key) => `${JSON.stringify(key)}:${value(key, body[key])}`).join(",") + "}";
}

const WORDS: Record<string, number> = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10 };

function number(text: string): number | null {
  const t = text.trim().toLowerCase();
  if (/^\d+$/.test(t)) return Number(t);
  return WORDS[t] ?? null;
}

/** agent/run.py read_promise_bounds: the two numbers the checks need, or bounds that pass everything. */
export function promiseBounds(promise: string): { maxAge: number; minSources: number } {
  let maxAge = 10 ** 9;
  const freshness = /(?:no more than|within|refreshed within)\s+([a-z0-9]+)\s+second/i.exec(promise);
  if (freshness) {
    const parsed = number(freshness[1]);
    if (parsed !== null) maxAge = parsed;
  }
  let minSources = 0;
  const sources = /at least\s+([a-z0-9]+)\s+(?:venue|source)/i.exec(promise);
  if (sources) {
    const parsed = number(sources[1]);
    if (parsed !== null) minSources = parsed;
  }
  return { maxAge, minSources };
}

export type Check = { name: "freshness" | "non empty" | "subject"; pass: boolean; detail: string };

/**
 * The three checks shown side by side, each with its actual numbers. The
 * verdict of agent/checks.py check() is whether all three pass, and it is the
 * same rule: subject, then a usable price, then age against the promise.
 */
export function checks(body: Record<string, unknown>, requested: string, promise: string, received: Date): Check[] {
  const { maxAge } = promiseBounds(promise);
  const pair = typeof body.pair === "string" ? body.pair : "";
  const price = body.price;
  const hasPrice = typeof price === "number" && price !== 0;
  const ts = typeof body.ts === "string" ? Date.parse(body.ts) : NaN;
  const age = Number.isNaN(ts) ? null : Math.floor((received.getTime() - ts) / 1000);
  return [
    {
      name: "freshness",
      pass: age !== null && age <= maxAge,
      detail: age === null ? `no usable timestamp, promise allows ${maxAge}s` : `ts is ${age} s old, promise allows ${maxAge}`,
    },
    {
      name: "non empty",
      pass: hasPrice,
      detail: hasPrice ? "price present" : Array.isArray(body.results) && body.results.length === 0 ? "empty result set, no price" : "no price",
    },
    {
      name: "subject",
      pass: pair === requested,
      detail: pair ? `${requested} requested, ${pair} returned` : `${requested} requested, no pair returned`,
    },
  ];
}
