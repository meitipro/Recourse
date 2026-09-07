import Feed from "@/components/Feed";
import { EXPLORER, NETWORK, loadFeed } from "@/lib/chain";

/**
 * The part of the page that waits on the chain, and nothing else.
 *
 * Reading the feed takes three RPC calls and Studio answers them in anywhere
 * from one second to ten, sometimes with an HTML error page the retry absorbs.
 * When this was awaited at the top of the page, the whole page was blank for
 * that long, and a slow chain looked exactly like a broken site. Streamed
 * behind a Suspense boundary, everything else renders at once and this section
 * shows its skeleton until the chain answers, or its notice if it does not.
 */
export default async function FeedSection() {
  const data = await loadFeed(50);
  const explorer = EXPLORER[NETWORK];
  return (
    <>
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
    </>
  );
}
