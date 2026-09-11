# Sources

A few claims on the site and in the README rest on something outside this
repository: how x402 settles, who governs it, what Mastercard and OpenAI do
about disputes, and how much x402 is used. Each is listed below with the page
it was checked against on 11 September 2026 and what that page says, in our
words rather than theirs.

Everything else the site shows is read from the chain, from
`evidence/snapshot.json` or from a committed results file, and
`tests/direct/test_snapshot.py` holds the README to those same files.

## How x402 settles

| claim | where it appears | source | what the source says |
| --- | --- | --- | --- |
| x402 settles a payment in milliseconds | README, opening; site, 02 The gap | [PayAI: Sub-second x402 settlement on Base with Flashblocks](https://blog.payai.network/sub-second-x402-settlement-on-base-with-flashblocks/), 24 July 2026 | median settlement on Base measured at about 750 ms with Flashblocks, from about 1.7 s before |
| | | [RZLT: agentic payments in 2026, an x402 explainer](https://www.rzlt.io/blog/agentic-payments-2026-x402-explainer), dated 14 July 2026 | same-chain settlement in production is sub-second; cross-chain fills take 2 to 8 seconds |
| settlement is final, with no chargeback path and no dispute window | README, opening; site, 02 The gap | [x402.org](https://x402.org/) | sets x402 against the payment methods it replaces, which it describes as slow and exposed to chargebacks and fees |
| one rail across chains and providers | site, 02 The gap, row 03 | [x402 docs: Networks and token support](https://docs.x402.org/core-concepts/network-and-token-support) | any EVM chain, plus Solana, Stellar, Algorand, Aptos, NEAR, XRPL and others, each named by a CAIP-2 identifier |
| | | [x402 docs: Facilitator](https://docs.x402.org/core-concepts/facilitator) | several facilitators run in production, across Base, Solana, Polygon, Avalanche and more |
| 69,000 active agents and 165 million x402 transactions by April 2026 | site, 02 The gap, row 03 | [RZLT](https://www.rzlt.io/blog/agentic-payments-2026-x402-explainer) | more than 165 million x402 transactions across 69,000 active agents by April |

## Who governs it

| claim | where it appears | source | what the source says |
| --- | --- | --- | --- |
| governance moved under the Linux Foundation, with Visa, Mastercard, American Express, Stripe and Google among its members | site, 02 The gap, row 01 | [Linux Foundation: operational launch of the x402 Foundation](https://www.linuxfoundation.org/press/linux-foundation-announces-operational-launch-of-x402-foundation-to-standardize-internet-native-payments-for-ai-agents-and-applications), 14 July 2026 | all five are among seventeen premier members, out of forty founding members |
| those companies now sit on the board of the rail | site, 02 The gap, closing line | [x402 Foundation: Members](https://x402.org/members/) | premier membership carries an appointed seat on the Governing Board, and all five are listed as premier |
| they spent fifty years building the modern chargeback | site, 02 The gap, closing line | [15 U.S.C. 1666 at Cornell LII](https://www.law.cornell.edu/uscode/text/15/1666) | the right to dispute a billing error with the card issuer was added by the Fair Credit Billing Act, Pub. L. 93-495, on 28 October 1974: fifty two years before this build |

## Disputes where the card rails are used

| claim | where it appears | source | what the source says |
| --- | --- | --- | --- |
| Mastercard's agent tokens preserve dispute rights | site, 02 The gap, row 02 | [Mastercard: Agentic token framework](https://www.mastercard.com/global/en/news-and-trends/stories/2025/agentic-commerce-framework.html), 14 October 2025 | the purchase intent data carried with an agentic token gives the merchant an audit trail for avoiding and resolving cardholder disputes |
| | | [Mastercard: How Verifiable Intent builds trust in agentic AI commerce](https://www.mastercard.com/us/en/news-and-trends/stories/2026/verifiable-intent.html), 5 March 2026 | when a dispute arises over an agent's purchase, every party can rely on the recorded authorization to resolve it |
| OpenAI's delegated credentials preserve dispute rights | site, 02 The gap, row 02 | [OpenAI: Agentic Commerce key concepts](https://developers.openai.com/commerce/guides/key-concepts) | OpenAI is not the merchant of record |
| | | [OpenAI: Agentic Commerce production guide](https://developers.openai.com/commerce/guides/production) | the merchant, as merchant of record, handles refunds and chargebacks |

Both Mastercard pages refuse scripted requests and open normally in a browser,
so a link checker reports them as 403 when they are not broken.
