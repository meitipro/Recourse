"use client";

/**
 * The clerk: hand it a case and watch the frozen contract's judge rule on it.
 *
 * Ported from the canvas, single case only. Three strings in, one verdict out,
 * through /api/clerk to the linter service, which loads contracts/dispute.py
 * through the test double and runs judge() unchanged. What comes back is the
 * deployed code's answer, not a paraphrase of it.
 *
 * It is one model where the chain uses a committee of five, and no chain at
 * all. Every state on this panel says "Recorded on chain: no", because it is
 * not, and the published 17 of 18 is not measured here and never will be.
 *
 * The canvas's second mode ran all eighteen cases and scored itself. That is
 * deliberately not here: a browser score standing next to the published one
 * would be a second accuracy number measured a different way.
 */

import { Fragment, useEffect, useState } from "react";

const MONO = "'Geist Mono', ui-monospace, monospace";

type Case = {
  id: string;
  promise: string;
  request: string;
  response: string;
  timing: string;
  expected: string;
};

type Answer = {
  verdict: string;
  reason: string;
  agreed: string;
  seconds: number;
  recorded_on_chain: boolean;
  timing_from: string;
};

const CHIP = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  height: "28px",
  padding: "0 10px",
  borderRadius: "0",
  cursor: "pointer",
  font: `500 10px ${MONO}`,
  letterSpacing: "0.1em",
  textTransform: "uppercase" as const,
};

