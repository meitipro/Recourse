# The site: design specification

> **Read this first.** This specification was written from the site as built
> before the Claude Design canvas was ported in `448b7b5`. Its binding rules,
> sections 1, 6.1, 6.2, 6.4, 6.5, 7, 8, 9 and 10, still hold, and the port was
> checked against every one of them. Its descriptions of layout and copy,
> section 2's shapes, section 3 and the section by section walk in 4, describe
> that earlier build. The canvas in `design/Recourse.dc.html` now decides those,
> and `design/README.md` lists every place the port departed from the canvas
> and why.

What the page at `web/` must contain, how each part behaves, and the rules
that decide every colour, word and button. Written from the site as built, so a
designer or a reviewer can check the page against it line by line. Where the
page and this document disagree, one of them is wrong and it is the page that
gets fixed, unless the disagreement is a new decision recorded here first.

Two kinds of rule are mixed in here, and a redesign should tell them apart.
The rules about what is shown and how it must not mislead (sections 1, 4, 6.1,
6.2, 6.4, 6.5, 7, 8, 9, 10) come from the project and bind any design of it. The
rules about shape, width and button chrome (sections 2 shape, 3, 5.1) describe
this build and a new design is free to replace them, so long as one filled
control remains the one that does work.

The page has three jobs, in this order: explain the gap, show the mechanism,
prove the thing runs by showing live verdicts. Everything on it serves one of
the three or is not on it.

---

## 1. Principles

**An instrument panel, not a landing page.** The reader is a judge with the
receipt open, an agent developer deciding whether to trust this, or a reviewer
who will click every number. Nothing is decorative. Every element either
carries information from the chain or explains how to read it.

**Every number is read, never typed.** Feed tiles come from the contract's
views. Evaluation figures come from `eval/results.json` and
`eval/results-v2.json`. The settlement window comes from `contracts/FROZEN.json`.
There is no number on the page that a person keyed in, and the one exception
is the three failure cards, which are illustrations and are labelled as such by
being example JSON, not chain rows.

**Unknown is shown as unknown.** A read that has not returned shows a dash. A
read that failed shows a notice saying so, with the time it was attempted. A
recorded snapshot shown in place of the chain says it is a snapshot, with the
time it was recorded, at the top of the section, in a style that cannot be
mistaken for the loading state. A zero is never shown where the truth is "we do
not know".

**Both accuracy figures, same size, always.** 17 of 18 never appears without 1
of 3 beside it at the same type size. A page that shows the better number large
and the worse one small is making a claim the numbers do not support.

**Accepted is not finalized.** Two words, two meanings, two states in the UI.
Collapsing them into one green tick misreports the protocol.

**Dark only.** No light mode. One accent colour, used as emitted light on small
elements, never as a large fill. State colours appear only where a state is
being named.

**House style in every string.** The spaced hyphen is the only connector. No em
dash, no en dash, no ellipsis, no separator dot. `python scripts/check.py`
enforces this across the repository and the site's copy is inside its scope.
Model output quoted from chain state is a record and is never normalised.

---

## 2. Tokens

Defined once in `web/app/globals.css` on `:root`. Nothing else names a colour.

### Surfaces

| token | value | use |
| --- | --- | --- |
| `--ground` | `#0a0c12` | page background |
| `--panel` | `#0e1119` | cards, tiles, the table, the linter box |
| `--code` | `#0c1018` | `pre` blocks, the evidence strings |
| `--hairline` | `#1b2130` | default 1px borders and table rules |
| `--hairline-strong` | `#263048` | borders that need to read as an edge: inputs, chips, the secondary button |

### Text

| token | value | use |
| --- | --- | --- |
| `--text` | `#eef3f8` | headings, numbers, primary copy |
| `--text-2` | `#aeb9c8` | body paragraphs |
| `--muted` | `#7c8798` | captions, legends, labels under tiles |
| `--dim` | `#4a5468` | eyebrows, the small denominator beside a headline number. **Fails WCAG AA for text**: 2.57:1 on ground, 2.48:1 on panel, measured. A redesign must not inherit it for anything a reader has to read; `--muted` at 5.38:1 is the lightest grey that passes |

