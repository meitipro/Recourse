#!/usr/bin/env python3
"""
Deploy both contracts, wire them, fund the three accounts, register the seller.

    python scripts/deploy.py

Studio persistence is temporary, so this recreates the whole state in one
command and is meant to be run every morning. It writes deployed.json, which the
agent, the evaluation runner and the feed all read.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from shared.chain import GEN, ROOT, Chain, load_accounts, network_name, save_deployment

PROMISE = (
    "Returns the spot price for the requested pair, aggregated from at least "
    "three venues, with a timestamp no more than five seconds old."
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", type=int, default=300, help="settlement window in seconds")
    parser.add_argument("--bond", type=int, default=1, help="buyer bond in whole GEN")
    parser.add_argument("--fund", type=int, default=500, help="GEN to fund each account with")
    parser.add_argument(
        "--eval-instance",
        action="store_true",
        help="also deploy a dispute instance whose authorised caller is the owner, "
        "so the evaluation runner can put cases to it directly",
    )
    args = parser.parse_args()

    started = time.time()
    accounts = load_accounts()
    owner, seller, buyer = accounts["owner"], accounts["seller"], accounts["buyer"]
    print(f"network  {network_name()}")
    print(f"owner    {owner.address}")
    print(f"seller   {seller.address}")
    print(f"buyer    {buyer.address}")

    chain = Chain(owner)

    print("\nfunding")
    for name, account in (("owner", owner), ("seller", seller), ("buyer", buyer)):
        chain.fund(account.address, args.fund * GEN)

    print("\ndeploying")
    escrow = chain.deploy(ROOT / "contracts" / "escrow.py", [args.window, args.bond * GEN])
    dispute = chain.deploy(ROOT / "contracts" / "dispute.py", [escrow])

    print("\nwiring")
    chain.send(escrow, "set_dispute_contract", [dispute])
    stats = chain.read_json(escrow, "stats")
    if stats["dispute_contract"].lower() != dispute.lower():
        raise SystemExit(f"wiring did not take: escrow points at {stats['dispute_contract']}")
    print(f"  escrow -> dispute  {stats['dispute_contract']}")

    print("\nregistering the seller")
    seller_chain = Chain(seller)
    seller_chain.send(escrow, "register_seller", [PROMISE])
    row = chain.read_json(escrow, "get_seller", [seller.address])
    print(f"  promise stored, {len(row['promise'])} chars, judgeable {row['judgeable']}")

    record = {
        "network": network_name(),
        "escrow": escrow,
        "dispute": dispute,
        "owner": owner.address,
        "seller": seller.address,
        "buyer": buyer.address,
        "window_seconds": args.window,
        "bond_wei": str(args.bond * GEN),
        "promise": PROMISE,
        "deployed_at": int(time.time()),
    }

    if args.eval_instance:
        print("\ndeploying the evaluation instance")
        # A second dispute contract whose authorised caller is the owner account
        # rather than the escrow. It lets the evaluation runner put a case
        # directly to the real judgment code, on real consensus, without moving
        # money. Its settle emission goes to an account rather than a contract
        # and fails as its own transaction, which is expected and harmless: the
        # case row is written before the message is emitted.
        eval_dispute = chain.deploy(ROOT / "contracts" / "dispute.py", [owner.address])
        record["eval_dispute"] = eval_dispute

    save_deployment(record)
    print(f"\nwrote deployed.json in {time.time() - started:.0f}s")
    print(f"  escrow   {escrow}")
    print(f"  dispute  {dispute}")
    if args.eval_instance:
        print(f"  eval     {record['eval_dispute']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
