/**
 * The page's sections, ported from the Claude Design canvas.
 *
 * Server rendered, because everything here comes from a committed file: the
 * freeze record, each network's evaluation result files. Three statements the canvas
 * carried were corrected against the repository before this shipped, and each
 * correction is noted where it happened. The rest is the design's own markup,
 * the second export's since 2026-09-15, carried in by hand.
 */

import { Fragment } from "react";

import { capital, list, spell } from "@/lib/words";

type Row = { id: string; correct: boolean; stable: boolean; expected: string; observed: string[] };

type Results = {
  accuracy: number;
  stability: number;
  n: number;
  runs: number;
  unclear: number;
  measured_at: number;
  rows: Row[];
};

/** One network's column: its first set and its held out set, each as measured there. */
export type EvaluationColumn = { network: string; results: Results; heldOut: Results };

export function GapSection() {
  return (
    <>
    <section id="gap" style={{ borderTop: "1px solid #151A25", padding: "clamp(40px, 4.6vw, 72px) clamp(20px, 5vw, 100px)", display: "flex", flexWrap: "wrap", alignItems: "flex-start", gap: "clamp(20px, 3vw, 56px)" } as React.CSSProperties}> <div style={{ flex: "0 0 clamp(146px, 14vw, 224px)", minWidth: "0", position: "sticky", top: "92px" } as React.CSSProperties}> <div style={{ font: "500 clamp(26px, 2.8vw, 40px)/1 'Geist Mono', ui-monospace, monospace", letterSpacing: "-0.02em", color: "#7C8798" } as React.CSSProperties}>02</div> <div style={{ marginTop: "12px", font: "500 10.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.16em", textTransform: "uppercase", color: "#22D3EE" } as React.CSSProperties}>The gap</div> <div style={{ marginTop: "14px", height: "1px", background: "#1B2130" } as React.CSSProperties}> </div> </div> <div style={{ flex: "1 1 min(620px, 100%)", minWidth: "0" } as React.CSSProperties}> <div style={{ height: "1px", background: "#1B2130" } as React.CSSProperties}> </div> <h2 style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: "600", fontSize: "clamp(28px, 4vw, 40px)", lineHeight: "1.1", letterSpacing: "-0.025em", marginTop: "14px", maxWidth: "30ch" } as React.CSSProperties}>Three layers shipped. The fourth <em style={{ fontStyle: "italic", color: "#EEF3F8" } as React.CSSProperties}>was never built</em>.</h2> <p style={{ marginTop: "16px", fontSize: "15.5px", lineHeight: "1.65", color: "#AEB9C8", maxWidth: "74ch" } as React.CSSProperties}>x402 settles machine payments in milliseconds and finally. Once settlement confirms there is no chargeback path, no dispute window and no pull back. That is by design: a push payment with no reversal is precisely what lets machines transact without accounts or credit relationships.</p> <div style={{ display: "grid", gap: "10px", marginTop: "clamp(28px, 4vw, 40px)" } as React.CSSProperties}> <div style={{ display: "grid", gridTemplateColumns: "34px minmax(0, 1fr) auto", gap: "clamp(12px, 2vw, 22px)", alignItems: "center", border: "1px solid #1B2130", borderRadius: "0", background: "#0E1119", padding: "18px clamp(14px, 2vw, 22px)", transition: "border-color 0.2s ease" } as React.CSSProperties} className="rc-hover-6"> <span style={{ font: "500 12px 'Geist Mono', ui-monospace, monospace", color: "#7C8798" } as React.CSSProperties}>01</span> <div> <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "10px" } as React.CSSProperties}> <span style={{ font: "500 12px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8" } as React.CSSProperties}>Payments</span> <span style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.12em", textTransform: "uppercase", color: "#7C8798", borderLeft: "1px solid #263048", paddingLeft: "10px", whiteSpace: "nowrap" } as React.CSSProperties}>Linux Foundation</span> </div> <p style={{ marginTop: "7px", fontSize: "14px", lineHeight: "1.6", color: "#AEB9C8", maxWidth: "78ch" } as React.CSSProperties}>Settlement in milliseconds. Governance moved under the Linux Foundation, with Visa, Mastercard, American Express, Stripe and Google among its members.</p> </div> <span style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798", border: "1px solid #1B2130", borderRadius: "0", padding: "5px 11px", whiteSpace: "nowrap" } as React.CSSProperties}>Shipped</span> </div> <div style={{ display: "grid", gridTemplateColumns: "34px minmax(0, 1fr) auto", gap: "clamp(12px, 2vw, 22px)", alignItems: "center", border: "1px solid #1B2130", borderRadius: "0", background: "#0E1119", padding: "18px clamp(14px, 2vw, 22px)", transition: "border-color 0.2s ease" } as React.CSSProperties} className="rc-hover-6"> <span style={{ font: "500 12px 'Geist Mono', ui-monospace, monospace", color: "#7C8798" } as React.CSSProperties}>02</span> <div> <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "10px" } as React.CSSProperties}> <span style={{ font: "500 12px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8" } as React.CSSProperties}>Identity</span> <span style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.12em", textTransform: "uppercase", color: "#7C8798", borderLeft: "1px solid #263048", paddingLeft: "10px", whiteSpace: "nowrap" } as React.CSSProperties}>Mastercard, OpenAI</span> </div> <p style={{ marginTop: "7px", fontSize: "14px", lineHeight: "1.6", color: "#AEB9C8", maxWidth: "78ch" } as React.CSSProperties}>Agent tokens and delegated credentials. Mastercard's preserve dispute rights. OpenAI's preserve dispute rights.</p> </div> <span style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798", border: "1px solid #1B2130", borderRadius: "0", padding: "5px 11px", whiteSpace: "nowrap" } as React.CSSProperties}>Shipped</span> </div> <div style={{ display: "grid", gridTemplateColumns: "34px minmax(0, 1fr) auto", gap: "clamp(12px, 2vw, 22px)", alignItems: "center", border: "1px solid #1B2130", borderRadius: "0", background: "#0E1119", padding: "18px clamp(14px, 2vw, 22px)", transition: "border-color 0.2s ease" } as React.CSSProperties} className="rc-hover-6"> <span style={{ font: "500 12px 'Geist Mono', ui-monospace, monospace", color: "#7C8798" } as React.CSSProperties}>03</span> <div> <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "10px" } as React.CSSProperties}> <span style={{ font: "500 12px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8" } as React.CSSProperties}>Interoperability</span> <span style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.12em", textTransform: "uppercase", color: "#7C8798", borderLeft: "1px solid #263048", paddingLeft: "10px", whiteSpace: "nowrap" } as React.CSSProperties}>x402, across chains</span> </div> <p style={{ marginTop: "7px", fontSize: "14px", lineHeight: "1.6", color: "#AEB9C8", maxWidth: "78ch" } as React.CSSProperties}>One rail across chains and providers. Sixty nine thousand active agents and one hundred and sixty five million x402 transactions reported by April 2026.</p> </div> <span style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798", border: "1px solid #1B2130", borderRadius: "0", padding: "5px 11px", whiteSpace: "nowrap" } as React.CSSProperties}>Shipped</span> </div> <div style={{ display: "grid", gridTemplateColumns: "34px minmax(0, 1fr) auto", gap: "clamp(12px, 2vw, 22px)", alignItems: "center", border: "1px dashed rgba(34,211,238,0.55)", borderRadius: "0", background: "transparent", padding: "18px clamp(14px, 2vw, 22px)" } as React.CSSProperties}> <span style={{ font: "500 12px 'Geist Mono', ui-monospace, monospace", color: "#22D3EE" } as React.CSSProperties}>04</span> <div> <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "10px" } as React.CSSProperties}> <span style={{ font: "500 12px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#22D3EE" } as React.CSSProperties}>Dispute right</span> <span style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.12em", textTransform: "uppercase", color: "#22D3EE", borderLeft: "1px solid rgba(34,211,238,0.4)", paddingLeft: "10px", whiteSpace: "nowrap" } as React.CSSProperties}>no owner</span> </div> <p style={{ marginTop: "7px", fontSize: "14px", lineHeight: "1.6", color: "#AEB9C8", maxWidth: "78ch" } as React.CSSProperties}>No chargeback path. No dispute window. No pull back.</p> </div> <span style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#22D3EE", border: "1px dashed rgba(34,211,238,0.55)", borderRadius: "0", padding: "5px 11px", whiteSpace: "nowrap" } as React.CSSProperties}>Missing</span> </div> </div> <p style={{ marginTop: "22px", paddingLeft: "18px", borderLeft: "1px solid rgba(34,211,238,0.4)", fontFamily: "'Source Serif 4', Georgia, serif", fontSize: "clamp(17px, 2.2vw, 21px)", lineHeight: "1.45", color: "#EEF3F8", maxWidth: "62ch" } as React.CSSProperties}>The companies that spent fifty years building the modern chargeback now sit on the board of a payment rail that has none.</p> </div> </section>
    </>
  );
}

