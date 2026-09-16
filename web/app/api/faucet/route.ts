import { ipOf, where } from "@/lib/app-server";
import { GEN, fund } from "@/lib/cycle";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * Test GEN for a visitor's own wallet on Studio Next, for tier two of /app.
 *
 * Server side because Studio's RPC does not reliably send CORS headers, and
 * because the amount must not be a number the page can edit.
 *
 * The amount goes as a decimal string and the RPC's answer is ignored, for
 * the reason lib/cycle.ts fund() records: passed a number, sim_fundAccount
 * answers with a hash and credits nothing; passed a string, it answers with an
 * error after the credit has landed. Success is the balance moving.
 *
 * Limits are held in this process's memory, per address and per IP, so they
 * slow a loop on one instance rather than enforce anything across all of them.
 */

const FAUCET_GEN = 100n;
const PER_ADDRESS_MS = 10 * 60 * 1000;
const PER_IP_MS = 60 * 1000;
const lastByAddress = new Map<string, number>();
const lastByIp = new Map<string, number>();

export async function POST(request: Request) {
  const at = where();
  if (!at) return Response.json({ error: "not_configured", message: "This copy of the site has no Studio Next deployment on record." }, { status: 503 });

  const body = await request.json().catch(() => ({}));
  const address = String((body as { address?: unknown })?.address ?? "");
  if (!/^0x[0-9a-fA-F]{40}$/.test(address)) {
    return Response.json({ error: "bad_address", message: "That is not a wallet address." }, { status: 400 });
  }

  const now = Date.now();
  const key = address.toLowerCase();
  const ip = ipOf(request);
  const waitAddress = (lastByAddress.get(key) ?? 0) + PER_ADDRESS_MS - now;
  const waitIp = (lastByIp.get(ip) ?? 0) + PER_IP_MS - now;
  const wait = Math.max(waitAddress, waitIp);
  if (wait > 0) {
    return Response.json(
      { error: "too_soon", message: `The faucet already funded this ${waitAddress > 0 ? "wallet" : "connection"} recently. Try again in ${Math.ceil(wait / 1000)} seconds.` },
      { status: 429, headers: { "Retry-After": String(Math.ceil(wait / 1000)) } },
    );
  }
  lastByAddress.set(key, now);
  lastByIp.set(ip, now);
  if (lastByAddress.size > 5000) lastByAddress.clear();
  if (lastByIp.size > 5000) lastByIp.clear();

  const { before, after } = await fund(at, address, FAUCET_GEN * GEN);
  if (after <= before) {
    lastByAddress.delete(key);
    lastByIp.delete(ip);
    return Response.json(
      { error: "not_funded", message: "Studio's faucet was asked, but the balance has not moved. Nothing was spent. Try again in a moment." },
      { status: 502 },
    );
  }
  return Response.json({ funded: true, before: before.toString(), after: after.toString() });
}
