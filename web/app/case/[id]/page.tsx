import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { EXPLORER, NETWORK, loadEvidence, toCitation, toPid } from "@/lib/chain";

export const dynamic = "force-dynamic";

const STATUS = ["open", "withdrawn", "disputed", "resolved"] as const;
const VERDICT = ["pending", "honored", "not_honored", "unclear"] as const;

/**
 * One case, at a permanent address.
 *
 * /case/RC-2026-0003 and /case/p-000003 are the same page. The citation is
 * derived off chain from the payment id and the year the verdict landed, so
 * the site, the bot and the MCP server print the same one without a contract
 * change. Everything on this page is read from the chain when it is opened.
 */
export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  return { title: `${decodeURIComponent(id)} | Recourse` };
}

function clock(seconds: number) {
  return seconds ? new Date(seconds * 1000).toISOString().replace("T", " ").slice(0, 19) + " UTC" : "-";
}

function gen(wei: string) {
  const value = BigInt(wei || "0");
  return `${value / 10n ** 18n}.${String((value % 10n ** 18n) / 10n ** 16n).padStart(2, "0")} GEN`;
}

export default async function CasePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let pid: string;
  try {
    pid = toPid(decodeURIComponent(id));
  } catch {
    notFound();
  }
  const evidence = await loadEvidence(pid);
  if (!evidence.ok || !evidence.payment) {
    return (
      <main className="case-page">
        <p className="eyebrow">
          <Link href="/#feed">Recourse</Link> / case
        </p>
        <h1 className="case-title">{pid}</h1>
        <div className="notice bad">The chain could not be read. {evidence.error}</div>
      </main>
    );
  }
  const payment = evidence.payment;
  const decided = evidence.case;
  const citation = decided ? toCitation(pid, decided.decided_at) : null;
  const status = STATUS[payment.status] ?? String(payment.status);
  const verdict = VERDICT[payment.verdict] ?? String(payment.verdict);

  return (
    <main className="case-page">
      <p className="eyebrow">
        <Link href="/#feed">Recourse</Link> / case
      </p>
      <h1 className="case-title">{citation ?? pid}</h1>
      <p className="case-sub">
        {citation ? `${pid} on ${NETWORK}` : `never disputed, so there is no case; payment ${pid} on ${NETWORK}`}
      </p>

      <dl className="case-facts">
        <dt>status</dt>
        <dd>
          {status}
          {payment.status === 2 && decided ? " (verdict written, money moves on finalization)" : ""}
          {payment.status === 3 ? " (money moved)" : ""}
        </dd>
        <dt>verdict</dt>
        <dd className={`verdict ${verdict}`}>{payment.status < 2 ? "not contested" : verdict.replace("_", " ")}</dd>
        <dt>amount</dt>
        <dd>{gen(payment.amount)}</dd>
        <dt>bond</dt>
        <dd>{gen(payment.bond)}</dd>
        <dt>paid</dt>
        <dd>{clock(payment.created_at)}</dd>
        <dt>responded</dt>
        <dd>{clock(payment.responded_at)}</dd>
        {decided ? (
          <>
            <dt>decided</dt>
            <dd>{clock(decided.decided_at)}</dd>
          </>
        ) : null}
        <dt>buyer</dt>
        <dd className="mono">{payment.buyer}</dd>
        <dt>seller</dt>
        <dd className="mono">{payment.seller}</dd>
      </dl>

      {decided ? (
        <>
          <h2>What the validators read</h2>
          <div className="evidence">
            {(
              [
                ["promise", decided.promise],
                ["request", decided.request],
                ["response", decided.response],
                ["timing", decided.timing],
              ] as const
            ).map(([label, value]) => (
              <div className="evidence-block" key={label}>
                <div className="evidence-label">{label}</div>
                <pre>{value}</pre>
              </div>
            ))}
          </div>
          <h2>What they wrote</h2>
          <blockquote className="case-reason">{decided.reason}</blockquote>
          <p className="caption">
            Read from chain when this page was opened. The verdict is the committee&apos;s; the reason is the
            leader&apos;s display string and was never compared.{" "}
            <a href={`${EXPLORER[NETWORK]}`} rel="noreferrer">
              Explorer
            </a>
          </p>
        </>
      ) : (
        <>
          <h2>The frozen strings</h2>
          <div className="evidence">
            {(
              [
                ["request", payment.request ?? ""],
                ["response", payment.response ?? ""],
              ] as const
            ).map(([label, value]) => (
              <div className="evidence-block" key={label}>
                <div className="evidence-label">{label}</div>
                <pre>{value || "(none recorded)"}</pre>
              </div>
            ))}
          </div>
        </>
      )}
    </main>
  );
}
