"""
The bot, without Telegram, a chain or a model.

The boundary is tested as a property of the process, not a policy: the client
has no account, the source names no write method, a secret gets one reply and
nothing else is read. The commands are tested through injected dependencies
that record what they were asked.
"""

from __future__ import annotations

import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from bot.guard import looks_like_secret  # noqa: E402
from bot.handlers import Unavailable, citation, handle, to_pid  # noqa: E402
from bot.state import Bucket, Conversations  # noqa: E402


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

    def addresses(self):
        return {"escrow": "0xESCROW", "dispute": "0xDISPUTE", "explorer": "https://explorer"}

    def read_json(self, contract, method, args):
        self.calls.append(("read", contract, method, tuple(args)))
        if self.fail_chain:
            raise Unavailable("rate limited")
        if method == "get_payment":
            return dict(self.payment)
        if method == "get_case":
            return dict(self.case)
        if method == "get_seller":
            return {"address": args[0], "promise": "P", "active": True, "judgeable": True, "registered_at": 1, "total": 7, "upheld": 2, "live": 3, "reviewed": ""}
        if method == "gate_reason":
            return ""
        if method == "stats" and contract == "0xESCROW":
            return {"payments": 7, "held": str(9 * 10**18), "bond_amount": str(10**18), "window_seconds": 300}
        if method == "stats":
            return {"cases": 3}
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


def test_the_chain_reader_has_no_account():
    from bot.main import reader

    chain = reader()
    assert chain.account is None
    assert getattr(chain.client, "local_account", None) is None


def test_no_file_in_the_bot_names_a_write():
    # The chain's write methods and anything that would need a key. Not the
    # word "withdrawing" in help text, and not sys.stderr.write: the first
    # version banned both and failed on its own prose.
    banned = (
        "write_contract", "deploy_contract", "send_transaction", "chain.write(", ".write(contract",
        "open_dispute(", "register_seller(", "record_response(", "reclaim(", "withdraw(",
        "private_key", "sign_message", "create_account(", "load_accounts(",
    )
    for path in (ROOT / "bot").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        # Strip docstrings and comments: the README-style prose in module
        # docstrings legitimately names the things it promises not to do.
        code = re.sub(r'"""[\s\S]*?"""', "", source)
        code = re.sub(r"^\s*#.*$", "", code, flags=re.M)
        for word in banned:
            assert word not in code, f"{path.name} mentions {word}"


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
