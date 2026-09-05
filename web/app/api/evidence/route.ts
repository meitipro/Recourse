import { NextResponse } from "next/server";
import { loadEvidence } from "@/lib/chain";

export const dynamic = "force-dynamic";

/**
 * Studio allows about thirty requests a minute across the whole node, and this
 * route spends one or two of them per call. A visitor holding down a row, or
 * anything automated, can therefore exhaust the budget for every other visitor
 * and the page then renders its own "chain could not be read" notice.
 *
 * The budget is a shared resource, so the limit is global rather than per IP.
 * Keying it on an address would be keying it on a header a caller can set, and
 * would not protect the thing actually at risk. The cost is that one noisy
 * client can make others wait, which is visibly a 429 with a reason rather than
 * a page that quietly claims there are no payments.
 */
const WINDOW_MS = 60_000;
const MAX_IN_WINDOW = 20;
let hits: number[] = [];

function overBudget(): boolean {
  const cutoff = Date.now() - WINDOW_MS;
  hits = hits.filter((at) => at > cutoff);
  if (hits.length >= MAX_IN_WINDOW) return true;
  hits.push(Date.now());
  return false;
}

/**
 * Read only, one payment id in, the frozen evidence out.
 *
 * The chain is never reached from the browser: the RPC needs retries and the
 * page should not hand a viewer a way to spend the rate limit thirty times a
 * second. The id is checked against the shape the contract mints so this cannot
 * be turned into a general purpose proxy.
 */
export async function GET(request: Request) {
  const pid = new URL(request.url).searchParams.get("pid") || "";
  if (!/^p-\d{6}$/.test(pid)) {
    return NextResponse.json({ ok: false, error: "bad payment id" }, { status: 400 });
  }
  if (overBudget()) {
    return NextResponse.json(
      { ok: false, error: "too many reads of the chain in the last minute" },
      { status: 429, headers: { "Retry-After": "30" } },
    );
  }
  const result = await loadEvidence(pid);
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}
