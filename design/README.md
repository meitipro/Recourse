# The design, and how it got into the site

The site's layout, type, colour and spacing come from a Claude Design canvas.
This directory holds that canvas and the tools that put it into `web/`, so
the port is reproducible rather than remembered.

| file | what it is |
| --- | --- |
| `Recourse.dc.html` | the canvas: header, hero, six sections, footer, plus three artboards the site does not ship. This is the second export, of 2026-09-15 |
| `RecourseBoot.dc.html` | the boot screen the canvas imports above its header, new in the second export |
| `RecourseFeed.dc.html` | the feed panel the canvas imports, with its skeleton, empty, snapshot and failed states |
| `RecourseClerk.dc.html` | the clerk artboard. See below |
| `extract.py` | unpacks a bundled export into its pages and diffs two exports, or an export against this directory, page by page |
| `to_jsx.py` | the first port's converter: HTML to JSX, mechanically |
| `build_site.py`, `build_feed.py`, `build_clerk.py` | the first port's assembly into `web/components/site/`. Do not run them again; see below |

## Why a converter rather than a rebuild

Rebuilding a design by reading it and typing something similar loses it. The
spacing scale, the exact greys, the clamp() curves and the hover states are the
design, and an eye reproduces none of them faithfully. So every inline style in
the first port came through `to_jsx.py` byte for byte, and every change the
second export made was carried across from a diff, style for style.

What the converter handles: bindings to JSX expressions, `sc-if` and `sc-for`
to conditionals and maps, style strings to style objects with duplicate
properties resolved the way CSS resolves them, SVG attributes to camelCase,
and the canvas's `style-hover` and `style-focus` attributes to real CSS
classes, which are appended to `app/globals.css` because React has no inline
pseudo classes.

## Porting a new export

The three build scripts rebuild each component from the canvas. Run now, they
would drop every departure listed below and everything the site has learned
about Studio Next since the first port. The second export went the other way:

    python design/extract.py design OLD_OR_NEW_EXPORT.html OUT

unpacks the export into its pages and writes one diff per page into `OUT`,
flattened one tag per line so each difference names the element that changed.
Each difference was then carried into `web/` by hand and checked against the
record before it shipped. The pages in this directory are the export the site
follows now, so the next export is diffed against them the same way, then
`npx tsc --noEmit` and `python scripts/test.py`.

## What the port changed, and why

The canvas is a design surface with no chain and no backend, so some of what it
carried was placeholder. Four things were corrected against this repository
rather than shipped as drawn, and each is a claim the project already refuses
to make elsewhere:

| the canvas said | the site says | why |
| --- | --- | --- |
| "Verdict and money land in the same transaction" | the verdict is written, and the settlement it implies moves when that transaction finalizes, about half a minute later | Two transactions, deliberately. Paying out on acceptance would let a successful appeal arrive after the money had gone. This is one of the three things the project got wrong first and fixed |
| "End to end: under one minute" | "Dispute to money back, median", read from the snapshot: the median over the not honored cases on the record | The verdict lands inside a minute and the money follows on finality, so one end to end figure under a minute would be false. The site states the snapshot's median and types no number |
| "Judgment costs about one dollar per case" | one adjudication is ten model calls, and studionet charges nothing for them | That dollar figure was inherited from a differently shaped contract, was never measured here, and had already been removed from the README once |
| "Settlement window: a few minutes" | the window read from `contracts/FROZEN.json` | Every number on the page is read, never typed |

Two other differences are structural rather than corrections. The feed's rows
are chain payments where the canvas showed the eighteen evaluation fixtures,
and the canvas's component gallery is a design system artboard rather than site
content, so the header's group carries the clerk and the feed instead.

Three more came out of checking `docs/DESIGN.md` against the code on
2026-09-13. These were not claims but places where the canvas broke a rule the
project binds, and the site was changed rather than the rule:

| the canvas drew | the site does | why |
| --- | --- | --- |
| the linter's result ending at the verdict, the reason and the rewrite | a line under every result naming the stage, and at stage 2 "A dry run, not the gate's verdict" | Stage 2 asks one model the gate's question and the gate on chain asks a committee. `linter/service.py` promises every consumer says so, and a reader who takes the panel's answer for the gate's is misled by omission |
| the Upheld tile in green and Disputes opened in red | the tile labelled Not honored, in the red of the badge for the same verdict, and Disputes opened in text colour | The tile counts not honored verdicts, which the table one screen below badges red, and "Upheld" without "against the seller" read as the seller upheld; a count that mixes states names none |
| the clerk's Honored chip as a solid accent fill | the honored badge's green, outlined | The table names honored green, and the accent is never a state's colour |

## The second export

The second export, of 2026-09-15, took the first round of corrections into the
canvas, added Studio Next beside studionet, and changed the shape of the page:
a floating header, a boot screen, one row per network in every evaluation tile
and a row of chips for each, a centred closing line. Those are ported as
drawn. Where it wrote something the record does not support, the site says
what the record does:

