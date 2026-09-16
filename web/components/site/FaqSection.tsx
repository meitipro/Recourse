"use client";

/**
 * 09, Questions: the FAQ, in the shape of the faq-tabs block, ported by hand.
 *
 * Four tabs, each a filled bar rising under the chosen one, and under them
 * the questions as an accordion whose plus turns to a cross. Height and fill
 * are CSS transitions, and a reader who asked for less motion gets neither.
 *
 * Every answer restates something the README or the contracts already say,
 * and none carries a number: the figures live in the sections that read them
 * from the chain or the committed evaluation, and the answers point there.
 */

import { useId, useState } from "react";

const MONO = "'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace";
const SERIF = "'Source Serif 4', Georgia, serif";

type Item = { question: string; answer: React.ReactNode };

export const CATEGORIES: Record<string, string> = {
  protocol: "The protocol",
  disputes: "Disputes and verdicts",
  agents: "For agents",
  network: "This deployment",
};

const A = ({ href, children }: { href: string; children: React.ReactNode }) => (
  <a href={href} style={{ color: "#22D3EE", textUnderlineOffset: "3px" }} {...(href.startsWith("http") ? { target: "_blank", rel: "noreferrer" } : {})}>
    {children}
  </a>
);

const C = ({ children }: { children: React.ReactNode }) => (
  <code style={{ font: `400 0.92em ${MONO}`, color: "#EEF3F8", background: "#0C1018", border: "1px solid #1B2130", borderRadius: "4px", padding: "1px 5px" }}>{children}</code>
);

export const FAQS: Record<string, Item[]> = {
  protocol: [
    {
      question: "What is Recourse?",
      answer: "A dispute right for the un-negotiated machine payment. An agent pays into escrow against a promise the seller published in plain language. If the response breaks that promise, the buyer contests it and a committee of GenLayer validators rules.",
    },
    {
      question: "Why is x402 on its own not enough?",
      answer: "x402 settles a payment in milliseconds and finally. Once settlement confirms there is no chargeback path and no dispute window, by design. Recourse holds the payment for a short window, so there is something left to contest.",
    },
    {
      question: "Who writes the terms?",
      answer: "The seller, in one sentence it publishes on its own. That sentence is the whole contract. A buyer that has never heard of Recourse is still protected by it, and a seller is bound by nothing it did not write.",
    },
    {
      question: "What does an honest sale cost?",
      answer: "No judgment and no added latency. The response is recorded on chain, the window closes with nobody contesting, and the seller withdraws. The committee only runs when a buyer opens a dispute.",
    },
  ],
  disputes: [
    {
      question: "What does the committee actually see?",
      answer: "Three frozen strings from the parties, the promise, the request and the response, and a timing block the chain wrote, which no party can set. Nothing is read from the live internet at judgment time, by either contract.",
    },
    {
      question: "What verdicts are possible, and where does the money go?",
      answer: "Honored: the payment and the bond go to the seller. Not honored: both go back to the buyer. Unclear: the seller is paid and the buyer's bond is returned, because a promise too loose to judge is the seller's wording at fault, not the buyer.",
    },
    {
      question: "Can a response talk the judge into a verdict?",
      answer: "Each validator asks the same question with the evidence in both presentation orders, and when the two readings disagree the answer is unclear. Three evaluation cases attack the judge: an instruction to rule honored inside a response, a forged rules block inside a promise, and a forged good response inside a request. In every recorded run, on studionet and on Studio Next, each was ruled not honored, against what the attack asked for, and every stored reason rests on what the response is missing. The one reason that mentions the injected note calls it an invalid instruction.",
    },
    {
      question: "What if judgment never lands?",
      answer: (
        <>
          After the dispute window passes with no verdict, either party can call <C>reclaim</C>. The seller is paid and the bond goes back to the buyer, so no payment can sit in escrow forever.
        </>
      ),
    },
  ],
  agents: [
    {
      question: "How does my agent learn to use it?",
      answer: (
        <>
          Hand it the skill: <C>curl -s https://recourse-site-seven.vercel.app/skill.md</C>, or install it as a Claude Code plugin from <A href="https://github.com/meitipro/recourse-skill">meitipro/recourse-skill</A>. <A href="#skill">Section 07</A> has the card and every address it is published at.
        </>
      ),
    },
    {
      question: "Does anything here hold a key or move money for me?",
      answer: "No. The skill, the MCP server and Notary only read. Paying, disputing, withdrawing and signing happen in the agent's own wallet, and nothing in this project asks for a private key.",
    },
    {
      question: "How do I know a promise is worth paying against?",
      answer: (
        <>
          Paste it into the linter at the <A href="#top">top of the page</A>. Stage 1 is deterministic and names the check a promise fails. Stage 2 puts the deployed gate&apos;s question to one model, as a dry run of what the committee on chain decides.
        </>
      ),
    },
    {
      question: "I have no agent. Where do I start?",
      answer: (
        <>
          <A href="https://t.me/AskRecourseBot">Ask Notary on Telegram</A>. It reads promises, disputes and verdicts off the chain, and nothing needs installing.
        </>
      ),
    },
  ],
  network: [
    {
      question: "Which network does this site read?",
      answer: "GenLayer Studio Next. The same contracts first ran on studionet, and that deployment stays in the record rather than being somewhere this page can be pointed.",
    },
    {
      question: "Does the money actually move on Studio Next?",
      answer: "The verdict is written and the settlement does not move. Consensus v0.6 funds a value transfer only at the root of a transaction's fee allocation tree, and the payout sits two messages below the dispute that pays for it, so the escrow keeps the payment and the bond. On studionet the same path returned both to the buyer.",
    },
    {
      question: "How good is the judge?",
      answer: (
        <>
          <A href="#evaluation">Section 06</A> publishes two figures side by side and never one alone: one on the cases the question was narrowed against, and one on a held out set committed before it could be run. Both are read from the committed evaluation files.
        </>
      ),
    },
    {
      question: "Can I watch a real dispute?",
      answer: (
        <>
          <A href="/app">Run one</A>. The page pays, contests a stale response and shows each validator&apos;s vote as the chain reveals it, with every transaction linked to the explorer.
        </>
      ),
    },
  ],
};

