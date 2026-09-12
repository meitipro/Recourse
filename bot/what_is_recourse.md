# What Recourse is

x402 settles a machine payment in milliseconds and finally. Once settlement
confirms there is no chargeback path and no dispute window, by design, because a
push payment with no reversal is what lets machines transact without accounts
or credit relationships. Agents can spend money in milliseconds. Nothing in the
stack lets them get it back.

Recourse is the missing dispute right. It holds the payment for a short window,
lets the buying agent contest it, and has GenLayer validators rule.

## The cycle

1. The seller registers and publishes a delivery promise in plain language.
2. The buyer pays into `RecourseEscrow`. Funds enter escrow, not the seller.
3. The response is delivered instantly and recorded on chain, signed by the
   seller over its hash. No judgment runs here, so an honest sale adds no
   latency.
4. A settlement window runs (300 seconds on the frozen deployment). If nobody
   contests, the seller withdraws.
5. To contest, the buyer posts a bond (1 GEN). `RecourseDispute` receives the
   promise, the request, the response, and a timing block the chain wrote, and
   answers one narrow question in both presentation orders.
6. The verdict is written on acceptance and the money moves on finalization.

## The three verdicts

| Verdict | Payment | Bond | Seller record |
| --- | --- | --- | --- |
| honored | to seller | to seller | unchanged |
| not_honored | to buyer | to buyer | upheld plus one |
| unclear | to seller | to buyer | unchanged |

`unclear` exists so the system is never forced to manufacture certainty about
a promise written too loosely to judge. A losing dispute costs the buyer the
bond, or contesting everything is free; an unclear verdict is the promise's
fault rather than the buyer's, so the bond comes back.

## What is measured

Two evaluation sets, both published: 17 of 18 on the set the question was
narrowed against, and 1 of 3 on a held out set committed before it could be
run. Both numbers are always shown together. The pattern they agree on: a
promise that does not settle the question gets answered on its plain words.
Write promises that settle the question. `02-write-a-promise.md` is how.

## Read the live state

Read only, no cost. Python with `genlayer_py`. One thing the SDK insists on:
a read needs a sender address, so a client with no account raises
`No account provided and no account is connected` on its first read. Give it
a throwaway key. It holds nothing, is never stored, and is never used to sign
a write; it exists because the SDK wants a `from`.

```python
import json
from genlayer_py import create_account, create_client, studionet

ESCROW = "0x5125De939F7373eAE741B133FB32B7E9915C8F78"
DISPUTE = "0x80A98929EcA334804dbB04d31F6050bca42C0Cc4"

client = create_client(chain=studionet, account=create_account())   # throwaway, reads only

stats = json.loads(client.read_contract(ESCROW, "stats", []))
# {"bond_amount": "1000000000000000000", "held": "...", "payments": 7, "window_seconds": 300, ...}

recent = json.loads(client.read_contract(DISPUTE, "recent_verdicts", [10]))
# [{"pid": "p-000003", "verdict": 2, "verdict_name": "not_honored", "reason": "...", "decided_at": 1788639536}, ...]
```

Studio allows about thirty requests a minute for the whole node. Read pages
(`recent_rows`, `recent_verdicts`), not rows.

## Studio drops connections, and the SDK does not retry

`genlayer_py` makes one attempt per call and turns a dropped TLS handshake into
a hard failure. Against studionet that happens often enough that a script
following these files verbatim died on its first read while this file was
being verified. Mount a retrying session under the SDK once, before any call:

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from genlayer_py.provider import provider as _provider

session = requests.Session()
session.mount("https://", HTTPAdapter(max_retries=Retry(
    total=12, connect=12, read=6, backoff_factor=0.7,
    status_forcelist=[408, 429, 500, 502, 503, 504],
    allowed_methods=frozenset(["POST", "GET"]), raise_on_status=False,
)))
session.exceptions = requests.exceptions      # the provider looks for this on the module it was given
_provider.requests = session
```

Read retries are safe. A write retried at this layer re-sends the identical
signed bytes, which the node de-duplicates; a write retried by calling
`write_contract` again is a second transaction, because the SDK fetches a new
nonce inside every call. Never wrap `write_contract` in a plain retry loop.
