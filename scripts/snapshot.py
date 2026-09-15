#!/usr/bin/env python3
"""
Record what the chain holds about the frozen contracts, so the evidence
survives a testnet reset.

    python scripts/snapshot.py                              # evidence/snapshot.json and evidence/receipts/
    python scripts/snapshot.py --network studio-next        # evidence/snapshot-studio-next.json, receipts/studio-next/
    python scripts/snapshot.py --contested p-000003 --honest p-000001

Both testnets' persistence is temporary. Every number this repository
publishes was measured against one of the two pairs, and the feed, the case
pages and the README's transaction links all point at them. This script reads everything
back and writes it down: every payment row with its frozen strings, every
case, every transaction the two contracts ever received or sent, decoded to
its method and the payment it concerns, the four refusals, the totals the feed
shows, and the evaluation numbers. The site reads the chain first and this
file second, and says which one it is showing.

evidence/receipts/ holds the raw receipt of every transaction in one contested
cycle and one honest cycle, as the RPC returned them, unedited.

Reads only. The account is a throwaway, because a read needs a sender and
nothing here should ever be able to write.
"""

from __future__ import annotations

import argparse
import base64
import datetime
import json
import pathlib
import shutil
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from genlayer_py import create_account  # noqa: E402
from genlayer_py.abi.calldata.decoder import decode as decode_calldata  # noqa: E402

from shared.chain import (  # noqa: E402
    EXPLORERS, KNOWN_CHAIN_IDS, V06_NETWORKS, Chain, frozen_deployment, frozen_record, network_name, retry,
    select_network,
)

EVIDENCE = ROOT / "evidence"
SNAPSHOT = EVIDENCE / "snapshot.json"
RECEIPTS = EVIDENCE / "receipts"


def snapshot_path(network: str) -> pathlib.Path:
    """studionet keeps evidence/snapshot.json, the file the README has always cited. Every other network gets its own."""
    return SNAPSHOT if network == "studionet" else EVIDENCE / f"snapshot-{network}.json"


def receipts_dir(network: str) -> pathlib.Path:
    """studionet's receipts stay where snapshot.json names them. Every other network's go in a folder of its own."""
    return RECEIPTS if network == "studionet" else RECEIPTS / network

#: Studio allows about thirty requests a minute. Every RPC call here goes
#: through paced(), which keeps the whole run under that without a 429.
PACE_SECONDS = 2.2

STATUS_NAMES = ["open", "withdrawn", "disputed", "resolved"]
VERDICT_NAMES = ["pending", "honored", "not_honored", "unclear"]

#: Consensus statuses come back as numbers from the transaction list and as
#: names from other calls. Both are understood, the name is what gets written.
TX_STATUS = {
    0: "UNINITIALIZED", 1: "PENDING", 2: "PROPOSING", 3: "COMMITTING", 4: "REVEALING", 5: "ACCEPTED",
    6: "UNDETERMINED", 7: "FINALIZED", 8: "CANCELED", 9: "APPEAL_REVEALING", 10: "APPEAL_COMMITTING",
    11: "VALIDATORS_TIMEOUT", 12: "LEADER_TIMEOUT", 13: "LEADER_REVEALING",
}

_last_call = 0.0


def paced(what: str, fn, *args, **kwargs):
    """One RPC call, no sooner than PACE_SECONDS after the previous one, with the usual read retries."""
    global _last_call
    wait = _last_call + PACE_SECONDS - time.time()
    if wait > 0:
        time.sleep(wait)
    try:
        return retry(what, fn, *args, **kwargs)
    finally:
        _last_call = time.time()


# --- decoding what the chain kept --------------------------------------------
def tx_status(raw) -> str:
    if isinstance(raw, int):
        return TX_STATUS.get(raw, str(raw))
    text = str(raw)
    return TX_STATUS.get(int(text), text) if text.isdigit() else text


