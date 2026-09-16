/**
 * Which network a page reads, and the facts about a network the browser needs
 * as well as the server. No chain or file imports, so client components can
 * use it.
 *
 * Studio Next is the only network a page reads, because the hackathon
 * requires it. studionet, where the same logic, the same prompt and the same
 * strings were first frozen, stays in the record the page shows and is not
 * somewhere the page can be pointed: a network in the address is redirected
 * away. No environment variable moves the default, so no deployment can open
 * on the wrong network by accident.
 */

export const NETWORK_NAMES = ["studionet", "studio-next", "bradbury", "asimov"] as const;

export type NetworkName = (typeof NETWORK_NAMES)[number];

/** What every page reads. */
export const DEFAULT_NETWORK: NetworkName = "studio-next";

/**
 * Whether a verdict's settlement pays out on this network. On Studio Next,
 * consensus v0.6 funds a value transfer only at the root of a transaction's
 * fee allocation tree, and settle's transfers sit two messages below the one that
 * funds them, so the verdict is written to the case and the escrow keeps the
 * money. shared/chain.py settlement_moves says the same for the scripts.
 */
export function settlementMoves(network: NetworkName): boolean {
  return network !== "studio-next";
}
