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

import Boot from "@/components/site/Boot";
import ContractCards from "@/components/site/ContractCards";
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
  type EvaluationColumn,
} from "@/components/site/Sections";
import SiteFooter from "@/components/site/SiteFooter";
import SiteHeader from "@/components/site/SiteHeader";
import { permanentRedirect } from "next/navigation";
import { DEFAULT_NETWORK, EXPLORER, deploymentOf, deployments, loadFeed, settlementMoves, type NetworkName } from "@/lib/chain";

export const dynamic = "force-dynamic";
export const revalidate = 0;

type Results = EvaluationColumn["results"];

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
};

/**
 * Three totals the snapshot times off the chain's own transactions and
 * receipts. The How and Limits sections state them, so they are read here and
 * never typed there.
 */
type SettlementTotals = {
  median_dispute_to_money_back_seconds?: number | null;
  median_finality_seconds?: number | null;
  committee?: number | null;
};

/** One chain read per request and network, shared by the hero and the feed. */
const getFeed = cache((network: NetworkName) => loadFeed(50, network));

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

async function HeroWithTotals({ network }: { network: NetworkName }) {
  const data = await getFeed(network);
  // Decided means a committee ruled, and a ruling is a case. On studionet
  // every case settled, so this is also every settled dispute. On Studio Next a
  // case is judged and the escrow keeps the money, and the count still shows
  // the committee's rulings rather than settlements that cannot run there.
  const decided = data.rows.filter((row) => row.case);
  const upheld = decided.filter((row) => row.case?.verdict === 2);
  const elapsed = decided
    .map((row) => (row.case ? row.case.decided_at - row.created_at : 0))
    .filter((value) => value > 0)
    .sort((a, b) => a - b);
  const median = elapsed.length ? elapsed[Math.floor(elapsed.length / 2)] : 0;
  // A failed read knows nothing, and a dash is what nothing looks like.
  const known = data.ok;
  return (
    <Hero
      network={network}
      escrow={data.escrow}
      dispute={data.dispute}
      explorer={EXPLORER[network]}
      stats={{
        payments: known ? String(data.totalPayments || data.rows.length) : "-",
        disputes: known ? String(data.rows.filter((row) => row.status === 2 || row.status === 3).length) : "-",
        upheld: known ? (decided.length ? `${upheld.length}/${decided.length}` : "-") : "-",
        median: known ? (median ? `${median}s` : "-") : "-",
      }}
    />
  );
}

async function LiveFeed({ network }: { network: NetworkName }) {
  const data = await getFeed(network);
  return <FeedPanel data={data} limit={6} />;
}

export default async function Page({ searchParams }: { searchParams: Promise<{ network?: string | string[] }> }) {
  // Studio Next, and nothing in the address can move it. Links once named a
  // network in the query; such an address lands here without it, because
  // studionet is in the record this page shows and not somewhere it reads.
  if ((await searchParams).network !== undefined) permanentRedirect("/");
  const network = DEFAULT_NETWORK;
  const pairs = deployments();
  const names = pairs.map((one) => one.network);
  const pair = deploymentOf(network);
  const frozen = readOutside<Frozen>(["contracts/FROZEN.json"]);
  // The evaluation gives every deployment its own column, never merged and
  // never averaged, whichever network the rest of the page is reading.
  const columns: EvaluationColumn[] = (names.length ? names : [network]).flatMap((name) => {
    // studionet's files carry no suffix, and any other network's are named for it.
    const suffix = name === "studionet" ? "" : `.${name}`;
    const results = readOutside<Results>([`eval/results${suffix}.json`]);
    const heldOut = readOutside<Results>([`eval/results-v2${suffix}.json`]);
    return results && heldOut ? [{ network: name, results, heldOut }] : [];
  });
  const snapshotName = network === "studionet" ? "snapshot.json" : `snapshot-${network}.json`;
  const settlement: SettlementTotals =
    readOutside<{ totals?: SettlementTotals }>([`evidence/${snapshotName}`])?.totals ?? {};
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
      {/* The boot screen steps through what this render read: the case ids
          and the networks the freeze record names. */}
      <Boot cases={cases.map((one) => one.id)} networks={names} />
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
              network={network}
              escrow={pair?.escrow ?? ""}
              dispute={pair?.dispute ?? ""}
              explorer={EXPLORER[network]}
              stats={{ payments: "-", disputes: "-", upheld: "-", median: "-" }}
            />
          }
        >
          <HeroWithTotals network={network} />
        </Suspense>

        <GapSection />
        <FailuresSection />
        <HowSection
          windowSeconds={frozen?.window_seconds ?? null}
          bondWei={frozen?.bond_wei ?? null}
          moneyBackSeconds={settlement.median_dispute_to_money_back_seconds ?? null}
          finalitySeconds={settlement.median_finality_seconds ?? null}
          network={network}
          settlementMoves={settlementMoves(network)}
        />

        <div id="feed">
          <FeedSectionShell>
            <Suspense fallback={<FeedSkeleton />}>
              <LiveFeed network={network} />
            </Suspense>
            {/* Both pairs of addresses stay on the page: the first deployment is
                the record, and the two networks are the strongest evidence here. */}
            <ContractCards pairs={pairs} reading={network} />
          </FeedSectionShell>
        </div>

        <div id="clerk">
          <Clerk cases={cases} />
        </div>

        {columns.length ? <EvaluationSection columns={columns} /> : null}

        <LimitsSection committee={settlement.committee ?? null} />
        <ClosingSection />
      </main>
      <SiteFooter network={network} deployments={pairs.map((one) => ({ network: one.network, chainId: one.chainId }))} />
    </div>
  );
}
