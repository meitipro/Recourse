#!/usr/bin/env python3
"""
Put both paths on the explorer, not just the successes.

    python scripts/evidence.py

A page showing only successes proves the file compiles. Refusing is what this
contract is for: an escrow whose settlement can be called by anyone is not an
escrow, and the check that stops it is the single most important line in the
project. So the refusal goes on chain deliberately, its hash is recorded, and
the README links to it.

Written into deployed.json under "evidence", so nothing has to be copied by hand
into a document that then drifts.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from shared.chain import GEN, Chain, load_accounts, load_deployment, save_deployment

EXPLORER = "https://explorer-studio.genlayer.com"


def refusal(chain: Chain, address: str, method: str, args: list, expect: str, value: int = 0):
    """
    Make the contract refuse, on chain, and keep the hash.

    The transaction is ACCEPTED: a committee agreed that the refusal is the
    correct execution result. That is the point, and it is why accepted is never
    the same question as succeeded.
    """
    try:
        tx = chain.write(address, method, args, value)
        receipt = chain.wait(tx, "ACCEPTED")
        from shared.chain import check as read_receipt

        outcome = read_receipt(receipt)
        hash_hex = tx if isinstance(tx, str) else getattr(tx, "hex", lambda: str(tx))()
        if outcome["ok"]:
            print(f"  {method}: NOT REFUSED, which is a problem")
            return None
        if expect not in outcome.get("refusal", ""):
            print(f"  {method}: refused with {outcome.get('refusal')!r}, expected {expect!r}")
            return None
        print(f"  {method} refused: {outcome['refusal']}")
        print(f"    status {outcome['status']}, execution {outcome['execution']}")
        print(f"    {EXPLORER}/tx/{hash_hex}")
        return {
            "hash": hash_hex,
            "method": method,
            "refusal": outcome["refusal"],
            "status": outcome["status"],
            "execution": outcome["execution"],
        }
    except Exception as error:  # noqa: BLE001
        print(f"  {method}: could not record: {str(error)[:140]}")
        return None


def main() -> int:
    deployment = load_deployment()
    accounts = load_accounts()
    escrow = deployment["escrow"]
    stranger = Chain(accounts["buyer"])
    seller = Chain(accounts["seller"])

    print(f"network  {deployment['network']}")
    print(f"escrow   {escrow}\n")
    print("recording refusals on chain")

    records = []

    # The one that matters. Without this check any account names its own verdict
    # and drains every payment the contract holds.
    found = refusal(
        stranger, escrow, "settle", ["p-000001", 2, "mine now"], "not authorised"
    )
    if found:
        records.append(found)

    # A seller trying to clear their own judgeability flag. The gate is worthless
    # if the party it judges can overrule it.
    found = refusal(
        seller, escrow, "set_judgeable", [deployment["seller"], True], "not authorised"
    )
    if found:
        records.append(found)

    # Unwinding a dispute that is not stuck. The route out must not be a way to
    # abandon a judgment that is still running.
    found = refusal(stranger, escrow, "reclaim", ["p-000001"], "")
    if found:
        records.append(found)

    print("\nverdicts that have landed on chain")
    verdicts: dict = {}
    try:
        rows = json.loads(stranger.read(deployment["dispute"], "recent_verdicts", [50]))
        for row in rows:
            verdicts.setdefault(row["verdict_name"], row["pid"])
        for name in ("honored", "not_honored", "unclear"):
            where = verdicts.get(name)
            print(f"  {name:<12} {where or 'not yet demonstrated on this deployment'}")
    except Exception as error:  # noqa: BLE001
        print(f"  could not read the case index: {str(error)[:120]}")

    deployment["evidence"] = {
        "refusals": records,
        "verdicts_seen": verdicts,
        "explorer": EXPLORER,
    }
    save_deployment(deployment)
    print(f"\nrecorded {len(records)} refusal(s) into deployed.json")
    if not records:
        print("Nothing was recorded, so nothing is proved. Investigate before submitting.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