### Accent

| token | value | use |
| --- | --- | --- |
| `--accent` | `#22d3ee` | links, the primary button border and text, the "gap" pill, the network badge |
| `--accent-dim` | `#0e7f92` | link underline on hover, borders of accent pills |
| `--accent-wash` | `rgba(34,211,238,0.08)` | the only permitted accent background, behind pills and the primary button |

The accent is never a solid fill wider than a button. There is no accent
heading, accent panel or accent hero.

### State

| token | value | means |
| --- | --- | --- |
| `--pending` / `--pending-wash` | `#d9a441` | a verdict not yet landed; the snapshot notice border |
| `--resolved` / `--resolved-wash` | `#4ade80` | honored; a finalized row's dot; an evaluation hit |
| `--refused` / `--refused-wash` | `#f87171` | not honored; a failed read; an evaluation miss; a chain refusal |

Unclear has no colour of its own on purpose: it is neither success nor failure
and reads as neither. See 6.4.

### Type

| token | family | role |
| --- | --- | --- |
| `--serif` | Source Serif 4 Variable, Georgia | `h1`, `h2`, `h3`, the closing line |
| `--sans` | Work Sans Variable, system-ui | body |
| `--mono` | Geist Mono, ui-monospace | every number, every address, every hash, every label, every button, eyebrows, pills, badges |

Fonts are self hosted through `@fontsource`. Google Fonts is not reachable from
the build machine and must not be reintroduced.

Body is 15px, line height 1.6. Paragraph measure is capped at 62ch. `h1` is
`clamp(2rem, 6vw, 3.4rem)`; `h2` is `clamp(1.3rem, 3.2vw, 1.75rem)`; headline
numbers are `clamp(3rem, 12vw, 5.5rem)`. Numbers always use tabular figures.

### Shape

Radius is 4px everywhere except pills, which are fully round, and verdict
badges and case chips, which are 3px. Borders are 1px. There are no shadows.

---

## 3. Layout

One column. `.shell` caps content at 1120px, centred, with
`clamp(1rem, 4vw, 2.5rem)` of side padding. Sections stack with generous
vertical space and a hairline between them.

Every `main`, `section`, `div`, `header` and `footer` has `min-width: 0`, and
`body` has `overflow-x: hidden`. This is the rule that stops a grid child from
forcing sideways scroll on a phone; do not remove it to fix something else.

Breakpoints: the five step flow becomes one column below 760px, and steps gain
a left border in place of the row rule. The table wraps in `.table-wrap` with
horizontal scroll inside it, so the page itself never scrolls sideways. Test
at 320px wide, not 375.

Motion: the only animation is the loading skeleton's pulse, and it is disabled
under `prefers-reduced-motion`.

---

## 4. The page, section by section

Sections appear in this order and each carries an eyebrow, an `h2`, then its
content. The eyebrow is the section's name in mono capitals; the `h2` is a
sentence.

### 4.1 Header

- **Wordmark**: "Recourse" in serif with the full stop in accent colour.
- **Network badge**, beside the wordmark, mono, accent: `reading studionet`.
  Always shown, even with one deployment. The value is the network the page
  reads, never a constant.
- **h1**: "A dispute right for the un-negotiated call."
- **Lede**: three sentences. The un-negotiated call, the one sentence the
  seller published, and "Agents can spend money in milliseconds; nothing in the
  stack lets them get it back."
- **Two buttons**: primary "Live verdicts" scrolling to `#feed`; secondary
  "Repository" opening GitHub. See 5.1 for the two button styles.

### 4.2 The gap

Eyebrow "The gap". `h2` "The rail is finished. The right is missing."

