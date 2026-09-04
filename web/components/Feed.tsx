"use client";

/**
 * The live feed. Read only, and structurally incapable of anything else: it
 * receives rows as props from a server component and holds no client.
 *
 * The one UI decision that matters here is distinguishing accepted from
 * finalized. Almost nobody does, because a single green tick is easier, and they
 * mean different things: accepted is a committee agreeing, provisional until the
 * appeal window closes; finalized is settled. Collapsing them for tidiness would
 * misreport the protocol.
 */

import { useEffect, useState } from "react";
import type { FeedData, Row } from "@/lib/chain";

const STATUS = ["open", "withdrawn", "disputed", "resolved"] as const;
const VERDICT = ["pending", "honored", "not_honored", "unclear"] as const;

function short(address: string) {
  if (!address || address.length < 12) return address || "-";
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function gen(wei: string) {
  const value = BigInt(wei || "0");
  const whole = value / 10n ** 18n;
  const fraction = (value % 10n ** 18n) / 10n ** 16n;
  return `${whole}.${String(fraction).padStart(2, "0")}`;
}

function clock(seconds: number) {
  if (!seconds) return "-";
  return new Date(seconds * 1000).toISOString().slice(11, 19);
}

function Address({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      className="addr"
      title={value}
      onClick={(event) => {
        event.stopPropagation();
        navigator.clipboard?.writeText(value).then(
          () => {
            setCopied(true);
            setTimeout(() => setCopied(false), 1200);
          },
          () => undefined,
        );
      }}
    >
      {copied ? "copied" : short(value)}
    </button>
  );
}

/**
 * What state this payment is in, and how settled that state is.
 *
 * A window that has expired without a withdrawal reads as released, because
 * economically it is: nothing on chain fires on its own, and the seller can
 * collect at any time.
 */
function stateOf(row: Row, now: number) {
  if (row.status === 3) return { label: "settled, finalized", tone: "settled" };
  if (row.status === 1) return { label: "withdrawn", tone: "settled" };
  if (row.status === 2) {
    return row.case
      ? { label: "judged, accepted", tone: "provisional" }
      : { label: "in consensus", tone: "provisional" };
  }
  if (now > row.window_ends) return { label: "released, uncollected", tone: "open" };
  return { label: "window open", tone: "open" };
}

function Evidence({ row }: { row: Row }) {
  const blocks: Array<[string, string]> = [
    ["promise", row.case?.promise ?? "recorded on the seller's row"],
    ["request", row.request || "-"],
    ["response", row.response || "not yet recorded"],
  ];
  if (row.case?.timing) blocks.push(["timing, written by the chain", row.case.timing]);
  if (row.case?.reason) blocks.push(["reason given with the verdict", row.case.reason]);
  return (
    <tr className="drawer">
      <td colSpan={7}>
        <div className="evidence">
          {blocks.map(([label, value]) => (
            <div className="evidence-block" key={label}>
              <div className="eyebrow">{label}</div>
              <pre>{value}</pre>
            </div>
          ))}
          <div className="caption">
            {row.response_sig
              ? `Signed by the seller: ${short(row.response_sig)}`
              : row.recorded_by && row.recorded_by !== row.seller
                ? "Recorded by the buyer. The seller did not sign it."
                : "No signature recorded."}
          </div>
        </div>
      </td>
    </tr>
  );
}

export default function Feed({ data }: { data: FeedData }) {
  const [open, setOpen] = useState<string | null>(null);
  const [now, setNow] = useState(() => Math.floor(Date.now() / 1000));

  useEffect(() => {
    const timer = setInterval(() => setNow(Math.floor(Date.now() / 1000)), 1000);
    return () => clearInterval(timer);
  }, []);

  const rows = data.rows;
  const disputes = rows.filter((row) => row.status === 2 || row.status === 3);
  const resolved = rows.filter((row) => row.status === 3);
  const upheld = resolved.filter((row) => row.verdict === 2);
  const elapsed = resolved
    .map((row) => (row.case ? row.case.decided_at - row.created_at : 0))
    .filter((value) => value > 0)
    .sort((a, b) => a - b);
  const median = elapsed.length ? elapsed[Math.floor(elapsed.length / 2)] : 0;

  return (
    <>
      <div className="stats">
        <div className="stat">
          <div className="stat-value">{rows.length}</div>
          <div className="stat-label">payments</div>
        </div>
        <div className="stat">
          <div className="stat-value">{disputes.length}</div>
          <div className="stat-label">disputes opened</div>
        </div>
        <div className="stat">
          <div className="stat-value">
            {resolved.length ? `${upheld.length}/${resolved.length}` : "-"}
          </div>
          <div className="stat-label">upheld</div>
        </div>
        <div className="stat">
          <div className="stat-value">{median ? `${median}s` : "-"}</div>
          <div className="stat-label">median settlement</div>
        </div>
      </div>

      {data.error ? (
        <div className="notice bad">
          The chain could not be read. {data.error}
          <br />
          Last successful read: {data.readAt ? new Date(data.readAt).toUTCString() : "never"}.
        </div>
      ) : rows.length === 0 ? (
        <div className="notice">
          The feed is live and waiting. No payments have been made to this deployment yet.
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>time</th>
                <th>payment</th>
                <th>seller</th>
                <th className="num">amount</th>
                <th>state</th>
                <th>verdict</th>
                <th className="num">elapsed</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const state = stateOf(row, now);
                const verdict = VERDICT[row.verdict] ?? "pending";
                const settledIn = row.case ? row.case.decided_at - row.created_at : 0;
                return (
                  <>
                    <tr
                      key={row.pid}
                      className="expandable"
                      onClick={() => setOpen(open === row.pid ? null : row.pid)}
                    >
                      <td className="mono">{clock(row.created_at)}</td>
                      <td className="mono">{row.pid}</td>
                      <td>
                        <Address value={row.seller} />
                      </td>
                      <td className="num mono">{gen(row.amount)}</td>
                      <td>
                        <span className={`state ${state.tone}`}>
                          <span className="dot" />
                          {state.label}
                        </span>
                      </td>
                      <td>
                        <span className={`verdict ${verdict}`}>
                          {verdict === "pending" && row.status !== 2
                            ? STATUS[row.status]
                            : verdict.replace("_", " ")}
                        </span>
                      </td>
                      <td className="num mono">{settledIn ? `${settledIn}s` : "-"}</td>
                    </tr>
                    {open === row.pid ? <Evidence key={`${row.pid}-e`} row={row} /> : null}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="legend">
        <span>
          <b>accepted</b>the committee agreed on the receipt, provisional until the appeal
          window closes
        </span>
        <span>
          <b>finalized</b>appeals complete, and the only state that is actually settled
        </span>
        <span>
          <b>released</b>the window expired with no dispute, so the seller may collect at any
          time
        </span>
      </div>
      <p className="caption">
        Read from chain at {new Date(data.readAt).toUTCString()}. Click a row for the evidence the
        validators saw.
      </p>
    </>
  );
}