export function FailuresSection() {
  return (
    <>
    <section style={{ borderTop: "1px solid #151A25", padding: "clamp(40px, 4.6vw, 72px) clamp(20px, 5vw, 100px)", display: "flex", flexWrap: "wrap", alignItems: "flex-start", gap: "clamp(20px, 3vw, 56px)" } as React.CSSProperties}> <div style={{ flex: "0 0 clamp(146px, 14vw, 224px)", minWidth: "0", position: "sticky", top: "92px" } as React.CSSProperties}> <div style={{ font: "500 clamp(26px, 2.8vw, 40px)/1 'Geist Mono', ui-monospace, monospace", letterSpacing: "-0.02em", color: "#7C8798" } as React.CSSProperties}>03</div> <div style={{ marginTop: "12px", font: "500 10.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.16em", textTransform: "uppercase", color: "#22D3EE" } as React.CSSProperties}>The failures</div> <div style={{ marginTop: "14px", height: "1px", background: "#1B2130" } as React.CSSProperties}> </div> </div> <div style={{ flex: "1 1 min(620px, 100%)", minWidth: "0" } as React.CSSProperties}> <div style={{ height: "1px", background: "#1B2130" } as React.CSSProperties}> </div> <h2 style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: "600", fontSize: "clamp(28px, 4vw, 40px)", lineHeight: "1.1", letterSpacing: "-0.025em", marginTop: "14px", maxWidth: "26ch" } as React.CSSProperties}>Three ways an endpoint takes the money and <em style={{ fontStyle: "italic", color: "#EEF3F8" } as React.CSSProperties}>returns nothing</em> </h2> <p style={{ marginTop: "16px", fontSize: "15.5px", lineHeight: "1.65", color: "#AEB9C8", maxWidth: "74ch" } as React.CSSProperties}>These are the only failures Recourse exists for. Each returns HTTP 200, settles payment, and passes every deterministic check that exists today.</p> <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", marginTop: "clamp(28px, 4vw, 40px)" } as React.CSSProperties}> <div style={{ flex: "1 1 190px", minWidth: "0", border: "1px solid #1B2130", borderRadius: "0", background: "#0E1119", padding: "20px", transition: "border-color 0.2s ease" } as React.CSSProperties} className="rc-hover-6"> <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "10px" } as React.CSSProperties}> <div style={{ font: "500 12px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8" } as React.CSSProperties}>Stale</div> <span style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.1em", color: "#7C8798", border: "1px solid #1B2130", borderRadius: "0", padding: "4px 7px" } as React.CSSProperties}>200 OK</span> </div> <pre style={{ margin: "14px 0 0", padding: "14px", background: "#0C1018", border: "1px solid #151A25", borderRadius: "0", font: "400 11.5px/1.75 'Geist Mono', ui-monospace, monospace", color: "#AEB9C8", whiteSpace: "pre-wrap", wordBreak: "break-word" } as React.CSSProperties}>&#123;<span style={{ color: "#7C8798" } as React.CSSProperties}>"pair"</span>: "ETH-USD",
