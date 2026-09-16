"use client";

/**
 * The live consensus panel. It polls /api/run/status, which reads the
 * adjudicate transaction and the case off the chain, and shows only what came
 * back: the elapsed time on this page's own clock, each status the
 * transaction has actually passed with the chain's timestamp, each validator
 * with the time its run ended and its vote once revealed, and then the
 * verdict. There is no progress bar and no estimate, because nothing here
 * knows how long consensus will take.
 */

import { useEffect, useState } from "react";

import { Label, Panel, T, TxLink, short } from "./ui";

/* eslint-disable @typescript-eslint/no-explicit-any */

const clock = (ms: number) => {
  const s = Math.max(0, Math.floor(ms / 1000));
  return s >= 60 ? `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s` : `${s}s`;
};
const time = (iso: string | null) => (iso ? iso.slice(11, 19) + " UTC" : "");

export default function Consensus({ pid, adjudicate, explorer, startedAt }: { pid: string; adjudicate: string | null; explorer: string; startedAt: number }) {
  const [data, setData] = useState<any>(null);
  const [now, setNow] = useState(Date.now());
  const [gone, setGone] = useState(false);
  // Each status the transaction has been seen in, with the chain's timestamp,
  // kept across polls: a receipt read after the decision can drop the first ones.
  const [seen, setSeen] = useState<Record<string, string | null>>({});
  const done = Boolean(data?.case) && data?.lifecycle?.state && data.lifecycle.state !== "processing";
  const undetermined = data?.lifecycle?.outcome && data.lifecycle.outcome !== "accepted";

  useEffect(() => {
    if (done) return;
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(tick);
  }, [done]);

  useEffect(() => {
    let live = true;
    let failures = 0;
    const poll = async () => {
      while (live) {
        try {
          const response = await fetch(`/api/run/status?pid=${pid}${adjudicate ? `&adjudicate=${adjudicate}` : ""}`, { cache: "no-store" });
          const body = await response.json();
          if (!live) return;
          if (response.ok) {
            failures = 0;
            setGone(false);
            setData(body);
            setSeen((previous) => {
              const next = { ...previous };
              for (const one of body?.statuses ?? []) if (!(one.status in next) || (!next[one.status] && one.at)) next[one.status] = one.at;
              return next;
            });
            if (body?.case && body?.lifecycle?.state && body.lifecycle.state !== "processing") {
              setNow(Date.now());
              return;
            }
          } else if (++failures > 3) setGone(true);
        } catch {
          if (++failures > 3) setGone(true);
        }
        await new Promise((r) => setTimeout(r, 3000));
      }
    };
    poll();
    return () => {
      live = false;
    };
  }, [pid, adjudicate]);

  const ORDER = ["PENDING", "PROPOSING", "COMMITTING", "REVEALING", "ACCEPTED", "FINALIZED"];
  const statuses = ORDER.filter((status) => status in seen).map((status) => ({ status, at: seen[status] }));
  const validators: any[] = data?.validators ?? [];
  const decided = data?.case;

  return (
    <Panel>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: "8px", alignItems: "baseline" }}>
        <Label color={T.accent}>The committee</Label>
        <span style={{ font: `500 13px ${T.mono}`, color: T.ink, fontVariantNumeric: "tabular-nums" }}>{clock(now - startedAt)}</span>
      </div>
      {adjudicate ? (
        <div style={{ marginTop: "8px", font: `400 12px ${T.mono}`, color: T.muted }}>
          adjudicate <TxLink explorer={explorer} hash={adjudicate} />
        </div>
      ) : null}
      {gone ? <p style={{ margin: "10px 0 0", font: `400 13px ${T.sans}`, color: T.amber }}>Studio Next is not answering right now. The dispute is on chain and still being judged; this panel keeps asking.</p> : null}

      <div style={{ marginTop: "14px" }}>
        <Label>Status, as the chain records it</Label>
        <ol style={{ listStyle: "none", margin: "8px 0 0", padding: 0, display: "grid", gap: "4px" }}>
          {statuses.length === 0 ? <li style={{ font: `400 12.5px ${T.mono}`, color: T.muted }}>waiting for the transaction to appear</li> : null}
          {data?.phase && data?.lifecycle?.state === "processing" ? <li style={{ font: `400 12.5px ${T.mono}`, color: T.accent }}>now {data.phase}</li> : null}
          {statuses.map((one) => (
            <li key={one.status} style={{ display: "flex", gap: "12px", font: `400 12.5px ${T.mono}` }}>
              <span style={{ color: T.ink, flex: "0 0 104px" }}>{one.status}</span>
              <span style={{ color: T.muted }}>{time(one.at)}</span>
            </li>
          ))}
        </ol>
      </div>

      <div style={{ marginTop: "16px" }}>
        <Label>How each validator voted</Label>
        <div style={{ marginTop: "8px", display: "grid", gap: "6px" }}>
          {validators.length === 0 ? <div style={{ font: `400 12.5px ${T.mono}`, color: T.muted }}>the committee has not been selected yet</div> : null}
          {validators.map((one) => {
            const tone = one.vote === "agree" ? T.pass : one.vote === "disagree" ? T.fail : one.vote ? T.muted : T.body;
            return (
              <div key={one.address ?? `seat-${one.seat}`} style={{ display: "flex", flexWrap: "wrap", gap: "4px 12px", alignItems: "baseline", borderTop: `1px solid ${T.line}`, paddingTop: "6px" }}>
                <span style={{ font: `500 12.5px ${T.mono}`, color: T.ink, flex: "0 0 104px" }}>{one.address ? short(one.address) : `seat ${one.seat + 1}`}</span>
                <span style={{ font: `400 11px ${T.mono}`, letterSpacing: "0.08em", textTransform: "uppercase", color: T.muted, flex: "0 0 70px" }}>{one.role}</span>
                <span style={{ font: `600 12px ${T.mono}`, textTransform: "uppercase", color: tone, flex: "0 0 74px" }}>{one.vote ?? (one.ranUntil ? "ran" : "running")}</span>
                <span style={{ font: `400 12px ${T.mono}`, color: T.muted, minWidth: 0 }}>
                  {one.model ?? ""}
                  {one.ranUntil ? `, finished ${time(one.ranUntil)}` : ""}
                  {one.seconds ? `, ${one.seconds}s` : ""}
                </span>
              </div>
            );
          })}
        </div>
        {validators.some((one) => one.vote === "idle") ? (
          <p style={{ margin: "8px 0 0", font: `400 12.5px/1.6 ${T.sans}`, color: T.muted }}>
            Idle means the node was cancelled once quorum was reached, so its vote was not needed.
          </p>
        ) : null}
      </div>

      {decided ? (
        <div style={{ marginTop: "18px", borderTop: `1px solid ${T.line}`, paddingTop: "16px", display: "grid", gap: "12px" }}>
          <div>
            <Label>Verdict</Label>
            <div style={{ marginTop: "6px", font: `600 clamp(22px, 5vw, 28px) ${T.mono}`, textTransform: "uppercase", color: decided.verdict === "honored" ? T.pass : decided.verdict === "not_honored" ? T.fail : T.body }}>
              {String(decided.verdict).replace("_", " ")}
            </div>
          </div>
          <blockquote style={{ margin: 0, padding: "0 0 0 12px", borderLeft: `2px solid ${T.accent}`, font: `400 16px/1.55 ${T.serif}`, color: T.ink }}>{decided.reason}</blockquote>
          <div style={{ font: `400 12.5px/1.6 ${T.sans}`, color: T.body }}>
            The judge asked in both presentation orders, and they {decided.orders === "agreed" ? "agreed" : "disagreed, which resolves to unclear"}. The chain stores that outcome, not the two answers separately.
          </div>
          <details>
            <summary style={{ cursor: "pointer", font: `500 12px ${T.mono}`, color: T.accent }}>The three frozen strings it was handed, and the timing the chain wrote</summary>
            <dl style={{ margin: "10px 0 0", display: "grid", gap: "8px" }}>
              {(["promise", "request", "response", "timing"] as const).map((name) => (
                <div key={name}>
                  <dt style={{ font: `500 10px ${T.mono}`, letterSpacing: "0.14em", textTransform: "uppercase", color: T.muted }}>{name}</dt>
                  <dd style={{ margin: "4px 0 0", font: `400 12.5px/1.6 ${T.mono}`, color: T.body, wordBreak: "break-word" }}>{decided[name]}</dd>
                </div>
              ))}
            </dl>
          </details>
          <div style={{ font: `400 13px ${T.sans}`, color: T.body }}>
            {done ? `Dispute to verdict on this page: ${clock(now - startedAt)}. ` : ""}
            <a href={`/case/${decided.citation}`} style={{ color: T.accent, font: `500 13px ${T.mono}` }}>{decided.citation}</a>, the case at its permanent address.
          </div>
          {data?.payment?.status === 2 ? (
            <p style={{ margin: 0, font: `400 13px/1.6 ${T.sans}`, color: T.amber }}>
              The verdict is written. On Studio Next the settlement does not move: the escrow still holds the payment and the bond.
            </p>
          ) : null}
        </div>
      ) : null}

      {undetermined ? (
        <p style={{ margin: "14px 0 0", font: `400 13px/1.6 ${T.sans}`, color: T.amber }}>
          Consensus did not resolve this dispute. After the dispute window either party can call reclaim: the payment goes to the seller and the bond back to the buyer.{" "}
          <a href={`/case/${pid}`} style={{ color: T.accent }}>The case page</a> shows where it stands.
        </p>
      ) : null}
    </Panel>
  );
}
