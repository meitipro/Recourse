/**
 * The footer: the page's colophon, not a byline.
 *
 * Three columns under a rule. The mark and the wordmark as design/logo sets
 * them, the record this page reads, and where the source lives; then a
 * bottom bar saying where every figure above came from. The canvas carried an
 * article link and the author's handle here. Neither is here now: nothing is
 * published at that address, and the last thing a reader meets should be what
 * the project is and what stands behind it rather than who wrote it.
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

const LABEL = {
  font: `500 9.5px ${MONO}`,
  letterSpacing: "0.16em",
  textTransform: "uppercase",
  color: "#7C8798",
} as React.CSSProperties;

const LINE = { font: `500 12px ${MONO}`, color: "#AEB9C8" } as React.CSSProperties;

/** One of the three. They share the row and fill it, and wrap whole rather than squeezing. */
const COLUMN = { flex: "1 1 212px", minWidth: 0 } as React.CSSProperties;

/** Every page this site points at is a page, never an endpoint: the linter and the MCP server answer POST, and the README's Install section names them. */
const SOURCES = [
  { label: "Repository", href: "https://github.com/meitipro/Recourse" },
  { label: "Skill and MCP server", href: "https://github.com/meitipro/recourse-skill" },
  { label: "GenLayer", href: "https://genlayer.com" },
];

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
      <div style={{ padding: "clamp(40px, 6vw, 64px) clamp(20px, 5vw, 100px) clamp(30px, 4vw, 40px)" } as React.CSSProperties}>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "clamp(28px, 4vw, 56px)",
            alignItems: "flex-start",
          } as React.CSSProperties}
        >
          <div style={COLUMN}>
            <div style={{ display: "flex", alignItems: "center", gap: "14px" } as React.CSSProperties}>
              <Mark size={32} />
              <span
                style={{
                  fontFamily: "'Source Serif 4', Georgia, serif",
                  fontWeight: "600",
                  fontSize: "20px",
                  letterSpacing: "0.22em",
                  color: "#EEF3F8",
                } as React.CSSProperties}
              >
                RECOURSE
              </span>
            </div>
            <p style={{ marginTop: "14px", font: `400 12.5px/1.6 ${MONO}`, color: "#7C8798", maxWidth: "32ch" } as React.CSSProperties}>
              A dispute right for the un-negotiated machine payment.
            </p>
          </div>

          <div style={COLUMN}>
            <div style={LABEL}>The record</div>
            <p style={{ ...LINE, marginTop: "13px", color: "#EEF3F8" } as React.CSSProperties}>
              Reading {network} / chain {reading?.chainId ?? "-"}
            </p>
            {others.length ? (
              <p style={{ ...LINE, marginTop: "7px", color: "#7C8798", maxWidth: "34ch", lineHeight: "1.6" } as React.CSSProperties}>
                Also ran on {others.map((one, index) => (<Fragment key={one.network}>{index ? ", " : ""}{one.network} / chain {one.chainId}</Fragment>))}, kept in the record
              </p>
            ) : null}
          </div>

          <div style={COLUMN}>
            <div style={LABEL}>Source</div>
            <div style={{ marginTop: "13px", display: "grid", gap: "8px", justifyItems: "start" } as React.CSSProperties}>
              {SOURCES.map((one) => (
                <a
                  key={one.href}
                  href={one.href}
                  target="_blank"
                  rel="noreferrer"
                  style={{ ...LINE, letterSpacing: "0.04em", textUnderlineOffset: "4px" } as React.CSSProperties}
                  className="rc-hover-5"
                >
                  {one.label}
                </a>
              ))}
            </div>
          </div>
        </div>

        <div
          style={{
            marginTop: "clamp(30px, 4.5vw, 46px)",
            paddingTop: "16px",
            borderTop: "1px solid #151A25",
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "space-between",
            alignItems: "baseline",
            gap: "10px 28px",
          } as React.CSSProperties}
        >
          <p style={{ font: `400 11px/1.65 ${MONO}`, color: "#7C8798", maxWidth: "78ch", minWidth: 0 } as React.CSSProperties}>
            The feed, its totals and the evaluation are read from the chain when this page opens, and from the record committed in the repository when the chain cannot be reached.
          </p>
          <p
            style={{
              display: "inline-flex",
              alignItems: "baseline",
              gap: "16px",
              font: `500 10px ${MONO}`,
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              color: "#7C8798",
              whiteSpace: "nowrap",
            } as React.CSSProperties}
          >
            <span>MIT licensed</span>
            <span>2026</span>
          </p>
        </div>
      </div>
    </footer>
  );
}
