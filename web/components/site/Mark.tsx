/**
 * The Recourse mark: one path out, a half turn, one path returning
 * underneath, with the arrowhead against the flow. The geometry is
 * design/logo/README.md's, drawn once on a 32 unit grid, and every size here
 * is that one path. tests/direct/test_design.py holds this path to the pack.
 *
 * Below 20px the 2.6 stroke lands between device pixels and greys out, so the
 * pack's favicon weight, 3.4, is used there. The mark never sits inside a
 * circle or a badge, and it is never rotated or mirrored: the direction of
 * return is the meaning.
 */

export const MARK_PATH = "M7 11H21A6 6 0 0 1 21 23H7M11.5 18.5L7 23L11.5 27.5";

export default function Mark({
  size = 26,
  color = "#22D3EE",
  label,
}: {
  size?: number;
  color?: string;
  /** Set when the mark stands alone for its link; left out beside the wordmark, which already names it. */
  label?: string;
}) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 32 32"
      width={size}
      height={size}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      style={{ display: "block", flex: "0 0 auto" }}
    >
      <path fill="none" stroke={color} strokeWidth={size < 20 ? 3.4 : 2.6} strokeLinecap="square" d={MARK_PATH} />
    </svg>
  );
}
