# Testing by hand

A protocol for checking Recourse without taking this repository's prose on
trust. Every command below was run on 15 September 2026 (UTC), and what is
quoted under each is what it printed then, except where a section says it was
not run again and why. Where a command writes to a chain, it says so: running
it again adds payments, and that network's snapshot has to be re-taken
afterwards.

Two networks are covered. studionet runs the frozen pair in `contracts/`;
Studio Next runs the port in `contracts/v06/`. The site reads Studio Next
unless its address asks for studionet. Every script defaults to Studio Next
and takes `--network studionet`. Reading studionet needs genlayer-py 0.16.3 and
reading Studio Next needs 0.19.0rc2, which is what `requirements.txt` pins;
the two cannot share one environment, so here the Studio Next commands run
from `.venv`, which has 0.19.0rc2, and the studionet ones from the system
interpreter, which has 0.16.3.

## 1. The gate, offline

```bash
.venv\Scripts\python scripts\test.py
```

Needs genvm-linter 0.11.1rc2 on the path, which `.venv` has. The system
interpreter's linter cannot fetch the GenVM bundle the gate pins, and its four
validate steps fail with `No GenVM runner bundle for v0.6.0-rc5`. The gate
lints and validates all four contract files, runs the direct tests, checks
house style, holds the README's test count to pytest, and typechecks the site.
It printed:

```
426 passed
=== lint escrow / lint dispute / lint v06/escrow / lint v06/dispute
=== validate escrow / validate dispute / validate v06/escrow / validate v06/dispute
README, docs/RULES.md and pytest agree: 426 direct tests, 1 skipped
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
five API names, `gl.Contract`, `gl.get_contract_at`, `gl.vm.run_nondet_unsafe`,
`gl.message_raw` and the emit stage `accepted`, which consensus v0.6 calls
`decided`. `contracts/FROZEN.json` names the five under `v06.diff_is`.

## 3. The deployments are these files

```bash
python scripts/prepare.py --network studionet && python scripts/verify.py --network studionet
.venv\Scripts\python scripts\prepare.py --network studio-next
.venv\Scripts\python scripts\verify.py --network studio-next
```

`verify.py` reads each contract's source back off the chain, diffs it against
the repository and lints what came back. It checks the network `deployed.json`
names, and `prepare.py` writes that file, so each network's `prepare.py` comes
first: run straight after studionet's, the Studio Next check stopped on
`deployed.json is for studionet but RECOURSE_NETWORK is studio-next`.
`prepare.py` wrote nothing to either chain here: every account was funded and
the seller already registered. On studionet it printed
`source matches contracts/escrow.py (28514 bytes)`,
`source matches contracts/dispute.py (21352 bytes)`, both evaluation instances
running the same `contracts/dispute.py`, 19 payments and 10 cases under live
state, and `the deployment matches this repository`. On Studio Next:

```
escrow  0x3d3fa7Fd2E143C4D6b47D31f15D19B102Ec9e0dA
  source matches contracts/v06/escrow.py (28624 bytes)
dispute  0xba5f285FdB14E3e1d130b3C9346728aBfEC479f4
  source matches contracts/v06/dispute.py (21449 bytes)
evaluation instance for eval/results.studio-next.json  0x67Bb1971C340c24dbE65fBE89acFcF2FaCDb9bB0
  runs the same contracts/v06/dispute.py (21449 bytes)
live state
  payments      11
  cases         6
