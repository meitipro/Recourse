"""
Assemble the ported design into the Next app.

The JSX bodies come from to_jsx.py, so every inline style is the design's own.
This file only supplies the variables, wires the real data, and corrects the
three claims the project's own rules refuse to publish.
"""
from __future__ import annotations

import pathlib
import re

HERE = pathlib.Path(".")
WEB = pathlib.Path("G:/GenLayer Works/GenLayer Cards/GenLayerCard/Recourse/web")
OUT = WEB / "components" / "site"
OUT.mkdir(parents=True, exist_ok=True)


def read(name: str) -> str:
    return (HERE / name).read_text(encoding="utf-8")


def sub_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    assert n == 1, f"{label}: expected 1 occurrence, found {n}"
    return text.replace(old, new, 1)



VOID_TAGS = {"br", "img", "input", "hr", "meta", "link", "rect", "path", "circle", "line", "polygon", "stop", "use"}


def remove_block(text: str, marker: str, levels: int = 1) -> str:
    """
    Cut the element `levels` above `marker`, with its whole subtree.

    Used for the two call to action blocks that open the clerk. The clerk is a
    real feature of the design and is not built yet, so its buttons come out
    rather than sitting on the page promising something that is not there.
    """
    at = text.index(marker)
    opens = []
    for m in re.finditer(r"<(/?)([A-Za-z][\w.]*)([^>]*?)(/?)>", text[:at]):
        closing, tag, _, self_close = m.groups()
        if tag.lower() in VOID_TAGS or self_close:
            continue
        if closing:
            if opens:
                opens.pop()
        else:
            opens.append(m.start())
    start = opens[-levels]
    depth = 0
    for m in re.finditer(r"<(/?)([A-Za-z][\w.]*)([^>]*?)(/?)>", text[start:]):
        closing, tag, _, self_close = m.groups()
        if tag.lower() in VOID_TAGS or self_close:
            continue
        depth += -1 if closing else 1
        if depth == 0:
            return text[:start] + text[start + m.end():]
    raise AssertionError("unbalanced block")

# --------------------------------------------------------------- header
header = read("out-header.jsx")
# The parts gallery is a design-system artboard, not site content. The group
# keeps its two-button shape with the clerk and the feed, both real places.
header = sub_once(header, ">Components<", ">Feed<", "header parts label")
header = header.replace("v.showParts", "v.showFeed").replace("v.navPartsBg", "v.navFeedBg").replace(
    "v.navPartsColor", "v.navFeedColor")
header = header.replace("v.showAgent", "v.showClerk").replace("v.navAgentBg", "v.navClerkBg").replace(
    "v.navAgentColor", "v.navClerkColor")
header = header.replace(">Clerk<", ">Clerk<")

HEADER_TSX = '''"use client";

/**
 * The site header, ported from the Claude Design canvas.
 *
 * Every inline style below is the design's own, converted mechanically rather
 * than retyped, so no spacing or colour decision is lost in translation. What
 * this file adds is the state the canvas computed at design time: the viewport
 * width the layout branches on, the mobile menu, and the two group buttons.
 *
 * The canvas had a third view, a component gallery. That is a design system
 * artboard rather than site content, so the group carries the clerk and the
 * feed, which are both real places on this site.
 */

import { useEffect, useState } from "react";

export default function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [vw, setVw] = useState(1280);

  useEffect(() => {
    const onResize = () => {
      const w = window.innerWidth || document.documentElement.clientWidth || 0;
      if (w > 0) setVw(w);
      if (w >= 901) setMenuOpen(false);
    };
    onResize();
    window.addEventListener("resize", onResize);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("resize", onResize);
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  const jump = (id: string) => (e: React.MouseEvent) => {
    e.preventDefault();
    setMenuOpen(false);
    const go = () => {
      if (id === "top") {
        window.scrollTo({ top: 0, behavior: "smooth" });
        return;
      }
      const el = document.getElementById(id);
      if (el) {
        window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 72, behavior: "smooth" });
      }
    };
    setTimeout(go, menuOpen ? 60 : 0);
  };

  const wide = vw >= 901;
  const v = {
    goTop: jump("top"),
    goGap: jump("gap"),
    goHow: jump("how"),
    goEval: jump("evaluation"),
    showClerk: jump("clerk"),
    showFeed: jump("feed"),
    linksDisplay: wide ? "flex" : "none",
    burgerDisplay: wide ? "none" : "inline-flex",
    navClerkBg: "transparent",
    navClerkColor: "#AEB9C8",
    navFeedBg: "transparent",
    navFeedColor: "#AEB9C8",
    toggleMenu: () => setMenuOpen((open) => !open),
    closeMenu: () => setMenuOpen(false),
    menuAria: menuOpen ? "Close menu" : "Open menu",
    menuOpen: menuOpen,
    menuHidden: !menuOpen,
    menuOpacity: menuOpen ? "1" : "0",
    menuEvents: menuOpen ? "auto" : "none",
    menuClip: menuOpen ? "inset(0 0 0 0)" : "inset(0 0 100% 0)",
    menuItemY: menuOpen ? "0px" : "8px",
    menuItemOp: menuOpen ? "1" : "0",
    bar1Top: menuOpen ? "22px" : "15px",
    bar1Rot: menuOpen ? "45deg" : "0deg",
    bar2Op: menuOpen ? "0" : "1",
    bar2Scale: menuOpen ? "0.6" : "1",
    bar3Top: menuOpen ? "22px" : "29px",
    bar3Rot: menuOpen ? "-45deg" : "0deg",
  };

  return (
    <>
__HEADER__
    </>
  );
}
'''

