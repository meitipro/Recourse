"use client";

/**
 * 07, For your agent: the skill, the card that hands it over, and where it lives.
 *
 * The shape is Hirael's Feature 07, ported by hand into this site's tokens
 * rather than installed: a badge, a serif head, one paragraph, then three
 * blocks, each with a ringed icon seal lit from behind, rising into place as
 * they scroll into view. Then the skill.md card, and a row of the
 * addresses the skill is published at.
 *
 * Everything the blocks say is the skill repository's own: SKILL.md's
 * description, the six reference files in reference/, and the MCP server's
 * five registered tools, all read only.
 */

import { useEffect, useRef } from "react";

import AgentCard, { NOTARY, SITE, SKILL_REPO } from "./AgentCard";

const MONO = "'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace";
const SERIF = "'Source Serif 4', Georgia, serif";
const SANS = "'Work Sans', system-ui, sans-serif";


function Seal({ children }: { children: React.ReactNode }) {
  return (
    <div className="rc-seal" aria-hidden="true">
      <span className="rc-seal-glow" />
      <span style={{ position: "relative", zIndex: 2, display: "inline-flex", color: "#22D3EE" } as React.CSSProperties}>{children}</span>
    </div>
  );
}

const ICON = { width: 40, height: 40, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.4, strokeLinecap: "square" as const, strokeLinejoin: "miter" as const };

const BLOCKS = [
  {
    title: "SKILL.md",
    body: "When an agent is about to pay for an API call, or has just paid and got a response that looks wrong: write a promise, pay through escrow, check the response, file a dispute, read the verdict.",
    icon: (
      <svg {...ICON}>
        <path d="M6 3h8l4 4v14H6z" />
        <path d="M14 3v4h4M9 12h6M9 15.5h6M9 19h3.5" />
      </svg>
    ),
  },
  {
    title: "Six reference files",
    body: "One for each step, from what Recourse is to reading a verdict, with the calls written out, and a file of the frozen contract addresses they go to.",
    icon: (
      <svg {...ICON}>
        <path d="M4 6h12v14H4z" />
        <path d="M8 3h12v14M7.5 10.5h5M7.5 14h5" />
      </svg>
    ),
  },
  {
    title: "A read only MCP server",
    body: "Five tools over Streamable HTTP: check a promise, explain the protocol, read a case, read a seller's record, read the live counts. None of them pays, disputes or signs.",
    icon: (
      <svg {...ICON}>
        <path d="M9 3v5M15 3v5M6 8h12v4a6 6 0 0 1-12 0z" />
        <path d="M12 18v3" />
      </svg>
    ),
  },
];

const LINKS = [
  { label: "skill.md", href: `${SITE}/skill.md` },
  { label: "SKILL.md on GitHub", href: `${SKILL_REPO}/blob/main/SKILL.md` },
  { label: "Reference files", href: `${SKILL_REPO}/tree/main/reference` },
  { label: "MCP server", href: `${SKILL_REPO}/tree/main/mcp` },
  { label: "Notary on Telegram", href: NOTARY },
];

export default function SkillSection() {
  const grid = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = grid.current;
    if (!root || typeof IntersectionObserver === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    // The blocks are visible from the start. The rise plays only when the
    // observer reports a block about to scroll in from below, so a browser or
    // a capture tool that never delivers it still shows every block.
    const seen = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            if (entry.boundingClientRect.top > window.innerHeight * 0.6) entry.target.classList.add("rc-in");
            seen.unobserve(entry.target);
          }
        }
      },
      { rootMargin: "0px 0px 160px 0px" },
    );
    root.querySelectorAll(".rc-rise").forEach((item) => seen.observe(item));
    return () => seen.disconnect();
  }, []);

  return (
    <section id="skill" aria-labelledby="rc-skill" className="rc-skill-band">
      <div style={{ position: "relative", zIndex: 1, maxWidth: "1120px", margin: "0 auto", display: "flex", flexDirection: "column", alignItems: "center", gap: "clamp(40px, 5vw, 60px)" } as React.CSSProperties}>
        <header style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "18px", textAlign: "center", maxWidth: "760px" } as React.CSSProperties}>
          <span style={{ display: "inline-flex", alignItems: "center", gap: "10px", border: "1px solid #263048", borderRadius: "4px", background: "rgba(14,17,25,0.7)", padding: "7px 14px", font: `500 10px ${MONO}`, letterSpacing: "0.16em", textTransform: "uppercase" } as React.CSSProperties}>
            <span style={{ color: "#7C8798" }}>07</span>
            <span aria-hidden="true" style={{ width: "12px", height: "1px", background: "#263048" }} />
            <span style={{ color: "#22D3EE" }}>For your agent</span>
          </span>
          <h2 id="rc-skill" style={{ fontFamily: SERIF, fontWeight: 500, fontSize: "clamp(30px, 4.4vw, 52px)", lineHeight: 1.08, letterSpacing: "-0.025em", color: "#EEF3F8", textWrap: "balance" } as React.CSSProperties}>
            One file teaches an agent the dispute right{" "}
            <em style={{ fontStyle: "italic", color: "#7C8798" }}>before it pays for anything</em>
          </h2>
          <p style={{ fontFamily: SANS, fontSize: "clamp(14px, 1.1vw, 16.5px)", lineHeight: 1.65, color: "#AEB9C8", maxWidth: "62ch" } as React.CSSProperties}>
            An agent that pays for API calls needs to know three things at the moment it pays: what a promise worth paying against looks like, how to hold the money in escrow, and what to do when the response is wrong. The Recourse skill carries all three, and it is one fetch away.
          </p>
        </header>

        <div ref={grid} className="rc-skill-grid">
          {BLOCKS.map((block, index) => (
            <article key={block.title} className="rc-rise rc-skill-block" style={{ animationDelay: `${index * 100}ms` } as React.CSSProperties}>
              <Seal>{block.icon}</Seal>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" } as React.CSSProperties}>
                <h3 style={{ font: `500 13px ${MONO}`, letterSpacing: "0.08em", textTransform: "uppercase", color: "#EEF3F8" } as React.CSSProperties}>{block.title}</h3>
                <p style={{ fontFamily: SANS, fontSize: "14px", lineHeight: 1.65, color: "#7C8798" } as React.CSSProperties}>{block.body}</p>
              </div>
            </article>
          ))}
        </div>

        <div style={{ width: "100%", display: "flex", justifyContent: "center" } as React.CSSProperties}>
          <AgentCard />
        </div>

        <nav aria-label="Where the skill is published" style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "10px 26px" } as React.CSSProperties}>
          {LINKS.map((link) => (
            <a key={link.href} href={link.href} target="_blank" rel="noreferrer" style={{ font: `500 11px ${MONO}`, letterSpacing: "0.12em", textTransform: "uppercase", color: "#AEB9C8", textUnderlineOffset: "4px" } as React.CSSProperties} className="rc-hover-5">
              {link.label}
            </a>
          ))}
        </nav>
      </div>
    </section>
  );
}
