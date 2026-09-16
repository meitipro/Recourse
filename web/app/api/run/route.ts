import { createAccount, generatePrivateKey } from "genlayer-js";

import { GLOBAL_PER_HOUR, PAY_GEN, PER_IP, demoSeller, ipOf, latestCase, paymentsLastHour, takeIpSlot, where } from "@/lib/app-server";
import { GEN, Refused, fund, readJson, readerFor, returnedOf, send, writerFor } from "@/lib/cycle";
import { MODES, buildBody, checks, serialize, type Mode } from "@/lib/quote";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
/** Funding, pay, record and contest take about forty seconds on Studio Next; the key is gone before judgment runs. */
export const maxDuration = 300;

/* eslint-disable @typescript-eslint/no-explicit-any */

/**
 * Tier one of /app: one real contested cycle on Studio Next, paid by the
 * server, with nothing installed and nothing signed by the visitor.
 *
 * The server creates an account for this run and nowhere else. Its key lives
 * in this function's memory, signs three writes, pay, record_response and
 * open_dispute, and is dropped when the stream ends, before the committee has
 * even started. Nothing is stored and nothing reaches the browser but hashes,
 * addresses and what the chain returned. After open_dispute is decided,
 * everything left to watch is readable without a key, from /api/run/status.
 *
 * The answer is a stream of JSON lines, one per step, sent the moment each
 * step happens: a hash appears when the transaction is submitted, not after
 * it is decided.
 */

const FAUCET_GEN = 100n;
const PAIR = "ETH-USD";

export async function POST(request: Request) {
  const at = where();
  const seller = demoSeller();
  if (!at || !seller) {
    return Response.json({ error: "not_configured", message: "This copy of the site has no Studio Next deployment or demo seller on record." }, { status: 503 });
  }

  let mode: Mode = "stale";
  try {
    const body = await request.json();
    if (MODES.includes(body?.mode)) mode = body.mode;
  } catch {
    // no body is the default run
  }

  const wait = takeIpSlot(ipOf(request));
  if (wait > 0) {
    return Response.json(
      {
        error: "rate_limited",
        message: `This address has run ${PER_IP} cycles in the last hour, the limit, because each one spends real GEN and ten model calls. It can run again in ${Math.ceil(wait / 60)} minutes.`,
        latest: await latestCase(at),
      },
      { status: 429, headers: { "Retry-After": String(wait) } },
    );
  }
  try {
    if ((await paymentsLastHour(at)) >= GLOBAL_PER_HOUR) {
      return Response.json(
        {
          error: "rate_limited",
          message: `The escrow has recorded ${GLOBAL_PER_HOUR} payments in the last hour, the limit for runs from this page, counted on chain across every visitor.`,
          latest: await latestCase(at),
        },
        { status: 429 },
      );
    }
  } catch {
    return Response.json({ error: "rpc", message: "Studio Next is not answering. Nothing was spent." }, { status: 503 });
  }

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      const emit = (event: Record<string, unknown>) =>
        controller.enqueue(encoder.encode(JSON.stringify({ at: Date.now(), ...event }, (_k, v) => (typeof v === "bigint" ? v.toString() : v)) + "\n"));
      let step = "fund";
      try {
        const account = createAccount(generatePrivateKey());
        emit({ step: "account", address: account.address, mode });

        const funded = await fund(at, account.address, FAUCET_GEN * GEN);
        if (funded.after <= funded.before) {
          emit({ step: "error", failed: "fund", message: "Studio's faucet did not credit the run's account. Nothing was spent. Try again in a moment." });
          controller.close();
          return;
        }
        emit({ step: "funded", before: funded.before, after: funded.after });

        const reader = readerFor(at);
        const writer = writerFor(at, { account });
        step = "promise";
        const promise = String((await readJson(at, reader, at.escrow, "get_seller", [seller])).promise);
        const stats = await readJson(at, reader, at.escrow, "stats");
        emit({ step: "promise", seller, promise, escrow: at.escrow, bond: stats.bond_amount, window: stats.window_seconds, amount: PAY_GEN * GEN });

        step = "pay";
        const requestText = `GET /quote?pair=${PAIR}`;
        const paid = await send(writer, at, { address: at.escrow, functionName: "pay", args: [seller, requestText], value: PAY_GEN * GEN }, (hash) =>
          emit({ step: "pay_submitted", hash }),
        );
        let pid = returnedOf(paid.receipt);
        if (typeof pid !== "string") {
          const rows = await readJson(at, reader, at.escrow, "recent_rows", [10]);
          pid = (Array.isArray(rows) ? rows : []).find((row: any) => String(row.buyer).toLowerCase() === account.address.toLowerCase())?.pid;
        }
        if (typeof pid !== "string") throw new Error("the payment was accepted but its id could not be read back");
        emit({ step: "pay_decided", hash: paid.hash, pid });

        step = "response";
        const received = new Date();
        const body = buildBody(PAIR, mode, received);
        const text = serialize(body);
        const results = checks(body, PAIR, promise, received);
        emit({ step: "response", request: requestText, response: text, body, checks: results, receivedAt: received.toISOString() });

        step = "record";
        const recorded = await send(writer, at, { address: at.escrow, functionName: "record_response", args: [pid, text, ""] }, (hash) =>
          emit({ step: "record_submitted", hash }),
        );
        emit({ step: "record_decided", hash: recorded.hash });

        if (results.every((one) => one.pass)) {
          emit({
            step: "no_dispute",
            pid,
            message: "All three checks passed, so there is nothing to contest. The buyer lets the window close and the seller withdraws; no judgment runs and nobody pays anything extra.",
          });
          controller.close();
          return;
        }

        step = "dispute";
        const opened = await send(writer, at, { address: at.escrow, functionName: "open_dispute", args: [pid], value: BigInt(stats.bond_amount) }, (hash) =>
          emit({ step: "dispute_submitted", hash }),
        );
        const triggered = opened.receipt?.triggered_transactions;
        emit({ step: "dispute_decided", hash: opened.hash, pid, adjudicate: Array.isArray(triggered) ? triggered[0] ?? null : null });
      } catch (error: any) {
        if (error instanceof Refused) {
          emit({ step: "error", failed: step, hash: error.hash, outcome: error.outcome, message: `The chain refused ${step}: ${error.message.replace(/\[(EXPECTED|EXTERNAL|TRANSIENT|LLM_ERROR)\]\s*/g, "")}` });
        } else {
          emit({ step: "error", failed: step, message: String(error?.message ?? error).slice(0, 240) });
        }
      }
      controller.close();
    },
  });

  return new Response(stream, {
    headers: { "Content-Type": "application/x-ndjson; charset=utf-8", "Cache-Control": "no-store", "X-Accel-Buffering": "no" },
  });
}
