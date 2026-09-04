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
