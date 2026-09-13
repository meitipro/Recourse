# The ninety second video: script

Screen capture only. The words on the right are read aloud over the shot on
the left, in the time the shot takes. Every number spoken is one this
repository publishes today, and nothing on screen is something the build
cannot show at recording time. Items marked OPTIONAL are not live on every
machine; the script reads correctly with them left out.

The contested path takes well over a minute and a half of real time, so the
video cannot watch it in real time. The stopwatch on screen is what makes the jump
cuts honest: the viewer sees the real elapsed time at each cut.

Every browser shot below names something that is on the site as it stands
since the canvas port. If the site changes again, walk this table against the
page before recording, not after.

Prepare everything in the shot list at the bottom before pressing record.

## The script

| time | shot: what is on screen | words, read aloud |
| --- | --- | --- |
| 0:00 to 0:10 | **Browser, the site, freshly loaded, top of the page.** The RECOURSE wordmark and "A promise that costs something to break." Behind them the lane runs: within the first few seconds one tick rises, marked CONTESTED, and slides back marked RETURNED. Hold for it. | An agent pays an endpoint it has never met, for one call, with nothing signed. The whole contract is one sentence the seller published on its own. Recourse is the dispute right for exactly that call. |
| 0:10 to 0:18 | **Terminal A.** `python scripts/demo.py` has just started, run by `scripts/record.py`. The first lines show the network and the escrow and dispute addresses, then the promise read from chain: `promise   Returns the spot price for the requested pair, aggregated from at least three venues, with a timestamp no more than five seconds old.` and under it `judgeable True, upheld N of M payments`, the seller's record. | This is the promise, on chain, written by the seller alone. Three venues. Five seconds. That sentence is the entire agreement. |
| 0:18 to 0:30 | **Terminal A, the honest path.** Under `the honest path` the agent's own lines scroll as each step happens, among them `paid             4 GEN, payment p-000NNN`, `recorded         evidence frozen, seller signature verified`, `check            pass: ok` and `outcome          accepted, letting the window expire`. Under the last, `seller may withdraw after NNNNNNNNNN`: the window's end in the chain's own units, seconds since 1970, which the words do not mention. | The honest path first. The agent pays into escrow, the response is good, the agent lets the window expire. No judgment ran. Nobody paid anything extra. That is what proves this is not a tax on honest sellers. |
| 0:30 to 0:36 | **Terminal A.** Under `the contested path`, the line starting `The same endpoint switches to stale and still returns 200.`, then the agent's lines again, and once it has paid and the response is recorded, `check            FAIL: stale: 32400s old, promise allows 5s`. The age reads 32401s instead when a second ticks over between the seller stamping its price and the agent receiving it. | Same endpoint. It switches to serving a nine hour old price, and still returns two hundred. Every deterministic check passes except the one that read the promise. |
| 0:36 to 0:42 | **Terminal A and Terminal B side by side.** Terminal A prints `disputed         bond 1 GEN posted, no human involved`, and Terminal B opens beside it at that line, running `python scripts/stopwatch.py`: `00:0N since the dispute was accepted`. | The agent posts a one GEN bond and files the dispute itself. No human is in the loop from here on. The clock starts. |
| 0:42 to 0:56 | **Browser tab 3, the case page** at `/case/RC-2026-NNNN` for this payment, filmed after the feed at 1:04 and placed here in the edit: the case and its citation exist only once the verdict lands, and the feed row at 1:04 is where the citation is read. **Terminal B must not be in frame**: by then it has stopped at about `01:40`, past the `01:05` the 0:56 cut shows. The four blocks: promise, request, response, timing. Scroll slowly. | Five validators receive four strings. The promise, the request, the response, and the chain's own record of when each arrived. Neither party wrote that last one. They answer one question, in both presentation orders, and a committee has to agree. |
| 0:56 to 1:04 | **Jump cut.** Terminal A prints `verdict          not_honored`, the reason line under it and `dispute to verdict      NNs`, the moment the verdict lands. Terminal B reads about `01:05`. Hold on the reason. | About a minute: not honored. The reason is the committee's, written to chain, and it names the five second bound the seller wrote. |
| 1:04 to 1:12 | **Jump cut.** Terminal A prints `dispute to money back   NNNs`, and after the buyer's balance, `refund                 5 GEN returned, balance is net zero`. Terminal B stops by itself at that refund line, reading about `01:40`. The demo's result block follows, with `under a minute  no` in it: that line measures money back, which follows the verdict on finality, as the words for this shot say, so it can stay in frame. Then **Browser, section 05, Live feed**, "Every payment, every case, public", reloaded, since the feed reads the chain once, when the page loads: the new row shows its citation `RC-2026-NNNN`, status `SETTLED, FINALIZED`, verdict `NOT HONORED`. | Money moves on finalization, half a minute after the verdict, so a successful appeal could never reverse a payout. Payment and bond are back. The case has a citation, and the citation is a permalink. |
| 1:12 to 1:18 | OPTIONAL, needs the honest payment's window (300 s) to have closed, which comes some minutes after the refund: `scripts/record.py` prints the time it closes and waits for a key, so cut the wait. **Terminal A:** `python scripts/withdraw.py p-000NNN` for the honest payment. Output: `withdrawn`, seller balance up, `no judgment ran and nobody paid anything extra`. If not recording this, the feed row reading `RELEASED, UNCOLLECTED` covers it. | And the honest payment from the start: its window closed, the seller collects it, and no committee ever heard about it. |
| 1:18 to 1:28 | **Browser, section 06, Evaluation**, "The number, published whatever it is". Four numbers at the same size: `17 / 18`, `17 / 18`, `3 / 18`, `1 / 3`. Hold on both accuracy figures together. | Judged against answers committed before the code: seventeen of eighteen. Against three cases committed before the runner could read them and never tuned against: one of three. Both numbers, the same size, always. That gap is the honest measurement of this judge. |
| 1:28 to 1:30 | **Browser tab 1, the hero's strip**, the two copyable addresses, Escrow and Dispute, then scroll to the footer's `studionet / chain 61999`. | Same bytes, frozen, and the hashes prove it. |

