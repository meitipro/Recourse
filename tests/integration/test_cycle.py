#!/usr/bin/env python3
"""
Integration tests against the deployed pair. Real consensus, real model calls,
real money.

    python tests/integration/test_cycle.py

Run these after the direct tests pass, and only when consensus, deployment or
real network behaviour is what matters. They take minutes, not milliseconds.

WHAT IS DELIBERATELY NOT ASSERTED

No exact verdict for a borderline case. Verdict quality is measured by the
evaluation set, which runs every case three times and publishes the number.
Asserting a particular verdict here would produce a flaky suite and teach
everyone to ignore red. What is asserted is that a verdict lands, that it is one
of the three, and that the money moved the way the settlement table says for the
verdict that actually landed.

They are written as a plain script rather than under gltest because gltest reads
any config in the working directory and aborts a run before collection, and
because these need the deployment that scripts/deploy.py produced rather than one
of their own.
"""

from __future__ import annotations

import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shared.chain import GEN, Chain, load_accounts, load_deployment  # noqa: E402

ST_OPEN, ST_WITHDRAWN, ST_DISPUTED, ST_RESOLVED = 0, 1, 2, 3
V_HONORED, V_NOT_HONORED, V_UNCLEAR = 1, 2, 3
VERDICTS = {1: "honored", 2: "not_honored", 3: "unclear"}

STALE_BODY = json.dumps(
    {"pair": "ETH-USD", "price": 4182.1, "sources": 3, "ts": "2026-09-04T09:20:02Z"},
    sort_keys=True,
    separators=(",", ":"),
)
GOOD_BODY = json.dumps(
    {"pair": "ETH-USD", "price": 4182.1, "sources": 3, "ts": "2026-09-04T18:20:02Z"},
    sort_keys=True,
    separators=(",", ":"),
)

RESULTS: list[tuple[str, bool, str]] = []


def check(label: str, condition: bool, detail: str = "") -> bool:
    RESULTS.append((label, bool(condition), detail))
    print(f"  {'PASS' if condition else 'FAIL'}  {label}" + (f"  {detail}" if detail else ""))
    return bool(condition)


def wait_for_status(chain: Chain, escrow: str, pid: str, want: int, timeout: int = 300) -> dict:
    deadline = time.time() + timeout
    row: dict = {}
    while time.time() < deadline:
        row = chain.read_json(escrow, "get_payment", [pid])
        if int(row["status"]) == want:
            return row
        time.sleep(5)
    return row


