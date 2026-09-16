/**
 * The three frozen strings a case was judged on, for the feed's drawer.
 *
 * The feed reads a page of cases in one call, and that call carries each
 * case's verdict and reason but not the strings, which are the long part. The
 * drawer promises "the three frozen strings the validators were given", so it
 * asks here when a contested row is opened: one case, read from the chain the
 * way the case page reads it, on the network the page is reading, and nothing
 * else about the request is kept.
 */

import { DEFAULT_NETWORK, loadEvidence, toPid } from "@/lib/chain";

export const dynamic = "force-dynamic";

export async function GET(request: Request, { params }: { params: Promise<{ pid: string }> }) {
  const { pid: raw } = await params;
  let pid: string;
  try {
    pid = toPid(decodeURIComponent(raw));
  } catch {
    return Response.json({ error: "not a payment id or citation" }, { status: 400 });
  }
  // An older link may still carry a network in the address. It is ignored: the
  // drawer reads the one network the page does.
  const network = DEFAULT_NETWORK;
  const evidence = await loadEvidence(pid, network);
  if (!evidence.ok || !evidence.case) {
    return Response.json({ error: evidence.error ?? "no case for this payment" }, { status: 404 });
  }
  const { promise, request: asked, response, timing } = evidence.case;
  return Response.json({ pid, network, source: evidence.source, promise, request: asked, response, timing });
}
