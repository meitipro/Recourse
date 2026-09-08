#!/usr/bin/env python3
"""
Get a clean clone ready to run the demo against the FROZEN contracts.

    python scripts/prepare.py                       # studionet, the only deployment

Deploys nothing. The contracts are frozen at the bytes in contracts/FROZEN.json
and live at one address pair per network under its `deployments`; every
published number is tied to those. What a clone needs is three accounts of its
own with GEN on the chosen network, a seller among them registered on that
network's escrow, and a deployed.json naming that network's pair, which is
what this writes.

Studio funds accounts over the RPC and this does it for you. On a network with
a browser faucet this would stop and name the page and the addresses when they
are short, and do nothing else.

Idempotent. Run it twice and it funds nothing twice and registers nobody
twice.
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

from shared.chain import (  # noqa: E402
    GEN, Chain, frozen_deployment, frozen_record, load_accounts, network_name,
    require_funds, save_deployment, select_network,
)

MIN_BALANCE = 50 * GEN


def write_feed_env(record: dict) -> None:
    """Point the feed at this network. Addresses come from FROZEN.json; the name is what it needs."""
    path = ROOT / "web" / ".env.local"
    path.write_text(
        "\n".join(
            [
                "# Written by scripts/prepare.py. Edit FROZEN.json, not this file.",
                f"NEXT_PUBLIC_RECOURSE_NETWORK={record['network']}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"  feed env -> {path.relative_to(ROOT)}  (network {record['network']})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network", default=None, help="the network to run against; default studionet, the only deployment")
    args = parser.parse_args()
    network = select_network(args.network)

    from scripts.deploy import PROMISE  # noqa: PLC0415  the same promise every deployment registers

    entry = frozen_deployment(network)
    escrow, dispute = entry["escrow"], entry["dispute"]

    accounts = load_accounts()
    owner, seller, buyer = accounts["owner"], accounts["seller"], accounts["buyer"]
    chain = Chain(owner)
    print(f"network  {network}  (chain {entry['chain_id']})")
    print(f"escrow   {escrow}  (frozen)")
    print(f"dispute  {dispute}  (frozen)")

    print("\nfunding, where a balance is below 50 GEN")
    if network == "studionet":
        for name, account in (("owner", owner), ("seller", seller), ("buyer", buyer)):
            balance = chain.balance(account.address)
            if balance >= MIN_BALANCE:
                print(f"  {name:6} {account.address[:10]} {balance / GEN:.0f} GEN, enough")
                continue
            chain.fund(account.address, 500 * GEN)
    else:
        require_funds(chain, {"owner": owner, "seller": seller, "buyer": buyer}, MIN_BALANCE)
        for name, account in (("owner", owner), ("seller", seller), ("buyer", buyer)):
            print(f"  {name:6} {account.address[:10]} {chain.balance(account.address) / GEN:.0f} GEN")

    print(f"\nthe seller on the {network} escrow")
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
    # Keep whatever an earlier run recorded for THIS network (evidence, an eval
    # instance) and refresh only the parts this machine owns. A record for a
    # different network is replaced: the file describes one network at a time.
    record: dict = {}
    deployed = ROOT / "deployed.json"
    if deployed.exists():
        import json

        previous = json.loads(deployed.read_text(encoding="utf-8"))
        if previous.get("network") == network:
            record = previous
    record.update(
        {
            "network": network,
            "chain_id": entry["chain_id"],
            "escrow": escrow,
            "dispute": dispute,
            "owner": owner.address,
            "seller": seller.address,
            "buyer": buyer.address,
            "window_seconds": int(stats["window_seconds"]),
            "bond_wei": str(stats["bond_amount"]),
            "promise": row["promise"],
            "prepared_at": int(time.time()),
            "frozen_at_commit": frozen_record()["frozen_at_commit"],
        }
    )
    save_deployment(record)
    write_feed_env(record)
    print(f"\nwrote deployed.json for {network}. Now: python scripts/demo.py --network {network}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
