# The ninety second video: script

Screen capture only. The words on the right are read aloud over the shot on
the left, in the time the shot takes. Every number spoken is one this
repository publishes today, and nothing on screen is something the build
cannot show at recording time. Items marked OPTIONAL are not live on every
machine; the script reads correctly with them left out.

The contested path takes about ninety seconds of real time, so the video
cannot watch it in real time. The stopwatch on screen is what makes the jump
cuts honest: the viewer sees the real elapsed time at each cut.

Prepare everything in the shot list at the bottom before pressing record.

## The script

| time | shot: what is on screen | words, read aloud |
| --- | --- | --- |
| 0:00 to 0:10 | **Browser, the site, top of the page.** Hero: "A dispute right for the un-negotiated call." The network badge in the header is visible. Hold. | An agent pays an endpoint it has never met, for one call, with nothing signed. The whole contract is one sentence the seller published on its own. Recourse is the dispute right for exactly that call. |
| 0:10 to 0:18 | **Terminal A.** `python scripts/demo.py` has just started. The first lines show the promise read from chain and the seller's address: `promise   Returns the spot price for the requested pair, aggregated from at least three venues, with a timestamp no more than five seconds old.` and `judgeable True`. | This is the promise, on chain, written by the seller alone. Three venues. Five seconds. That sentence is the entire agreement. |
| 0:18 to 0:30 | **Terminal A, the honest path.** The block under `the honest path`: `check ok`, `payment p-000NNN`, `outcome accepted, letting the window expire`, `signature verified`. | The honest path first. The agent pays into escrow, the response is good, the agent lets the window expire. No consensus ran. Nobody paid anything extra. That is what proves this is not a tax on honest sellers. |
| 0:30 to 0:36 | **Terminal A.** The line `The same endpoint switches to stale and still returns 200.` and under it `check      stale: 32400s old, promise allows 5s`. | Same endpoint. It switches to serving a nine hour old price, and still returns two hundred. Every deterministic check passes except the one that read the promise. |
| 0:36 to 0:42 | **Terminal A and Terminal B side by side.** Terminal A prints `disputed         bond 1 GEN posted, no human involved`. Terminal B is `python scripts/stopwatch.py`, just started, reading `00:0N`. | The agent posts a one GEN bond and files the dispute itself. No human is in the loop from here on. The clock starts. |
| 0:42 to 0:56 | **Browser, the case page** at `/case/RC-2026-NNNN` for this payment (open it from the feed row; it appears once the case row exists). The four blocks: promise, request, response, timing. Scroll slowly. **Terminal B** stays visible in a corner, counting. | Five validators receive four strings. The promise, the request, the response, and the chain's own record of when each arrived. Neither party wrote that last one. They answer one question, in both presentation orders, and a committee has to agree. |
| 0:56 to 1:04 | **Jump cut.** Terminal A prints `verdict    not_honored` and the reason line. Terminal B reads about `00:55` to `01:00`. Hold on the reason. | Under a minute: not honored. The reason is the committee's, written to chain, and it names the five second bound the seller wrote. |
| 1:04 to 1:12 | **Jump cut.** Terminal A prints `dispute to money back  88.Ns` and `refund   5 GEN returned, balance is net zero`. Terminal B reads about `01:28`. Stop the stopwatch. Then **Browser, the feed**: the row shows `RC-2026-NNNN`, `settled, finalized`, `NOT HONORED`. | Money moves on finalization, half a minute after the verdict, so a successful appeal could never reverse a payout. Payment and bond are back. The case has a citation, and the citation is a permalink. |
| 1:12 to 1:18 | OPTIONAL, needs the honest payment's window (300 s) to have closed. **Terminal A:** `python scripts/withdraw.py p-000NNN` for the honest payment. Output: `withdrawn`, seller balance up, `no consensus ran and nobody paid anything extra`. If not recording this, the feed row reading `released, uncollected` covers it. | And the honest payment from the start: its window closed, the seller collects it, and no committee ever heard about it. |
| 1:18 to 1:28 | **Browser, the evaluation section.** Four numbers at the same size: `17/18`, `17/18`, `3/18`, `1/3`. Hold on both accuracy figures together. | Judged against answers committed before the code: seventeen of eighteen. Against three cases committed before the runner could read them and never tuned against: one of three. Both numbers, the same size, always. That gap is the honest measurement of this judge. |
| 1:28 to 1:30 | **Browser, the site's foot**: the contract table, both networks if both are deployed, and the badge showing which one this recording used. | Same bytes, frozen, and the hashes prove it. |

