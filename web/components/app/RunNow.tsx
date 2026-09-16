"use client";

/**
 * Tier one: run a real dispute now, with no wallet. The server pays from an
 * account that exists for this run only; the visitor watches each step arrive
 * from /api/run as it happens, then the committee from /api/run/status.
 */

import { useState } from "react";

import type { Check, Mode } from "@/lib/quote";
import Consensus from "./Consensus";
import { Button, ChecksView, Label, ModePicker, Panel, SettlementNotice, Steps, T, TxLink, short, type StepView } from "./ui";

/* eslint-disable @typescript-eslint/no-explicit-any */

type Latest = { pid: string; citation: string; verdict: string; reason: string } | null;

const GEN = 10n ** 18n;
const gen = (wei: unknown) => {
  try {
    const value = BigInt(String(wei));
    return `${value / GEN}${value % GEN ? `.${String((value % GEN) / 10n ** 16n).padStart(2, "0")}` : ""}`;
  } catch {
    return "?";
  }
};

export default function RunNow({ explorer, amountGen, bondGen }: { explorer: string; amountGen: string; bondGen: string }) {
  const [mode, setMode] = useState<Mode>("stale");
  const [events, setEvents] = useState<Record<string, any>>({});
  const [running, setRunning] = useState(false);
  const [startedAt, setStartedAt] = useState(0);
  const [disputeAt, setDisputeAt] = useState(0);
  const [refusal, setRefusal] = useState<{ message: string; latest?: Latest } | null>(null);

  async function run() {
    setEvents({});
    setRefusal(null);
    setRunning(true);
    setStartedAt(Date.now());
    try {
      const response = await fetch("/api/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mode }) });
      if (!response.ok || !response.body) {
        const body = await response.json().catch(() => ({}));
        setRefusal({ message: body?.message ?? "Studio Next is not answering right now. Nothing was spent.", latest: body?.latest ?? null });
        return;
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let newline = buffer.indexOf("\n");
        while (newline >= 0) {
          const line = buffer.slice(0, newline).trim();
          buffer = buffer.slice(newline + 1);
          newline = buffer.indexOf("\n");
          if (!line) continue;
          const event = JSON.parse(line);
          if (event.step === "dispute_submitted") setDisputeAt(event.at);
          setEvents((previous) => ({ ...previous, [event.step]: event }));
        }
      }
    } catch {
      setRefusal({ message: "The connection to this page's server dropped. If a payment had been submitted, its hash is above and it is on chain; nothing is sent twice." });
    } finally {
      setRunning(false);
    }
  }

  const e = events;
  const failed: string | undefined = e.error?.failed;
  const state = (key: string, doneWhen: boolean, activeWhen: boolean): StepView["state"] =>
    failed === key ? "failed" : doneWhen ? "done" : activeWhen ? "active" : "waiting";

  const checks: Check[] | undefined = e.response?.checks;
  const steps: StepView[] = [
    {
      key: "fund",
      title: "An account for this run",
      state: state("fund", Boolean(e.funded), running && !e.funded),
      summary: e.funded ? `${short(e.account.address)}, ${gen(e.funded.after)} GEN from Studio's faucet` : e.account ? short(e.account.address) : undefined,
      detail: e.error?.failed === "fund" ? e.error.message : "Created on the server for this run and never stored. Funding it from Studio's faucet.",
    },
    {
      key: "promise",
      title: "The seller's promise, read from the escrow",
      state: state("promise", Boolean(e.promise), Boolean(e.funded) && !e.promise),
      summary: e.promise ? `seller ${short(e.promise.seller)}` : undefined,
      detail: e.promise ? (
        <div style={{ display: "grid", gap: "6px" }}>
          <div style={{ font: `400 15px/1.55 ${T.serif}`, color: T.ink }}>{e.promise.promise}</div>
          <div style={{ font: `400 12.5px ${T.sans}`, color: T.muted }}>This sentence is the entire contract between them.</div>
        </div>
      ) : null,
    },
    {
      key: "pay",
      title: `Pay ${amountGen} GEN into the escrow`,
      state: state("pay", Boolean(e.pay_decided), Boolean(e.promise) && !e.pay_decided),
      summary: e.pay_decided ? e.pay_decided.pid : e.pay_submitted ? "submitted" : undefined,
      detail: e.pay_submitted ? <TxLink explorer={explorer} hash={e.pay_submitted.hash} /> : "Estimating the fee deposit and submitting.",
    },
    {
      key: "response",
      title: "The seller's response, and the buyer's checks",
      state: state("response", Boolean(e.response), Boolean(e.pay_decided) && !e.response),
      summary: checks ? `${checks.filter((one) => !one.pass).length} of 3 failed` : undefined,
      detail: e.response ? <ChecksView response={e.response.response} checks={e.response.checks} receivedAt={e.response.receivedAt} /> : null,
    },
    {
      key: "record",
      title: "Freeze the response on chain",
      state: state("record", Boolean(e.record_decided), Boolean(e.response) && !e.record_decided),
      summary: e.record_decided ? "recorded, unsigned" : e.record_submitted ? "submitted" : undefined,
      detail: e.record_submitted ? (
        <div style={{ display: "grid", gap: "6px" }}>
          <TxLink explorer={explorer} hash={e.record_submitted.hash} />
          <span style={{ font: `400 12.5px/1.6 ${T.sans}`, color: T.muted }}>Recorded by the buyer with no seller signature, so the row reads signed: false. The demo seller&apos;s key is not on this server.</span>
        </div>
      ) : null,
    },
    {
      key: "dispute",
      title: `Contest it, with a ${bondGen} GEN bond`,
      state: e.no_dispute ? "skipped" : state("dispute", Boolean(e.dispute_decided), Boolean(e.record_decided) && !e.dispute_decided),
      summary: e.no_dispute ? "nothing to contest" : e.dispute_decided ? "accepted, judgment started" : e.dispute_submitted ? "submitted" : undefined,
      detail: e.no_dispute ? e.no_dispute.message : e.dispute_submitted ? <TxLink explorer={explorer} hash={e.dispute_submitted.hash} /> : null,
    },
  ];

  return (
    <div style={{ display: "grid", gap: "12px", minWidth: 0 }}>
      <Panel>
        <div style={{ display: "grid", gap: "14px" }}>
          <ModePicker mode={mode} onChange={setMode} disabled={running} />
          <SettlementNotice amountGen={amountGen} bondGen={bondGen} />
          <p style={{ margin: 0, font: `400 13px/1.6 ${T.sans}`, color: T.body }}>
            This page&apos;s server pays, so nothing is installed and nothing is signed by you. The transactions, the committee and the verdict are real, and
            every receipt is public.
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", alignItems: "center" }}>
            <Button onClick={run} disabled={running}>
              {running ? "Running" : Object.keys(e).length ? "Replay, a fresh cycle" : "Run a real dispute now"}
            </Button>
          </div>
        </div>
      </Panel>

      {refusal ? (
        <Panel style={{ borderColor: "rgba(217,165,65,0.35)" }}>
          <Label color={T.amber}>Not run</Label>
          <p style={{ margin: "8px 0 0", font: `400 13.5px/1.6 ${T.sans}`, color: T.body }}>{refusal.message}</p>
          {refusal.latest ? (
            <p style={{ margin: "10px 0 0", font: `400 13.5px/1.6 ${T.sans}`, color: T.body }}>
              The most recent real case instead: <a href={`/case/${refusal.latest.citation}`} style={{ color: T.accent, font: `500 13px ${T.mono}` }}>{refusal.latest.citation}</a>, ruled{" "}
              <strong style={{ color: T.ink }}>{refusal.latest.verdict.replace("_", " ")}</strong>. &ldquo;{refusal.latest.reason}&rdquo;
            </p>
          ) : null}
        </Panel>
      ) : null}

      {startedAt ? <Steps steps={steps} /> : null}
      {e.error && e.error.failed !== "fund" ? (
        <p style={{ margin: 0, font: `400 13.5px/1.6 ${T.sans}`, color: T.fail }}>
          {e.error.message}
          {e.error.hash ? (
            <>
              {" "}
              <TxLink explorer={explorer} hash={e.error.hash} />
            </>
          ) : null}
        </p>
      ) : null}
      {e.dispute_decided ? <Consensus pid={e.dispute_decided.pid} adjudicate={e.dispute_decided.adjudicate} explorer={explorer} startedAt={disputeAt || e.dispute_decided.at} /> : null}
    </div>
  );
}
