#!/usr/bin/env python3
"""
The buyer agent. Reads the promise from chain, pays, checks, contests.

    python agent/run.py --mode stale          # the contested path
    python agent/run.py --no-dispute          # the honest path
    python agent/run.py --mode stale --json   # machine readable

Its checking logic is deterministic, so the demo produces the same result every
time it runs. The judgment belongs to the validators and never to this agent: if
the agent were smart, the demo would be showing an agent's opinion rather than
the network's verdict, and a judge would notice.

No human is involved between paying and being refunded.
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

# The verdict reason is model output and can carry any character. A Windows
# console hands a child process an ansi codepage that cannot encode most of
# them, so printing one kills the run somewhere that has nothing to do with the
# chain. The text is never normalised, because it is a record of what was
# written on chain rather than copy this project owns.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agent.checks import check
from seller.signing import verify
from shared.chain import GEN, Chain, load_accounts, load_deployment

STATUS = {0: "open", 1: "withdrawn", 2: "disputed", 3: "resolved"}
VERDICT = {0: "pending", 1: "honored", 2: "not_honored", 3: "unclear"}


def http(url: str, payload: dict | None = None, headers: dict | None = None):
    """Returns (status, body text, headers). Never raises on an HTTP error code."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=headers or {})
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.read().decode("utf-8"), dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8"), dict(error.headers)


def discover_rail(endpoint: str, pair: str) -> dict:
    """
    Ask without paying and read the challenge, the way 402 is meant to work.

    The endpoint names the scheme it accepts and the header to present proof in.
    Taking the header from the challenge rather than hardcoding one is what lets
    the same agent buy from an x402 endpoint and from an endpoint settling on
    somebody else's rail, with no flag and no branch.
    """
    fallback = {"scheme": "recourse-escrow", "header": "x-payment-proof"}
    code, body, _ = http(f"{endpoint}/quote?pair={pair}")
    if code != 402:
        # A 200 here means the endpoint is not asking to be paid at all. Say so
        # rather than carrying on as if payment had been demanded.
        return {**fallback, "challenged": False}
    try:
        accepts = json.loads(body).get("accepts") or []
        offer = accepts[0]
        return {
            "scheme": str(offer.get("scheme") or fallback["scheme"]),
            "header": str(offer.get("header") or fallback["header"]),
            "challenged": True,
        }
    except (ValueError, IndexError, AttributeError):
        return {**fallback, "challenged": True}


def read_promise_bounds(promise: str) -> tuple[int, int]:
    """
    Turn the promise into the two numbers the deterministic checks need.

    Three hardcoded patterns, no model. A promise this cannot read falls back to
    bounds that pass everything, so the agent contests nothing it cannot justify
    and the case never reaches consensus on the agent's guesswork.
    """
    words = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    }

    def number(text: str) -> int | None:
        text = text.strip().lower()
        if text.isdigit():
            return int(text)
        return words.get(text)

    max_age = 10**9
    freshness = re.search(
        r"(?:no more than|within|refreshed within)\s+([a-z0-9]+)\s+second", promise, re.I
    )
    if freshness:
        parsed = number(freshness.group(1))
        if parsed is not None:
            max_age = parsed

    min_sources = 0
    sources = re.search(r"at least\s+([a-z0-9]+)\s+(?:venue|source)", promise, re.I)
    if sources:
        parsed = number(sources.group(1))
        if parsed is not None:
            min_sources = parsed

    return max_age, min_sources