| the canvas says | the site says | why |
| --- | --- | --- |
| "Reading eval/cases.json - case 07 of 18", then three more labels, each shown for a fixed time | "Read from eval/cases.json - case 07 of 18", stepping through the ids the server read; "Read from contracts/FROZEN.json - two deployments, studionet and studio-next", from the record's own keys; the fonts label waiting on `document.fonts.ready`; the lane label waiting on the lane's first frame | A label saying the page is reading while only a clock runs describes work that is not happening. The server did read both files to render the page, so the past tense is true, and the two waits are real ones |
| a boot screen that only a script timer removes | the same timer, a CSS animation that removes it at four seconds with no script at all, and no boot screen under reduced motion | A cover over the whole page that depends on a script traps the page whenever the script fails |
| "Dispute to money back: about 90 s" | "Dispute to money back, median", read from this network's snapshot: 100 s on studionet, "does not move" on studio-next | The recorded median is 100 seconds, and on studio-next no settlement has moved |
| "The settlement window runs for 300 seconds, read from contracts/FROZEN.json" and "300 s" | the same words, with the figure read from that file | Every number on the page is read, never typed |
| the settle step ending at "about half a minute later" | the finality median read from the snapshot, and on studio-next one more sentence: the verdict is written, the payment and the bond stay in escrow, and why | The step alone describes a refund studio-next cannot pay |
| "five nodes times two presentation orders, and studio charges nothing for them" | the committee read from the snapshot, and "studionet charges nothing for them and studio-next charges a fee in testnet GEN" | Studio Next does charge. Its snapshot keeps what each method paid, spent and got back |
| "eval/results.json" under every tile | each network's file, one per line | The studio-next row is read from `eval/results.studio-next.json` |
| studio-next's case 07 chip, "Expected unclear - answered not honored - one run returned no verdict" | the same, ending "one run returned no verdict and the other two disagreed" | Its runs were not_honored, no verdict, unclear. Every chip title is computed from the runs the file records |
| "from studionet, one of two temporary testnets; ... in evidence/snapshot.json" | the network shown, and that network's snapshot file | studio-next's snapshot is `evidence/snapshot-studio-next.json` |
| the feed view's four contract cards, studio-next's pair noted "ported from 44111a3" | the four cards, under the feed: the pair being read marked, the other linking to it, and studio-next's noted "deployed from 44111a3" | Both pairs stay published whichever network the page reads. `44111a3` is the commit studio-next's pair was deployed from; the pair itself is a port of the frozen one at `ccc470a` |
| the header's wide bar or menu button chosen by a viewport width held in state | two classes and a media query | The server's HTML is then right on a phone, rather than drawing the wide bar there until the script runs |
| the closing line: the index, the eyebrow and a rule stacked above it, a rule below | a closing panel centred on both axes: the eyebrow between two rules, the line in larger type with "missing" underlined in the dashed accent of the gap section's Missing row, the mark as a seal, and the hero's lane along its foot with the middle tick in the accent | Asked for by the owner on 2026-09-15: centred, and more formal |
| each tile's network and figure held on one line | the same, with the figure wrapping under the network's name when the tile is too narrow for both | Measured: at 1280 pixels wide the figure ran 24 pixels past its row, at 1366 eight. Wrapped, nothing runs past at any width measured from 320 to 1440 |

## Two things the first port got wrong

Found while porting the second export, and fixed in `web/app/globals.css`:

- **No hover or focus state the canvas drew ever showed.** Each became a class
  in `globals.css`, but the element keeps the same property in its inline
  style, and an inline declaration beats any rule that is not `!important`.
  The rules now carry it, and the linter button's hover skips it while it is
  disabled.
- **The canvas's fonts never loaded on the main page.** The ported styles ask
  for 'Source Serif 4' and 'Work Sans', and fontsource's variable packages
  register 'Source Serif 4 Variable' and 'Work Sans Variable'. Nothing on the
  page asked for those, so it drew Georgia and the system sans. Three
  `@font-face` rules now answer the canvas's names with the same files.

## The clerk

`RecourseClerk.dc.html` is the design's own interactive judge, and it is built.
`web/components/site/Clerk.tsx` came through the same converter as the rest of
the site; `build_clerk.py` assembles it.

Three strings in, one verdict out, through `/api/clerk` to the linter service,
which loads `contracts/dispute.py` through the test double and runs `judge()`
unchanged. What comes back is the deployed code's answer rather than a
paraphrase of it, and it needs a model behind the linter the way stage 2 does.

Two things the port decided:

**The canvas's second mode is not here.** It ran all eighteen committed cases
in the browser and scored itself. That would stand a second accuracy number,
measured by one model rather than a committee, beside the published one. The
mode tabs came out with it rather than sitting there as controls that do
nothing.

**A committed case is judged against its own timing block.** The chain writes
that block, and a case from last week judged against this second's clock fails
any freshness bound it carried, so loading case 01 and pressing the button
would contradict its own committed answer. The panel sends the case's timing
while the three strings are still that case, and says which clock was used.
Anything typed by hand gets the clock now.

Every state says "Recorded on chain: no", before a verdict and beside it, and
both are literals rather than values so no later edit can flip them.
`tests/direct/test_linter.py` holds the route to never logging and the panel to
both disclaimers.

Four more came off it on 2026-09-15, each a sentence or a snippet the panel
cannot back:

| the clerk artboard showed | the site shows | why |
| --- | --- | --- |
| an Integration section: `recourse.serve`, `recourse.pay`, `res.satisfies` and `res.contest` | nothing; the section is cut | No such wrapper exists in either repository, and a snippet that reads as a shipped SDK is a claim with no code behind it |
| "Judge one case, or run the whole committed set" | one case at a time | The set mode was never built, for the reason above |
| "a single model in your browser" | one model on the linter service, running judge() from `contracts/dispute.py` unchanged | The browser runs nothing; `/api/clerk` does |
| the curl call titled "Read the judge prompt your agent will be held to", "version pinned per case" | the same call, titled for what it does: it puts a case to the judge | The call returns a verdict, not the prompt, and nothing pins a prompt version per case |

The two call to action blocks in the how and evaluation sections are still off
the page. They return when the clerk answers on the live site, which needs the
hosting and the key, and not before.
