# The two contracts

Two on chain, deliberately. The money path must be finished and provably correct
before any language model touches the system, so the escrow is fully
deterministic and the single model call lives somewhere else. There is a second
reason specific to GenLayer: deterministic execution has to reproduce identically
across validators, and a mismatch is classified as a deterministic violation
which opens a tribunal and can slash the leader. Keeping all non-determinism in
one small contract keeps that risk contained.

## API names, verified against the pinned SDK

Every GenLayer API used here was read from the standard library that the
`Depends` header actually pins, not from a docs page. The header
`py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` resolves
through `py-genlayer/<hash>/runner.json` to std lib `11rhn002...`, which is the
`gl/` layout. Two std libs ship with incompatible APIs, so following the header
rather than picking a directory is the difference between a real function and an
imaginary one.

| Purpose | Call | Where it was verified |
| --- | --- | --- |
| Revert | `raise gl.vm.UserError(msg)` | `gl/vm.py` |
| Transaction time | `gl.message_raw["datetime"]` | `_internal/msg.py`, field `datetime` |
| Caller | `gl.message.sender_address` | `gl/__init__.py`, `MessageType` |
| Value received | `gl.message.value` | same, payable methods only |
| Model call | `gl.nondet.exec_prompt(prompt)` returns `str` | `gl/nondet/__init__.py` |
| Custom equivalence | `gl.vm.run_nondet_unsafe(leader, validator)` | `gl/vm.py:143` |
| Leader result | `gl.vm.Return` with `.calldata` | `gl/vm.py` |
| Call another contract | `gl.get_contract_at(addr).emit(on=...).method(...)` | `gl/genvm_contracts.py:129` |
| Pay an account | `@gl.evm.contract_interface` proxy, `emit_transfer(value=...)` | `py/evm/generate.py` |

**There is no timestamp in `gl.message`.** `MessageType` carries
`contract_address`, `sender_address`, `origin_address`, `value` and `chain_id`,
and nothing else. Every sketch of this project wrote `self._now()` as if a block
time accessor existed. The deterministic source is `gl.message_raw["datetime"]`,
an ISO string fixed for the transaction and therefore identical on every
validator. `_seconds` parses it against a fixed epoch using integer arithmetic,
because `.timestamp()` returns a float and no float appears anywhere here.

**The EVM transfer kwargs carry `value` only.** `TransactionDataKwArgs` has no
`on`, so `emit_transfer(value=v, on="finalized")` on the EVM proxy is a
`TypeError`. The internal proxy does take `on`; the external one does not.

## RecourseEscrow

Fourteen methods, four view and ten write. No model call, no web access, no
randomness, no float.

| Method | Caller | Refuses with |
| --- | --- | --- |
| `set_dispute_contract(addr)` | owner, once | `not owner`, `dispute contract already set`, `zero address` |
| `register_seller(promise)` | anyone | `already registered`, `promise length` |
| `update_promise(promise)` | that seller | `not registered`, `open payments`, `promise length` |
| `set_active(bool)` | that seller | `not registered` |
| `set_judgeable(seller, ok)` | dispute contract | `not authorised`, `unknown seller` |
| `pay(seller, request)` payable | anyone | `unknown seller`, `seller inactive`, `promise not judgeable`, `zero value`, `request too long` |
| `record_response(pid, body, sig)` | seller or buyer | `not a party`, `not open`, `response already recorded`, `empty response`, `window closed`, `response too long` |
| `withdraw(pid)` | that seller | `not seller`, `not open`, `window open` |
| `open_dispute(pid)` payable | that buyer | `not buyer`, `not open`, `no response`, `window closed`, `wrong bond`, `dispute contract not set` |
| `settle(pid, verdict, reason)` | dispute contract | `not authorised`, `not disputed`, `bad verdict` |
| `get_payment`, `get_seller`, `recent`, `recent_rows`, `stats` | anyone | views, JSON with sorted keys |

`recent_rows(n)` returns a whole page of payments as one JSON array, without the
request and response bodies. The feed used to read `recent()` and then
`get_payment()` once per id, which is one request per row; Studio allows thirty
requests a minute, so a dozen rows rate limited the page on an ordinary load and
it rendered an error over an empty table. `recent_verdicts(n)` on the dispute
contract is the same shape for cases. Between them a page load is three requests
whatever the row count, and the evidence bodies are fetched only for the one row
a reader expands.

### The settlement table

| Verdict | Payment | Bond | Seller record |
| --- | --- | --- | --- |
| honored | to seller | to seller | upheld unchanged |
| not honored | to buyer | to buyer | upheld plus one |
| unclear | to seller | to buyer | upheld unchanged |

The asymmetry is deliberate. A losing dispute must cost the buyer something or
contesting everything becomes free, but an unclear verdict is the promise's
fault rather than the buyer's, so taking the bond there would punish a buyer for
a seller's vague wording.

