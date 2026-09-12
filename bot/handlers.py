"""
What the bot says. Pure functions over injected dependencies, so every reply
can be tested without Telegram, a chain or a model.

    respond(update, me, ctx) -> Outgoing | None     one Telegram update
    handle(chat_id, text, conversations, bucket, deps, threads, chat) -> reply

The commands format the reads in bot/records.py. Free text goes to
bot/agent.py, where a model chooses among the same five reads and answers from
what they returned. Every number in a reply comes from a call made in that
turn: the chain, the linter, the committed evaluation files. Nothing is
recalled from memory, and when a call fails the reply says what could not be
read rather than filling the gap.
"""

from __future__ import annotations

import dataclasses
import re
import typing

from bot.agent import ChatUnavailable, ReadContext, converse, mask_quantities
from bot.guard import COMPROMISED, looks_like_secret
from bot.records import (  # noqa: F401 - citation, to_pid and the names stay importable from here
    STATUS,
    VERDICT,
    Deps,
    Unavailable,
    case_record,
    citation,
    seller_record,
    stats_record,
    to_pid,
)

HELP = """Recourse, read only. Nothing here holds a key or moves money.

Ask in plain words: whether a promise is any good, what happened with a case, how often it rules for the seller, whether a response would pass. Or use a command:

/promise <text>   is this promise judgeable? The linter, in chat.
/check            a dry run of the judge: the promise, then the response body.
/case <id>        one adjudicated case, by p-000043 or RC-2026-0043.
/seller <addr>    a seller's public record.
/stats            live counts from chain, and both evaluation figures.
/help             this.

Paying, disputing and withdrawing are done from your own wallet. The exact calls are in the skill: github.com/meitipro/recourse-skill"""

NO_MODEL = (
    "Free text needs a model to choose which read to make, and this bot has none right now: {why}.\n"
    "The commands read directly: /promise <text>, /check, /case <id>, /seller <addr>, /stats. /help explains each."
)


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
    try:
        record = case_record(pid, deps)
    except Unavailable as error:
        return f"Could not read {pid} from the chain: {error}"
    if not record["disputed"]:
        return f"{pid} was never disputed, so there is no case to read. Status: {record['status']}. Window ends {record['window_ends']}."
    if not record["decided"]:
        return f"{pid} is disputed and judgment is still running: no case row yet. Dispute ends {record['dispute_ends']}."
    return "\n".join([
        f"{record['citation']}  ({pid})",
        f"verdict   {record['verdict']}",
        f"status    {record['status']}" + ("  (money moved)" if record["money"] == "moved" else "  (verdict written, money moves on finalization)"),
        f"reason    {record['reason']}",
        "",
        f"promise   {record['promise']}",
        f"request   {record['request']}",
        f"response  {record['response']}",
        f"timing    {record['timing']}",
        "",
        f"amount {record['amount']}, bond {record['bond']}, paid {record['paid_at']}, decided {record['decided_at']}",
        f"{record['explorer']}",
    ])


def cmd_seller(argument: str, deps: Deps) -> str:
    address = argument.strip()
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", address):
        return "Send an address after the command: /seller 0x965c98389197055CFb3FD8b1E3e9a11AE6d40C99"
    try:
        record = seller_record(address, deps)
    except Unavailable as error:
        return f"Could not read that seller: {error}"
    lines = [
        f"seller     {record['address']}",
        f"promise    {record['promise']}",
        f"active     {'yes' if record['active'] else 'no'}    judgeable {'yes' if record['judgeable'] else 'NO, payments refused'}",
        f"payments   {record['payments_taken']} taken, {record['live']} live, {record['disputes_upheld_against']} disputes upheld against it",
        f"registered {record['registered_at']}",
    ]
    if record["gate_said"]:
        lines.append(f"gate said  {record['gate_said']}")
    return "\n".join(lines)