One paragraph on x402 settling finally and the two payment networks that keep
dispute rights where x402 does not. Then **the stack**: four rows, each a title,
a line, and a pill. Payments, Identity, Interoperability read `shipped` in a
quiet pill. Dispute right reads `missing` in an accent pill and the row itself
carries the `missing` class, which is the one place on the page the accent wash
appears behind a whole row.

### 4.3 The failures

Eyebrow "The failures". `h2` "Every one of these returns 200 and settles
payment."

Three cards: Stale, Hollow, Substituted. Each is a `figure` with a head row
(title plus a `200 OK` badge), a `pre` of example JSON, and a `figcaption` in
one sentence. The badge is the only element on the page that says 200, and it
says it in every card because that is the point.

Caption under the cards: every deterministic check passes, so deciding whether
a response was worth paying for takes a judge, and a judge has to be cheap,
fast and neutral at once.

### 4.4 The linter

Eyebrow "The linter". `h2` "Would a judge be able to rule on your promise?"
One paragraph explaining stage 1 and stage 2, then the panel. The panel is
specified in full in section 7.

### 4.5 How it works

Eyebrow "How it works". `h2` "An escrow window, a promise, a bond, three
verdicts."

Five steps in a row, each with a two digit index (`01` to `05`), a one word
title and one line: Call, Hold, Contest, Judge, Settle. Below, three facts in a
row: the settlement window in seconds read from `FROZEN.json`, "uncontested
releases with no judgment", "the honest path adds no latency". The window
figure is never typed; if the record is missing it says "a few minutes".

### 4.6 Live feed

Eyebrow "Live feed". `h2` "Reading the chain, right now." Anchor `#feed`.

This is the only part of the page that waits on the chain, and it streams in
behind a Suspense boundary so the rest of the page never waits. Its content is
specified in section 6.

### 4.7 Verdict quality

Eyebrow "Verdict quality". `h2` "The answers were committed one commit before
the judge."

Four headline numbers in a grid, all the same size: accuracy, stability,
landed on unclear, and the held out set. Each is `N` large with `/M` small and
dim beside it, and a label in muted text under it. Then a grid of eighteen case
chips, `01` to `18`, each green when the judge matched the committed answer and
red when it did not, with a title attribute naming the expected verdict and
whether the case was stable. A caption states how many runs each case took, on
which network, and points at `eval/RESULTS.md`.

Then the **two sets notice**, in a dashed box: "Two sets, always together."
followed by which set the question was narrowed against and which was held
out, and the one miss where the judge has the better argument than the answer
key and is still counted as a miss.

If `results.json` is absent the whole section shows one notice: "The
evaluation has not been run against this deployment yet. The number goes here
when it has, whatever it is." No placeholder number, ever.

### 4.8 Scope

Eyebrow "Scope". `h2` "What this is."

Three short paragraphs: one adjudication is ten model calls and studionet
charges nothing, so the page states work rather than a price; a vague promise
produces a vague verdict and the system says so through unclear; Recourse is a
candidate for the arbiter slot, not a competitor to an escrow.

### 4.9 Footer

The closing line in serif: "A refund system where the merchant picks the judge
is a refund policy. It is not a dispute right." Then a row: "Recourse" on the
left, and on the right three links, repository, genlayer, and the author's X
handle.

Planned, not built: when the three Vercel projects exist, the footer gains
links to the hosted linter and MCP server, in the same commit that puts the
URLs into the README's Install section. Until then the footer has exactly the
three links above.

---

## 5. Controls

### 5.1 Buttons

Three styles and no fourth.

| | primary `.button` | secondary `.button.secondary` | action `.linter-button` |
| --- | --- | --- | --- |
| font | mono, 0.8rem, 0.04em tracking | same | mono, 0.85rem |
| border | 1px accent-dim | 1px hairline-strong | none |
| text | accent | text-2 | ground (dark on light) |
| background | accent wash | transparent | **accent, solid** |
| hover | border accent, wash to 14% | border muted, text to text | unchanged |
| radius | 4px | 4px | 4px |
| where | header, "Live verdicts" | header, "Repository" | the linter panel only |

