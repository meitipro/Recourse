/**
 * Reads the chain for the feed. Server side only.
 *
 * Read only by construction: the client is created without an account, so it
 * cannot submit anything even by mistake. That is the correct posture for a
 * public page and it is worth doing structurally rather than by discipline.
 *
 * genlayer-js builds its transport with retryCount 0, so a single dropped
 * connection fails the whole call. Against Studio that is the difference
 * between working and not, so every read here retries.
 */

import { createClient } from "genlayer-js";
import { studionet, testnetAsimov, testnetBradbury } from "genlayer-js/chains";

const CHAINS = {
  studionet,
  bradbury: testnetBradbury,
  asimov: testnetAsimov,
} as const;

export type NetworkName = keyof typeof CHAINS;

export const NETWORK: NetworkName =
  (process.env.NEXT_PUBLIC_RECOURSE_NETWORK as NetworkName) || "studionet";

export const ESCROW = process.env.NEXT_PUBLIC_RECOURSE_ESCROW || "";
export const DISPUTE = process.env.NEXT_PUBLIC_RECOURSE_DISPUTE || "";

/**
 * The SDK carries genlayer-explorer.vercel.app for studionet, which answers 503
 * on every request. This one URL is pinned for that reason; everything else
 * comes from the chain object so nothing can drift.
 */
export const EXPLORER: Record<NetworkName, string> = {
  studionet: "https://explorer-studio.genlayer.com",
  bradbury: "https://explorer-bradbury.genlayer.com",
  asimov: "https://explorer-asimov.genlayer.com",
};

let cached: ReturnType<typeof createClient> | null = null;

function client() {
  if (!cached) {
    cached = createClient({ chain: CHAINS[NETWORK] });
  }
  return cached;
}

async function withRetry<T>(what: string, fn: () => Promise<T>, attempts = 6): Promise<T> {
  let last: unknown;
  for (let i = 0; i < attempts; i += 1) {
    try {
      return await fn();
    } catch (error) {
      last = error;
      if (i < attempts - 1) {
        await new Promise((resolve) => setTimeout(resolve, Math.min(400 * 2 ** i, 4000)));
      }
    }
  }
  throw new Error(`${what} failed after ${attempts} attempts: ${String(last).slice(0, 160)}`);
}

async function read<T = unknown>(address: string, functionName: string, args: unknown[] = []) {
  return withRetry(functionName, () =>
    client().readContract({ address: address as `0x${string}`, functionName, args }),
  ) as Promise<T>;
}

export type Payment = {
  pid: string;
  buyer: string;
  seller: string;
  amount: string;
  request: string;
  response: string;
  response_sig: string;
  recorded_by: string;
  created_at: number;
  responded_at: number;
  window_ends: number;
  bond: string;
  status: number;
  verdict: number;
};

export type Case = {
  pid: string;
  promise: string;
  request: string;
  response: string;
  timing: string;
  reason: string;
  verdict: number;
  verdict_name: string;
  opened_at: number;
  decided_at: number;
};

export type Row = Payment & { case?: Case };

export type FeedData = {
  ok: boolean;
  error?: string;
  readAt: number;
  network: NetworkName;
  escrow: string;
  dispute: string;
  windowSeconds: number;
  bondWei: string;
  rows: Row[];
  seller?: {
    address: string;
    promise: string;
    total: number;
    upheld: number;
    live: number;
    judgeable: boolean;
  };
};

/**
 * Every number on the page comes from here. Nothing is invented, and an empty
 * chain produces an empty feed rather than a placeholder row.
 */
export async function loadFeed(limit = 50): Promise<FeedData> {
  const base: FeedData = {
    ok: false,
    readAt: Date.now(),
    network: NETWORK,
    escrow: ESCROW,
    dispute: DISPUTE,
    windowSeconds: 0,
    bondWei: "0",
    rows: [],
  };

  if (!ESCROW || !DISPUTE) {
    return { ...base, error: "No contract addresses are configured. Run scripts/deploy.py." };
  }

  try {
    const stats = JSON.parse(await read<string>(ESCROW, "stats"));
    const ids = await read<string[]>(ESCROW, "recent", [limit]);

    const rows: Row[] = [];
    for (const pid of ids) {
      const payment = JSON.parse(await read<string>(ESCROW, "get_payment", [pid])) as Payment;
      const row: Row = { ...payment };
      // A case exists only once a dispute was opened. Reading one for every
      // payment would spend a request per row to learn nothing.
      if (payment.status === 2 || payment.status === 3) {
        try {
          row.case = JSON.parse(await read<string>(DISPUTE, "get_case", [pid])) as Case;
        } catch {
          // The case row is written by the adjudication transaction, so between
          // opening a dispute and the verdict landing there is genuinely nothing
          // to read. That is a state, not a failure.
        }
      }
      rows.push(row);
    }

    let seller: FeedData["seller"];
    const sellerAddress = rows[0]?.seller;
    if (sellerAddress) {
      try {
        const parsed = JSON.parse(await read<string>(ESCROW, "get_seller", [sellerAddress]));
        seller = parsed;
      } catch {
        seller = undefined;
      }
    }

    return {
      ...base,
      ok: true,
      readAt: Date.now(),
      windowSeconds: Number(stats.window_seconds),
      bondWei: String(stats.bond_amount),
      rows,
      seller,
    };
  } catch (error) {
    // Say so plainly with the last successful read time. Showing stale data as
    // current would be ironic in this particular project.
    return { ...base, error: String(error).slice(0, 300) };
  }
}
