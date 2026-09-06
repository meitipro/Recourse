/**
 * One page that does three jobs: explains the gap, shows the mechanism, and
 * proves the thing runs by showing live verdicts.
 *
 * Every number on this page comes from chain state or from the committed
 * evaluation results. Nothing is typed in by hand, and an empty chain produces
 * an empty feed rather than an invented row.
 */

import fs from "node:fs";
import path from "node:path";
import Feed from "@/components/Feed";
import Linter from "@/components/Linter";
import { EXPLORER, NETWORK, loadFeed } from "@/lib/chain";

export const dynamic = "force-dynamic";
export const revalidate = 0;

type Results = {
  accuracy: number;
  stability: number;
  n: number;
  runs: number;
  unclear: number;
  rows: Array<{ id: string; correct: boolean; stable: boolean; expected: string }>;
};

function readResults(name = "results.json"): Results | null {
  // Published numbers only. If the evaluation has not been run against this
  // deployment there is no number, and the section says so rather than showing a
  // placeholder that reads as a measurement.
  for (const candidate of [`../eval/${name}`, `../../eval/${name}`]) {
    try {
      const file = path.join(process.cwd(), candidate);
      if (fs.existsSync(file)) {
        return JSON.parse(fs.readFileSync(file, "utf8")) as Results;
      }
    } catch {
      // fall through
    }
  }
  return null;
}

const FAILURES = [
  {
    title: "Stale",
    body: `{"pair":"ETH-USD","price":4182.1,\n "sources":3,\n "ts":"09:20:02Z"}`,
    caption: "Correct shape, expired content. Nine hours old against a five second promise.",
  },
  {
    title: "Hollow",
    body: `{"pair":"ETH-USD",\n "results":[],\n "count":0}`,
    caption: "Well formed, carrying nothing. An empty result set returned as success.",
  },
  {
    title: "Substituted",
    body: `{"pair":"BTC-USD","price":118400.0,\n "sources":3,\n "ts":"18:20:02Z"}`,
    caption: "Answers a different question than the one paid for.",
  },
];

const STEPS = [
  { title: "Call", line: "The buyer pays. Funds enter escrow, not the seller balance." },
  { title: "Hold", line: "A settlement window runs. The response arrives immediately." },
  { title: "Contest", line: "The buyer posts a bond and opens a case." },
  { title: "Judge", line: "Validators receive three frozen strings and one question." },
  { title: "Settle", line: "The verdict is written and the refund follows it on chain." },
];

const STACK = [
  { title: "Payments", body: "x402, settled in milliseconds", state: "shipped" },
  { title: "Identity", body: "agent tokens and delegated authority", state: "shipped" },
  { title: "Interoperability", body: "one rail across chains and providers", state: "shipped" },
  { title: "Dispute right", body: "no chargeback, no window, no pull back", state: "missing" },
];

