# The ninety second video: script

Screen capture only. The words on the right are read aloud over the shot on
the left, in the time the shot takes. Every number spoken is one this
repository publishes today, and nothing on screen is something the build
cannot show at recording time. Items marked OPTIONAL are not live on every
machine; the script reads correctly with them left out.

The take is on Studio Next, chain 61997, where the ported pair runs. There the
committee's verdict is recorded on chain and the settlement it implies does
not move: consensus v0.6 funds a value transfer only from the top of a
transaction, and settle's transfers sit two messages below the transaction
that funds them. So the contested path ends on the verdict, the case and the
three frozen strings, and the words say plainly that the settlement does not
move. No shot shows money moving for the contested payment, because it stays
in escrow.

The contested path takes minutes of real time, so the video cannot watch it in
real time. The stopwatch on screen is what makes the jump cuts honest: the
viewer sees the real elapsed time at each cut.

Every browser shot below names something that is on the site as it stands
since the canvas port. If the site changes again, walk this table against the
page before recording, not after.

Prepare everything in the shot list at the bottom before pressing record.

## The script

| time | shot: what is on screen | words, read aloud |
| --- | --- | --- |
| 0:00 to 0:10 | **Browser, the site, freshly loaded, top of the page.** The RECOURSE wordmark and "A promise that costs something to break." Behind them the lane runs: within the first few seconds one tick rises, marked CONTESTED, and slides back marked JUDGED, the word the site uses on Studio Next, where the settlement does not move. Hold for it. | An agent pays an endpoint it has never met, for one call, with nothing signed. The whole contract is one sentence the seller published on its own. Recourse is the dispute right for exactly that call. |
| 0:10 to 0:18 | **Terminal A.** `python scripts/demo.py --network studio-next` has just started, run by `scripts/record.py`. The first lines show the network and the escrow and dispute addresses, then the promise read from chain: `promise   Returns the spot price for the requested pair, aggregated from at least three venues, with a timestamp no more than five seconds old.` and under it `judgeable True, upheld N of M payments`, the seller's record. | This is the promise, on chain, written by the seller alone. Three venues. Five seconds. That sentence is the entire agreement. |
| 0:18 to 0:30 | **Terminal A, the honest path.** Under `the honest path` the agent's own lines scroll as each step happens, among them `paid             4 GEN, payment p-000NNN`, `recorded         evidence frozen, seller signature verified`, `check            pass: ok` and `outcome          accepted, letting the window expire`. Under the last, `seller may withdraw after NNNNNNNNNN`: the window's end in the chain's own units, seconds since 1970, which the words do not mention. | The honest path first. The agent pays into escrow, the response is good, the agent lets the window expire. No judgment ran. Nobody paid anything extra. That is what proves this is not a tax on honest sellers. |
| 0:30 to 0:36 | **Terminal A.** Under `the contested path`, the line starting `The same endpoint switches to stale and still returns 200.`, then the agent's lines again, and once it has paid and the response is recorded, `check            FAIL: stale: 32400s old, promise allows 5s`. The age reads 32401s instead when a second ticks over between the seller stamping its price and the agent receiving it. | Same endpoint. It switches to serving a nine hour old price, and still returns two hundred. Every deterministic check passes except the one that read the promise. |
| 0:36 to 0:42 | **Terminal A and Terminal B side by side.** Terminal A prints `disputed         bond 1 GEN posted, no human involved`, and Terminal B opens beside it at that line, running `python scripts/stopwatch.py`: `00:0N since the dispute was accepted`. | The agent posts a one GEN bond and files the dispute itself. No human is in the loop from here on. The clock starts. |
| 0:42 to 0:56 | **Browser tab 3, the case page** at `/case/RC-2026-NNNN` for this payment, filmed after the feed at 1:04 and placed here in the edit: the case and its citation exist only once the verdict lands, and the feed row at 1:04 is where the citation is read. **Terminal B must not be in frame**: by then it has stopped, at the verdict the 0:56 cut shows. The status line reads `disputed (verdict written; on this runtime the settlement does not move)`. The four blocks: promise, request, response, timing. Scroll slowly. | Five validators receive four strings. The promise, the request, the response, and the chain's own record of when each arrived. Neither party wrote that last one. They answer one question, in both presentation orders, and a committee has to agree. |
| 0:56 to 1:04 | **Jump cut.** Terminal A prints `verdict          not_honored` the moment the committee writes it to the case, the reason line under it and `dispute to verdict      NNs`. Terminal B stops by itself at the verdict line. Hold on the reason. | Not honored. The reason is the committee's, written to chain in its own words. |
| 1:04 to 1:12 | **Jump cut.** About a minute after the verdict, Terminal A prints `settlement       not moved: the escrow still holds the payment and the bond`. The agent watches the escrow that long because the settlement is attempted about half a minute after the verdict, and on this runtime it cannot be funded. The demo's result block follows with the verdict and the same settlement line, and no amount for the contested payment, because none moved. Then **Browser, section 05, Live feed**, "Every payment, every case, public", reloaded, since the feed reads the chain once, when the page loads: the new row shows its citation `RC-2026-NNNN`, status `JUDGED, ACCEPTED` and verdict `NOT HONORED`. Click the row: the three frozen strings the validators were given, the promise, the request and the response, open beneath it. | The verdict is recorded on chain, and on this runtime the settlement does not move. |
| 1:12 to 1:18 | OPTIONAL, needs the honest payment's window (300 s) to have closed, which comes some minutes after the verdict: `scripts/record.py` prints the time it closes and waits for a key, so cut the wait. **Terminal A:** `python scripts/withdraw.py p-000NNN` for the honest payment. Output: `withdrawn`, seller balance up, `no judgment ran and nobody paid anything extra`. If not recording this, the feed row reading `RELEASED, UNCOLLECTED` covers it. | And the honest payment from the start: its window closed, and the seller collects it with no judgment ever run on it. |
| 1:18 to 1:28 | **Browser, section 06, Evaluation**, "The number, published whatever it is". Every tile carries a studionet row and a studio-next row. Four numbers at the same size: `16 / 18`, `16 / 18`, `2 / 18`, `2 / 3`, on the studio-next rows, each tile naming the files its rows came from, `eval/results.studio-next.json` or its v2 file among them. Hold on both accuracy figures together. | Judged against answers committed before the code: sixteen of eighteen. Against three cases committed before the runner could read them and never tuned against: two of three. Both numbers, the same size, always. That gap is the honest measurement of this judge. |
| 1:28 to 1:30 | **Browser tab 1, the hero's strip**, the two copyable addresses, Escrow and Dispute, then scroll to the footer's `studio-next / chain 61997`. | Deployed bytes match the repository, and hashes prove it. |

