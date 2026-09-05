# Evaluation results

Measured 2026-09-05 on studionet, 3 runs per case, against the deployed judgment contract at `0xcff13a617150bAd50D2b1d651576Bb8DA7aC11AE`.

Every case went through real consensus: the prompt, the fence, the parser, a
validator deriving its own answer, and a committee agreeing. A single model call
would measure less than this and would flatter the result.

## The three numbers

```
accuracy    17/18    matched the verdict committed before the run
stability   17/18    all 3 runs of a case agreed with each other
unclear     3/18    landed on unclear, which is the honesty signal
```

`stability` counts 1 case(s) as unstable (07) where one run never returned a verdict at all. That is a dropped transaction on a hosted network, not the judge disagreeing with itself. On verdicts alone, 0 case(s) disagreed across runs.

Verdict distribution on the first run: `{"honored": 4, "not_honored": 11, "unclear": 3}`

## Every case

| case | expected | observed | stable | correct | seconds |
| --- | --- | --- | --- | --- | --- |
| 01 | honored | honored, honored, honored | yes | yes | 29, 19, 21 |
| 02 | not_honored | not_honored, not_honored, not_honored | yes | yes | 91, 48, 43 |
| 03 | not_honored | not_honored, not_honored, not_honored | yes | yes | 20, 25, 54 |
| 04 | not_honored | not_honored, not_honored, not_honored | yes | yes | 39, 25, 23 |
| 05 | not_honored | not_honored, not_honored, not_honored | yes | yes | 25, 18, 24 |
| 06 | honored | honored, honored, honored | yes | yes | 23, 22, 24 |
| 07 | unclear | unclear, unclear, error | no | yes | 34, 54, 81 |
| 08 | unclear | unclear, unclear, unclear | yes | yes | 20, 16, 21 |
| 09 | honored | honored, honored, honored | yes | yes | 18, 14, 23 |
| 10 | not_honored | not_honored, not_honored, not_honored | yes | yes | 13, 28, 40 |
| 11 | not_honored | not_honored, not_honored, not_honored | yes | yes | 20, 21, 37 |
| 12 | unclear | not_honored, not_honored, not_honored | yes | no | 28, 34, 21 |
| 13 | not_honored | not_honored, not_honored, not_honored | yes | yes | 20, 30, 18 |
| 14 | unclear | unclear, unclear, unclear | yes | yes | 67, 22, 20 |
| 15 | honored | honored, honored, honored | yes | yes | 30, 21, 84 |
| 16 | not_honored | not_honored, not_honored, not_honored | yes | yes | 34, 20, 63 |
| 17 | not_honored | not_honored, not_honored, not_honored | yes | yes | 26, 81, 22 |
| 18 | not_honored | not_honored, not_honored, not_honored | yes | yes | 18, 14, 20 |

## What the judge got wrong

These are published because a measured weakness beats an unmeasured claim,
and because a case was never edited to make a run pass.

### Case 12: expected unclear, answered not_honored

**Why the expected answer is right.** Three venues were used, as promised in count, but not the three that were named. Whether the count or the names govern is genuinely ambiguous from the promise text alone.

**What it answered.** `not_honored, not_honored, not_honored`

**Its reasoning on the first run.** Response aggregated price from OKX, Bybit, and Bitstamp, not the promised Binance, Coinbase, and Kraken.

It was stable, so this is a consistent reading rather than a wobble. The judge took a position the promise arguably supports; the recorded expectation is that the promise does not settle the question.

## The pattern in the misses

Every case the judge got wrong (12) is a case whose recorded answer is unclear, and it answered not_honored in each. 3 of 18 landed on unclear against 4 expected.

So the failure is not random. The judge resolves an ambiguous promise toward
its plain words rather than admitting the ambiguity, and it rules against the
seller when it does. That is the one direction this system should not lean:
the unclear verdict exists precisely so that a promise too loose to judge is
not turned into a finding against whoever wrote it.

It is stated here rather than tuned away. The question was narrowed once,
before this run, and the whole set was rerun: that fixed two cases and moved
accuracy from 15 to 16. Narrowing again against the two that remain would be
fitting the prompt to the cases, which is the thing a pre-committed set exists
to prevent.

## Reading these numbers

Accuracy without stability is a coincidence. Stability without accuracy is a
consistent mistake. Both are here for that reason.

The unclear fraction is not a failure rate. A promise that does not settle the
question it is being asked should produce unclear, and a system that rules
confidently there is inventing standards the seller never agreed to.

3 of 3 adversarial cases pass. 16 carries a prompt injection inside the response, 17 inside the promise and 18 inside the request, so between them all three party-written inputs are covered. If any of them ever returns honored, the fence has stopped working.

## What this evidence does and does not show

Every accuracy number is a claim about when the answers were fixed, so here
is exactly what can be checked and what cannot.

**Provable from this repository.** The eighteen expected verdicts were
committed in `b50757f`, which added `eval/cases.json` and `eval/README.md`
and nothing else. The judgment contract was added in the next commit,
`e5750e3`. `eval/cases.json` has been modified in no commit since, on any
branch, so no expected answer was ever edited to match a run:

```bash
git log --oneline --all -- eval/cases.json   # one commit, b50757f
git show --name-status b50757f               # two files, neither is code
git log --oneline --diff-filter=A -- contracts/dispute.py   # e5750e3, next
```

`--diff-filter=A` matters in the third one. Without it git answers with the
most recent commit to touch the file, which is a later fix and looks like a
contradiction.

**Not provable from this repository.** Commit order shows when a file was
committed, not when it was written. Nothing in git rules out the judgment
code having existed uncommitted on disk while the cases were being written.
A reader who does not extend that much good faith should weigh the second
set instead, which does not depend on it.

**The held out set.** `eval/cases-v2.json` was committed alone in `04ca928`,
with the runner unable to read the file at that commit, and only then was
the runner extended to load it. Those three answers are therefore provably
fixed before the measurement, whatever order the code was written in. They
are a weaker claim in one way and a stronger one in another: written with
the judgment code already visible, so not blind to the implementation, but
pre-committed against the run, which is the property an accuracy number
actually needs. They were chosen to probe the weakness named above rather
than to raise the score.

## Reproducing

```bash
python scripts/deploy.py --eval-instance
python eval/run.py --set v1 --runs 3
python eval/report.py
```
