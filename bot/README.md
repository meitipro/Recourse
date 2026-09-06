# The Recourse bot

A read only Telegram bot. It lints promises, dry runs the judge, reads cases
and seller records, and reports the live counts beside both evaluation
figures. It cannot do anything else, structurally.

## The boundary

Never holds a private key, signs anything, submits a write transaction,
accepts a seed phrase or key in a message, or stores a message beyond the
request that produced it.

- The chain client runs on a throwaway account generated at startup
  (`bot/main.py:reader`): the Python SDK refuses a read without a sender
  address, so a reader with no account cannot read, which the first version
  of this found the hard way. The account holds no GEN, is never written to
  disk and is never handed to a write. `tests/direct/test_bot.py` asserts it
  is not one of the demo's accounts and differs on every start, and scans
  `bot/` for any chain write or key handling.
- A message containing what looks like a private key or a seed phrase gets one
  reply: it is now compromised and must be rotated. The rest of the message is
  not read.
- State is in memory, keyed by chat id, cleared after ten minutes. A restart
  losing a half finished `/check` is acceptable.
- A token bucket per chat id. Commands that reach a model cost five tokens
  from a bucket of twenty that refills ten a minute.
- The transport logs update ids and chat ids, never text.

## Commands

| | |
| --- | --- |
| `/promise <text>` | The linter, in chat. Stage 1 is free and names the failed check; stage 2 asks the deployed gate's question of one model and offers a rewrite when the answer is no. |
| `/check` | Two steps, the promise then the response body. Runs the frozen contract's own `judge()` against one model, both presentation orders, and labels the result a dry run with no money and no consensus. |
| `/case <id>` | One adjudicated case by `p-000043` or `RC-2026-0043`: the frozen strings, the verdict, the reason, the timings. |
| `/seller <addr>` | The public record: promise, payments, upheld, live, judgeable, and the gate's reason if it ever ruled. |
| `/stats` | Live counts from chain, and `17/18` beside `1/3`. Never one without the other. |
| `/help` | The list. |

Free text is answered only about Recourse, GenLayer, x402 and machine payment
disputes, and only by pointing at the command that makes the call. A number
this bot states comes from a call it made in that turn or it is not stated.

## Run it

```bash
export TELEGRAM_BOT_TOKEN=123456:token-from-botfather
python bot/main.py
```

Stage 2 of `/promise` and all of `/check` need a model behind the linter:
`ANTHROPIC_API_KEY` in the environment, or the `claude` CLI signed in on the
machine. Without one, both say so and offer nothing.
