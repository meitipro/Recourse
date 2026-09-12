"""
The bot, without Telegram, a chain or a model.

The boundary is tested as a property of the process, not a policy: the client
has no account, the source names no write method, a secret gets one reply and
nothing else is read. The commands are tested through injected dependencies
that record what they were asked, and free text through a model double that
plays back its turns and records everything it was handed.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from types import SimpleNamespace

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from bot.agent import SYSTEM, TOOLS, ClaudeChat, NoChat, Turn, _turn, mask_quantities, unsourced  # noqa: E402
from bot.guard import looks_like_secret  # noqa: E402
from bot.handlers import Context, Unavailable, addressed, citation, handle, respond, to_pid  # noqa: E402
from bot.state import Bucket, Conversations, Seen, Threads  # noqa: E402


class FakeDeps:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.payment = {
            "pid": "p-000003", "buyer": "0xb", "seller": "0xs", "amount": str(4 * 10**18), "bond": str(10**18),
            "request": "GET /quote?pair=ETH-USD", "response": '{"pair":"ETH-USD"}', "response_sig": "", "recorded_by": "0xs",
            "created_at": 1788639512, "responded_at": 1788639523, "window_ends": 1788639812, "dispute_ends": 1788643131,
            "status": 3, "verdict": 2,
        }
        self.case = {
            "pid": "p-000003", "promise": "P", "request": "R", "response": "X", "timing": "T",
            "verdict": 2, "verdict_name": "not_honored", "reason": "nine hours old", "opened_at": 1788639536, "decided_at": 1788639536,
        }
        self.lint_result = {"judgeable": False, "reason": "no measurable term here", "failed_check": "no measurable term", "suggestion": None, "stage": 1}
        self.dry = {"verdict": "not_honored", "reason": "stale", "agreed": "yes"}
        self.fail_chain = False
        self.no_case = False

    def addresses(self):
        return {"escrow": "0xESCROW", "dispute": "0xDISPUTE", "explorer": "https://explorer"}

    def read_json(self, contract, method, args):
        self.calls.append(("read", contract, method, tuple(args)))
        if self.fail_chain:
            raise Unavailable("rate limited")
        if method == "get_payment":
            return dict(self.payment)
        if method == "get_case":
            if self.no_case:
                raise Unavailable("case not found")
            return dict(self.case)
        if method == "get_seller":
            return {"address": args[0], "promise": "P", "active": True, "judgeable": True, "registered_at": 1, "total": 7, "upheld": 2, "live": 3, "reviewed": ""}
        if method == "gate_reason":
            return ""
        if method == "stats" and contract == "0xESCROW":
            return {"payments": 7, "held": str(9 * 10**18), "bond_amount": str(10**18), "window_seconds": 300}
        if method == "stats":
            return {"cases": 3}
        if method == "recent_verdicts":
            rows = [
                {"pid": "p-000003", "verdict": 2, "verdict_name": "not_honored"},
                {"pid": "p-000002", "verdict": 1, "verdict_name": "honored"},
                {"pid": "p-000001", "verdict": 3, "verdict_name": "unclear"},
            ]
            return rows[: args[0]]
        raise AssertionError(method)

    def lint(self, promise):
        self.calls.append(("lint", promise))
        return dict(self.lint_result)

    def dry_run(self, promise, response):
        self.calls.append(("dry_run", promise, response))
        return dict(self.dry)

    def evaluation(self):
        self.calls.append(("evaluation",))
        return {"tuned": {"accuracy": 17, "n": 18, "stability": 17}, "held_out": {"accuracy": 1, "n": 3, "stability": 2}}


def world():
    return Conversations(), Bucket(), FakeDeps()


# --- the boundary -----------------------------------------------------------


def test_the_chain_reader_is_a_throwaway_that_holds_nothing():
    # The SDK needs a sender address for a read, so "no account" was a reader
    # that could not read. What can be asserted instead: the account is not one
    # of the demo's three, it is different on every start, and nothing in bot/
    # can hand it to a write (the scan below).
    from bot.main import reader

    first, second = reader(), reader()
    assert first.account is not None
    assert first.account.address != second.account.address
    keys = ROOT / ".accounts.json"
    if keys.exists():
        from genlayer_py import create_account

        demo = {create_account(k).address.lower() for k in json.loads(keys.read_text(encoding="utf-8")).values()}
        assert first.account.address.lower() not in demo


def test_no_file_in_the_bot_names_a_write():
    # The chain's write methods and anything that would need a key. Not the
    # word "withdrawing" in help text, and not sys.stderr.write: the first
    # version banned both and failed on its own prose.
    banned = (
        "write_contract", "deploy_contract", "send_transaction", "chain.write(", ".write(contract",
        "open_dispute(", "register_seller(", "record_response(", "reclaim(", "withdraw(",
        "private_key", "sign_message", "load_accounts(",
    )
    for path in (ROOT / "bot").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        # Strip docstrings and comments: the README-style prose in module
        # docstrings legitimately names the things it promises not to do.
        code = re.sub(r'"""[\s\S]*?"""', "", source)
        code = re.sub(r"^\s*#.*$", "", code, flags=re.M)
        for word in banned:
            assert word not in code, f"{path.name} mentions {word}"
        # A bare create_account() is a fresh throwaway key and is how the
        # reader exists at all. create_account(<anything>) imports a key and
        # is banned.
        assert not re.search(r"create_account\((?!\))", code), f"{path.name} imports a key"


def test_a_private_key_gets_one_reply_and_nothing_else_is_read():
    conversations, bucket, deps = world()
    key = "0x" + "ab" * 32
    reply = handle(1, f"/stats please also look at {key}", conversations, bucket, deps)
    assert "compromised" in reply and "Rotate" in reply
    assert key not in reply and "ab" * 32 not in reply
    assert deps.calls == [], "nothing else in the message was processed"


def test_a_seed_phrase_is_caught_without_the_hex_shape():
    phrase = "abandon ability able about above absent absorb abstract absurd abuse access accident"
    assert looks_like_secret(f"my phrase is {phrase} thanks") == "seed phrase"
    assert looks_like_secret("the dispute was about an absent response and access to data") is None
    conversations, bucket, deps = world()
    reply = handle(1, phrase, conversations, bucket, deps)
    assert "seed phrase" in reply and "abandon" not in reply


def test_a_secret_clears_a_conversation_in_progress():
    conversations, bucket, deps = world()
    handle(1, "/check", conversations, bucket, deps)
    handle(1, "0x" + "cd" * 32, conversations, bucket, deps)
    assert conversations.get(1) is None


class RecordingThreads(Threads):
    """Thread memory that keeps a copy of every write, so a test can see what ever entered it."""

    def __init__(self) -> None:
        super().__init__()
        self.writes: list[tuple[int, str, str]] = []

    def add(self, chat_id: int, said: str, replied: str) -> None:
        self.writes.append((chat_id, said, replied))
        super().add(chat_id, said, replied)


def test_a_secret_never_enters_the_thread_memory_or_reaches_a_model():
    """
    The boundary keeps six messages and names one exception: a message that
    looks like a private key or a seed phrase is refused in the turn it
    arrives and never enters that memory. An empty thread afterwards cannot
    show it, because a guard that ran after the append and then cleared would
    leave the same empty thread. So every write to the memory is recorded,
    and so is every request to the model on either side of the secret.
    """
    key = "0x" + "ab" * 32
    phrase = "abandon ability able about above absent absorb abstract absurd abuse access accident"
    for secret, hidden in ((f"is this one mine {key}", key[2:]), (f"my phrase is {phrase}", phrase)):
        conversations, bucket, deps = world()
        threads = RecordingThreads()
        chat = ScriptedChat(say("A read only bot for Recourse."), say("Nothing before that is remembered here."))
        ctx = Context(conversations=conversations, bucket=bucket, deps=deps, threads=threads, seen=Seen(), chat=chat)
        respond({"update_id": 1, "message": group("@RecourseBot what is this", message_id=1)}, ME, ctx)
        assert len(threads.history(-100)) == 2
        refused = respond({"update_id": 2, "message": group(f"@RecourseBot {secret}", message_id=2)}, ME, ctx)
        assert "compromised" in refused.text and hidden not in refused.text
        assert not any(hidden in said or hidden in replied for _, said, replied in threads.writes), "the secret entered the thread memory"
        assert len(chat.requests) == 1, "the refused turn asked no model"
        assert threads.history(-100) == [], "the chat's memory went with it"
        respond({"update_id": 3, "message": group("@RecourseBot and the one before it", message_id=3)}, ME, ctx)
        assert hidden not in json.dumps(chat.requests, default=str), "the secret reached a model"
        assert "what is this" not in json.dumps(chat.requests[1]["messages"], default=str), "what came before it was cleared"
        assert deps.calls == []


class FakeTelegram:
    """Stands where bot/telegram.py's Telegram would: one batch of updates, and a log to read."""

    def __init__(self, *updates) -> None:
        self.batch = list(updates)
        self.sent: list[tuple[int, str]] = []
        self.logged: list[str] = []

    def updates(self):
        batch, self.batch = self.batch, []
        return batch

    def send(self, chat_id, text, reply_to=None, thread_id=None):
        self.sent.append((chat_id, text))

    def log(self, message):
        self.logged.append(message)