Ninety seconds. About two hundred words.

## What each line rests on

| spoken | where it is published |
| --- | --- |
| three venues, five seconds | the registered promise, read from chain at demo start |
| nobody paid anything extra | the honest path: no judgment, `outcome accepted` |
| one GEN bond | `bond_wei` in `contracts/FROZEN.json`, printed by the demo, and the site's Contest step reads it from the same file |
| four strings, neither party wrote the last | `README.md`, "Three things we got wrong first"; the case page's timing block |
| both presentation orders, a committee has to agree | `contracts/dispute.py` `judge()`; `docs/RULES.md` rule 04 |
| the verdict recorded, and the settlement not moving on this runtime | the agent's own `verdict` and `settlement` lines; `evidence/snapshot-studio-next.json`, where every case is judged and still disputed and every settle ended `fee no_matching_allocation # external`; the README's "Settlement on Studio Next" |
| sixteen of eighteen, two of three | `eval/RESULTS.md` and `eval/RESULTS-V2.md`, the Studio Next column; the studio-next rows of the site's section 06 |
| deployed bytes match, hashes prove it | `python scripts/verify.py --network studio-next`; `contracts/FROZEN.json`, the README's contract table |

## OPTIONAL shots, and the version without them

- **The promise linter**, in the hero. Paste `Returns accurate market data.`
  into the promise box and press "Is this judgeable?". Stage 1 refuses it with
  no model: NOT JUDGEABLE and the reason, which is the promise payment p-000014
  ran on chain on studionet, then the stage line, "Stage 1 of the linter:
  deterministic, free." No rewrite follows, key or no key: one is offered only
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
- **The live site**: the hosted site at `https://recourse-site-seven.vercel.app`
  reads Studio Next unless its address asks for studionet, the same as
  `http://localhost:4500`, the production build this take uses. `--hosted`
  films the hosted site instead.