<span style={{ color: "#7C8798" } as React.CSSProperties}>"price"</span>: 4182.10,
<span style={{ color: "#7C8798" } as React.CSSProperties}>"sources"</span>: 3,
<span style={{ color: "#7C8798" } as React.CSSProperties}>"ts"</span>: <span style={{ color: "#22D3EE" } as React.CSSProperties}>"2026-09-04T05:11:07Z"</span>&#125;</pre> <p style={{ marginTop: "12px", fontSize: "13.5px", lineHeight: "1.6", color: "#AEB9C8" } as React.CSSProperties}>Correct shape, expired content. Nine hours old against a five second promise.</p> </div> <div style={{ flex: "1 1 190px", minWidth: "0", border: "1px solid #1B2130", borderRadius: "0", background: "#0E1119", padding: "20px", transition: "border-color 0.2s ease" } as React.CSSProperties} className="rc-hover-6"> <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "10px" } as React.CSSProperties}> <div style={{ font: "500 12px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8" } as React.CSSProperties}>Hollow</div> <span style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.1em", color: "#7C8798", border: "1px solid #1B2130", borderRadius: "0", padding: "4px 7px" } as React.CSSProperties}>200 OK</span> </div> <pre style={{ margin: "14px 0 0", padding: "14px", background: "#0C1018", border: "1px solid #151A25", borderRadius: "0", font: "400 11.5px/1.75 'Geist Mono', ui-monospace, monospace", color: "#AEB9C8", whiteSpace: "pre-wrap", wordBreak: "break-word" } as React.CSSProperties}>&#123;<span style={{ color: "#7C8798" } as React.CSSProperties}>"pair"</span>: "ETH-USD",
<span style={{ color: "#7C8798" } as React.CSSProperties}>"results"</span>: <span style={{ color: "#22D3EE" } as React.CSSProperties}>[]</span>,
<span style={{ color: "#7C8798" } as React.CSSProperties}>"count"</span>: <span style={{ color: "#22D3EE" } as React.CSSProperties}>0</span>&#125;</pre> <p style={{ marginTop: "12px", fontSize: "13.5px", lineHeight: "1.6", color: "#AEB9C8" } as React.CSSProperties}>Well formed, carrying nothing. An empty result set returned as success.</p> </div> <div style={{ flex: "1 1 190px", minWidth: "0", border: "1px solid #1B2130", borderRadius: "0", background: "#0E1119", padding: "20px", transition: "border-color 0.2s ease" } as React.CSSProperties} className="rc-hover-6"> <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "10px" } as React.CSSProperties}> <div style={{ font: "500 12px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8" } as React.CSSProperties}>Substituted</div> <span style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.1em", color: "#7C8798", border: "1px solid #1B2130", borderRadius: "0", padding: "4px 7px" } as React.CSSProperties}>200 OK</span> </div> <pre style={{ margin: "14px 0 0", padding: "14px", background: "#0C1018", border: "1px solid #151A25", borderRadius: "0", font: "400 11.5px/1.75 'Geist Mono', ui-monospace, monospace", color: "#AEB9C8", whiteSpace: "pre-wrap", wordBreak: "break-word" } as React.CSSProperties}>&#123;<span style={{ color: "#7C8798" } as React.CSSProperties}>"pair"</span>: <span style={{ color: "#22D3EE" } as React.CSSProperties}>"BTC-USD"</span>,
<span style={{ color: "#7C8798" } as React.CSSProperties}>"price"</span>: 118400.00,
<span style={{ color: "#7C8798" } as React.CSSProperties}>"sources"</span>: 3,
<span style={{ color: "#7C8798" } as React.CSSProperties}>"ts"</span>: "2026-09-04T14:11:12Z"&#125;</pre> <p style={{ marginTop: "12px", fontSize: "13.5px", lineHeight: "1.6", color: "#AEB9C8" } as React.CSSProperties}>Answers a different question than the one paid for. ETH-USD was requested.</p> </div> </div> <p style={{ marginTop: "18px", font: "500 11px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Every deterministic check passes</p> </div> </section>
    </>
  );
}

