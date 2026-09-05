# The held out set: 1 of 3

Written by hand, unlike [RESULTS-V2.md](RESULTS-V2.md), which is generated from
the measurement. The numbers there are not typed. The reading here is.

Three cases, answers committed alone in `04ca928` before the runner could load
the file, then run three times each through consensus on studionet.

```
accuracy    1/3
stability   2/3
unclear     1/3
```

**The headline 17 of 18 on the first set does not survive contact with this
one.** That is the finding, it is published rather than fixed, and the
difference between the two numbers is more informative than either alone.

## Why the two sets disagree so much

The first eighteen were written from the case list in the build document, and
the judgment question was narrowed twice against them. Narrowing a question
against a set improves the score on that set and proves progressively less
about anything else. Three cases written afterwards, deliberately aimed at the
weakness the first set had already exposed, score 1 of 3.

Both numbers are real. `17/18` is what the judge does on the distribution it
was tuned against. `1/3` is what it does on three cases chosen to be hard in
the direction it is known to be weak. A reader who wants one number should take
neither: they should take the pattern, which both sets agree on and which is
stated at the bottom of [RESULTS.md](RESULTS.md). The judge resolves a promise
that does not settle the question toward the promise's plain words.

## Case by case

**19, expected unclear, answered not_honored twice and unclear once.** A
promise with two measurable clauses that cannot both be satisfied: the three
most recent filings, none older than 24 hours, where only two filings exist
inside the window. Two runs picked the age clause and ruled against the seller.
One run had the two presentation orders disagree and resolved to unclear, which
is the two-order mechanism doing exactly its job. So the case sits on the
boundary and the instability is the honest signal, not noise.

This is the documented bias, reproduced on a case it had never seen: when a
promise does not settle the question, rule on its plain words, against the
seller.

**20, expected honored, answered honored three times.** A decimal price carried
as a JSON string, four seconds old against a ten second bound. The judge read
the substance and did not treat the container as a breach. Stable and correct,
and it is the case that shows the judge is not simply biased against sellers in
general.

**21, expected honored, answered unclear three times, and the recorded answer
is the arguable one.** The buyer asked for `SOL-USD` from an endpoint promising
`ETH-USD` and `BTC-USD`, and got an immediate error naming what is supported.
The recorded expectation was honored: nothing promised was withheld. The judge
said, three times with the same reasoning, *the promise does not define
behaviour for unsupported pairs*, and therefore unclear.

That reasoning is sound. A promise silent on a request outside its scope really
does not settle what should happen, and unclear is what this system is supposed
to answer when a promise does not settle a question. **On this case the judge
has the better argument and the answer key is the weaker one.**

It stays as recorded and it stays counted as a miss. Editing a case after
seeing the run is the one thing that would make every other number here
worthless, and the rule does not get an exception for the times the judge is
right. What is allowed is saying so, which is this paragraph.

## What was not done about it

The adjudication question was not narrowed against these three, and will not
be. A held out set spends itself the moment it is used for tuning: after that
there is nothing held out and the next number means what `17/18` means. The
runner refuses to even suggest narrowing when `--set` is anything but `v1`.

The honest reading of both sets together is that the judge is reliable on
promises that state something checkable, and leans toward the plain words when
they do not. The unclear verdict is the mitigation and it is under-produced.
Two of the three misses across both sets are cases where a promise was silent
and the judge answered anyway.
