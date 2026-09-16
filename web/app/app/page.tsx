import type { Metadata } from "next";
import Link from "next/link";

import Mark from "@/components/site/Mark";
import RunNow from "@/components/app/RunNow";
import WalletRun from "@/components/app/WalletRun";
import { PAY_GEN, demoSeller, where } from "@/lib/app-server";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Run a dispute | Recourse",
  description: "Watch a real dispute go through a real validator committee on GenLayer Studio Next, with no wallet.",
};

/**
 * /app: a real dispute, on chain, from this page. Tier one is paid by the
 * server and needs nothing from the visitor; tier two is paid and signed by
 * the visitor's own wallet. Both write the same cycle through lib/cycle.ts.
 *
 * The network, the addresses, the RPC and the explorer come from
 * contracts/FROZEN.json and the bond from the same record; nothing on this
 * page is a second copy of any of them.
 */
export default function AppPage() {
  const at = where();
  const seller = demoSeller();
  const bondGen = String(BigInt(bondWei()) / 10n ** 18n);
  const amountGen = String(PAY_GEN);

  return (
    <div style={{ minHeight: "100vh", background: "#0A0C12", color: "#EEF3F8", padding: "0 clamp(16px, 5vw, 40px) 64px" }}>
      <header style={{ maxWidth: "880px", margin: "0 auto", padding: "18px 0", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px" }}>
        <Link href="/" aria-label="Recourse, the site" style={{ display: "inline-flex", alignItems: "center", gap: "10px" }}>
          <Mark size={26} />
          <span style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: 600, fontSize: "13px", letterSpacing: "0.22em", color: "#EEF3F8" }}>RECOURSE</span>
        </Link>
        <Link href="/" style={{ font: "500 12px 'Geist Mono', ui-monospace, monospace", color: "#AEB9C8" }}>Back to the site</Link>
      </header>

      <main style={{ maxWidth: "880px", margin: "0 auto", display: "grid", gap: "clamp(28px, 5vw, 44px)" }}>
        <section style={{ display: "grid", gap: "12px", paddingTop: "clamp(12px, 3vw, 28px)" }}>
          <div style={{ font: "500 10.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.16em", textTransform: "uppercase", color: "#22D3EE" }}>Run it now</div>
          <h1 style={{ margin: 0, fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: 600, fontSize: "clamp(30px, 6vw, 46px)", lineHeight: 1.08, letterSpacing: "-0.02em" }}>
            Watch a real dispute go through a real committee.
          </h1>
          <p style={{ margin: 0, maxWidth: "62ch", fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif", fontSize: "15.5px", lineHeight: 1.65, color: "#AEB9C8" }}>
            One button. An agent pays a seller on GenLayer Studio Next, gets a response that breaks the seller&apos;s promise, checks it, and contests it.
            Five validators judge the case, and you watch each vote land.
          </p>
        </section>

        {at && seller ? (
          <>
            <section aria-labelledby="tier-one" style={{ display: "grid", gap: "12px" }}>
              <h2 id="tier-one" style={{ margin: 0, fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: 600, fontSize: "clamp(20px, 4vw, 26px)" }}>No wallet</h2>
              <RunNow explorer={at.explorer} amountGen={amountGen} bondGen={bondGen} />
            </section>
            <section aria-labelledby="tier-two" style={{ display: "grid", gap: "12px" }}>
              <h2 id="tier-two" style={{ margin: 0, fontFamily: "'Source Serif 4', Georgia, serif", fontWeight: 600, fontSize: "clamp(20px, 4vw, 26px)" }}>With your own wallet</h2>
              <p style={{ margin: 0, maxWidth: "62ch", fontFamily: "'Work Sans', ui-sans-serif, system-ui, sans-serif", fontSize: "14.5px", lineHeight: 1.65, color: "#AEB9C8" }}>
                The same cycle, paid from your balance and signed in your wallet. Studio&apos;s faucet gives the test GEN for it.
              </p>
              <WalletRun at={at} seller={seller} chainName="GenLayer Studio Next" amountGen={amountGen} bondGen={bondGen} />
            </section>
          </>
        ) : (
          <p style={{ margin: 0, color: "#D9A441" }}>This copy of the site has no Studio Next deployment or demo seller on record, so nothing can run here.</p>
        )}
      </main>
    </div>
  );
}

function bondWei(): string {
  try {
    // contracts/FROZEN.json, the record the rest of the site reads the pair from.
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const fs = require("node:fs") as typeof import("node:fs");
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const path = require("node:path") as typeof import("node:path");
    for (const candidate of ["../contracts/FROZEN.json", "../../contracts/FROZEN.json"]) {
      const file = path.join(process.cwd(), candidate);
      if (fs.existsSync(file)) return String(JSON.parse(fs.readFileSync(file, "utf8")).bond_wei ?? "0");
    }
  } catch {
    // unreadable record: the page shows no bond rather than an invented one
  }
  return "0";
}
