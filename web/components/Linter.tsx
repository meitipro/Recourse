"use client";

/**
 * The promise linter, on the page. One textarea, one button, one result.
 *
 * It posts to /api/lint, which forwards to the one linter service; nothing is
 * decided here. Three states and only three: judgeable, not judgeable, or
 * "could not reach the linter". Never a spinner that runs forever, never an
 * invented result, and nothing pasted here is stored, which is true because
 * the route and the service log the path and status of a request and never
 * its body.
 */

import { useState } from "react";

type Result = {
  judgeable: boolean;
  reason: string;
  failed_check: string | null;
  suggestion: string | null;
  stage: 1 | 2;
};

type State =
  | { kind: "idle" }
  | { kind: "busy" }
  | { kind: "result"; result: Result }
  | { kind: "error"; message: string };

const EXAMPLES = [
  "Accurate market data.",
  "Prices aggregated from at least three venues, refreshed within five seconds.",
];

export default function Linter() {
  const [promise, setPromise] = useState("");
  const [state, setState] = useState<State>({ kind: "idle" });
  const [copied, setCopied] = useState(false);

  async function check() {
    const text = promise.trim();
    if (!text) return;
    setState({ kind: "busy" });
    // A hard ceiling on the wait. Stage 2 can take a while; forever is not a state.
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 210_000);
    try {
      const response = await fetch("/api/lint", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ promise: text }),
        signal: controller.signal,
      });
      const payload = (await response.json()) as Result & { error?: string };
      if (!response.ok || payload.error) {
        setState({
          kind: "error",
          message:
            response.status === 429
              ? "Too many checks in the last minute. Try again shortly."
              : payload.error
                ? `Could not reach the linter. ${payload.error}`
                : "Could not reach the linter. Try again.",
        });
        return;
      }
      setState({ kind: "result", result: payload });
    } catch {
      setState({ kind: "error", message: "Could not reach the linter. Try again." });
    } finally {
      clearTimeout(timer);
    }
  }

  const result = state.kind === "result" ? state.result : null;

  return (
    <div className="linter">
      <label className="linter-label" htmlFor="promise">
        A delivery promise, as a seller would register it
      </label>
      <textarea
        id="promise"
        className="linter-input"
        rows={3}
        maxLength={2000}
        placeholder="Returns the spot price for the requested pair, aggregated from at least three venues, with a timestamp no more than five seconds old."
        value={promise}
        onChange={(event) => setPromise(event.target.value)}
        onKeyDown={(event) => {
          if ((event.metaKey || event.ctrlKey) && event.key === "Enter") check();
        }}
      />
      <div className="linter-row">
        <button className="linter-button" onClick={check} disabled={state.kind === "busy" || !promise.trim()}>
          {state.kind === "busy" ? "Checking" : "Is this judgeable?"}
        </button>
        <span className="linter-examples">
          try{" "}
          {EXAMPLES.map((example, index) => (
            <button key={example} className="linter-example" onClick={() => setPromise(example)}>
              {index === 0 ? "a vague one" : "a judgeable one"}
            </button>
          ))}
        </span>
      </div>

      {result ? (
        <div className={`linter-result ${result.judgeable ? "yes" : "no"}`}>
          <div className="linter-verdict">{result.judgeable ? "Judgeable" : "Not judgeable"}</div>
          <p>{result.reason}</p>
          {result.judgeable ? (
            <p className="linter-meta">A response could be ruled against this. That is what a promise is for.</p>
          ) : null}
          {result.failed_check ? (
            <p className="linter-meta">
              Failed the deterministic check <b>{result.failed_check}</b>. No model was asked and nothing was spent.
            </p>
          ) : null}
          {result.suggestion ? (
            <div className="linter-suggestion">
              <div className="linter-meta">A rewrite that keeps the intent and passes the checks</div>
              <pre className="linter-code">{result.suggestion}</pre>
              <button
                className="linter-copy"
                onClick={() => {
                  navigator.clipboard?.writeText(result.suggestion || "").then(
                    () => {
                      setCopied(true);
                      setTimeout(() => setCopied(false), 1200);
                    },
                    () => undefined,
                  );
                }}
              >
                {copied ? "copied" : "copy"}
              </button>
            </div>
          ) : null}
          <p className="linter-meta">
            {result.stage === 1
              ? "Stage 1 of the linter: deterministic, free."
              : "Stage 2 of the linter: the deployed gate's question, put to one model. A dry run, not the gate's verdict."}
          </p>
        </div>
      ) : null}

      {state.kind === "error" ? <div className="linter-result error">{state.message}</div> : null}

      <p className="linter-footnote">Nothing you paste here is stored.</p>
    </div>
  );
}
