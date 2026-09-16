# Demo runbook

Print this. The take is on Studio Next, as `docs/SCRIPT.md` says, and every
command that touches Studio Next runs from the project's `.venv`, which holds
the v0.6 SDK that network needs. Walk the take with
`.venv\Scripts\python scripts\record.py --network studio-next --dry-run` three
times, run it once for real, then record.

## When: the recording, then the tail

The recording is the step immediately before the tail. It spends payments on
Studio Next, so the snapshot and the feed image must both come after it, in
that order.

`scripts/record.py` drives the take from Terminal A in the order
`docs/SCRIPT.md` films it: it prints each shot's label, runs what the shot
runs, opens the stopwatch beside itself when the dispute line prints, and
waits for a key at every switch to a browser tab. `--dry-run` walks the same
sequence without running anything or writing to the chain. It stops at the
first shot whose line never prints, names the shot and what SCRIPT.md expects
there, and retries nothing.

The tail, in this order, no step skipped:

1. **Every chain write finishes, the recording's included.**
   `prepare.py --network studio-next`, the one real run and the recording
   itself, its optional withdraw shot too, all write to Studio Next, as does
   any other script run with `--network studio-next`. The imports,
   `scripts/smoke.py`, the site's clerk and the bot write nothing to it.
2. `.venv\Scripts\python scripts\snapshot.py --network studio-next`. The
   record catches up to the chain.
3. The same with `--check`, which must say no drift. Drift means something in
   step 1 had not finished.
4. `python docs/shots.py`, as under "The two README images" below, and the feed
   caption rewritten to what the new image shows. It comes after the snapshot,
   not merely after the chain writes, because the image and the snapshot must
   agree.
5. `.venv\Scripts\python scripts\test.py`, green. Between steps 2 and 4 it
   fails on purpose whenever the snapshot gained a payment: the feed image and
   its caption are held to the snapshot, and so is the Studio Next timing at
   the top of the README.
6. The hand check: `python scripts/hand_check.py`, then walk
   `docs/HAND-CHECK.md` by hand: every README number beside the file behind
   it, every link with what it answered, and the order a stranger reads them
   in. The script reads and never fails; the ticking is by hand.

Reversing any two of these produces a repository that looks correct and is
not. Submit after step 6.

## Before

- [ ] `.venv\Scripts\python scripts\test.py` is green. Style, both pairs linted and validated, direct tests.
- [ ] `.venv\Scripts\python scripts\prepare.py --network studio-next` run today. The contracts are frozen and are
      not redeployed; this funds the three accounts, registers the seller on
      the ported escrow, and writes `deployed.json` for Studio Next.
- [ ] `.venv\Scripts\python scripts\verify.py --network studio-next` says the deployment matches this
      repository. A contract edited after deploying has a published address
      that no longer stands behind the published source.
- [ ] Feed open at `http://localhost:4500`, a production build. It reads Studio
      Next and nothing else, so there is nothing to set.
- [ ] The seller endpoint: nothing to start. `demo.py` starts it on `http://localhost:4501`.
- [ ] Terminal font size increased.

## Run

```bash
.venv\Scripts\python scripts\prepare.py --network studio-next   # 1  funded accounts, seller registered on the ported pair
.venv\Scripts\python scripts\demo.py --network studio-next      # 2  both paths, one command
```

`demo.py` does the whole sequence, with the buyer agent's lines on screen as
each step happens. To drive it by hand instead, the agent reads its network
from `RECOURSE_NETWORK`, so set it first in the agent's terminal:

```bash
python seller/main.py                                            # terminal 1
$env:RECOURSE_NETWORK="studio-next"                              # terminal 2, PowerShell
.venv\Scripts\python agent/run.py --no-dispute                   # 3  the honest path
curl -X POST localhost:4501/admin/mode -d '{"mode":"stale"}'     # 4  flip the switch
.venv\Scripts\python agent/run.py --mode stale                   # 5  the contested path
```

Watch the feed row appear and move to judged, accepted. On Studio Next it
stays there: the verdict is written to the case and the settlement does not
move.

## After

- [ ] The feed row shows the verdict and the seconds from payment to dispute. That column is the chain's own clock and is not settlement time.
- [ ] The seller's upheld counter did not move. It moves on settlement, and on
      Studio Next the settlement does not run; the demo's `seller record` line
      shows it unchanged.
- [ ] The buyer's balance did not come back. The escrow keeps the payment and
      the bond, and the agent's `settlement` line says `not moved`. The money
      path completes on studionet.