def test_no_message_text_reaches_the_log_even_when_a_turn_fails():
    """
    The boundary says no message text is logged. An answered update is logged
    by its ids. A failed turn is where text could leak: an error raised while
    answering can carry what was typed, and the loop used to log the first 120
    characters of any error. It logs the error's name now, and only the
    transport's own errors, which carry Telegram's reason or the network's,
    keep their message.
    """
    from bot.main import failure, serve
    from bot.telegram import TelegramError

    typed = "Prices from three venues, never older than five seconds."

    class Breaking(FakeDeps):
        def lint(self, promise):
            raise RuntimeError(f"the linter choked on {promise}")

    conversations, bucket, _ = world()
    ctx = Context(conversations=conversations, bucket=bucket, deps=Breaking(), threads=Threads(), seen=Seen())
    private = {"chat": {"id": 11, "type": "private"}, "from": {"id": 11}}
    telegram = FakeTelegram(
        {"update_id": 1, "message": {**private, "message_id": 1, "text": "/stats"}},
        {"update_id": 2, "message": {**private, "message_id": 2, "text": f"/promise {typed}"}},
    )
    serve(telegram, ME, ctx, pause=lambda seconds: None)
    assert telegram.logged == ["update 1 chat 11 answered", "loop error: RuntimeError"]
    assert len(telegram.sent) == 1
    assert failure(ValueError(typed)) == "ValueError"
    assert failure(TelegramError("telegram sendMessage: Bad Request: chat not found")).endswith("chat not found")
    assert failure(TimeoutError("The read operation timed out")).endswith("timed out")


