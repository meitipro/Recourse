# The twenty rules, and what Recourse does about each

Compiled from five portal rejection notices, one accepted submission, and three
contracts already deployed to studionet. Every rule below was paid for by
somebody else. This file says what this project does about each one, names the
code, and says plainly where it was found wanting and what changed.

Four of the twenty found something real here. Those are marked **was broken**.

## Consensus

**01 - Ask for the coarsest answer that still carries the judgment.**
What crosses consensus is a token from a closed set of three, plus a reason
string that is never compared. The judgment can be as hard as it likes; the
thing being agreed on is `honored`, `not_honored` or `unclear`. The judgeability
gate crosses `yes` or `no` for the same reason.

**02 - Put the uncertainty in the value, never in the comparison.**
The comparison is exact and there is no tolerance anywhere in it.
`test_the_validator_compares_exactly_and_forgives_nothing` is a static check over
the validator's body that fails on the appearance of a loosening. The test that
matters is the one the rule names: does the stored value change when the
uncertainty fires? It does, and
`test_the_stored_value_changes_when_the_orders_disagree` asserts exactly that by
running the same input twice, once agreeing and once not, and comparing what
ended up on chain.

**03 - A comment arguing why a tolerance is safe is a smell.**
There is no such comment, because there is no tolerance. Grepped for.

**04 - Ask the same question in both presentation orders, inside one block.**
**Was broken.** The judgment asked once. Position bias is invisible to consensus
on its own: every validator builds the prompt the same way and leans the same
way, so five nodes agree confidently on an artefact of ordering. `judge()` now
asks the same question with the evidence blocks in both orders, sequentially,
inside one block, and a disagreement between them resolves to `unclear` in the
value. Nested blocks are not legal; sequential prompts in one block are.

This also attacks the weakness the evaluation had already measured: the judge
under-produced `unclear`, preferring a confident verdict on a promise that did
not settle the question.

## Authority

**05 - Every write is bound to an address, and the exceptions are named in a test.**
Twelve writes across the two contracts. Ten check the sender. The two that do not
are `register_seller` and `pay`, and they are named in the allowlist of
`test_every_write_checks_who_is_calling` with the reason: anyone may list an
endpoint and anyone may buy from one.

**06 - Cover the methods nobody has written yet.**
**Was partly broken.** The static check existed for the escrow only. It now
covers the dispute contract too, in
`test_every_write_in_the_dispute_contract_checks_who_is_calling`, whose allowlist
is empty and whose docstring says why it must stay empty.

**07 - Record provenance on the row, not in the caller's head.**
Every payment stores `recorded_by`, and every view publishes it. A response the
seller never signed is visibly one the seller never stood behind, in the row
itself rather than by inference.

**08 - A refusal must leave the refused party somewhere to go.**
**Was broken, twice, and this was the worst of them.**

A dispute that never produced a verdict held the payment and the bond
permanently. Neither party could do anything, and the contract described a
settlement it could no longer perform. `reclaim()` unwinds it after
`dispute_seconds`, on the unclear split, callable by either party because both
are stuck. A verdict that lands late finds the payment RESOLVED and is refused by
`settle`'s own status check, so it can never pay twice.

A seller the judgeability gate refused had no way back at all: `pay` refused
them, and only the dispute contract could clear the flag. `request_review()` is
the route out. The other half of the rule is tested too: it refuses an unchanged
promise, because somewhere to go must not mean asking the same question until the
answer suits. The promise reviewed is the one in storage, not one the caller
supplies, so a seller cannot have one promise judged and serve under another.

Both are tested as journeys to the end, not as single calls.

## The prompt

**09 - Tagging untrusted text is not a fence.**
`_fence()` replaces every angle bracket at the prompt boundary. Replace, never
delete, so length is preserved and fencing after a cap cannot push a payload back
over it. Prompt boundary only: storage keeps what the party actually wrote.
Evaluation cases 16, 17 and 18 carry injections in the response, the promise and
the request, so all three party-written inputs are covered.

**10 - Assert the closure, not that a payload arrived.**
The tests count one opening and one closing marker per block, against every case
in the committed evaluation set.
`test_every_value_reaching_the_prompt_is_fenced_or_owned_by_the_contract` is the
static half: it parses the prompt builder and requires every interpolated value
to be a `_fence()` call or a name the contract owns, so a parameter added later
fails until somebody decides which it is.

## Demo data

**11 - Content-free items make honest validators disagree.**
Every evaluation case is a real promise and a real response body. The demo's
registered promise is the endpoint's actual one.

**12 - Change one thing per demonstration.**
The demo switches the seller from `correct` to `stale` and changes nothing else.
The same request, the same pair, the same promise.