The first two are text with a hairline around them. The third is the single
filled control on the page, and it is filled because it is the one button that
does work rather than navigates: it spends a request and returns a verdict.
Nothing else earns the solid accent. No button is uppercase, wider than its
label plus padding, or carries an icon.

Anchors that look like buttons (the two in the header) use the same classes as
real buttons so a reader cannot tell which is which and does not need to.

### 5.2 Links

Accent text, no underline at rest, a 1px accent-dim underline on hover. Every
external link carries `rel="noreferrer"`. Addresses and hashes are links to the
explorer wherever they appear, and are displayed in mono.

### 5.3 The address button

`.addr`: a mono button showing the first six and last four characters of an
address. Click copies the full address to the clipboard and the label reads
"copied" for 1.2 seconds. Title attribute carries the full address. Clicking
it does not open the row it sits in.

### 5.4 Pills and badges

| element | class | style |
| --- | --- | --- |
| stack state | `.pill.shipped` / `.pill.gap` | round, mono 0.66rem uppercase; shipped is quiet text-2, gap is accent on accent wash |
| HTTP badge | `.badge-200` | mono 0.65rem, resolved green with a green border, on the failure cards only. Green on purpose: the response passed every check that exists, and that is the failure |
| network badge | `.network-badge` | mono, accent, beside the wordmark |
| verdict badge | `.verdict.*` | see 6.4 |
| case chip | `.case-chip.hit` / `.miss` | mono 0.7rem, green or red, 3px radius |

### 5.5 Notices

`.notice`: a dashed hairline-strong box, muted text. Used for anything the
page is telling the reader about itself rather than about the chain.

| variant | border | when |
| --- | --- | --- |
| `.notice` | dashed hairline-strong | the two sets explanation; "feed is live and waiting"; "evaluation not run yet" |
| `.notice.bad` | dashed, refused at 40% | the chain could not be read; the evidence could not be read |
| `.notice.recorded` | **solid**, pending at 55% | the feed is showing the recorded snapshot |

The recorded notice is solid where every other notice is dashed, so it cannot
be mistaken for the loading state or for an error. It is the one notice that
carries a `role="status"`.

---

## 6. The feed

### 6.1 Sources, and saying which

The feed reads the chain first, for at most twenty seconds, and the recorded
snapshot at `evidence/snapshot.json` second. The result carries a `source`
of `live` or `snapshot`, and the page prints it. There are exactly four states:

| state | tiles | above the table | caption under the table |
| --- | --- | --- | --- |
| loading | four dashes | "Reading the chain. Studio answers in one to ten seconds; the page is not waiting on anything else. If it has not answered in twenty, the recorded snapshot takes over and says so." | none |
| live | numbers | nothing | "Read from chain at {time}. Click a row for the evidence the validators saw." |
| snapshot | numbers from the snapshot | the recorded notice: "Recorded snapshot, not a live read. Taken {time} from studionet, a temporary testnet; {why}. Every row below is what the chain held then, and every transaction hash behind it is in evidence/snapshot.json." | "From the recorded snapshot of {time}; the chain was tried at {time}." |
| failed, no snapshot | four dashes | `.notice.bad`: "The chain could not be read. {error}. Attempted at {time}. No snapshot covers this network." | none |

A live answer with rows always wins. The snapshot takes over only when the
chain did not answer inside the deadline, or answered with no payments where
the snapshot has some, and `why` names which.

### 6.2 The four tiles

`.stats`, four `.stat` cells each with a mono `.stat-value` and a muted
`.stat-label`:

