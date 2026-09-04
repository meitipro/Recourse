import { NextResponse } from "next/server";
import { loadEvidence } from "@/lib/chain";

export const dynamic = "force-dynamic";

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
  const result = await loadEvidence(pid);
  return NextResponse.json(result, { status: result.ok ? 200 : 502 });
}
