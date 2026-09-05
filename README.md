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

We wrote eighteen disputes with their correct verdicts **before** writing any
judgment code. `git log --follow eval/cases.json contracts/dispute.py` shows the
order, and that order is what makes the number mean anything.

```
accuracy    16/18    matched the verdict recorded before the code
stability   16/18    all three runs of a case agreed with each other
unclear      2/18    landed on unclear, which is the honesty signal
```

Each case runs three times through real consensus on a deployed contract, not
through a single model call, so what is measured is the whole judgment path: the
prompt, the fence, the parser, a validator deriving its own answer, and a
committee agreeing.

Both cases it got wrong are cases whose recorded answer is unclear, and it
answered not honored in both. That is the one direction this system should not
lean, it is not tuned away, and [eval/RESULTS.md](eval/RESULTS.md) says so at
length along with every case and its reasoning.

The three adversarial cases pass. Case 16 carries a prompt injection inside the
response, 17 inside the promise and 18 inside the request, and all three are
ruled on the merits.

## What is verified, and how

```bash
python scripts/test.py         # house style, both contracts linted, 146 direct tests
python scripts/mutate.py --table docs/MUTATIONS.md   # 30 defences, each verified
python scripts/verify.py       # the deployed bytes still match this repository
python scripts/evidence.py     # put the refusals on chain and record them
RECOURSE_INTEGRATION=1 python -m pytest tests/integration -q   # 26 live checks
python eval/run.py --runs 3    # the published accuracy number, on chain
```

A green suite says the tests agree with the code, not that they would notice if
the code were wrong. `scripts/mutate.py` deletes one defence at a time across
both contracts and records which test noticed. **30 of 30 are caught**, and
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

    escrow    0x6a226d9B0E813C5D95277bf92fdB341A7bA1b342
    dispute   0x48E6088B871E76b1bD59c4BAd3d5b074799C60F7
    network   studionet, chain id 61999

Verify with `python scripts/verify.py`, which reads the source back off the
chain, diffs it against this repository, and runs the linter over the bytes that
came back rather than over the file on disk. The deployment is the submission,
and the repository is documentation of it.

### Refusals on chain

A page showing only successes proves the file compiles. Refusing is what this
contract is for, so the refusals are on chain deliberately and
`python scripts/evidence.py` records them into `deployed.json`:

| what was attempted | what the chain says |
| --- | --- |
| `settle` from an ordinary account | `[EXPECTED] not authorised` |
| a seller clearing its own judgeability flag | `[EXPECTED] not authorised` |
| unwinding a dispute that is not stuck | refused |

Every one is ACCEPTED with an execution result of ERROR. That is not a
contradiction and it is the thing worth understanding about this protocol: a
committee agreed that the refusal was the correct execution result. Accepted is
never the same question as succeeded.

`contracts/README.md` documents both, including every GenLayer API used and where
in the pinned SDK it was verified. `docs/SECURITY.md` is the adversarial review:
four attackers, what each tries, and the test that would fail if the defence
stopped working.

## Why GenLayer

A judge has to be cheap, fast and neutral at once. Arbitration fails the first
two. Deterministic contracts cannot answer the question at all. A single model
API fails neutrality, because whoever pays for inference owns the verdict.

**A refund system where the merchant picks the judge is a refund policy. It is
not a dispute right.**

## Later

Session batching for sub cent payments. Seller bonds scaled to volume.
Deployment as an arbiter inside an existing x402 escrow slot. A reputation index
built from verdict history.

Judgment costs about a dollar a case, so the first version targets payments above
that line. A vague promise produces a vague verdict, and the system says so
through the unclear outcome rather than performing confidence it has not earned.

---

**The rail is finished. The right is missing.**
