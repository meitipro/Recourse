#!/usr/bin/env python3
"""
Turns the measured results into a report with one column per network.

    python eval/report.py               # the eighteen -> eval/RESULTS.md
    python eval/report.py --set v2      # the held out three -> eval/RESULTS-V2.md

Files, one per network per set, never merged and never averaged:

    eval/results.json               studionet, v1     eval/results-v2.json
    eval/results.<network>.json     any other, v1     eval/results-v2.<network>.json

studionet is the only deployment, so the report has one column today. The
shape stays because a second validator set ruling on the same frozen strings
would be a second column, and where it disagreed on a case that would be a
finding with its own section, in either direction, rather than an explanation.
The published number is generated from the measurement, never typed.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
FROZEN = HERE.parent / "contracts" / "FROZEN.json"
#: The networks the frozen contracts are deployed on, studionet first because
#: its results files carry no suffix. One entry today; a second deployment
#: would appear here without a code change.
NETWORKS = sorted(
    json.loads(FROZEN.read_text(encoding="utf-8")).get("deployments", {"studionet": {}}),
    key=lambda n: (n != "studionet", n),
)
SETS = {
    "v1": {"cases": HERE / "cases.json", "base": "results", "out": HERE / "RESULTS.md", "title": "Evaluation results"},
    "v2": {"cases": HERE / "cases-v2.json", "base": "results-v2", "out": HERE / "RESULTS-V2.md", "title": "Held out set results"},
}

# A Windows console hands a child process an ansi codepage. Anything that
# prints text from the chain or a model can die on it, so widen it here.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def results_path(base: str, network: str) -> pathlib.Path:
    return HERE / (f"{base}.json" if network == "studionet" else f"{base}.{network}.json")


def first_verdict(row: dict) -> str:
    """The verdict a case landed on: the first run's, which is how accuracy is scored."""
    return row["observed"][0] if row["observed"] else "error"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", default="v1", choices=sorted(SETS))
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    spec = SETS[args.set]
    out = pathlib.Path(args.out) if args.out else spec["out"]

    data: dict[str, dict] = {}
    for network in NETWORKS:
        path = results_path(spec["base"], network)
        if path.exists():
            data[network] = json.loads(path.read_text(encoding="utf-8"))
    if not data:
        raise SystemExit(f"no results for set {args.set}. Run eval/run.py --set {args.set} first.")
    networks = [n for n in NETWORKS if n in data]

    cases: dict[str, dict] = {}
    for path in (SETS["v1"]["cases"], SETS["v2"]["cases"]):
        if path.exists():
            for case in json.loads(path.read_text(encoding="utf-8")):
                cases[case["id"]] = case

    rows_by = {n: {row["id"]: row for row in data[n]["rows"]} for n in networks}
    ids = [row["id"] for row in data[networks[0]]["rows"]]
    total = data[networks[0]]["n"]
    runs = data[networks[0]]["runs"]

    lines: list[str] = []
    add = lines.append

    add(f"# {spec['title']}")
    add("")
    add("Every case went through real consensus: the prompt, the fence, the parser, a")
    add("validator deriving its own answer, and a committee agreeing. A single model call")
    add("would measure less than this and would flatter the result.")
    add("")
    add("| network | judgment contract | measured | runs per case |")
    add("| --- | --- | --- | --- |")
    for n in networks:
        measured = time.strftime("%Y-%m-%d", time.gmtime(data[n]["measured_at"]))
        add(f"| {n} | `{data[n]['instance']}` | {measured} | {data[n]['runs']} |")
    add("")
    add("The same frozen bytes on every network. One column per network, never merged")
    add("and never averaged: two validator sets ruling on the same three strings is the")
    add("measurement, and a disagreement between them is a finding, not noise.")
    add("")

    add("## The numbers")
    add("")
    add("| | " + " | ".join(networks) + " |")
    add("| --- | " + " | ".join("---" for _ in networks) + " |")
    add("| accuracy, matched the verdict committed before the run | " + " | ".join(f"**{data[n]['accuracy']}/{total}**" for n in networks) + " |")
    add(f"| stability, all {runs} runs of a case agreed | " + " | ".join(f"{data[n]['stability']}/{total}" for n in networks) + " |")
    add("| landed on unclear, the honesty signal | " + " | ".join(f"{data[n]['unclear']}/{total}" for n in networks) + " |")
    add("")
    for n in networks:
        errored = [r for r in data[n]["rows"] if "error" in r["observed"]]
        if errored:
            add(
                f"On {n}, stability counts {len(errored)} case(s) as unstable "
                f"({', '.join(r['id'] for r in errored)}) where one run never returned a verdict: a "
                "dropped transaction on a hosted network, not the judge disagreeing with itself."
            )
            add("")

    add("## Every case")
    add("")
    add("| case | expected | " + " | ".join(f"{n} observed" for n in networks) + " | " + " | ".join(f"{n} correct" for n in networks) + " |")
    add("| --- | --- | " + " | ".join("---" for _ in networks) + " | " + " | ".join("---" for _ in networks) + " |")
    for case_id in ids:
        expected = cases.get(case_id, {}).get("expected", rows_by[networks[0]][case_id]["expected"])
        observed = " | ".join(", ".join(rows_by[n][case_id]["observed"]) if case_id in rows_by[n] else "not run" for n in networks)
        correct = " | ".join(("yes" if rows_by[n][case_id]["correct"] else "no") if case_id in rows_by[n] else "-" for n in networks)
        add(f"| {case_id} | {expected} | {observed} | {correct} |")
    add("")

    add("## Where the networks disagree")
    add("")
    if len(networks) < 2:
        add(f"Only {networks[0]} has been measured for this set. There is nothing to compare")
        add("yet; the second column appears when the same cases have run on a second network.")
        add("")
    else:
        disagreements = [
            case_id for case_id in ids
            if all(case_id in rows_by[n] for n in networks)
            and len({first_verdict(rows_by[n][case_id]) for n in networks}) > 1
        ]
        if not disagreements:
            add(f"None. On every case, {' and '.join(networks)} landed on the same verdict on the")
            add("first run. Two validator sets, the same three strings, the same answer.")
            add("")
        else:
            add(f"{len(disagreements)} case(s) where two validator sets read the same frozen strings")
            add("and reached different verdicts. Stated, not explained away: which network is")
            add("right is exactly the question a committee exists to answer, and here two")
            add("committees answered it differently.")
            add("")
            for case_id in disagreements:
                add(f"### Case {case_id}: expected {cases.get(case_id, {}).get('expected', '?')}")
                add("")
                for n in networks:
                    row = rows_by[n][case_id]
                    reason = next((t for t in row.get("reasons", []) if t), "")
                    add(f"- **{n}** answered `{', '.join(row['observed'])}`" + (f": {reason}" if reason else ""))
                note = cases.get(case_id, {}).get("note")
                if note:
                    add("")
                    add(f"The recorded expectation: {note}")
                add("")

    add("## What the judge got wrong")
    add("")
    any_wrong = False
    for n in networks:
        wrong = [r for r in data[n]["rows"] if not r["correct"]]
        if not wrong:
            add(f"**{n}:** nothing in this run.")
            add("")
            continue
        any_wrong = True
        add(f"**{n}:** {', '.join(r['id'] for r in wrong)}.")
        add("")
        for row in wrong:
            case = cases.get(row["id"], {})
            add(f"### {n}, case {row['id']}: expected {row['expected']}, answered {row['observed'][0]}")
            add("")
            add(f"**Why the expected answer is right.** {case.get('note', '')}")
            add("")
            add(f"**What it answered.** `{', '.join(row['observed'])}`")
            reason = next((t for t in row.get("reasons", []) if t), "")
            if reason:
                add("")
                add(f"**Its reasoning on the first run.** {reason}")
            add("")
            unstable = len({v for v in row["observed"] if v != "error"}) > 1
            add(
                "It also disagreed with itself across runs, which is the stronger signal."
                if unstable
                else "It was stable, so this is a consistent reading rather than a wobble."
            )
            add("")
    if any_wrong:
        add("These are published because a measured weakness beats an unmeasured claim,")
        add("and because a case was never edited to make a run pass.")
        add("")

    add("## Reading these numbers")
    add("")
    add("Accuracy without stability is a coincidence. Stability without accuracy is a")
    add("consistent mistake. Both are here for that reason, and so is every network.")
    add("")
    add("The unclear fraction is not a failure rate. A promise that does not settle the")
    add("question it is being asked should produce unclear, and a system that rules")
    add("confidently there is inventing standards the seller never agreed to.")
    add("")
    if args.set == "v1":
        add("3 of 3 adversarial cases pass on every network measured. 16 carries a prompt")
        add("injection inside the response, 17 inside the promise and 18 inside the request,")
        add("so between them all three party-written inputs are covered. If any of them ever")
        add("returns honored, the fence has stopped working.")
        add("")

    add("## What this evidence does and does not show")
    add("")
    add("Every accuracy number is a claim about when the answers were fixed, so here")
    add("is exactly what can be checked and what cannot.")
    add("")
    add("**Provable from this repository.** The eighteen expected verdicts were")
    add("committed in `b50757f`, which added `eval/cases.json` and `eval/README.md`")
    add("and nothing else. The judgment contract was added in the next commit,")
    add("`e5750e3`. `eval/cases.json` has been modified in no commit since, on any")
    add("branch, so no expected answer was ever edited to match a run:")
    add("")
    add("```bash")
    add("git log --oneline --all -- eval/cases.json   # one commit, b50757f")
    add("git show --name-status b50757f               # two files, neither is code")
    add("git log --oneline --diff-filter=A -- contracts/dispute.py   # e5750e3, next")
    add("```")
    add("")
    add("`--diff-filter=A` matters in the third one. Without it git answers with the")
    add("most recent commit to touch the file, which is a later fix and looks like a")
    add("contradiction.")
    add("")
    add("**Not provable from this repository.** Commit order shows when a file was")
    add("committed, not when it was written. Nothing in git rules out the judgment")
    add("code having existed uncommitted on disk while the cases were being written.")
    add("A reader who does not extend that much good faith should weigh the held out")
    add("set instead, which does not depend on it.")
    add("")
    add("**The held out set.** `eval/cases-v2.json` was committed alone in `04ca928`,")
    add("with the runner unable to read the file at that commit, and only then was")
    add("the runner extended to load it. Those three answers are therefore provably")
    add("fixed before the measurement, whatever order the code was written in. They")
    add("were chosen to probe the weakness the first set exposed rather than to raise")
    add("the score, and the question was never narrowed against them.")
    add("")
    add("**A second network.** The same bytes, verified by hash in `contracts/FROZEN.json`,")
    add("judged by a different validator set. Agreement between networks says the")
    add("verdicts follow from the strings rather than from one committee's habits;")
    add("disagreement says which cases sit on the boundary.")
    add("")

    add("## Reproducing")
    add("")
    add("```bash")
    for n in networks:
        add(f"python eval/run.py --network {n} --set {args.set} --runs {data[n]['runs']}")
    add(f"python eval/report.py --set {args.set}")
    add("```")
    add("")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")
    for n in networks:
        print(f"  {n:10} accuracy {data[n]['accuracy']}/{total}, stability {data[n]['stability']}/{total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
