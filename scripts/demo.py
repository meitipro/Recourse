#!/usr/bin/env python3
"""
The whole demo, both paths, one command.

    python scripts/demo.py                 both paths
    python scripts/demo.py --contested     the contested path only
    python scripts/demo.py --honest        the honest path only

Starts the seller endpoint, runs the honest path, switches the endpoint to stale,
and runs the contested path. The buyer agent's own lines are on screen as each
step happens, so the verdict appears when it lands and the money when it
arrives, never all at once at the end. Nothing here is staged: every number
comes back from the chain.

The recording runs this through scripts/record.py, and docs/SCRIPT.md says how
to rehearse it: three dry runs of record.py, one real run, then the take.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Model output is printed here, and a model writes whatever characters it likes.
# One verdict reason came back containing a non-breaking hyphen, which the ansi
# codepage a Windows console hands a child process cannot encode, and the demo
# died on the print rather than on anything to do with the chain. Never
# normalise the text itself: it is a record of what was written on chain, not
# house copy. Widen the console instead.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from shared.chain import GEN, Chain, load_accounts, load_deployment, select_network  # noqa: E402

ENDPOINT = "http://localhost:4501"


def wait_for_endpoint(seconds: int = 20) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{ENDPOINT}/health", timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    return False


def rule(title: str) -> None:
    print("\n" + "=" * 66)
    print(f"  {title}")
    print("=" * 66)


def agent(*flags: str) -> dict:
    """
    Run the buyer agent with its lines on screen as they happen, and return its
    report. It used to run under --json with its output captured, so the
    contested path showed nothing for two minutes and then everything at once,
    and the dispute line the recording starts its stopwatch on never showed at
    all. The report now comes back through a file. --json is still there for
    scripts/rail.py, which wants the report alone.
    """
    with tempfile.TemporaryDirectory(prefix="recourse-demo-") as scratch:
        report = pathlib.Path(scratch) / "report.json"
        command = [sys.executable, "-u", "agent/run.py", "--report", str(report), *flags]
        process = subprocess.Popen(
            command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
        assert process.stdout is not None
        for line in process.stdout:
            print("  " + line.rstrip(), flush=True)
        code = process.wait()
        if not report.exists():
            raise SystemExit(f"the agent exited {code} without a report")
        return json.loads(report.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contested", action="store_true", help="skip the honest path")
    parser.add_argument("--honest", action="store_true", help="skip the contested path")
    parser.add_argument("--keep-seller", action="store_true", help="do not start the endpoint")
    parser.add_argument("--network", default=None, help="the network to run against; default studio-next")
    args = parser.parse_args()
    select_network(args.network)

    deployment = load_deployment()
    accounts = load_accounts()
    chain = Chain(accounts["owner"])

    rule("setup")
    print(f"network   {deployment['network']}")
    print(f"escrow    {deployment['escrow']}")
    print(f"dispute   {deployment['dispute']}")
    seller_row = chain.read_json(deployment["escrow"], "get_seller", [deployment["seller"]])
    print(f"promise   {seller_row['promise']}")
    print(f"          judgeable {seller_row['judgeable']}, upheld {seller_row['upheld']} "
          f"of {seller_row['total']} payments")

    process = None
    if not args.keep_seller:
        process = subprocess.Popen(
            [sys.executable, "seller/main.py", "--port", "4501", "--mode", "correct"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not wait_for_endpoint():
            raise SystemExit("the seller endpoint did not come up on 4501")
        print("endpoint  http://localhost:4501, mode correct")

    try:
        if not args.contested:
            rule("the honest path")
            print("The seller serves a good response. The agent checks it, accepts it, and")
            print("lets the window expire. No judgment runs and nobody pays anything extra.\n")
            agent("--mode", "correct", "--no-dispute")

        contested = None
        if not args.honest:
            rule("the contested path")
            print("The same endpoint switches to stale and still returns 200. The agent")
            print("detects it, posts a bond and opens a case. No human is involved.\n")
            contested = agent("--mode", "stale")
            refund = int(contested.get("refund_expected", 0)) / GEN
            landed = contested.get("refund_landed")
            if refund:
                # Read from the chain after the settlement message landed, not
                # inferred from the settlement table. The verdict landing and
                # the money landing are two different transactions.
                print(
                    f"  refund                 {refund:.0f} GEN "
                    + ("returned, balance is net zero" if landed else "NOT YET LANDED"),
                    flush=True,
                )

        rule("result")
        row = chain.read_json(deployment["escrow"], "get_seller", [deployment["seller"]])
        print(f"seller record   {row['upheld']} upheld of {row['total']} payments")
        if contested and contested.get("settlement") == "not moved":
            # On a runtime where the settlement cannot be funded the verdict is
            # the outcome, and the result says so. No money moved, so there is
            # no money to report and nothing here reports any.
            print(f"verdict         {contested['verdict']}")
            print("settlement      not moved: the escrow still holds the payment and the bond")
        elif contested:
            settled = contested.get("settled")
            landed = contested.get("refund_landed")
            # The claim is money back, not verdict reached, so the number that
            # decides it is the one measured to the refund arriving.
            seconds = contested.get(
                "seconds_dispute_to_refund", contested.get("seconds_dispute_to_settlement", 0)
            )
            print(f"verdict         {contested['verdict']}")
            print(f"elapsed         {seconds}s from dispute to money returned")
            print(f"money returned  {'yes' if landed else 'not yet'}")
            print(f"under a minute  {'yes' if settled and landed and seconds < 60 else 'no'}")
        print(f"\nfeed            http://localhost:4500")
        return 0
    finally:
        if process:
            process.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
