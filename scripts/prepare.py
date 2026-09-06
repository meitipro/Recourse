#!/usr/bin/env python3
"""
Get a clean clone ready to run the demo against the FROZEN contracts.

    python scripts/prepare.py

Deploys nothing. The contracts are frozen at the addresses in
contracts/FROZEN.json and every published number is tied to them, so a clone
must not create a new pair to run a demo. What a clone needs instead is three
funded accounts of its own, a seller among them registered on the frozen
escrow, and a deployed.json naming the frozen pair, which is what this writes.

Idempotent. Run it twice and it funds nothing twice and registers nobody
twice.
"""

from __future__ import annotations

import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from scripts.deploy import PROMISE, write_feed_env  # noqa: E402
from shared.chain import GEN, Chain, load_accounts, load_deployment, network_name, save_deployment  # noqa: E402

FROZEN = ROOT / "contracts" / "FROZEN.json"
MIN_BALANCE = 50 * GEN


def main() -> int:
    if not FROZEN.exists():
        raise SystemExit("contracts/FROZEN.json is missing; nothing is frozen to prepare against")
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    escrow, dispute = frozen["escrow"]["address"], frozen["dispute"]["address"]

    accounts = load_accounts()
    owner, seller, buyer = accounts["owner"], accounts["seller"], accounts["buyer"]
    chain = Chain(owner)
    print(f"network  {network_name()}")
    print(f"escrow   {escrow}  (frozen)")
    print(f"dispute  {dispute}  (frozen)")

    print("\nfunding, where a balance is below 50 GEN")
    for name, account in (("owner", owner), ("seller", seller), ("buyer", buyer)):
        balance = chain.balance(account.address)
        if balance >= MIN_BALANCE:
            print(f"  {name:6} {account.address[:10]} {balance / GEN:.0f} GEN, enough")
            continue
        chain.fund(account.address, 500 * GEN)

    print("\nthe seller on the frozen escrow")
    # A view that refuses reaches this side as a bare "execution failed", with
    # the contract's "unknown seller" nowhere in it. So the read is not the
    # test; the registration is. Attempting it is idempotent: a seller already
    # on the escrow is refused with "already registered", which is the answer.
    try:
        row = chain.read_json(escrow, "get_seller", [seller.address])
        print(f"  already registered, promise {len(row['promise'])} chars, judgeable {row['judgeable']}")
    except Exception as error:  # noqa: BLE001
        if "execution failed" not in str(error) and "unknown seller" not in str(error):
            raise
        try:
            Chain(seller).send(escrow, "register_seller", [PROMISE])
            print("  registered")
        except RuntimeError as refusal:
            if "already registered" not in str(refusal):
                raise
            print("  already registered (the read failed, the contract said so instead)")
        row = chain.read_json(escrow, "get_seller", [seller.address])
        print(f"  promise {len(row['promise'])} chars, judgeable {row['judgeable']}")

    stats = chain.read_json(escrow, "stats")
    # Keep whatever an earlier run recorded (evidence, an eval instance) and
    # only refresh the parts this machine owns.
    try:
        record = load_deployment()
    except SystemExit:
        record = {}
    record.update(
        {
            "network": network_name(),
            "escrow": escrow,
            "dispute": dispute,
            "owner": owner.address,
            "seller": seller.address,
            "buyer": buyer.address,
            "window_seconds": int(stats["window_seconds"]),
            "bond_wei": str(stats["bond_amount"]),
            "promise": row["promise"],
            "prepared_at": int(time.time()),
            "frozen_at_commit": frozen["frozen_at_commit"],
        }
    )
    save_deployment(record)
    write_feed_env(record)
    print("\nwrote deployed.json against the frozen pair. Now: python scripts/demo.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
