# The Recourse bot

A read only Telegram bot. It lints promises, dry runs the judge, reads cases
and seller records, and reports the live counts beside both evaluation
figures. It cannot do anything else, structurally.

## The boundary

Never holds a private key, signs anything or submits a write transaction.

It keeps the last six messages of a chat in memory for ten minutes, three
asked and three answered, so "and the one before it" resolves. A message
carrying what looks like a private key or a seed phrase is the one exception:
it is refused in the turn it arrives, never enters that memory or reaches a
model, and clears what the chat had in memory with it. Nothing is written to
disk, nothing survives a restart, and no message text is logged.

- The chain client runs on a throwaway account generated at startup
  (`bot/main.py:reader`): the Python SDK refuses a read without a sender
  address, so a reader with no account cannot read, which the first version
  of this found the hard way. The account holds no GEN, is never written to
  disk and is never handed to a write. `tests/direct/test_bot.py` asserts it
  is not one of the demo's accounts and differs on every start, and scans
  `bot/` for any chain write or key handling.
- A message containing what looks like a private key or a seed phrase gets one
  reply: it is now compromised and must be rotated. The check runs before
  anything else reads the message, so the rest of it is not read.
  `tests/direct/test_bot.py` records every write to the thread memory and
  every request to the model on either side of one, and the secret is in
  neither.
- State is in memory, keyed by chat id: the half finished `/check` and the
  thread memory, each gone ten minutes after it was last written. A restart
  loses both, which is acceptable. `tests/direct/test_bot.py` scans `bot/` for
  the ways Python writes a file.
- A token bucket per chat id. Commands that reach a model cost five tokens
  from a bucket of twenty that refills ten a minute.
- The transport logs update ids and chat ids, never text. A turn that fails is
  logged by the name of its error alone, because an error raised while
  answering a message can carry what was typed; only the transport's own
  errors, which carry Telegram's reason or the network's, are logged whole.

## Commands

| | |
| --- | --- |
| `/promise <text>` | The linter, in chat. Stage 1 is free and names the failed check; stage 2 asks the deployed gate's question of one model and offers a rewrite when the answer is no. |
| `/check` | Two steps, the promise then the response body. Runs the frozen contract's own `judge()` against one model, both presentation orders, and labels the result a dry run with no money and no consensus. |
| `/case <id>` | One adjudicated case by `p-000043` or `RC-2026-0043`: the frozen strings, the verdict, the reason, the timings. |
| `/seller <addr>` | The public record: promise, payments, upheld, live, judgeable, and the gate's reason if it ever ruled. |
| `/stats` | Live counts from chain, and `17/18` beside `1/3`. Never one without the other. |
| `/help` | The list. |

The commands are shortcuts. Nobody has to learn them.

## Free text

Ask in plain words and a model chooses the read. It is handed five tools and
nothing else, `lint`, `judge_dry_run`, `get_case`, `get_seller` and
`get_stats`, which are the reads the commands make, and it makes at most three
in a turn before answering with what they returned.

| asked | read |
| --- | --- |
| is this promise any good | `lint` |
| what happened with RC-2026-0014 | `get_case` |
| how often does it rule for the seller | `get_stats`, which counts the decided cases by verdict |
| would this response pass | `judge_dry_run`, which starts the two step dry run when the promise or the body is missing |
| what is this | none: the answer comes from `bot/what_is_recourse.md`, the skill's first reference file |

A number this bot states comes from a call it made in that turn or it is not
stated. The model is given nothing else to draw from: the system prompt and
the tool definitions carry no numbers, the reference file is carried with its
numbers withheld, and the thread memory shows every earlier quantity as `[n]`,
keeping only identifiers such as a case citation. Every number in an answer is
then checked against what that turn's reads returned, and an answer stating
one they did not is sent back once, then refused.

- **Groups.** It answers only when named, by `@` its username or
  `/command@` it, or replied to. In a direct message it answers everything.
  It never answers one message twice, never answers another bot, and never
  speaks first: a reply is attached to the message it answers.
- **Thread memory.** The six messages the boundary names, gone ten minutes
  after the last one, like the `/check` state. In a group it keeps only the
  messages that named it or replied to it, the ones it answers.
- **Voice.** Six lines unless asked to expand, plain and technical, no emoji,
  no exclamation, no persona. It says when it does not know and names the
  command that would find out. It never says whether to pay an endpoint,
  never gives financial advice, and never speculates about an undecided case;
  `get_case` returns nothing about the outcome of one.
- **Cost.** Every free text turn spends at least one model call, so it costs
  what `/check`'s model step costs, five tokens, and a read inside it that
  reaches a model costs five more. The refusal says what the limit protects
  and when it lifts.
- **Model.** Claude Opus 5 through the Anthropic SDK at low effort, with
  adaptive thinking and the server side refusal fallback. `RECOURSE_BOT_MODEL`
  overrides the model and `RECOURSE_BOT_BACKEND=none` turns free text off. The
  `claude` CLI is not a backend for free text: it carries tools of its own,
  and the model here must be handed the five reads and nothing more.
- **Injection.** A promise, a response body or a case reason inside a read's
  result is text a party wrote, and the model is told so. The most it can do
  is steer the model into another read, and every read is read only and
  counted against the chat's bucket.

## Run it

```bash
export TELEGRAM_BOT_TOKEN=123456:token-from-botfather
python bot/main.py
```

Stage 2 of `/promise` and all of `/check` need a model behind the linter:
`ANTHROPIC_API_KEY` in the environment, or the `claude` CLI signed in on the
machine. Without one, both say so and offer nothing. Free text needs a
credential the Anthropic SDK finds, `ANTHROPIC_API_KEY` or an `ant auth login`
profile, for the reason above; without one it says so and the commands work.

To watch it answer without Telegram, `python scripts/ask_bot.py` puts ten
questions through the same function a direct message reaches, against the live
chain, and prints the reads each one made beside the reply.
