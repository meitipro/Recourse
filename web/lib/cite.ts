/**
 * Case citations, derived off chain and shared by the feed, the case page,
 * the bot and the MCP server: p-000043 decided in 2026 is RC-2026-0043.
 *
 * No chain imports here on purpose. The feed is a client component and must
 * not pull the chain client into the browser bundle to format an id.
 */

export function toPid(caseId: string): string {
  const trimmed = caseId.trim();
  const cite = /^RC-\d{4}-(\d{4,6})$/i.exec(trimmed);
  if (cite) return `p-${cite[1].padStart(6, "0")}`;
  const plain = /^p-(\d{1,6})$/i.exec(trimmed);
  if (plain) return `p-${plain[1].padStart(6, "0")}`;
  if (/^\d{1,6}$/.test(trimmed)) return `p-${trimmed.padStart(6, "0")}`;
  throw new Error(`not a case id: ${caseId}`);
}

/** Four digits minimum, never truncated: p-012345 is RC-2026-12345. */
export function toCitation(pid: string, decidedAt: number): string {
  const year = decidedAt ? new Date(decidedAt * 1000).getUTCFullYear() : new Date().getUTCFullYear();
  return `RC-${year}-${String(parseInt(pid.replace(/^p-/, ""), 10)).padStart(4, "0")}`;
}
