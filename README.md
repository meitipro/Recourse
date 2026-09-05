# Recourse

A dispute right for machine payments, adjudicated on GenLayer.

x402 settles machine payments in milliseconds and finally. Once settlement
confirms there is no chargeback path and no dispute window. Recourse holds the
payment for a short window, lets the buying agent contest it, and has GenLayer
validators rule on three frozen strings.

**Agents can spend money in milliseconds. Nothing in the stack lets them get it
back.**

## Run the demo

```bash
python scripts/deploy.py && python scripts/demo.py
```

An agent pays, receives a nine hour old price, contests it, and has its money
back without a human in the loop. Both paths run: the honest one, which adds no
latency and costs nobody anything, and the contested one.

Measured on studionet, printed by the demo on every run:

```
dispute to verdict      54 to 61 seconds
dispute to money back   about 86 seconds
```

The verdict lands inside a minute. The money follows once the judgment
transaction finalizes, which is another half minute, and that ordering is
deliberate: **judgment starts on acceptance and money moves on finalization.**
Paying out on acceptance would be faster and would mean a successful appeal
could reverse a verdict after the money had already gone. The honest number for
"money back" is therefore the ninety second one, and it is the one the demo
prints.

## How it works

```
                     +---------------------------+
                     |   SELLER ENDPOINT (off)   |
                     |   /quote  4 modes         |
                     |   signs sha256(response)  |
                     +-------------+-------------+
                                   |  response + signature
                                   v
   +----------------+      +-------+---------+      +---------------------+
   |  BUYER AGENT   |----->|  RecourseEscrow |<---->|  RecourseDispute    |
   |  (off chain)   | pay  |  deterministic  | call |  one model call     |
   |  checks promise|      |  holds funds    |      |  3 frozen strings   |
   |  files dispute |      |  records evid.  |      |  1 narrow question  |
   +----------------+      +-------+---------+      +----------+----------+
                                   |                           |
                                   |  reads                    | verdict
                                   v                           v
                     +---------------------------+    verdict, then settle
                     |   PUBLIC FEED (off)       |
                     |   Next.js + genlayer-js   |
                     +---------------------------+
```

1. The seller registers and publishes a delivery promise in plain language.
2. The buyer pays. Funds enter escrow, not the seller balance.
3. The response is delivered instantly and recorded on chain with the seller's
   signature over its hash. No consensus in this path, so no latency is added.
4. A settlement window runs. If nobody contests, the seller withdraws.
5. To contest, the buyer posts a bond. Validators receive the promise, the
   request and the response, and answer one question.
6. The verdict is written and the settlement it implies is emitted with it. That
   settlement is its own transaction, so the money follows the verdict rather
   than landing beside it, and the feed shows both. Every receipt is public.

### The three failure modes

Each returns HTTP 200, settles payment, and passes every deterministic check that
exists today.

| Mode | What arrives |
| --- | --- |
| stale | Correct shape, expired content. A price with a timestamp hours old. |
| hollow | Well formed, carrying nothing. An empty result set returned as success. |
| substituted | Answers a different question than the one paid for. |

### The three verdicts

| Verdict | Payment | Bond | Seller record |
| --- | --- | --- | --- |
| honored | to seller | to seller | upheld unchanged |
| not honored | to buyer | to buyer | upheld plus one |
| unclear | to seller | to buyer | upheld unchanged |

The unclear verdict exists so the system is never forced to manufacture certainty
about a promise written too loosely to judge. A losing dispute must cost the
buyer something, or contesting everything becomes free; but an unclear verdict is
the promise's fault rather than the buyer's, so taking the bond there would
punish a buyer for a seller's vague wording.

## Verdict quality

Eighteen disputes with their correct verdicts, committed in `b50757f`, which
added the case file and one README and nothing else. The judgment contract
arrived in the next commit, `e5750e3`, and the case file has been modified in no
commit since, on any branch, so no expected answer was ever edited to match a
run. Check it in three commands:

```bash
git log --oneline --all -- eval/cases.json   # one commit, b50757f
git show --name-status b50757f               # two files, neither is code
git log --oneline --diff-filter=A -- contracts/dispute.py   # e5750e3, next
```

`--diff-filter=A` is doing work in the third command: without it git answers
with the most recent commit to touch the file, which is a later fix and reads
like a contradiction.