def test_nothing_in_the_bot_writes_a_file():
    """
    The boundary says nothing is written to disk and nothing survives a
    restart. The state is bot/state.py's dictionaries, and this holds all of
    bot/ to that by naming the ways Python writes a file.
    """
    banned = (
        r"(?<![\w.])open\(", r"\.write_text\(", r"\.write_bytes\(", r"\bjson\.dump\(", r"\bpickle\b",
        r"\bshelve\b", r"\bsqlite3\b", r"FileHandler", r"\btempfile\b", r"\.mkdir\(", r"\bmakedirs\(",
        r"\bos\.write\(", r"\bshutil\.(copy|move)", r"\.touch\(",
    )
    for path in (ROOT / "bot").glob("*.py"):
        code = re.sub(r'"""[\s\S]*?"""', "", path.read_text(encoding="utf-8"))
        code = re.sub(r"^\s*#.*$", "", code, flags=re.M)
        for pattern in banned:
            assert not re.search(pattern, code), f"{path.name} matches {pattern}, a way to write a file"


# --- commands ---------------------------------------------------------------


def test_promise_is_the_linter_in_chat():
    conversations, bucket, deps = world()
    reply = handle(1, "/promise Accurate market data.", conversations, bucket, deps)
    assert ("lint", "Accurate market data.") in deps.calls
    assert "NOT JUDGEABLE" in reply and "no measurable term" in reply and "no model was asked" in reply
    assert "stored" in reply