(OUT / "SiteHeader.tsx").write_text(
    HEADER_TSX.replace("__HEADER__", header.rstrip()), encoding="utf-8"
)

# --------------------------------------------------------------- hero
hero = read("sec-hero.jsx")
# Addresses come from the freeze record rather than the canvas.
hero = sub_once(hero, "0x5125...8F78", "{escrowShort}", "hero escrow")
hero = sub_once(hero, "0x80A9...0Cc4", "{disputeShort}", "hero dispute")
# The raw canvas element becomes the ported animation component.
old_canvas = '<canvas id="rc-lane" aria-hidden="true" style={{ position: "absolute", inset: "0", zIndex: "0", width: "100%", height: "100%", display: "block" } as React.CSSProperties}> </canvas>'
hero = sub_once(
    hero, old_canvas,
    '<div aria-hidden="true" style={{ position: "absolute", inset: "0", zIndex: "0" }}>'
    '<LaneCanvas onFallback={setLaneFallback} /></div>',
    "hero canvas",
)

HERO_TSX = '''"use client";

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
    lintRows: Math.min(6, Math.max(3, text.split("\\n").length + Math.floor(text.length / 70))),
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
    lintReason: done ? result!.reason : error,
    lintSuggestion: done ? result!.suggestion || "" : "",
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
__HERO__
    </>
  );
}
'''

(OUT / "Hero.tsx").write_text(HERO_TSX.replace("__HERO__", hero.rstrip()), encoding="utf-8")

# --------------------------------------------------------------- sections
gap = read("sec-gap.jsx")
failures = read("sec-failures.jsx")
how = read("sec-how.jsx")
feedsection = read("sec-clerkcta.jsx")
# The canvas embedded its feed component here and its button switched artboards.
# On the site the real panel goes in, and the button expands it in place.
feedsection = re.sub(r"<dc-import[\s\S]*?</dc-import>", "{children}", feedsection)
assert "{children}" in feedsection, "feed slot not found"
feedsection = feedsection.replace("onClick={v.showFeed}", "onClick={undefined}")
feedsection = re.sub(r'<button type="button" onClick=\{undefined\}[\s\S]*?</button>', "", feedsection, count=1)
evaluation = read("sec-evaluation.jsx")
limits = read("sec-limits.jsx")
closing = read("sec-closing.jsx")

# --- corrections the project's own rules require -------------------------
# 1. Judgment lands on acceptance; money moves when that transaction
#    finalizes. Two transactions, about half a minute apart. Saying they are
#    one is the claim this project spent a rewrite getting right.
how = sub_once(
    how,
    "Verdict and money land in the same transaction. The receipt is public.",
    "The verdict is written and the settlement it implies is emitted with it. "
    "Money moves when that transaction finalizes, about half a minute later, so "
    "an appeal can never arrive after the payout. Both receipts are public.",
    "settle step",
)
# 2. The published end to end number is the money, not the verdict.
how = sub_once(how, ">under one minute<", ">about 90 seconds<", "end to end")
how = sub_once(how, ">End to end<", ">Dispute to money back<", "end to end label")
# 3. The settlement window is read from the freeze record.
how = sub_once(how, ">a few minutes<", ">{windowLabel}<", "settlement window")
# 4. The dollar a case figure was inherited from a differently shaped contract
#    and never measured here. It was removed from the README once already.
# The clerk is the design's own feature and needs a model behind it, so its two
# call to action blocks wait for the clerk itself rather than sitting here as
# buttons that do nothing.
how = remove_block(how, "v.showAgent", levels=1)
evaluation = remove_block(evaluation, "v.showAgent", levels=2)

limits = sub_once(
    limits,
    "Judgment costs about one dollar per case, so the first version targets payments above that line. Session batching is the route below it.",
    "One adjudication is ten model calls: a committee of five, each asking the same "
    "question in both presentation orders. studionet charges nothing for them, so this "
    "states the work rather than a price it cannot read off a receipt. Session batching "
    "is the route to payments below the cost of judging one.",
    "cost limit",
)

# --- evaluation numbers, read rather than typed --------------------------
# Each headline number is found by the label above its card, so the four are
# never confused with one another or with a case chip that happens to say 17.
def bind_number(text: str, label: str, expr: str) -> str:
    pattern = re.compile(
        r'(>' + re.escape(label) + r'</div>.*?<span[^>]*fontVariantNumeric: "tabular-nums" \} as React\.CSSProperties\}>)(\d+)(</span>)',
        re.S,
    )
    found = pattern.search(text)
    assert found, f"no headline number under {label!r}"
    return text[:found.start()] + found.group(1) + "{" + expr + "}" + found.group(3) + text[found.end():]