def decoded_call(tx: dict) -> dict | None:
    """The method and arguments a transaction carried, or None for a plain transfer."""
    data = tx.get("data") or {}
    calldata = data.get("calldata") if isinstance(data, dict) else None
    if not calldata:
        return None
    try:
        call = decode_calldata(memoryview(base64.b64decode(calldata)))
    except Exception as error:  # noqa: BLE001
        return {"method": "?", "args": [], "undecodable": str(error)[:120]}
    if not isinstance(call, dict):
        return {"method": "?", "args": [], "undecodable": "calldata is not a call"}
    args = call.get("args") or []
    # Consensus v0.6 keeps the method name under the empty key, where the
    # earlier ABI called it "method". Both are read.
    method = call.get("method", call.get("", "?"))
    return {"method": str(method), "args": [_short(a) for a in args]}


def _short(value, limit: int = 200) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= limit else text[:limit] + f"... ({len(text)} chars)"


def leader_result(tx: dict) -> dict:
    """
    Execution result and returned value from the leader's receipt.

    A successful call answers a byte 0 and then the calldata-encoded return
    value. A refusal answers a byte 1 and then the message as text. Reading the
    status byte first is what keeps a refusal from being read as a value.
    """
    consensus = tx.get("consensus_data") or {}
    leader = consensus.get("leader_receipt")
    if isinstance(leader, list):
        leader = leader[0] if leader else None
    if not isinstance(leader, dict):
        return {"execution": "", "returned": None, "refusal": "", "vm_error": ""}
    execution = str(leader.get("execution_result", "")).upper()
    raw = leader.get("result")
    returned, refusal, vm_error = None, "", ""
    if isinstance(raw, str) and raw:
        try:
            payload = base64.b64decode(raw)
        except Exception:  # noqa: BLE001
            payload = b""
        if payload and payload[0] == 0:
            try:
                value = decode_calldata(memoryview(payload[1:]))
                returned = value if isinstance(value, (str, int, bool, type(None))) else _short(value)
            except Exception:  # noqa: BLE001
                returned = None
        elif payload and payload[0] == 1:
            refusal = payload[1:].decode("utf-8", "replace")
        elif payload:
            # A VM error, byte 2: the runtime stopped the call, the contract did
            # not refuse it. Kept apart so it is never read as a refusal.
            vm_error = payload[1:].decode("utf-8", "replace")
    return {"execution": execution, "returned": returned, "refusal": refusal, "vm_error": vm_error}


def summarise(tx: dict, explorer: str) -> dict:
    """One transaction, in the words a reader needs: hash, method, payment, outcome, links."""
    call = decoded_call(tx)
    outcome = leader_result(tx)
    value = int(tx.get("value") or 0)
    method = call["method"] if call else ("transfer" if value else "?")
    entry = {
        "hash": tx["hash"],
        "created_at": tx.get("created_at"),
        "from": tx.get("from_address"),
        "to": tx.get("to_address"),
        "value_wei": str(value),
        "method": method,
        "args": call["args"] if call else [],
        "status": tx_status(tx.get("status")),
        "execution": outcome["execution"],
        "returned": outcome["returned"],
        "refusal": outcome["refusal"],
        "vm_error": outcome["vm_error"],
        "triggered_by": tx.get("triggered_by"),
        # When the committee accepted it, and how many validators voted on
        # its last round. The settlement timings and the committee are read
        # from these rather than typed anywhere.
        "accepted_at": tx.get("timestamp_awaiting_finalization"),
        # A receipt names the committee in last_round. A listed record does
        # not, and carries the size the committee started with instead.
        "validators": len((tx.get("last_round") or {}).get("round_validators") or [])
        or int(tx.get("num_of_initial_validators") or 0),
        "triggered": list(tx.get("triggered_transactions") or []),
        "explorer": f"{explorer}/tx/{tx['hash']}",
    }
    if call and call.get("undecodable"):
        entry["undecodable"] = call["undecodable"]
    return entry