export function HowSection({
  windowSeconds,
  bondWei,
  moneyBackSeconds,
  finalitySeconds,
  network,
  settlementMoves,
}: {
  windowSeconds: number | null;
  bondWei: string | null;
  moneyBackSeconds: number | null;
  finalitySeconds: number | null;
  network: string;
  settlementMoves: boolean;
}) {
  // Read from contracts/FROZEN.json, where the canvas now types the 300 the
  // record holds. "a few minutes" is what this shows only when it is missing.
  const windowLabel = windowSeconds ? `${windowSeconds} s` : "a few minutes";
  const holdLabel = windowSeconds
    ? `The settlement window runs for ${windowSeconds} seconds, read from contracts/FROZEN.json.`
    : "The settlement window runs.";
  // Read from contracts/FROZEN.json, the value the escrow was deployed with.
  const bondLabel = bondWei ? ` of ${Number(bondWei) / 1e18} GEN` : "";
  // Both from this network's snapshot, timed off the chain's own transactions:
  // the median over the public record, by the feed's rule. Money back is timed
  // on the not_honored cases, the only ruling that returns the payment.
  // The canvas typed a figure here; where the settlement never moves there is
  // no money back to time, and the tile says that rather than a dash.
  const moneyBackLabel = moneyBackSeconds ? `${moneyBackSeconds} s` : settlementMoves ? "-" : "does not move";
  const finalityLabel = finalitySeconds ? `, about ${finalitySeconds} seconds later` : "";
  // The step states the mechanism, and where a runtime stops it the step says
  // so rather than let the sentence before it imply a refund. The README's
  // Settlement on Studio Next gives the whole reason.
  const settleNote = settlementMoves
    ? ""
    : ` On ${network} the verdict is written and the payment and the bond stay in escrow: consensus v0.6 accepts a value transfer only at the root of a transaction's fee allocation tree, and settle's payouts sit two messages below the transaction that funds them.`;
  return (
    <>
    <section id="how" style={{ borderTop: "1px solid #151A25", padding: "clamp(40px, 4.6vw, 72px) clamp(20px, 5vw, 100px)", display: "flex", flexWrap: "wrap", alignItems: "flex-start", gap: "clamp(20px, 3vw, 56px)" } as React.CSSProperties}> <div style={{ flex: "0 0 clamp(146px, 14vw, 224px)", minWidth: "0", position: "sticky", top: "92px" } as React.CSSProperties}> <div style={{ font: "500 clamp(26px, 2.8vw, 40px)/1 'Geist Mono', ui-monospace, monospace", letterSpacing: "-0.02em", color: "#7C8798" } as React.CSSProperties}>04</div> <div style={{ marginTop: "12px", font: "500 10.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.16em", textTransform: "uppercase", color: "#22D3EE" } as React.CSSProperties}>How it works</div> <div style={{ marginTop: "14px", height: "1px", background: "#1B2130" } as React.CSSProperties}> </div> <p style={{ marginTop: "14px", font: "400 10.5px/1.8 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.08em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>No judgment in the paid path</p> </div> <div style={{ flex: "1 1 min(620px, 100%)", minWidth: "0" } as React.CSSProperties}> <div style={{ height: "1px", background: "#1B2130" } as React.CSSProperties}> </div> <h2 style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: "600", fontSize: "clamp(28px, 4vw, 40px)", lineHeight: "1.1", letterSpacing: "-0.025em", marginTop: "14px", maxWidth: "26ch" } as React.CSSProperties}>Five steps, <em style={{ fontStyle: "italic", color: "#EEF3F8" } as React.CSSProperties}>no human in the loop</em> </h2> <div style={{ display: "flex", flexWrap: "wrap", gap: "1px", marginTop: "clamp(28px, 4vw, 40px)", border: "1px solid #1B2130", borderRadius: "0", background: "#1B2130", overflow: "hidden" } as React.CSSProperties}> <div style={{ flex: "1 1 178px", minWidth: "0", background: "#0E1119", padding: "20px 18px 22px" } as React.CSSProperties}> <div style={{ display: "flex", alignItems: "center", gap: "10px" } as React.CSSProperties}> <span style={{ font: "500 11px 'Geist Mono', ui-monospace, monospace", color: "#22D3EE" } as React.CSSProperties}>01</span> <span style={{ height: "1px", flex: "1", background: "#263048" } as React.CSSProperties}> </span> </div> <div style={{ marginTop: "14px", font: "500 12px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8" } as React.CSSProperties}>Call</div> <p style={{ marginTop: "9px", fontSize: "13.5px", lineHeight: "1.6", color: "#AEB9C8" } as React.CSSProperties}>The agent pays and receives the response immediately. No judgment in this path, no latency added.</p> </div> <div style={{ flex: "1 1 178px", minWidth: "0", background: "#0E1119", padding: "20px 18px 22px" } as React.CSSProperties}> <div style={{ display: "flex", alignItems: "center", gap: "10px" } as React.CSSProperties}> <span style={{ font: "500 11px 'Geist Mono', ui-monospace, monospace", color: "#22D3EE" } as React.CSSProperties}>02</span> <span style={{ height: "1px", flex: "1", background: "#263048" } as React.CSSProperties}> </span> </div> <div style={{ marginTop: "14px", font: "500 12px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8" } as React.CSSProperties}>Hold</div> <p style={{ marginTop: "9px", fontSize: "13.5px", lineHeight: "1.6", color: "#AEB9C8" } as React.CSSProperties}>Funds enter escrow, not the seller balance. {holdLabel}</p> </div> <div style={{ flex: "1 1 178px", minWidth: "0", background: "#0E1119", padding: "20px 18px 22px" } as React.CSSProperties}> <div style={{ display: "flex", alignItems: "center", gap: "10px" } as React.CSSProperties}> <span style={{ font: "500 11px 'Geist Mono', ui-monospace, monospace", color: "#22D3EE" } as React.CSSProperties}>03</span> <span style={{ height: "1px", flex: "1", background: "#263048" } as React.CSSProperties}> </span> </div> <div style={{ marginTop: "14px", font: "500 12px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8" } as React.CSSProperties}>Contest</div> <p style={{ marginTop: "9px", fontSize: "13.5px", lineHeight: "1.6", color: "#AEB9C8" } as React.CSSProperties}>The agent posts a fixed bond{bondLabel} and opens a case. No human is involved.</p> </div> <div style={{ flex: "1 1 178px", minWidth: "0", background: "#0E1119", padding: "20px 18px 22px" } as React.CSSProperties}> <div style={{ display: "flex", alignItems: "center", gap: "10px" } as React.CSSProperties}> <span style={{ font: "500 11px 'Geist Mono', ui-monospace, monospace", color: "#22D3EE" } as React.CSSProperties}>04</span> <span style={{ height: "1px", flex: "1", background: "#263048" } as React.CSSProperties}> </span> </div> <div style={{ marginTop: "14px", font: "500 12px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8" } as React.CSSProperties}>Judge</div> <p style={{ marginTop: "9px", fontSize: "13.5px", lineHeight: "1.6", color: "#AEB9C8" } as React.CSSProperties}>Validators receive three frozen strings and answer one question independently. Nothing is read from the live internet.</p> </div> <div style={{ flex: "1 1 178px", minWidth: "0", background: "#0E1119", padding: "20px 18px 22px" } as React.CSSProperties}> <div style={{ display: "flex", alignItems: "center", gap: "10px" } as React.CSSProperties}> <span style={{ font: "500 11px 'Geist Mono', ui-monospace, monospace", color: "#22D3EE" } as React.CSSProperties}>05</span> </div> <div style={{ marginTop: "14px", font: "500 12px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8" } as React.CSSProperties}>Settle</div> <p style={{ marginTop: "9px", fontSize: "13.5px", lineHeight: "1.6", color: "#AEB9C8" } as React.CSSProperties}>The verdict is written, and the settlement moves when that transaction finalizes{finalityLabel}. Two transactions, deliberately, so a successful appeal cannot arrive after the money has gone.{settleNote}</p> </div> </div> <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px", marginTop: "12px" } as React.CSSProperties}> <div style={{ border: "1px solid #1B2130", borderRadius: "0", background: "#0C1018", padding: "15px 18px" } as React.CSSProperties}> <div style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Settlement window</div> <div style={{ marginTop: "6px", font: "500 15px 'Geist Mono', ui-monospace, monospace", color: "#EEF3F8" } as React.CSSProperties}>{windowLabel}</div> </div> <div style={{ border: "1px solid #1B2130", borderRadius: "0", background: "#0C1018", padding: "15px 18px" } as React.CSSProperties}> <div style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Uncontested</div> <div style={{ marginTop: "6px", font: "500 15px 'Geist Mono', ui-monospace, monospace", color: "#EEF3F8" } as React.CSSProperties}>auto release</div> </div> <div style={{ border: "1px solid #1B2130", borderRadius: "0", background: "#0C1018", padding: "15px 18px" } as React.CSSProperties}> <div style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Dispute to money back, median</div> <div style={{ marginTop: "6px", font: "500 15px 'Geist Mono', ui-monospace, monospace", color: "#EEF3F8" } as React.CSSProperties}>{moneyBackLabel}</div> </div> </div>  </div> </section>
    </>
  );
}

export function FeedSectionShell({ children }: { children: React.ReactNode }) {
  return (
    <>
    <section style={{ borderTop: "1px solid #151A25", padding: "clamp(40px, 4.6vw, 72px) clamp(20px, 5vw, 100px)", display: "flex", flexWrap: "wrap", alignItems: "flex-start", gap: "clamp(20px, 3vw, 56px)" } as React.CSSProperties}> <div style={{ flex: "0 0 clamp(146px, 14vw, 224px)", minWidth: "0", position: "sticky", top: "92px" } as React.CSSProperties}> <div style={{ font: "500 clamp(26px, 2.8vw, 40px)/1 'Geist Mono', ui-monospace, monospace", letterSpacing: "-0.02em", color: "#7C8798" } as React.CSSProperties}>05</div> <div style={{ marginTop: "12px", font: "500 10.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.16em", textTransform: "uppercase", color: "#22D3EE" } as React.CSSProperties}>Live feed</div> <div style={{ marginTop: "14px", height: "1px", background: "#1B2130" } as React.CSSProperties}> </div> <p style={{ marginTop: "14px", font: "400 10.5px/1.8 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.08em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Read only - escrow and dispute contracts</p> </div> <div style={{ flex: "1 1 min(620px, 100%)", minWidth: "0" } as React.CSSProperties}> <div style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-end", justifyContent: "space-between", gap: "14px" } as React.CSSProperties}> <div> <div style={{ height: "1px", background: "#1B2130" } as React.CSSProperties}> </div> <h2 style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: "600", fontSize: "clamp(28px, 4vw, 40px)", lineHeight: "1.1", letterSpacing: "-0.025em", marginTop: "14px" } as React.CSSProperties}>Every payment, every case, public</h2> </div>  </div> <div style={{ marginTop: "clamp(24px, 3vw, 32px)" } as React.CSSProperties}> {children} </div> </div> </section>
    </>
  );
}

