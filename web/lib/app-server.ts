/**
 * Server side facts for /app: where the pair lives, who the demo seller is,
 * what the latest public case is, and the limits a run is held to.
 *
 * Every value comes from contracts/FROZEN.json, the committed Studio Next
 * snapshot or the chain. Nothing here is a second copy of a network, an
 * address, a bond or a window.
 */

import { DEFAULT_NETWORK, deploymentOf } from "./chain";
import { toCitation } from "./cite";
import type { Where } from "./cycle";
import { readJson, readerFor } from "./cycle";
import { loadSnapshot } from "./snapshot";

/* eslint-disable @typescript-eslint/no-explicit-any */

export function where(): Where | null {
  const pair = deploymentOf(DEFAULT_NETWORK);
  if (!pair) return null;
  return { chainId: pair.chainId, rpc: pair.rpc, explorer: pair.explorer, escrow: pair.escrow, dispute: pair.dispute };
}

/**
 * The demo seller: the seller the committed snapshot records the most
 * payments against, which is the one scripts/prepare.py registered with the
 * spot price promise. Its promise is read from the escrow at run time, never
 * from here.
 */
export function demoSeller(): string | null {
  const snapshot = loadSnapshot(DEFAULT_NETWORK);
  const sellers = Object.entries(snapshot?.sellers ?? {}).sort((a, b) => b[1].total - a[1].total);
  return sellers[0]?.[0] ?? null;
}

/** The most recent decided case on chain, shown to a visitor who cannot run one right now. */
export async function latestCase(at: Where): Promise<{ pid: string; citation: string; verdict: string; reason: string } | null> {
  try {
    const verdicts = await readJson(at, readerFor(at), at.dispute, "recent_verdicts", [1]);
    const one = Array.isArray(verdicts) ? verdicts[0] : null;
    if (!one) return null;
    return { pid: one.pid, citation: toCitation(one.pid, Number(one.decided_at)), verdict: one.verdict_name, reason: one.reason };
  } catch {
    return null;
  }
}

/**
 * Two limits on a run, because every run spends real GEN from Studio's faucet
 * and ten model calls across a committee.
 *
 * PER_IP is held in this process's memory, so it is per serverless instance:
 * it stops a loop, not a determined visitor. GLOBAL is read off the chain
 * itself, the payments the escrow recorded in the last hour, so it holds
 * across every instance at once and cannot be reset by a cold start.
 */
/** What a demo run pays, in whole GEN: the buyer agent's own default, agent/run.py --amount. */
export const PAY_GEN = 4n;

export const PER_IP = 3;
export const PER_IP_WINDOW_MS = 60 * 60 * 1000;
export const GLOBAL_PER_HOUR = 30;

const byIp = new Map<string, number[]>();

export function ipOf(request: Request): string {
  return request.headers.get("x-forwarded-for")?.split(",")[0].trim() || request.headers.get("x-real-ip") || "unknown";
}

/** Seconds until this address may run again, or 0 when it may run now. Records the run when it may. */
export function takeIpSlot(ip: string, now = Date.now()): number {
  const recent = (byIp.get(ip) ?? []).filter((at) => at > now - PER_IP_WINDOW_MS);
  if (recent.length >= PER_IP) {
    byIp.set(ip, recent);
    return Math.ceil((recent[0] + PER_IP_WINDOW_MS - now) / 1000);
  }
  recent.push(now);
  byIp.set(ip, recent);
  if (byIp.size > 5000) byIp.clear();
  return 0;
}

/** How many payments the escrow recorded in the last hour, read from the chain. */
export async function paymentsLastHour(at: Where): Promise<number> {
  const rows = await readJson(at, readerFor(at), at.escrow, "recent_rows", [GLOBAL_PER_HOUR]);
  const since = Math.floor(Date.now() / 1000) - 3600;
  return (Array.isArray(rows) ? rows : []).filter((row: any) => Number(row.created_at) > since).length;
}