def test_promise_offers_the_rewrite_when_the_gate_said_no():
    conversations, bucket, deps = world()
    deps.lint_result = {"judgeable": False, "reason": "quality only", "failed_check": None, "suggestion": "Returns the spot price within ten seconds.", "stage": 2}
    reply = handle(1, "/promise Great prices always", conversations, bucket, deps)
    assert "Returns the spot price within ten seconds." in reply
    assert "dry run" in reply


def test_check_takes_two_steps_and_labels_the_dry_run():
    conversations, bucket, deps = world()
    first = handle(7, "/check", conversations, bucket, deps)
    assert "Step 1" in first
    second = handle(7, "Prices within five seconds.", conversations, bucket, deps)
    assert "response body" in second
    third = handle(7, '{"price": 1, "ts": "old"}', conversations, bucket, deps)
    assert third.startswith("DRY RUN")
    assert "not_honored" in third and "no money, no consensus" in third
    assert ("dry_run", "Prices within five seconds.", '{"price": 1, "ts": "old"}') in deps.calls
    assert conversations.get(7) is None, "the conversation is cleared once answered"


def test_case_accepts_a_citation_and_prints_one():
    conversations, bucket, deps = world()
    reply = handle(1, "/case RC-2026-0003", conversations, bucket, deps)
    assert ("read", "0xESCROW", "get_payment", ("p-000003",)) in deps.calls
    assert reply.startswith("RC-2026-0003  (p-000003)")
    assert "not_honored" in reply and "nine hours old" in reply and "money moved" in reply


def test_case_says_when_there_is_no_case():
    conversations, bucket, deps = world()
    deps.payment["status"] = 0
    reply = handle(1, "/case 3", conversations, bucket, deps)
    assert "never disputed" in reply
    assert not any(call[2] == "get_case" for call in deps.calls if call[0] == "read")


def test_stats_shows_both_evaluation_figures_together():
    conversations, bucket, deps = world()
    reply = handle(1, "/stats", conversations, bucket, deps)
    assert "17/18" in reply and "1/3" in reply
    assert "always together" in reply
    assert "payments 7" in reply and "cases 3" in reply


def test_a_failed_chain_read_is_said_not_guessed():
    conversations, bucket, deps = world()
    deps.fail_chain = True
    reply = handle(1, "/stats", conversations, bucket, deps)
    assert "could not be read" in reply
    assert "payments" not in reply.split("live counts")[1].split("\n")[0]


def test_free_text_off_topic_redirects_and_on_topic_points_at_a_command():
    conversations, bucket, deps = world()
    assert "/stats" in handle(1, "what is the weather in Paris", conversations, bucket, deps)
    on_topic = handle(1, "how many disputes has recourse settled?", conversations, bucket, deps)
    assert "/stats" in on_topic
    assert not re.search(r"\b\d+/\d+\b", on_topic), "no number is stated without a call"
    assert deps.calls == []


# --- rate limit and state ---------------------------------------------------


def test_the_bucket_stops_a_loop_on_promise():
    conversations, bucket, deps = world()
    replies = [handle(1, "/promise Accurate market data.", conversations, bucket, deps) for _ in range(6)]
    assert sum("Slow down" in reply for reply in replies) >= 2
    # Another chat is unaffected.
    assert "Slow down" not in handle(2, "/promise Accurate market data.", conversations, bucket, deps)


def test_state_expires_after_ten_minutes():
    now = [1000.0]
    conversations = Conversations(clock=lambda: now[0])
    conversations.set(1, {"step": "promise"})
    now[0] += 599
    assert conversations.get(1) == {"step": "promise"}
    now[0] += 2
    assert conversations.get(1) is None


def test_ids_and_citations_round_trip():
    assert to_pid("RC-2026-0043") == "p-000043"
    assert to_pid("p-43") == "p-000043"
    assert to_pid("43") == "p-000043"
    assert citation("p-000043", 1788639536) == "RC-2026-0043"
    with pytest.raises(ValueError):
        to_pid("forty three")


# --- free text: a model that can only read ----------------------------------

FIVE = ["lint", "judge_dry_run", "get_case", "get_seller", "get_stats"]


