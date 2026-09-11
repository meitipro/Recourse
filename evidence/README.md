# Evidence that survives a testnet reset

studionet keeps state for a while and then does not. Every number the
repository publishes was measured against the frozen pair there, so what the
chain held is written down here, read back from the chain rather than typed.

## snapshot.json

`python scripts/snapshot.py` writes it from a throwaway account, which can
read and cannot write. It holds:

- `totals`: what the feed's tiles show, computed by the feed's own rules, and
  four numbers the README's timing block and the site's How and Limits sections
  state: the median time from a dispute to the verdict and to the money back,
  the median time a transaction takes to finalize once its committee accepts
  it, and the size of the committee. Each is traced through the transactions by
  hash, open_dispute to adjudicate to settle to payout, and nothing that prints
  them types them.
- `fees`: `eth_gasPrice`, and the receipt of the first success of each method
  on chain and of the first refusal, with the `gasUsed` and `effectiveGasPrice`
  each returned.
- `payments`: every payment row with its frozen strings, its case when it was
  contested, and the hash of every transaction that touched it: pay,
  record_response, open_dispute, adjudicate, settle, withdraw, the payouts.
- `cases`: every verdict, with the four strings the validators read and the
  reason the leader wrote.
- `transactions`: everything either contract ever sent or received, decoded to
  method, arguments, payment, consensus status, execution result and returned
  value, with an explorer link each.
- `refusals`: every transaction the contracts refused on chain, with the
  sentence they refused it with. The README's four are among them.
- `evaluation`: the published accuracy and stability numbers, copied from
  `eval/results.json` and `eval/results-v2.json`.
- `recorded_at`: when. The site prints it whenever it shows this file.

The site reads the chain first and this file second, and says which one it is
showing. `tests/direct/test_snapshot.py` holds this file to the rest of the
repository: every transaction the README cites must be in it, the README's
four refusals must be among its own word for word, its timings and fees must be
the ones the README prints, and its evaluation numbers must be the reports', so
re-measuring without re-taking the snapshot fails the gate.

## receipts/

The raw receipt of every transaction in one cycle of each kind, as
`get_transaction` returned them, with the fields sorted and nothing else
touched. Each file is named by its position in the cycle, the method, and the
first twelve hex digits of its hash. `snapshot.json` names which payment each
folder is and lists the files.

The four directories, and what each one is:

| directory | files | the cycle, and how it ended |
| --- | --- | --- |
| `contested-p-000003/` | 6 | A nine hour old price against a promise allowing five seconds. Ruled **not_honored**: payment and bond both returned to the buyer, and the seller's upheld counter moved. This is the cycle the README's Rails section cites, bought against an opaque settlement id. |
| `honored-p-000013/` | 6 | A compliant response, contested anyway. Ruled **honored**: payment and bond both to the seller, so the buyer's bond was forfeit. What stops contesting everything being free. |
| `unclear-p-000014/` | 7 | A real breach, nine hours stale, against another seller, whose whole promise was "Returns accurate market data.". Ruled **unclear**: the payment stood and the bond came back, because a promise nobody can rule on is the seller's fault and not the buyer's. Two payouts, one to each party, which is why this one has seven files. |
| `honest-p-000001/` | 4 | Never disputed. Paid, answered, the window expired, and the seller withdrew. No judgment ran anywhere in it and nobody paid anything extra. |

The names come from `snapshot.json`, which records the payment id behind each
directory along with its verdict and the files it holds.

Re-running `snapshot.py` rewrites one field in every existing receipt:
`current_timestamp` is the node's own clock at the moment of the read, not part
of the transaction. A diff touching only that line means the chain said exactly
the same thing at a later time. Nothing in these files is edited, which is why
that noise is left in rather than stripped out.

The three verdicts are on the public record rather than only in the evaluation
set, which is what `scripts/verdicts.py` exists for. A record of nothing but
not_honored would read as a buyer-side tool rather than an adjudicator, and
`tests/direct/test_snapshot.py` fails if any of the three ever leaves it.
