#!/usr/bin/env python3
"""
The whole demo, both paths, one command.

    python scripts/demo.py                 both paths
    python scripts/demo.py --contested     the contested path only
    python scripts/demo.py --window 60     a shorter window, for the honest path

Starts the seller endpoint, runs the honest path, switches the endpoint to stale,
runs the contested path, and prints the elapsed times. Nothing here is staged:
every number comes back from the chain.

Follow this three times clean before recording anything.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.chain import GEN, Chain, load_accounts, load_deployment  # noqa: E402

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
    """Run the buyer agent and return its machine readable report."""
    command = [sys.executable, "agent/run.py", "--json", *flags]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    sys.stderr.write(result.stderr)
    try:
        return json.loads(result.stdout)
    except ValueError:
        print(result.stdout[-2000:])
        raise SystemExit("the agent produced no report")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contested", action="store_true", help="skip the honest path")
    parser.add_argument("--honest", action="store_true", help="skip the contested path")
    parser.add_argument("--keep-seller", action="store_true", help="do not start the endpoint")
    args = parser.parse_args()

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
        honest = None
        if not args.contested:
            rule("the honest path")
            print("The seller serves a good response. The agent checks it, accepts it, and")
            print("lets the window expire. No consensus runs and nobody pays anything extra.\n")
            honest = agent("--mode", "correct", "--no-dispute")
            print(f"  check      {honest['check']['reason']}")
            print(f"  payment    {honest['pid']}, {honest['response']}")
            print(f"  outcome    {honest['outcome']}, window ends {honest['window_ends']}")
            print(f"  signature  {'verified' if honest.get('signature_valid') else 'absent'}")

        contested = None
        if not args.honest:
            rule("the contested path")
            print("The same endpoint switches to stale and still returns 200. The agent")
            print("detects it, posts a bond and opens a case. No human is involved.\n")
            contested = agent("--mode", "stale")
            print(f"  check      {contested['check']['reason']}")
            print(f"  verdict    {contested['verdict']}")
            if contested.get("reason"):
                print(f"  reason     {contested['reason']}")
            print(f"  dispute to settlement  {contested['seconds_dispute_to_settlement']}s")
            print(f"  payment to settlement  {contested['seconds_payment_to_settlement']}s")
            before = int(contested["balance_before"]) / GEN
            after = int(contested["balance_after"]) / GEN
            print(f"  buyer balance          {before:.2f} -> {after:.2f} GEN")

        rule("result")
        row = chain.read_json(deployment["escrow"], "get_seller", [deployment["seller"]])
        print(f"seller record   {row['upheld']} upheld of {row['total']} payments")
        if contested:
            settled = contested.get("settled")
            seconds = contested.get("seconds_dispute_to_settlement", 0)
            print(f"verdict         {contested['verdict']}")
            print(f"elapsed         {seconds}s from dispute to money returned")
            print(f"under a minute  {'yes' if settled and seconds < 60 else 'no'}")
        print(f"\nfeed            http://localhost:4500")
        return 0
    finally:
        if process:
            process.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