export default async function Page() {
  const data = await loadFeed(50);
  const results = readResults();
  const heldOut = readResults("results-v2.json");
  const explorer = EXPLORER[NETWORK];

  return (
    <>
      <header className="shell hero">
        <div className="wordmark">
          Recourse<span>.</span>
        </div>
        <h1 style={{ marginTop: "2.5rem" }}>A dispute right for machine payments.</h1>
        <p className="lede" style={{ marginTop: "1.5rem" }}>
          Agents can spend money in milliseconds. Nothing in the stack lets them get it back.
        </p>
        <div className="actions">
          <a className="button" href="#feed">
            Live verdicts
          </a>
          <a
            className="button secondary"
            href="https://github.com/meitipro/Recourse"
            rel="noreferrer"
          >
            Repository
          </a>
        </div>
      </header>

      <main>
        <section className="shell">
          <div className="eyebrow">The gap</div>
          <h2>The rail is finished. The right is missing.</h2>
          <p style={{ marginTop: "1rem" }}>
            x402 settles machine payments in milliseconds and finally. Once settlement confirms
            there is no chargeback path and no dispute window, by design, because a push payment
            with no reversal is precisely what lets machines transact without accounts or credit
            relationships. Mastercard&apos;s agent tokens preserve dispute rights.
            OpenAI&apos;s preserve dispute rights. x402 does not.
          </p>
          <div className="stack">
            {STACK.map((row) => (
              <div
                className={`stack-row${row.state === "missing" ? " missing" : ""}`}
                key={row.title}
              >
                <div>
                  <h3>{row.title}</h3>
                  <p>{row.body}</p>
                </div>
                <span className={`pill ${row.state === "missing" ? "gap" : "shipped"}`}>
                  {row.state}
                </span>
              </div>
            ))}
          </div>
        </section>

        <section className="shell">
          <div className="eyebrow">The failures</div>
          <h2>Every one of these returns 200 and settles payment.</h2>
          <div className="cards">
            {FAILURES.map((card) => (
              <figure className="card" key={card.title} style={{ margin: 0 }}>
                <div className="card-head">
                  <h3>{card.title}</h3>
                  <span className="badge-200">200 OK</span>
                </div>
                <pre>{card.body}</pre>
                <figcaption>{card.caption}</figcaption>
              </figure>
            ))}
          </div>
          <p className="caption" style={{ marginTop: "1.5rem" }}>
            Every deterministic check passes. Deciding whether a response was worth paying for
            takes a judge, and a judge has to be cheap, fast and neutral at once.
          </p>
        </section>

        <section className="shell" id="linter">
          <div className="eyebrow">The linter</div>
          <h2>Would a judge be able to rule on your promise?</h2>
          <p>
            A promise is the only standard a response is judged against. One that says only that
            data is accurate leaves a judge two choices, invent a standard the seller never agreed
            to or answer unclear. Paste one. Stage 1 is deterministic and free and names the check
            it failed; stage 2 asks the deployed gate&apos;s exact question of one model and offers
            a rewrite when the answer is no.
          </p>
          <Linter />
        </section>

        <section className="shell">
          <div className="eyebrow">How it works</div>
          <h2>An escrow window, a promise, a bond, three verdicts.</h2>
          <div className="flow">
            {STEPS.map((step, index) => (
              <div className="step" key={step.title}>
                <div className="step-index">{String(index + 1).padStart(2, "0")}</div>
                <h3>{step.title}</h3>
                <p>{step.line}</p>
              </div>
            ))}
          </div>
          <div className="flow-facts">
            <span>
              settlement window {data.windowSeconds ? `${data.windowSeconds}s` : "a few minutes"}
            </span>
            <span>uncontested releases with no consensus</span>
            <span>the honest path adds no latency</span>
          </div>
        </section>

        <section className="shell" id="feed">
          <div className="eyebrow">Live feed</div>
          <h2>Reading the chain, right now.</h2>
          <div style={{ marginTop: "2rem" }}>
            <Feed data={data} />
          </div>
          {data.escrow ? (
            <p className="caption" style={{ marginTop: "1.25rem" }}>
              escrow{" "}
              <a href={`${explorer}/address/${data.escrow}`} rel="noreferrer" className="mono">
                {data.escrow}
              </a>{" "}
              &nbsp; dispute{" "}
              <a href={`${explorer}/address/${data.dispute}`} rel="noreferrer" className="mono">
                {data.dispute}
              </a>{" "}
              &nbsp; network <span className="mono">{NETWORK}</span>
            </p>
          ) : null}
        </section>

        <section className="shell">
          <div className="eyebrow">Verdict quality</div>
          <h2>The answers were committed one commit before the judge.</h2>
          {results ? (
            <>
              <div className="eval-grid">
                <div>
                  <div className="headline-number">
                    {results.accuracy}
                    <small>/{results.n}</small>
                  </div>
                  <div className="stat-label">accuracy against verdicts committed first</div>
                </div>
                <div>
                  <div className="headline-number">
                    {results.stability}
                    <small>/{results.n}</small>
                  </div>
                  <div className="stat-label">
                    stability across {results.runs} consecutive runs
                  </div>
                </div>
                <div>
                  <div className="headline-number">
                    {results.unclear}
                    <small>/{results.n}</small>
                  </div>
                  <div className="stat-label">landed on unclear</div>
                </div>
                {heldOut ? (
                  // The worse number at the same size as the better one. A
                  // project that shows 17 large and 1 small is making a claim
                  // the numbers alone do not support.
                  <div>
                    <div className="headline-number">
                      {heldOut.accuracy}
                      <small>/{heldOut.n}</small>
                    </div>
                    <div className="stat-label">held out set, never tuned against</div>
                  </div>
                ) : null}
              </div>
              <div className="case-grid">
                {results.rows.map((row) => (
                  <div
                    className={`case-chip ${row.correct ? "hit" : "miss"}`}
                    key={row.id}
                    title={`${row.id}: expected ${row.expected}, ${
                      row.correct ? "matched" : "did not match"
                    }, ${row.stable ? "stable" : "unstable"}`}
                  >
                    {row.id}
                  </div>
                ))}
              </div>
              <p className="caption" style={{ marginTop: "1.5rem" }}>
                Each case ran {results.runs} times through real consensus on {NETWORK}. Full
                results, including every case the judge got wrong, are in eval/RESULTS.md.
              </p>
              {heldOut ? (
                // The number the README refuses to publish alone. The first set
                // is the one the question was narrowed against; this one was
                // committed before the runner could read it and never tuned
                // against. Both are real, and the gap is the informative part.
                <div className="notice" style={{ marginTop: "1.5rem" }}>
                  <b>Two sets, always together.</b> {results.accuracy} of {results.n} is the set
                  the judgment question was narrowed against. {heldOut.accuracy} of {heldOut.n} is
                  three further cases with answers committed before the runner could read them,
                  aimed at the weakness the first set exposed, and never tuned against.
                  {heldOut.accuracy < heldOut.n
                    ? " On one miss the judge has the better argument than the answer key, and it is still counted as a miss. The reading is in eval/HELD-OUT.md."
                    : ""}
                </div>
              ) : null}
            </>
          ) : (
            <div className="notice">
              The evaluation has not been run against this deployment yet. The number goes here
              when it has, whatever it is.
            </div>
          )}
        </section>

        <section className="shell">
          <div className="eyebrow">Scope</div>
          <h2>What this is.</h2>
          <p>
            One adjudication is ten model calls: a committee of five, each asking the same
            question in both presentation orders. Studionet charges nothing for them, so this
            page states the work rather than a price it cannot read off a receipt.
          </p>
          <p>
            A vague promise produces a vague verdict, and the system says so through the unclear
            outcome rather than performing confidence it has not earned.
          </p>
          <p>
            Recourse is not a competitor to an escrow that refunds on an arbiter&apos;s decision.
            It is a candidate for that arbiter slot: a judge neither the operator nor the buyer
            controls.
          </p>
        </section>
      </main>

      <footer className="shell">
        <p className="close">A refund system where the merchant picks the judge is a refund
          policy. It is not a dispute right.</p>
        <div className="footer-row">
          <span>Recourse</span>
          <div className="footer-links">
            <a href="https://github.com/meitipro/Recourse" rel="noreferrer">
              repository
            </a>
            <a href="https://genlayer.com" rel="noreferrer">
              genlayer
            </a>
            <a href="https://x.com/meitipro1" rel="noreferrer">
              @meitipro1
            </a>
          </div>
        </div>
      </footer>
    </>
  );
}
