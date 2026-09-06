"""
Tests for the off chain half: the agent's deterministic checks, the promise
reader, the canonicaliser and the seller's signing.

None of this is trusted by the contracts. It is tested because a bug here shows
up as the demo failing to detect a bad response, which looks like a judgment
failure and is not one.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent.checks import check  # noqa: E402
from agent.run import read_promise_bounds  # noqa: E402
from seller.main import build_body  # noqa: E402
from seller.signing import recover, sign_body, verify  # noqa: E402
from shared.canonical import canonical, digest, digest_text  # noqa: E402

NOW = datetime.datetime(2026, 9, 4, 18, 20, 4, tzinfo=datetime.timezone.utc)
PROMISE = (
    "Returns the spot price for the requested pair, aggregated from at least "
    "three venues, with a timestamp no more than five seconds old."
)
KEY = "0x" + "11" * 32


def at(offset: int) -> str:
    return (NOW + datetime.timedelta(seconds=offset)).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- the promise reader ---------------------------------------------------


def test_the_standard_promise_yields_five_seconds_and_three_sources():
    assert read_promise_bounds(PROMISE) == (5, 3)


def test_digits_and_words_both_read():
    assert read_promise_bounds("refreshed within 5 seconds, at least 3 venues") == (5, 3)
    assert read_promise_bounds("no more than ten seconds old, at least two sources") == (10, 2)


def test_an_unreadable_promise_falls_back_to_bounds_that_pass_everything():
    """
    The agent must never contest on a bound it invented. A promise it cannot read
    produces no complaint, and the payment goes through.
    """
    max_age, min_sources = read_promise_bounds("Returns accurate market data.")
    assert min_sources == 0
    assert max_age > 10**8
    assert check(
        {"pair": "ETH-USD", "price": 1.0, "sources": 1, "ts": at(-7200)},
        "ETH-USD", max_age, min_sources, now=NOW,
    ).ok


# --- the three checks -----------------------------------------------------


def ok(body: dict) -> bool:
    return check(body, "ETH-USD", 5, 3, now=NOW).ok


def test_a_good_response_passes():
    assert ok({"pair": "ETH-USD", "price": 4182.10, "sources": 3, "ts": at(-2)})


def test_stale_is_caught():
    result = check(
        {"pair": "ETH-USD", "price": 4182.10, "sources": 3, "ts": at(-32400)},
        "ETH-USD", 5, 3, now=NOW,
    )
    assert not result.ok and result.mode == "stale"
    assert "32400s old" in result.reason and "allows 5s" in result.reason


def test_hollow_is_caught():
    for body in (
        {"pair": "ETH-USD", "results": [], "count": 0},
        {"pair": "ETH-USD", "price": None, "sources": 3, "ts": at(-1)},
        {"pair": "ETH-USD", "price": 0, "sources": 3, "ts": at(-1)},
        {"pair": "ETH-USD", "price": "string", "sources": 3, "ts": at(-1)},
        {},
    ):
        result = check(body, "ETH-USD", 5, 3, now=NOW)
        assert not result.ok and result.mode == "hollow", body


def test_substituted_is_caught():
    result = check(
        {"pair": "BTC-USD", "price": 118400.0, "sources": 3, "ts": at(-1)},
        "ETH-USD", 5, 3, now=NOW,
    )
    assert not result.ok and result.mode == "substituted"
    assert "asked ETH-USD" in result.reason and "got BTC-USD" in result.reason


def test_too_few_sources_is_caught():
    assert not ok({"pair": "ETH-USD", "price": 4182.10, "sources": 2, "ts": at(-1)})
    assert not ok({"pair": "ETH-USD", "price": 4182.10, "sources": 0, "ts": at(-1)})


def test_field_order_and_extra_fields_do_not_matter():
    assert ok({"ts": at(-2), "sources": 3, "price": 4182.10, "pair": "ETH-USD"})
    assert ok({"pair": "ETH-USD", "price": 4182.10, "sources": 3, "ts": at(-2), "extra": [1, 2]})


def test_a_naive_timestamp_is_read_as_utc_not_local():
    """Timezone is the reason an agent silently fails to notice a stale response."""
    naive = (NOW - datetime.timedelta(seconds=2)).strftime("%Y-%m-%dT%H:%M:%S")
    assert ok({"pair": "ETH-USD", "price": 1.0, "sources": 3, "ts": naive})
    offset = (NOW + datetime.timedelta(hours=1, seconds=-2)).strftime("%Y-%m-%dT%H:%M:%S+01:00")
    assert ok({"pair": "ETH-USD", "price": 1.0, "sources": 3, "ts": offset})


def test_an_unparseable_timestamp_never_raises():
    for value in (None, "", "yesterday", 12345, {"nested": True}):
        result = check(
            {"pair": "ETH-USD", "price": 1.0, "sources": 3, "ts": value},
            "ETH-USD", 5, 3, now=NOW,
        )
        assert not result.ok


def test_the_agent_makes_no_model_call():
    source = (ROOT / "agent" / "checks.py").read_text(encoding="utf-8")
    runner = (ROOT / "agent" / "run.py").read_text(encoding="utf-8")
    for banned in ("openai", "anthropic", "exec_prompt", "completion"):
        assert banned not in source.lower() and banned not in runner.lower()


# --- the seller's four modes ----------------------------------------------


def test_every_mode_is_well_formed_and_only_correct_passes():
    passes = {}
    for mode in ("correct", "stale", "hollow", "substituted"):
        body = build_body("ETH-USD", mode)
        assert json.loads(canonical(body)) == body, f"{mode} must serialise cleanly"
        passes[mode] = check(body, "ETH-USD", 5, 3).ok
    assert passes == {"correct": True, "stale": False, "hollow": False, "substituted": False}


def test_each_failure_mode_is_the_one_it_claims_to_be():
    modes = {
        mode: check(build_body("ETH-USD", mode), "ETH-USD", 5, 3).mode
        for mode in ("stale", "hollow", "substituted")
    }
    assert modes == {"stale": "stale", "hollow": "hollow", "substituted": "substituted"}


# --- canonicalisation and signing -----------------------------------------


def test_canonical_sorts_keys_and_drops_whitespace():
    assert canonical({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    assert canonical({"a": [1, {"z": 1, "y": 2}]}) == '{"a":[1,{"y":2,"z":1}]}'


def test_two_orderings_of_the_same_object_hash_the_same():
    first = {"pair": "ETH-USD", "price": 4182.10, "sources": 3}
    second = {"sources": 3, "price": 4182.10, "pair": "ETH-USD"}
    assert digest(first) == digest(second)


def test_non_ascii_hashes_as_characters_not_escapes():
    assert canonical({"venue": "Kraken é"}) == '{"venue":"Kraken é"}'


def test_a_signature_recovers_the_signing_address():
    body = {"pair": "ETH-USD", "price": 4182.10, "sources": 3, "ts": at(0)}
    text, signature = sign_body(KEY, body)
    from eth_account import Account

    assert recover(text, signature).lower() == Account.from_key(KEY).address.lower()
    assert verify(text, signature, Account.from_key(KEY).address)


def test_the_signed_string_is_the_string_that_goes_on_chain():
    """
    Re-serialising between signing and recording is the classic way to lose an
    hour. The signature is over the exact bytes, so the exact bytes are returned.
    """
    body = {"z": 1, "a": 2}
    text, signature = sign_body(KEY, body)
    assert text == '{"a":2,"z":1}'
    assert verify(text, signature, __import__("eth_account").Account.from_key(KEY).address)
    reserialised = json.dumps(json.loads(text))
    assert reserialised != text
    assert not verify(reserialised, signature, __import__("eth_account").Account.from_key(KEY).address)


def test_a_tampered_body_fails_verification():
    body = {"pair": "ETH-USD", "price": 4182.10, "sources": 3, "ts": at(0)}
    text, signature = sign_body(KEY, body)
    from eth_account import Account

    # A JSON float does not round trip as it was written: 4182.10 serialises as
    # 4182.1, so the string on chain is not the literal from the source. Tamper
    # with the serialised form, which is the thing that was actually signed.
    assert '"price":4182.1,' in text
    tampered = text.replace("4182.1,", "9999.99,")
    assert tampered != text
    assert not verify(tampered, signature, Account.from_key(KEY).address)
    assert not verify(text.replace("ETH-USD", "BTC-USD"), signature, Account.from_key(KEY).address)


def test_digest_text_matches_digest_of_the_same_object():
    body = {"a": 1, "b": [2, 3]}
    assert digest_text(canonical(body)) == digest(body)


if __name__ == "__main__":
    failures = []
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for name, fn in tests:
        try:
            fn()
        except Exception as error:  # noqa: BLE001
            failures.append(f"{name}: {type(error).__name__} {error}")
    print(f"{len(tests) - len(failures)}/{len(tests)} off chain tests passed")
    for line in failures:
        print("  FAIL", line)
    sys.exit(1 if failures else 0)


# --- refusing a request the promise never covered -------------------------
#
# Every test below exists because of a bug that was in the endpoint, not
# because of one that was imagined. `BOOK.get(pair, 0.0)` answered a fabricated
# {"price": 0.0, "sources": 3} for any pair it had never carried, the seller
# signed it, and the buyer picks the pair. That is a way to manufacture a
# breach out of an honest endpoint, and the agent then contested it
# automatically.


def test_an_unsupported_pair_is_refused_rather_than_priced_at_zero():
    body = build_body("DOGE-USD", "correct")
    assert body["error"] == "unsupported pair"
    assert "price" not in body
    assert "sources" not in body
    assert body["supported"] == ["BTC-USD", "ETH-USD", "SOL-USD"]


def test_every_failure_mode_still_refuses_an_unsupported_pair():
    # The switch must not become a way to get a fabricated quote back.
    for mode in ("correct", "stale", "hollow", "substituted"):
        body = build_body("NOPE-USD", mode)
        assert body.get("error") == "unsupported pair", mode
        assert "price" not in body, mode


def test_the_seller_never_signs_an_unbounded_pair():
    from seller.main import MAX_PAIR

    body = build_body("X" * 500, "correct")
    assert len(body["requested"]) <= MAX_PAIR
    text, signature = sign_body(KEY, body)
    assert verify(text, signature, recover(text, signature))


def test_a_refusal_is_not_contestable():
    body = build_body("DOGE-USD", "correct")
    verdict = check(body, "DOGE-USD", 5, 3, now=NOW)
    assert verdict.mode == "declined"
    # Not ok, because nothing was delivered. Not contestable either, because
    # there is nothing for a committee to rule on.
    assert verdict.ok is False
    assert verdict.contestable is False


def test_a_real_failure_is_still_contestable():
    # build_body stamps against the real clock, so the check has to read the
    # same one. Pinning NOW here put the stale body in the future and made it
    # look fresh, which is the freshness bug this project already fixed once.
    moment = datetime.datetime.now(datetime.timezone.utc)
    for mode in ("stale", "hollow", "substituted"):
        body = build_body("ETH-USD", mode)
        verdict = check(body, "ETH-USD", 5, 3, now=moment)
        assert verdict.contestable is True, mode


def test_an_error_body_carrying_a_price_is_not_treated_as_a_refusal():
    # A seller could otherwise dodge every dispute by attaching an error string
    # to a response that did arrive.
    body = {"error": "degraded", "pair": "ETH-USD", "price": 0, "sources": 3, "ts": at(0)}
    verdict = check(body, "ETH-USD", 5, 3, now=NOW)
    assert verdict.mode != "declined"
    assert verdict.contestable is True


# --- the rail is negotiated, not assumed ----------------------------------


def test_both_rails_advertise_a_different_scheme_and_header():
    from seller.main import RAILS

    assert RAILS["x402"]["header"] != RAILS["external"]["header"]
    assert RAILS["x402"]["scheme"] != RAILS["external"]["scheme"]


def test_the_agent_reads_the_proof_header_out_of_the_challenge(monkeypatch):
    from agent import run as agent_run

    challenge = json.dumps(
        {"accepts": [{"scheme": "external-settlement", "header": "x-settlement-id"}]}
    )
    monkeypatch.setattr(agent_run, "http", lambda *a, **k: (402, challenge, {}))
    rail = agent_run.discover_rail("http://endpoint", "ETH-USD")
    assert rail == {
        "scheme": "external-settlement",
        "header": "x-settlement-id",
        "challenged": True,
    }


def test_a_malformed_challenge_falls_back_to_x402_rather_than_raising(monkeypatch):
    from agent import run as agent_run

    for body in ("not json", "{}", '{"accepts": []}', '{"accepts": [{}]}'):
        monkeypatch.setattr(agent_run, "http", lambda *a, **k: (402, body, {}))
        rail = agent_run.discover_rail("http://endpoint", "ETH-USD")
        assert rail["header"] == "x-payment-proof", body
        assert rail["challenged"] is True


def test_an_endpoint_that_does_not_ask_for_payment_is_reported_as_such(monkeypatch):
    from agent import run as agent_run

    monkeypatch.setattr(agent_run, "http", lambda *a, **k: (200, "{}", {}))
    assert agent_run.discover_rail("http://endpoint", "ETH-USD")["challenged"] is False


# --- the evaluation sets stay separable -----------------------------------


def test_the_two_case_sets_share_no_ids():
    first = json.loads((ROOT / "eval" / "cases.json").read_text(encoding="utf-8"))
    second = json.loads((ROOT / "eval" / "cases-v2.json").read_text(encoding="utf-8"))
    assert not {case["id"] for case in first} & {case["id"] for case in second}


def test_every_case_carries_an_expected_verdict_from_the_closed_set():
    for name in ("cases.json", "cases-v2.json"):
        rows = json.loads((ROOT / "eval" / name).read_text(encoding="utf-8"))
        for case in rows:
            assert case["expected"] in {"honored", "not_honored", "unclear"}, case["id"]
            assert case["note"].strip(), case["id"]


# --- a write is retried only while it is provably unsent ------------------
#
# The SDK fetches the nonce and signs inside every write_contract call. A plain
# retry around it, on a response lost after the node accepted the transaction,
# fetches nonce N+1 and sends a second one, and for pay that is a second
# payment. The nonce is the evidence: unchanged means nothing reached the node.


class _Account:
    address = "0x" + "ab" * 20


class _Client:
    """Fails a set number of times, and moves the nonce or not, on purpose."""

    def __init__(self, failures: int, nonce_moves_on_failure: bool, nonce_readable: bool = True):
        self.failures = failures
        self.moves = nonce_moves_on_failure
        self.readable = nonce_readable
        self.nonce = 7
        self.sent = 0

    def get_current_nonce(self, address):
        if not self.readable:
            raise ConnectionError("nonce unreadable")
        return self.nonce

    def write_contract(self, **kwargs):
        if self.failures:
            self.failures -= 1
            if self.moves:
                # The node took it and the response was lost.
                self.nonce += 1
            raise TimeoutError("read timed out")
        self.sent += 1
        self.nonce += 1
        return "0xhash"


def _chain(client):
    from shared import chain as chain_module

    # No sleeping between attempts in a unit test.
    chain_module.BACKOFF = 0
    return chain_module.Chain(account=_Account(), client=client)


def test_a_failure_before_the_node_saw_it_is_retried():
    client = _Client(failures=2, nonce_moves_on_failure=False)
    assert _chain(client).write("0xescrow", "pay", ["s", "r"], value=1) == "0xhash"
    assert client.sent == 1


def test_a_lost_response_after_the_node_took_it_is_never_resent():
    import pytest

    client = _Client(failures=1, nonce_moves_on_failure=True)
    with pytest.raises(RuntimeError, match="Not resending"):
        _chain(client).write("0xescrow", "pay", ["s", "r"], value=1)
    # The one attempt that failed is the only transaction the node ever saw.
    assert client.sent == 0
    assert client.nonce == 8


def test_an_unreadable_nonce_does_not_default_to_resending():
    import pytest

    client = _Client(failures=1, nonce_moves_on_failure=False, nonce_readable=False)
    with pytest.raises(RuntimeError, match="Not resending"):
        _chain(client).write("0xescrow", "pay", ["s", "r"], value=1)
    assert client.sent == 0


def test_a_contract_refusal_is_never_retried():
    import pytest

    class Refusing(_Client):
        def write_contract(self, **kwargs):
            self.sent += 1
            raise RuntimeError("execution reverted: [EXPECTED] wrong bond")

    client = Refusing(failures=0, nonce_moves_on_failure=False)
    with pytest.raises(RuntimeError, match="wrong bond"):
        _chain(client).write("0xescrow", "open_dispute", ["p-000001"], value=1)
    assert client.sent == 1