evaluation = bind_number(evaluation, "Accuracy", "results.accuracy")
evaluation = bind_number(evaluation, "Stability", "results.stability")
evaluation = bind_number(evaluation, "Landed on unclear", "results.unclear")
evaluation = bind_number(evaluation, "Held out set", "heldOut.accuracy")
evaluation = evaluation.replace(">/ 18<", ">/ {results.n}<")
evaluation = evaluation.replace(">/ 3<", ">/ {heldOut.n}<")
evaluation = evaluation.replace("2026-09-05", "{measuredOn}")

# The eighteen case chips become one map over the measured rows, keeping the
# design's own two colourways: green where the judge matched the committed
# answer, red where it did not.
CHIPS = """<div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "12px" }}>
        {results.rows.map((row) => (
          <span
            key={row.id}
            title={`Expected ${row.expected.replace("_", " ")} - ${row.correct ? "matched" : "did not match"} - ${row.stable ? "all three runs agreed" : "the three runs disagreed"}`}
            style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", minWidth: "36px", padding: "7px 9px", font: "500 11px 'Geist Mono', ui-monospace, monospace", color: row.correct ? "#4ADE80" : "#F87171", background: row.correct ? "rgba(74,222,128,0.10)" : "rgba(248,113,113,0.10)", border: `1px solid ${row.correct ? "rgba(74,222,128,0.35)" : "rgba(248,113,113,0.35)"}`, borderRadius: "0", fontVariantNumeric: "tabular-nums" }}
          >
            {row.id}
          </span>
        ))}
      </div>"""

chip_start = evaluation.rfind('<div style={{ display: "flex", flexWrap: "wrap", gap: "6px"', 0, evaluation.find(">01<"))
chip_end = evaluation.find("</div>", evaluation.find(">18<")) + len("</div>")
assert chip_start > 0 and chip_end > chip_start, "could not find the chip block"
evaluation = evaluation[:chip_start] + CHIPS + evaluation[chip_end:]

SECTIONS_TSX = '''/**
 * The page's sections, ported from the Claude Design canvas.
 *
 * Server rendered, because everything here comes from a committed file: the
 * freeze record, the two evaluation result files. Three statements the canvas
 * carried were corrected against the repository before this shipped, and each
 * correction is noted where it happened. The rest is the design's own markup.
 */

type Results = {
  accuracy: number;
  stability: number;
  n: number;
  runs: number;
  unclear: number;
  measured_at: number;
  rows: Array<{ id: string; correct: boolean; stable: boolean; expected: string }>;
};

export function GapSection() {
  return (
    <>
__GAP__
    </>
  );
}

export function FailuresSection() {
  return (
    <>
__FAILURES__
    </>
  );
}

export function HowSection({ windowSeconds }: { windowSeconds: number | null }) {
  // Read from contracts/FROZEN.json. The canvas said "a few minutes", which is
  // what this shows only when the record is missing.
  const windowLabel = windowSeconds ? `${windowSeconds} seconds` : "a few minutes";
  return (
    <>
__HOW__
    </>
  );
}

export function FeedSectionShell({ children }: { children: React.ReactNode }) {
  return (
    <>
__FEEDSECTION__
    </>
  );
}

export function EvaluationSection({
  results,
  heldOut,
}: {
  results: Results;
  heldOut: Results;
}) {
  const measuredOn = new Date(results.measured_at * 1000).toISOString().slice(0, 10);
  const byId = new Map(results.rows.map((row) => [row.id, row]));
  return (
    <>
__EVALUATION__
    </>
  );
}

export function LimitsSection() {
  return (
    <>
__LIMITS__
    </>
  );
}

export function ClosingSection() {
  return (
    <>
__CLOSING__
    </>
  );
}
'''

sections = (SECTIONS_TSX
            .replace("__GAP__", gap.rstrip())
            .replace("__FAILURES__", failures.rstrip())
            .replace("__HOW__", how.rstrip())
            .replace("__FEEDSECTION__", feedsection.rstrip())
            .replace("__EVALUATION__", evaluation.rstrip())
            .replace("__LIMITS__", limits.rstrip())
            .replace("__CLOSING__", closing.rstrip()))
(OUT / "Sections.tsx").write_text(sections, encoding="utf-8")

# --------------------------------------------------------------- footer
footer = read("out-footer.jsx")
FOOTER_TSX = '''/**
 * The footer, ported from the canvas. The article link the canvas carried is
 * not here: nothing is published at that address yet, and a link that names a
 * page which does not exist is the sort of claim this site refuses elsewhere.
 */

export default function SiteFooter({ network, chainId }: { network: string; chainId: number }) {
  return (
    <>
__FOOTER__
    </>
  );
}
'''
footer = footer.replace("studionet / chain 61999", "{network} / chain {chainId}")
(OUT / "SiteFooter.tsx").write_text(FOOTER_TSX.replace("__FOOTER__", footer.rstrip()), encoding="utf-8")

print("wrote:")
for f in sorted(OUT.glob("*.tsx")):
    print(f"  {f.relative_to(WEB)}  {len(f.read_text(encoding='utf-8')):6} chars")