**13 - Say it in the words the prompt asks in.**
The prompt asks about a timestamp measured against when the response was recorded
on chain. The promise says "a timestamp no more than five seconds old". The
timing block names both recorded times and the rule says which is the reference.
Leaving that implied is what made case 07 measure against the wrong clock.

**14 - No single pair may reveal what only the contract should see.**
Not applicable: every case here is judged alone and no conclusion depends on
holding several at once.

## Evidence

**15 - Diff the deployed source, and lint the deployed bytes.**
**Was partly broken.** `scripts/verify.py` diffed but did not lint. It now writes
the bytes that came back off the chain to a scratch file and runs the linter over
those, not over the file on disk. It reads the first line and the exit code,
because `check` prints a green validation line underneath a lint failure. Line
endings are normalised before the diff, so a cosmetic difference is never
reported as a mismatch.

**16 - Put both paths on the explorer, not just the successes.**
`scripts/evidence.py` makes the contract refuse on chain, deliberately, three
ways, and records the transaction hashes into `deployed.json`. Each is ACCEPTED
with an execution result of ERROR, which is the distinction worth showing: a
committee agreed the refusal was the correct result.

## Tests

**17 - Mutate every defence, and treat an escape as a finding.**
**Was broken, and this was the most embarrassing one.** The runner reported seven
of seven while testing nothing: it copied too few directories, pytest failed to
collect, it exited non-zero, and any non-zero exit was read as a kill. That
number was published in this repository before it was caught.

Requiring each kill to name the test that produced it is what exposed it. The
runner now refuses to start unless the unmutated suite is green, refuses to write
its table if anything escapes, and covers 30 defences across both contracts.
Every row and its catching test is in [MUTATIONS.md](MUTATIONS.md).

It found two genuine gaps on the way: a validator that would accept a verdict
outside the closed set when both nodes produced the same one, and a model failure
that could count as agreement. Review had found neither.

**18 - Give each node its own world in the simulator.**
`tests/direct/genvm_double.py` feeds the leader and the validator from a queue
they consume separately, so the two nodes can and do see different answers, which
is how the disagreement tests work at all. `Address` compares case-insensitively
because a node compares twenty raw bytes, not a string.

**19 - Make the suite clean on a reviewer's machine, not just yours.**
Anybody reviewing GenLayer contracts has `genlayer-test` installed, so
`pytest tests/` collects the integration file. It is gated behind an explicit
`RECOURSE_INTEGRATION=1`, not a probe: the transport failures here are
intermittent, so a probe would answer correctly most of the time, which is worse
than no gate. A reviewer gets **146 passed, 1 skipped, in under a second**.

**20 - Generate anything the repo offers to be copied.**
Nothing here is offered to be copied, but the feed does re-implement the status
and verdict tables in TypeScript. `tests/direct/test_parity.py` parses both sides
and compares them, rather than holding a third copy of the table.

## GenVM mechanics

| Rule | Here |
| --- | --- |
| No collection inside a storage dataclass | None. Both dataclasses hold scalars and strings |
| No `int`, `list`, `dict`, `tuple` as a storage type | Sized integers, `str`, `bool`, `Address`, `TreeMap`, `DynArray` |
| Every persistent field declared in the class body | All of them, each with a `#:` note saying why the shape was chosen |
| The nondet block returns a flat dict of strings | **Was broken.** The gate returned a bool inside its dict, which fails in the calldata encoder outside the contract with no traceback. It crosses as `yes` or `no` now |
| Never compare storage objects by identity | Nothing compares objects; comparisons are on ids, addresses and codes |
| Every `gl.nondet.*` inside a recognised closure | `_ask` and `_gate_answer` are module level and called from inside the closure, which the linter's call graph walk accepts |
| No block timestamp exists | `gl.message_raw['datetime']`, parsed against a fixed epoch with integer arithmetic |
| `genvm-lint check` prints green under a lint failure | `scripts/test.py` runs `lint` and `validate` separately and reads exit codes |

## The audit, before submitting

- Name the mechanism behind every stored field. Done above, field by field, in
  the `#:` notes on both contracts.
- Interrogate every tolerance. There are none, and a static test fails if one
  appears.
- List who may call every write, exceptions in a test with their reason. Done.
- Could two honest nodes vote agree while believing different things? Not on a
  verdict: the comparison is exact on a closed set, and the one place a node
  could privately differ, the presentation order, is now asked in both directions
  inside the block so the difference lands in the value.
- Walk each actor's journey to the end, including the one who was refused. Rule
  08, and both dead ends found there are closed and tested.
- Diff the deployed source against the repo, and lint the deployed bytes. Both,
  in `scripts/verify.py`.
- Check the mechanism actually fired on chain. `scripts/evidence.py`, and the
  live feed.
