#!/usr/bin/env python3
"""
The seller collects an uncontested payment after its window has closed.

    python scripts/withdraw.py p-000001
    python scripts/withdraw.py p-000001 --network studionet

This is the last step of the honest path, the one the demo leaves for the
window to reach: no dispute was filed, the window expired, and the seller
takes the payment. No judgment runs, nobody paid anything extra, and the
feed's row goes from "released, uncollected" to "withdrawn". The contract
refuses it before the window closes, and says so.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from shared.chain import GEN, Chain, load_accounts, load_deployment, select_network  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pid", help="the payment id, p-000001")
    parser.add_argument("--network", default=None, help="the network to run against; default studionet, the only deployment")
    args = parser.parse_args()
    select_network(args.network)

    deployment = load_deployment()
    seller = Chain(load_accounts()["seller"])
    escrow = deployment["escrow"]

    row = seller.read_json(escrow, "get_payment", [args.pid])
    before = seller.balance(deployment["seller"])
    print(f"payment  {args.pid}  {int(row['amount']) / GEN:.2f} GEN  status {row['status']}  window ends {row['window_ends']}")
    outcome = seller.send(escrow, "withdraw", [args.pid])
    print(f"withdrawn  tx {outcome['hash']}")
    # The payout is a value message that becomes its own transaction and lands
    # on finalization, about half a minute after the withdraw is accepted.
    # Reading the balance the instant the receipt arrives reports money still
    # in flight as money that never came, which this printed once.
    deadline = time.time() + 90
    after = seller.balance(deployment["seller"])
    while after <= before and time.time() < deadline:
        time.sleep(5)
        after = seller.balance(deployment["seller"])
    note = "" if after > before else "  (not landed after 90 s; the payout moves on finalization, check again)"
    print(f"seller balance  {before / GEN:.2f} -> {after / GEN:.2f} GEN{note}")
    print("no judgment ran and nobody paid anything extra")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
