"""
Assemble the clerk from the canvas, single case only.

The canvas offered a second mode that runs all eighteen committed cases in the
browser and scores itself. That is out of scope by decision: it would put a
second accuracy number next to the published one, measured by one model rather
than a committee, and the runbook scopes the clerk to three inputs and one
button. The mode tabs and the whole batch panel come out rather than sitting
there as controls that do nothing.
"""
from __future__ import annotations

import pathlib
import re

WEB = pathlib.Path("G:/GenLayer Works/GenLayer Cards/GenLayerCard/Recourse/web")
OUT = WEB / "components" / "site"
body = pathlib.Path("out-nested-2.jsx").read_text(encoding="utf-8").rstrip()

VOID_TAGS = {"br", "img", "input", "hr", "meta", "link", "rect", "path", "circle", "line", "polygon", "stop", "use", "textarea"}
TAG = re.compile(r"<(/?)([A-Za-z][\w.]*)([^>]*?)(/?)>")


def remove_block(text: str, marker: str, levels: int = 1) -> str:
    """Cut the element `levels` above `marker`, with its whole subtree."""
    at = text.index(marker)
    opens = []
    for m in TAG.finditer(text[:at]):
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
    for m in TAG.finditer(text[start:]):
        closing, tag, _, self_close = m.groups()
        if tag.lower() in VOID_TAGS or self_close:
            continue
        depth += -1 if closing else 1
        if depth == 0:
            return text[:start] + text[start + m.end():]
    raise AssertionError("unbalanced block")


def remove_guard(text: str, guard: str) -> str:
    """
    Cut a whole `{cond && (<> ... </>)}` region, guard included.

    Counted on the fragment markers the converter emits rather than on tag
    depth, because a guarded region can hold several sibling elements and a
    nested map closes with an extra paren.
    """
    start = text.index(guard)
    opens = ("(<>", "(<Fragment")
    closes = ("</>)}", "</Fragment>))}")
    depth = 0
    i = start
    while i < len(text):
        for token in closes:
            if text.startswith(token, i):
                depth -= 1
                i += len(token)
                if depth == 0:
                    return text[:start] + text[i:]
                break
        else:
            for token in opens:
                if text.startswith(token, i):
                    depth += 1
                    i += len(token)
                    break
            else:
                i += 1
    raise AssertionError("unbalanced guard")


# The two mode tabs and the note beside them.
body = remove_block(body, "v.tabSingle", levels=2)
# The batch panel.
body = remove_guard(body, "{v.isBatch && (<>")
# Single is the only mode now, so its guard is noise.
body = body.replace("{v.isSingle && (<>", "{true && (<>", 1)

# The canvas said the bond is sized to the cost of judgment. It is fixed when
# the escrow is deployed, studionet charges nothing for judgment, and the bond
# is forfeit when the response is ruled honored, which is the real reason a
# frivolous case is not free.
OLD_BOND = "The bond is sized to the cost of judgment, so a frivolous case is not free."
assert body.count(OLD_BOND) == 1, "the clerk's bond sentence moved"
body = body.replace(
    OLD_BOND,
    "The bond is fixed when the escrow is deployed and is forfeit when the response is ruled honored, so contesting everything is not free.",
    1,
)

# The canvas printed "Recorded on chain: no" beside a verdict, so a reader only
# met it after judging. It belongs in the state a reader meets first, and it is
# a literal rather than a value, so no later edit can make this panel claim it
# was recorded when it was not.
ALWAYS = (
    """<div style={{ marginTop: "9px", display: "inline-flex", alignItems: "center", gap: "8px", """
    """font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", """
    """textTransform: "uppercase", color: "#D9A441" } as React.CSSProperties}>"""
    """<span>Recorded on chain</span><span style={{ color: "#EEF3F8" }}>no</span></div>"""
)
marker = "Every verdict below is indicative, and none of it is the published number.</p>"
assert body.count(marker) == 1, "the standing warning moved"
body = body.replace(marker, marker + " " + ALWAYS, 1)

left = sorted(set(re.findall(r"v\.[A-Za-z_][A-Za-z0-9_]*", body)))
print("variables the clerk still needs:", " ".join(left))

TSX = '''"use client";

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
  const curlCmd = `curl -s -X POST ${origin || "<this site>"}/api/clerk \\\\
  -H "Content-Type: application/json" \\\\
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
__BODY__
    </>
  );
}
'''

(OUT / "Clerk.tsx").write_text(TSX.replace("__BODY__", body), encoding="utf-8")
print("wrote Clerk.tsx", len((OUT / "Clerk.tsx").read_text(encoding="utf-8")), "chars")