export default function Clerk({ cases }: { cases: Case[] }) {
  const [promise, setPromise] = useState("");
  const [request, setRequest] = useState("");
  const [response, setResponse] = useState("");
  const [loaded, setLoaded] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "busy" | "done" | "error">("idle");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [error, setError] = useState("");
  const [curlCopied, setCurlCopied] = useState(false);

  const ready = promise.trim() && request.trim() && response.trim();
  const busy = status === "busy";

  // The committed expectation applies only while the three strings on screen
  // are still the case that was loaded. Edit any of them and it stops being
  // that case, so the expectation and its timing stop being used.
  const current = cases.find((one) => one.id === loaded);
  const untouched =
    current !== undefined &&
    current.promise === promise &&
    current.request === request &&
    current.response === response;

  async function submit() {
    if (!ready || busy) return;
    setStatus("busy");
    setError("");
    try {
      const reply = await fetch("/api/clerk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // A committed case is judged against its own timing block, the one
        // the chain wrote when it ran. Anything typed by hand gets the clock
        // now, and the panel says which was used.
        body: JSON.stringify(untouched && current ? { promise, request, response, timing: current.timing } : { promise, request, response }),
        signal: AbortSignal.timeout(200_000),
      });
      const payload = (await reply.json()) as Answer & { error?: string };
      if (!reply.ok || payload.error) {
        setStatus("error");
        setError(
          reply.status === 429
            ? "Too many judgments in the last minute. Try again shortly."
            : payload.error || "Could not reach the clerk. Try again.",
        );
        return;
      }
      setAnswer(payload);
      setStatus("done");
    } catch {
      setStatus("error");
      setError("Could not reach the clerk. Try again.");
    }
  }

  function load(one: Case) {
    setPromise(one.promise);
    setRequest(one.request);
    setResponse(one.response);
    setLoaded(one.id);
    setStatus("idle");
    setAnswer(null);
    setError("");
  }

  function clear() {
    setPromise("");
    setRequest("");
    setResponse("");
    setLoaded(null);
    setStatus("idle");
    setAnswer(null);
    setError("");
  }

  const expectation = untouched ? current.expected : "";
  const verdict = answer?.verdict ?? "";
  const matched = expectation && verdict ? expectation === verdict : null;

  // The example targets wherever this page is actually served from. It used to
  // name recourse.vercel.app, which belongs to an unrelated project, so a
  // reader copying it would have sent three strings to a stranger.
  const [origin, setOrigin] = useState("");
  useEffect(() => setOrigin(window.location.origin), []);
  const curlCmd = `curl -s -X POST ${origin || "<this site>"}/api/clerk \\
  -H "Content-Type: application/json" \\
  -d '{"promise": "...", "request": "...", "response": "..."}'`;

  const verdictColour =
    verdict === "honored" ? "#4ADE80" : verdict === "not_honored" ? "#F87171" : "#AEB9C8";

  const v = {
    chips: cases.map((one) => ({
      id: one.id,
      load: () => load(one),
      style: {
        ...CHIP,
        background: loaded === one.id ? "rgba(34,211,238,0.08)" : "#0C1018",
        color: loaded === one.id ? "#22D3EE" : "#7C8798",
        border: `1px solid ${loaded === one.id ? "rgba(34,211,238,0.4)" : "#1B2130"}`,
      } as React.CSSProperties,
    })),
    chipNote: loaded
      ? untouched
        ? `case ${loaded}, as committed`
        : `case ${loaded}, edited`
      : `${cases.length} committed cases`,
    promise,
    request,
    response,
    setPromise: (e: React.ChangeEvent<HTMLTextAreaElement>) => setPromise(e.target.value.slice(0, 4000)),
    setRequest: (e: React.ChangeEvent<HTMLTextAreaElement>) => setRequest(e.target.value.slice(0, 4000)),
    setResponse: (e: React.ChangeEvent<HTMLTextAreaElement>) => setResponse(e.target.value.slice(0, 4000)),
    onKey: (e: React.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        void submit();
      }
    },
    submit,
    submitLabel: busy ? "Judging" : "Put it to the judge",
    submitStyle: {
      display: "inline-flex",
      alignItems: "center",
      height: "44px",
      padding: "0 20px",
      borderRadius: "0",
      border: "1px solid rgba(34,211,238,0.4)",
      background: ready && !busy ? "rgba(34,211,238,0.07)" : "transparent",
      color: ready && !busy ? "#22D3EE" : "#4A5468",
      cursor: !ready ? "not-allowed" : busy ? "wait" : "pointer",
      font: `500 12px ${MONO}`,
      letterSpacing: "0.08em",
    } as React.CSSProperties,
    clearAll: clear,
    isIdle: status === "idle",
    isBusy: busy,
    isDone: status === "done" && answer !== null,
    isError: status === "error",
    stateLabel:
      status === "busy"
        ? "Reading the three frozen strings"
        : status === "done"
          ? "Judged"
          : status === "error"
            ? "Not judged"
            : "No case submitted",
    stateStyle: { font: `500 10px ${MONO}`, letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties,
    verdict: verdict ? verdict.replace("_", " ") : "",
    verdictStyle: {
      font: `500 clamp(22px, 3vw, 30px) ${MONO}`,
      letterSpacing: "-0.01em",
      textTransform: "uppercase",
      color: verdictColour,
    } as React.CSSProperties,
    reason: answer?.reason ?? "",
    elapsed: answer ? `${answer.seconds}s, timing from ${answer.timing_from}` : "-",
    expected: expectation ? expectation.replace("_", " ") : "not a committed case",
    expectedColor: matched === null ? "#7C8798" : matched ? "#4ADE80" : "#F87171",
    // The route answers "not configured" only when the build has no
    // LINTER_URL, so that is the one case that gets the offline sentence.
    // Anything else is a real failure and says so, with a way to retry.
    errorText: error.includes("not configured")
      ? "This copy of the site has no judge behind it, so the clerk cannot rule here. The feed and the evaluation do not need one."
      : error,
    curlCmd,
    copyCurl: () => {
      navigator.clipboard?.writeText(curlCmd);
      setCurlCopied(true);
      setTimeout(() => setCurlCopied(false), 1600);
    },
    curlNote: curlCopied ? "copied" : "copy",
    curlNoteColor: curlCopied ? "#22D3EE" : "#7C8798",
  };

  return (
    <>
 <div style={{ fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif", color: "#EEF3F8", background: "#0A0C12" } as React.CSSProperties}> <div style={{ display: "flex", alignItems: "center", gap: "14px" } as React.CSSProperties}> <span style={{ font: "500 10.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.16em", textTransform: "uppercase", color: "#22D3EE", whiteSpace: "nowrap" } as React.CSSProperties}>The Clerk</span> <span style={{ height: "1px", flex: "1", background: "#1B2130" } as React.CSSProperties}> </span> </div> <h1 style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: "600", fontSize: "clamp(32px, 5vw, 50px)", lineHeight: "1.04", letterSpacing: "-0.03em", marginTop: "16px", maxWidth: "22ch" } as React.CSSProperties}>Put the judge <em style={{ fontStyle: "italic", color: "#EEF3F8" } as React.CSSProperties}>on the stand</em> </h1> <p style={{ marginTop: "16px", fontSize: "15.5px", lineHeight: "1.65", color: "#AEB9C8", maxWidth: "66ch" } as React.CSSProperties}>The clerk takes the same three frozen strings a validator receives and answers the same single question. Judge one case, or run the whole committed set and watch the accuracy number assemble itself.</p>  <div style={{ display: "flex", alignItems: "flex-start", gap: "12px", marginTop: "18px", border: "1px solid rgba(217,165,65,0.28)", borderRadius: "0", background: "rgba(217,165,65,0.05)", padding: "14px 16px" } as React.CSSProperties}> <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: "#D9A441", marginTop: "7px", flex: "0 0 auto" } as React.CSSProperties}> </span> <div> <div style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#D9A441" } as React.CSSProperties}>The judge prompt, not the deployed contract</div> <p style={{ marginTop: "7px", fontSize: "13.5px", lineHeight: "1.6", color: "#AEB9C8", maxWidth: "76ch" } as React.CSSProperties}>This runs the documented judge prompt against a single model in your browser. On chain the same prompt runs across a validator committee that must reach agreement, and nothing here is written to a receipt. Every verdict below is indicative, and none of it is the published number.</p> <div style={{ marginTop: "9px", display: "inline-flex", alignItems: "center", gap: "8px", font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#D9A441" } as React.CSSProperties}><span>Recorded on chain</span><span style={{ color: "#EEF3F8" }}>no</span></div> </div> </div> {true && (<> <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", marginTop: "20px", alignItems: "stretch" } as React.CSSProperties}> <div style={{ flex: "1 1 400px", minWidth: "0", border: "1px solid #1B2130", borderRadius: "0", background: "#0E1119", padding: "clamp(18px, 2.4vw, 24px)" } as React.CSSProperties}> <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "10px" } as React.CSSProperties}> <span style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Case file</span> <button type="button" onClick={v.clearAll} style={{ background: "transparent", border: "0", padding: "0", cursor: "pointer", font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.04em", color: "#7C8798" } as React.CSSProperties}>Clear</button> </div> <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "14px" } as React.CSSProperties}> {(v.chips || []).map((chip, i) => (<Fragment key={i}> <button type="button" onClick={chip.load} style={chip.style}>{chip.id}</button> </Fragment>))} </div> <p style={{ marginTop: "11px", font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.12em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>{v.chipNote}</p> <div style={{ marginTop: "20px" } as React.CSSProperties}> <label style={{ display: "block", font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Promise</label> <textarea onChange={v.setPromise} onKeyDown={v.onKey} value={v.promise} rows={3} placeholder="What the seller published about this endpoint" style={{ width: "100%", marginTop: "9px", resize: "vertical", border: "1px solid #1B2130", borderRadius: "0", background: "#0C1018", color: "#EEF3F8", padding: "12px 13px", font: "400 12.5px/1.65 'Geist Mono', ui-monospace, monospace", outline: "none" } as React.CSSProperties} className="rc-focus-1" /> </div> <div style={{ marginTop: "16px" } as React.CSSProperties}> <label style={{ display: "block", font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Request</label> <textarea onChange={v.setRequest} onKeyDown={v.onKey} value={v.request} rows={2} placeholder="The call the buying agent paid for" style={{ width: "100%", marginTop: "9px", resize: "vertical", border: "1px solid #1B2130", borderRadius: "0", background: "#0C1018", color: "#EEF3F8", padding: "12px 13px", font: "400 12.5px/1.65 'Geist Mono', ui-monospace, monospace", outline: "none" } as React.CSSProperties} className="rc-focus-1" /> </div> <div style={{ marginTop: "16px" } as React.CSSProperties}> <label style={{ display: "block", font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Response</label> <textarea onChange={v.setResponse} onKeyDown={v.onKey} value={v.response} rows={4} placeholder="What the endpoint actually returned" style={{ width: "100%", marginTop: "9px", resize: "vertical", border: "1px solid #1B2130", borderRadius: "0", background: "#0C1018", color: "#EEF3F8", padding: "12px 13px", font: "400 12.5px/1.65 'Geist Mono', ui-monospace, monospace", outline: "none" } as React.CSSProperties} className="rc-focus-1" /> </div> <button type="button" onClick={v.submit} style={v.submitStyle}>{v.submitLabel}</button> <p style={{ marginTop: "11px", font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.12em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Three strings in, one verdict out. Command or control and enter submits</p> </div> <div style={{ flex: "1 1 340px", minWidth: "0", display: "flex", flexDirection: "column", gap: "12px" } as React.CSSProperties}> <div style={{ border: "1px solid #1B2130", borderRadius: "0", background: "#0E1119", padding: "clamp(18px, 2.4vw, 24px)", flex: "1 1 auto" } as React.CSSProperties}> <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "10px" } as React.CSSProperties}> <span style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Verdict</span> <span style={v.stateStyle}>{v.stateLabel}</span> </div> {v.isIdle && (<> <div style={{ padding: "clamp(30px, 5vw, 48px) 0", textAlign: "center" } as React.CSSProperties}> <div style={{ width: "42px", height: "42px", margin: "0 auto", border: "1px dashed #263048", borderRadius: "0" } as React.CSSProperties}> </div> <p style={{ marginTop: "18px", fontFamily: "'Source Serif 4', Georgia, serif", fontSize: "19px", lineHeight: "1.35", color: "#AEB9C8" } as React.CSSProperties}>No case submitted</p> <p style={{ marginTop: "8px", fontSize: "13px", lineHeight: "1.6", color: "#7C8798", maxWidth: "34ch", marginLeft: "auto", marginRight: "auto" } as React.CSSProperties}>Load a committed case or write your own, then submit it for judgment.</p> </div> </>)} {v.isBusy && (<> <div style={{ padding: "22px 0 6px" } as React.CSSProperties}> <span style={{ display: "block", height: "26px", width: "132px", borderRadius: "0", background: "#1B2130", animation: "rc-shimmer 1.5s ease-in-out infinite" } as React.CSSProperties}> </span> <span style={{ display: "block", height: "10px", width: "100%", borderRadius: "3px", background: "#1B2130", marginTop: "22px", animation: "rc-shimmer 1.5s ease-in-out infinite" } as React.CSSProperties}> </span> <span style={{ display: "block", height: "10px", width: "88%", borderRadius: "3px", background: "#1B2130", marginTop: "10px", animation: "rc-shimmer 1.5s ease-in-out infinite" } as React.CSSProperties}> </span> <span style={{ display: "block", height: "10px", width: "54%", borderRadius: "3px", background: "#1B2130", marginTop: "10px", animation: "rc-shimmer 1.5s ease-in-out infinite" } as React.CSSProperties}> </span> <div style={{ position: "relative", marginTop: "26px", height: "2px", background: "#1B2130", overflow: "hidden" } as React.CSSProperties}> <span style={{ position: "absolute", inset: "0", width: "40%", background: "linear-gradient(90deg, transparent, #22D3EE, transparent)", animation: "rc-sweep 1.4s ease-in-out infinite" } as React.CSSProperties}> </span> </div> <p style={{ marginTop: "14px", font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.12em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Reading the three frozen strings</p> </div> </>)} {v.isDone && (<> <div style={{ paddingTop: "20px", animation: "rc-rise 0.24s ease both" } as React.CSSProperties}> <span style={v.verdictStyle}>{v.verdict}</span> <p style={{ marginTop: "18px", fontFamily: "'Source Serif 4', Georgia, serif", fontSize: "clamp(17px, 2.4vw, 21px)", lineHeight: "1.45", color: "#EEF3F8" } as React.CSSProperties}>{v.reason}</p> <div style={{ marginTop: "22px", borderTop: "1px solid #1B2130" } as React.CSSProperties}> <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "12px", padding: "12px 0", borderBottom: "1px solid #151A25" } as React.CSSProperties}> <span style={{ font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Time to verdict</span> <span style={{ font: "500 13px 'Geist Mono', ui-monospace, monospace", color: "#EEF3F8", fontVariantNumeric: "tabular-nums" } as React.CSSProperties}>{v.elapsed}</span> </div> <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "12px", padding: "12px 0", borderBottom: "1px solid #151A25" } as React.CSSProperties}> <span style={{ font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Committed expectation</span> <span style={{ font: "500 13px 'Geist Mono', ui-monospace, monospace", color: v.expectedColor } as React.CSSProperties}>{v.expected}</span> </div> <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "12px", padding: "12px 0" } as React.CSSProperties}> <span style={{ font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Recorded on chain</span> <span style={{ font: "500 13px 'Geist Mono', ui-monospace, monospace", color: "#7C8798" } as React.CSSProperties}>no</span> </div> </div> </div> </>)} {v.isError && (<> <div style={{ padding: "26px 0 6px" } as React.CSSProperties}> <span style={{ display: "inline-flex", alignItems: "center", gap: "7px", font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.12em", textTransform: "uppercase", color: "#D9A441", border: "1px solid rgba(217,165,65,0.4)", borderRadius: "0", padding: "5px 11px" } as React.CSSProperties}>Not judged</span> <p style={{ marginTop: "16px", fontSize: "14px", lineHeight: "1.6", color: "#AEB9C8" } as React.CSSProperties}>{v.errorText}</p> <button type="button" onClick={v.submit} style={{ marginTop: "18px", height: "38px", padding: "0 16px", borderRadius: "0", border: "1px solid #263048", background: "#0C1018", color: "#EEF3F8", cursor: "pointer", font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.04em", textTransform: "uppercase" } as React.CSSProperties}>Try again</button> </div> </>)} </div> <div style={{ border: "1px solid #1B2130", borderRadius: "0", background: "#0C1018", padding: "clamp(18px, 2.4vw, 24px)" } as React.CSSProperties}> <div style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>The one question a validator answers</div> <p style={{ marginTop: "12px", fontFamily: "'Source Serif 4', Georgia, serif", fontSize: "17px", lineHeight: "1.45", color: "#EEF3F8" } as React.CSSProperties}>Did this response honor that promise, for this request?</p> <div style={{ display: "flex", flexWrap: "wrap", gap: "7px", marginTop: "16px" } as React.CSSProperties}> <span style={{ display: "inline-flex", alignItems: "center", font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.12em", textTransform: "uppercase", color: "#05191F", background: "#22D3EE", borderRadius: "0", padding: "5px 10px" } as React.CSSProperties}>Honored</span> <span style={{ display: "inline-flex", alignItems: "center", font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.12em", textTransform: "uppercase", color: "#F87171", background: "rgba(248,113,113,0.10)", border: "1px solid rgba(248,113,113,0.35)", borderRadius: "0", padding: "5px 10px" } as React.CSSProperties}>Not honored</span> <span style={{ display: "inline-flex", alignItems: "center", font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.12em", textTransform: "uppercase", color: "#AEB9C8", border: "1px dashed #263048", borderRadius: "0", padding: "5px 10px" } as React.CSSProperties}>Unclear</span> </div> <div style={{ marginTop: "18px", borderTop: "1px solid #1B2130", paddingTop: "16px", display: "grid", gap: "9px" } as React.CSSProperties}> <p style={{ fontSize: "13px", lineHeight: "1.6", color: "#AEB9C8" } as React.CSSProperties}>Field ordering is ignored. Extra undocumented fields do not break a promise, because the promise sets a floor and not a ceiling.</p> <p style={{ fontSize: "13px", lineHeight: "1.6", color: "#AEB9C8" } as React.CSSProperties}>Nothing is read from the live internet. The judge sees only the three strings, frozen at the moment the case was opened.</p> <p style={{ fontSize: "13px", lineHeight: "1.6", color: "#AEB9C8" } as React.CSSProperties}>A promise with nothing measurable in it produces unclear, rather than a standard the seller never agreed to.</p> </div> </div> </div> </div> </>)}  <div style={{ marginTop: "clamp(48px, 7vw, 76px)", display: "flex", alignItems: "center", gap: "14px" } as React.CSSProperties}> <span style={{ font: "500 10.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.16em", textTransform: "uppercase", color: "#22D3EE", whiteSpace: "nowrap" } as React.CSSProperties}>Integration</span> <span style={{ height: "1px", flex: "1", background: "#1B2130" } as React.CSSProperties}> </span> </div> <h2 style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: "600", fontSize: "clamp(26px, 3.6vw, 38px)", lineHeight: "1.1", letterSpacing: "-0.025em", marginTop: "16px", maxWidth: "24ch" } as React.CSSProperties}>One wrapper, <em style={{ fontStyle: "italic", color: "#EEF3F8" } as React.CSSProperties}>no rewrite</em> </h2> <p style={{ marginTop: "16px", fontSize: "15.5px", lineHeight: "1.65", color: "#AEB9C8", maxWidth: "66ch" } as React.CSSProperties}>A selling endpoint keeps its handler and publishes a promise. A buying agent keeps its call and gains the ability to contest it. Neither side changes how the money moves.</p> <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", marginTop: "clamp(24px, 3vw, 32px)" } as React.CSSProperties}> <div style={{ flex: "1 1 330px", minWidth: "0", border: "1px solid #1B2130", borderRadius: "0", background: "#0E1119", padding: "clamp(18px, 2.4vw, 24px)" } as React.CSSProperties}> <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "10px" } as React.CSSProperties}> <span style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8" } as React.CSSProperties}>Selling endpoint</span> <span style={{ font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.12em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>publishes a promise</span> </div> <pre style={{ margin: "15px 0 0", padding: "15px", background: "#0C1018", border: "1px solid #151A25", borderRadius: "0", font: "400 11.5px/1.8 'Geist Mono', ui-monospace, monospace", color: "#AEB9C8", whiteSpace: "pre-wrap", wordBreak: "break-word" } as React.CSSProperties}> <span style={{ color: "#7C8798" } as React.CSSProperties}>recourse</span>.serve(&#123;
  promise: <span style={{ color: "#22D3EE" } as React.CSSProperties}>"Spot price for the requested pair,</span> <span style={{ color: "#22D3EE" } as React.CSSProperties}>    three venues, under five seconds."</span>,
  price: <span style={{ color: "#22D3EE" } as React.CSSProperties}>"0.01 USDC"</span>,
  handler<span style={{ color: "#7C8798" } as React.CSSProperties}>,</span>
&#125;)</pre> <p style={{ marginTop: "13px", fontSize: "13.5px", lineHeight: "1.6", color: "#AEB9C8" } as React.CSSProperties}>The promise is the only new thing the seller writes. It is what the judge will be handed, so vagueness costs the seller its own protection.</p> </div> <div style={{ flex: "1 1 330px", minWidth: "0", border: "1px solid #1B2130", borderRadius: "0", background: "#0E1119", padding: "clamp(18px, 2.4vw, 24px)" } as React.CSSProperties}> <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "10px" } as React.CSSProperties}> <span style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8" } as React.CSSProperties}>Buying agent</span> <span style={{ font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.12em", textTransform: "uppercase", color: "#22D3EE" } as React.CSSProperties}>gains a dispute right</span> </div> <pre style={{ margin: "15px 0 0", padding: "15px", background: "#0C1018", border: "1px solid #151A25", borderRadius: "0", font: "400 11.5px/1.8 'Geist Mono', ui-monospace, monospace", color: "#AEB9C8", whiteSpace: "pre-wrap", wordBreak: "break-word" } as React.CSSProperties}> <span style={{ color: "#7C8798" } as React.CSSProperties}>const</span> res = <span style={{ color: "#7C8798" } as React.CSSProperties}>await</span> recourse.pay(url, params)

<span style={{ color: "#7C8798" } as React.CSSProperties}>// the response arrived with no added latency</span> <span style={{ color: "#7C8798" } as React.CSSProperties}>if</span> (!res.satisfies(promise))
  <span style={{ color: "#7C8798" } as React.CSSProperties}>await</span> res.<span style={{ color: "#22D3EE" } as React.CSSProperties}>contest</span>()</pre> <p style={{ marginTop: "13px", fontSize: "13.5px", lineHeight: "1.6", color: "#AEB9C8" } as React.CSSProperties}>One call to contest, inside the hold window. The bond is fixed when the escrow is deployed and is forfeit when the response is ruled honored, so contesting everything is not free.</p> </div> </div> <div style={{ marginTop: "12px", border: "1px solid #1B2130", borderRadius: "0", background: "#0C1018", padding: "clamp(18px, 2.4vw, 24px)" } as React.CSSProperties}> <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "12px" } as React.CSSProperties}> <span style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Read the judge prompt your agent will be held to</span> <span style={{ font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.12em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>version pinned per case</span> </div> <div style={{ display: "flex", alignItems: "center", gap: "12px", marginTop: "14px", border: "1px solid #1B2130", borderRadius: "0", background: "#0A0C12", padding: "13px 15px" } as React.CSSProperties}> <span style={{ font: "500 12.5px 'Geist Mono', ui-monospace, monospace", color: "#22D3EE", flex: "0 0 auto" } as React.CSSProperties}>$</span> <code style={{ flex: "1 1 auto", minWidth: "0", font: "400 12.5px 'Geist Mono', ui-monospace, monospace", color: "#AEB9C8", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } as React.CSSProperties}>{v.curlCmd}</code> <button type="button" onClick={v.copyCurl} style={{ flex: "0 0 auto", background: "transparent", border: "0", padding: "0", cursor: "pointer", font: "500 9.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.04em", color: v.curlNoteColor } as React.CSSProperties}>{v.curlNote}</button> </div> <p style={{ marginTop: "12px", fontSize: "13.5px", lineHeight: "1.6", color: "#AEB9C8", maxWidth: "78ch" } as React.CSSProperties}>The prompt is the contract. It is committed to the repository, pinned per case, and handed to every validator unchanged, so a seller can read exactly what it will be judged against before it publishes a promise.</p> </div> </div>
    </>
  );
}
