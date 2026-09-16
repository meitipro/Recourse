"use client";

/**
 * Both deployments' addresses: the four cards the canvas drew under its feed
 * view, built here under the feed. Every address the repository publishes is
 * on the page, the pair being read says so, and the other pair says what it
 * is: the record of the first deployment, not a link to reading it.
 */

import { useRef, useState } from "react";

import type { NetworkName } from "@/lib/networks";

type Pair = { network: NetworkName; escrow: string; dispute: string; provenance: string };

const short = (address: string) => (address && address.length > 12 ? `${address.slice(0, 6)}...${address.slice(-4)}` : address || "-");

const LABEL = { font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties;

export default function ContractCards({ pairs, reading }: { pairs: Pair[]; reading: NetworkName }) {
  const [copied, setCopied] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const copy = (key: string, address: string) => {
    navigator.clipboard?.writeText(address);
    setCopied(key);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setCopied(""), 1600);
  };

  const cards = pairs.flatMap((pair) =>
    (["escrow", "dispute"] as const).map((role) => ({ key: `${pair.network}-${role}`, role, address: pair[role], pair })),
  );

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", marginTop: "12px" } as React.CSSProperties}>
      {cards.map((card) => {
        const current = card.pair.network === reading;
        return (
          <div key={card.key} style={{ flex: "1 1 205px", minWidth: "0", border: `1px solid ${current ? "rgba(34,211,238,0.35)" : "#1B2130"}`, borderRadius: "0", background: "#0E1119", padding: "18px 20px" } as React.CSSProperties}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "10px" } as React.CSSProperties}>
              <span style={LABEL}>{card.role === "escrow" ? "Escrow" : "Dispute"}, {card.pair.network}</span>
              {current ? (
                <span style={{ ...LABEL, color: "#22D3EE" } as React.CSSProperties}>Reading</span>
              ) : (
                <span style={LABEL}>In the record</span>
              )}
            </div>
            <button type="button" onClick={() => copy(card.key, card.address)} title={card.address} aria-label={`Copy the ${card.pair.network} ${card.role} address, ${card.address}`} style={{ marginTop: "10px", display: "inline-flex", alignItems: "center", gap: "8px", border: "1px solid #263048", borderRadius: "0", background: "#0C1018", color: "#7C8798", font: "500 12px 'Geist Mono', ui-monospace, monospace", padding: "8px 11px", cursor: "pointer" } as React.CSSProperties}>{short(card.address)}</button>
            <p style={{ marginTop: "10px", font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.12em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>{copied === card.key ? "copied" : `${card.pair.network}, ${card.pair.provenance}`}</p>
          </div>
        );
      })}
    </div>
  );
}
