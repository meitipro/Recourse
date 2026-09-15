/**
 * The footer, ported from the canvas. The article link the canvas carried is
 * not here: nothing is published at that address yet, and a link that names a
 * page which does not exist is the sort of claim this site refuses elsewhere.
 *
 * It names the network the page is reading, which follows the address, and
 * then every other deployment the freeze record holds, each a link that reads
 * it instead. So the footer and the evaluation's columns name the same
 * networks, and the footer never names one the page is not reading.
 */

import { Fragment } from "react";

import { networkQuery, type NetworkName } from "@/lib/networks";

export default function SiteFooter({
  network,
  deployments,
}: {
  network: NetworkName;
  deployments: Array<{ network: NetworkName; chainId: number }>;
}) {
  const reading = deployments.find((one) => one.network === network);
  const others = deployments.filter((one) => one.network !== network);
  return (
    <>
  <footer style={{ borderTop: "1px solid #1B2130", background: "#0C1018" } as React.CSSProperties}> <div style={{ padding: "clamp(28px, 4vw, 40px) clamp(20px, 5vw, 100px) clamp(34px, 5vw, 48px)", display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "flex-start", gap: "24px" } as React.CSSProperties}> <div> <div style={{ font: "500 15px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.22em", color: "#EEF3F8" } as React.CSSProperties}>RECOURSE</div> <p style={{ marginTop: "9px", font: "500 12px 'Geist Mono', ui-monospace, monospace", color: "#7C8798" } as React.CSSProperties}>A dispute right for machine payments</p> <p style={{ marginTop: "5px", font: "500 12px 'Geist Mono', ui-monospace, monospace", color: "#AEB9C8" } as React.CSSProperties}>Reading {network} / chain {reading?.chainId ?? "-"}</p> {others.length ? (<p style={{ marginTop: "5px", font: "500 12px 'Geist Mono', ui-monospace, monospace", color: "#7C8798" } as React.CSSProperties}>Also deployed on {others.map((one, index) => (<Fragment key={one.network}>{index ? ", " : ""}<a href={`/${networkQuery(one.network)}`} style={{ color: "#AEB9C8" } as React.CSSProperties} className="rc-hover-5">{one.network} / chain {one.chainId}</a></Fragment>))}</p>) : null} </div> <nav style={{ display: "flex", flexWrap: "wrap", gap: "18px", font: "500 12.5px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.06em", textTransform: "uppercase" } as React.CSSProperties}> <a href="https://github.com/meitipro/Recourse" target="_blank" rel="noreferrer" style={{ color: "#AEB9C8" } as React.CSSProperties}>Repository</a>  <a href="https://genlayer.com" target="_blank" rel="noreferrer" style={{ color: "#AEB9C8" } as React.CSSProperties}>GenLayer</a> <a href="https://x.com/meitipro1" target="_blank" rel="noreferrer" style={{ color: "#AEB9C8" } as React.CSSProperties}>@meitipro1</a> </nav> </div> </footer>
    </>
  );
}