def cmd_stats(deps: Deps) -> str:
    record = stats_record(deps)
    lines = [
        f"{record['network']}, frozen contracts (the same bytes on every network)",
        f"escrow  {record['escrow']}",
        f"dispute {record['dispute']}",
        "",
    ]
    live = record.get("live")
    if live:
        lines.append(f"payments {live['payments']}   cases {live['cases']}   held {live['held']}   bond {live['bond']}   window {live['window_seconds']}s")
    else:
        lines.append(f"live counts could not be read: {record['live_error']}")
    lines.append("")
    evaluation = record.get("evaluation")
    if evaluation:
        tuned, held = evaluation["tuned"], evaluation["held_out"]
        lines.append("evaluation, both figures, always together:")
        lines.append(f"  {tuned['accuracy']}/{tuned['n']} on the set the question was narrowed against")
        lines.append(f"  {held['accuracy']}/{held['n']} on the held out set, committed before it could be run and never tuned against")
        lines.append("The pattern both agree on: a promise that does not settle the question gets answered on its plain words.")
    else:
        lines.append(f"evaluation figures could not be read: {record['evaluation_error']}")
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
            "DRY RUN, no money, no consensus. One model, both presentation orders, the deployed contract's own judge().",
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


def slow_down(bucket, chat_id: int, cost: float) -> str:
    """A refusal that says what the limit protects and when it lifts."""
    wait = bucket.wait_seconds(chat_id, cost)
    if cost >= bucket.expensive:
        return (
            "Slow down: this chat has used its share of model calls for now. The limit protects the model "
            "budget that answers every chat, so one loop cannot spend it for everyone. /stats, /case and "
            f"/seller only read the chain and cost less. Try again in about {wait} seconds."
        )
    return (
        "Slow down: this chat is reading faster than the shared studionet node allows. The limit protects "
        f"that node, which rate limits every reader at once. Try again in about {wait} seconds."
    )


# --- one message ------------------------------------------------------------


def handle(
    chat_id: int,
    text: str,
    conversations,
    bucket,
    deps: Deps,
    threads=None,
    chat=None,
    trace: list | None = None,
) -> str:
    """One message in, one reply out. The secret check runs before anything."""
    text = (text or "").strip()
    if not text:
        return HELP

    what = looks_like_secret(text)
    if what:
        # Nothing of this message is kept anywhere, the thread included.
        conversations.clear(chat_id)
        if threads is not None:
            threads.clear(chat_id)
        return COMPROMISED.format(what=what)

    reply = _reply(chat_id, text, conversations, bucket, deps, threads, chat, trace)
    if threads is not None:
        threads.add(chat_id, text, mask_quantities(reply))
    return reply


def _reply(chat_id: int, text: str, conversations, bucket, deps: Deps, threads, chat, trace) -> str:
    state = conversations.get(chat_id) or {}
    command, _, argument = text.partition(" ")
    command = command.lower().split("@")[0]

    # A conversation in progress takes plain text as its next step.
    if state.get("step") == "promise" and not text.startswith("/"):
        conversations.set(chat_id, {"step": "response", "promise": text})
        return "Promise noted. Now send the response body, as the endpoint returned it."
    if state.get("step") == "response" and not text.startswith("/"):
        if not bucket.take(chat_id, cost=bucket.expensive):
            return slow_down(bucket, chat_id, bucket.expensive)
        return cmd_check(chat_id, text, conversations, deps)

    if command in ("/start", "/help"):
        return HELP
    if command == "/promise":
        if not bucket.take(chat_id, cost=bucket.expensive):
            return slow_down(bucket, chat_id, bucket.expensive)
        return cmd_promise(argument, deps)
    if command == "/check":
        if not bucket.take(chat_id):
            return slow_down(bucket, chat_id, 1)
        return cmd_check(chat_id, argument, conversations, deps)
    if command == "/case":
        if not bucket.take(chat_id):
            return slow_down(bucket, chat_id, 1)
        return cmd_case(argument, deps)
    if command == "/seller":
        if not bucket.take(chat_id):
            return slow_down(bucket, chat_id, 1)
        return cmd_seller(argument, deps)
    if command == "/stats":
        if not bucket.take(chat_id):
            return slow_down(bucket, chat_id, 1)
        return cmd_stats(deps)
    if text.startswith("/"):
        return f"Unknown command {command}.\n\n" + HELP
    return _free_text(chat_id, text, conversations, bucket, deps, threads, chat, trace)


