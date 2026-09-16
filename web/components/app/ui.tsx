"use client";

/**
 * The pieces both tiers of /app share: the tokens from docs/DESIGN.md, the
 * step list that collapses a finished step to one line with a tick, links to
 * the explorer, and the settlement notice that is shown before anyone pays.
 */

import type { ReactNode } from "react";

import type { Check, Mode } from "@/lib/quote";
import { MODES } from "@/lib/quote";

export const T = {
  ground: "#0A0C12",
  panel: "#0E1119",
  inset: "#0C1018",
  line: "#1B2130",
  strong: "#263048",
  ink: "#EEF3F8",
  body: "#AEB9C8",
  muted: "#7C8798",
  accent: "#22D3EE",
  pass: "#4ADE80",
  fail: "#F87171",
  amber: "#D9A441",
  serif: "'Source Serif 4', Georgia, serif",
  sans: "'Work Sans', ui-sans-serif, system-ui, sans-serif",
  mono: "'Geist Mono', ui-monospace, monospace",
  radius: "4px",
};

export const short = (value: string) => (value && value.length > 12 ? `${value.slice(0, 6)}...${value.slice(-4)}` : value);

export function TxLink({ explorer, hash }: { explorer: string; hash: string }) {
  return (
    <a href={`${explorer}/tx/${hash}`} target="_blank" rel="noreferrer" style={{ font: `500 12px ${T.mono}`, color: T.accent, wordBreak: "break-all" }}>
      {hash}
    </a>
  );
}

export function Panel({ children, style }: { children: ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ border: `1px solid ${T.line}`, borderRadius: T.radius, background: T.panel, padding: "clamp(16px, 3vw, 22px)", minWidth: 0, ...style }}>
      {children}
    </div>
  );
}

export function Label({ children, color }: { children: ReactNode; color?: string }) {
  return <div style={{ font: `500 10px ${T.mono}`, letterSpacing: "0.14em", textTransform: "uppercase", color: color ?? T.muted }}>{children}</div>;
}

export type StepState = "waiting" | "active" | "done" | "failed" | "skipped";

export type StepView = { key: string; title: string; state: StepState; summary?: ReactNode; detail?: ReactNode };

/** One row per step. Done collapses to a single line with a tick; the active step shows its detail. */
export function Steps({ steps }: { steps: StepView[] }) {
  return (
    <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: "8px" }}>
      {steps.map((step, index) => {
        const mark = step.state === "done" ? "✓" : step.state === "failed" ? "×" : step.state === "skipped" ? "-" : String(index + 1);
        const tone = step.state === "done" ? T.pass : step.state === "failed" ? T.fail : step.state === "active" ? T.accent : T.muted;
        // A finished step stays open: its hash, the promise and the checks are the
        // evidence, and a visitor reads them after the run as much as during it.
        const open = step.state !== "waiting";
        return (
          <li key={step.key} style={{ border: `1px solid ${step.state === "active" ? "rgba(34,211,238,0.35)" : T.line}`, borderRadius: T.radius, background: T.inset, padding: "10px 12px", minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: "10px", minWidth: 0 }}>
              <span aria-hidden="true" style={{ font: `600 12px ${T.mono}`, color: tone, flex: "0 0 16px" }}>{mark}</span>
              <span style={{ font: `500 13px ${T.sans}`, color: step.state === "waiting" ? T.muted : T.ink, flex: "0 0 auto" }}>{step.title}</span>
              {step.summary ? <span style={{ font: `400 12px ${T.mono}`, color: T.body, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{step.summary}</span> : null}
            </div>
            {open && step.detail ? <div style={{ marginTop: "10px", paddingLeft: "26px", minWidth: 0 }}>{step.detail}</div> : null}
          </li>
        );
      })}
    </ol>
  );
}

