"""
What the bot says. Pure functions over injected dependencies, so every reply
can be tested without Telegram, a chain or a model.

    handle(chat_id, text, conversations, bucket, deps) -> reply

Every number in a reply comes from a call made in that turn: the chain, the
linter, the committed evaluation files. Nothing is recalled from memory, and
when a call fails the reply says what could not be read rather than filling
the gap.
"""

from __future__ import annotations

import json
import re
import typing

from bot.guard import COMPROMISED, looks_like_secret

STATUS = ["open", "withdrawn", "disputed", "resolved"]
VERDICT = ["pending", "honored", "not_honored", "unclear"]
GEN = 10**18

HELP = """Recourse, read only. Nothing here holds a key or moves money.

/promise <text>   is this promise judgeable? The linter, in chat.
/check            a dry run of the judge: the promise, then the response body.
/case <id>        one adjudicated case, by p-000043 or RC-2026-0043.
/seller <addr>    a seller's public record.
/stats            live counts from chain, and both evaluation figures.
/help             this.

Paying, disputing and withdrawing are done from your own wallet. The exact calls are in the skill: github.com/meitipro/recourse-skill"""

ON_TOPIC = (
    "recourse", "genlayer", "x402", "dispute", "escrow", "bond", "verdict", "promise",
    "judge", "chargeback", "refund", "machine payment", "paid api", "stale", "hollow",
    "substituted", "unclear", "honored", "studionet", "validator", "settle",
)

REDIRECT = "This bot answers questions about Recourse, GenLayer, x402 and machine payment disputes, and it answers numbers only from a call it just made.\n\n" + HELP


class Deps(typing.Protocol):
    def read_json(self, contract: str, method: str, args: list) -> typing.Any: ...
    def lint(self, promise: str) -> dict: ...
    def dry_run(self, promise: str, response: str) -> dict: ...
    def evaluation(self) -> dict: ...
    def addresses(self) -> dict: ...


class Unavailable(RuntimeError):
    """A dependency could not answer. The reply says so; it never guesses."""


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
    import datetime

    year = datetime.datetime.fromtimestamp(decided_at, datetime.timezone.utc).year if decided_at else datetime.datetime.now(datetime.timezone.utc).year
    return f"RC-{year}-{int(pid.split('-')[1]):04d}"


def gen(wei: str | int) -> str:
    value = int(wei)
    return f"{value // GEN}.{(value % GEN) // 10**16:02d} GEN"


