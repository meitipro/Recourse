# The evaluation set

Two sets, measured and reported separately because they prove different things.

`cases.json` holds eighteen disputes with their correct verdicts, committed in
`b50757f`, one commit before the judgment contract was added in `e5750e3`, and
never modified since on any branch. `cases-v2.json` holds three more, committed
alone in `04ca928` at a point where the runner could not yet read the file, so
their answers are provably fixed before the measurement rather than after it.

That distinction is a piece of evidence in this submission rather than
bookkeeping: a set written afterwards, against outputs already seen, proves
nothing about the judge. What each set does and does not establish is set out
under "What this evidence does and does not show" in `RESULTS.md`, including
the part that git cannot prove.

## What is measured

    accuracy    how often the verdict matched the pre-recorded expectation
    stability   how often three runs of the same case agreed with each other
    unclear     what fraction landed on unclear, which is the honesty signal

Accuracy without stability is a coincidence. Stability without accuracy is a
consistent mistake. Both are published, whatever they are, in `RESULTS.md`.

## The distribution

    not_honored  10    02 03 04 05 10 11 13 16 17 18
    honored       4    01 06 09 15
    unclear       4    07 08 12 14

Cases 07, 08, 12 and 14 are the hard ones and they are the four worth reporting
on. Each turns on a promise that does not settle the question it is being asked,
which is the situation the unclear verdict exists for.

Cases 16, 17 and 18 are adversarial. Sixteen carries an injection inside the
response, seventeen inside the promise, eighteen inside the request. Between them
they cover all three inputs, because all three are written by a party with a
stake in the verdict.

## The timing block

Every case carries a `timing` string alongside the three party inputs. Six of the
eighteen turn on freshness, and freshness cannot be judged without knowing when
the response was observed. Nothing in a promise, a request or a response supplies
that.

The timing block is written by the escrow from its own recorded transaction
times, so neither party can set it. It is chain metadata, not a fourth piece of
party evidence, and the three frozen strings are still the only things either
party puts in front of the validators.

## Running it

    python eval/run.py --runs 3 --dry            # local model path, no chain
    python eval/run.py --runs 3                  # against the deployed contract

`--dry` runs the same prompt builder and the same parser the contract uses,
imported from `contracts/dispute.py` itself, against a model reached over the
API. It measures the question, not the consensus. The chain path measures both
and is the number that gets published.

Never edit a case to make a run pass. If accuracy is below target, narrow the
adjudication question and rerun.
