import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * The promise linter, for the site panel. POST { promise } in, the linter's
 * shape out, unchanged.
 *
 * This route holds none of the logic. It forwards to the one linter service
 * (linter/service.py, reached over LINTER_URL) so the panel, the bot and the
 * MCP server cannot drift apart. What it does hold is the two things a public
 * endpoint needs in front of a model call:
 *
 *   - a per-address rate limit, generous because stage 1 is free, and a global
 *     one because stage 2 is not
 *   - no logging. Nothing here writes to the console or a file, or forwards
 *     the promise anywhere but the linter. Someone will paste something they
 *     should not have on day one, and the only safe log is the one that does
 *     not exist. tests/direct/test_linter.py asserts this from the source.
 */
const LINTER_URL = process.env.LINTER_URL || "http://127.0.0.1:4503/lint";
const WINDOW_MS = 60_000;
const PER_ADDRESS = 30;
const GLOBAL = 120;
const MAX_PROMISE = 500;

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
  // The forwarded header is set by the platform in front of this route and
  // is a caller-controlled string anywhere else, which is why the global cap
  // above exists as well.
  const address =
    request.headers.get("x-forwarded-for")?.split(",")[0].trim() ||
    request.headers.get("x-real-ip") ||
    "unknown";
  if (overBudget(address)) {
    return NextResponse.json(
      { error: "too many checks in the last minute" },
      { status: 429, headers: { "Retry-After": "30" } },
    );
  }

  let promise: unknown;
  try {
    promise = (await request.json())?.promise;
  } catch {
    return NextResponse.json({ error: "bad json" }, { status: 400 });
  }
  if (typeof promise !== "string" || !promise.trim()) {
    return NextResponse.json({ error: "promise must be a non-empty string" }, { status: 400 });
  }
  if (promise.length > MAX_PROMISE * 4) {
    // The linter reports the real bound as a failed check. This guard only
    // stops something absurd from being forwarded at all.
    return NextResponse.json({ error: "promise is far over the limit" }, { status: 413 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(LINTER_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ promise }),
      cache: "no-store",
      signal: AbortSignal.timeout(200_000),
    });
  } catch {
    return NextResponse.json({ error: "Could not reach the linter. Try again." }, { status: 503 });
  }

  let payload: unknown;
  try {
    payload = await upstream.json();
  } catch {
    return NextResponse.json({ error: "Could not reach the linter. Try again." }, { status: 502 });
  }
  return NextResponse.json(payload, {
    status: upstream.status,
    headers: { "Cache-Control": "no-store" },
  });
}
