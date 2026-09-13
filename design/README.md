# The design, and how it got into the site

The site's layout, type, colour and spacing come from a Claude Design canvas.
This directory holds that canvas and the converter that put it into `web/`, so
the port is reproducible rather than remembered.

| file | what it is |
| --- | --- |
| `Recourse.dc.html` | the canvas: header, hero, six sections, footer, plus three artboards the site does not ship |
| `RecourseFeed.dc.html` | the feed panel the canvas imports, with its skeleton, empty, snapshot and failed states |
| `RecourseClerk.dc.html` | the clerk artboard, not built yet. See below |
| `to_jsx.py` | the converter: HTML to JSX, mechanically |
| `build_site.py` | assembles the header, hero, sections and footer into `web/components/site/` |
| `build_feed.py` | assembles the feed panel around the real chain read |

## Why a converter rather than a rebuild

Rebuilding a design by reading it and typing something similar loses it. The
spacing scale, the exact greys, the clamp() curves and the hover states are the
design, and an eye reproduces none of them faithfully. So every inline style in
`web/components/site/` came through `to_jsx.py` byte for byte.

What the converter handles: bindings to JSX expressions, `sc-if` and `sc-for`
to conditionals and maps, style strings to style objects with duplicate
properties resolved the way CSS resolves them, SVG attributes to camelCase,
and the canvas's `style-hover` and `style-focus` attributes to real CSS
classes, which are appended to `app/globals.css` because React has no inline
pseudo classes.

To re-port after the canvas changes: export it, extract the template, run the
three scripts, then `npx tsc --noEmit` and `python scripts/test.py`.

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

The two call to action blocks in the how and evaluation sections are still off
the page. They return when the clerk answers on the live site, which needs the
hosting and the key, and not before.