def ask(name, **arguments):
    """A model turn that makes one read."""
    call = f"call_{name}"
    return Turn(stop="tool_use", content=[{"type": "tool_use", "id": call, "name": name, "input": arguments}], calls=[(call, name, arguments)])


def say(text):
    """A model turn that answers."""
    return Turn(stop="end_turn", content=[{"type": "text", "text": text}], text=text)


class ScriptedChat:
    """A model double: plays its turns back in order and records every request."""

    name = "scripted"

    def __init__(self, *turns):
        self.turns = list(turns)
        self.requests: list[dict] = []

    def ready(self):
        return True, None

    def respond(self, system, messages, tools, final):
        self.requests.append({"system": system, "messages": list(messages), "tools": tools, "final": final})
        return self.turns.pop(0)


class FakeClient:
    """Stands where anthropic.Anthropic() would, and records each request."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.sent: list[dict] = []
        outer = self

        class _Messages:
            def create(self, **kwargs):
                outer.sent.append(kwargs)
                return outer.responses.pop(0)

        self.beta = SimpleNamespace(messages=_Messages())


def text_response(text):
    return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)])


def test_the_model_is_handed_the_five_reads_and_nothing_else():
    """
    The one boundary free text adds. A model that invents a write tool has
    nothing to call: the tool list is five reads, every request carries exactly
    that list, and any other name reaches no dependency at all.
    """
    assert [tool["name"] for tool in TOOLS] == FIVE
    for tool in TOOLS:
        assert set(tool) <= {"name", "description", "input_schema", "strict"}, f"{tool['name']} is not a plain custom tool"
    chat = ScriptedChat(ask("open_dispute", pid="p-000003"), say("There is no such read. This bot cannot dispute anything."))
    conversations, bucket, deps = world()
    reply = handle(1, "dispute p-000003 for me", conversations, bucket, deps, threads=Threads(), chat=chat)
    assert all(request["tools"] is TOOLS for request in chat.requests)
    assert deps.calls == [], "the invented tool reached nothing"
    result = chat.requests[1]["messages"][-1]["content"][0]
    assert result["is_error"] and "no read called open_dispute" in result["content"]
    assert "cannot dispute" in reply
    # And the request the SDK sends carries that list and nothing more.
    client = FakeClient(text_response("ok"))
    ClaudeChat(client=client).respond(SYSTEM, [{"role": "user", "content": "hi"}], TOOLS, final=False)
    assert client.sent[0]["tools"] is TOOLS


def test_the_sdk_request_is_the_configured_model_at_low_effort_with_the_refusal_fallback():
    client = FakeClient(text_response("ok"), text_response("ok"))
    chat = ClaudeChat(client=client)
    assert chat.ready() == (True, None)
    chat.respond(SYSTEM, [{"role": "user", "content": "hi"}], TOOLS, final=False)
    chat.respond(SYSTEM, [{"role": "user", "content": "hi"}], TOOLS, final=True)
    first, last = client.sent
    assert first["model"] == chat.model
    assert first["thinking"] == {"type": "adaptive"} and first["output_config"] == {"effort": "low"}
    assert first["fallbacks"] == "default" and first["betas"] == ["server-side-fallback-2026-07-01"]
    assert first["system"] == SYSTEM
    assert first["tool_choice"] == {"type": "auto"} and last["tool_choice"] == {"type": "none"}


def test_after_a_fallback_only_the_finishing_model_is_echoed():
    blocks = [
        SimpleNamespace(type="thinking", thinking=""),
        SimpleNamespace(type="tool_use", id="declined", name="get_stats", input={}),
        SimpleNamespace(type="fallback"),
        SimpleNamespace(type="thinking", thinking=""),
        SimpleNamespace(type="tool_use", id="kept", name="get_case", input={"id": "p-000003"}),
    ]
    turn = _turn("tool_use", blocks)
    assert [block.type for block in turn.content] == ["thinking", "tool_use"]
    assert turn.calls == [("kept", "get_case", {"id": "p-000003"})]


def test_free_text_is_answered_from_a_read_made_that_turn():
    chat = ScriptedChat(ask("get_case", id="RC-2026-0003"), say("RC-2026-0003 ruled not_honored: nine hours old. The money moved."))
    conversations, bucket, deps = world()
    reply = handle(1, "what happened with RC-2026-0003", conversations, bucket, deps, threads=Threads(), chat=chat)
    assert reply == "RC-2026-0003 ruled not_honored: nine hours old. The money moved."
    assert ("read", "0xESCROW", "get_payment", ("p-000003",)) in deps.calls
    result = chat.requests[1]["messages"][-1]["content"][0]
    assert result["tool_use_id"] == "call_get_case" and '"verdict": "not_honored"' in result["content"]


def test_a_number_no_read_returned_is_never_stated():
    chat = ScriptedChat(say("Recourse has settled 42 disputes."), say("Still 42, from memory."))
    conversations, bucket, deps = world()
    reply = handle(1, "how many disputes has it settled", conversations, bucket, deps, threads=Threads(), chat=chat)
    assert "42" not in reply and "/stats" in reply
    assert "42" in chat.requests[1]["messages"][-1]["content"], "the model was told which number had no read behind it"
    assert unsourced("payments 7, bond 1.00 GEN", [json.dumps({"payments": 7, "bond": "1.00 GEN"})], "") == []
    assert unsourced("payments 8", [json.dumps({"payments": 7})], "") == ["8"]
    assert unsourced("RC-2026-0004 is next", [json.dumps({"citation": "RC-2026-0003"})], "") == ["RC-2026-0004"]


def test_three_reads_at_most_then_it_answers_with_what_it_has():
    chat = ScriptedChat(
        ask("get_stats"), ask("get_case", id="p-000003"), ask("get_seller", address="0x" + "a" * 40),
        say("That is what the reads returned."),
    )
    conversations, _, deps = world()
    reply = handle(1, "tell me all of it", conversations, Bucket(capacity=100), deps, threads=Threads(), chat=chat)
    assert [request["final"] for request in chat.requests] == [False, False, False, True]
    assert reply == "That is what the reads returned."
    # Four reads asked for at once: three run, the fourth gets an error.
    many = Turn(
        stop="tool_use",
        content=[{"type": "tool_use", "id": f"c{i}", "name": "get_stats", "input": {}} for i in range(4)],
        calls=[(f"c{i}", "get_stats", {}) for i in range(4)],
    )
    chat = ScriptedChat(many, say("Answered from the reads that ran."))
    handle(2, "the stats, four times over", conversations, Bucket(capacity=100), deps, threads=Threads(), chat=chat)
    results = chat.requests[1]["messages"][-1]["content"]
    assert [result.get("is_error", False) for result in results] == [False, False, False, True]
    assert chat.requests[1]["final"] is True


def test_the_model_is_given_no_number_to_draw_on():
    assert not re.search(r"\d", SYSTEM.replace("x402", "")), "the system prompt carries a number"
    assert not re.search(r"\d", json.dumps(TOOLS).replace("x402", "")), "a tool definition carries a number"
    assert "the missing dispute right" in SYSTEM, "what Recourse is comes from the skill's reference file"
    remembered = mask_quantities("RC-2026-0003 ruled not_honored, 4.00 GEN back after 83 seconds, over x402.")
    assert "RC-2026-0003" in remembered and "x402" in remembered
    assert "4.00" not in remembered and "83" not in remembered and remembered.count("[n]") == 2


def test_an_undecided_case_gives_the_model_nothing_to_speculate_from():
    conversations, bucket, deps = world()
    deps.payment["status"] = 2
    deps.no_case = True
    chat = ScriptedChat(ask("get_case", id="p-000003"), say("p-000003 is still being judged."))
    reply = handle(1, "is p-000003 decided", conversations, bucket, deps, threads=Threads(), chat=chat)
    result = json.loads(chat.requests[1]["messages"][-1]["content"][0]["content"])
    assert result["decided"] is False and "verdict" not in result and "reason" not in result
    assert reply == "p-000003 is still being judged."


def test_thread_memory_is_the_last_six_messages_for_ten_minutes():
    now = [1000.0]
    threads = Threads(clock=lambda: now[0])
    for n in range(4):
        threads.add(1, f"question {n}", f"answer {n}")
    history = threads.history(1)
    assert len(history) == 6 and history[0] == {"role": "user", "content": "question 1"}
    now[0] += 599
    assert len(threads.history(1)) == 6
    now[0] += 2
    assert threads.history(1) == []
    # A reply is remembered with its quantities masked, and a secret clears it.
    conversations, bucket, deps = world()
    threads = Threads()
    handle(1, "/stats", conversations, bucket, deps, threads=threads)
    remembered = threads.history(1)[1]["content"]
    assert "payments [n]" in remembered and "payments 7" not in remembered
    handle(1, "0x" + "ef" * 32, conversations, bucket, deps, threads=threads)
    assert threads.history(1) == [], "a secret clears the thread too"


def test_six_lines_unless_asked_to_expand():
    long = "\n".join(f"line {word}" for word in ("one", "two", "three", "four", "five", "six", "seven", "eight"))
    chat = ScriptedChat(say(long), say(long))
    conversations, bucket, deps = world()
    short = handle(1, "tell me about it", conversations, bucket, deps, threads=Threads(), chat=chat)
    assert len(short.splitlines()) == 6 and short.endswith("Ask me to expand for the rest.")
    full = handle(1, "expand on that", conversations, bucket, deps, threads=Threads(), chat=chat)
    assert len(full.splitlines()) == 8


def test_would_this_response_pass_starts_the_two_step_dry_run():
    chat = ScriptedChat(ask("judge_dry_run", promise="", response=""), say("Step 1 of 2: send the seller's promise."))
    conversations, bucket, deps = world()
    threads = Threads()
    assert handle(3, "would this response pass", conversations, bucket, deps, threads=threads, chat=chat) == "Step 1 of 2: send the seller's promise."
    assert conversations.get(3) == {"step": "promise"}
    assert "response body" in handle(3, "Prices within five seconds.", conversations, bucket, deps, threads=threads, chat=chat)
    third = handle(3, '{"price": 1, "ts": "old"}', conversations, bucket, deps, threads=threads, chat=chat)
    assert third.startswith("DRY RUN")
    assert ("dry_run", "Prices within five seconds.", '{"price": 1, "ts": "old"}') in deps.calls


def test_free_text_costs_what_check_costs_and_the_refusal_says_what_it_protects():
    conversations, deps, threads = Conversations(), FakeDeps(), Threads()
    bucket = Bucket(capacity=12, per_minute=0.001)
    chat = ScriptedChat(say("Ask about a case or a seller."), say("Ask about a case or a seller."))
    assert "Ask about" in handle(1, "hello", conversations, bucket, deps, threads=threads, chat=chat)
    assert "Ask about" in handle(1, "hello again", conversations, bucket, deps, threads=threads, chat=chat)
    refused = handle(1, "and again", conversations, bucket, deps, threads=threads, chat=chat)
    assert refused.startswith("Slow down") and "protects the model budget" in refused and "seconds" in refused
    assert len(chat.requests) == 2, "the refused turn spent no model call"
    # A dry run inside a free text turn costs what /check's model step costs, on top.
    bucket = Bucket(capacity=10, per_minute=0.001)
    chat = ScriptedChat(ask("judge_dry_run", promise="Prices within five seconds.", response='{"ts": "old"}'), say("DRY RUN: not_honored, stale."))
    handle(2, "would this pass", conversations, bucket, deps, threads=threads, chat=chat)
    assert ("dry_run", "Prices within five seconds.", '{"ts": "old"}') in deps.calls
    assert not bucket.take(2, cost=1), "five for the turn and five for the dry run"


def test_without_a_model_free_text_says_so_and_names_the_commands():
    conversations, bucket, deps = world()
    reply = handle(1, "how often does it rule for the seller", conversations, bucket, deps, threads=Threads(), chat=NoChat())
    assert "turned off" in reply and "/stats" in reply and "/case" in reply
    assert deps.calls == []
    assert bucket.take(1, cost=bucket.capacity), "saying so cost nothing"


# --- groups, and one reply per message ----------------------------------------

ME = {"id": 42, "username": "RecourseBot"}


def group(text, **extra):
    return {"message_id": 5, "chat": {"id": -100, "type": "supergroup"}, "from": {"id": 7, "is_bot": False}, "text": text, **extra}


def test_in_a_group_it_answers_only_when_named_or_replied_to():
    assert addressed({"chat": {"type": "private"}, "text": "how often does it rule for the seller"}, ME) == "how often does it rule for the seller"
    assert addressed(group("how often does it rule for the seller"), ME) is None
    assert addressed(group("/stats"), ME) is None
    assert addressed(group("@recoursebot what is this"), ME) == "what is this"
    assert addressed(group("/stats@RecourseBot"), ME) == "/stats"
    assert addressed(group("/stats@OtherBot"), ME) is None
    assert addressed(group("@RecourseBotFan hello"), ME) is None
    assert addressed(group("and the one before it", reply_to_message={"from": {"id": 42}}), ME) == "and the one before it"
    assert addressed(group("thanks", reply_to_message={"from": {"id": 9}}), ME) is None
    assert addressed(group("what is this", entities=[{"type": "text_mention", "user": {"id": 42}}]), ME) == "what is this"


def test_one_message_gets_one_reply_and_the_bot_never_speaks_first():
    conversations, bucket, deps = world()
    ctx = Context(conversations=conversations, bucket=bucket, deps=deps, threads=Threads(), seen=Seen())
    update = {"update_id": 1, "message": group("/stats@RecourseBot")}
    first = respond(update, ME, ctx)
    assert first is not None and first.reply_to == 5 and "payments 7" in first.text
    assert respond(update, ME, ctx) is None, "a message delivered twice is answered once"
    from_a_bot = group("@RecourseBot hi", **{"from": {"id": 8, "is_bot": True}, "message_id": 6})
    assert respond({"update_id": 2, "message": from_a_bot}, ME, ctx) is None, "another bot is never answered"
    assert respond({"update_id": 3}, ME, ctx) is None, "an update with no message is not a prompt to speak"
    direct = respond({"update_id": 4, "message": {"message_id": 9, "chat": {"id": 11, "type": "private"}, "from": {"id": 11}, "text": "/stats"}}, ME, ctx)
    assert direct is not None and direct.reply_to is None
    # The only place a message is sent is the reply to an update.
    main = (ROOT / "bot" / "main.py").read_text(encoding="utf-8")
    assert main.count(".send(") == 1 and "out = respond(update" in main


def test_the_reference_the_bot_explains_from_is_the_skills_own():
    ours = (ROOT / "bot" / "what_is_recourse.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    theirs = ROOT.parent / "recourse-skill" / "reference" / "01-what-is-recourse.md"
    if not theirs.exists():
        pytest.skip("the skill repository is not checked out beside this one")
    assert ours == theirs.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_a_missing_credential_is_said_before_any_charge_and_never_crashes_a_turn(monkeypatch):
    """
    The SDK builds a client with no credential and fails only when a request
    is sent. The first live run of ten questions found that by charging the
    chat and then crashing the turn with no reply at all.
    """
    import anthropic

    bare = SimpleNamespace(api_key=None, auth_token=None, credentials=None)
    monkeypatch.setattr(anthropic, "Anthropic", lambda *args, **kwargs: bare)
    ready, why = ClaudeChat().ready()
    assert ready is False and "no Anthropic credential" in why
    conversations, bucket, deps = world()
    reply = handle(1, "how often does it rule for the seller", conversations, bucket, deps, threads=Threads(), chat=ClaudeChat())
    assert "no Anthropic credential" in reply and "/stats" in reply
    assert bucket.take(1, cost=bucket.capacity), "saying so cost nothing"

    class Unauthenticated:
        def create(self, **kwargs):
            raise TypeError('"Could not resolve authentication method. Expected one of api_key, auth_token, or credentials to be set."')

    chat = ClaudeChat(client=SimpleNamespace(beta=SimpleNamespace(messages=Unauthenticated())))
    reply = handle(2, "how often does it rule for the seller", conversations, bucket, deps, threads=Threads(), chat=chat)
    assert "no Anthropic credential" in reply, "a request that cannot authenticate is a reply, not a crash"
