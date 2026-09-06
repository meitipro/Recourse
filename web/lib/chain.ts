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

/** Every argument this feed ever passes is a payment id or a row count. */
type ReadArg = string | number;

async function read<T = unknown>(address: string, functionName: string, args: ReadArg[] = []) {
  return withRetry(functionName, () =>
    client().readContract({ address: address as `0x${string}`, functionName, args }),
  ) as Promise<T>;
}

export type Payment = {
  pid: string;
  buyer: string;
  seller: string;
  amount: string;
  bond: string;
  created_at: number;
  responded_at: number;
  window_ends: number;
  status: number;
  verdict: number;
  /** List rows carry flags rather than the bodies, which only the drawer needs. */
  has_response?: boolean;
  signed?: boolean;
  recorded_by?: string;
  /** Present only on a single row fetched by loadEvidence. */
  request?: string;
  response?: string;
  response_sig?: string;
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
  /** From the contract, so it is right even when the page shows fewer rows. */
  totalPayments: number;
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
    totalPayments: 0,
    rows: [],
  };

  if (!ESCROW || !DISPUTE) {
    return { ...base, error: "No contract addresses are configured. Run scripts/deploy.py." };
  }

  try {
    // Three requests for the whole page, whatever the row count.
    //
    // This used to be one request per payment plus one per dispute. Studio
    // allows thirty requests a minute, so a dozen rows rate limited the page on
    // an ordinary load and it rendered an error over an empty table. The
    // contract now answers a whole page in a single view.
    const stats = JSON.parse(await read<string>(ESCROW, "stats"));
    const payments = JSON.parse(await read<string>(ESCROW, "recent_rows", [limit])) as Payment[];
    const verdicts = JSON.parse(
      await read<string>(DISPUTE, "recent_verdicts", [limit]),
    ) as Case[];

    const byPid = new Map(verdicts.map((entry) => [entry.pid, entry]));
    const rows: Row[] = payments.map((payment) => {
      const decided = byPid.get(payment.pid);
      // A case exists only once the adjudication transaction has written one.
      // Between opening a dispute and the verdict landing there is genuinely
      // nothing to read, which is a state rather than a failure.
      return decided ? { ...payment, case: decided } : { ...payment };
    });

    let seller: FeedData["seller"];
    const sellerAddress = rows[0]?.seller;
    if (sellerAddress) {
      try {
        seller = JSON.parse(await read<string>(ESCROW, "get_seller", [sellerAddress]));
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
      totalPayments: Number(stats.payments),
      rows,
      seller,
    };
  } catch (error) {
    // Say so plainly with the last successful read time. Showing stale data as
    // current would be ironic in this particular project.
    return { ...base, error: String(error).slice(0, 300) };
  }
}

// Citations live in lib/cite.ts, which has no chain imports, so the client
// side feed can format one without pulling this module into the browser.
export { toCitation, toPid } from "./cite";

/**
 * The three frozen strings for one payment, fetched when a row is expanded.
 *
 * Kept out of the list read on purpose: the bodies are the largest fields by
 * far, only one row's worth is ever on screen, and putting them in the list
 * would make every page load carry fifty of them to show none.
 */
export async function loadEvidence(pid: string): Promise<{
  ok: boolean;
  error?: string;
  payment?: Payment;
  case?: Case;
}> {
  if (!ESCROW) return { ok: false, error: "no contract configured" };
  try {
    const payment = JSON.parse(await read<string>(ESCROW, "get_payment", [pid])) as Payment;
    let decided: Case | undefined;
    if (payment.status === 2 || payment.status === 3) {
      try {
        decided = JSON.parse(await read<string>(DISPUTE, "get_case", [pid])) as Case;
      } catch {
        decided = undefined;
      }
    }
    return { ok: true, payment, case: decided };
  } catch (error) {
    return { ok: false, error: String(error).slice(0, 200) };
  }
}