/** "not_honored" the way the copy writes it. */
function said(verdict: string): string {
  return verdict.replace("_", " ");
}

/** The day a measurement was taken, from its unix time. */
function day(at: number): string {
  return new Date(at * 1000).toISOString().slice(0, 10);
}

/**
 * What a chip says on hover: what was expected, what the case landed on, and
 * whether its runs held. A run that returned no verdict is counted, and where
 * the runs left over split as well the title says so, which the canvas's title
 * for studio-next's case 07 left out.
 */
function chipTitle(row: Row, runs: number): string {
  const first = row.observed[0] ?? "error";
  const answered = row.correct ? "matched" : first === "error" ? "returned no verdict" : `answered ${said(first)}`;
  const failed = row.observed.filter((verdict) => verdict === "error").length;
  const split = new Set(row.observed.filter((verdict) => verdict !== "error")).size > 1;
  const lost = `${spell(failed)} run${failed === 1 ? "" : "s"} returned no verdict`;
  const held = split
    ? failed
      ? `${lost} and the other ${spell(runs - failed)} disagreed`
      : `the ${spell(runs)} runs disagreed`
    : failed
      ? lost
      : `all ${spell(runs)} runs agreed`;
  return `Expected ${said(row.expected)} - ${answered} - ${held}`;
}

/** The cases a network's first set missed. */
function missesOf(column: EvaluationColumn): string[] {
  return column.results.rows.filter((row) => !row.correct).map((row) => row.id);
}

/** The verdict a case landed on: its first run's, which is how accuracy is scored. */
function landedOn(column: EvaluationColumn, id: string): string | undefined {
  return column.results.rows.find((row) => row.id === id)?.observed[0];
}

/** studionet's files carry no suffix, and any other network's are named for it. */
function suffixOf(network: string): string {
  return network === "studionet" ? "" : `.${network}`;
}

const SMALL = { font: "400 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.1em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties;

const NOTE = { marginTop: "10px", fontSize: "13.5px", lineHeight: "1.65", color: "#AEB9C8", maxWidth: "78ch" } as React.CSSProperties;

/** One headline tile: a row per network, a rule between them, and the files its numbers came from. */
function Figure({
  label,
  columns,
  pick,
  files,
}: {
  label: string;
  columns: EvaluationColumn[];
  pick: (column: EvaluationColumn) => [number, number];
  files: string[];
}) {
  return (
    <div style={{ flex: "1 1 210px", minWidth: "0", border: "1px solid #1B2130", borderRadius: "0", background: "#0E1119", padding: "clamp(18px, 2.2vw, 26px)" } as React.CSSProperties}>
      <div style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.16em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>{label}</div>
      <div style={{ marginTop: "16px", display: "flex", flexDirection: "column", gap: "12px" } as React.CSSProperties}>
        {columns.map((column, index) => {
          const [value, of] = pick(column);
          return (
            <Fragment key={column.network}>
              {index > 0 ? <div style={{ height: "1px", background: "#1B2130" } as React.CSSProperties}></div> : null}
              {/* The canvas keeps the network and its figure on one line. Where
                  four tiles share a row and each is too narrow for both, the
                  figure ran past the tile's edge, so here it wraps under the
                  network's name instead. */}
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "baseline", justifyContent: "space-between", gap: "10px", whiteSpace: "nowrap" } as React.CSSProperties}>
                <span style={SMALL}>{column.network}</span>
                <span style={{ display: "inline-flex", alignItems: "baseline", gap: "6px" } as React.CSSProperties}>
                  <span style={{ font: "500 clamp(28px, 3.6vw, 44px)/1 'Geist Mono', ui-monospace, monospace", color: "#EEF3F8", letterSpacing: "-0.03em", fontVariantNumeric: "tabular-nums" } as React.CSSProperties}>{value}</span>
                  <span style={{ font: "500 clamp(14px, 1.8vw, 20px)/1 'Geist Mono', ui-monospace, monospace", color: "#7C8798" } as React.CSSProperties}>/ {of}</span>
                </span>
              </div>
            </Fragment>
          );
        })}
      </div>
      {/* The canvas names eval/results.json under every tile. Each figure
          here names the files its numbers came from, one per network. */}
      <div style={{ ...SMALL, marginTop: "16px", overflowWrap: "anywhere" } as React.CSSProperties}>
        {files.map((file) => (
          <div key={file}>{file}</div>
        ))}
      </div>
    </div>
  );
}

