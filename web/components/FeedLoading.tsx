/**
 * What the feed section shows while the chain is being read.
 *
 * The same four tiles the feed renders, each holding a dash, and one line that
 * says what is happening. Dashes rather than zeros, because a zero here would
 * be an invented number on a page that exists to refuse them; a caption rather
 * than a spinner, because a spinner that runs for ten seconds reads as broken
 * and this one can. If the read fails, the feed itself takes over with its
 * own notice and the last successful read time.
 */
export default function FeedLoading() {
  return (
    <div style={{ marginTop: "2rem" }} aria-busy="true" aria-live="polite">
      <div className="stats">
        {["payments", "disputes opened", "upheld", "median pay to dispute"].map((label) => (
          <div className="stat" key={label}>
            <div className="stat-value">-</div>
            <div className="stat-label">{label}</div>
          </div>
        ))}
      </div>
      <div className="notice">
        Reading the chain. Studio answers in one to ten seconds; the page is not waiting on
        anything else.
      </div>
    </div>
  );
}
