/**
 * Every failure /app can meet, as a sentence a visitor can act on. No raw
 * error object and no "something went wrong" ever reaches the page.
 *
 * The approach is Fieldwork's humanError: known codes first, then the
 * contract's own sentence with its consensus class stripped, because
 * "[EXPECTED] window closed" is for validators comparing failures and "window
 * closed" is for the person holding the phone.
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

export type Advice = { text: string; action?: "install" | "retry" | "switch" | "faucet" | "reclaim" };

export function humanError(raw: unknown): Advice {
  const error = raw as any;
  const code = error?.code ?? error?.data?.originalError?.code ?? error?.cause?.code;
  const text = String(error?.message ?? error ?? "").replace(/^Error:\s*/i, "");

  if (text === "no_wallet") {
    return { text: "No wallet was found in this browser. Install MetaMask, reload this page, and connect.", action: "install" };
  }
  if (code === 4001 || code === "ACTION_REJECTED" || /user rejected|user denied|denied transaction/i.test(text)) {
    return { text: "You cancelled that in your wallet. Nothing was sent.", action: "retry" };
  }
  if (text === "wrong_network") {
    return { text: "Your wallet is on another network. Switch it to Studio Next to continue.", action: "switch" };
  }
  if (text === "insufficient_balance" || /insufficient funds|exceeds balance/i.test(text)) {
    return { text: "This wallet does not hold enough GEN for the payment, the bond and the fee deposit. The faucet above puts 100 test GEN in it.", action: "faucet" };
  }
  if (text === "undetermined" || /undetermined/i.test(text)) {
    return {
      text: "Consensus did not resolve this one. After the dispute window, either party can call reclaim: the payment goes to the seller and the bond back to the buyer. The case page shows where it stands.",
      action: "reclaim",
    };
  }
  if (/fetch failed|failed to fetch|networkerror|ECONNRESET|timed out|timeout|503|502|504|not answering/i.test(text)) {
    return { text: "Studio Next is not answering right now. Nothing was spent. Try again in a moment.", action: "retry" };
  }

  const cleaned = text.replace(/\[(EXPECTED|EXTERNAL|TRANSIENT|LLM_ERROR)\]\s*/g, "").trim();
  return { text: cleaned ? `The chain refused this: ${cleaned}` : "The chain refused this without a reason.", action: "retry" };
}