export function ChecksView({ response, checks, receivedAt }: { response: string; checks: Check[]; receivedAt: string }) {
  return (
    <div style={{ display: "grid", gap: "10px", minWidth: 0 }}>
      <pre style={{ margin: 0, padding: "10px 12px", border: `1px solid ${T.line}`, borderRadius: T.radius, background: T.ground, color: T.body, font: `400 12px/1.6 ${T.mono}`, whiteSpace: "pre-wrap", wordBreak: "break-all" }}>{response}</pre>
      {/* The CLI seller signs with a key read from .accounts.json on the machine running it. That key is not on this server, so the response both tiers freeze is unsigned. */}
      <div style={{ font: `400 12px ${T.mono}`, color: T.amber }}>Signed by nothing - this demo seller holds no key on this server, unlike a real seller.</div>
      <div style={{ font: `400 11px ${T.mono}`, color: T.muted }}>received {receivedAt.replace("T", " ").replace(/\.\d+Z$/, " UTC")}</div>
      <div style={{ display: "grid", gap: "6px" }}>
        {checks.map((one) => (
          <div key={one.name} style={{ display: "flex", flexWrap: "wrap", gap: "4px 10px", alignItems: "baseline" }}>
            <span style={{ font: `600 11px ${T.mono}`, letterSpacing: "0.08em", textTransform: "uppercase", color: one.pass ? T.pass : T.fail, flex: "0 0 92px" }}>
              {one.pass ? "pass" : "fail"} {one.name}
            </span>
            <span style={{ font: `400 12.5px ${T.mono}`, color: T.ink }}>{one.detail}</span>
          </div>
        ))}
      </div>
      <p style={{ margin: 0, font: `400 12.5px/1.6 ${T.sans}`, color: T.muted }}>Three deterministic checks, no model. The judgment itself belongs to the committee.</p>
    </div>
  );
}

export function ModePicker({ mode, onChange, disabled }: { mode: Mode; onChange: (mode: Mode) => void; disabled?: boolean }) {
  return (
    <div>
      <Label>What the demo seller returns</Label>
      <div role="radiogroup" style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "8px" }}>
        {MODES.map((one) => (
          <button
            key={one}
            type="button"
            role="radio"
            aria-checked={mode === one}
            disabled={disabled}
            onClick={() => onChange(one)}
            style={{
              minHeight: "34px",
              padding: "0 12px",
              borderRadius: T.radius,
              border: `1px solid ${mode === one ? "rgba(34,211,238,0.45)" : T.line}`,
              background: mode === one ? "rgba(34,211,238,0.08)" : T.inset,
              color: mode === one ? T.accent : T.body,
              font: `500 12px ${T.mono}`,
              cursor: disabled ? "not-allowed" : "pointer",
            }}
          >
            {one}
          </button>
        ))}
      </div>
      <p style={{ margin: "8px 0 0", font: `400 12.5px/1.6 ${T.sans}`, color: T.muted }}>
        This is a demo seller that can be told to misbehave. A real seller would not offer the choice.
      </p>
    </div>
  );
}

/** Shown before any payment, in the pay card, never after it. */
export function SettlementNotice({ amountGen, bondGen }: { amountGen: string; bondGen: string }) {
  return (
    <div role="note" style={{ border: "1px solid rgba(217,165,65,0.35)", borderRadius: T.radius, background: "rgba(217,165,65,0.05)", padding: "12px 14px" }}>
      <Label color={T.amber}>Before you pay: the money does not move on this network</Label>
      <p style={{ margin: "8px 0 0", font: `400 13.5px/1.65 ${T.sans}`, color: T.body }}>
        The payment, the checks, the committee&apos;s vote, the verdict and the record are all real here. What does not happen on Studio Next is the
        settlement: consensus v0.6 funds a value transfer only at the root of a transaction&apos;s fee allocation, and the payout sits two messages below
        the transaction that pays for it. So a {amountGen} GEN payment and a {bondGen} GEN bond stay in the escrow even when the verdict goes your way. The
        verdict is final before the transfer is ever attempted, so it stands either way, and on a network where that transfer is funded the same
        transaction pays out.
      </p>
    </div>
  );
}

export function Button({ children, onClick, disabled, kind = "primary" }: { children: ReactNode; onClick?: () => void; disabled?: boolean; kind?: "primary" | "quiet" }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      style={{
        minHeight: "44px",
        padding: "0 18px",
        borderRadius: T.radius,
        border: `1px solid ${kind === "primary" ? "rgba(34,211,238,0.5)" : T.strong}`,
        background: kind === "primary" ? (disabled ? "transparent" : "rgba(34,211,238,0.08)") : T.inset,
        color: disabled ? T.muted : kind === "primary" ? T.accent : T.ink,
        font: `500 13px ${T.mono}`,
        letterSpacing: "0.04em",
        cursor: disabled ? "not-allowed" : "pointer",
      }}
    >
      {children}
    </button>
  );
}