Ninety seconds. About two hundred words.

## What each line rests on

| spoken | where it is published |
| --- | --- |
| three venues, five seconds | the registered promise, read from chain at demo start |
| nobody paid anything extra | the honest path: no consensus, `outcome accepted` |
| one GEN bond | `bond_wei` in `contracts/FROZEN.json`, printed by the demo |
| four strings, neither party wrote the last | `README.md`, "Three things we got wrong first"; the case page's timing block |
| both presentation orders, a committee has to agree | `contracts/dispute.py` `judge()`; `docs/RULES.md` rule 04 |
| under a minute; half a minute more to money | the demo's own two lines, about 60 s and about 89 s |
| a citation that is a permalink | `/case/RC-2026-NNNN` |
| seventeen of eighteen, one of three | `eval/RESULTS.md`, `eval/HELD-OUT.md`, the site's evaluation section |
| same bytes, hashes prove it | `contracts/FROZEN.json`, the README's contract table |

## OPTIONAL shots, and the version without them

- **The linter panel** (a vague promise refused, the rewrite offered): stage 2
  and the rewrite need `ANTHROPIC_API_KEY` behind the linter. Without it the
  panel refuses at stage 1 and names the check; with it, insert a six second
  shot after 0:18: paste `Accurate market data.`, show NOT JUDGEABLE and the
  rewrite. Words: *A promise too vague to judge is refused before any money
  moves, and rewritten.*
- **The live site URL**: read the hosted site if the Vercel imports are done;
  `http://localhost:4500` otherwise. The script is the same.
- **Bradbury**: if the same bytes are deployed there by recording day, run the
  demo with `--network bradbury` and the badge reads bradbury. If not, studionet;
  the words do not change.
- **The withdraw shot** at 1:12, as marked.

## Shot list: before pressing record

In the order they are needed. Every window open, every state reached, before
the first frame.

1. **Terminal B, ready but not started.** `cd` into the repository; the command
   `python scripts/stopwatch.py` typed and not yet run. Large font.
2. **Terminal A, the seller endpoint**: `python scripts/demo.py --network <network>`
   is what will run, and it starts the endpoint itself; nothing to prepare
   beyond `python scripts/prepare.py --network <network>` having been run once
   today and `python scripts/verify.py --network <network>` having said the
   deployment matches. Large font. Do not start the demo until 0:10.
3. **Browser tab 1, the site**, top of page, network badge visible. Local:
   `npm run dev` in `web/` already running on 4500, page loaded once so the
   feed is warm. Hosted: the live URL.
4. **Browser tab 2, the feed** (`#feed`), loaded, showing the rows from a rehearsal
   so the table is not empty at 1:04. It will refresh once the contested
   payment lands.
5. **Browser tab 3, blank**, for the case permalink at 0:42; the URL is read off
   the feed row's citation.
6. **Browser tab 4, the evaluation section** (`#` the "Verdict quality" section),
   scrolled so all four headline numbers are in frame.
7. OPTIONAL **Terminal C**: `python scripts/withdraw.py p-000NNN --network <network>`
   typed, for the honest payment's id, run only after that window has closed.
8. The linter service, if the OPTIONAL linter shot is being recorded:
   `python linter/serve.py` running with `ANTHROPIC_API_KEY` set, and
   `LINTER_URL` set for the site.

Rehearse the whole thing three times clean, as `docs/RUNBOOK.md` says, and
record the third.
