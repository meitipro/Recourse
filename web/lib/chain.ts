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

import fs from "node:fs";
import path from "node:path";

import { createClient } from "genlayer-js";
import { studionet, testnetAsimov, testnetBradbury } from "genlayer-js/chains";

import { loadSnapshot, snapshotEvidence, snapshotRows } from "./snapshot";

const CHAINS = {
  studionet,
  bradbury: testnetBradbury,
  asimov: testnetAsimov,
} as const;

export type NetworkName = keyof typeof CHAINS;

/**
 * studionet, the only deployment, unless the environment names another network
 * that contracts/FROZEN.json has an entry for. A network without one gets the
 * error in loadFeed rather than a guess.
 */
export const NETWORK: NetworkName =
  (process.env.NEXT_PUBLIC_RECOURSE_NETWORK as NetworkName) || "studionet";

/**
 * The frozen pair's addresses on this network, from contracts/FROZEN.json,
 * which next.config.mjs traces into the hosted function. The environment can
 * still override them, but nothing needs to set them: the freeze record is the
 * source, so a deployment can never point at addresses the repository does
 * not publish.
 */
type FrozenRecord = {
  deployments?: Record<string, { chain_id: number; escrow: string; dispute: string; explorer?: string }>;
};

function readFrozenDeployment(): { escrow: string; dispute: string } {
  for (const candidate of ["../contracts/FROZEN.json", "../../contracts/FROZEN.json"]) {
    try {
      const file = path.join(process.cwd(), candidate);
      if (fs.existsSync(file)) {
        const record = JSON.parse(fs.readFileSync(file, "utf8")) as FrozenRecord;
        const entry = record.deployments?.[NETWORK];
        if (entry) return { escrow: entry.escrow, dispute: entry.dispute };
      }
    } catch {
      // fall through to the environment
    }
  }
  return { escrow: "", dispute: "" };
}

const frozen = readFrozenDeployment();
export const ESCROW = process.env.NEXT_PUBLIC_RECOURSE_ESCROW || frozen.escrow;
export const DISPUTE = process.env.NEXT_PUBLIC_RECOURSE_DISPUTE || frozen.dispute;

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
  /** Where the rows came from. Never left to a reader to infer: the feed prints it. */
  source: "live" | "snapshot";
  /** Snapshot only: when scripts/snapshot.py recorded it, in ms, and why the chain is not being shown. */
  recordedAt?: number;
  why?: string;
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
 * The chain, read now. Nothing is invented, and an empty chain produces an
 * empty feed rather than a placeholder row; loadFeed decides whether an empty
 * or failed answer is replaced by the recorded snapshot.
 */
async function readLive(limit = 50): Promise<FeedData> {
  const base: FeedData = {
    ok: false,
    source: "live",
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
    return {
      ...base,
      error:
        `The frozen contracts have never been deployed on ${NETWORK}; contracts/FROZEN.json has no entry for it. ` +
        "The only deployment is studionet: unset NEXT_PUBLIC_RECOURSE_NETWORK, or set it to studionet.",
    };
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

/** How long a page waits on the chain before the snapshot, if there is one, takes over. */
const LIVE_DEADLINE_MS = 20_000;

function withDeadline<T>(promise: Promise<T>, ms: number, onTimeout: () => T): Promise<T> {
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve(onTimeout()), ms);
    promise.then(
      (value) => {
        clearTimeout(timer);
        resolve(value);
      },
      () => {
        clearTimeout(timer);
        resolve(onTimeout());
      },
    );
  });
}

function emptyFeed(error: string): FeedData {
  return {
    ok: false,
    source: "live",
    readAt: Date.now(),
    network: NETWORK,
    escrow: ESCROW,
    dispute: DISPUTE,
    windowSeconds: 0,
    bondWei: "0",
    totalPayments: 0,
    rows: [],
    error,
  };
}

/**
 * Every number on the page comes from here: the chain first, the recorded
 * snapshot second, and the result says which.
 *
 * The snapshot takes over in exactly two cases: the chain did not answer
 * inside the deadline, or it answered with no payments where the snapshot has
 * some, which is what a reset looks like. Both are named in `why` and printed
 * above the table. A live answer with rows is always what is shown, and a
 * repository without a snapshot behaves as it did before there was one.
 */
export async function loadFeed(limit = 50): Promise<FeedData> {
  const live = await withDeadline(readLive(limit), LIVE_DEADLINE_MS, () =>
    emptyFeed(`the chain did not answer within ${LIVE_DEADLINE_MS / 1000} seconds`),
  );
  if (live.ok && live.totalPayments > 0) return live;
  const snapshot = loadSnapshot();
  if (!snapshot || snapshot.network !== NETWORK || snapshot.totals.payments === 0) return live;
  const why = live.ok
    ? "the chain answered with no payments, which is what a reset looks like"
    : `the chain could not be read: ${live.error ?? "no answer"}`;
  const rows = snapshotRows(snapshot, limit);
  const first = rows[0]?.seller;
  const seller = first && snapshot.sellers[first] ? { ...snapshot.sellers[first], address: first } : undefined;
  return {
    ok: true,
    source: "snapshot",
    recordedAt: snapshot.recorded_at * 1000,
    why,
    readAt: Date.now(),
    network: NETWORK,
    escrow: snapshot.escrow,
    dispute: snapshot.dispute,
    windowSeconds: Number(snapshot.stats?.window_seconds ?? 0),
    bondWei: String(snapshot.stats?.bond_amount ?? "0"),
    totalPayments: snapshot.totals.payments,
    rows,
    seller,
  };
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
export type Evidence = {
  ok: boolean;
  error?: string;
  source: "live" | "snapshot";
  recordedAt?: number;
  why?: string;
  payment?: Payment;
  case?: Case;
};

async function readEvidenceLive(pid: string): Promise<Evidence> {
  if (!ESCROW) return { ok: false, source: "live", error: "no contract configured" };
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
    return { ok: true, source: "live", payment, case: decided };
  } catch (error) {
    return { ok: false, source: "live", error: String(error).slice(0, 200) };
  }
}

/** One payment's evidence: the chain first, the snapshot second, and the answer says which. */
export async function loadEvidence(pid: string): Promise<Evidence> {
  const live = await withDeadline(readEvidenceLive(pid), LIVE_DEADLINE_MS, () => ({
    ok: false,
    source: "live" as const,
    error: `the chain did not answer within ${LIVE_DEADLINE_MS / 1000} seconds`,
  }));
  if (live.ok && live.payment) return live;
  const snapshot = loadSnapshot();
  const recorded = snapshot && snapshot.network === NETWORK ? snapshotEvidence(snapshot, pid) : null;
  if (!snapshot || !recorded) return live;
  return {
    ok: true,
    source: "snapshot",
    recordedAt: snapshot.recorded_at * 1000,
    why: `the chain could not be read: ${live.error ?? "no answer"}`,
    payment: recorded.payment,
    case: recorded.case,
  };
}
