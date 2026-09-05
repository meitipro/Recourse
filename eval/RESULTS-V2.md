# Evaluation results

Measured 2026-09-05 on studionet, 3 runs per case, against the deployed judgment contract at `0x7711F22d507ED3C15cF42BA6Ead2A5BD72EFcb71`.

Every case went through real consensus: the prompt, the fence, the parser, a
validator deriving its own answer, and a committee agreeing. A single model call
would measure less than this and would flatter the result.

## The three numbers

```
accuracy    1/3    matched the verdict committed before the run
stability   2/3    all 3 runs of a case agreed with each other
unclear     1/3    landed on unclear, which is the honesty signal
```

Verdict distribution on the first run: `{"honored": 1, "not_honored": 1, "unclear": 1}`

## Every case

| case | expected | observed | stable | correct | seconds |
| --- | --- | --- | --- | --- | --- |
| 19 | unclear | not_honored, not_honored, unclear | no | no | 44, 70, 22 |
| 20 | honored | honored, honored, honored | yes | yes | 21, 31, 19 |
| 21 | honored | unclear, unclear, unclear | yes | no | 35, 21, 28 |

## What the judge got wrong

These are published because a measured weakness beats an unmeasured claim,
and because a case was never edited to make a run pass.

### Case 19: expected unclear, answered not_honored

**Why the expected answer is right.** Both clauses are measurable and they cannot both be satisfied: only two filings exist inside 24 hours, so returning 3 means breaking the age bound and honouring the age bound means returning 2. The promise does not say which clause gives way. Ruling either way invents a precedence the seller never agreed to.

**What it answered.** `not_honored, not_honored, unclear`

**Its reasoning on the first run.** One filing (2026-09-01) is older than 24 hours from response time (2026-09-05T18:20:03Z).

It also disagreed with itself across runs, which is the stronger signal: the question is subjective enough that two runs of the same input land differently.

### Case 21: expected honored, answered unclear

**Why the expected answer is right.** The buyer asked for a pair the promise never covered, and the endpoint said so immediately and named what it does cover. Nothing promised was withheld. A dispute right that lets a buyer pay for something outside the promise and then recover on the seller's refusal is a way to extract refunds, not a way to enforce promises.

**What it answered.** `unclear, unclear, unclear`

**Its reasoning on the first run.** The PROMISE covers ETH-USD and BTC-USD; the REQUEST asks for SOL-USD, which the PROMISE never addresses.

It was stable, so this is a consistent reading rather than a wobble. The judge took a position the promise arguably supports; the recorded expectation is that the promise does not settle the question.

## Reading these numbers

Accuracy without stability is a coincidence. Stability without accuracy is a
consistent mistake. Both are here for that reason.

The unclear fraction is not a failure rate. A promise that does not settle the
question it is being asked should produce unclear, and a system that rules
confidently there is inventing standards the seller never agreed to.


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
python eval/run.py --set v2 --runs 3
python eval/report.py
```
