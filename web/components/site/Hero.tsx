"use client";

/**
 * The hero, ported from the canvas: the lane animation, the promise linter,
 * and the strip of chain totals along the foot of the panel.
 *
 * The canvas shipped its linter disabled and labelled "Live site only",
 * because a design canvas has no backend. Here it posts to /api/lint, which is
 * the one linter service, and shows the three states the panel is allowed to
 * have: judgeable, not judgeable, or it could not be reached. Nothing is
 * decided in this file.
 *
 * The totals come from the same chain read the feed uses, so the number in the
 * hero and the number in the table can never disagree. Before that read
 * returns they are dashes, never zeros.
 */

import { useEffect, useRef, useState } from "react";

import LaneCanvas from "./LaneCanvas";

type Stats = {
  payments: string;
  disputes: string;
  upheld: string;
  median: string;
};

type LintResult = {
  judgeable: boolean;
  reason: string;
  failed_check: string | null;
  suggestion: string | null;
  stage: 1 | 2;
};

export default function Hero({
  stats,
  escrow,
  dispute,
  explorer,
}: {
  stats: Stats;
  escrow: string;
  dispute: string;
  explorer: string;
}) {
  const [vw, setVw] = useState(1280);
  const [laneFallback, setLaneFallback] = useState(false);
  const [text, setText] = useState("");
  const [status, setStatus] = useState<"idle" | "busy" | "done" | "error">("idle");
  const [result, setResult] = useState<LintResult | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState("");
  const [sugCopied, setSugCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const onResize = () => {
      const w = window.innerWidth || document.documentElement.clientWidth || 0;
      if (w > 0) setVw(w);
    };
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const short = (a: string) => (a && a.length > 12 ? `${a.slice(0, 6)}...${a.slice(-4)}` : a || "-");
  const escrowShort = short(escrow);
  const disputeShort = short(dispute);

  function flash(which: string) {
    setCopied(which);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setCopied(""), 1200);
  }

  async function lint() {
    const promise = text.trim();
    if (!promise || status === "busy") return;
    setStatus("busy");
    setError("");
    // Stage 2 can take a while. Forever is not a state, so the wait has a ceiling.
    const controller = new AbortController();
    const ceiling = setTimeout(() => controller.abort(), 210_000);
    try {
      const response = await fetch("/api/lint", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ promise }),
        signal: controller.signal,
      });
      const payload = (await response.json()) as LintResult & { error?: string };
      if (!response.ok || payload.error) {
        setStatus("error");
        setError(
          response.status === 429
            ? "Too many checks in the last minute. Try again shortly."
            : payload.error
              ? `Could not reach the linter. ${payload.error}`
              : "Could not reach the linter. Try again.",
        );
        return;
      }
      setResult(payload);
      setStatus("done");
    } catch {
      setStatus("error");
      setError("Could not reach the linter. Try again.");
    } finally {
      clearTimeout(ceiling);
    }
  }

  const busy = status === "busy";
  const done = status === "done" && result !== null;
  const wide = vw > 720;
  const v = {
    laneFallbackDisplay: laneFallback ? "block" : "none",
    goGap: (e: React.MouseEvent) => {
      e.preventDefault();
      const el = document.getElementById("gap");
      if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 72, behavior: "smooth" });
    },
    scrim: !wide
      ? "linear-gradient(to bottom, rgba(10,12,18,0.55) 0%, rgba(10,12,18,0.3) 28%, rgba(10,12,18,0.88) 100%)"
      : "linear-gradient(to right, transparent 0%, transparent 42%, rgba(10,12,18,0.55) 70%, rgba(10,12,18,0.86) 100%), linear-gradient(to bottom, rgba(10,12,18,0.6) 0%, transparent 20%, transparent 100%)",
    heroJustify: !wide ? "center" : "flex-end",
    panelWidth: !wide ? "100%" : vw <= 1100 ? "min(72vw, 540px)" : "min(36vw, 640px)",
    panelMin: vw <= 1100 ? "0" : "400px",
    h1Size: vw <= 380 ? "clamp(42px, 14vw, 62px)" : "clamp(52px, 6vw, 112px)",
    lintText: text,
    lintRows: Math.min(6, Math.max(3, text.split("\n").length + Math.floor(text.length / 70))),
    lintChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setText(e.target.value.slice(0, 600));
      setSugCopied(false);
    },
    lintKey: (e: React.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        void lint();
      }
    },
    lintSubmit: (e: React.FormEvent) => {
      e.preventDefault();
      void lint();
    },
    lintBorder: "rgba(255,255,255,0.20)",
    counter: `${text.length} / 500`,
    counterColor: (text.length > 0 && text.length < 20) || text.length > 500 ? "#22D3EE" : "#7C8798",
    lintDisabled: busy || !text.trim(),
    lintButtonLabel: busy ? "Checking" : "Is this judgeable?",
    lintButtonColor: text.trim() ? "#EEF3F8" : "#4A5468",
    lintCursor: text.trim() ? (busy ? "wait" : "pointer") : "not-allowed",
    lintHoverBg: text.trim() ? "rgba(255,255,255,0.16)" : "rgba(255,255,255,0.10)",
    lintLoadingDisplay: busy ? "block" : "none",
    resultDisplay: done || status === "error" ? "block" : "none",
    resultOpacity: done || status === "error" ? "1" : "0",
    resultY: done || status === "error" ? "0px" : "10px",
    lintPass: done && result!.judgeable,
    lintFail: done && !result!.judgeable,
    lintError: status === "error",
    lintOffline: status === "error" && error.includes("linter not configured"),
    lintReason: done ? result!.reason : error,
    lintSuggestion: done ? result!.suggestion || "" : "",
    // linter/service.py promises every consumer says this. The gate on chain
    // asks a committee; stage 2 here asks one model, and must say so.
    lintStage: done
      ? result!.stage === 2
        ? "Stage 2 of the linter: the deployed gate's question, put to one model. A dry run, not the gate's verdict."
        : "Stage 1 of the linter: deterministic, free."
      : "",
    copySuggestion: () => {
      const suggestion = result?.suggestion || "";
      if (suggestion) navigator.clipboard?.writeText(suggestion);
      setSugCopied(true);
      setTimeout(() => setSugCopied(false), 1600);
    },
    copySugLabel: sugCopied ? "Copied" : "Copy",
    copySugColor: sugCopied ? "#22D3EE" : "#7C8798",
    statColor: "#7C8798",
    statPayments: stats.payments,
    statDisputes: stats.disputes,
    statUpheld: stats.upheld,
    statMedian: stats.median,
    copyEscrow: () => {
      navigator.clipboard?.writeText(escrow);
      flash("escrow");
    },
    copyDispute: () => {
      navigator.clipboard?.writeText(dispute);
      flash("dispute");
    },
    escrowTipOp: copied === "escrow" ? "1" : "0",
    disputeTipOp: copied === "dispute" ? "1" : "0",
    repoUrl: "https://github.com/meitipro/Recourse",
    explorer,
  };

  return (
    <>
    <section id="hero" style={{ position: "relative", isolation: "isolate", overflow: "hidden", minHeight: "max(calc(100svh - 72px), 640px)", display: "grid", gridTemplateRows: "minmax(0, 1fr) auto auto", background: "#0A0C12" } as React.CSSProperties}> <div aria-hidden="true" style={{ position: "absolute", inset: "0", zIndex: "0", background: "transparent" } as React.CSSProperties}> </div> <div aria-hidden="true" style={{ position: "absolute", inset: "0", zIndex: "0" }}><LaneCanvas onFallback={setLaneFallback} /></div> <div aria-hidden="true" style={{ position: "absolute", inset: "0", zIndex: "0", display: v.laneFallbackDisplay } as React.CSSProperties}> <svg width="100%" height="100%" preserveAspectRatio="none" style={{ position: "absolute", inset: "0", display: "block" } as React.CSSProperties}> <defs> <pattern id="rc-ticks" x="0" y="0" width={56} height="100%" patternUnits="userSpaceOnUse"> <rect x="0" y="0" width={1} height={72} fill="rgba(70,84,104,0.78)"> </rect> </pattern> </defs> <rect x="0" y="0" width="100%" height={72} fill="url(#rc-ticks)" style={{ transform: "translateY(calc(58% - 72px))" } as React.CSSProperties}> </rect> <rect x="0" y="58%" width="100%" height={1} fill="#1B2130"> </rect> <rect x="50%" y="58%" width={1} height={150} fill="#22D3EE" style={{ transform: "translateY(-150px)" } as React.CSSProperties}> </rect> <rect x="50%" y="58%" width={1} height={58} fill="#22D3EE"> </rect> <text x="50%" y="58%" dy="74" textAnchor="middle" fill="#22D3EE" fontFamily="Geist Mono, ui-monospace, monospace" fontSize="10" fontWeight="500" letterSpacing="2">RETURNED</text> </svg> </div> <div aria-hidden="true" style={{ position: "absolute", inset: "0", zIndex: "0", pointerEvents: "none", background: v.scrim } as React.CSSProperties}> </div> <div style={{ position: "relative", zIndex: "1", display: "flex", alignItems: "center", justifyContent: v.heroJustify, padding: "clamp(36px, 5vw, 72px) clamp(20px, 5vw, 100px)", minHeight: "0" } as React.CSSProperties}> <div style={{ width: v.panelWidth, minWidth: v.panelMin, maxWidth: "100%", display: "flex", flexDirection: "column", alignItems: "flex-start" } as React.CSSProperties}> <span style={{ display: "inline-block", font: "500 clamp(10px, 0.7vw, 13px)/1 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace", letterSpacing: "0.2em", textTransform: "uppercase", color: "#AEB9C8", border: "1px solid #263048", padding: "clamp(8px, 0.7vw, 12px) clamp(13px, 1vw, 18px)", whiteSpace: "nowrap" } as React.CSSProperties}>Promise linter</span> <h1 style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: "400", fontSize: v.h1Size, letterSpacing: "0.01em", lineHeight: "0.95", marginTop: "clamp(26px, 3vw, 48px)", color: "#EEF3F8" } as React.CSSProperties}>RECOURSE</h1> <p style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: "400", fontSize: "clamp(17px, 1.5vw, 26px)", lineHeight: "1.35", color: "#AEB9C8", marginTop: "clamp(14px, 1.4vw, 22px)" } as React.CSSProperties}>A promise that costs something to break.</p> <p style={{ fontFamily: "'Work Sans', system-ui, sans-serif", fontWeight: "400", fontSize: "clamp(13px, 0.95vw, 16px)", lineHeight: "1.55", color: "#7C8798", maxWidth: "46ch", marginTop: "clamp(10px, 1vw, 16px)" } as React.CSSProperties}>Agents can spend money in milliseconds. Nothing in the stack lets them get it back.</p> <form noValidate={true} onSubmit={v.lintSubmit} style={{ marginTop: "clamp(30px, 3.6vw, 60px)", display: "flex", flexDirection: "column", gap: "clamp(12px, 1.1vw, 18px)", width: "100%" } as React.CSSProperties}> <div style={{ position: "relative" } as React.CSSProperties}> <label htmlFor="rc-promise" style={{ position: "absolute", width: "1px", height: "1px", overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap" } as React.CSSProperties}>Your delivery promise</label> <textarea id="rc-promise" rows={v.lintRows} maxLength={600} value={v.lintText} onChange={v.lintChange} onKeyDown={v.lintKey} placeholder="Paste what your API promises to deliver. For example: prices aggregated from at least three venues, refreshed within five seconds." style={{ display: "block", width: "100%", background: "transparent", border: "0", borderBottom: `1px solid ${v.lintBorder}`, borderRadius: "0", padding: "0 2px clamp(11px, 1vw, 16px)", fontFamily: "'Work Sans', system-ui, sans-serif", fontWeight: "400", fontSize: "clamp(15px, 0.95vw, 17px)", lineHeight: "1.5", color: "#EEF3F8", resize: "none", outline: "none", transition: "border-color 0.25s ease" } as React.CSSProperties} className="rc-focus-3" /> <div aria-hidden="true" style={{ display: "flex", justifyContent: "flex-end", marginTop: "6px", font: "400 10px 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace", color: v.counterColor, fontVariantNumeric: "tabular-nums" } as React.CSSProperties}>{v.counter}</div> </div> <button type="submit" disabled={v.lintDisabled} style={{ position: "relative", overflow: "hidden", width: "100%", border: "0", borderRadius: "0", padding: "clamp(15px, 1.5vw, 24px) 20px", background: "rgba(255,255,255,0.10)", color: v.lintButtonColor, cursor: v.lintCursor, font: "500 clamp(10px, 0.76vw, 13px) 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace", letterSpacing: "0.04em", transition: "background 0.25s ease" } as React.CSSProperties} className="rc-hover-4">{v.lintButtonLabel}<span aria-hidden="true" style={{ position: "absolute", left: "0", bottom: "0", height: "1px", width: "40%", background: "#22D3EE", display: v.lintLoadingDisplay, animation: "rc-sweep 1.2s linear infinite" } as React.CSSProperties}> </span> </button> <div style={{ display: "flex", flexWrap: "wrap", gap: "clamp(20px, 2vw, 34px)", marginTop: "clamp(6px, 0.6vw, 10px)" } as React.CSSProperties}> <a href="#feed" style={{ font: "500 clamp(10px, 0.72vw, 13px) 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace", letterSpacing: "0.18em", textTransform: "uppercase", color: "#7C8798", textUnderlineOffset: "4px", transition: "color 0.25s ease" } as React.CSSProperties} className="rc-hover-5">Live verdicts</a> <a href={v.repoUrl} target="_blank" rel="noreferrer" style={{ font: "500 clamp(10px, 0.72vw, 13px) 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace", letterSpacing: "0.18em", textTransform: "uppercase", color: "#7C8798", textUnderlineOffset: "4px", transition: "color 0.25s ease" } as React.CSSProperties} className="rc-hover-5">Repository</a> </div> </form> <div role="status" aria-live="polite" style={{ width: "100%", marginTop: "clamp(16px, 1.4vw, 22px)", opacity: v.resultOpacity, transform: `translateY(${v.resultY})`, transition: "opacity 0.4s cubic-bezier(0.16, 1, 0.3, 1), transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)", display: v.resultDisplay } as React.CSSProperties}> {v.lintPass && (<> <div style={{ borderLeft: "2px solid #22D3EE", background: "#0E1119", padding: "clamp(14px, 1.2vw, 20px)" } as React.CSSProperties}> <div style={{ font: "500 11px 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace", letterSpacing: "0.18em", textTransform: "uppercase", color: "#22D3EE" } as React.CSSProperties}>Judgeable</div> <p style={{ marginTop: "10px", fontFamily: "'Work Sans', system-ui, sans-serif", fontWeight: "400", fontSize: "14.5px", lineHeight: "1.55", color: "#AEB9C8" } as React.CSSProperties}>{v.lintReason}</p> <p style={{ marginTop: "10px", font: "400 10.5px 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace", letterSpacing: "0.08em", color: "#7C8798" } as React.CSSProperties}>A response could be ruled against this.</p> </div> </>)} {v.lintFail && (<> <div style={{ borderLeft: "2px solid rgba(232,179,102,0.7)", background: "#0E1119", padding: "clamp(14px, 1.2vw, 20px)" } as React.CSSProperties}> <div style={{ font: "500 11px 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace", letterSpacing: "0.18em", textTransform: "uppercase", color: "#E8B366" } as React.CSSProperties}>Not judgeable</div> <p style={{ marginTop: "10px", fontFamily: "'Work Sans', system-ui, sans-serif", fontWeight: "400", fontSize: "14.5px", lineHeight: "1.55", color: "#AEB9C8" } as React.CSSProperties}>{v.lintReason}</p> {v.lintSuggestion && (<><div style={{ position: "relative", marginTop: "12px", background: "#0C1018", padding: "12px 14px", paddingRight: "74px" } as React.CSSProperties}> <p style={{ font: "400 12.5px/1.6 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace", color: "#EEF3F8", userSelect: "text", wordBreak: "break-word" } as React.CSSProperties}>{v.lintSuggestion}</p> <button type="button" onClick={v.copySuggestion} style={{ position: "absolute", top: "10px", right: "12px", background: "transparent", border: "0", padding: "4px 0", cursor: "pointer", font: "500 10px 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace", letterSpacing: "0.04em", color: v.copySugColor } as React.CSSProperties}>{v.copySugLabel}</button> </div></>)} </div> </>)} {v.lintStage && (<p style={{ marginTop: "10px", font: "400 10px 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace", letterSpacing: "0.06em", color: "#7C8798" } as React.CSSProperties}>{v.lintStage}</p>)} {v.lintError && (<> <p style={{ font: "400 12.5px 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace", color: "#7C8798" } as React.CSSProperties}>{v.lintOffline ? "This copy of the site has no linter behind it, so nothing can be judged here. The feed and the evaluation do not need one." : v.lintReason}</p> </>)} <p style={{ marginTop: "10px", font: "400 10px 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace", letterSpacing: "0.06em", color: "#7C8798" } as React.CSSProperties}>Nothing you paste here is stored. It is sent to the judge once and discarded.</p> </div> </div> </div> <div style={{ position: "relative", zIndex: "1", display: "flex", justifyContent: "center", paddingBottom: "24px" } as React.CSSProperties}> <button type="button" onClick={v.goGap} aria-label="Scroll to the gap" style={{ background: "transparent", border: "0", padding: "0", cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: "10px" } as React.CSSProperties}> <span aria-hidden="true" style={{ display: "block", width: "1px", height: "28px", background: "rgba(255,255,255,0.20)" } as React.CSSProperties}> </span> <span style={{ font: "400 9px 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace", letterSpacing: "0.2em", color: "#7C8798" } as React.CSSProperties}>THE GAP</span> </button> </div> <div style={{ position: "relative", zIndex: "1", borderTop: "1px solid rgba(255,255,255,0.09)", padding: "clamp(14px, 1.4vw, 24px) clamp(20px, 5vw, 100px)", display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "12px 24px", font: "400 clamp(10px, 0.72vw, 12px) 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace", letterSpacing: "0.1em", textTransform: "uppercase" } as React.CSSProperties}> <span style={{ color: "#7C8798", whiteSpace: "nowrap" } as React.CSSProperties}>Adjudicated on GenLayer</span> <span style={{ display: "flex", flexWrap: "wrap", gap: "6px 14px", color: "#AEB9C8", fontVariantNumeric: "tabular-nums" } as React.CSSProperties}> <span> <span style={{ color: v.statColor } as React.CSSProperties}>{v.statPayments}</span> payments</span> <span style={{ color: "#7C8798" } as React.CSSProperties}>-</span> <span> <span style={{ color: v.statColor } as React.CSSProperties}>{v.statDisputes}</span> disputes</span> <span style={{ color: "#7C8798" } as React.CSSProperties}>-</span> <span> <span style={{ color: v.statColor } as React.CSSProperties}>{v.statUpheld}</span> not honored</span> <span style={{ color: "#7C8798" } as React.CSSProperties}>-</span> <span> <span style={{ color: v.statColor } as React.CSSProperties}>{v.statMedian}</span> median, pay to dispute</span> </span> <span style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "6px 14px", color: "#7C8798" } as React.CSSProperties}> <span style={{ position: "relative", display: "inline-flex", alignItems: "center", gap: "8px" } as React.CSSProperties}>Escrow <button type="button" onClick={v.copyEscrow} style={{ background: "transparent", border: "0", padding: "0", cursor: "pointer", font: "inherit", letterSpacing: "inherit", textTransform: "none", color: "#AEB9C8" } as React.CSSProperties}>{escrowShort}</button> <span aria-hidden="true" style={{ position: "absolute", left: "50%", bottom: "calc(100% + 8px)", transform: "translateX(-50%)", font: "500 9px 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace", letterSpacing: "0.16em", color: "#22D3EE", opacity: v.escrowTipOp, transition: "opacity 0.2s ease", whiteSpace: "nowrap", pointerEvents: "none" } as React.CSSProperties}>COPIED</span> </span> <span style={{ color: "#7C8798" } as React.CSSProperties}>-</span> <span style={{ position: "relative", display: "inline-flex", alignItems: "center", gap: "8px" } as React.CSSProperties}>Dispute <button type="button" onClick={v.copyDispute} style={{ background: "transparent", border: "0", padding: "0", cursor: "pointer", font: "inherit", letterSpacing: "inherit", textTransform: "none", color: "#AEB9C8" } as React.CSSProperties}>{disputeShort}</button> <span aria-hidden="true" style={{ position: "absolute", left: "50%", bottom: "calc(100% + 8px)", transform: "translateX(-50%)", font: "500 9px 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace", letterSpacing: "0.16em", color: "#22D3EE", opacity: v.disputeTipOp, transition: "opacity 0.2s ease", whiteSpace: "nowrap", pointerEvents: "none" } as React.CSSProperties}>COPIED</span> </span> </span> </div> </section>
    </>
  );
}