def _free_text(chat_id: int, text: str, conversations, bucket, deps: Deps, threads, chat, trace) -> str:
    """
    Free text goes to a model that chooses among the five reads. Every turn
    spends at least one model call, so it costs what /check's model step costs.
    Whether a model is there is asked first, so a bot without one does not
    charge for saying so.
    """
    if chat is None:
        return NO_MODEL.format(why="no model is configured")
    ready, why = chat.ready()
    if not ready:
        return NO_MODEL.format(why=why)
    if not bucket.take(chat_id, cost=bucket.expensive):
        return slow_down(bucket, chat_id, bucket.expensive)
    history = threads.history(chat_id) if threads is not None else []
    context = ReadContext(deps=deps, bucket=bucket, chat_id=chat_id, conversations=conversations, trace=trace)
    try:
        return converse(text, history, context, chat)
    except ChatUnavailable as error:
        return NO_MODEL.format(why=error)


# --- one update -------------------------------------------------------------


@dataclasses.dataclass
class Context:
    """Everything a reply can touch, all of it in this process's memory."""

    conversations: typing.Any
    bucket: typing.Any
    deps: Deps
    threads: typing.Any
    seen: typing.Any
    chat: typing.Any = None


@dataclasses.dataclass
class Outgoing:
    chat_id: int
    text: str
    reply_to: int | None = None
    thread_id: int | None = None


def addressed(message: dict, me: dict) -> str | None:
    """
    The text to answer, or None when the message is not for this bot.

    In a private chat every message is. In a group only one that names the bot,
    by @username, a text mention or /command@username, or that replies to one
    of its messages. A bare /command in a group is left alone: several bots can
    share a command name, and the rule is to answer only when addressed.
    """
    text = message.get("text")
    if not isinstance(text, str):
        return None
    if (message.get("chat") or {}).get("type") == "private":
        return text
    my_id = me.get("id")
    username = me.get("username") or ""
    mention = re.compile(r"@" + re.escape(username) + r"\b", re.I) if username else None
    named = bool(mention and mention.search(text))
    for entity in message.get("entities") or []:
        if entity.get("type") == "text_mention" and my_id is not None and (entity.get("user") or {}).get("id") == my_id:
            named = True
    replied = my_id is not None and ((message.get("reply_to_message") or {}).get("from") or {}).get("id") == my_id
    if not (named or replied):
        return None
    return mention.sub("", text).strip() if mention else text.strip()


def respond(update: dict, me: dict, ctx: Context, trace: list | None = None) -> Outgoing | None:
    """
    One Telegram update in, at most one reply out.

    It answers only a message it was sent: nothing here starts a conversation.
    A message already answered is never answered again, even if Telegram
    delivers it twice, and a message from another bot is ignored so two bots
    cannot talk each other into a loop. In a group the reply is attached to
    the message it answers, in the same topic.
    """
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id, message_id = chat.get("id"), message.get("message_id")
    if chat_id is None or message_id is None or (message.get("from") or {}).get("is_bot"):
        return None
    text = addressed(message, me)
    if text is None or not ctx.seen.first(chat_id, message_id):
        return None
    reply = handle(chat_id, text, ctx.conversations, ctx.bucket, ctx.deps, threads=ctx.threads, chat=ctx.chat, trace=trace)
    group = chat.get("type") != "private"
    return Outgoing(chat_id=chat_id, text=reply, reply_to=message_id if group else None, thread_id=message.get("message_thread_id"))