export function EvaluationSection({ columns }: { columns: EvaluationColumn[] }) {
  const [first] = columns;
  const { n, runs } = first.results;
  const both = columns.length === 2;
  const measured = columns.map((column) => `${column.network} on ${day(column.results.measured_at)}`);
  const where = columns.length > 1 ? `Measured on ${spell(columns.length)} networks, ${list(measured)}` : `Measured on ${measured[0]}`;
  const files = (base: string) => columns.map((column) => `eval/${base}${suffixOf(column.network)}.json`);
  // A miss every network shares is a reading of the case rather than a
  // wobble, and case 12 is the one the paragraph below explains. Any other set
  // of misses is named from the rows rather than explained here.
  const shared = missesOf(first).filter((id) => columns.every((column) => missesOf(column).includes(id)));
  const twelveHeld = columns.every((column) => {
    const row = column.results.rows.find((one) => one.id === "12");
    return !!row && row.stable && row.observed.every((verdict) => verdict === "not_honored");
  });
  const named = columns
    .map((column) => {
      const missed = missesOf(column);
      return missed.length ? `case${missed.length === 1 ? "" : "s"} ${list(missed)} on ${column.network}` : `none on ${column.network}`;
    })
    .join(", and ");
  // Where the two columns landed differently, on the first run, the way
  // accuracy is scored and eval/RESULTS.md counts it.
  const ids = first.results.rows.map((row) => row.id);
  const differ = both ? ids.filter((id) => landedOn(columns[0], id) !== landedOn(columns[1], id)) : [];
  const extra = differ.length === 1 ? columns.filter((column) => missesOf(column).includes(differ[0])) : [];
  const parted = differ.length
    ? ` ${differ.length === 1 ? `Case ${differ[0]}` : `Cases ${list(differ)}`} did not: two validator sets read the same frozen strings and reached different verdicts, which is a finding rather than noise${extra.length === 1 ? `, and it is the extra miss on ${extra[0].network}` : ""}.`
    : "";
  return (
    <>
    <section id="evaluation" style={{ borderTop: "1px solid #151A25", padding: "clamp(40px, 4.6vw, 72px) clamp(20px, 5vw, 100px)", display: "flex", flexWrap: "wrap", alignItems: "flex-start", gap: "clamp(20px, 3vw, 56px)" } as React.CSSProperties}>
      <div style={{ flex: "0 0 clamp(146px, 14vw, 224px)", minWidth: "0", position: "sticky", top: "92px" } as React.CSSProperties}>
        <div style={{ font: "500 clamp(26px, 2.8vw, 40px)/1 'Geist Mono', ui-monospace, monospace", letterSpacing: "-0.02em", color: "#7C8798" } as React.CSSProperties}>06</div>
        <div style={{ marginTop: "12px", font: "500 10.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.16em", textTransform: "uppercase", color: "#22D3EE" } as React.CSSProperties}>Evaluation</div>
        <div style={{ marginTop: "14px", height: "1px", background: "#1B2130" } as React.CSSProperties}></div>
        <p style={{ marginTop: "14px", font: "400 10.5px/1.8 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.08em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>{capital(spell(n))} cases committed before the run</p>
      </div>
      <div style={{ flex: "1 1 min(620px, 100%)", minWidth: "0" } as React.CSSProperties}>
        <div style={{ height: "1px", background: "#1B2130" } as React.CSSProperties}></div>
        <h2 style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: "600", fontSize: "clamp(28px, 4vw, 40px)", lineHeight: "1.1", letterSpacing: "-0.025em", marginTop: "14px", maxWidth: "24ch" } as React.CSSProperties}>The number, published <em style={{ fontStyle: "italic", color: "#EEF3F8" } as React.CSSProperties}>whatever it is</em></h2>
        <p style={{ marginTop: "16px", fontSize: "15.5px", lineHeight: "1.65", color: "#AEB9C8", maxWidth: "74ch" } as React.CSSProperties}>{capital(spell(n))} cases with the correct verdict written down and committed before the dispute contract ran. The git history proves the order. {where}, {spell(runs)} runs per case, through real consensus rather than a single model call.{columns.length > 1 ? " One column per network, never merged and never averaged." : ""}</p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", marginTop: "clamp(28px, 4vw, 40px)", alignItems: "stretch" } as React.CSSProperties}>
          <Figure label="Accuracy" columns={columns} pick={(column) => [column.results.accuracy, column.results.n]} files={files("results")} />
          <Figure label="Stability" columns={columns} pick={(column) => [column.results.stability, column.results.n]} files={files("results")} />
          <Figure label="Landed on unclear" columns={columns} pick={(column) => [column.results.unclear, column.results.n]} files={files("results")} />
          <Figure label="Held out set" columns={columns} pick={(column) => [column.heldOut.accuracy, column.heldOut.n]} files={files("results-v2")} />
        </div>
        {columns.map((column) => (
          <div key={column.network} style={{ marginTop: "14px", display: "flex", flexWrap: "wrap", alignItems: "center", gap: "10px" } as React.CSSProperties}>
            <span style={{ ...SMALL, flex: "0 0 auto", minWidth: "92px" } as React.CSSProperties}>{column.network}</span>
            <span style={{ display: "flex", flexWrap: "wrap", gap: "6px" } as React.CSSProperties}>
              {column.results.rows.map((row) => (
                <span
                  key={row.id}
                  title={chipTitle(row, column.results.runs)}
                  style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", minWidth: "34px", padding: "6px 8px", font: "500 11px 'Geist Mono', ui-monospace, monospace", color: row.correct ? "#4ADE80" : "#F87171", background: row.correct ? "rgba(74,222,128,0.10)" : "rgba(248,113,113,0.10)", border: `1px solid ${row.correct ? "rgba(74,222,128,0.35)" : "rgba(248,113,113,0.35)"}`, borderRadius: "0", fontVariantNumeric: "tabular-nums" } as React.CSSProperties}
                >
                  {row.id}
                </span>
              ))}
            </span>
          </div>
        ))}
        <p style={{ marginTop: "12px", font: "400 11px/1.7 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.06em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>{capital(spell(runs))} runs per case. Green matched the committed answer, red did not. Hover a chip for what it answered and whether it was stable. Full table in eval/RESULTS.md.</p>
        <div style={{ marginTop: "16px", border: "1px dashed #263048", borderRadius: "0", background: "transparent", padding: "18px 20px" } as React.CSSProperties}>
          <div style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Two sets, always together</div>
          <p style={NOTE}>The first {spell(n)} cases are the set the question was written against, committed in b50757f one commit before the judgment contract existed. The {spell(first.heldOut.n)} held out cases were committed alone in 04ca928, with the runner unable to read the file at that commit, so their answers are provably fixed before the measurement. They were chosen to probe the weakness the first set exposed rather than to raise the score, which is why the second figure is the lower one.</p>
          {both && shared.length === 1 && shared[0] === "12" && twelveHeld ? (
            <p style={NOTE}>Both networks read case 12 as not honored where the committed expectation was unclear: three named venues were promised and three different venues were used, and the promise never settles whether the count or the names govern. Both answered it the same way {spell(runs)} times, so it is a consistent reading rather than a wobble. It is counted as a miss on both.</p>
          ) : columns.length === 1 && shared.length === 1 && shared[0] === "12" ? (
            <p style={NOTE}>The one miss in the first set is case 12, where three named venues were promised and three different venues were used. The judge ruled not honored and gave the same ground in all {spell(runs)} runs. The answer key says unclear because the promise never settles whether the count or the names govern. It is counted as a miss.</p>
          ) : columns.some((column) => missesOf(column).length) ? (
            <p style={NOTE}>The misses in the first set are {named}. eval/RESULTS.md sets out each one beside what the other network answered, and each is counted as a miss.</p>
          ) : (
            <p style={NOTE}>Nothing in the first set was missed.</p>
          )}
          {both ? (
            <p style={NOTE}>The two pairs of contracts are the same logic, the same prompt and the same strings, with a published diff that touches only API names, running under two runtimes. {capital(spell(ids.length - differ.length))} of {spell(ids.length)} cases landed on the same verdict on both networks.{parted}</p>
          ) : null}
        </div>
        <p style={{ marginTop: "22px", paddingLeft: "18px", borderLeft: "1px solid rgba(34,211,238,0.4)", fontFamily: "'Source Serif 4', Georgia, serif", fontSize: "clamp(17px, 2.2vw, 21px)", lineHeight: "1.45", color: "#EEF3F8", maxWidth: "62ch" } as React.CSSProperties}>A dispute layer whose reliability has not been measured is a claim, not infrastructure.</p>
      </div>
    </section>
    </>
  );
}

export function LimitsSection({ committee }: { committee: number | null }) {
  // The committee is the size the chain's own receipts show, recorded in this
  // network's snapshot. Each member asks in both presentation orders. What each
  // network charges is the README's, from the receipts both snapshots keep.
  const work = committee
    ? `One adjudication is ${spell(committee * 2)} model calls, ${spell(committee)} nodes times two presentation orders.`
    : "One adjudication asks every member of the committee the same question in both presentation orders.";
  return (
    <>
    <section style={{ borderTop: "1px solid #151A25", padding: "clamp(40px, 4.6vw, 72px) clamp(20px, 5vw, 100px)", display: "flex", flexWrap: "wrap", alignItems: "flex-start", gap: "clamp(20px, 3vw, 56px)" } as React.CSSProperties}> <div style={{ flex: "0 0 clamp(146px, 14vw, 224px)", minWidth: "0", position: "sticky", top: "92px" } as React.CSSProperties}> <div style={{ font: "500 clamp(26px, 2.8vw, 40px)/1 'Geist Mono', ui-monospace, monospace", letterSpacing: "-0.02em", color: "#7C8798" } as React.CSSProperties}>07</div> <div style={{ marginTop: "12px", font: "500 10.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.16em", textTransform: "uppercase", color: "#22D3EE" } as React.CSSProperties}>What it is not</div> <div style={{ marginTop: "14px", height: "1px", background: "#1B2130" } as React.CSSProperties}> </div> </div> <div style={{ flex: "1 1 min(620px, 100%)", minWidth: "0" } as React.CSSProperties}> <div style={{ height: "1px", background: "#1B2130" } as React.CSSProperties}> </div> <h2 style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: "600", fontSize: "clamp(28px, 4vw, 40px)", lineHeight: "1.1", letterSpacing: "-0.025em", marginTop: "14px", maxWidth: "24ch" } as React.CSSProperties}>Three limits, <em style={{ fontStyle: "italic", color: "#EEF3F8" } as React.CSSProperties}>each with its reason</em> </h2> <div style={{ marginTop: "clamp(28px, 4vw, 40px)", borderTop: "1px solid #1B2130" } as React.CSSProperties}> <div style={{ display: "grid", gridTemplateColumns: "minmax(0, clamp(200px, 22vw, 320px)) minmax(0, 1fr)", gap: "clamp(12px, 3vw, 44px)", padding: "22px 0", borderBottom: "1px solid #1B2130" } as React.CSSProperties}> <div style={{ font: "500 11.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8" } as React.CSSProperties}>Not sub cent yet</div> <p style={{ fontSize: "15px", lineHeight: "1.65", color: "#AEB9C8", maxWidth: "80ch" } as React.CSSProperties}>{work} studionet charges nothing for them and studio-next charges a fee in testnet GEN, so the page states the work rather than a price, and the first version targets payments large enough to carry that work. Session batching is the route below it.</p> </div> <div style={{ display: "grid", gridTemplateColumns: "minmax(0, clamp(200px, 22vw, 320px)) minmax(0, 1fr)", gap: "clamp(12px, 3vw, 44px)", padding: "22px 0", borderBottom: "1px solid #1B2130" } as React.CSSProperties}> <div style={{ font: "500 11.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8" } as React.CSSProperties}>Not an adoption driver today</div> <p style={{ fontSize: "15px", lineHeight: "1.65", color: "#AEB9C8", maxWidth: "80ch" } as React.CSSProperties}>Agents fail at the payment step for want of funded wallets, not for fear of being cheated. This matters once wallets are routine and an agent must choose between two endpoints that will both take its money.</p> </div> <div style={{ display: "grid", gridTemplateColumns: "minmax(0, clamp(200px, 22vw, 320px)) minmax(0, 1fr)", gap: "clamp(12px, 3vw, 44px)", padding: "22px 0", borderBottom: "1px solid #1B2130" } as React.CSSProperties}> <div style={{ font: "500 11.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8" } as React.CSSProperties}>Not perfect judgment</div> <p style={{ fontSize: "15px", lineHeight: "1.65", color: "#AEB9C8", maxWidth: "80ch" } as React.CSSProperties}>A vague promise produces a vague verdict, and the system says so through the unclear outcome rather than performing confidence it has not earned.</p> </div> </div> <p style={{ marginTop: "22px", paddingLeft: "18px", borderLeft: "1px solid rgba(34,211,238,0.4)", fontFamily: "'Source Serif 4', Georgia, serif", fontSize: "clamp(17px, 2.2vw, 21px)", lineHeight: "1.45", color: "#EEF3F8", maxWidth: "62ch" } as React.CSSProperties}>A refund system in which the merchant selects the judge is a refund policy. It is not a dispute right.</p> </div> </section>
    </>
  );
}

