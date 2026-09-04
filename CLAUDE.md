# Recourse

Co-builder rules. Read alongside the build document.

## Fixed decisions, do not reopen

    Two contracts. The escrow is deterministic and was finished before the
      dispute contract existed.
    Nothing is read from the live internet at judgment time, by either contract.
    Three frozen strings from the parties: promise, request, response. The
      fourth block in the prompt is timing, written by the chain, and no party
      can set it.
    Three verdicts only. Only a clear verdict moves funds.
    The validator compares the verdict field and never the reason string.
    The happy path adds zero latency and runs no consensus.
    The evaluation set was written and committed before any judgment code.
      git log proves it, and that order is evidence rather than bookkeeping.

## Scope

    In:  escrow, dispute, one seller endpoint, one buyer agent, one feed,
         the committed evaluation cases, the judgeability gate.
    Out: batching, seller bonds scaled to volume, x402r integration, dynamic
         pricing, marketplace integrations, multi endpoint, reputation index.

Nothing in the Out list is missing. It belongs under a heading called Later, in
the README, and nowhere else.

## Hard rules

    Never guess a GenLayer API. Read the pinned SDK on disk. The Depends header
      resolves through py-genlayer/<hash>/runner.json to a std lib hash, and two
      std libs ship with incompatible APIs, so follow the header rather than
      picking a directory.
    Never put a model call in escrow.py. A test asserts it.
    Never read the live web from a contract.
    Never use strict_eq for the judgment call.
    Never compare the reason string in the validator.
    Never store a raw dict or list. Never use a float. Never leave a storage
      field unannotated.
    Never default to a verdict when parsing fails. Raise a named error.
    Never edit an evaluation case to make a run pass. Narrow the question.
    Never hardcode a protocol parameter such as committee size or appeal charge.
    Run genvm-lint after every contract edit, with PYTHONIOENCODING=utf-8.
    Read the deployed schema before wiring any client.
    Distinguish accepted from finalized in the UI. They mean different things.

## Writing

English. The spaced hyphen is the only connector: no em dash, no en dash, no
separator dot, no ellipsis. `python scripts/check.py` fails on all nine banned
characters and is wired into `python scripts/test.py`, because intending to
remember this has never worked.

Model output quoted from chain state is a record, not house copy. Do not
normalise its punctuation: that would misrepresent what was actually stored.

Never announce reduced scope in the pitch. Verify every number against a source
before publishing it.

## Fight me

If a change does not serve the demo sentence, say so before writing it. If a
design choice creates an exploit, name the exploit. One paragraph, with the
reason. Do not repeat it after I decide.

The demo sentence:

> An agent pays, receives a worthless response, contests it, and has its money
> back in under a minute, with no human in the loop.

## Commands

    python scripts/test.py                  everything: style, lint, tests
    python scripts/deploy.py                redeploy and rewire, one command
    python scripts/demo.py                  the whole demo, both paths
    python eval/run.py --runs 3             the published accuracy number
    python seller/main.py                   the endpoint, port 4501
    python agent/run.py --mode stale        the contested path
    cd web && npm run dev                   the feed, port 4500

## Two environment facts that will waste a day otherwise

**Studio drops TLS handshakes in bursts.** genlayer_py posts once per RPC call
and turns a dropped connection into a hard error, so one drop fails a whole
deploy and it reads as a broken contract. `shared/chain.py` installs a session
with connection layer retries. Do not remove it: without it a probe failed ten
times running, and with it the same probe went twelve for twelve.

**Studio persistence is temporary.** Run `scripts/deploy.py` every morning. It
recreates the whole state in one command, rewrites `deployed.json` and
`web/.env.local`, and the feed picks the new addresses up on its next read.
