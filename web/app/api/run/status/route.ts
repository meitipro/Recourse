import { where } from "@/lib/app-server";
import { toCitation } from "@/lib/cite";
import { readJson, readerFor, retried } from "@/lib/cycle";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/* eslint-disable @typescript-eslint/no-explicit-any */

/**
 * What the committee is doing about one dispute, read off the chain each time
 * the panel asks. Nothing here is estimated or animated: every status is the
 * adjudicate transaction's own, every time is its own monitoring timestamp,
 * and a validator's vote appears only once the chain has revealed it.
 *
 * GET ?pid=p-000012&adjudicate=0x...
 */

const STAGES = ["PENDING", "PROPOSING", "COMMITTING", "REVEALING", "ACCEPTED", "FINALIZED"];
const iso = (seconds: unknown) => (typeof seconds === "number" && seconds > 0 ? new Date(seconds * 1000).toISOString() : null);

function modelOf(node: any): { model: string | null; provider: string | null } {
  const config = node?.node_config ?? {};
  return { model: config.primary_model?.model ?? config.model ?? null, provider: config.primary_model?.provider ?? config.provider ?? null };
}

export async function GET(request: Request) {
  const at = where();
  if (!at) return Response.json({ error: "not_configured" }, { status: 503 });
  const url = new URL(request.url);
  const pid = url.searchParams.get("pid") ?? "";
  const hash = url.searchParams.get("adjudicate") ?? "";
  if (!/^p-\d{6}$/.test(pid) || (hash && !/^0x[0-9a-fA-F]{64}$/.test(hash))) {
    return Response.json({ error: "bad_request" }, { status: 400 });
  }

  const reader = readerFor(at);
  const out: Record<string, unknown> = { pid, adjudicate: hash || null };

  try {
    if (hash) {
      const tx: any = await retried("adjudicate", () => reader.getTransaction({ hash }));
      const history = tx?.consensus_history ?? {};
      const round = history.consensus_results?.[history.consensus_results.length - 1] ?? {};
      const monitoring: Record<string, number> = { ...(round.monitoring ?? {}), ...(history.current_monitoring ?? {}) };
      const seen: string[] = [...(round.status_changes ?? []), ...(history.current_status_changes ?? [])];
      out.lifecycle = tx?.lifecycle ?? null;
      out.phase = tx?.lifecycle?.phase ?? null;
      out.execution = tx?.txExecutionResultName ?? null;
      out.statuses = STAGES.filter((stage) => seen.includes(stage) || monitoring[stage]).map((stage) => ({ status: stage, at: iso(monitoring[stage]) }));

      const roster: string[] = tx?.last_round?.round_validators ?? [];
      const leaderIndex = Number(tx?.last_round?.leader_index ?? 0);
      const votes: Record<string, string> = tx?.consensus_data?.votes ?? {};
      const nodes: any[] = [...(tx?.consensus_data?.leader_receipt ?? []), ...(tx?.consensus_data?.validators ?? [])];
      // Before the vote is revealed the receipt carries no roster, but its
      // monitoring already records each committee seat finishing its run.
      // Those seats are shown as they finish, and gain an address and a vote
      // once the chain reveals them.
      const seats = new Set<number>();
      for (const key of Object.keys(monitoring)) {
        const match = /^COMMITTING\.VALIDATOR_(\d+)\.RUN_(START|END)$/.exec(key);
        if (match) seats.add(Number(match[1]));
      }
      if (!roster.length) {
        out.validators = [...seats].sort((a, b) => a - b).map((index) => ({
          address: null,
          seat: index,
          role: "validator",
          model: null,
          provider: null,
          ranUntil: iso(monitoring[`COMMITTING.VALIDATOR_${index}.RUN_END`]),
          vote: null,
          seconds: null,
        }));
      } else out.validators = roster.map((address, index) => {
        const node = nodes.find((one) => String(one?.node_config?.address ?? "").toLowerCase() === address.toLowerCase());
        const vote = Object.entries(votes).find(([key]) => key.toLowerCase() === address.toLowerCase())?.[1] ?? null;
        return {
          address,
          seat: index,
          role: index === leaderIndex ? "leader" : "validator",
          ...modelOf(node),
          ranUntil: iso(monitoring[`COMMITTING.VALIDATOR_${index}.RUN_END`] ?? (index === leaderIndex ? monitoring["PROPOSING.LEADER.RUN_END"] : undefined)),
          vote,
          seconds: typeof node?.processing_time === "number" && node.processing_time > 0 ? Math.round(node.processing_time / 100) / 10 : null,
        };
      });
    }

    const payment = await readJson(at, reader, at.escrow, "get_payment", [pid]);
    out.payment = { status: Number(payment.status), amount: payment.amount, bond: payment.bond, buyer: payment.buyer, seller: payment.seller };
    if (Number(payment.status) >= 2) {
      try {
        const decided = await readJson(at, reader, at.dispute, "get_case", [pid]);
        if (Number(decided.verdict)) {
          const disagreed = String(decided.reason).startsWith("Read one way");
          out.case = {
            verdict: decided.verdict_name,
            reason: decided.reason,
            promise: decided.promise,
            request: decided.request,
            response: decided.response,
            timing: decided.timing,
            decidedAt: Number(decided.decided_at),
            citation: toCitation(pid, Number(decided.decided_at)),
            // dispute.py judge() asks in both presentation orders and, when they
            // differ, writes unclear with a reason that begins "Read one way".
            orders: disagreed ? "disagreed" : "agreed",
          };
        }
      } catch {
        // no case row yet: adjudicate has not written one
      }
    }
    return Response.json(out, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json({ error: "rpc", message: "Studio Next is not answering right now." }, { status: 503 });
  }
}
