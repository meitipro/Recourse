"""
The five reads as data.

The commands format these for a person, and the conversational agent hands
them to the model as tool results. One place reads the chain for both, so a
command and a free text answer about the same case cannot disagree.

Every value here comes from a call made now: the chain, the linter, or the
committed evaluation files. A read that fails raises Unavailable, and the caller
says what could not be read rather than filling the gap.
"""

from __future__ import annotations

import datetime
import re
import typing

STATUS = ["open", "withdrawn", "disputed", "resolved"]
VERDICT = ["pending", "honored", "not_honored", "unclear"]
GEN = 10**18
ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}")


class Unavailable(RuntimeError):
    """A dependency could not answer. The reply says so; it never guesses."""


class Deps(typing.Protocol):
    def read_json(self, contract: str, method: str, args: list) -> typing.Any: ...
    def lint(self, promise: str) -> dict: ...
    def dry_run(self, promise: str, response: str) -> dict: ...
    def evaluation(self) -> dict: ...
    def addresses(self) -> dict: ...


def to_pid(text: str) -> str:
    cleaned = text.strip()
    cite = re.fullmatch(r"RC-\d{4}-(\d{4,6})", cleaned, re.I)
    if cite:
        return f"p-{int(cite.group(1)):06d}"
    plain = re.fullmatch(r"p-(\d{1,6})", cleaned, re.I)
    if plain:
        return f"p-{int(plain.group(1)):06d}"
    if re.fullmatch(r"\d{1,6}", cleaned):
        return f"p-{int(cleaned):06d}"
    raise ValueError(f"not a case id: {cleaned}. Use p-000043 or RC-2026-0043.")


def citation(pid: str, decided_at: int) -> str:
    year = datetime.datetime.fromtimestamp(decided_at, datetime.timezone.utc).year if decided_at else datetime.datetime.now(datetime.timezone.utc).year
    return f"RC-{year}-{int(pid.split('-')[1]):04d}"


def gen(wei: str | int) -> str:
    value = int(wei)
    return f"{value // GEN}.{(value % GEN) // 10**16:02d} GEN"


def clock(seconds: int) -> str:
    if not seconds:
        return "-"
    return datetime.datetime.fromtimestamp(int(seconds), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def case_record(argument: str, deps: Deps) -> dict:
    """
    One case as data. Raises ValueError for an id that is not one, and
    Unavailable when the payment itself cannot be read. A case that has not
    been decided carries no verdict and no reason, because there is none yet
    and nothing here invents one.
    """
    pid = to_pid(argument)
    a = deps.addresses()
    payment = deps.read_json(a["escrow"], "get_payment", [pid])
    code = payment["status"]
    status = STATUS[code] if 0 <= code < 4 else str(code)
    if code < 2:
        return {"pid": pid, "status": status, "disputed": False, "window_ends": clock(payment["window_ends"])}
    try:
        case = deps.read_json(a["dispute"], "get_case", [pid])
    except Unavailable:
        return {
            "pid": pid,
            "status": status,
            "disputed": True,
            "decided": False,
            "dispute_ends": clock(payment["dispute_ends"]),
            "note": "judgment is still running: there is no case row yet, so nothing is decided",
        }
    response = case["response"]
    return {
        "citation": citation(pid, case["decided_at"]),
        "pid": pid,
        "status": status,
        "disputed": True,
        "decided": True,
        "verdict": case.get("verdict_name") or VERDICT[case["verdict"]],
        "money": "moved" if code == 3 else "verdict written, money moves on finalization",
        "reason": case["reason"],
        "promise": case["promise"],
        "request": case["request"],
        "response": response[:600] + (" ..." if len(response) > 600 else ""),
        "timing": case["timing"],
        "amount": gen(payment["amount"]),
        "bond": gen(payment["bond"]),
        "paid_at": clock(payment["created_at"]),
        "decided_at": clock(case["decided_at"]),
        "explorer": a["explorer"],
    }


def seller_record(address: str, deps: Deps) -> dict:
    """A seller's public record. ValueError for anything that is not an address."""
    address = address.strip()
    if not ADDRESS.fullmatch(address):
        raise ValueError("not a seller address: it has to be the full address, 0x and forty hex characters")
    a = deps.addresses()
    seller = deps.read_json(a["escrow"], "get_seller", [address])
    try:
        gate = deps.read_json(a["dispute"], "gate_reason", [address]) or ""
    except Unavailable:
        gate = ""
    return {
        "address": seller["address"],
        "promise": seller["promise"],
        "active": bool(seller["active"]),
        "judgeable": bool(seller["judgeable"]),
        "payments_taken": seller["total"],
        "live": seller["live"],
        "disputes_upheld_against": seller["upheld"],
        "registered_at": clock(seller["registered_at"]),
        "gate_said": gate or None,
    }


def stats_record(deps: Deps) -> dict:
    """
    Live counts from chain and both evaluation figures. Either half can fail
    on its own, and the one that failed says so in place of its numbers.
    """
    a = deps.addresses()
    out: dict = {"network": a.get("network", "studionet"), "escrow": a["escrow"], "dispute": a["dispute"]}
    try:
        e = deps.read_json(a["escrow"], "stats", [])
        d = deps.read_json(a["dispute"], "stats", [])
        out["live"] = {
            "payments": e["payments"],
            "cases": d["cases"],
            "held": gen(e["held"]),
            "bond": gen(e["bond_amount"]),
            "window_seconds": e["window_seconds"],
        }
    except Unavailable as error:
        out["live_error"] = str(error)
    try:
        ev = deps.evaluation()
        out["evaluation"] = {
            "tuned": ev["tuned"],
            "held_out": ev["held_out"],
            "note": (
                "both figures, always together: the tuned set is the one the question was narrowed "
                "against, the held out set was committed before it could be run and never tuned against"
            ),
        }
    except Unavailable as error:
        out["evaluation_error"] = str(error)
    return out


def verdict_split(deps: Deps, cases: int) -> dict:
    """
    How decided cases split between the three verdicts, counted from the
    dispute contract's own page of recent verdicts. The contract caps that page,
    so the result says how many it counted rather than assuming it saw them all.
    """
    a = deps.addresses()
    rows = deps.read_json(a["dispute"], "recent_verdicts", [int(cases)]) if int(cases) > 0 else []
    counts = {name: sum(1 for row in rows if row.get("verdict_name") == name) for name in VERDICT[1:]}
    counted = sum(counts.values())
    return {
        "counted": counted,
        "counts": counts,
        "percent": {name: round(100 * n / counted) for name, n in counts.items()} if counted else {},
        "what_each_means": (
            "honored: payment and bond to the seller. unclear: payment to the seller, bond back to "
            "the buyer. not_honored: payment and bond back to the buyer."
        ),
    }
