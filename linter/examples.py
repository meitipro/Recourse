"""
Six worked examples, three that pass and three that fail.

Taken from the evaluation sets so the linter and the judge cannot tell different
stories: a promise the judge was able to rule on must pass here, and the one
promise the judge was recorded as unable to rule on (case 08) must fail here,
at stage 1, before any money is spent.

    python -m linter.examples          # against the live model, stage 2 included
    python -m linter.examples --dry    # stage 1 only, no model, no cost
"""

from __future__ import annotations

EXAMPLES = [
    {
        "promise": "Prices aggregated from at least three venues, refreshed within five seconds.",
        "expect": {"judgeable": True, "stage": 2, "failed_check": None},
        "why": "A count and a freshness bound. Cases 01 to 07 were judged against this shape.",
    },
    {
        "promise": "Returns at least ten items, each with a title and a url, published in the last twenty four hours.",
        "expect": {"judgeable": True, "stage": 2, "failed_check": None},
        "why": "A count, two named fields and a time window.",
    },
    {
        "promise": "Returns the full text of the requested document, or an explicit not found.",
        "expect": {"judgeable": True, "stage": 2, "failed_check": None},
        "why": "No number anywhere, and still judgeable: both outcomes are named and a reader can check for either.",
    },
    {
        "promise": "Accurate market data.",
        "expect": {"judgeable": False, "stage": 1, "failed_check": "no measurable term"},
        "why": "Evaluation case 08, recorded unclear. Accurate against what, and how fresh?",
    },
    {
        "promise": "High quality results.",
        "expect": {"judgeable": False, "stage": 1, "failed_check": "no measurable term"},
        "why": "A quality and a noun. Nothing to count, bound or name.",
    },
    {
        "promise": "Fast and reliable responses.",
        "expect": {"judgeable": False, "stage": 1, "failed_check": "no measurable term"},
        "why": "Two qualities. Fast compared to what, reliable measured how?",
    },
]


def main() -> int:
    import json
    import sys

    from linter.service import ModelUnavailable, lint

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    dry = "--dry" in sys.argv
    model = None
    if dry:
        from linter.service import NoModel

        model = NoModel()

    failures = 0
    skipped = 0
    for example in EXAMPLES:
        try:
            result = lint(example["promise"], model=model)
        except ModelUnavailable as error:
            # Not run is not the same as matched. The first version of this
            # counted it that way and printed 6 of 6 with four never asked.
            skipped += 1
            print(f"skip {example['promise']}\n     stage 2 needed and no model: {error}\n")
            continue
        matched = all(result.get(key) == value for key, value in example["expect"].items())
        failures += 0 if matched else 1
        print(f"{'ok  ' if matched else 'MISS'} {example['promise']}")
        print(f"     {json.dumps(result, ensure_ascii=False)}")
        print(f"     {example['why']}\n")
    ran = len(EXAMPLES) - skipped
    print(f"{ran - failures} of {ran} matched" + (f", {skipped} could not be run without a model" if skipped else ""))
    return 1 if failures or skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())