export function ClosingSection() {
  // The page's last word, set as a closing panel centred on both axes: the
  // index and the eyebrow between two rules, the line itself in the largest
  // serif on the page after the hero, and the mark as a seal. Along its foot
  // runs the hero's lane, a tick for every payment, and the one in the middle
  // stands up in the accent: the payment somebody contested. "missing" is
  // underlined in the dashed accent the gap section gives its Missing row.
  const rule = { height: "1px", background: "#263048", flex: "0 0 auto" } as React.CSSProperties;
  return (
    <>
    <section aria-labelledby="rc-closing" style={{ position: "relative", overflow: "hidden", borderTop: "1px solid #1B2130", borderBottom: "1px solid #1B2130", background: "radial-gradient(ellipse 70% 60% at 50% 42%, #0E1119 0%, #0A0C12 72%)", minHeight: "clamp(460px, 76svh, 780px)", display: "grid", placeItems: "center", padding: "clamp(72px, 10vw, 128px) clamp(20px, 5vw, 100px) clamp(116px, 13vw, 156px)" } as React.CSSProperties}>
      <div style={{ position: "relative", zIndex: "1", display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", maxWidth: "100%" } as React.CSSProperties}>
        <div style={{ display: "flex", alignItems: "center", gap: "14px", font: "500 10.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.3em", textTransform: "uppercase" } as React.CSSProperties}>
          <span aria-hidden="true" style={{ ...rule, width: "clamp(20px, 6vw, 64px)" } as React.CSSProperties}></span>
          <span style={{ color: "#7C8798" } as React.CSSProperties}>08</span>
          <span aria-hidden="true" style={{ ...rule, width: "14px" } as React.CSSProperties}></span>
          <span style={{ color: "#22D3EE" } as React.CSSProperties}>In one line</span>
          <span aria-hidden="true" style={{ ...rule, width: "clamp(20px, 6vw, 64px)" } as React.CSSProperties}></span>
        </div>
        <h2 id="rc-closing" style={{ marginTop: "clamp(34px, 5vw, 56px)", fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: "500", fontSize: "clamp(40px, 7.6vw, 108px)", lineHeight: "1.02", letterSpacing: "-0.035em", color: "#EEF3F8" } as React.CSSProperties}>
          <span style={{ display: "block", textWrap: "balance" } as React.CSSProperties}>The rail is finished.</span>
          <span style={{ display: "block", marginTop: "0.08em", fontStyle: "italic", textWrap: "balance" } as React.CSSProperties}>The right is <span className="rc-missing">missing</span>.</span>
        </h2>
        <div aria-hidden="true" style={{ marginTop: "clamp(40px, 6vw, 64px)", display: "flex", alignItems: "center", gap: "16px" } as React.CSSProperties}>
          <span style={{ ...rule, width: "clamp(40px, 8vw, 88px)" } as React.CSSProperties}></span>
          <span style={{ width: "40px", height: "40px", borderRadius: "50%", border: "1px solid rgba(34,211,238,0.5)", display: "inline-flex", alignItems: "center", justifyContent: "center", fontFamily: "'Source Serif 4', Georgia, serif", fontStyle: "italic", fontWeight: "600", fontSize: "16px", color: "#EEF3F8" } as React.CSSProperties}>R</span>
          <span style={{ ...rule, width: "clamp(40px, 8vw, 88px)" } as React.CSSProperties}></span>
        </div>
      </div>
      <svg aria-hidden="true" width="100%" height="96" style={{ position: "absolute", left: "0", right: "0", bottom: "0", display: "block" } as React.CSSProperties}>
        <defs>
          <pattern id="rc-closing-ticks" x="50%" y="0" width={56} height={96} patternUnits="userSpaceOnUse">
            <rect x="0" y={68} width={1} height={28} fill="rgba(70,84,104,0.6)"></rect>
          </pattern>
        </defs>
        <rect x="0" y="0" width="100%" height={96} fill="url(#rc-closing-ticks)"></rect>
        <rect x="50%" y={24} width={1} height={72} fill="#22D3EE"></rect>
      </svg>
    </section>
    </>
  );
}
