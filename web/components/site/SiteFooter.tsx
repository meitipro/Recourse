/**
 * The footer: the page's colophon, not a byline.
 *
 * Stacked and centred, in the shape of the stacked circular footer, carried
 * into this site's tokens and its 4px corners: the mark in a ringed seal, the
 * wordmark and the one line of what this is, the places the project lives,
 * two icon buttons, the record this page reads, and a bottom rule saying where
 * every figure above came from. The reference's email form is not here: there
 * is no list to subscribe to, and a form that goes nowhere would be the one
 * false thing on the page.
 *
 * It names the network the page reads, and then every other deployment the
 * freeze record holds, as the record: named with its chain, never linked. So
 * the footer and the evaluation's columns name the same networks, and nothing
 * on the page takes a visitor to one it does not read.
 */

import { Fragment } from "react";

import type { NetworkName } from "@/lib/networks";

import Mark from "./Mark";

const MONO = "'Geist Mono', ui-monospace, monospace";

/** Every page this site points at is a page, never an endpoint: the linter and the MCP server answer POST, and the README's Install section names them. */
const SOURCES = [
  { label: "Repository", href: "https://github.com/meitipro/Recourse" },
  { label: "Skill and MCP server", href: "https://github.com/meitipro/recourse-skill" },
  { label: "Notary on Telegram", href: "https://t.me/AskRecourseBot" },
  { label: "GenLayer", href: "https://genlayer.com" },
];

const ICON_BUTTON = { width: "40px", height: "40px", display: "inline-flex", alignItems: "center", justifyContent: "center", border: "1px solid #263048", borderRadius: "4px", color: "#AEB9C8", transition: "border-color 0.25s ease, color 0.25s ease" } as React.CSSProperties;

export default function SiteFooter({
  network,
  deployments,
}: {
  network: NetworkName;
  deployments: Array<{ network: NetworkName; chainId: number }>;
}) {
  const reading = deployments.find((one) => one.network === network);
  const others = deployments.filter((one) => one.network !== network);
  return (
    <footer style={{ borderTop: "1px solid #1B2130", background: "#0C1018" } as React.CSSProperties}>
      <div style={{ padding: "clamp(56px, 7vw, 88px) clamp(20px, 5vw, 100px) clamp(30px, 4vw, 40px)", display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" } as React.CSSProperties}>
        <div className="rc-footer-seal">
          <span className="rc-seal-glow" aria-hidden="true" />
          <span style={{ position: "relative", zIndex: 2, display: "inline-flex" } as React.CSSProperties}>
            <Mark size={34} />
          </span>
        </div>
        <span style={{ marginTop: "22px", fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: "600", fontSize: "20px", letterSpacing: "0.22em", color: "#EEF3F8" } as React.CSSProperties}>RECOURSE</span>
        <p style={{ marginTop: "10px", font: `400 12.5px/1.6 ${MONO}`, color: "#7C8798", maxWidth: "40ch" } as React.CSSProperties}>
          A dispute right for the un-negotiated machine payment.
        </p>

        <nav aria-label="Where the project lives" style={{ marginTop: "30px", display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "12px 28px" } as React.CSSProperties}>
          {SOURCES.map((one) => (
            <a key={one.href} href={one.href} target="_blank" rel="noreferrer" style={{ font: `500 12px ${MONO}`, letterSpacing: "0.04em", color: "#AEB9C8", textUnderlineOffset: "4px" } as React.CSSProperties} className="rc-hover-5">
              {one.label}
            </a>
          ))}
        </nav>

        <div style={{ marginTop: "26px", display: "flex", gap: "12px" } as React.CSSProperties}>
          <a href="https://github.com/meitipro/Recourse" target="_blank" rel="noreferrer" aria-label="Recourse on GitHub" style={ICON_BUTTON} className="rc-icon-button">
            <svg width="17" height="17" viewBox="0 0 24 24" aria-hidden="true">
              <path fill="currentColor" d="M12 .5a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2c-3.2.7-3.88-1.37-3.88-1.37-.52-1.33-1.28-1.69-1.28-1.69-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.19-3.1-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.84 1.19 3.1 0 4.42-2.7 5.39-5.26 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .5z" />
            </svg>
          </a>
          <a href="https://t.me/AskRecourseBot" target="_blank" rel="noreferrer" aria-label="Notary on Telegram" style={ICON_BUTTON} className="rc-icon-button">
            <svg width="17" height="17" viewBox="0 0 24 24" aria-hidden="true">
              <path fill="currentColor" d="M21.9 4.3 18.6 19.8c-.25 1.1-.9 1.37-1.83.85l-5.05-3.72-2.44 2.35c-.27.27-.5.5-1.01.5l.36-5.14 9.35-8.45c.41-.36-.09-.56-.63-.2L5.8 13.26.82 11.7c-1.08-.34-1.1-1.08.23-1.6L20.5 2.6c.9-.33 1.69.21 1.4 1.7z" />
            </svg>
          </a>
        </div>

        <div style={{ marginTop: "32px", display: "grid", gap: "6px", justifyItems: "center" } as React.CSSProperties}>
          <p style={{ font: `500 12px ${MONO}`, color: "#EEF3F8" } as React.CSSProperties}>
            Reading {network} / chain {reading?.chainId ?? "-"}
          </p>
          {others.length ? (
            <p style={{ font: `500 12px/1.6 ${MONO}`, color: "#7C8798", maxWidth: "60ch" } as React.CSSProperties}>
              Also ran on {others.map((one, index) => (<Fragment key={one.network}>{index ? ", " : ""}{one.network} / chain {one.chainId}</Fragment>))}, kept in the record
            </p>
          ) : null}
        </div>

        <div style={{ marginTop: "clamp(34px, 5vw, 50px)", paddingTop: "18px", borderTop: "1px solid #151A25", width: "100%", display: "flex", flexDirection: "column", alignItems: "center", gap: "10px" } as React.CSSProperties}>
          <p style={{ font: `400 11px/1.65 ${MONO}`, color: "#7C8798", maxWidth: "78ch" } as React.CSSProperties}>
            The feed, its totals and the evaluation are read from the chain when this page opens, and from the record committed in the repository when the chain cannot be reached.
          </p>
          <p style={{ display: "inline-flex", gap: "16px", font: `500 10px ${MONO}`, letterSpacing: "0.16em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>
            <span>MIT licensed</span>
            <span>2026</span>
          </p>
        </div>
      </div>
    </footer>
  );
}