### Two departures from the original specification

**`record_response` accepts the buyer.** In the specification only the seller
could record, which left a seller able to take payment, deliver nothing on chain
and block the dispute path entirely, with the payment releasing anyway. The
recorder is stored in `recorded_by`, and the signature field is only kept when
the seller recorded, so a response the seller never signed is visibly that. The
buyer still cannot overwrite a response the seller already wrote.

**`open_dispute` sends a fourth string.** Six of the eighteen evaluation cases
turn on freshness, and nothing in a promise, a request or a response says when
the response was observed. The escrow builds the timing block from `created_at`
and `responded_at`, both written by the chain, so neither party can move the
boundary they are judged against. The three frozen strings are unchanged: they
are still the only evidence either party puts in front of the validators.

### Invariants

Asserted after every scenario in the direct tests:

1. a payment never leaves RESOLVED or WITHDRAWN
2. `held` always equals the sum of amount plus bond over live payments
3. what was taken in equals what is held plus what was paid out
4. `open_dispute` is impossible without a recorded response
5. `settle` is impossible from any address except `dispute_contract`

`held` is a counter rather than a scan, and `Seller.live` likewise. Deriving
either by walking `payment_ids` grows without bound and would eventually make
`update_promise` impossible to execute.

## RecourseDispute

Six methods, four view and two write. Exactly one non-deterministic block runs
per case, and `test_exactly_one_non_deterministic_block_runs_per_case` asserts it.

### The equivalence design

Partial field matching, which is the pattern the documentation recommends for
this shape of problem.

    def leader_fn():        return _ask(prompt)          # one verdict, one reason
    def validator_fn(res):  return _ask(prompt)["verdict"] == res.calldata["verdict"]

The **verdict** is compared, after checking it is inside the closed set of three.
The **reason** is never compared: two correct judgments never word their
reasoning identically, and comparing free text would make consensus impossible.

Not `strict_eq`, which the documentation says never to use on model output and
which would fail on the first differing character. Not `prompt_non_comparative`,
which would ask a validator whether the leader's answer looks acceptable. This is
a settlement decision, so the validator derives the answer independently and then
compares. A validator that only checked the format would prove the leader
formatted correctly and nothing else.

### The fence

Tag-wrapping untrusted text is not a fence. The seller writes the promise and the
buyer writes the request, so either can close their own block and open a forged
one that arrives in the right position and the right shape. `_fence` replaces `<`
and `>` at the prompt boundary. Replace, never delete: length is preserved, so
the fence cannot push a payload past a cap already applied, and the attempt stays
readable as the text it is. Storage keeps every string verbatim.

### Error classes

Two are raised: `[EXPECTED]` for business logic and `[LLM_ERROR]` for model or
parse failures. `[EXTERNAL]` and `[TRANSIENT]` are declared because the
validator classifies them and that classification has to be right the day
anything here reads an external source, but nothing raises them today.

    expected or external   deterministic, must match exactly to agree
    transient on both      agree, the outside world was unavailable to both
    model or unknown       disagree, forcing a retry with new validators

Parsing never defaults to a verdict. Defaulting to unclear on a parse failure
would let a broken model quietly decide every case in the seller's favour,
because unclear leaves the payment with the seller.

## Traps worth knowing before editing these files

- **Name the class after the product.** `genvm-lint validate` skips any class
  called `Contract` by name and reports "No contract class found", which reads
  like a broken contract and is not one.
- **`genvm-lint check` runs lint and validate and prints a green validation line
  underneath a lint failure.** Read the first line, or the exit code.
- **On Windows set `PYTHONIOENCODING=utf-8`** before calling the linter, or it
  dies printing its own tick and reports a passing contract as failed.
- **Never pass a bare lambda to `run_nondet_unsafe`.** The linter adds the
  containing scope of such a lambda to its non-deterministic set, and every
  storage write after the call is then reported as an error. Named nested `def`s
  are registered as the block instead.
- **`gl.nondet.*` must be reachable from the equivalence block.** A module level
  helper called from inside the closure is fine, and the linter walks the call
  graph to check it. `_ask` and `_fence` are both module level for that reason.
- **A view argument dies past roughly 200 bytes on Studio**, with an RLP error
  that names a byte count rather than a size problem. No view here takes a
  document; the largest argument any view takes is a payment id.
- **Storage is unreachable inside a non-deterministic block**, and only the
  block's return value crosses back. Bind everything to locals first.

## Running the checks

    PYTHONIOENCODING=utf-8 genvm-lint lint contracts/escrow.py
    PYTHONIOENCODING=utf-8 genvm-lint validate contracts/escrow.py
    python -m pytest tests/direct/ -q -p no:gltest -p no:gltest_direct
