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
| "End to end: under one minute" | "Dispute to money back: about 90 seconds" | The verdict is inside a minute; the money is not. The README publishes the ninety second number as the honest one |
| "Judgment costs about one dollar per case" | one adjudication is ten model calls, and studionet charges nothing for them | That dollar figure was inherited from a differently shaped contract, was never measured here, and had already been removed from the README once |
| "Settlement window: a few minutes" | the window read from `contracts/FROZEN.json` | Every number on the page is read, never typed |

Two other differences are structural rather than corrections. The feed's rows
are chain payments where the canvas showed the eighteen evaluation fixtures,
and the canvas's component gallery is a design system artboard rather than site
content, so the header's group carries the clerk and the feed instead.

## The clerk

`RecourseClerk.dc.html` is the design's own interactive judge: it takes the
three frozen strings, puts the documented judge prompt to one model, and shows
the verdict beside the committed expectation, marked "Recorded on chain: no".
It is honest by construction and it is not built yet, because it needs a model
behind it the way the linter's second stage does.

Until it exists, its two call to action blocks are not on the page. A button
that opens nothing is the kind of claim this site refuses everywhere else.