def out(payload: dict, as_json: bool, line: str = "") -> None:
    if as_json:
        return
    print(line)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", default="", choices=["", "correct", "stale", "hollow", "substituted"])
    parser.add_argument("--no-dispute", action="store_true", help="pay and accept, for the honest path")
    parser.add_argument("--json", action="store_true", help="machine readable output")
    parser.add_argument("--endpoint", default="http://localhost:4501")
    parser.add_argument("--pair", default="ETH-USD")
    parser.add_argument("--amount", type=int, default=4, help="payment in whole GEN")
    parser.add_argument("--timeout", type=int, default=240, help="seconds to wait for a verdict")
    parser.add_argument(
        "--settlement-id", default="",
        help="an outside rail's own payment reference, presented instead of the escrow id",
    )
    args = parser.parse_args()

    report: dict = {"steps": [], "mode": args.mode or "unchanged"}
    deployment = load_deployment()
    accounts = load_accounts()
    buyer = Chain(accounts["buyer"])
    escrow = deployment["escrow"]
    seller_address = deployment["seller"]

    if args.mode:
        code, body, _ = http(f"{args.endpoint}/admin/mode", {"mode": args.mode})
        if code != 200:
            raise SystemExit(f"could not set the seller mode: {code} {body[:120]}")
        out(report, args.json, f"seller mode      {args.mode}")

    # 1 - read the promise from chain. The endpoint also serves one; the chain is
    # what the seller will be judged against, so the chain is what is used.
    seller_row = buyer.read_json(escrow, "get_seller", [seller_address])
    promise = seller_row["promise"]
    max_age, min_sources = read_promise_bounds(promise)
    report["promise"] = promise
    report["bounds"] = {"max_age_s": max_age, "min_sources": min_sources}
    out(report, args.json, f"promise          {promise}")
    out(report, args.json, f"bounds read      freshness {max_age}s, sources >= {min_sources}")

    code, served, _ = http(f"{args.endpoint}/promise")
    if code == 200:
        endpoint_promise = json.loads(served).get("promise")
        if endpoint_promise != promise:
            out(report, args.json, "  warning: the endpoint's promise differs from the chain's")
        report["promise_matches_endpoint"] = endpoint_promise == promise

    # The 402 challenge names the scheme and the header. Read it rather than
    # assuming x402, so the same agent works against an endpoint that settles
    # somewhere else entirely.
    rail = discover_rail(args.endpoint, args.pair)
    report["rail"] = rail
    out(report, args.json, f"rail             {rail['scheme']}, proof in {rail['header']}")

    balance_before = buyer.balance(accounts["buyer"].address)

    # 2 - pay into escrow. Funds do not reach the seller balance.
    request_text = f"GET /quote?pair={args.pair}"
    started = time.time()
    paid = buyer.send(escrow, "pay", [seller_address, request_text], value=args.amount * GEN)
    # The payment id comes from the transaction's own return value. Reading
    # recent(1) instead would hand back whichever payment landed last, which is
    # not necessarily this one.
    pid = paid["result"]
    if not isinstance(pid, str) or not pid.startswith("p-"):
        raise SystemExit(f"pay did not return a payment id, got {pid!r}")
    report["pid"] = pid
    report["pay_hash"] = paid["hash"]
    out(report, args.json, f"paid             {args.amount} GEN, payment {pid}")

    # 3 - call the endpoint and receive the response immediately. No consensus
    # in this path, so nothing here adds latency to an honest sale.
    # The proof is whatever the rail identifies the settlement by. On x402 that
    # is the escrow payment id; on an outside rail it is that rail's own
    # reference, which the chain never sees and never needs to.
    proof = args.settlement_id or pid
    report["settlement_reference"] = proof
    code, body, headers = http(
        f"{args.endpoint}/quote?pair={args.pair}", headers={rail["header"]: proof}
    )
    # The moment the response arrived. Freshness has to be judged against this
    # and not against the clock at checking time: recording the response on
    # chain takes a consensus round, and measuring after it would call a five
    # second promise stale purely because a transaction took six seconds. The
    # question is whether the response was fresh when it was delivered.
    received_at = datetime.datetime.now(datetime.timezone.utc)
    signature = headers.get("x-response-sig", "")
    report["http_status"] = code
    report["response"] = body
    out(report, args.json, f"response         HTTP {code}, {len(body)} bytes")

    # 4 - record the response on chain. The seller signs; the seller records.
    seller_chain = Chain(accounts["seller"])
    recorded = seller_chain.send(escrow, "record_response", [pid, body, signature])
    report["record_hash"] = recorded["hash"]
    signed_by_seller = verify(body, signature, seller_address) if signature else False
    report["signature_valid"] = signed_by_seller
    out(
        report,
        args.json,
        f"recorded         evidence frozen, seller signature {'verified' if signed_by_seller else 'absent'}",
    )

    # 5 - check the body against the promise. Three deterministic checks.
    try:
        parsed = json.loads(body)
    except ValueError:
        parsed = {}
    verdict = check(parsed, args.pair, max_age, min_sources, now=received_at)
    report["check"] = {
        "ok": verdict.ok,
        "reason": verdict.reason,
        "mode": verdict.mode,
        "contestable": verdict.contestable,
    }
    label = "pass" if verdict.ok else ("declined" if verdict.mode == "declined" else "FAIL")
    out(report, args.json, f"check            {label}: {verdict.reason}")

    # A refusal is not contested. Posting a bond against an endpoint that said
    # it does not carry what was asked for is a false dispute, and the buyer
    # chose the request.
    if verdict.ok or not verdict.contestable or args.no_dispute:
        # 6a - quiet close. The window expires and the seller withdraws. Nobody
        # paid anything extra and no consensus ran.
        row = buyer.read_json(escrow, "get_payment", [pid])
        report["outcome"] = "declined" if verdict.mode == "declined" else "accepted"
        report["window_ends"] = row["window_ends"]
        out(
            report, args.json,
            f"outcome          {report['outcome']}, letting the window expire",
        )
        out(report, args.json, f"                 seller may withdraw after {row['window_ends']}")
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    # 6b - contest. A bond, and a case neither party judges.
    bond = int(deployment["bond_wei"])
    contested_at = time.time()
    opened = buyer.send(escrow, "open_dispute", [pid], value=bond)
    report["dispute_hash"] = opened["hash"]
    out(report, args.json, f"disputed         bond {bond / GEN:.0f} GEN posted, no human involved")

    # 7 - poll until the verdict lands.
    deadline = time.time() + args.timeout
    row = {}
    while time.time() < deadline:
        row = buyer.read_json(escrow, "get_payment", [pid])
        if int(row["status"]) == 3:
            break
        time.sleep(5)

    elapsed = time.time() - contested_at
    total = time.time() - started
    settled = int(row.get("status", 0)) == 3
    name = VERDICT.get(int(row.get("verdict", 0)), "pending")
    report["verdict"] = name
    report["settled"] = settled
    report["seconds_dispute_to_settlement"] = round(elapsed, 1)
    report["seconds_payment_to_settlement"] = round(total, 1)

    case_reason = ""
    if settled:
        try:
            case_reason = buyer.read_json(deployment["dispute"], "get_case", [pid])["reason"]
        except Exception:  # noqa: BLE001
            case_reason = ""
    report["reason"] = case_reason

    # 8 - the money. Balances are read from the chain, never assumed from the
    # settlement table.
    #
    # The verdict landing is not the money landing. Settlement emits a value
    # message, that message becomes its own transaction, and the emitting
    # receipt finalizing means only that it was queued. Reading the balance the
    # instant the status turns RESOLVED reports a refund that is still in
    # flight as one that never came, which is a worse lie than saying nothing.
    expected = int(row.get("amount", 0)) + int(row.get("bond", 0)) if name == "not_honored" else 0
    balance_after = buyer.balance(accounts["buyer"].address)
    refund_deadline = time.time() + 90
    while expected and balance_after < balance_before and time.time() < refund_deadline:
        time.sleep(5)
        balance_after = buyer.balance(accounts["buyer"].address)
    refund_seconds = round(time.time() - (refund_deadline - 90), 1)

    report["balance_before"] = str(balance_before)
    report["balance_after"] = str(balance_after)
    report["refund_expected"] = str(expected)
    report["refund_landed"] = bool(expected) and balance_after >= balance_before
    report["seconds_verdict_to_refund"] = refund_seconds
    report["seconds_dispute_to_refund"] = round(time.time() - contested_at, 1)

    out(report, args.json, "")
    out(report, args.json, f"verdict          {name}")
    if case_reason:
        out(report, args.json, f"reason           {case_reason}")
    out(report, args.json, f"dispute to verdict      {elapsed:.0f}s")
    out(report, args.json, f"dispute to money back   {report['seconds_dispute_to_refund']:.0f}s")
    out(report, args.json, f"payment to settlement   {total:.0f}s")
    out(
        report,
        args.json,
        f"buyer balance    {balance_before / GEN:.2f} -> {balance_after / GEN:.2f} GEN"
        + (
            f"  ({expected / GEN:.0f} returned)"
            if report["refund_landed"]
            else f"  (waiting on {expected / GEN:.0f} GEN)"
            if expected
            else ""
        ),
    )
    if not settled:
        out(report, args.json, f"  still {STATUS.get(int(row.get('status', 0)), '?')} after {args.timeout}s")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if settled or args.no_dispute else 1


if __name__ == "__main__":
    raise SystemExit(main())
