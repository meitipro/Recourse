# Testing by hand

A protocol for checking Recourse without taking this repository's prose on
trust. Every command below was run on 14 September 2026 (UTC), and what is
quoted under each is what it printed then. Where a command writes to a chain,
it says so: running it again adds payments, and the snapshot has to be
re-taken afterwards.

Two networks are covered. studionet runs the frozen pair in `contracts/`;
Studio Next runs the port in `contracts/v06/`. Every script defaults to
studionet and takes `--network studio-next`. Reading studionet needs
genlayer-py 0.16.3 and reading Studio Next needs 0.19.0rc2, which is what
`requirements.txt` pins; the two cannot share one environment.

## 1. The gate, offline

```bash
GENVM_VERSION=v0.6.0-rc5 python scripts/test.py
```

Needs genvm-linter 0.11.1rc2 on the path. It lints and validates all four
contract files, runs the direct tests, checks house style, holds the README's
test count to pytest, and typechecks the site. It printed:

```
422 passed
=== lint escrow / lint dispute / lint v06/escrow / lint v06/dispute
=== validate escrow / validate dispute / validate v06/escrow / validate v06/dispute
README, docs/RULES.md and pytest agree: 422 direct tests, 1 skipped
all green
```

The direct tests run the contract files through a test double, so they prove
the contracts' own logic and nothing about GenVM. The skipped test needs git
history and skips in a shallow clone.

`python scripts/check.py` is the freeze and house style part on its own. It
printed `contracts frozen at the deployed bytes, unchanged; the ported pair is
the port`: the four files still hash to `contracts/FROZEN.json`, and
`contracts/v06/` is exactly what `scripts/port.py` generates from the first
pair.

## 2. The port is only API names

```bash
cat contracts/v06/PORT.diff
```

The whole difference between the pairs: the runtime header, two imports, and
five API names. `contracts/FROZEN.json` names the five under `v06.diff_is`.

## 3. The deployments are these files

```bash
python scripts/prepare.py && python scripts/verify.py     # studionet
python scripts/verify.py --network studio-next
```

`verify.py` reads each contract's source back off the chain, diffs it against
the repository and lints what came back. It checks the network `deployed.json`
names, so on studionet `prepare.py` comes first; it wrote nothing to the chain
here, since every account was funded and the seller already registered. On
studionet it printed `source matches contracts/escrow.py (28514 bytes)`,
`source matches contracts/dispute.py (21352 bytes)`, the same for both
evaluation instances, and `the deployment matches this repository`. On Studio
Next:

```
escrow  0x3d3fa7Fd2E143C4D6b47D31f15D19B102Ec9e0dA
  source matches contracts/v06/escrow.py (28624 bytes)
dispute  0xba5f285FdB14E3e1d130b3C9346728aBfEC479f4
  source matches contracts/v06/dispute.py (21449 bytes)
evaluation instance for eval/results.studio-next.json  0x67Bb1971C340c24dbE65fBE89acFcF2FaCDb9bB0
  runs the same contracts/v06/dispute.py (21449 bytes)
the deployment matches this repository
```

## 4. The recorded evidence still describes the chain

```bash
python scripts/snapshot.py --check
python scripts/snapshot.py --network studio-next --check
```

Each compares its network's snapshot with the chain and writes nothing. Both
printed `no drift. The recorded evidence still describes the chain.`, over 19
payments on studionet and 7 on Studio Next.

## 5. The evaluation

```bash
python eval/run.py --network studio-next --set v1 --runs 3   # about half an hour
python eval/run.py --network studio-next --set v2 --runs 3   # about six minutes
python eval/report.py && python eval/report.py --set v2
```

Each case runs three times through consensus on a judgment instance the
runner deploys. It writes to the chain. On Studio Next it printed
`accuracy 16/18`, `stability 16/18`, `unclear 2/18`, `wrong 07, 12`, and for
the held out set `accuracy 2/3`, `wrong 21`. `eval/report.py` rebuilds
`eval/RESULTS.md` and `eval/RESULTS-V2.md` from the result files, one column
per network, and neither report has a number typed into it.

