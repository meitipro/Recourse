# Evidence that survives a testnet reset

studionet keeps state for a while and then does not. Every number the
repository publishes was measured against the frozen pair there, so what the
chain held is written down here, read back from the chain rather than typed.

## snapshot.json

`python scripts/snapshot.py` writes it from a throwaway account, which can
read and cannot write. It holds:

- `totals`: what the feed's tiles show, computed by the feed's own rules.
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
repository: every transaction the README cites must be in it, its refusals
must be the README's, and its evaluation numbers must be the reports', so
re-measuring without re-taking the snapshot fails the gate.

## receipts/

The raw receipt of every transaction in one cycle of each kind, as
`get_transaction` returned them, with the fields sorted and nothing else
touched. Each file is named by its position in the cycle, the method, and the
first twelve hex digits of its hash. `snapshot.json` names which payment each
folder is and lists the files.

| folder | what it is |
| --- | --- |
| `contested-*` | a dispute ruled **not_honored**: the buyer is made whole and the seller's upheld counter moves |
| `honored-*` | a compliant response contested anyway, ruled **honored**: payment and bond both to the seller |
| `unclear-*` | a real breach against a promise too vague to rule on, ruled **unclear**: the payment stands and the bond comes back |
| `honest-*` | never disputed: paid, answered, and withdrawn by the seller when the window closed. No consensus ran |

Re-running `snapshot.py` rewrites one field in every existing receipt:
`current_timestamp` is the node's own clock at the moment of the read, not part
of the transaction. A diff touching only that line means the chain said exactly
the same thing at a later time. Nothing in these files is edited, which is why
that noise is left in rather than stripped out.

The three verdicts are on the public record rather than only in the evaluation
set, which is what `scripts/verdicts.py` exists for. A record of nothing but
not_honored would read as a buyer-side tool rather than an adjudicator, and
`tests/direct/test_snapshot.py` fails if any of the three ever leaves it.