Ninety seconds. About two hundred words.

## What each line rests on

| spoken | where it is published |
| --- | --- |
| three venues, five seconds | the registered promise, read from chain at demo start |
| nobody paid anything extra | the honest path: no judgment, `outcome accepted` |
| one GEN bond | `bond_wei` in `contracts/FROZEN.json`, printed by the demo, and the site's Contest step reads it from the same file |
| four strings, neither party wrote the last | `README.md`, "Three things we got wrong first"; the case page's timing block |
| both presentation orders, a committee has to agree | `contracts/dispute.py` `judge()`; `docs/RULES.md` rule 04 |
| about a minute; half a minute more to money | the demo's own two lines, and the medians over the public record in `evidence/snapshot.json`, which the README prints |
| a citation that is a permalink | `/case/RC-2026-NNNN` |
| seventeen of eighteen, one of three | `eval/RESULTS.md`, `eval/HELD-OUT.md`, the site's section 06 |
| same bytes, hashes prove it | `contracts/FROZEN.json`, the README's contract table |

## OPTIONAL shots, and the version without them

- **The promise linter**, in the hero. Paste `Returns accurate market data.`
  into the promise box and press "Is this judgeable?". Stage 1 refuses it with
  no model: NOT JUDGEABLE and the reason, which is the promise payment p-000014
  ran on chain, then the stage line, "Stage 1 of the linter: deterministic,
  free." No rewrite follows, key or no key: one is offered only
  when a promise passes stage 1 and the gate's question says no. Insert as a
  six second shot after 0:18, but film it straight after the opening shot,
  before the demo starts at 0:10: the demo does not wait while a browser shot
  is filmed, so filmed after 0:18 the contested path, its dispute line and
  Terminal B opening would all happen off camera. Words: *A promise too vague
  to judge is refused before any money moves.*
- **The rewrite**, in the hero, straight after the refusal, about ten
  seconds. Needs `ANTHROPIC_API_KEY` behind the linter, so record it on the
  hosted site once the key is set there. Clear the box, paste
  `Returns pricing data for the requested pair, refreshed regularly.` and
  press "Is this judgeable?". Stage 1 lets it through, because "the requested
  pair" names a field. Stage 2 puts the deployed gate's own question to the
  model, which refuses it because "refreshed regularly" sets no freshness
  limit, and a second call writes the rewrite, so cut from the click to the
  answer. Wait for, top to bottom: NOT JUDGEABLE; the gate's reason, one line
  of at most 120 characters, about the missing freshness limit; a dark box
  holding the rewrite, with Copy at its top right; the stage line, "Stage 2
  of the linter: the deployed gate's question, put to one model. A dry run,
  not the gate's verdict."; the line saying nothing pasted is stored. The gate
  refused this promise in both of two runs made for
  this script, and one of them produced these two lines:

      'Refreshed regularly' gives no freshness limit, and 'pricing data' names no field, count or bound.
      Each response includes a numeric price for exactly the pair requested, with a timestamp showing that price was refreshed within the 24 hours before the response.

  Every run named here is a stand-in, not output from a linter backend: no
  credential was available on the build machine, so the linter's own prompts
  were answered by a separate model instance, Opus 5, and `lint()` parsed the
  answers. A model writes both lines, so they change every run: wait for the
  shape, not the words. Paste it once on the hosted site before recording. If
  it answers Judgeable there, the second choice is
  `Prices are updated every so often from a number of trusted venues.`, also
  refused in both of its runs. Words: *A promise can name what it returns and
  still leave open how fresh it is. The gate's own question catches that
  before any money moves, and the linter offers a version a judge could rule
  on.* Without a key, leave this shot out: the refusal above stands on its
  own, and its words never mention a rewrite. On a site with no key the panel
  answers this promise with an error line instead of a verdict, so do not
  paste it there.
