"use client";

/**
 * The skill.md card: the one line an agent needs, and the way in for someone
 * without one. The shape is Internet Court's card, in this site's tokens.
 *
 * The command is the deployed site's own /skill.md, which serves the skill
 * repository's SKILL.md as text, so what an agent fetches here and what the
 * repository says cannot differ. The person without an agent is sent to
 * Notary, the Telegram bot, which reads the same record.
 */

import { useState } from "react";

export const SITE = "https://recourse-site-seven.vercel.app";
export const SKILL_COMMAND = `curl -s ${SITE}/skill.md`;
export const SKILL_REPO = "https://github.com/meitipro/recourse-skill";
export const NOTARY = "https://t.me/AskRecourseBot";

const MONO = "'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace";
const LABEL = { font: `500 10px ${MONO}`, letterSpacing: "0.16em", textTransform: "uppercase" } as React.CSSProperties;

export default function AgentCard() {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(SKILL_COMMAND);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section aria-labelledby="rc-skill-card" style={{ border: "1px solid #1B2130", borderRadius: "4px", background: "#0E1119", maxWidth: "640px", minWidth: 0 } as React.CSSProperties}>
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "baseline", gap: "8px 16px", padding: "14px 16px", borderBottom: "1px solid #1B2130" } as React.CSSProperties}>
        <h2 id="rc-skill-card" style={{ ...LABEL, margin: 0, color: "#EEF3F8" }}>skill.md</h2>
        <a href={SKILL_REPO} target="_blank" rel="noreferrer" style={{ ...LABEL, color: "#22D3EE", textUnderlineOffset: "4px" }} className="rc-hover-5">
          View on GitHub <span aria-hidden="true">{"↗"}</span>
        </a>
      </div>

      <div style={{ padding: "16px" } as React.CSSProperties}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", background: "#0C1018", border: "1px solid #1B2130", borderRadius: "4px", padding: "10px 10px 10px 14px", minWidth: 0 } as React.CSSProperties}>
          <code style={{ flex: "1 1 auto", minWidth: 0, font: `400 12.5px/1.6 ${MONO}`, color: "#EEF3F8", overflowWrap: "anywhere" } as React.CSSProperties}>
            <span aria-hidden="true" style={{ color: "#7C8798" }}>$ </span>
            {SKILL_COMMAND}
          </code>
          <button
            type="button"
            onClick={copy}
            aria-label={copied ? "Copied" : "Copy the command"}
            title={copied ? "Copied" : "Copy"}
            style={{ flex: "0 0 auto", display: "inline-flex", alignItems: "center", justifyContent: "center", width: "32px", height: "32px", background: "transparent", border: "1px solid #263048", borderRadius: "4px", color: copied ? "#22D3EE" : "#AEB9C8", cursor: "pointer" } as React.CSSProperties}
          >
            {copied ? (
              <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8.5l3 3 7-7" fill="none" stroke="currentColor" strokeWidth="1.6" /></svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><rect x="5" y="5" width="8.5" height="8.5" rx="1" fill="none" stroke="currentColor" strokeWidth="1.4" /><path d="M11 3H3.5a1 1 0 0 0-1 1v7" fill="none" stroke="currentColor" strokeWidth="1.4" /></svg>
            )}
          </button>
        </div>
        <p style={{ ...LABEL, margin: "10px 0 0", color: "#7C8798" }}>For your agent</p>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "10px 16px", padding: "12px 16px", borderTop: "1px solid #1B2130" } as React.CSSProperties}>
        <span style={{ ...LABEL, color: "#AEB9C8" }}>No agent? Start here</span>
        <a
          href={NOTARY}
          target="_blank"
          rel="noreferrer"
          style={{ ...LABEL, display: "inline-block", color: "#22D3EE", border: "1px solid #22D3EE", borderRadius: "4px", padding: "10px 14px", textDecoration: "none", minHeight: "24px" } as React.CSSProperties}
          className="rc-hover-5"
        >
          Talk to Notary
        </a>
      </div>
    </section>
  );
}