## 6. What happens to money on Studio Next

Read it off the chain rather than this file. The Studio Next snapshot keeps
every transaction either contract sent or received, and
`tests/direct/test_snapshot.py` holds it to the README: every settle that ran
there ended `fee no_matching_allocation # external`, every case is still
disputed, and the withdraw and the reclaim the README cites ran. To see a
payout from the top of a transaction, which is the kind that does run:

```bash
python scripts/withdraw.py p-000004 --network studio-next
```

It printed `withdrawn  tx 0x77c1a88e...` and `seller balance  504.00 -> 505.00
GEN`. It writes to the chain, and a payment can be withdrawn once, so on a
second run it is refused.

## 7. The rail claim

```bash
python scripts/rail.py --network studio-next
```

Buys from a seller that settles outside x402, contests, and checks what the
chain stored. It printed `the settlement id appears in none of them` over
fifteen fields, and `wrote docs/rail-proof-studio-next.json`. It writes to the
chain.

## 8. The hosted services

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://recourse-site-seven.vercel.app/
curl -s -X POST https://recourse-linter.vercel.app/api/lint \
  -H "Content-Type: application/json" -d '{"promise":"Returns accurate market data."}'
```

The site answered `200`, and its feed read studionet live, with no snapshot
banner. The linter refused the promise at stage 1, with no model:

```
{"judgeable": false, "reason": "Nothing here is measurable: no number, unit, time bound, count, named field or named source. Say what arrives and how fresh, not how good.", "failed_check": "no measurable term", "suggestion": null, "stage": 1}
```

A promise that passes stage 1 goes to stage 2, which needs a model credential
on the linter's host. The hosted linter has none, and answered
`{"error": "no model is configured, so judgeability cannot be asked"}`.

The MCP server:

```bash
curl -s https://recourse-mcp-eight.vercel.app/api/mcp \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"recourse_stats","arguments":{"network":"studio-next"}}}'
```

It answered with the escrow's and the dispute's live stats read from chain
61997, 7 payments, and an evaluation block of `16/18` for the tuned set and
`2/3` for the held out set on Studio Next, beside studionet's `17/18` and
`1/3`, read from this repository's result files. Asked for `studionet`, it read
chain 61999 instead, 19 payments. Each network is read by its own line of
genlayer-js: 2.0.0-rc.1 for Studio Next, and 1.1.8 for studionet, where every
read through 2.0.0-rc.1 failed with `Missing or invalid parameters`.

## 9. The site, locally

```bash
cd web && npx next build && npx next start -p 4500
```

`web/.env.local`, which `scripts/prepare.py` writes, names the network. Built
for Studio Next, the feed read its payments from chain 61997 through
genlayer-js 2.0.0-rc.1, and section 06 read `16 / 18`, `16 / 18`, `2 / 18` and
`2 / 3`, each tile naming `eval/results.studio-next.json` or its v2 file, with
"the two misses in the first set on studio-next are cases 07 and 12".
Built for studionet, the feed read the escrow live through genlayer-js 1.1.8,
19 payments, 10 disputes opened and 8/10 not honored, with no snapshot banner,
and section 06 read `17 / 18`, `17 / 18`, `3 / 18` and `1 / 3` over
`eval/results.json` and its v2 file.

## 10. The recording, rehearsed

```bash
python scripts/record.py --dry-run
```

Runs nothing and writes nothing. It printed `SCRIPT.md 11 shots in its table,
checked against record.py's plan before this printed, shot for shot, in
order`, then every shot in the order `docs/SCRIPT.md` films them.

## What this does not cover

- The contested path was not run end to end on studionet on 14 September. The
  timings the README prints are medians over the snapshot recorded on 11
  September, and section 4 found no drift from the chain.
- `docs/MUTATIONS.md` is from the mutation run after the port, 32 of 32
  defences caught in each pair. `scripts/mutate.py` refuses to write that file
  if any mutant escapes, and it takes long enough that it was not run again.
- The linter's stage 2 and the clerk were not run: both need a model, and none
  was configured.
