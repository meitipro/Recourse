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
 *
 * Every read names its network. A page reads Studio Next, and lib/networks.ts
 * holds that rule where the browser can see it too; the other deployment the
 * freeze record holds is read only for the record it shows.
 */

import fs from "node:fs";
import path from "node:path";

// Two lines of the SDK, one per consensus version. 2.0.0-rc.1 reads Studio
// Next, which runs consensus v0.6, and fails every read on studionet with
// "Missing or invalid parameters". 1.1.8, the line this site shipped with,
// reads studionet and knows no chain 61997. Each network is read by the line
// that reads it, which was measured, not assumed, on 14 September.
import { createClient as createClientV06 } from "genlayer-js";
import { studioDevnet } from "genlayer-js/chains";
import { createClient as createClientV05 } from "genlayer-js-v1";
import { studionet, testnetAsimov, testnetBradbury } from "genlayer-js-v1/chains";

import { DEFAULT_NETWORK, type NetworkName } from "./networks";
import { loadSnapshot, snapshotEvidence, snapshotRows } from "./snapshot";

export { DEFAULT_NETWORK, settlementMoves } from "./networks";
export type { NetworkName } from "./networks";

/**
 * Studio Next is the SDK's studioDevnet: studio-next.genlayer.com and
 * studio-dev.genlayer.com are one network, chain 61997. The organisers name
 * the first, so its RPC is pinned here rather than taken from the SDK.
 */
const STUDIO_NEXT = {
  ...studioDevnet,
  rpcUrls: { default: { http: ["https://studio-next.genlayer.com/api"] } },
} as typeof studioDevnet;

const CHAINS = {
  studionet,
  "studio-next": STUDIO_NEXT,
  bradbury: testnetBradbury,
  asimov: testnetAsimov,
} satisfies Record<NetworkName, unknown>;

/**
 * One deployment of the pair, from contracts/FROZEN.json, which
 * next.config.mjs traces into the hosted functions. The freeze record is the
 * only source of addresses: a page can never point at a pair the repository
 * does not publish, and no environment variable can move it to another.
 */
export type Deployment = {
  network: NetworkName;
  chainId: number;
  escrow: string;
  dispute: string;
  /** Where the pair's bytes come from: the freeze commit, or the commit the port was deployed from. */
  provenance: string;
};

type FrozenRecord = {
  deployments?: Record<
    string,
    { chain_id: number; escrow: string; dispute: string; frozen_at_commit?: string; deployed_from_commit?: string }
  >;
};

let recorded: Deployment[] | null = null;

/** Every deployment the freeze record holds, in its order. Read once per process. */
export function deployments(): Deployment[] {
  if (recorded) return recorded;
  recorded = [];
  for (const candidate of ["../contracts/FROZEN.json", "../../contracts/FROZEN.json"]) {
    try {
      const file = path.join(process.cwd(), candidate);
      if (!fs.existsSync(file)) continue;
      const record = JSON.parse(fs.readFileSync(file, "utf8")) as FrozenRecord;
      recorded = Object.entries(record.deployments ?? {})
        .filter(([name]) => name in CHAINS)
        .map(([name, entry]) => ({
          network: name as NetworkName,
          chainId: entry.chain_id,
          escrow: entry.escrow,
          dispute: entry.dispute,
          provenance: entry.frozen_at_commit
            ? `frozen at ${entry.frozen_at_commit}`
            : entry.deployed_from_commit
              ? `deployed from ${entry.deployed_from_commit}`
              : "",
        }));
      break;
    } catch {
      // an unreadable record is the same as none: every read then says so by name
    }
  }
  return recorded;
}

export function deploymentOf(network: NetworkName): Deployment | undefined {
  return deployments().find((one) => one.network === network);
}

/**
 * The SDK carries genlayer-explorer.vercel.app for studionet, which answers 503
 * on every request. This one URL is pinned for that reason; everything else
 * comes from the chain object so nothing can drift.
 */
export const EXPLORER: Record<NetworkName, string> = {
  studionet: "https://explorer-studio.genlayer.com",
  "studio-next": "https://explorer-studio-dev.genlayer.com",
  bradbury: "https://explorer-bradbury.genlayer.com",
  asimov: "https://explorer-asimov.genlayer.com",
};

