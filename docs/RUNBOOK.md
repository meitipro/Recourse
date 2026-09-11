# Demo runbook

Print this. Follow it exactly, three times clean, before recording.

## Before

- [ ] `python scripts/test.py` is green. Style, both contracts linted, direct tests.
- [ ] `python scripts/prepare.py` run today. The contracts are frozen and are
      not redeployed; this funds the three accounts, registers the seller on
      the frozen escrow, and writes `deployed.json` and `web/.env.local`.
- [ ] `python scripts/verify.py` says the deployment matches this repository.
      A contract edited after deploying has a published address that no longer
      stands behind the published source.
- [ ] `web/.env.local` carries the frozen addresses `prepare.py` just wrote.
- [ ] Feed open at `http://localhost:4500`, showing an empty state or the fresh rows.
- [ ] Seller endpoint on `http://localhost:4501`, mode correct.
- [ ] Terminal font size increased.

## Run

```bash
python scripts/prepare.py         # 1  funded accounts, seller registered on the frozen contracts
python scripts/demo.py            # 2  both paths, one command
```

`demo.py` does the whole sequence and prints the timings. To drive it by hand
instead, for a slower and more legible recording:

```bash
python seller/main.py                                    # terminal 1
genlayer call <escrow> get_seller --args <seller>        # 3  show the promise on chain
python agent/run.py --no-dispute                         # 4  the honest path
curl -X POST localhost:4501/admin/mode -d '{"mode":"stale"}'   # 5  flip the switch
python agent/run.py --mode stale                         # 6  the contested path
```

Watch the feed row appear, move to judged, then settle.

## After

- [ ] The feed row shows the verdict and the seconds from payment to dispute. That column is the chain's own clock and is not settlement time; the demo prints settlement by wall clock.
- [ ] The seller's upheld counter incremented.
- [ ] The buyer's balance came back.
- [ ] Nothing in the terminal is red.
- [ ] `python scripts/snapshot.py` run after the last cycle, so
      `evidence/snapshot.json` holds what was just recorded and
      `python scripts/test.py` is green with it. Studio's persistence is
      temporary; the snapshot is what outlives it.

## Before publishing anything

Run this after the last cycle that touched the chain, and read the answer:

```bash
python scripts/snapshot.py --check
```

It compares the recorded snapshot's payment count and verdict distribution
against the chain and writes nothing. Three answers, and only one of them means
carry on:

| it says | what to do |
| --- | --- |
| no drift | nothing. The published totals still describe the chain |
| DRIFT, with the lines that differ | `python scripts/snapshot.py`, then check the totals in `README.md` against it |
| chain unreachable | nothing is wrong. Drift cannot be measured without the chain, so it exits zero and says so |

**This is not in `scripts/test.py`, on purpose.** The ten snapshot tests are
one directional: they hold the snapshot to the repository, so writing to the
chain never fails them, it only makes the snapshot quietly stale. A gate that
needs the network is a gate people learn to ignore, so this is a command
somebody runs and reads rather than one CI runs for them.

## The two README images

```bash
cd web && npx next build && LINTER_URL=http://127.0.0.1:4503/lint npx next start -p 4500
python linter/serve.py            # another terminal, for the linter shot
python docs/shots.py              # drives the Chrome already on this machine
```

It writes `docs/images/feed.png` and `docs/images/linter.png` from a production
build, so no development indicator lands in the picture. The feed shot waits
until the four tiles carry numbers, because a capture mid load shows dashes.
The linter shot types "Returns accurate market data.", the promise payment
p-000014 ran on chain, and waits for the refusal; stage 1 answers that one
without a model, so this needs no key.

Recapture whenever the chain totals change, and rewrite both captions in the
same commit to describe what the new images show.

## What the numbers should look like

Measured on Studio, with judgment starting on acceptance and money moving on
finalization. Each write is accepted in around five seconds:

    pay                       around 5s
    record_response           around 5s
    open_dispute              around 5s

The two figures that matter are medians over every dispute on the public
record, kept in `evidence/snapshot.json` under `totals` and printed at the top
of the README: `median_dispute_to_verdict_seconds` and
`median_dispute_to_money_back_seconds`. One run lands ten or twenty seconds
either side of them.

The earlier ordering, where the adjudication also waited for finalization,
stacked two appeal windows and measured 89 seconds to the verdict alone. Do not
quote a number from memory: `demo.py` prints the real one every time it runs,
and it is the only one worth saying out loud.

**Say the right one out loud.** The verdict lands in about a minute and the
money later, because the settlement message only fires once the judgment
transaction finalizes. Those are two separate transactions and the second is
the one that matters to the buyer. If the video says "money back in under a
minute" over a run that took a hundred seconds, a judge with the receipt open
will see it. Say "the verdict lands in about a minute and the money follows on
finality", which is both true and a better answer, because paying out before
finality would mean a successful appeal could reverse a verdict after the
money had gone.

## If something goes wrong

Read the receipt before changing any code.

```bash
genlayer receipt <txHash> --stdout --stderr    # always first
genlayer schema  <address>                     # confirm the interface
genlayer code    <address>                     # confirm what is deployed
```

**A refusal the contract raised is plain text in stderr**, not in any error
field. `shared/chain.py::check` surfaces it, so a failure from `Chain.send`
already carries the sentence the contract raised.

**Accepted is not success.** A receipt containing a user error can be Accepted,
because validators can agree that an error is the correct execution result. Read
the execution result too.

**The status comes back as a number.** Consensus v0.6 defines fourteen and a node
answers with the code, not the name. Five is Accepted, seven is Finalized.
`status_name` in `shared/chain.py` maps them.

**Every RPC call failing.** Studio drops TLS handshakes in bursts. The session in
`shared/chain.py` retries at the connection layer. If you have removed it, put it
back: a plain post succeeded three times in four here and failed ten times
running inside one burst.

**Money did not move after a verdict.** The settlement is an emitted message,
which becomes its own transaction and lands when the emitting one finalizes,
about half a minute after the verdict is accepted. A balance read the instant
the status turns resolved shows money still in flight as money that never
came. `agent/run.py` and `scripts/withdraw.py` poll the balance for up to
ninety seconds for that reason; do the same rather than inferring it from the
verdict.

**Everything worked yesterday and is gone today.** Studio persistence is
temporary, and the frozen pair goes with it. `evidence/snapshot.json` and
`evidence/receipts/` hold what the chain held, and the site shows them, saying
so, when the chain no longer answers. Redeploying is a `--unfreeze` and
invalidates every published number; `contracts/FROZEN.json` lists what a
redeploy has to redo before anything is published again.