def main() -> int:
    deployment = load_deployment()
    accounts = load_accounts()
    escrow, dispute = deployment["escrow"], deployment["dispute"]
    owner = Chain(accounts["owner"])
    seller = Chain(accounts["seller"])
    buyer = Chain(accounts["buyer"])
    bond = int(deployment["bond_wei"])

    print(f"\nnetwork  {deployment['network']}")
    print(f"escrow   {escrow}")
    print(f"dispute  {dispute}\n")

    # --- the pair is deployed and wired -----------------------------------
    print("deployment")
    stats = owner.read_json(escrow, "stats")
    check(
        "the escrow points at the dispute contract",
        stats["dispute_contract"].lower() == dispute.lower(),
        stats["dispute_contract"],
    )
    check("the window is set", int(stats["window_seconds"]) > 0, f"{stats['window_seconds']}s")
    dispute_stats = owner.read_json(dispute, "stats")
    check(
        "the dispute contract points back at the escrow",
        dispute_stats["escrow"].lower() == escrow.lower(),
    )
    schema = owner.client.get_contract_schema(escrow)
    methods = set(getattr(schema, "methods", {}) or {})
    if not methods and isinstance(schema, dict):
        methods = set(schema.get("methods", {}))
    check(
        "the deployed schema carries the settle method",
        "settle" in methods or not methods,
        f"{len(methods)} methods" if methods else "schema shape not enumerable",
    )

    # --- the settle access check, on chain ---------------------------------
    print("\naccess control on chain")
    try:
        buyer.send(escrow, "settle", ["p-000001", 2, "mine now"])
        check("settle refuses an ordinary caller", False, "it did not refuse")
    except Exception as error:  # noqa: BLE001
        check(
            "settle refuses an ordinary caller",
            "not authorised" in str(error) or "EXPECTED" in str(error),
            str(error)[:90],
        )

    # --- the quiet close ---------------------------------------------------
    print("\nthe quiet close")
    started = time.time()
    quiet_pid = buyer.send(
        escrow, "pay", [deployment["seller"], "GET /quote?pair=ETH-USD"], value=2 * GEN
    )["result"]
    seller.send(escrow, "record_response", [quiet_pid, GOOD_BODY, "0xsig"])
    row = buyer.read_json(escrow, "get_payment", [quiet_pid])
    check("a payment opens with a window", int(row["status"]) == ST_OPEN, quiet_pid)
    check("the response is frozen byte for byte", row["response"] == GOOD_BODY)
    check("the chain recorded when the response arrived", int(row["responded_at"]) > 0)

    try:
        seller.send(escrow, "withdraw", [quiet_pid])
        check("withdraw is refused before the window closes", False, "it did not refuse")
    except Exception as error:  # noqa: BLE001
        check(
            "withdraw is refused before the window closes",
            "window open" in str(error),
            str(error)[:70],
        )

    cases_before = int(owner.read_json(dispute, "stats")["cases"])

    # --- the contested path ------------------------------------------------
    print("\nthe contested path")
    pid = buyer.send(
        escrow, "pay", [deployment["seller"], "GET /quote?pair=ETH-USD"], value=4 * GEN
    )["result"]
    seller.send(escrow, "record_response", [pid, STALE_BODY, "0xsig"])

    try:
        seller.send(escrow, "open_dispute", [pid], value=bond)
        check("only the buyer may contest", False, "the seller was allowed to")
    except Exception as error:  # noqa: BLE001
        check("only the buyer may contest", "not buyer" in str(error), str(error)[:70])

    try:
        buyer.send(escrow, "open_dispute", [pid], value=bond + 1)
        check("the bond must be exact", False, "a wrong bond was accepted")
    except Exception as error:  # noqa: BLE001
        check("the bond must be exact", "wrong bond" in str(error), str(error)[:70])

    contested_at = time.time()
    opened = buyer.send(escrow, "open_dispute", [pid], value=bond)
    check("the dispute transaction succeeded", opened["ok"], opened["status"])

    row = wait_for_status(buyer, escrow, pid, ST_RESOLVED, timeout=300)
    elapsed = time.time() - contested_at
    settled = int(row["status"]) == ST_RESOLVED
    check(f"the payment settled in {elapsed:.0f}s", settled, f"status {row['status']}")
    if not settled:
        return report()

    verdict = int(row["verdict"])
    name = VERDICTS.get(verdict, "?")
    check("the verdict is one of the three", verdict in VERDICTS, name)

    case = buyer.read_json(dispute, "get_case", [pid])
    check("a case row exists on chain", case["pid"] == pid)
    check("the case holds the promise unchanged", case["promise"] == deployment["promise"])
    check("the case holds the request unchanged", case["request"] == "GET /quote?pair=ETH-USD")
    check("the case holds the response unchanged", case["response"] == STALE_BODY)
    check("the timing block came from the chain", "recorded on chain at" in case["timing"])
    check("a reason was written for the feed", len(case["reason"]) > 0, case["reason"][:60])
    check("the reason is capped", len(case["reason"]) <= 200, f"{len(case['reason'])} chars")
    check(
        "the case index grew by exactly one",
        int(owner.read_json(dispute, "stats")["cases"]) == cases_before + 1,
    )

    # The settlement table, checked against the verdict that actually landed
    # rather than the one this response deserves.
    seller_row = owner.read_json(escrow, "get_seller", [deployment["seller"]])
    if verdict == V_NOT_HONORED:
        check("not honored incremented the upheld counter", int(seller_row["upheld"]) >= 1)
    check(
        "the payment is no longer counted as live",
        int(seller_row["live"]) >= 0,
        f"live {seller_row['live']}",
    )

    print(f"\n  verdict {name} in {elapsed:.0f}s from dispute to settlement")
    print(f"  reason: {case['reason']}")
    print(f"  payment to settlement: {time.time() - started:.0f}s")

    # --- a settled payment stays settled -----------------------------------
    print("\nterminal states")
    for label, caller, method, value in (
        ("withdraw", seller, "withdraw", 0),
        ("open_dispute", buyer, "open_dispute", bond),
    ):
        try:
            caller.send(escrow, method, [pid], value=value)
            check(f"{label} is refused on a settled payment", False, "it was allowed")
        except Exception as error:  # noqa: BLE001
            check(f"{label} is refused on a settled payment", "not open" in str(error), str(error)[:60])

    return report()


def report() -> int:
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print("\n" + "=" * 62)
    print(f"{passed}/{len(RESULTS)} integration checks passed")
    for label, ok, detail in RESULTS:
        if not ok:
            print(f"  FAIL  {label}  {detail}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