the deployment matches this repository
```

## 4. The recorded evidence still describes the chain

```bash
python scripts/snapshot.py --network studionet --check
.venv\Scripts\python scripts\snapshot.py --network studio-next --check
```

Each compares its network's snapshot with the chain and writes nothing. The
Studio Next check first answered DRIFT, `payments: snapshot 9, chain 11` and
`not_honored: snapshot 3, chain 4`, because section 6's demo had just added two
payments. `.venv\Scripts\python scripts\snapshot.py --network studio-next`
re-took the snapshot, and both checks then printed `no drift. The recorded
evidence still describes the chain.`, over 19 payments on studionet and 11 on
Studio Next.

## 5. The evaluation

```bash
python eval/run.py --network studio-next --set v1 --runs 3   # the tuned set, eighteen cases
python eval/run.py --network studio-next --set v2 --runs 3   # the held out set, three cases
python eval/report.py && python eval/report.py --set v2
```

Each case runs three times through consensus on a judgment instance the
runner deploys, so it writes to the chain. The runs were not repeated here:
the published numbers are the measurement, and running again for a different
one is not how they are checked. What was checked is what the runs left.
`eval/results.studio-next.json` holds accuracy 16/18, stability 16/18, 2/18
landed on unclear and the misses 07 and 12, and
`eval/results-v2.studio-next.json` holds 2/3 with the miss 21. `eval/report.py`
rebuilt `eval/RESULTS.md` and `eval/RESULTS-V2.md` from the four result files
byte for byte, one column per network, printing
`studio-next accuracy 16/18, stability 16/18` and
`studio-next accuracy 2/3, stability 2/3` beside studionet's `17/18, 17/18`
and `1/3, 2/3`.

## 6. What happens to money on Studio Next

Read it off the chain rather than this file. The Studio Next snapshot keeps
every transaction either contract sent or received, and
`tests/direct/test_snapshot.py` holds it to the README: every settle that ran
there ended `fee no_matching_allocation # external`, every case is still
disputed, and the withdraw and the reclaim the README cites ran. To see a
payout from the top of a transaction, which is the kind that does run:

```bash
.venv\Scripts\python scripts\withdraw.py p-000004 --network studio-next
```

Its first run, on 14 September, withdrew the payment in `0x77c1a88e...`, which
the snapshot keeps with an execution of SUCCESS. A payment can be withdrawn
once: run again on 15 September it wrote a refused transaction,
`0xb6f706f7...`, and stopped on
`withdraw failed: status=ACCEPTED execution=FINISHED_WITH_ERROR [EXPECTED] not open`.

The contested path itself, once, on Studio Next:

```bash
.venv\Scripts\python scripts\demo.py --network studio-next
```

It writes two payments and a dispute to the chain. The honest payment was
p-000010 and the contested one p-000011, which printed:

```
verdict          not_honored
dispute to verdict      30s
settlement       not moved: the escrow still holds the payment and the bond
```

The settlement line came after the agent had watched the escrow for a
minute, and the result block repeated the verdict and that line with no
refund in it.

## 7. The rail claim

```bash
.venv\Scripts\python scripts\rail.py --network studio-next
```

Buys from a seller that settles outside x402, contests, and checks what the
chain stored. It writes to the chain and rewrites
`docs/rail-proof-studio-next.json`, so it was not run again here. The proof it
wrote records p-000005, paid over the external settlement rail, its settlement
id `set_3PxQrLbGk29fVn`, and the verdict not_honored. Read back from the chain
on 15 September, the escrow's row for p-000005 and the dispute contract's case
for it hold 25 fields between them, 15 and 10, and the settlement id is in
none of them.

## 8. The hosted services

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://recourse-site-seven.vercel.app/
curl -s -X POST https://recourse-linter.vercel.app/api/lint \
  -H "Content-Type: application/json" -d '{"promise":"Returns accurate market data."}'
```

The site answered `200`. Its feed read Studio Next live, with no snapshot
banner: 11 payments, 7 disputes opened and 4/6 not honored, the totals
`evidence/snapshot-studio-next.json` keeps, with the Studio Next pair in the
hero's strip and `Reading studio-next / chain 61997` in the footer. At
`/?network=studionet` it read studionet instead: 19, 10 and 8/10, the studionet
pair, and `Reading studionet / chain 61999`.

The linter refused the promise at stage 1, with no model:

```
{"judgeable": false, "reason": "Nothing here is measurable: no number, unit, time bound, count, named field or named source. Say what arrives and how fresh, not how good.", "failed_check": "no measurable term", "suggestion": null, "stage": 1}
```

A promise that passes stage 1 goes to stage 2, which needs a model credential
on the linter's host. The hosted linter has none: `Returns the spot price for
the requested pair, aggregated from at least three venues, with a timestamp no
more than five seconds old.` answered
`{"error": "no model is configured, so judgeability cannot be asked"}`.

The site's clerk asks the same host's judge, so it has no model either:

```bash
curl -s -X POST https://recourse-site-seven.vercel.app/api/clerk \
  -H "Content-Type: application/json" \
  -d '{"promise":"Returns the spot price for the requested pair from at least three venues.","request":"GET /quote?pair=ETH-USD","response":"pair ETH-USD price 4182.10 sources 3"}'