- [ ] Nothing in the terminal is red.
- [ ] After the last cycle, the tail at the top of this page from step 2: the
      snapshot, `--check`, the feed image and its caption, the gate, the hand
      check. Studio's persistence is temporary; the snapshot is what outlives
      it.

## Before publishing anything

Run this after the last cycle that touched the chain, and read the answer:

```bash
.venv\Scripts\python scripts\snapshot.py --check
```

It compares the Studio Next snapshot, its payment count and verdict
distribution, with the chain and writes nothing. Three answers, and only one
of them means carry on:

| it says | what to do |
| --- | --- |
| no drift | nothing. The published totals still describe the chain |
| DRIFT, with the lines that differ | the tail from step 2: the snapshot of that network, this check again, the feed image and its caption, the gate, then the totals in `README.md` by hand |
| chain unreachable | nothing is wrong. Drift cannot be measured without the chain, so it exits zero and says so |

**This is not in `scripts/test.py`, on purpose.** The snapshot tests are one
directional: they hold the snapshot to the repository, so writing to the chain
never fails them, it only makes the snapshot quietly stale. A gate that needs
the network is a gate people learn to ignore, so this is a command somebody
runs and reads rather than one CI runs for them.

## The two README images

```bash
cd web && npx next build && LINTER_URL=http://127.0.0.1:4503/lint npx next start -p 4500
python linter/serve.py            # another terminal, for the linter shot
python docs/shots.py              # drives the Chrome already on this machine
```

It writes `docs/images/feed.png` and `docs/images/linter.png` from a production
build, so no development indicator lands in the picture. The feed shot is of
the page as it opens, which reads Studio Next, and waits until the four tiles
carry numbers, because a capture mid load shows dashes. The linter shot types
"Returns accurate market data.", the promise payment p-000014 ran on chain on
studionet, and waits for the refusal; stage 1 answers that one without a
model, so this needs no key.

Recapture whenever the chain totals change, and rewrite both captions in the
same commit to describe what the new images show. The script writes what the
four tiles read, and the network the footer names, to `docs/images/feed.json`,
and `tests/direct/test_snapshot.py` holds that file and the feed caption to
that network's snapshot, so once a snapshot records a new payment the gate
fails until the picture is retaken. The picture once said fourteen payments
while the snapshot said nineteen, and nothing failed.

## What the numbers should look like

Each write is accepted in around five seconds, on either network:

    pay                       around 5s
    record_response           around 5s
    open_dispute              around 5s

The figures that matter are medians over every dispute on each network's
public record, kept in its snapshot under `totals` and printed at the top of
the README. On Studio Next there is one, `median_dispute_to_case_seconds` in
`evidence/snapshot-studio-next.json`: the dispute to the verdict written to the
case, because the settlement never runs there. On studionet there are two,
`median_dispute_to_verdict_seconds` and `median_dispute_to_money_back_seconds`
in `evidence/snapshot.json`. One run lands ten or twenty seconds either side
of them.

The earlier ordering, where the adjudication also waited for finalization,
stacked two appeal windows and measured 89 seconds to the verdict alone. Do not
quote a number from memory: `demo.py` prints the real one every time it runs,
and it is the only one worth saying out loud.

**Say the right one out loud.** On Studio Next, the take's network, the
verdict is written and the settlement does not move: say that, as
`docs/SCRIPT.md` does, and never imply a refund. On studionet the verdict lands
in about a minute and the money later, because the settlement message only
fires once the judgment transaction finalizes. There, say "the verdict lands
in about a minute and the money follows on finality", never "money back in
under a minute" over a run that took a hundred seconds: paying out before
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

**Money did not move after a verdict.** On Studio Next it never does: every
settle there ends `fee no_matching_allocation # external`, which is the
runtime's fee rule and not a bug to chase; the README's "Settlement on Studio
Next" has the reason. On studionet the settlement is an emitted message, which
becomes its own transaction and lands when the emitting one finalizes, about
half a minute after the verdict is accepted. A balance read the instant the
status turns resolved shows money still in flight as money that never came.
`agent/run.py` and `scripts/withdraw.py` poll the balance for up to ninety
seconds for that reason; do the same rather than inferring it from the
verdict.

**Everything worked yesterday and is gone today.** Both testnets' persistence
is temporary, and the pairs go with it. `evidence/snapshot.json`,
`evidence/snapshot-studio-next.json` and `evidence/receipts/` hold what each
chain held, and the site shows them, saying so, when a chain no longer
answers. Redeploying is a `--unfreeze` and invalidates every published number;
`contracts/FROZEN.json` lists what a redeploy has to redo before anything is
published again.