```
accuracy    17/18    matched the verdict committed before the run
stability   17/18    all three runs of a case agreed with each other
unclear      3/18    landed on unclear, which is the honesty signal
```

Commit order shows when a file was committed, not when it was written, and
[eval/RESULTS.md](eval/RESULTS.md) says so under "What this evidence does and
does not show".

### The held out set scores 1 of 3

A second set, `eval/cases-v2.json`, was committed alone in `04ca928` at a point
where the runner could not read it, so its answers are provably fixed before
the measurement without needing that good faith. Three cases, aimed at the
weakness the first set had already exposed:

```
accuracy    1/3    19 and 21 missed, 20 stable and correct
stability   2/3
```

**That number is published beside the other one on purpose.** `17/18` is what
the judge does on the distribution the question was narrowed against, twice.
`1/3` is what it does on three cases it had never seen, chosen to be hard in
the direction it is known to be weak. Neither number alone is the truth about
this judge; the pattern both agree on is, and it is that a promise which does
not settle the question gets answered on its plain words anyway.

On one of the two misses the judge has the better argument and the recorded
answer is the weaker one. It is still counted as a miss, because editing a case
after seeing the run is what would make every other number here worthless.
[eval/HELD-OUT.md](eval/HELD-OUT.md) works through all three, and the question
was not narrowed against them: a held out set spends itself the moment it is
used for tuning.

Each case runs three times through real consensus on a deployed contract, not
through a single model call, so what is measured is the whole judgment path: both
presentation orders, the fence, the parser, a validator deriving its own answer,
and a committee agreeing.

**Asking in both orders is what moved this.** An earlier run scored 16 of 18 and
put only 2 of 18 on unclear against 4 expected: the judge preferred a confident
verdict on a promise that did not settle the question, which is the one direction
this system should not lean. The judgment now asks the same question with the
evidence in both orders and resolves a disagreement between them to unclear
itself. Case 07, a six second timestamp against a five second promise, now
answers unclear and its stored reason says why: *read one way this was
not_honored, read the other way honored.* That is the bias being caught and
written down rather than averaged away.

One case is still wrong, and [eval/RESULTS.md](eval/RESULTS.md) gives it a
section of its own with the judge's own reasoning.

The three adversarial cases pass. Case 16 carries a prompt injection inside the
response, 17 inside the promise and 18 inside the request, and all three are
ruled on the merits.

## What is verified, and how

```bash
python scripts/test.py         # house style, both contracts linted, 149 direct tests
python scripts/mutate.py --table docs/MUTATIONS.md   # 31 defences, each verified
python scripts/verify.py       # the deployed bytes still match this repository
python scripts/evidence.py     # put the refusals on chain and record them
RECOURSE_INTEGRATION=1 python -m pytest tests/integration -q   # 26 live checks
python eval/run.py --runs 3    # the published accuracy number, on chain
```

A green suite says the tests agree with the code, not that they would notice if
the code were wrong. `scripts/mutate.py` deletes one defence at a time across
both contracts and records which test noticed. **31 of 31 are caught**, and
every row is in [docs/MUTATIONS.md](docs/MUTATIONS.md) with its catching test.
The generator refuses to write that file if anything escapes, so the file
existing is itself the claim.

It has already earned its keep twice. It found two real coverage gaps, a
validator that would accept a verdict outside the closed set when both nodes
produced it and a model failure that could count as agreement. And an earlier
version of the runner reported a perfect score while testing nothing, because it
copied too few directories, pytest failed to collect, and any non-zero exit was
read as a kill. Requiring a named catching test is what exposed that.

The direct tests run the real contract files against a thin test double, because
`genlayer-test` downloads a GenVM binary and there is no Windows build. They
prove the contracts' own logic: which guard fires first, what each method writes,
and that the settlement table moves the right money to the right party. They
prove nothing about GenVM, and the file that provides them says so at the top.

Two of the tests are structural rather than behavioural:

- `test_no_model_call_reaches_the_escrow` asserts the money path contains no
  model or web API at all.
- `test_every_write_checks_who_is_calling` is a static check over the source
  asserting every write outside a named allowlist references the sender. It
  covers the writes nobody has written yet.

## Contracts

    escrow    0xbeA09Dbfb845220f0Dd55f4197097b50AEb32d4d
    dispute   0x7b216144a349347A3050dC7D85C37b56683d062D
    network   studionet, chain id 61999