/** The one method the feed calls, which both lines of the SDK provide in the same shape. */
type Reader = {
  readContract: (options: { address: `0x${string}`; functionName: string; args: unknown[] }) => Promise<unknown>;
};

const readers = new Map<NetworkName, Reader>();

function client(network: NetworkName): Reader {
  let reader = readers.get(network);
  if (!reader) {
    reader = (
      network === "studio-next"
        ? createClientV06({ chain: STUDIO_NEXT })
        : createClientV05({ chain: CHAINS[network] as typeof studionet })
    ) as unknown as Reader;
    readers.set(network, reader);
  }
  return reader;
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

async function read<T = unknown>(network: NetworkName, address: string, functionName: string, args: ReadArg[] = []) {
  return withRetry(functionName, () =>
    client(network).readContract({ address: address as `0x${string}`, functionName, args }),
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

function emptyFeed(network: NetworkName, error?: string): FeedData {
  const pair = deploymentOf(network);
  return {
    ok: false,
    source: "live",
    readAt: Date.now(),
    network,
    escrow: pair?.escrow ?? "",
    dispute: pair?.dispute ?? "",
    windowSeconds: 0,
    bondWei: "0",
    totalPayments: 0,
    rows: [],
    ...(error ? { error } : {}),
  };
}

/**
 * The chain, read now. Nothing is invented, and an empty chain produces an
 * empty feed rather than a placeholder row; loadFeed decides whether an empty
 * or failed answer is replaced by the recorded snapshot.
 */
async function readLive(network: NetworkName, limit = 50): Promise<FeedData> {
  const base = emptyFeed(network);
  const pair = deploymentOf(network);
  if (!pair) {
    const offered = deployments().map((one) => one.network).join(" and ");
    return {
      ...base,
      error:
        `The frozen contracts have never been deployed on ${network}; contracts/FROZEN.json has no entry for it. ` +
        `The deployments are ${offered || "missing from this build"}.`,
    };
  }

  try {
    // Three requests for the whole page, whatever the row count.
    //
    // This used to be one request per payment plus one per dispute. Studio
    // allows thirty requests a minute, so a dozen rows rate limited the page on
    // an ordinary load and it rendered an error over an empty table. The
    // contract now answers a whole page in a single view.
    const stats = JSON.parse(await read<string>(network, pair.escrow, "stats"));
    const payments = JSON.parse(await read<string>(network, pair.escrow, "recent_rows", [limit])) as Payment[];
    const verdicts = JSON.parse(
      await read<string>(network, pair.dispute, "recent_verdicts", [limit]),
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
        seller = JSON.parse(await read<string>(network, pair.escrow, "get_seller", [sellerAddress]));
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
export async function loadFeed(limit = 50, network: NetworkName = DEFAULT_NETWORK): Promise<FeedData> {
  const live = await withDeadline(readLive(network, limit), LIVE_DEADLINE_MS, () =>
    emptyFeed(network, `the chain did not answer within ${LIVE_DEADLINE_MS / 1000} seconds`),
  );
  if (live.ok && live.totalPayments > 0) return live;
  const snapshot = loadSnapshot(network);
  if (!snapshot || snapshot.network !== network || snapshot.totals.payments === 0) return live;
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
    network,
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

async function readEvidenceLive(network: NetworkName, pid: string): Promise<Evidence> {
  const pair = deploymentOf(network);
  if (!pair) return { ok: false, source: "live", error: `no contract deployed on ${network}` };
  try {
    const payment = JSON.parse(await read<string>(network, pair.escrow, "get_payment", [pid])) as Payment;
    let decided: Case | undefined;
    if (payment.status === 2 || payment.status === 3) {
      try {
        decided = JSON.parse(await read<string>(network, pair.dispute, "get_case", [pid])) as Case;
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
export async function loadEvidence(pid: string, network: NetworkName = DEFAULT_NETWORK): Promise<Evidence> {
  const live = await withDeadline(readEvidenceLive(network, pid), LIVE_DEADLINE_MS, () => ({
    ok: false,
    source: "live" as const,
    error: `the chain did not answer within ${LIVE_DEADLINE_MS / 1000} seconds`,
  }));
  if (live.ok && live.payment) return live;
  const snapshot = loadSnapshot(network);
  const recorded = snapshot && snapshot.network === network ? snapshotEvidence(snapshot, pid) : null;
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
