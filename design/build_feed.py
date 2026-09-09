"""Assemble the design's feed panel around the real chain read."""
from __future__ import annotations

import pathlib

WEB = pathlib.Path("G:/GenLayer Works/GenLayer Cards/GenLayerCard/Recourse/web")
OUT = WEB / "components" / "site"
body = pathlib.Path("out-nested-1.jsx").read_text(encoding="utf-8").rstrip()

# The canvas labelled the first column "Time" and put a case id in it. On the
# chain the citation is the thing a reader needs to click, so the column
# carries both and says so, the same way the canvas relabels its other columns
# per mode.
body = body.replace("Time{v.sortGlyph}", "{v.colTime}{v.sortGlyph}")

# The citation is the permalink a reader cites and the video opens cold, so it
# sits in the row beside the seller rather than only inside the drawer.
CITE = ("""{row.citation ? (<Link href={`/case/${row.citation}`} onClick={(e) => e.stopPropagation()} """
        """style={{ color: "#22D3EE", borderBottom: "1px solid transparent" }}>{row.citation}</Link>) """
        """: (<span style={{ color: "#7C8798" }}>{row.pid}</span>)}{" "}"""
        """<span style={{ color: "#7C8798" }}>{row.seller}</span>""")
body = body.replace(">{row.seller}</span>", ">" + CITE + "</span>", 1)

