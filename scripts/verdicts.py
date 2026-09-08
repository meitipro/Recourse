#!/usr/bin/env python3
"""
Put the two missing verdicts on the public record.

    python scripts/verdicts.py --cycle honored
    python scripts/verdicts.py --cycle unjudgeable
    python scripts/verdicts.py --cycle both

The chain held six disputes and six not_honored. The contract returns three
verdicts and the evaluation set exercises all three, but a reader of the feed
sees the chain and nothing else, and a hundred percent upheld rate reads as a
buyer-side tool rather than an adjudicator. These two cycles put the other two
verdicts where that reader can find them.

  honored       A compliant response, contested anyway. The buyer's own
                deterministic check passes and it files the dispute regardless,
                which the escrow allows on purpose: contesting a good response
                has to cost the bond, or contesting everything is free. The
                buyer agent will not do this, by design, so it is done here.

  unjudgeable   A second seller whose whole promise is "Returns accurate market
                data.", serving a stale price. The breach is real and the
                promise cannot support a ruling on it, so the expectation is
                unclear: the payment stands and the bond comes back. This is
                evaluation case 08 run on chain rather than against a double,
                and it is the strongest single demonstration that the third
                verdict is real.

Nothing here is retried to reach an expectation. Each cycle runs once, the
verdict that lands is the verdict reported, and a surprise is a finding rather
than a reason to run it again.

Two scratch accounts keep the demo's three balances clean: contest_buyer files
these disputes, vague_seller carries the vague promise. Both are written to
.accounts.json, which git ignores, and both are funded from Studio's faucet.
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# A verdict reason is model output and can carry any character; a Windows
# console hands a child process a codepage that cannot encode most of them.
# Widen the console rather than touching the text, which is a record.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from genlayer_py import create_account  # noqa: E402

from agent.checks import check  # noqa: E402
from agent.run import discover_rail, http, read_promise_bounds  # noqa: E402
from seller.signing import verify  # noqa: E402
from shared.chain import (  # noqa: E402
    GEN, KEYS, Chain, load_accounts, load_deployment, select_network,
)

VERDICT = {0: "pending", 1: "honored", 2: "not_honored", 3: "unclear"}
STATUS = {0: "open", 1: "withdrawn", 2: "disputed", 3: "resolved"}

VAGUE_PROMISE = "Returns accurate market data."
MIN_BALANCE = 50 * GEN


# --- accounts ----------------------------------------------------------------
def ensure_accounts(names: list[str]) -> dict:
    """
    Add scratch accounts to .accounts.json without disturbing the three the demo
    reads by name. Existing keys are never rewritten.
    """
    raw = json.loads(KEYS.read_text(encoding="utf-8")) if KEYS.exists() else {}
    added = [name for name in names if name not in raw]
    for name in added:
        raw[name] = create_account().key.hex()
    if added:
        KEYS.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
        print(f"  wrote {', '.join(added)} to {KEYS.name}, which git ignores")
    return load_accounts()


def fund_if_short(chain: Chain, accounts: dict, names: list[str]) -> None:
    for name in names:
        address = accounts[name].address
        balance = chain.balance(address)
        if balance >= MIN_BALANCE:
            print(f"  {name:14} {address[:10]} {balance / GEN:.0f} GEN, enough")
            continue
        print(f"  {name:14} {address[:10]} funding")
        chain.fund(address, 500 * GEN)


# --- the endpoint ------------------------------------------------------------
def start_endpoint(port: int, mode: str, account: str, promise: str | None) -> subprocess.Popen:
    command = [
        sys.executable, "seller/main.py", "--port", str(port), "--mode", mode, "--account", account,
    ]
    if promise:
        command += ["--promise", promise]
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://localhost:{port}/health", timeout=2) as response:
                if response.status == 200:
                    print(f"endpoint   http://localhost:{port}, mode {mode}, signing as {account}")
                    return process
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    process.terminate()
    raise SystemExit(f"the seller endpoint did not come up on {port}")


# --- one cycle ---------------------------------------------------------------
def wait_for_verdict(chain: Chain, escrow: str, dispute: str, pid: str, timeout: int) -> tuple[dict, dict]:
    """Poll until the payment leaves DISPUTED. Returns (payment row, case row or {})."""
    deadline = time.time() + timeout
    row: dict = {}
    while time.time() < deadline:
        time.sleep(5)
        row = chain.read_json(escrow, "get_payment", [pid])
        if int(row["status"]) == 3:
            break
    case: dict = {}
    try:
        case = chain.read_json(dispute, "get_case", [pid])
    except Exception:  # noqa: BLE001
        case = {}
    return row, case


#: Who the settlement table pays, per verdict. Waiting on the right party is the
#: whole difficulty: the buyer's balance has already moved by the time a verdict
#: lands, because it paid and posted a bond, so "did any balance change" answers
#: yes immediately and reports a payout still in flight as one that never came.
PAYEES = {"honored": ("seller",), "not_honored": ("buyer",), "unclear": ("seller", "buyer")}


def settle_balances(
    chain: Chain, who: dict[str, str], verdict: str, seconds: int = 180,
) -> tuple[dict[str, int], bool]:
    """
    Wait for the payouts this verdict implies to land, and say whether they did.

    Each payout is an emitted message that becomes its own transaction and lands
    when the settling transaction finalizes, about half a minute later. The
    baseline is taken here, after the verdict, so what is being waited on is the
    money and nothing else.
    """
    at_verdict = {name: chain.balance(address) for name, address in who.items()}
    expected = [name for name in PAYEES.get(verdict, ()) if name in who]
    deadline = time.time() + seconds
    current = dict(at_verdict)
    while time.time() < deadline and not all(current[name] > at_verdict[name] for name in expected):
        time.sleep(5)
        current = {name: chain.balance(address) for name, address in who.items()}
    landed = all(current[name] > at_verdict[name] for name in expected) if expected else True
    return current, landed


def run_cycle(
    label: str,
    expected: str,
    chain: Chain,
    escrow: str,
    dispute: str,
    buyer_account,
    seller_account,
    seller_address: str,
    port: int,
    amount_gen: int,
    bond_wei: int,
    timeout: int,
) -> dict:
    """One payment, one response, one dispute, one verdict. Never retried."""
    buyer = Chain(buyer_account)
    seller = Chain(seller_account)
    report: dict = {"cycle": label, "expected": expected}

    promise = buyer.read_json(escrow, "get_seller", [seller_address])["promise"]
    report["promise"] = promise
    print(f"promise    {promise}")

    endpoint = f"http://localhost:{port}"
    rail = discover_rail(endpoint, "ETH-USD")

    before = {"buyer": buyer.balance(buyer_account.address), "seller": buyer.balance(seller_address)}
    report["balance_before"] = {k: str(v) for k, v in before.items()}

    request_text = "GET /quote?pair=ETH-USD"
    paid = buyer.send(escrow, "pay", [seller_address, request_text], value=amount_gen * GEN)
    pid = paid["result"]
    if not isinstance(pid, str) or not pid.startswith("p-"):
        raise SystemExit(f"pay did not return a payment id, got {pid!r}")
    report["pid"] = pid
    report["pay_hash"] = paid["hash"]
    print(f"paid       {amount_gen} GEN, payment {pid}")

    code, body, headers = http(f"{endpoint}/quote?pair=ETH-USD", headers={rail["header"]: pid})
    received_at = datetime.datetime.now(datetime.timezone.utc)
    signature = headers.get("x-response-sig", "")
    report["response"] = body
    print(f"response   HTTP {code}, {body}")

    recorded = seller.send(escrow, "record_response", [pid, body, signature])
    report["record_hash"] = recorded["hash"]
    signed = verify(body, signature, seller_address) if signature else False
    report["signature_valid"] = signed
    print(f"recorded   seller signature {'verified' if signed else 'ABSENT'}")

    # What the buyer's own deterministic check made of it, printed whether or
    # not it agrees with the decision to dispute. In the honored cycle it passes
    # and the dispute is filed anyway, which is the whole point of that cycle.
    max_age, min_sources = read_promise_bounds(promise)
    try:
        parsed = json.loads(body)
    except ValueError:
        parsed = {}
    own = check(parsed, "ETH-USD", max_age, min_sources, now=received_at)
    report["buyer_check"] = {"ok": own.ok, "reason": own.reason, "mode": own.mode}
    print(f"buyer check {'pass' if own.ok else 'FAIL'}: {own.reason}")

    contested_at = time.time()
    opened = buyer.send(escrow, "open_dispute", [pid], value=bond_wei)
    report["dispute_hash"] = opened["hash"]
    print(f"disputed   bond {bond_wei / GEN:.0f} GEN posted")

    row, case = wait_for_verdict(buyer, escrow, dispute, pid, timeout)
    verdict = VERDICT.get(int(row.get("verdict", 0)), str(row.get("verdict")))
    report["status"] = STATUS.get(int(row.get("status", 0)), str(row.get("status")))
    report["verdict"] = verdict
    report["reason"] = case.get("reason", "")
    report["seconds_dispute_to_verdict"] = round(time.time() - contested_at, 1)
    print(f"verdict    {verdict}  after {report['seconds_dispute_to_verdict']:.0f}s")
    if report["reason"]:
        print(f"reason     {report['reason']}")

    after, landed = settle_balances(
        buyer, {"buyer": buyer_account.address, "seller": seller_address}, verdict,
    )
    report["balance_after"] = {k: str(v) for k, v in after.items()}
    report["payout_landed"] = landed
    moved = {name: (after[name] - before[name]) / GEN for name in after}
    report["moved_gen"] = {k: round(v, 2) for k, v in moved.items()}
    print(f"buyer      {before['buyer'] / GEN:.2f} -> {after['buyer'] / GEN:.2f} GEN  ({moved['buyer']:+.2f})")
    print(f"seller     {before['seller'] / GEN:.2f} -> {after['seller'] / GEN:.2f} GEN  ({moved['seller']:+.2f})")
    print(f"payout     {'landed' if landed else 'NOT LANDED within the wait; it moves on finalization'}")

    report["as_expected"] = verdict == expected
    print(
        f"expected   {expected}: {'yes' if report['as_expected'] else 'NO, this landed ' + verdict}"
    )
    return report


# --- the two cycles ----------------------------------------------------------
def honored(chain, accounts, deployment, args) -> dict:
    print("\n" + "=" * 70)
    print("  HONORED: a compliant response, contested anyway")
    print("=" * 70)
    print("The seller serves a good response and the buyer's own check passes. It")
    print("files the dispute regardless. Contesting a good response has to cost the")
    print("bond, or contesting everything is free, so the expectation is honored:")
    print("payment and bond both to the seller.\n")
    process = start_endpoint(4501, "correct", "seller", None)
    try:
        return run_cycle(
            "honored", "honored", chain,
            deployment["escrow"], deployment["dispute"],
            accounts["contest_buyer"], accounts["seller"], deployment["seller"],
            4501, args.amount, int(deployment["bond_wei"]), args.timeout,
        )
    finally:
        process.terminate()


def unjudgeable(chain, accounts, deployment, args) -> dict:
    print("\n" + "=" * 70)
    print("  UNJUDGEABLE: a real breach against a promise that cannot settle it")
    print("=" * 70)
    print(f'A second seller whose whole promise is "{VAGUE_PROMISE}" serves a')
    print("stale price. The breach is real and the promise says nothing measurable")
    print("about freshness, so the expectation is unclear: the payment stands and")
    print("the bond comes back, because a vague promise is the seller's fault and")
    print("not the buyer's.\n")

    vague = accounts["vague_seller"]
    escrow = deployment["escrow"]
    try:
        row = chain.read_json(escrow, "get_seller", [vague.address])
        print(f"seller     already registered, promise {row['promise']!r}")
    except Exception as error:  # noqa: BLE001
        if "execution failed" not in str(error) and "unknown seller" not in str(error):
            raise
        try:
            Chain(vague).send(escrow, "register_seller", [VAGUE_PROMISE])
            print(f"seller     registered {vague.address} with the vague promise")
        except RuntimeError as refusal:
            if "already registered" not in str(refusal):
                raise
            print("seller     already registered")

    process = start_endpoint(4502, "stale", "vague_seller", VAGUE_PROMISE)
    try:
        return run_cycle(
            "unjudgeable", "unclear", chain,
            escrow, deployment["dispute"],
            accounts["contest_buyer"], vague, vague.address,
            4502, args.amount, int(deployment["bond_wei"]), args.timeout,
        )
    finally:
        process.terminate()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cycle", default="both", choices=["honored", "unjudgeable", "both"])
    parser.add_argument("--network", default=None, help="the network to run against; default studionet, the only deployment")
    parser.add_argument("--amount", type=int, default=4, help="payment in whole GEN")
    parser.add_argument("--timeout", type=int, default=300, help="seconds to wait for a verdict")
    parser.add_argument("--out", default="", help="also write the reports here as JSON")
    args = parser.parse_args()
    network = select_network(args.network)

    deployment = load_deployment()
    accounts = ensure_accounts(["contest_buyer", "vague_seller"])
    chain = Chain(accounts["owner"])

    print(f"network    {network}")
    print(f"escrow     {deployment['escrow']}")
    print(f"dispute    {deployment['dispute']}")
    print("\nfunding the scratch accounts, where a balance is below 50 GEN")
    fund_if_short(chain, accounts, ["contest_buyer", "vague_seller"])

    reports = []
    if args.cycle in ("honored", "both"):
        reports.append(honored(chain, accounts, deployment, args))
    if args.cycle in ("unjudgeable", "both"):
        reports.append(unjudgeable(chain, accounts, deployment, args))

    print("\n" + "=" * 70)
    print("  result")
    print("=" * 70)
    for report in reports:
        mark = "as expected" if report["as_expected"] else "NOT as expected"
        print(f"{report['cycle']:12} {report['pid']}  {report['verdict']:12} {mark}")
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(reports, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"\nwrote {args.out}")
    print("\nRun python scripts/snapshot.py so the recorded evidence carries these.")
    return 0 if all(r["as_expected"] for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
