/**
 * What the feed shows while the chain is being read.
 *
 * The design's own skeleton rows and its own wording. Dashes rather than
 * zeros, because a zero here would be an invented number on a page that exists
 * to refuse them, and a sentence rather than a spinner, because a spinner that
 * runs for ten seconds reads as broken and this one can.
 */

const HEAD: React.CSSProperties = {
  font: "500 9.5px 'Geist Mono', ui-monospace, monospace",
  letterSpacing: "0.14em",
  textTransform: "uppercase",
  color: "#7C8798",
};

const GRID: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "104px minmax(140px, 1.6fr) 96px 124px 136px 92px",
  gap: "12px",
  alignItems: "center",
};

const BAR: React.CSSProperties = {
  height: "9px",
  borderRadius: "3px",
  background: "#1B2130",
  animation: "rc-shimmer 1.5s ease-in-out infinite",
};

const TILES = ["Payments", "Disputes opened", "Upheld", "Median pay to dispute"];

export default function FeedSkeleton() {
  return (
    <div style={{ border: "1px solid #1B2130", borderRadius: "0", background: "#0E1119", overflow: "hidden" }} aria-busy="true" aria-live="polite">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", borderBottom: "1px solid #1B2130" }}>
        {TILES.map((label) => (
          <div key={label} style={{ padding: "clamp(14px, 2vw, 20px)", borderRight: "1px solid #151A25" }}>
            <div style={{ font: "500 clamp(22px, 3vw, 30px)/1 'Geist Mono', ui-monospace, monospace", color: "#7C8798", fontVariantNumeric: "tabular-nums" }}>-</div>
            <div style={{ marginTop: "9px", ...HEAD }}>{label}</div>
          </div>
        ))}
      </div>

      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "12px",
          padding: "13px clamp(14px, 2vw, 20px)",
          background: "#0C1018",
          border: "1px dashed #263048",
        }}
      >
        <div style={{ minWidth: "0" }}>
          <div style={{ font: "500 10px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#7C8798" }}>
            Reading the chain
          </div>
          <p style={{ marginTop: "7px", fontSize: "13px", lineHeight: "1.6", color: "#AEB9C8", maxWidth: "78ch" }}>
            Studio answers in one to ten seconds; the page is not waiting on anything else. If it has not
            answered in twenty, the recorded snapshot takes over and says so.
          </p>
        </div>
      </div>

      <div style={{ ...GRID, padding: "12px clamp(14px, 2vw, 20px)", borderBottom: "1px solid #1B2130", background: "#0C1018" }}>
        <span style={HEAD}>Time</span>
        <span style={HEAD}>Case / seller</span>
        <span style={HEAD}>Amount</span>
        <span style={HEAD}>Status</span>
        <span style={HEAD}>Verdict</span>
        <span style={{ ...HEAD, textAlign: "right" }}>To dispute</span>
      </div>

      {[{ w: "82%" }, { w: "64%" }, { w: "88%" }, { w: "71%" }].map((row, index) => (
        <div key={index} style={{ ...GRID, padding: "17px clamp(14px, 2vw, 20px)", borderBottom: "1px solid #151A25" }}>
          <span style={{ ...BAR, width: "74%" }} />
          <span style={{ ...BAR, width: row.w }} />
          <span style={{ ...BAR, width: "62%" }} />
          <span style={{ ...BAR, height: "18px", borderRadius: "0", width: "84px" }} />
          <span style={{ ...BAR, height: "18px", borderRadius: "0", width: "96px" }} />
          <span style={{ ...BAR, width: "54%", marginLeft: "auto" }} />
        </div>
      ))}
    </div>
  );
}
