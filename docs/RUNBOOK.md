# Demo runbook

Print this. Follow it exactly, three times clean, before recording.

## Before

- [ ] `python scripts/test.py` is green. Style, both contracts linted, direct tests.
- [ ] `python scripts/deploy.py` run fresh this morning. Studio persistence is
      temporary and yesterday's addresses will be gone.
- [ ] `python scripts/verify.py` says the deployment matches this repository.
      A contract edited after deploying has a published address that no longer
      stands behind the published source.
- [ ] `web/.env.local` carries the addresses `deploy.py` just wrote.
- [ ] Feed open at http://localhost:4500, showing an empty state or the fresh rows.
- [ ] Seller endpoint on http://localhost:4501, mode correct.
- [ ] Terminal font size increased.

## Run

```bash
python scripts/deploy.py          # 1  fresh contracts, funded accounts, seller registered
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

- [ ] The feed row shows the verdict and the elapsed seconds.
- [ ] The seller's upheld counter incremented.
- [ ] The buyer's balance came back.
- [ ] Nothing in the terminal is red.

## What the numbers should look like

Measured on Studio, with judgment starting on acceptance and money moving on
finalization:

    pay                       around 5s
    record_response           around 5s
    open_dispute              around 5s
    dispute to settlement     see the demo output, it is printed every run

The earlier ordering, where the adjudication also waited for finalization,
stacked two appeal windows and measured 89 seconds end to end. Do not quote a
number from memory: `demo.py` prints the real one every time it runs, and it is
the only one worth saying out loud.

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
which becomes its own transaction. The emitting receipt finalizing means only
that the message was queued. On Studio a value message delivered to an ordinary
account is refused, so the payment can read resolved on chain while no balance
moved. Check the payee's balance rather than inferring it from the verdict.

**Everything worked yesterday and is gone today.** Studio persistence is
temporary. Run `scripts/deploy.py`. That is what it is for.
