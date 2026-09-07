#!/usr/bin/env python3
"""
Deploy the frozen contracts to a network that does not have them yet.

    python scripts/deploy.py --network bradbury
    python scripts/deploy.py --network studionet

The freeze is over the contract bytes, not over a network: the same two files
go to every network, once each, and FROZEN.json gains one entry per network
under `deployments`. A network that already has an entry is refused unless
--unfreeze is passed, so neither network can be redeployed by accident.

Studio funds accounts over the RPC and this does it. Bradbury's faucet is a
browser page, so on bradbury this stops when the accounts are short and names
the page and the addresses. It writes deployed.json for the chosen network,
which the agent, the evaluation runner and the feed all read.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

# A Windows console hands a child process an ansi codepage. Anything that
# prints text from the chain or a model can die on it, so widen it here.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from shared.chain import (
    CHAINS, EXPLORERS, FROZEN, GEN, KNOWN_CHAIN_IDS, ROOT, Chain, frozen_record, load_accounts,
    network_name, require_funds, save_deployment, select_network,
)

PROMISE = (
    "Returns the spot price for the requested pair, aggregated from at least "
    "three venues, with a timestamp no more than five seconds old."
)


def record_frozen_deployment(network: str, escrow: str, dispute: str) -> None:
    """
    Extend the freeze record with where these bytes now live.

    The freeze is over the bytes, and the two hashes are not touched here. What
    gets added is one entry under `deployments` for this network: chain id, RPC,
    both addresses, when, and the commit the bytes came from. The gate checks
    the chain id against the name, so a wrong chain object fails there rather
    than publishing addresses that are not where they say.
    """
    if not FROZEN.exists():
        return
    import subprocess

    record = frozen_record()
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip() or "unknown"
    rpc = CHAINS[network].rpc_urls["default"]["http"][0]
    record.setdefault("deployments", {})[network] = {
        "chain_id": KNOWN_CHAIN_IDS[network],
        "rpc": rpc,
        "explorer": EXPLORERS.get(network, ""),
        "escrow": escrow,
        "dispute": dispute,
        "deployed_at": int(time.time()),
        "frozen_at_commit": record["frozen_at_commit"],
        "deployed_from_commit": commit,
    }
    FROZEN.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"  FROZEN.json -> deployments.{network}")


def write_feed_env(record: dict) -> None:
    """
    Point the feed at what was just deployed.

    Without this a redeploy leaves web/.env.local naming the previous contracts,
    and nothing looks wrong: the old contracts are still on chain and still
    answer, so the page renders a healthy feed of a deployment that is no longer
    the one this repository describes. A stale address that still works is worse
    than one that errors.
    """
    path = ROOT / "web" / ".env.local"
    path.write_text(
        "\n".join(
            [
                "# Written by scripts/deploy.py. Edit the deployment, not this file.",
                f"NEXT_PUBLIC_RECOURSE_NETWORK={record['network']}",
                f"NEXT_PUBLIC_RECOURSE_ESCROW={record['escrow']}",
                f"NEXT_PUBLIC_RECOURSE_DISPUTE={record['dispute']}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"  feed env -> {path.relative_to(ROOT)}")


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
    parser.add_argument(
        "--network", default=None,
        help="studionet or bradbury; default bradbury. The same frozen bytes go to "
        "every network, one deployment each",
    )
    parser.add_argument(
        "--unfreeze",
        action="store_true",
        help="deploy a NEW pair on a network that already has one in FROZEN.json. "
        "Every published number for that network is tied to its frozen pair; see "
        "FROZEN.json for what a redeploy then has to redo",
    )
    parser.add_argument(
        "--min-balance", type=int, default=10,
        help="whole GEN each account needs on a network with a browser faucet",
    )
    args = parser.parse_args()
    network = select_network(args.network)

    deployments = frozen_record().get("deployments", {}) if FROZEN.exists() else {}
    if network in deployments and not args.unfreeze:
        entry = deployments[network]
        print(f"The contracts are already deployed on {network} and that deployment is frozen:")
        print(f"    escrow   {entry['escrow']}")
        print(f"    dispute  {entry['dispute']}")
        print(f"Every published number for {network} is tied to that pair. A clone that")
        print("wants to run the demo needs accounts, not a deployment:")
        print(f"\n    python scripts/prepare.py --network {network} && python scripts/demo.py --network {network}\n")
        print("If a new deployment there is genuinely required, pass --unfreeze and follow")
        print("if_a_change_is_genuinely_required in FROZEN.json to the end.")
        return 1

    started = time.time()
    accounts = load_accounts()
    owner, seller, buyer = accounts["owner"], accounts["seller"], accounts["buyer"]
    print(f"network  {network_name()}")
    print(f"owner    {owner.address}")
    print(f"seller   {seller.address}")
    print(f"buyer    {buyer.address}")

    chain = Chain(owner)

    print("\nfunding")
    if network == "studionet":
        for name, account in (("owner", owner), ("seller", seller), ("buyer", buyer)):
            chain.fund(account.address, args.fund * GEN)
    else:
        # A browser faucet cannot be called from here, and the raw RPC faucet
        # answers 403. This stops and names the page and the addresses.
        require_funds(chain, {"owner": owner, "seller": seller, "buyer": buyer}, args.min_balance * GEN)
        for name, account in (("owner", owner), ("seller", seller), ("buyer", buyer)):
            print(f"  {name:6} {account.address[:10]} {chain.balance(account.address) / GEN:.2f} GEN")

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
    write_feed_env(record)
    record_frozen_deployment(network, escrow, dispute)
    print(f"\nwrote deployed.json in {time.time() - started:.0f}s")
    print(f"  escrow   {escrow}")
    print(f"  dispute  {dispute}")
    if args.eval_instance:
        print(f"  eval     {record['eval_dispute']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
