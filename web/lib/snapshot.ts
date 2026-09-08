/**
 * The recorded snapshot: what the chain held about the frozen contracts when
 * scripts/snapshot.py last ran. Server side only.
 *
 * studionet's persistence is temporary. A judge who opens the feed after a
 * reset would otherwise find an empty table or a dash that never resolves,
 * and both would misrepresent a deployment that ran. The chain is always
 * read first; this file is read second, and whatever is built from it says
 * so, with the time it was recorded. Nothing here ever looks live.
 *
 * evidence/snapshot.json is traced into the hosted function by
 * next.config.mjs, the same way the evaluation results are.
 */

import fs from "node:fs";
import path from "node:path";

import type { Case, Payment, Row } from "./chain";

export type SnapshotPayment = Payment & {
  status_name: string;
  verdict_name: string;
  case?: Case;
  transactions: Record<string, string | string[] | null>;
};

export type Snapshot = {
  recorded_at: number;
  recorded_at_iso: string;
  note: string;
  network: string;
  chain_id: number;
  escrow: string;
  dispute: string;
  totals: {
    payments: number;
    disputes_opened: number;
    decided: number;
    upheld: number;
    upheld_rate: number | null;
    unjudgeable: number;
    unjudgeable_rate: number | null;
    median_pay_to_dispute_seconds: number | null;
    transactions: number;
    refusals: number;
  };
  stats?: { window_seconds: number | string; bond_amount: string; payments: number };
  sellers: Record<string, { promise: string; total: number; upheld: number; live: number; judgeable: boolean }>;
  payments: SnapshotPayment[];
  cases: Case[];
};

let cached: Snapshot | null | undefined;

/** The snapshot, or null when the repository has none. Read once per process. */
export function loadSnapshot(): Snapshot | null {
  if (cached !== undefined) return cached;
  cached = null;
  for (const candidate of ["../evidence/snapshot.json", "../../evidence/snapshot.json"]) {
    try {
      const file = path.join(process.cwd(), candidate);
      if (fs.existsSync(file)) {
        cached = JSON.parse(fs.readFileSync(file, "utf8")) as Snapshot;
        break;
      }
    } catch {
      // an unreadable snapshot is the same as none: the live answer stands
    }
  }
  return cached;
}

/** The feed's rows from the snapshot, newest first, the way the contract's recent_rows answers. */
export function snapshotRows(snapshot: Snapshot, limit: number): Row[] {
  return [...snapshot.payments]
    .sort((a, b) => (a.pid < b.pid ? 1 : a.pid > b.pid ? -1 : 0))
    .slice(0, limit)
    .map((payment) => {
      const { status_name: _s, verdict_name: _v, transactions: _t, case: decided, ...row } = payment;
      return decided ? { ...row, case: decided } : { ...row };
    });
}

/** One payment and its case from the snapshot, for the drawer and the case page. */
export function snapshotEvidence(snapshot: Snapshot, pid: string): { payment: Payment; case?: Case } | null {
  const found = snapshot.payments.find((payment) => payment.pid === pid);
  if (!found) return null;
  const { status_name: _s, verdict_name: _v, transactions: _t, case: decided, ...payment } = found;
  return decided ? { payment, case: decided } : { payment };
}

/** The one line every consumer prints when it is showing the snapshot rather than the chain. */
export function snapshotLabel(snapshot: Snapshot): string {
  return `recorded ${snapshot.recorded_at_iso.replace("T", " ").replace("Z", " UTC")} on ${snapshot.network}, a temporary testnet`;
}
