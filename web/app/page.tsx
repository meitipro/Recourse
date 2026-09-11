/**
 * One page that does three jobs: explains the gap, shows the mechanism, and
 * proves the thing runs by showing live verdicts.
 *
 * The layout and every visual decision come from the Claude Design canvas,
 * ported rather than rebuilt. What this file owns is the data: every number
 * below is read from chain state or from a committed file, nothing is typed in
 * by hand, and an empty chain produces an empty feed rather than an invented
 * row.
 *
 * The chain read is shared. The hero's totals and the feed's table come from
 * one loadFeed call per request, so the number at the top of the page and the
 * number in the table can never disagree with each other.
 */

import fs from "node:fs";
import path from "node:path";
import { Suspense, cache } from "react";

import FeedPanel from "@/components/site/FeedPanel";
import FeedSkeleton from "@/components/site/FeedSkeleton";
import Clerk from "@/components/site/Clerk";
import Hero from "@/components/site/Hero";
import {
  ClosingSection,
  EvaluationSection,
  FailuresSection,
  FeedSectionShell,
  GapSection,
  HowSection,
  LimitsSection,
} from "@/components/site/Sections";
import SiteFooter from "@/components/site/SiteFooter";
import SiteHeader from "@/components/site/SiteHeader";
import { DISPUTE, ESCROW, EXPLORER, NETWORK, loadFeed } from "@/lib/chain";

export const dynamic = "force-dynamic";
export const revalidate = 0;

type Results = {
  accuracy: number;
  stability: number;
  n: number;
  runs: number;
  unclear: number;
  measured_at: number;
  rows: Array<{ id: string; correct: boolean; stable: boolean; expected: string }>;
};

type Case = {
  id: string;
  promise: string;
  request: string;
  response: string;
  timing: string;
  expected: string;
};

type Frozen = {
  window_seconds?: number;
  bond_wei?: string;
  deployments?: Record<string, { chain_id: number }>;
};

/** One chain read per request, shared by the hero and the feed. */
const getFeed = cache(() => loadFeed(50));

function readOutside<T>(names: string[]): T | null {
  // next.config.mjs traces these into the hosted function. Without that a
  // deployed build reads nothing here and the page would claim the evaluation
  // had never run while the repository says otherwise.
  for (const name of names) {
    for (const candidate of [`../${name}`, `../../${name}`]) {
      try {
        const file = path.join(process.cwd(), candidate);
        if (fs.existsSync(file)) return JSON.parse(fs.readFileSync(file, "utf8")) as T;
      } catch {
        // fall through to the next candidate
      }
    }
  }
  return null;
}

async function HeroWithTotals() {
  const data = await getFeed();
  const decided = data.rows.filter((row) => row.status === 3);
  const upheld = decided.filter((row) => row.verdict === 2);
  const elapsed = decided
    .map((row) => (row.case ? row.case.decided_at - row.created_at : 0))
    .filter((value) => value > 0)
    .sort((a, b) => a - b);
  const median = elapsed.length ? elapsed[Math.floor(elapsed.length / 2)] : 0;
  // A failed read knows nothing, and a dash is what nothing looks like.
  const known = data.ok;
  return (
    <Hero
      escrow={data.escrow || ESCROW}
      dispute={data.dispute || DISPUTE}
      explorer={EXPLORER[NETWORK]}
      stats={{
        payments: known ? String(data.totalPayments || data.rows.length) : "-",
        disputes: known ? String(data.rows.filter((row) => row.status === 2 || row.status === 3).length) : "-",
        upheld: known ? (decided.length ? `${upheld.length}/${decided.length}` : "-") : "-",
        median: known ? (median ? `${median}s` : "-") : "-",
      }}
    />
  );
}

async function LiveFeed() {
  const data = await getFeed();
  return <FeedPanel data={data} limit={6} />;
}

export default async function Page() {
  const frozen = readOutside<Frozen>(["contracts/FROZEN.json"]);
  const results = readOutside<Results>(["eval/results.json"]);
  const heldOut = readOutside<Results>(["eval/results-v2.json"]);
  // The clerk offers the committed cases to load. They are the answer key, so
  // they come from the file git proves was committed before the judge existed,
  // never from anything typed here.
  const cases = (readOutside<Case[]>(["eval/cases.json"]) ?? []).map((one) => ({
    id: one.id,
    promise: one.promise,
    request: one.request,
    response: one.response,
    timing: one.timing,
    expected: one.expected,
  }));
  const chainId = frozen?.deployments?.[NETWORK]?.chain_id ?? 0;

  return (
    // The canvas's page wrapper: it carries the type, the colour and the
    // overflow guard, rather than body, so the case page keeps its own.
    <div
      style={{
        background: "#0A0C12",
        color: "#EEF3F8",
        fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif",
        fontSize: "15px",
        lineHeight: "1.55",
        minHeight: "100vh",
        overflowX: "hidden",
      }}
    >
      <SiteHeader />
      <main id="top">
        {/*
          The hero waits on the chain only for the four totals along its foot.
          Streamed, so the headline, the linter and everything below render at
          once and a slow chain never looks like a broken site.
        */}
        <Suspense
          fallback={
            <Hero
              escrow={ESCROW}
              dispute={DISPUTE}
              explorer={EXPLORER[NETWORK]}
              stats={{ payments: "-", disputes: "-", upheld: "-", median: "-" }}
            />
          }
        >
          <HeroWithTotals />
        </Suspense>

        <GapSection />
        <FailuresSection />
        <HowSection windowSeconds={frozen?.window_seconds ?? null} bondWei={frozen?.bond_wei ?? null} />

        <div id="feed">
          <FeedSectionShell>
            <Suspense fallback={<FeedSkeleton />}>
              <LiveFeed />
            </Suspense>
          </FeedSectionShell>
        </div>

        <div id="clerk">
          <Clerk cases={cases} />
        </div>

        {results && heldOut ? (
          <EvaluationSection results={results} heldOut={heldOut} />
        ) : null}

        <LimitsSection />
        <ClosingSection />
      </main>
      <SiteFooter network={NETWORK} chainId={chainId} />
    </div>
  );
}