1. **payments**: the contract's own count, not the row count.
2. **disputes opened**: rows with status disputed or resolved.
3. **upheld**: `not_honored / resolved`, shown as `6/8`, never as a percentage.
4. **median pay to dispute**: the median of `decided_at - created_at` over
   resolved rows, in seconds. Not "median settlement": a case's `opened_at`
   and `decided_at` are one message's fixed datetime, so chain timestamps
   cannot see how long judgment took.

When the read failed every tile shows a dash. A zero here would be an invented
number.

### 6.3 The table

Columns, in order: time, payment, seller, amount, state, verdict, to dispute.

- **time**: `HH:MM:SS` UTC of `created_at`, mono.
- **payment**: the citation `RC-YYYY-NNNN` as a link to `/case/<id>` when a
  case exists, else the raw `p-NNNNNN`. The citation is derived off chain from
  the payment id and the year the verdict landed, so the site, the bot and the
  MCP print the same one.
- **seller**: the address button.
- **amount**: GEN to two decimals, right aligned, tabular.
- **state**: a coloured dot and a phrase, see 6.5.
- **verdict**: a badge, see 6.4, or muted "not contested".
- **to dispute**: seconds from payment to the dispute being accepted, or a
  dash.

Clicking a row opens its drawer, which fetches `/api/evidence?pid=` and shows
the promise, request and response in `pre` blocks, then timing written by the
chain and the reason given with the verdict when a case exists, then a line on
the signature: signed by the seller, recorded by the buyer with no seller
signature, or no signature recorded. If the evidence came from the snapshot the
drawer says so in the same line. While fetching, the drawer shows three
skeleton blocks, never a spinner.

### 6.4 The verdict badge

Mono, 0.66rem, uppercase, 3px radius, hairline border.

| verdict | text | border | background |
| --- | --- | --- | --- |
| honored | resolved green | green at 35% | resolved wash |
| not_honored | refused red | red at 35% | refused wash |
| unclear | text-2 | hairline-strong, **dashed** | none |
| pending | pending amber | amber at 35% | pending wash |

Unclear is deliberately colourless and dashed. It is neither success nor
failure, and giving it either colour would misreport what it means.

### 6.5 State, and the two words that are not the same

| status on chain | label | tone |
| --- | --- | --- |
| resolved | `settled, finalized` | green dot |
| withdrawn | `withdrawn` | green dot |
| disputed, case written | `judged, accepted` | amber dot |
| disputed, no case yet | `in consensus` | amber dot |
| open, window expired | `released, uncollected` | grey dot |
| open, window running | `window open` | grey dot |

Accepted means the committee agreed on the receipt, provisional until the
appeal window closes. Finalized means appeals complete, and is the only state
that is actually settled. The legend under the table says both, and "released"
is explained as the window expiring with no dispute so the seller may collect
at any time. Nothing on chain fires on its own.

### 6.6 Under the table

The legend (6.5), the source caption (6.1), and a line with the escrow and
dispute addresses as explorer links plus the network name.

---

## 7. The linter panel

One textarea, one button, one result. Three result states and no fourth.

- **Label**: "A delivery promise, as a seller would register it".
- **Textarea**: three rows, 2000 character cap, the judgeable promise as
  placeholder text in dim. Cmd or Ctrl plus Enter submits.
- **Button**: `.linter-button`, "Is this judgeable?", disabled while the box
  is empty or a check is running, label becomes "Checking" while busy. There is
  a hard 210 second ceiling on the wait; forever is not a state.
- **Examples**: "try a vague one, a judgeable one", two text buttons that fill
  the box. The vague one is "Accurate market data.", the judgeable one names
  three venues and five seconds.
- **Footnote**: "Nothing you paste here is stored." This is true because the
  route and the service log the path and status of a request and never its
  body.

Result box `.linter-result`:

