#!/usr/bin/env python3
"""
Runs the committed cases N times against the real judgment contract and reports
accuracy, stability and the verdict distribution.

    python eval/run.py --runs 3
    python eval/run.py --runs 1 --only 07,08,12,14

Every case goes to a deployed instance of contracts/dispute.py through real
consensus, so what is measured is the whole judgment path: the prompt, the fence,
the parser, the validator's independent second answer, and a committee agreeing.
A single model call would measure less than that and would flatter the result.

The instance used is the one deployed with its authorised caller set to the
evaluation account, so cases can be put to it without moving money. It runs the
same bytes as the contract wired to the escrow.

Never edit a case to make a run pass. If accuracy is below target, narrow the
adjudication question and rerun.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from shared.chain import Chain, load_accounts, load_deployment

HERE = pathlib.Path(__file__).resolve().parent
CASES = HERE / "cases.json"
NAMES = {0: "pending", 1: "honored", 2: "not_honored", 3: "unclear"}
TARGET = 14


def run_once(chain: Chain, address: str, case: dict, run_index: int, session: str) -> dict:
    """
    One adjudication.

    The case id carries the run index and a per invocation session tag. The
    contract refuses a second verdict on an id it has already decided, which is
    right on chain and would otherwise make a rerun measure the first run's
    answers. That refusal is what a fixed id produced the first time this ran.
    """
    pid = f"e{session}-{case['id']}-r{run_index}"
    started = time.time()
    try:
        outcome = chain.send(
            address,
            "adjudicate",
            [pid, case["promise"], case["request"], case["response"], case["timing"]],
        )
    except Exception as error:  # noqa: BLE001
        return {
            "verdict": "error",
            "detail": str(error)[:220],
            "seconds": round(time.time() - started, 1),
        }

    row = chain.read_json(address, "get_case", [pid])
    return {
        "verdict": NAMES.get(int(row["verdict"]), "pending"),
        "reason": row["reason"],
        "seconds": round(time.time() - started, 1),
        "status": outcome["status"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--out", default=str(HERE / "results.json"))
    parser.add_argument("--only", default="", help="comma separated case ids")
    parser.add_argument("--address", default="", help="override the dispute instance")
    args = parser.parse_args()

    cases = json.loads(CASES.read_text(encoding="utf-8"))
    if args.only:
        wanted = {piece.strip() for piece in args.only.split(",") if piece.strip()}
        cases = [case for case in cases if case["id"] in wanted]
    if not cases:
        raise SystemExit("no cases selected")

    deployment = load_deployment()
    address = args.address or deployment.get("eval_dispute") or deployment["dispute"]
    accounts = load_accounts()
    chain = Chain(accounts["owner"])

    print(f"network   {deployment['network']}")
    print(f"instance  {address}")
    print(f"cases     {len(cases)}   runs {args.runs}\n")

    session = format(int(time.time()) % 100000, "05d")
    print(f"session   {session}\n")
    rows = []
    started = time.time()
    for case in cases:
        observed, reasons, seconds = [], [], []
        for index in range(args.runs):
            result = run_once(chain, address, case, index, session)
            observed.append(result["verdict"])
            reasons.append(result.get("reason", result.get("detail", "")))
            seconds.append(result.get("seconds", 0))
            mark = "ok  " if result["verdict"] == case["expected"] else "MISS"
            print(
                f"  {case['id']} run {index + 1}  {mark} "
                f"expected {case['expected']:<12} got {result['verdict']:<12} "
                f"{result.get('seconds', 0):>5}s"
            )
        agree = len(set(observed)) == 1
        correct = observed[0] == case["expected"]
        rows.append(
            {
                "id": case["id"],
                "expected": case["expected"],
                "observed": observed,
                "reasons": reasons,
                "seconds": seconds,
                "stable": agree,
                "correct": correct,
                "note": case["note"],
            }
        )
        print(f"  {case['id']} -> {'stable' if agree else 'UNSTABLE'}, "
              f"{'correct' if correct else 'wrong'}\n")

    total = len(rows)
    accuracy = sum(1 for row in rows if row["correct"])
    stability = sum(1 for row in rows if row["stable"])
    distribution = collections.Counter(row["observed"][0] for row in rows)
    unclear = distribution.get("unclear", 0)

    print("=" * 62)
    print(f"accuracy   {accuracy}/{total}")
    print(f"stability  {stability}/{total}  across {args.runs} runs")
    print(f"unclear    {unclear}/{total}")
    print(f"verdicts   {dict(distribution)}")
    print(f"elapsed    {time.time() - started:.0f}s")
    wrong = [row["id"] for row in rows if not row["correct"]]
    unstable = [row["id"] for row in rows if not row["stable"]]
    if wrong:
        print(f"wrong      {', '.join(wrong)}")
    if unstable:
        print(f"disagreed  {', '.join(unstable)}")

    payload = {
        "accuracy": accuracy,
        "stability": stability,
        "n": total,
        "runs": args.runs,
        "unclear": unclear,
        "distribution": dict(distribution),
        "network": deployment["network"],
        "instance": address,
        "measured_at": int(time.time()),
        "rows": rows,
    }
    pathlib.Path(args.out).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"\nwrote {args.out}")
    if args.only:
        print("\nA subset run. The published number comes from the whole set.")
    elif accuracy < TARGET:
        print(
            f"\nBelow the target of {TARGET} of {total}. Narrow the adjudication "
            "question and rerun. Never widen it, and never edit a case."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
