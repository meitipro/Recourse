/**
 * Which network a page reads, and the facts about a network the browser needs
 * as well as the server. No chain or file imports, so client components can
 * use it.
 *
 * Studio Next is the default, because the hackathon requires it. studionet
 * runs the same logic, the same prompt and the same strings, and a page reads
 * it when its address asks: ?network=studionet. No environment variable moves
 * the default, so no deployment can open on the wrong network by accident.
 */

export const NETWORK_NAMES = ["studionet", "studio-next", "bradbury", "asimov"] as const;

export type NetworkName = (typeof NETWORK_NAMES)[number];

/** What a page reads when its address names no network. */
export const DEFAULT_NETWORK: NetworkName = "studio-next";

/** The query that keeps a link on the network being read. The default needs none. */
export function networkQuery(network: NetworkName): string {
  return network === DEFAULT_NETWORK ? "" : `?network=${network}`;
}

/**
 * Whether a verdict's settlement pays out on this network. On Studio Next,
 * consensus v0.6 funds a value transfer only at the root of a transaction's
 * allocation tree, and settle's transfers sit two messages below the one that
 * funds them, so the verdict is written to the case and the escrow keeps the
 * money. shared/chain.py settlement_moves says the same for the scripts.
 */
export function settlementMoves(network: NetworkName): boolean {
  return network !== "studio-next";
}