```

It answered HTTP 503 with
`{"error":"a judgment needs a model, and none is configured. Compare against the committed expectation instead: every committed case carries one, in eval/cases.json"}`.
That is the judge's sentence rather than the linter's, because a judgment is
a different question from judgeability. The clerk's panel on the site shows
it with the verdict a loaded committed case expects, to compare against
instead. Once a key is set on the linter's host, stage 2 and the clerk answer
with a verdict; until then neither can be checked.

The MCP server:

```bash
curl -s https://recourse-mcp-eight.vercel.app/api/mcp \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"recourse_stats","arguments":{}}}'
```

Asked with no network it reads Studio Next, the default in
`mcp/addresses.json`: the escrow's and the dispute's live stats from chain
61997, 11 payments, and an evaluation block of `16/18` for the tuned set and
`2/3` for the held out set on Studio Next, beside studionet's `17/18` and
`1/3`, read from this repository's result files. With
`"arguments":{"network":"studionet"}` it reads chain 61999 instead, 19
payments. Each network is read by its own line of genlayer-js, as
`mcp/package.json` pins them: 2.0.0-rc.1 for Studio Next and 1.1.8 for
studionet.

## 9. The site, locally

```bash
cd web && npx next build && npx next start -p 4500
```

The page reads Studio Next unless its address asks for studionet,
`/?network=studionet`; no environment variable names the network, and the
case links and the feed's drawer keep the one asked for. Its feed read
`11 PAYMENTS`, `7 DISPUTES OPENED` and `4/6 NOT HONORED` from chain 61997,
counting the committee's rulings, and the demo's contested row read
`RC-2026-0011`, `JUDGED, ACCEPTED`, `NOT HONORED`. The case page for
RC-2026-0003 read `p-000003 on studio-next` and `disputed (verdict written; on
this runtime the settlement does not move)`, and the hero's lane is labelled
JUDGED. At `/?network=studionet` the lane is labelled RETURNED and the feed read
19 payments, 10 disputes opened and 8/10 not honored, with no snapshot banner.
Section 06 is the same whichever network is read: every tile has a studionet
row and a studio-next row, `17 / 18` and `16 / 18` for accuracy and for
stability, `3 / 18` and `2 / 18` landed on unclear, and `1 / 3` and `2 / 3` for
the held out set, each tile naming the files its rows came from.

## 10. The recording, rehearsed

```bash
.venv\Scripts\python scripts\record.py --network studio-next --dry-run
```

Runs nothing and writes nothing. It printed `SCRIPT.md 11 shots in its table,
checked against record.py's plan before this printed, shot for shot, in
order` and `network studio-next`, then the shot list and every shot in the
order `docs/SCRIPT.md` films them: Terminal B stops at the verdict line, and
at 1:04 the line to wait for is `settlement not moved: the escrow still holds
the payment and the bond`. The take on Studio Next films no refund, because
none comes.

## What this does not cover

- The contested path was not run on studionet in this session. The studionet
  timings the README prints are medians over its snapshot recorded on 11
  September, and section 4 found that snapshot still describes the chain.
- The evaluation and the rail proof were not run again, for the reasons in
  sections 5 and 7.
- `docs/MUTATIONS.md` is from the mutation run after the port, 32 of 32
  defences verified in both pairs. `scripts/mutate.py` refuses to write that
  file if any mutant escapes, and it takes long enough that it was not run
  again.
- The linter's stage 2 and the clerk were not run with a model: the hosted
  linter has no key, and each says so in its own sentence.