def payment_of(entry: dict, by_hash: dict[str, dict]) -> str | None:
    """
    Which payment a transaction concerns.

    pay returns the id. Every other escrow method and the adjudication take the
    id as their first argument. A transfer has no calldata, so it is attributed
    through the transaction that triggered it, walking up until a call names one.
    """
    if entry["method"] == "pay":
        return entry["returned"] if isinstance(entry["returned"], str) else None
    if entry["method"] in {"record_response", "withdraw", "open_dispute", "reclaim", "settle", "adjudicate"}:
        first = entry["args"][0] if entry["args"] else None
        return first if isinstance(first, str) and first.startswith("p-") else None
    seen = set()
    parent = entry.get("triggered_by")
    while parent and parent not in seen and parent in by_hash:
        seen.add(parent)
        pid = payment_of(by_hash[parent], by_hash)
        if pid:
            return pid
        parent = by_hash[parent].get("triggered_by")
    return None


def settlement_timings(transactions: list[dict], payments: list[dict]) -> dict:
    """
    What the README and the site state about settlement, read off the chain.

    Every adjudication is traced by hash: the open_dispute that triggered it,
    the settle it emitted once it finalized, and the payouts that settle sent
    once it finalized in turn. Each figure is a median by the feed's rule,
    sorted and the element at n // 2:

    - dispute to verdict: from the dispute to the settle being accepted, the
      moment the escrow shows the ruling, over every decided dispute
    - dispute to money back: from the dispute to the first payout, over the
      disputes ruled not_honored, the only verdict that returns the payment
    - finality: from a transaction being accepted to the transaction it emits
      on finalization, over both such hops, judgment to settle and settle to
      payout
    - committee: how many validators each adjudication started with
    - dispute to verdict written: from the dispute to the adjudication being
      accepted, the moment the case holds the committee's verdict. On Studio
      Next it is the only one of these that exists: every settle there fails,
      so the verdict is written to the case and never reaches the escrow
    """

    def epoch(value: str) -> float:
        return datetime.datetime.fromisoformat(value).timestamp()

    def median(values: list[float]) -> int | None:
        ordered = sorted(values)
        return round(ordered[len(ordered) // 2]) if ordered else None

    verdict = {p["pid"]: p["verdict_name"] for p in payments}
    by_hash = {e["hash"]: e for e in transactions}
    to_verdict: list[float] = []
    to_case: list[float] = []
    money_back: list[float] = []
    finality: list[float] = []
    committee: list[float] = []
    for judged in transactions:
        if judged["method"] != "adjudicate" or judged["execution"] != "SUCCESS":
            continue
        if judged.get("validators"):
            committee.append(judged["validators"])
        opener = by_hash.get(judged.get("triggered_by") or "")
        if opener and judged.get("accepted_at"):
            to_case.append(judged["accepted_at"] - epoch(opener["created_at"]))
        settle = next(
            (
                e for e in transactions
                if e.get("triggered_by") == judged["hash"] and e["method"] == "settle" and e["execution"] == "SUCCESS"
            ),
            None,
        )
        if not opener or not settle:
            continue
        if judged.get("accepted_at"):
            finality.append(epoch(settle["created_at"]) - judged["accepted_at"])
        if settle.get("accepted_at"):
            to_verdict.append(settle["accepted_at"] - epoch(opener["created_at"]))
        payouts = [e for e in transactions if e.get("triggered_by") == settle["hash"] and e["method"] == "transfer"]
        if payouts and settle.get("accepted_at"):
            finality.append(min(epoch(e["created_at"]) for e in payouts) - settle["accepted_at"])
        if payouts and verdict.get(judged["pid"]) == "not_honored":
            money_back.append(min(epoch(e["created_at"]) for e in payouts) - epoch(opener["created_at"]))
    return {
        "median_dispute_to_verdict_seconds": median(to_verdict),
        "median_dispute_to_case_seconds": median(to_case),
        "median_dispute_to_money_back_seconds": median(money_back),
        "median_finality_seconds": median(finality),
        "committee": median(committee),
    }


def fee_sample(chain: Chain, transactions: list[dict], raw_txs: dict[str, dict], network: str) -> dict:
    """
    What the network charges, read off the chain rather than asserted.

    On a fee charging network each transaction carries its own accounting:
    the deposit it paid, what consensus consumed of it and what came back.
    Those are kept exactly as the chain reported them, in wei. On studionet,
    which charges nothing, the gas figures of each receipt are kept instead.

    The first success of each method on chain, and the first refusal, so the
    sample spans a transaction that ran the judgment and one refused on its
    first check. eth_gasPrice and each
    receipt's effectiveGasPrice and gasUsed are kept exactly as returned.
    """
    picked: dict[str, dict] = {}
    for e in transactions:
        if e["execution"] not in ("SUCCESS", "ERROR"):
            continue
        key = e["method"] if e["execution"] == "SUCCESS" else "refused"
        picked.setdefault(key, e)
    if network in V06_NETWORKS:
        accounting = []
        for key in sorted(picked):
            e = picked[key]
            fees = ((raw_txs.get(e["hash"]) or {}).get("data") or {}).get("fee_accounting") or {}
            accounting.append({
                "hash": e["hash"],
                "method": e["method"],
                "execution": e["execution"],
                "paid_fee_value": str(fees.get("paid_fee_value")),
                "primary_fee_spent": str(fees.get("primary_fee_spent")),
                "total_refunded": str(fees.get("total_refunded")),
            })
        price = paced("eth_gasPrice", chain.client.provider.make_request, "eth_gasPrice", [])
        return {"eth_gasPrice": price.get("result"), "fee_accounting": accounting}
    receipts = []
    for key in sorted(picked):
        e = picked[key]
        got = paced(
            "eth_getTransactionReceipt", chain.client.provider.make_request, "eth_getTransactionReceipt", [e["hash"]],
        )
        receipt = got.get("result") or {}
        receipts.append({
            "hash": e["hash"],
            "method": e["method"],
            "execution": e["execution"],
            "gasUsed": receipt.get("gasUsed"),
            "effectiveGasPrice": receipt.get("effectiveGasPrice"),
        })
    price = paced("eth_gasPrice", chain.client.provider.make_request, "eth_gasPrice", [])
    return {"eth_gasPrice": price.get("result"), "receipts": receipts}


# --- the snapshot ------------------------------------------------------------
def take(chain: Chain, escrow: str, dispute: str, explorer: str, network: str) -> dict:
    stats = paced("stats", chain.read_json, escrow, "stats")
    total = int(stats["payments"])
    rows = paced("recent_rows", chain.read_json, escrow, "recent_rows", [max(total, 1)]) if total else []
    cases = paced("recent_verdicts", chain.read_json, dispute, "recent_verdicts", [max(total, 1)]) if total else []
    case_by_pid = {case["pid"]: case for case in cases}

    payments = []
    for row in sorted(rows, key=lambda r: r["pid"]):
        full = paced("get_payment", chain.read_json, escrow, "get_payment", [row["pid"]])
        payment = dict(full)
        payment["status_name"] = STATUS_NAMES[int(full["status"])] if int(full["status"]) < 4 else str(full["status"])
        payment["verdict_name"] = VERDICT_NAMES[int(full["verdict"])] if int(full["verdict"]) < 4 else str(full["verdict"])
        if row["pid"] in case_by_pid:
            payment["case"] = case_by_pid[row["pid"]]
        payments.append(payment)

    sellers = {}
    for address in sorted({p["seller"] for p in payments}):
        try:
            sellers[address] = paced("get_seller", chain.read_json, escrow, "get_seller", [address])
        except Exception as error:  # noqa: BLE001
            sellers[address] = {"error": str(error)[:160]}

    raw_txs: dict[str, dict] = {}
    for address in (escrow, dispute):
        listed = paced(
            "sim_getTransactionsForAddress", chain.client.provider.make_request, "sim_getTransactionsForAddress", [address],
        )
        for tx in listed.get("result") or []:
            raw_txs[tx["hash"]] = tx
    entries = {h: summarise(tx, explorer) for h, tx in raw_txs.items()}
    for entry in entries.values():
        entry["pid"] = payment_of(entry, entries)
    transactions = sorted(entries.values(), key=lambda e: (e["created_at"] or "", e["hash"]))

    for payment in payments:
        mine = [e for e in transactions if e["pid"] == payment["pid"]]
        landed = {}
        for e in mine:
            if e["execution"] == "SUCCESS" and e["method"] in {
                "pay", "record_response", "open_dispute", "adjudicate", "settle", "withdraw", "reclaim",
            }:
                landed.setdefault(e["method"], e["hash"])
        payment["transactions"] = {
            "pay": landed.get("pay"),
            "record_response": landed.get("record_response"),
            "open_dispute": landed.get("open_dispute"),
            "adjudicate": landed.get("adjudicate"),
            "settle": landed.get("settle"),
            "withdraw": landed.get("withdraw"),
            "reclaim": landed.get("reclaim"),
            "payouts": [e["hash"] for e in mine if e["method"] == "transfer"],
            "every_attempt": [e["hash"] for e in mine],
        }

    refusals = [
        {"hash": e["hash"], "method": e["method"], "refusal": e["refusal"], "from": e["from"], "pid": e["pid"], "explorer": e["explorer"]}
        for e in transactions
        if e["execution"] == "ERROR" and e["refusal"].startswith("[EXPECTED]")
    ]

    fees = fee_sample(chain, transactions, raw_txs, network)

    decided = [p for p in payments if int(p["status"]) == 3]
    verdicts = {name: sum(1 for p in decided if p["verdict_name"] == name) for name in VERDICT_NAMES[1:]}
    elapsed = sorted(
        p["case"]["decided_at"] - p["created_at"] for p in decided if p.get("case") and p["case"]["decided_at"] > p["created_at"]
    )
    totals = {
        "payments": total,
        "by_status": {name: sum(1 for p in payments if p["status_name"] == name) for name in STATUS_NAMES},
        "disputes_opened": sum(1 for p in payments if int(p["status"]) in (2, 3)),
        "decided": len(decided),
        "verdicts": verdicts,
        "upheld": verdicts["not_honored"],
        "upheld_rate": round(verdicts["not_honored"] / len(decided), 4) if decided else None,
        "unjudgeable": verdicts["unclear"],
        "unjudgeable_rate": round(verdicts["unclear"] / len(decided), 4) if decided else None,
        # The feed's rule exactly: sorted, the element at n // 2. The two must agree.
        "median_pay_to_dispute_seconds": int(elapsed[len(elapsed) // 2]) if elapsed else None,
        # What the site's How and Limits sections state, from the chain.
        **settlement_timings(transactions, payments),
        "held_wei": str(stats["held"]),
        "transactions": len(transactions),
        "refusals": len(refusals),
    }
    return {
        "stats": stats,
        "payments": payments,
        "cases": sorted(cases, key=lambda c: c["pid"]),
        "sellers": sellers,
        "transactions": transactions,
        "refusals": refusals,
        "totals": totals,
        "fees": fees,
    }


def evaluation(network: str) -> dict:
    """This network's evaluation numbers, copied from its own measurement files so a drift is a test failure."""
    out = {}
    suffix = "" if network == "studionet" else f".{network}"
    for name, path in (("v1", ROOT / "eval" / f"results{suffix}.json"), ("v2", ROOT / "eval" / f"results-v2{suffix}.json")):
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        out[name] = {
            key: data.get(key) for key in ("instance", "network", "n", "runs", "accuracy", "stability", "unclear", "measured_at")
        }
    return out


# --- the receipts ------------------------------------------------------------
def cycle_hashes(payment: dict) -> list[tuple[str, str]]:
    """The transactions of one payment's cycle, in the order they happened."""
    tx = payment["transactions"]
    ordered = [(m, tx[m]) for m in ("pay", "record_response", "open_dispute", "adjudicate", "settle", "withdraw", "reclaim") if tx.get(m)]
    ordered += [("payout", h) for h in tx.get("payouts", [])]
    return ordered


def write_receipts(chain: Chain, label: str, payment: dict, base: pathlib.Path) -> list[str]:
    folder = base / f"{label}-{payment['pid']}"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    written = []
    for index, (method, tx_hash) in enumerate(cycle_hashes(payment), start=1):
        receipt = paced("get_transaction", chain.client.get_transaction, transaction_hash=tx_hash)
        path = folder / f"{index:02d}-{method}-{tx_hash[2:14]}.json"
        # As returned. sort_keys orders the fields and touches nothing else.
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        written.append(str(path.relative_to(ROOT)).replace("\\", "/"))
    return written


#: The cycles worth keeping raw receipts for: one per outcome the system can
#: reach. Each is (what the payment must look like, what to say when there is
#: none yet). A label with no matching payment is skipped, and the snapshot
#: names only the ones it actually wrote.
#:
#: A verdict cycle must also carry the committee's case. A payment unwound by
#: reclaim is resolved with the unclear split and no case at all, and filing it
#: as the cycle a committee ruled unclear would be a label the chain never
#: gave it.
CYCLES = {
    "contested": (
        lambda p: p["status_name"] == "resolved" and p["verdict_name"] == "not_honored" and bool(p.get("case")),
        "no contested cycle has settled yet",
    ),
    "honest": (
        lambda p: p["status_name"] == "withdrawn",
        "no honest cycle has been withdrawn yet",
    ),
    "honored": (
        lambda p: p["status_name"] == "resolved" and p["verdict_name"] == "honored" and bool(p.get("case")),
        "no dispute has been ruled honored yet",
    ),
    "unclear": (
        lambda p: p["status_name"] == "resolved" and p["verdict_name"] == "unclear" and bool(p.get("case")),
        "no dispute has been ruled unclear yet",
    ),
}


def pick_cycles(payments: list[dict], chosen: dict[str, str | None]) -> dict[str, dict]:
    """One payment per label: the one named, on the command line or by the last snapshot, else the most recent that fits."""
    by_pid = {p["pid"]: p for p in payments}
    picked: dict[str, dict] = {}
    for label, (fits, _) in CYCLES.items():
        named = chosen.get(label)
        if named:
            if named not in by_pid:
                raise SystemExit(f"{named} is not a payment on this deployment")
            picked[label] = by_pid[named]
            continue
        found = next((p for p in reversed(payments) if fits(p)), None)
        if found:
            picked[label] = found
    return picked


def pair_block(record: dict, deployment: dict) -> dict:
    """The recorded pair this network runs: the frozen one on studionet, the port on Studio Next."""
    pair = deployment.get("pair", "frozen")
    source = record if pair == "frozen" else record[pair]
    block = {
        "pair": pair,
        "runtime": source.get("runtime"),
        "escrow_sha256": source["escrow"]["sha256"],
        "dispute_sha256": source["dispute"]["sha256"],
        "window_seconds": record.get("window_seconds"),
        "bond_wei": record.get("bond_wei"),
    }
    if pair == "frozen":
        block["frozen_at_commit"] = record.get("frozen_at_commit")
    else:
        block["diff"] = source.get("diff")
    return block


# --- main --------------------------------------------------------------------
def check(chain: Chain, escrow: str, dispute: str, out: pathlib.Path) -> int:
    """
    Say whether the recorded snapshot still matches the chain.

    Deliberately not part of scripts/test.py. The snapshot tests are
    one directional: they hold the snapshot to the repository, so writing to
    the chain never breaks them, it only makes the snapshot quietly stale. A
    gate that needs the network is a gate people learn to ignore, so this is a
    command someone runs before publishing rather than one CI runs for them.

    A chain that cannot be reached is not a drift. It says so and exits zero.
    """
    if not out.exists():
        print(f"{out.name} does not exist yet. Run: python scripts/snapshot.py")
        return 1
    recorded = json.loads(out.read_text(encoding="utf-8"))
    totals = recorded["totals"]
    print(f"snapshot   recorded {recorded['recorded_at_iso']} on {recorded['network']}")

    # Three quick attempts rather than the ten a snapshot run is willing to
    # spend. Somebody runs this before publishing and waits for the answer, so
    # an unreachable chain has to say so in seconds.
    def quickly(what: str, fn, *fn_args):
        last: Exception | None = None
        for attempt in range(3):
            try:
                return fn(*fn_args)
            except Exception as error:  # noqa: BLE001
                last = error
                time.sleep(2 * (attempt + 1))
        raise last if last else RuntimeError(what)

    try:
        stats = quickly("stats", chain.read_json, escrow, "stats")
        live_payments = int(stats["payments"])
        time.sleep(PACE_SECONDS)
        cases = quickly("recent_verdicts", chain.read_json, dispute, "recent_verdicts", [max(live_payments, 1)])
    except Exception as error:  # noqa: BLE001
        print(f"chain      unreachable: {str(error)[:140]}")
        print("No drift can be measured without the chain, so this is not a failure.")
        return 0

    # Like with like: the chain's cases against the cases the snapshot kept. On
    # studionet every case settles, so these are also the settled verdicts. On
    # Studio Next a case is judged and never settled, and comparing the chain's
    # cases with the settled totals reported a drift that was not there.
    live_verdicts = {name: sum(1 for case in cases if case["verdict_name"] == name) for name in VERDICT_NAMES[1:]}
    kept = {name: sum(1 for case in recorded.get("cases", []) if case["verdict_name"] == name) for name in VERDICT_NAMES[1:]}
    drift = []
    if live_payments != totals["payments"]:
        drift.append(f"payments: snapshot {totals['payments']}, chain {live_payments}")
    for name, count in live_verdicts.items():
        if count != kept[name]:
            drift.append(f"{name}: snapshot {kept[name]}, chain {count}")

    print(f"chain      {live_payments} payments, verdicts {live_verdicts}")
    if not drift:
        print("no drift. The recorded evidence still describes the chain.")
        return 0
    print("\nDRIFT. The snapshot no longer describes the chain:")
    for line in drift:
        print(f"  {line}")
    print("\nEvery published total comes from the snapshot, so re-take it before publishing:")
    network = recorded.get("network", "studionet")
    print("  python scripts/snapshot.py" + ("" if network == "studionet" else f" --network {network}"))
    print("Then check the numbers in README.md and eval/RESULTS.md against it.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--check", action="store_true",
        help="compare the recorded snapshot against the chain and report drift, writing nothing",
    )
    parser.add_argument("--network", default=None, help="the network to read; default studionet")
    parser.add_argument(
        "--out", default=None,
        help="where to write the snapshot; default evidence/snapshot.json on studionet and "
        "evidence/snapshot-<network>.json elsewhere",
    )
    parser.add_argument("--contested", default=None, help="payment id of the contested cycle to keep raw receipts for")
    parser.add_argument("--honest", default=None, help="payment id of the honest cycle to keep raw receipts for")
    parser.add_argument("--honored", default=None, help="payment id of the dispute ruled honored")
    parser.add_argument("--unclear", default=None, help="payment id of the dispute ruled unclear")
    parser.add_argument("--no-receipts", action="store_true", help="write the snapshot only")
    args = parser.parse_args()
    network = select_network(args.network)
    out_path = pathlib.Path(args.out) if args.out else snapshot_path(network)

    deployment = frozen_deployment(network)
    record = frozen_record()
    explorer = deployment.get("explorer") or EXPLORERS[network]
    chain = Chain(create_account())

    print(f"network   {network}  chain {deployment['chain_id']}")
    print(f"escrow    {deployment['escrow']}")
    print(f"dispute   {deployment['dispute']}")

    if args.check:
        return check(chain, deployment["escrow"], deployment["dispute"], out_path)

    print("reading, paced to the rate limit ...")

    body = take(chain, deployment["escrow"], deployment["dispute"], explorer, network)
    now = int(time.time())
    kind = "frozen" if deployment.get("pair", "frozen") == "frozen" else "ported"
    snapshot = {
        "recorded_at": now,
        "recorded_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "note": (
            f"What the chain held about the {kind} contracts on {network} when this was recorded. "
            f"{network} is a temporary testnet. The site reads the chain first and this file second, and "
            "says which one it is showing. Regenerate with: python scripts/snapshot.py"
        ),
        "network": network,
        "chain_id": KNOWN_CHAIN_IDS.get(network, deployment.get("chain_id")),
        "rpc": deployment.get("rpc"),
        "explorer": explorer,
        "escrow": deployment["escrow"],
        "dispute": deployment["dispute"],
        "frozen": pair_block(record, deployment),
        "stats": body["stats"],
        "totals": body["totals"],
        "evaluation": evaluation(network),
        "refusals": body["refusals"],
        "fees": body["fees"],
        "sellers": body["sellers"],
        "payments": body["payments"],
        "cases": body["cases"],
        "transactions": body["transactions"],
        "receipts": {},
    }

    if not args.no_receipts:
        # A re-take keeps the cycles the published snapshot already names,
        # because the README and evidence/README.md cite those payments by
        # id. Without this the newest cycle of each kind silently replaced
        # them, which is how p-000003 was nearly lost as the contested cycle.
        previous: dict[str, str] = {}
        if out_path.exists():
            try:
                recorded = json.loads(out_path.read_text(encoding="utf-8"))
                previous = {label: info["pid"] for label, info in recorded.get("receipts", {}).items()}
            except (ValueError, KeyError, TypeError):
                previous = {}
        chosen = {label: getattr(args, label) or previous.get(label) for label in CYCLES}
        picked = pick_cycles(body["payments"], chosen)
        for label in CYCLES:
            if label in picked:
                snapshot["receipts"][label] = {
                    "pid": picked[label]["pid"],
                    "verdict": picked[label]["verdict_name"],
                    "status": picked[label]["status_name"],
                    "files": write_receipts(chain, label, picked[label], receipts_dir(network)),
                }
            else:
                print(f"{CYCLES[label][1]}; no {label} receipts written")

    out = out_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    t = body["totals"]
    print()
    print(f"wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    print(f"payments            {t['payments']}   {t['by_status']}")
    print(f"disputes opened     {t['disputes_opened']}   decided {t['decided']}   verdicts {t['verdicts']}")
    print(f"upheld rate         {t['upheld_rate']}   unjudgeable rate {t['unjudgeable_rate']}")
    print(f"median pay->dispute {t['median_pay_to_dispute_seconds']} s")
    print(
        f"settlement medians  verdict {t['median_dispute_to_verdict_seconds']} s, money back "
        f"{t['median_dispute_to_money_back_seconds']} s, finality {t['median_finality_seconds']} s, "
        f"committee {t['committee']}"
    )
    print(f"transactions        {t['transactions']}   refusals on chain {t['refusals']}")
    for label, info in snapshot["receipts"].items():
        print(f"{label:9} receipts  {info['pid']}  {info['verdict']:12} {len(info['files'])} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
