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

import { Fragment, useEffect, useState } from "react";
import type { Case, FeedData, Payment, Row } from "@/lib/chain";

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

/**
 * The evidence for one row, fetched when it is opened.
 *
 * The bodies are the largest fields on chain and only one row's worth is ever
 * on screen, so the list read leaves them out and this asks for them.
 */
function Evidence({ row }: { row: Row }) {
  const [state, setState] = useState<{
    loading: boolean;
    error?: string;
    payment?: Payment;
    verdict?: Case;
  }>({ loading: true });

  useEffect(() => {
    let live = true;
    fetch(`/api/evidence?pid=${encodeURIComponent(row.pid)}`)
      .then((response) => response.json())
      .then((data) => {
        if (!live) return;
        setState(
          data.ok
            ? { loading: false, payment: data.payment, verdict: data.case }
            : { loading: false, error: data.error || "could not read the chain" },
        );
      })
      .catch((error) => live && setState({ loading: false, error: String(error).slice(0, 160) }));
    return () => {
      live = false;
    };
  }, [row.pid]);

  if (state.loading) {
    return (
      <tr className="drawer">
        <td colSpan={7}>
          <div className="evidence">
            {["promise", "request", "response"].map((label) => (
              <div className="evidence-block" key={label}>
                <div className="eyebrow">{label}</div>
                <div className="skeleton" style={{ height: "2.4rem" }} />
              </div>
            ))}
          </div>
        </td>
      </tr>
    );
  }

  if (state.error || !state.payment) {
    return (
      <tr className="drawer">
        <td colSpan={7}>
          <div className="notice bad">The evidence could not be read. {state.error}</div>
        </td>
      </tr>
    );
  }

  const payment = state.payment;
  const decided = state.verdict ?? row.case;
  const blocks: Array<[string, string]> = [
    ["promise", decided?.promise ?? "on the seller's row, and frozen into a case when contested"],
    ["request", payment.request || "-"],
    ["response", payment.response || "not yet recorded"],
  ];
  if (decided?.timing) blocks.push(["timing, written by the chain", decided.timing]);
  if (decided?.reason) blocks.push(["reason given with the verdict", decided.reason]);

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
            {payment.response_sig
              ? `Signed by the seller: ${short(payment.response_sig)}`
              : payment.recorded_by && payment.recorded_by !== payment.seller
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

  // A failed read means these numbers are not known, so they are not shown. A
  // zero beside a notice saying the chain could not be read is an invented
  // number, and inventing one in a project about worthless data is the single
  // worst thing this page could do.
  const known = !data.error;
  const value = (shown: string) => (known ? shown : "-");

  return (
    <>
      <div className="stats">
        <div className="stat">
          <div className="stat-value">{value(String(data.totalPayments || rows.length))}</div>
          <div className="stat-label">payments</div>
        </div>
        <div className="stat">
          <div className="stat-value">{value(String(disputes.length))}</div>
          <div className="stat-label">disputes opened</div>
        </div>
        <div className="stat">
          <div className="stat-value">
            {value(resolved.length ? `${upheld.length}/${resolved.length}` : "-")}
          </div>
          <div className="stat-label">upheld</div>
        </div>
        <div className="stat">
          <div className="stat-value">{value(median ? `${median}s` : "-")}</div>
          {/*
            Payment to the dispute being accepted, by the chain's own clock.
            This used to say "median settlement", and it is not that: a case's
            opened_at and decided_at are one message's fixed datetime, so chain
            timestamps cannot see how long judgment took, and the money moves on
            a later finalization they cannot see either. Settlement measured by
            wall clock is about ninety seconds and is printed by the demo. This
            number is real; it was just labelled as a different one.
          */}
          <div className="stat-label">median pay to dispute</div>
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
                <th className="num">to dispute</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const state = stateOf(row, now);
                const verdict = VERDICT[row.verdict] ?? "pending";
                const settledIn = row.case ? row.case.decided_at - row.created_at : 0;
                return (
                  // The key belongs on the fragment, not on the elements inside
                  // it. React reconciles the list by the outermost child.
                  <Fragment key={row.pid}>
                    <tr
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
                        {row.verdict === 0 && row.status !== 2 ? (
                          // Nobody contested, so there is no verdict. Printing
                          // the status again here would read as one.
                          <span className="mono" style={{ color: "var(--dim)" }}>
                            not contested
                          </span>
                        ) : (
                          <span className={`verdict ${verdict}`}>
                            {verdict === "pending" ? "in consensus" : verdict.replace("_", " ")}
                          </span>
                        )}
                      </td>
                      <td className="num mono">{settledIn ? `${settledIn}s` : "-"}</td>
                    </tr>
                    {open === row.pid ? <Evidence row={row} /> : null}
                  </Fragment>
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