- **The clerk**, the section "Put the judge on the stand", between the feed and
  the evaluation. Needs a model behind the linter. Load case 01, press "Put it
  to the judge", hold on the verdict beside the committed expectation and on
  "Recorded on chain: no". Words: *Anyone can run the judge's own code on a
  committed case. It says plainly that this is not the chain.* It is filmed at
  1:12, after the withdraw shot when both are recorded, and the edit keeps
  whichever the running time has room for.
- **The live site**: read `https://recourse-site.vercel.app` if the imports are
  done, `http://localhost:4500` otherwise. The script is the same.
- **The withdraw shot** at 1:12, as marked.

The lane in the first shot is disabled under a reduced motion setting and
shows a still frame instead. Record on a machine with motion on.

## Shot list: before pressing record

In the order they are needed. Every window open, every state reached, before
the first frame.

1. **Terminal B, nothing to prepare.** `scripts/record.py` opens it beside
   Terminal A the moment the dispute line prints, running
   `python scripts/stopwatch.py`, and stops it at the refund line. Run
   `record.py` inside Windows Terminal, so Terminal B opens as a pane in the same
   large font; anywhere else it opens as a new window to drag into place.
2. **Terminal A, `python scripts/record.py`.** It starts `python scripts/demo.py`
   at 0:10, and the demo starts the seller endpoint itself; nothing to prepare
   beyond `python scripts/prepare.py` having been run once today and
   `python scripts/verify.py` having said the deployment matches. Large font.
3. **Browser tab 1, the site**, not yet loaded. Load it as recording starts so
   the lane's first CONTESTED lands inside the opening shot. Local: a
   production build on 4500, so no development indicator lands in frame, with
   `LINTER_URL` set, because without it a production build answers the linter
   panel with a 503. In `web/`, `npx next build`, then in bash
   `LINTER_URL=http://127.0.0.1:4503/lint npx next start -p 4500`, or in
   PowerShell `$env:LINTER_URL="http://127.0.0.1:4503/lint"; npx next start -p 4500`.
   Stop `npm run dev` first: both use port 4500, and building while it runs
   corrupts `web/.next`, after which every route fails. Hosted: the live URL.
4. **Browser tab 2, the feed** (`#feed`), loaded, showing the rows from the real
   run so the table is not empty at 1:04. It does not refresh by itself, since
   the feed reads the chain once, when the page loads: reload it at 1:04,
   after the refund line, for the settled row and its citation.
5. **Browser tab 3, blank**, for the case page, filmed after the feed at 1:04
   and placed at 0:42: its URL is the citation the reloaded feed row shows.
6. **Browser tab 4, section 06** (`#evaluation`), scrolled so all four headline
   numbers are in frame.
7. OPTIONAL, nothing to type: with `--withdraw`, `record.py` runs
   `python scripts/withdraw.py p-000NNN` for the honest payment in Terminal A,
   once that payment's window has closed.
8. The linter service, if an OPTIONAL linter, rewrite or clerk shot is being
   recorded: `python linter/serve.py` running, and `LINTER_URL` set for the
   site. The linter shot needs no key, since stage 1 asks no model; the rewrite
   and the clerk need `ANTHROPIC_API_KEY` behind the linter.

Rehearse with `python scripts/record.py --dry-run` three times: it walks the
order and the pauses, which are what a person gets wrong, and writes nothing to
the chain. Then run the take once for real without recording, which exercises
the chain's timing once. Then record. Not three real runs: each writes two
payments and a dispute to the chain that appear in no shot, on top of the
take's own. The take writes new payments too, so take the final snapshot after
it, not before: `python scripts/snapshot.py`, then
`python scripts/snapshot.py --check`.