function Question({ item, id }: { item: Item; id: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`rc-faq-item${open ? " rc-open" : ""}`}>
      <h3 style={{ margin: 0 }}>
        <button type="button" aria-expanded={open} aria-controls={`${id}-a`} id={`${id}-q`} onClick={() => setOpen(!open)} className="rc-faq-q">
          <span>{item.question}</span>
          <svg className="rc-faq-plus" width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
            <path d="M9 3v12M3 9h12" stroke="currentColor" strokeWidth="1.5" />
          </svg>
        </button>
      </h3>
      <div id={`${id}-a`} role="region" aria-labelledby={`${id}-q`} className="rc-faq-a" inert={!open}>
        <div style={{ overflow: "hidden" }}>
          <p style={{ padding: "0 20px 20px", fontSize: "15px", lineHeight: 1.7, color: "#AEB9C8", maxWidth: "72ch" }}>{item.answer}</p>
        </div>
      </div>
    </div>
  );
}

export default function FaqSection() {
  const keys = Object.keys(CATEGORIES);
  const [selected, setSelected] = useState(keys[0]);
  const base = useId();

  function onKey(event: React.KeyboardEvent, index: number) {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    event.preventDefault();
    const next = keys[(index + step + keys.length) % keys.length];
    setSelected(next);
    document.getElementById(`${base}-tab-${next}`)?.focus();
  }

  return (
    <section id="faq" aria-labelledby="rc-faq" style={{ borderTop: "1px solid #151A25", padding: "clamp(40px, 4.6vw, 72px) clamp(20px, 5vw, 100px)", display: "flex", flexWrap: "wrap", alignItems: "flex-start", gap: "clamp(20px, 3vw, 56px)", scrollMarginTop: "72px" } as React.CSSProperties}>
      <div style={{ flex: "0 0 clamp(146px, 14vw, 224px)", minWidth: "0", position: "sticky", top: "92px" } as React.CSSProperties}>
        <div style={{ font: `500 clamp(26px, 2.8vw, 40px)/1 ${MONO}`, letterSpacing: "-0.02em", color: "#7C8798" } as React.CSSProperties}>09</div>
        <div style={{ marginTop: "12px", font: `500 10.5px ${MONO}`, letterSpacing: "0.16em", textTransform: "uppercase", color: "#22D3EE" } as React.CSSProperties}>Questions</div>
        <div style={{ marginTop: "14px", height: "1px", background: "#1B2130" } as React.CSSProperties} />
      </div>
      <div style={{ flex: "1 1 min(620px, 100%)", minWidth: "0" } as React.CSSProperties}>
        <div style={{ height: "1px", background: "#1B2130" } as React.CSSProperties} />
        <h2 id="rc-faq" style={{ fontFamily: SERIF, fontWeight: 600, fontSize: "clamp(28px, 4vw, 40px)", lineHeight: 1.1, letterSpacing: "-0.025em", marginTop: "14px", maxWidth: "24ch" } as React.CSSProperties}>
          What people ask, <em style={{ fontStyle: "italic", color: "#EEF3F8" }}>answered from the record</em>
        </h2>

        <div role="tablist" aria-label="Question topics" style={{ marginTop: "clamp(24px, 3vw, 34px)", display: "flex", flexWrap: "wrap", gap: "10px" } as React.CSSProperties}>
          {keys.map((key, index) => (
            <button
              key={key}
              type="button"
              role="tab"
              id={`${base}-tab-${key}`}
              aria-selected={selected === key}
              aria-controls={`${base}-panel`}
              tabIndex={selected === key ? 0 : -1}
              onClick={() => setSelected(key)}
              onKeyDown={(event) => onKey(event, index)}
              className={`rc-faq-tab${selected === key ? " rc-on" : ""}`}
            >
              <span style={{ position: "relative", zIndex: 1 }}>{CATEGORIES[key]}</span>
            </button>
          ))}
        </div>

        <div role="tabpanel" id={`${base}-panel`} aria-labelledby={`${base}-tab-${selected}`} key={selected} className="rc-faq-panel" style={{ marginTop: "22px", display: "grid", gap: "10px" } as React.CSSProperties}>
          {FAQS[selected].map((item, index) => (
            <Question key={item.question} item={item} id={`${base}-${selected}-${index}`} />
          ))}
        </div>
      </div>
    </section>
  );
}