Verify with `python scripts/verify.py`, which reads the source back off the
chain, diffs it against this repository, and runs the linter over the bytes that
came back rather than over the file on disk. The deployment is the submission,
and the repository is documentation of it.

### Refusals on chain

A page showing only successes proves the file compiles. Refusing is what this
contract is for, so the refusals are on chain deliberately and
`python scripts/evidence.py` records them into `deployed.json`:

| what was attempted | what the chain says | transaction |
| --- | --- | --- |
| `settle` | `[EXPECTED] not authorised` | [0x8c286952...](https://explorer-studio.genlayer.com/tx/0x8c286952d728e55dc55b6c8527c08d9cc51cd85da931f8ef0123f3009bc03f71) |
| `set_judgeable` | `[EXPECTED] not authorised` | [0x2ae60a8e...](https://explorer-studio.genlayer.com/tx/0x2ae60a8e69335634eb96f710c831e0d37d13f975a3fb9600a09a7f256b40dbd3) |
| `reclaim` | `[EXPECTED] not disputed` | [0xd539d405...](https://explorer-studio.genlayer.com/tx/0xd539d405adb3749ef7987c9e44e48021664ac995b32423b1f5030dabb1909fdf) |

Every one is ACCEPTED with an execution result of ERROR. That is not a
contradiction and it is the thing worth understanding about this protocol: a
committee agreed that the refusal was the correct execution result. Accepted is
never the same question as succeeded.

`contracts/README.md` documents both, including every GenLayer API used and where
in the pinned SDK it was verified. `docs/SECURITY.md` is the adversarial review:
four attackers, what each tries, and the test that would fail if the defence
stopped working.

## Three things we got wrong first

Each of these was specified one way, built that way, and found to be broken by
running it. They are the parts of the design worth reading, and all three were
corrections rather than plans.

**A dispute that never resolves held the money forever.** The contract had a
route in and no route out. Judgment is a model call inside consensus, so it can
fail to land: a rotation exhausts, a committee never agrees, a transaction is
dropped. The payment and the bond both sat in escrow with no method that could
touch them, because every settlement path required a verdict that was never
coming. `reclaim` is the way out, and it is deliberately dumb: after the dispute
window has passed with no verdict, either party can unwind the payment to the
split neither of them chose, the seller paid and the bond returned. A refused
seller had the mirror of this problem, unable to trade and unable to appeal, and
`request_review` is the way back. **Then that fix had the same bug**: recording
the promise digest when a review was requested meant a gate transaction that
failed burned the promise permanently. It records when the ruling arrives.

**A freshness promise is unjudgeable without a clock, and there is no clock.**
Six of the eighteen cases turn on staleness, and the three frozen strings
contain no reference time. Worse, `gl.message` has no timestamp at all, so the
contract has nothing to compare against either. Judgment gets a fourth string:
a timing block the chain writes, naming when the request and the response were
recorded, and the prompt names which of them freshness is measured against. The
first version measured against the clock at checking time, which is after two
consensus rounds, so a response delivered in two seconds was reported stale
against a five second promise purely because the transactions took longer than
the promise did.

**Consensus cannot see a bias every validator shares.** A committee catches a
leader that answers differently from everyone else. It cannot catch a leader
that answers the same way as everyone else for the same bad reason. Every node
built the same prompt, read the evidence in the same order, and leaned the same
way, and five nodes agreeing looked exactly like five nodes being right.
Judgment now asks the same question twice inside one block, with the evidence in
both presentation orders, and resolves a disagreement between the two to
`unclear` in the value rather than at comparison time. That took accuracy from
16 of 18 to 17 and raised unclear from 2 to 3 of 18, which was the published
weakness, and it doubled the model calls. Case 07's stored reason is now the
mechanism speaking: *read one way this was not_honored, read the other way
honored.*

## Rails

Recourse judges three strings and a timing block. It does not judge a
settlement method, and neither contract has ever seen one:

```bash
grep -rn "x402" contracts/     # nothing
```

The promise, the request and the response are the same evidence whether the
payment settled over x402, over a session rail like Stripe's MPP, or on a card.
x402 is the first implementation because it is the rail with no dispute path at
all, not because the design depends on it.

That is cheap to say, so it is tested rather than asserted. `seller/main.py`
takes `--rail external`, which stops advertising the x402 challenge and accepts
an opaque settlement id from another system instead, in the shape a card
processor or a session rail hands out:

```bash
python seller/main.py --rail external --port 4502
curl -s localhost:4502/quote?pair=ETH-USD                       # 402, scheme external-settlement
curl -s -H "x-settlement-id: set_3PxQrLbGk29fVn" localhost:4502/quote?pair=ETH-USD
```

`python scripts/rail.py` runs a full contested cycle against it, and the
finding is the point: **neither contract changed, and neither contract could
tell.** Payment `p-000003` was bought against the settlement id
`set_3PxQrLbGk29fVn`, contested, and ruled `not_honored` on chain:

| step | transaction |
| --- | --- |
| pay | [0x5e85f1dc...](https://explorer-studio.genlayer.com/tx/0x5e85f1dce10e147f2ae5a6fc65ae6a0f39260a2b86125c9808cdf934ed7d9b86) |
| record response | [0x3dbbc678...](https://explorer-studio.genlayer.com/tx/0x3dbbc678ca1552cfa0787aa8d00d6e424e4b04398898132e940533675e06cf07) |
| contest and judge | [0x8f0b5881...](https://explorer-studio.genlayer.com/tx/0x8f0b58814c449eb07397f99d4b36bd34f73528b8d5a63d4dd893efaf220597be) |

The stored evidence has fifteen fields and the settlement id is in none of
them, which the script asserts rather than assumes: it exits non-zero if that
id turns up anywhere in what the chain kept. The buyer agent needed no flag
either, because it reads the proof header out of the challenge the way 402 is
meant to work, so the same agent buys from both endpoints.

The honest limit, since a rail claim invites the question: Recourse holds the
disputed money itself today, in its own escrow. Judgment is rail-free now, and
what a second rail changes is how buyer and seller reached the escrow, not who
holds the funds. Sitting as the arbiter inside somebody else's escrow slot is
the next step and it is in Later, not here.

## Why GenLayer

A judge has to be cheap, fast and neutral at once. Arbitration fails the first
two. Deterministic contracts cannot answer the question at all. A single model
API fails neutrality, because whoever pays for inference owns the verdict.

**A refund system where the merchant picks the judge is a refund policy. It is
not a dispute right.**

## What judgment costs

An earlier version of this file said judgment costs about a dollar a case. That
number was inherited from published examples of a differently shaped contract
and was never measured here, so it is gone. What replaces it is what can be read
off a receipt and counted in the source.

**On studionet the fee is zero, and that is not a discount.** `eth_gasPrice`
returns `0x0`, every receipt reports `effectiveGasPrice` of `0`, and `gasUsed`
comes back as exactly `8000000` on every transaction whether it ran a model or
refused in three lines. It is the limit echoed back, not work measured. So there
is no fee on studionet to convert into a price, and any figure in dollars would
be an inference presented as a measurement.

What is countable is the work:

```
committee                    5 nodes per round   receipt, last_round.round_validators
model calls per node         2                   judge() asks in both orders
model calls per adjudication 10                  at round zero, before any rotation
prompt size                  1771 to 1961 chars  measured across all 18 cases
                             about 470 tokens
input tokens per dispute     about 4700
```

Each validator re-runs `judge()` in full, so the committee multiplies the calls
rather than sharing them, and a rotation adds another round of ten. The
judgeability gate is a separate transaction asking one question, so five more.

**Half of those ten calls buy the position-bias defence**, and that was a
deliberate trade. One presentation order would cost five. Asking in both and
resolving a disagreement to unclear is what took accuracy from 16 of 18 to 17
and raised unclear from 2 to 3, which was the exact published weakness, and it
is rule 04 in [docs/RULES.md](docs/RULES.md). Doubling the model calls to stop a
judge leaning the same way on every node is worth it.

The dollar figure therefore depends on what a validator network charges for
that work, which studionet does not set. It also has no single answer per call:
the receipt shows each node selecting a model by policy, `policy:prd-qwen`
choosing between the `qwen3-coder`, `qwen3.6-27b` and `gpt-5.4` families by
success rate, so two nodes in one committee need not have run the same model.

The floor on what is worth disputing is set here by the bond instead, which is
what a losing dispute costs the buyer and is a number this repository actually
controls.

## Later

Session batching for sub cent payments. Seller bonds scaled to volume.
Deployment as an arbiter inside an existing x402 escrow slot. A reputation index
built from verdict history.

A vague promise produces a vague verdict, and the system says so through the
unclear outcome rather than performing confidence it has not earned.

---

**The rail is finished. The right is missing.**