def clock(seconds: int) -> str:
    import datetime

    if not seconds:
        return "-"
    return datetime.datetime.fromtimestamp(int(seconds), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- commands ---------------------------------------------------------------


def cmd_promise(argument: str, deps: Deps) -> str:
    if not argument.strip():
        return "Send the promise after the command: /promise Returns the spot price for the requested pair, refreshed within five seconds."
    try:
        result = deps.lint(argument)
    except Unavailable as error:
        return f"The linter could not answer: {error}. Stage 1 is free and deterministic; stage 2 needs a model the linter does not have right now."
    lines = []
    if result["judgeable"]:
        lines.append("JUDGEABLE. " + result["reason"])
        lines.append("A response could be ruled against this. That is what a promise is for.")
    else:
        head = "NOT JUDGEABLE"
        if result.get("failed_check"):
            head += f" (failed: {result['failed_check']}, no model was asked)"
        lines.append(head + ". " + result["reason"])
        if result.get("suggestion"):
            lines.append("\nA rewrite that keeps your intent and passes the checks:\n\n" + result["suggestion"])
    lines.append(f"\nstage {result['stage']} of the linter. Stage 2 is the deployed gate's question put to one model: a dry run, not the gate's verdict. Nothing you send here is stored.")
    return "\n".join(lines)


def cmd_case(argument: str, deps: Deps) -> str:
    try:
        pid = to_pid(argument)
    except ValueError as error:
        return str(error)
    a = deps.addresses()
    try:
        payment = deps.read_json(a["escrow"], "get_payment", [pid])
    except Unavailable as error:
        return f"Could not read {pid} from the chain: {error}"
    status = STATUS[payment["status"]] if 0 <= payment["status"] < 4 else str(payment["status"])
    if payment["status"] < 2:
        return f"{pid} was never disputed, so there is no case to read. Status: {status}. Window ends {clock(payment['window_ends'])}."
    try:
        case = deps.read_json(a["dispute"], "get_case", [pid])
    except Unavailable:
        return f"{pid} is disputed and judgment is still running: no case row yet. Dispute ends {clock(payment['dispute_ends'])}."
    verdict = case.get("verdict_name") or VERDICT[case["verdict"]]
    return "\n".join([
        f"{citation(pid, case['decided_at'])}  ({pid})",
        f"verdict   {verdict}",
        f"status    {status}" + ("  (money moved)" if payment["status"] == 3 else "  (verdict written, money moves on finalization)"),
        f"reason    {case['reason']}",
        "",
        f"promise   {case['promise']}",
        f"request   {case['request']}",
        f"response  {case['response'][:600]}" + (" ..." if len(case["response"]) > 600 else ""),
        f"timing    {case['timing']}",
        "",
        f"amount {gen(payment['amount'])}, bond {gen(payment['bond'])}, paid {clock(payment['created_at'])}, decided {clock(case['decided_at'])}",
        f"{a['explorer']}",
    ])


def cmd_seller(argument: str, deps: Deps) -> str:
    address = argument.strip()
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", address):
        return "Send an address after the command: /seller 0x965c98389197055CFb3FD8b1E3e9a11AE6d40C99"
    a = deps.addresses()
    try:
        seller = deps.read_json(a["escrow"], "get_seller", [address])
    except Unavailable as error:
        return f"Could not read that seller: {error}"
    gate = ""
    try:
        gate = deps.read_json(a["dispute"], "gate_reason", [address]) or ""
    except Unavailable:
        gate = ""
    lines = [
        f"seller     {seller['address']}",
        f"promise    {seller['promise']}",
        f"active     {'yes' if seller['active'] else 'no'}    judgeable {'yes' if seller['judgeable'] else 'NO, payments refused'}",
        f"payments   {seller['total']} taken, {seller['live']} live, {seller['upheld']} disputes upheld against it",
        f"registered {clock(seller['registered_at'])}",
    ]
    if gate:
        lines.append(f"gate said  {gate}")
    return "\n".join(lines)


def cmd_stats(deps: Deps) -> str:
    a = deps.addresses()
    lines = [f"studionet, frozen contracts", f"escrow  {a['escrow']}", f"dispute {a['dispute']}", ""]
    try:
        e = deps.read_json(a["escrow"], "stats", [])
        d = deps.read_json(a["dispute"], "stats", [])
        lines.append(f"payments {e['payments']}   cases {d['cases']}   held {gen(e['held'])}   bond {gen(e['bond_amount'])}   window {e['window_seconds']}s")
    except Unavailable as error:
        lines.append(f"live counts could not be read: {error}")
    lines.append("")
    try:
        ev = deps.evaluation()
        tuned, held = ev["tuned"], ev["held_out"]
        lines.append(f"evaluation, both figures, always together:")
        lines.append(f"  {tuned['accuracy']}/{tuned['n']} on the set the question was narrowed against")
        lines.append(f"  {held['accuracy']}/{held['n']} on the held out set, committed before it could be run and never tuned against")
        lines.append("The pattern both agree on: a promise that does not settle the question gets answered on its plain words.")
    except Unavailable as error:
        lines.append(f"evaluation figures could not be read: {error}")
    return "\n".join(lines)


def cmd_check(chat_id: int, argument: str, conversations, deps: Deps) -> str:
    state = conversations.get(chat_id) or {}
    if state.get("step") == "response":
        promise = state["promise"]
        response = argument.strip()
        conversations.clear(chat_id)
        if not response:
            return "Send the response body as the next message."
        try:
            result = deps.dry_run(promise, response)
        except Unavailable as error:
            return f"DRY RUN could not run: {error}. No model is available to ask, so no verdict is offered."
        return "\n".join([
            f"DRY RUN, no money, no consensus. One model, both presentation orders, the deployed contract's own judge().",
            f"verdict  {result['verdict']}",
            f"reason   {result['reason']}",
            f"orders   {'agreed' if result.get('agreed') == 'yes' else 'DISAGREED, resolved to unclear'}",
            "",
            "On chain this would be a five node committee. Treat this as what the judge would probably say, not what it did say.",
        ])
    if argument.strip():
        conversations.set(chat_id, {"step": "response", "promise": argument.strip()})
        return "Promise noted. Now send the response body, as the endpoint returned it."
    conversations.set(chat_id, {"step": "promise"})
    return "Step 1 of 2: send the seller's promise."


def handle(chat_id: int, text: str, conversations, bucket, deps: Deps) -> str:
    """One message in, one reply out. The secret check runs before anything."""
    text = (text or "").strip()
    if not text:
        return HELP

    what = looks_like_secret(text)
    if what:
        conversations.clear(chat_id)
        return COMPROMISED.format(what=what)

    state = conversations.get(chat_id) or {}
    command, _, argument = text.partition(" ")
    command = command.lower().split("@")[0]

    # A conversation in progress takes plain text as its next step.
    if state.get("step") == "promise" and not text.startswith("/"):
        conversations.set(chat_id, {"step": "response", "promise": text})
        return "Promise noted. Now send the response body, as the endpoint returned it."
    if state.get("step") == "response" and not text.startswith("/"):
        if not bucket.take(chat_id, cost=bucket.expensive):
            return "Slow down: too many model backed requests in this chat. Try again in a minute."
        return cmd_check(chat_id, text, conversations, deps)

    if command in ("/start", "/help"):
        return HELP
    if command == "/promise":
        if not bucket.take(chat_id, cost=bucket.expensive):
            return "Slow down: too many model backed requests in this chat. Try again in a minute."
        return cmd_promise(argument, deps)
    if command == "/check":
        if not bucket.take(chat_id):
            return "Slow down. Try again in a minute."
        return cmd_check(chat_id, argument, conversations, deps)
    if command == "/case":
        if not bucket.take(chat_id):
            return "Slow down. Try again in a minute."
        return cmd_case(argument, deps)
    if command == "/seller":
        if not bucket.take(chat_id):
            return "Slow down. Try again in a minute."
        return cmd_seller(argument, deps)
    if command == "/stats":
        if not bucket.take(chat_id):
            return "Slow down. Try again in a minute."
        return cmd_stats(deps)
    if text.startswith("/"):
        return f"Unknown command {command}.\n\n" + HELP

    lowered = text.lower()
    if any(term in lowered for term in ON_TOPIC):
        return (
            "I can answer that only with a call I make in this turn, and free text has no call behind it. "
            "Use /stats for the live numbers, /case for a verdict, /seller for a record, /promise to lint a promise, "
            "or read the skill: github.com/meitipro/recourse-skill"
        )
    return REDIRECT
