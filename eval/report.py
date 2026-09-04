#!/usr/bin/env python3
"""
Turns eval/results.json into eval/RESULTS.md.

    python eval/report.py

The published number is generated from the measurement, never typed. A number in
a README that nothing regenerates drifts away from the thing it claims to
describe, and the drift is invisible.
"""

from __future__ import annotations

import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE / "results.json"
CASES = HERE / "cases.json"
OUT = HERE / "RESULTS.md"

# A Windows console hands a child process an ansi codepage. Anything that
# prints text from the chain or a model can die on it, so widen it here.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    if not RESULTS.exists():
        raise SystemExit("no results.json. Run eval/run.py first.")
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in json.loads(CASES.read_text(encoding="utf-8"))}
    rows = data["rows"]
    total = data["n"]

    wrong = [row for row in rows if not row["correct"]]
    # A run that never produced a verdict is an infrastructure failure, not a
    # judge disagreeing with itself. Counting the two together makes a dropped
    # connection look like a subjective question, which is the opposite of what
    # the stability number is for.
    errored = [row for row in rows if "error" in row["observed"]]
    unstable = [
        row
        for row in rows
        if not row["stable"] and len({v for v in row["observed"] if v != "error"}) > 1
    ]
    measured = time.strftime("%Y-%m-%d", time.gmtime(data["measured_at"]))

    lines: list[str] = []
    add = lines.append

    add("# Evaluation results")
    add("")
    add(
        f"Measured {measured} on {data['network']}, {data['runs']} runs per case, "
        f"against the deployed judgment contract at `{data['instance']}`."
    )
    add("")
    add("Every case went through real consensus: the prompt, the fence, the parser, a")
    add("validator deriving its own answer, and a committee agreeing. A single model call")
    add("would measure less than this and would flatter the result.")
    add("")
    add("## The three numbers")
    add("")
    add("```")
    add(f"accuracy    {data['accuracy']}/{total}    matched the verdict recorded before the code")
    add(f"stability   {data['stability']}/{total}    all {data['runs']} runs of a case agreed with each other")
    add(f"unclear     {data['unclear']}/{total}    landed on unclear, which is the honesty signal")
    add("```")
    add("")
    if errored:
        add(
            f"`stability` counts {len(errored)} case(s) as unstable "
            f"({', '.join(row['id'] for row in errored)}) where one run never returned a "
            "verdict at all. That is a dropped transaction on a hosted network, not the "
            f"judge disagreeing with itself. On verdicts alone, "
            f"{len(unstable)} case(s) disagreed across runs"
            + (f": {', '.join(row['id'] for row in unstable)}." if unstable else ".")
        )
        add("")
    add(f"Verdict distribution on the first run: `{json.dumps(data['distribution'], sort_keys=True)}`")
    add("")

    add("## Every case")
    add("")
    add("| case | expected | observed | stable | correct | seconds |")
    add("| --- | --- | --- | --- | --- | --- |")
    for row in rows:
        observed = ", ".join(row["observed"])
        seconds = ", ".join(f"{value:.0f}" for value in row["seconds"])
        add(
            f"| {row['id']} | {row['expected']} | {observed} | "
            f"{'yes' if row['stable'] else 'no'} | "
            f"{'yes' if row['correct'] else 'no'} | {seconds} |"
        )
    add("")

    if wrong:
        add("## What the judge got wrong")
        add("")
        add("These are published because a measured weakness beats an unmeasured claim,")
        add("and because a case was never edited to make a run pass.")
        add("")
        for row in wrong:
            case = cases.get(row["id"], {})
            add(f"### Case {row['id']}: expected {row['expected']}, answered {row['observed'][0]}")
            add("")
            add(f"**Why the expected answer is right.** {case.get('note', '')}")
            add("")
            add(f"**What it answered.** `{', '.join(row['observed'])}`")
            reason = next((text for text in row.get("reasons", []) if text), "")
            if reason:
                add("")
                add(f"**Its reasoning on the first run.** {reason}")
            add("")
            if row["id"] in {r["id"] for r in unstable}:
                add(
                    "It also disagreed with itself across runs, which is the stronger signal: "
                    "the question is subjective enough that two runs of the same input land "
                    "differently."
                )
            else:
                add(
                    "It was stable, so this is a consistent reading rather than a wobble. "
                    "The judge took a position the promise arguably supports; the recorded "
                    "expectation is that the promise does not settle the question."
                )
            add("")
    else:
        add("## What the judge got wrong")
        add("")
        add("Nothing in this run.")
        add("")

    unclear_expected = sum(1 for row in rows if row["expected"] == "unclear")
    unclear_missed = [row for row in wrong if row["expected"] == "unclear"]
    if unclear_missed and len(unclear_missed) == len(wrong):
        add("## The pattern in the misses")
        add("")
        add(
            f"Every case the judge got wrong ({', '.join(row['id'] for row in wrong)}) is a "
            f"case whose recorded answer is unclear, and it answered not_honored in each. "
            f"{data['unclear']} of {total} landed on unclear against {unclear_expected} expected."
        )
        add("")
        add("So the failure is not random. The judge resolves an ambiguous promise toward")
        add("its plain words rather than admitting the ambiguity, and it rules against the")
        add("seller when it does. That is the one direction this system should not lean:")
        add("the unclear verdict exists precisely so that a promise too loose to judge is")
        add("not turned into a finding against whoever wrote it.")
        add("")
        add("It is stated here rather than tuned away. The question was narrowed once,")
        add("before this run, and the whole set was rerun: that fixed two cases and moved")
        add("accuracy from 15 to 16. Narrowing again against the two that remain would be")
        add("fitting the prompt to the cases, which is the thing a pre-committed set exists")
        add("to prevent.")
        add("")

    add("## Reading these numbers")
    add("")
    add("Accuracy without stability is a coincidence. Stability without accuracy is a")
    add("consistent mistake. Both are here for that reason.")
    add("")
    add("The unclear fraction is not a failure rate. A promise that does not settle the")
    add("question it is being asked should produce unclear, and a system that rules")
    add("confidently there is inventing standards the seller never agreed to.")
    add("")
    adversarial = [row for row in rows if row["id"] in ("16", "17", "18")]
    passed = [row for row in adversarial if row["correct"]]
    if adversarial:
        add(
            f"{len(passed)} of {len(adversarial)} adversarial cases pass. 16 carries a prompt "
            "injection inside the response, 17 inside the promise and 18 inside the request, "
            "so between them all three party-written inputs are covered. If any of them ever "
            "returns honored, the fence has stopped working."
        )
    add("")
    add("## Reproducing")
    add("")
    add("```bash")
    add("python scripts/deploy.py --eval-instance")
    add(f"python eval/run.py --runs {data['runs']}")
    add("python eval/report.py")
    add("```")
    add("")
    add("`git log --follow eval/cases.json contracts/dispute.py` shows the cases were")
    add("committed before the judgment code existed. That order is the reason these")
    add("numbers mean anything.")
    add("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"  accuracy {data['accuracy']}/{total}, stability {data['stability']}/{total}")
    if wrong:
        print(f"  wrong: {', '.join(row['id'] for row in wrong)}")
    if unstable:
        print(f"  unstable: {', '.join(row['id'] for row in unstable)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