| state | verdict line | then |
| --- | --- | --- |
| `.yes` | "Judgeable" | the reason; "A response could be ruled against this. That is what a promise is for." |
| `.no`, stage 1 | "Not judgeable" | the reason; "Failed the deterministic check **{name}**. No model was asked and nothing was spent." |
| `.no`, stage 2 | "Not judgeable" | the reason; a rewrite in a `pre` with a copy button that reads "copied" for 1.2 seconds |
| `.error` | the message | "Could not reach the linter. {detail}" or, on 429, "Too many checks in the last minute. Try again shortly." |

Every result ends with a stage line: "Stage 1 of the linter: deterministic,
free." or "Stage 2 of the linter: the deployed gate's question, put to one
model. A dry run, not the gate's verdict."

In production the route answers 503 "linter not configured" until `LINTER_URL`
is set, by design, and the panel shows that as the error state rather than
pretending.

---

## 8. The case page

**This route is load bearing and a drawer cannot replace it.** Four published
things depend on a case having its own URL: the video script's line that a
citation is a permalink and the fourteen second shot that opens one cold
(`docs/SCRIPT.md`, the shot at 0:42 and the row in "What each line rests on"),
the shot list's blank third tab, and the hosting smoke test that runs
`curl .../case/RC-2026-0003 | grep -c "not honored"` and expects 1
(`docs/HOSTING.md`). The last of those also fixes the rendering: the verdict
words must be in the HTML the server returns, so a case rendered only after a
client fetch fails the test even when it looks right in a browser. A drawer is
for scanning the feed; the route is for citing one case to somebody who was
not on the page. Keep both.

`/case/RC-YYYY-NNNN` and `/case/p-NNNNNN` are the same page. Metadata title
is the id. Everything on it is read from the chain when opened, with the same
snapshot fallback and the same recorded notice as the feed.

- **Eyebrow**: "Recourse / case", the first word a link home.
- **Title**: the citation when a case exists, else the payment id.
- **Subtitle**: "{pid} on studionet", or "never disputed, so there is no case;
  payment {pid} on studionet".
- **Facts** as a definition list: status (with "verdict written, money moves on
  finalization" or "money moved" appended where true), verdict (or "not
  contested"), amount, bond, paid, responded, decided, buyer, seller.
- **What the validators read**: promise, request, response, timing, each in a
  labelled `pre`. Then **What they wrote**: the reason as a blockquote. Then a
  caption: read from chain when opened, or from the snapshot because the chain
  could not be read; the verdict is the committee's, the reason is the
  leader's display string and was never compared; a link to the explorer.
- **Never disputed**: "The frozen strings", request and response only.
- **Not found**: a bad id 404s; a well formed id the chain and the snapshot
  both lack shows `.notice.bad` "The chain could not be read. {error}".

---

## 9. Copy rules

- Sentences, not labels, for `h2`. Labels, in mono capitals, for eyebrows.
- The spaced hyphen is the only connector in house copy.
- Text quoted from chain state, a reason, a promise, a response, is a record.
  Its punctuation, case and spacing are never normalised.
- Numbers on the page are read from a source and the source is named nearby.
- "Accepted" and "finalized" are never used interchangeably.
- "Unclear" is never described as a failure of the judge.
- No word implies a second network, a hosted URL that does not exist yet, or a
  feature under Later.

---

## 10. What is never on this page

- A light mode.
- A spinner without a ceiling.
- A zero standing in for an unknown.
- A placeholder number in the evaluation section.
- The better accuracy figure without the worse one at the same size.
- A snapshot rendered without the recorded notice.
- A percentage where a fraction is the truth.
- An accent fill wider than a button, or a second filled button.
- A button style beyond the three in 5.1.
- An icon.

---

## 11. Checking the page against this document

```bash
cd web && npx tsc --noEmit -p .          # the feed types, part of the gate
python scripts/check.py                  # house style over every string
```

Then open `http://localhost:4500` and walk sections 4.1 to 4.9 in order,
then one row's drawer, then one case page, then the linter with the vague
example. On a phone width of 320px nothing scrolls sideways. If the chain is
slow, the feed shows dashes and a sentence, and the rest of the page is already
there.
