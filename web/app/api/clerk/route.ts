import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * The clerk: a dry run of the frozen contract's own judge(), for the panel.
 *
 * POST { promise, request, response } in, the judge's answer out. This route
 * holds none of the judgment. It forwards to the one linter service, which
 * loads contracts/dispute.py through the test double and runs judge()
 * unchanged, both presentation orders and all, so what comes back is the
 * deployed code's answer rather than a paraphrase of it.
 *
 * It is one model where the chain uses a committee of five, and no chain at
 * all. Every answer carries recorded_on_chain false and the panel says so in
 * every state. Nothing here is a verdict.
 *
 * Two things a public endpoint needs in front of a model call, the same two
 * the lint route has:
 *
 *   - a rate limit, tighter than the linter's because every call here spends
 *     two model calls where stage 1 of the linter spends none
 *   - no logging. Nothing in this file writes a request body anywhere but to
 *     the linter. Somebody will paste something they should not have, and the
 *     only safe log is the one that does not exist.
 */

/**
 * Where the judge is. Derived from LINTER_URL so one variable configures both,
 * and a deployment cannot end up with a linter and no clerk.
 */
const configured = process.env.LINTER_URL || "";
const production = process.env.NODE_ENV === "production";
const base = configured || (production ? "" : "http://127.0.0.1:4503/lint");
const JUDGE_URL = base ? base.replace(/\/lint$/, "/judge") : "";

const WINDOW_MS = 60_000;
const PER_ADDRESS = 6;
const GLOBAL = 30;
const MAX_STRING = 4000;

const byAddress = new Map<string, number[]>();
let everyone: number[] = [];

function overBudget(address: string): boolean {
  const cutoff = Date.now() - WINDOW_MS;
  everyone = everyone.filter((at) => at > cutoff);
  const mine = (byAddress.get(address) || []).filter((at) => at > cutoff);
  if (everyone.length >= GLOBAL || mine.length >= PER_ADDRESS) {
    byAddress.set(address, mine);
    return true;
  }
  mine.push(Date.now());
  everyone.push(Date.now());
  byAddress.set(address, mine);
  if (byAddress.size > 5000) byAddress.clear();
  return false;
}

export async function POST(request: Request) {
  if (!JUDGE_URL) {
    return NextResponse.json({ error: "the clerk is not configured" }, { status: 503 });
  }
  // Set by the platform in front of this route, and a caller-controlled string
  // anywhere else, which is why the global cap above exists as well.
  const address =
    request.headers.get("x-forwarded-for")?.split(",")[0].trim() ||
    request.headers.get("x-real-ip") ||
    "unknown";
  if (overBudget(address)) {
    return NextResponse.json(
      { error: "too many judgments in the last minute" },
      { status: 429, headers: { "Retry-After": "60" } },
    );
  }

  let body: Record<string, unknown>;
  try {
    body = (await request.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json({ error: "bad json" }, { status: 400 });
  }

  const strings: Record<string, string> = {};
  for (const name of ["promise", "request", "response"]) {
    const value = body?.[name];
    if (typeof value !== "string" || !value.trim()) {
      return NextResponse.json({ error: `${name} must be a non-empty string` }, { status: 400 });
    }
    if (value.length > MAX_STRING) {
      return NextResponse.json(
        { error: `${name} is longer than the contract accepts` },
        { status: 413 },
      );
    }
    strings[name] = value;
  }

  // Optional, and the reason the panel can compare a committed case against
  // its committed answer: the chain writes the timing block, so a case judged
  // against this second's clock instead of its own would fail any freshness
  // bound it carried.
  const timing = body?.timing;
  if (timing !== undefined) {
    if (typeof timing !== "string" || timing.length > MAX_STRING) {
      return NextResponse.json({ error: "timing must be a string" }, { status: 400 });
    }
    strings.timing = timing;
  }

  let upstream: Response;
  try {
    upstream = await fetch(JUDGE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(strings),
      cache: "no-store",
      // Two model calls in sequence, and the chain's own judge takes about a
      // minute. Long, but not forever.
      signal: AbortSignal.timeout(200_000),
    });
  } catch {
    return NextResponse.json({ error: "Could not reach the clerk. Try again." }, { status: 503 });
  }

  let payload: unknown;
  try {
    payload = await upstream.json();
  } catch {
    return NextResponse.json({ error: "Could not reach the clerk. Try again." }, { status: 502 });
  }
  return NextResponse.json(payload, {
    status: upstream.status,
    headers: { "Cache-Control": "no-store" },
  });
}