TSX = '''"use client";

/**
 * The live feed, ported from the design canvas and wired to the chain.
 *
 * The canvas shipped this panel with the eighteen committed evaluation cases
 * in it, because a canvas has no chain. It also shipped every state the panel
 * needs: a skeleton, an empty table, a recorded snapshot notice and a failed
 * read. Those are exactly the four the site has to distinguish, so the design
 * carried over whole and only the data underneath it changed.
 *
 * What this file will not do is invent a number. A read that has not returned
 * shows dashes, a read that failed says so with the time it was attempted, and
 * a snapshot says it is a snapshot with the time it was recorded. The canvas's
 * count up animation on the totals is not here: the values arrive with the
 * server render, so counting up to a number already in the HTML would be an
 * animation about nothing.
 */

import Link from "next/link";
import { Fragment, useState } from "react";

import type { FeedData, Row } from "@/lib/chain";
import { toCitation } from "@/lib/cite";

const PILL: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  gap: "6px",
  font: "500 9.5px 'Geist Mono', ui-monospace, monospace",
  letterSpacing: "0.12em",
  textTransform: "uppercase",
  padding: "5px 9px",
  borderRadius: "0",
  whiteSpace: "nowrap",
};

/** The contract's own names, in the contract's own order. tests/direct/test_parity.py
 * holds this table to the codes escrow.py stores, so the underscore stays here and
 * the space belongs to the display. */
const VERDICT_NAMES = ["pending", "honored", "not_honored", "unclear"] as const;

/** The design's four verdict colourways. Unclear is dashed and colourless on purpose. */
function verdictStyle(verdict: string): React.CSSProperties {
  if (verdict === "honored") {
    return { ...PILL, color: "#4ADE80", background: "rgba(74,222,128,0.10)", border: "1px solid rgba(74,222,128,0.35)" };
  }
  if (verdict === "not_honored") {
    return { ...PILL, color: "#F87171", background: "rgba(248,113,113,0.10)", border: "1px solid rgba(248,113,113,0.35)" };
  }
  if (verdict === "unclear") {
    return { ...PILL, color: "#AEB9C8", background: "transparent", border: "1px dashed #263048" };
  }
  return { ...PILL, color: "#7C8798", background: "transparent", border: "1px solid #1B2130" };
}

function statusStyle(tone: string): React.CSSProperties {
  if (tone === "settled") {
    return { ...PILL, color: "#4ADE80", background: "transparent", border: "1px solid rgba(74,222,128,0.30)" };
  }
  if (tone === "provisional") {
    return { ...PILL, color: "#D9A441", background: "transparent", border: "1px solid rgba(217,164,65,0.35)" };
  }
  return { ...PILL, color: "#7C8798", background: "transparent", border: "1px solid #1B2130" };
}

/**
 * Accepted is a committee agreeing and is provisional until the appeal window
 * closes. Finalized is settled. Two words, two states, never collapsed.
 */
function stateOf(row: Row, now: number) {
  if (row.status === 3) return { label: "settled, finalized", tone: "settled" };
  if (row.status === 1) return { label: "withdrawn", tone: "settled" };
  if (row.status === 2) return row.case ? { label: "judged, accepted", tone: "provisional" } : { label: "in consensus", tone: "provisional" };
  if (now > row.window_ends) return { label: "released, uncollected", tone: "open" };
  return { label: "window open", tone: "open" };
}

function gen(wei: string) {
  const value = BigInt(wei || "0");
  return `${value / 10n ** 18n}.${String((value % 10n ** 18n) / 10n ** 16n).padStart(2, "0")}`;
}

function short(address: string) {
  return address && address.length > 12 ? `${address.slice(0, 6)}...${address.slice(-4)}` : address || "-";
}

export default function FeedPanel({ data, limit = 6 }: { data: FeedData; limit?: number }) {
  const [open, setOpen] = useState<string | null>(null);
  const [sort, setSort] = useState<"asc" | "desc">("desc");
  const [all, setAll] = useState(false);

  const now = Math.floor(Date.now() / 1000);
  const failed = !data.ok;
  const snapshot = data.source === "snapshot";
  const empty = data.ok && data.rows.length === 0;
  const known = data.ok;

  const sorted = [...data.rows].sort((a, b) => (sort === "asc" ? a.pid.localeCompare(b.pid) : b.pid.localeCompare(a.pid)));
  const shown = all ? sorted : sorted.slice(0, limit);

  const decided = data.rows.filter((row) => row.status === 3);
  const upheld = decided.filter((row) => row.verdict === 2);
  const elapsed = decided
    .map((row) => (row.case ? row.case.decided_at - row.created_at : 0))
    .filter((value) => value > 0)
    .sort((a, b) => a - b);
  const median = elapsed.length ? elapsed[Math.floor(elapsed.length / 2)] : 0;

  const notice = failed
    ? {
        edge: "dashed rgba(248,113,113,0.40)",
        tone: "#F87171",
        title: "The chain could not be read",
        body: `${data.error ?? "No answer."} No snapshot covers this network, so nothing is shown rather than something invented. Attempted at ${new Date(data.readAt).toUTCString()}.`,
        foot: "",
      }
    : snapshot
      ? {
          edge: "solid rgba(217,165,65,0.55)",
          tone: "#D9A441",
          title: "Recorded snapshot, not a live read",
          body: `Taken ${data.recordedAt ? new Date(data.recordedAt).toUTCString() : "at an unrecorded time"} from ${data.network}, a temporary testnet; ${data.why ?? "the chain did not answer"}. Every row below is what the chain held then, and every transaction hash behind it is in evidence/snapshot.json.`,
          foot: `From the recorded snapshot; the chain was tried at ${new Date(data.readAt).toUTCString()}.`,
        }
      : {
          edge: "solid #1B2130",
          tone: "#22D3EE",
          title: "Chain, reading the escrow contract",
          body: "The table below reads payments, statuses and elapsed times straight from the escrow contract when this page was opened. It renders its skeleton first and its empty state second, and never a row that did not happen.",
          foot: "Click a row for the three frozen strings the validators were given",
        };

  const rows = shown.map((row) => {
    const state = stateOf(row, now);
    const verdict = VERDICT_NAMES[row.verdict] ?? String(row.verdict);
    const citation = row.case ? toCitation(row.pid, row.case.decided_at) : null;
    const isOpen = open === row.pid;
    return {
      id: row.pid,
      pid: row.pid,
      citation,
      time: new Date(row.created_at * 1000).toISOString().slice(11, 19),
      seller: short(row.seller),
      amount: gen(row.amount),
      status: state.label,
      statusStyle: statusStyle(state.tone),
      verdict: row.status < 2 ? "not contested" : verdict.replace("_", " "),
      verdictStyle: row.status < 2 ? verdictStyle("pending") : verdictStyle(verdict),
      elapsed: row.case && row.case.decided_at > row.created_at ? `${row.case.decided_at - row.created_at}s` : "-",
      promise: row.case?.promise ?? "On the seller's row, and frozen into a case when the payment is contested.",
      request: row.request ?? "-",
      response: row.response ?? "Not recorded yet.",
      reason: row.case?.reason ?? "No case: this payment was never contested.",
      fixture: `Paid ${new Date(row.created_at * 1000).toUTCString()}. Seller ${row.seller}.${
        row.case ? ` Verdict written ${new Date(row.case.decided_at * 1000).toUTCString()}.` : ""
      } Read from the ${snapshot ? "recorded snapshot" : "escrow and dispute contracts"}, not typed.`,
      isOpen,
      edge: isOpen ? "#1B2130" : "#151A25",
      bg: isOpen ? "#0B0E15" : "transparent",
      toggle: () => setOpen(isOpen ? null : row.pid),
    };
  });

  const v = {
    chromeOn: true,
    showRows: !failed && !empty,
    showSkeleton: false,
    showEmpty: failed || empty,
    skeletons: [{ w: "82%" }, { w: "64%" }, { w: "88%" }, { w: "71%" }],
    rows,
    tableRadius: "0",
    colTime: "Time",
    colSeller: "Case / seller",
    colElapsed: "To dispute",
    sortGlyph: sort === "asc" ? "^" : "v",
    toggleSort: () => setSort(sort === "asc" ? "desc" : "asc"),
    stat1: known ? String(data.totalPayments || data.rows.length) : "-",
    stat2: known ? String(data.rows.filter((row) => row.status === 2 || row.status === 3).length) : "-",
    stat3: known ? (decided.length ? `${upheld.length}/${decided.length}` : "-") : "-",
    stat4: known ? (median ? `${median}s` : "-") : "-",
    stat1Color: known ? "#EEF3F8" : "#7C8798",
    stat2Color: known ? "#F87171" : "#7C8798",
    stat3Color: known ? "#4ADE80" : "#7C8798",
    stat4Color: known ? "#AEB9C8" : "#7C8798",
    label1: "Payments",
    label2: "Disputes opened",
    label3: "Upheld",
    label4: "Median pay to dispute",
    noticeBox: {
      display: "flex",
      flexWrap: "wrap" as const,
      alignItems: "flex-start" as const,
      justifyContent: "space-between",
      gap: "12px",
      padding: "13px clamp(14px, 2vw, 20px)",
      background: "#0C1018",
      border: `1px ${notice.edge}`,
    },
    noticeColor: notice.tone,
    noticeTitle: notice.title,
    noticeBody: notice.body,
    footNote: notice.foot,
    showFoot: !!notice.foot,
    more: data.rows.length > limit,
    allShown: all,
    toggleAll: () => setAll((value) => !value),
  };

  return (
    <>
__BODY__
    </>
  );
}
'''

(OUT / "FeedPanel.tsx").write_text(TSX.replace("__BODY__", body), encoding="utf-8")
print("wrote FeedPanel.tsx", len((OUT / "FeedPanel.tsx").read_text(encoding="utf-8")), "chars")