- **The withdraw shot** at 1:12, as marked.

The lane in the first shot is disabled under a reduced motion setting and
shows a still frame instead. Record on a machine with motion on.

## Shot list: before pressing record

In the order they are needed. Every window open, every state reached, before
the first frame.

1. **Terminal B, nothing to prepare.** `scripts/record.py` opens it beside
   Terminal A the moment the dispute line prints, running
   `python scripts/stopwatch.py`, and stops it at the verdict line. Run
   `record.py` inside Windows Terminal, so Terminal B opens as a pane in the same
   large font; anywhere else it opens as a new window to drag into place.
2. **Terminal A, `.venv\Scripts\python scripts\record.py --network studio-next`.**
   Studio Next needs the v0.6 SDK, which lives in `.venv`. It starts
   `python scripts/demo.py --network studio-next` at 0:10, and the demo starts
   the seller endpoint itself; nothing to prepare beyond
   `.venv\Scripts\python scripts\prepare.py --network studio-next` having been
   run once today and `.venv\Scripts\python scripts\verify.py --network studio-next`
   having said the deployment matches. Large font.
3. **Browser tab 1, the site**, not yet loaded. Load it as recording starts so
   the lane's first CONTESTED lands inside the opening shot. A production build
   on 4500, which reads Studio Next unless its address asks for studionet, so
   nothing names the network and any build will do. Set `LINTER_URL`,
   because without it a production build answers the linter panel with a 503.
   In `web/`, `npx next build`, then in PowerShell
   `$env:LINTER_URL="http://127.0.0.1:4503/lint"; npx next start -p 4500`, or in
   bash `LINTER_URL=http://127.0.0.1:4503/lint npx next start -p 4500`. Stop
   `npm run dev` first: both use port 4500, and building while it runs corrupts
   `web/.next`, after which every route fails.
4. **Browser tab 2, the feed** (`#feed`), loaded, showing the rows from the real
   run so the table is not empty at 1:04. It does not refresh by itself, since
   the feed reads the chain once, when the page loads: reload it at 1:04,
   after the settlement line, for the judged row and its citation.
5. **Browser tab 3, blank**, for the case page, filmed after the feed at 1:04
   and placed at 0:42: its URL is the citation the reloaded feed row shows.
6. **Browser tab 4, section 06** (`#evaluation`), scrolled so all four headline
   numbers are in frame.
7. OPTIONAL, nothing to type: with `--withdraw`, `record.py` runs
   `python scripts/withdraw.py p-000NNN --network studio-next` for the honest
   payment in Terminal A, once that payment's window has closed.
8. The linter service, if an OPTIONAL linter, rewrite or clerk shot is being
   recorded: `python linter/serve.py` running, and `LINTER_URL` set for the
   site. The linter shot needs no key, since stage 1 asks no model; the rewrite
   and the clerk need `ANTHROPIC_API_KEY` behind the linter.

Rehearse with `.venv\Scripts\python scripts\record.py --network studio-next
--dry-run` three times: it walks the order and the pauses, which are what a
person gets wrong, and writes nothing to the chain. Then run the take once for
real without recording, which exercises the chain's timing once. Then record.
Not three real runs: each writes two payments and a dispute to the chain that
appear in no shot, on top of the take's own. The take writes new payments too,
so take the final snapshot after it, not before:
`.venv\Scripts\python scripts\snapshot.py --network studio-next`, then the same
with `--check`.
