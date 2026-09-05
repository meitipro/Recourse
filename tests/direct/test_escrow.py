"""
Direct tests for the escrow. State transitions, access control, validation and
the settlement table, all on plain CPython against the doubles.

No model call appears anywhere in this file or in the contract it exercises.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import genvm_double as D  # noqa: E402
from harness import ONE_GEN, World, raises  # noqa: E402

ST_OPEN, ST_WITHDRAWN, ST_DISPUTED, ST_RESOLVED = 0, 1, 2, 3
V_NONE, V_HONORED, V_NOT_HONORED, V_UNCLEAR = 0, 1, 2, 3


# --- registration ---------------------------------------------------------


def test_promise_too_short_is_rejected():
    w = World()
    w.sender(w.SELLER)
    raises("promise length", w.escrow.register_seller, "too short")
    w.check_invariants()


def test_promise_too_long_is_rejected():
    w = World()
    w.sender(w.SELLER)
    raises("promise length", w.escrow.register_seller, "x" * 501)


def test_promise_at_both_bounds_is_accepted():
    w = World()
    w.register("x" * 20)
    assert w.seller()["promise"] == "x" * 20
    w.register("y" * 500, who=w.STRANGER)
    assert w.seller(w.STRANGER)["promise"] == "y" * 500


def test_duplicate_registration_is_rejected():
    w = World()
    w.register()
    w.sender(w.SELLER)
    raises("already registered", w.escrow.register_seller, w.PROMISE)


def test_promise_is_stored_exactly_as_given():
    w = World()
    odd = "  Returns a price.  Spacing   preserved, <angle> brackets kept.  "
    w.register(odd)
    assert w.seller()["promise"] == odd, "the promise is evidence and must not be normalised"


def test_a_new_seller_starts_with_zeroed_counters():
    w = World()
    w.register()
    row = w.seller()
    assert (row["total"], row["upheld"], row["live"]) == (0, 0, 0)
    assert row["active"] is True and row["judgeable"] is True


def test_get_seller_refuses_an_unknown_address():
    w = World()
    raises("unknown seller", w.escrow.get_seller, w.STRANGER)


# --- update_promise -------------------------------------------------------


def test_promise_cannot_be_rewritten_while_a_payment_is_open():
    w = World()
    w.register()
    w.pay()
    w.sender(w.SELLER)
    raises("open payments", w.escrow.update_promise, "A different promise entirely, at length.")
    w.check_invariants()


def test_promise_cannot_be_rewritten_while_a_payment_is_disputed():
    w = World().wired()
    w.register()
    pid = w.pay()
    w.record(pid)
    w.dispute_it(pid)
    w.sender(w.SELLER)
    raises("open payments", w.escrow.update_promise, "A different promise entirely, at length.")


def test_promise_can_be_rewritten_once_the_payment_is_settled():
    w = World()
    w.register()
    pid = w.pay()
    w.advance(301)
    w.sender(w.SELLER)
    w.escrow.withdraw(pid)
    fresh = "A new promise, long enough to pass the twenty character floor."
    w.escrow.update_promise(fresh)
    assert w.seller()["promise"] == fresh
    w.check_invariants()


def test_only_a_registered_seller_may_update_a_promise():
    w = World()
    w.sender(w.STRANGER)
    raises("not registered", w.escrow.update_promise, "A promise from nobody in particular.")


# --- payment --------------------------------------------------------------


def test_zero_value_is_rejected():
    w = World()
    w.register()
    w.sender(w.BUYER, 0)
    raises("zero value", w.escrow.pay, w.SELLER, "GET /quote")


def test_unregistered_seller_is_rejected():
    w = World()
    w.sender(w.BUYER, ONE_GEN)
    raises("unknown seller", w.escrow.pay, w.STRANGER, "GET /quote")


def test_inactive_seller_is_rejected():
    w = World()
    w.register()
    w.sender(w.SELLER)
    w.escrow.set_active(False)
    w.sender(w.BUYER, ONE_GEN)
    raises("seller inactive", w.escrow.pay, w.SELLER, "GET /quote")


def test_unjudgeable_promise_is_rejected():
    w = World()
    w.register()
    w.escrow.sellers[D.Address(w.SELLER)].judgeable = False
    w.sender(w.BUYER, ONE_GEN)
    raises("promise not judgeable", w.escrow.pay, w.SELLER, "GET /quote")


def test_request_over_the_cap_is_rejected():
    w = World()
    w.register()
    w.sender(w.BUYER, ONE_GEN)
    raises("request too long", w.escrow.pay, w.SELLER, "x" * 2001)


def test_window_ends_is_set_from_the_transaction_time():
    w = World(window=300)
    w.register()
    pid = w.pay()
    row = w.payment(pid)
    assert row["window_ends"] - row["created_at"] == 300
    assert row["created_at"] == w.t


def test_the_payment_id_is_appended_to_the_index():
    w = World()
    w.register()
    pid = w.pay()
    assert list(w.escrow.payment_ids) == [pid]
    assert w.escrow.recent(D.u32(10)) == [pid]


def test_two_payments_produce_different_ids():
    w = World()
    w.register()
    first = w.pay()
    second = w.pay()
    assert first != second
    assert w.escrow.recent(D.u32(10)) == [second, first], "recent is newest first"
    w.check_invariants()


def test_recent_is_capped_at_one_hundred():
    w = World()
    w.register()
    for _ in range(103):
        w.pay(amount=1)
    assert len(w.escrow.recent(D.u32(500))) == 100
    assert len(w.escrow.recent(D.u32(7))) == 7
    assert w.escrow.recent(D.u32(0)) == []


def test_paying_increments_total_and_live():
    w = World()
    w.register()
    w.pay()
    w.pay()
    row = w.seller()
    assert row["total"] == 2 and row["live"] == 2


def test_recent_rows_answers_the_whole_page_in_one_call():
    """
    The feed used to read recent() and then get_payment() per id, which is one
    request per row. Studio allows thirty a minute, so a dozen rows rate limited
    the page on an ordinary load and it rendered an error over an empty table.
    """
    w = World().wired()
    w.register()
    first = w.pay(amount=2 * ONE_GEN)
    second = w.pay(amount=3 * ONE_GEN)
    w.record(second, '{"pair":"ETH-USD"}', "0xsig")

    rows = json.loads(w.escrow.recent_rows(D.u32(10)))
    assert [row["pid"] for row in rows] == [second, first], "newest first"
    assert rows[0]["amount"] == str(3 * ONE_GEN)
    assert rows[0]["has_response"] is True and rows[0]["signed"] is True
    assert rows[1]["has_response"] is False and rows[1]["signed"] is False
    assert rows[0]["status"] == ST_OPEN and rows[0]["verdict"] == V_NONE


def test_recent_rows_carries_no_evidence_bodies():
    """
    The bodies are the largest fields on chain and only one row's worth is ever
    on screen. Carrying fifty of them to show none is what made the list read
    expensive in the first place.
    """
    w = World()
    w.register()
    pid = w.pay()
    body = '{"pair":"ETH-USD","price":4182.1,"sources":3,"ts":"2026-09-04T18:20:02Z"}'
    w.record(pid, body, "0xsignature")
    blob = w.escrow.recent_rows(D.u32(5))
    assert body not in blob
    assert "0xsignature" not in blob
    assert "GET /quote" not in blob
    row = json.loads(blob)[0]
    assert set(row) == {
        "pid", "buyer", "seller", "amount", "bond", "created_at", "responded_at",
        "window_ends", "dispute_ends", "has_response", "signed", "recorded_by",
        "status", "verdict",
    }


def test_recent_rows_is_capped_and_never_negative():
    w = World()
    w.register()
    for _ in range(103):
        w.pay(amount=1)
    assert len(json.loads(w.escrow.recent_rows(D.u32(500)))) == 100
    assert len(json.loads(w.escrow.recent_rows(D.u32(4)))) == 4
    assert json.loads(w.escrow.recent_rows(D.u32(0))) == []


def test_recent_rows_and_get_payment_agree():
    """One is a summary of the other, so they must never disagree about a fact."""
    w = World().wired()
    w.register()
    pid = w.pay(amount=7 * ONE_GEN)
    w.record(pid, '{"x":1}', "0xsig")
    w.dispute_it(pid)
    summary = json.loads(w.escrow.recent_rows(D.u32(1)))[0]
    full = w.payment(pid)
    for field in ("pid", "buyer", "seller", "amount", "bond", "created_at",
                  "responded_at", "window_ends", "status", "verdict", "recorded_by"):
        assert summary[field] == full[field], field
    assert summary["has_response"] == (full["response"] != "")
    assert summary["signed"] == (full["response_sig"] != "")


def test_an_unknown_payment_id_is_refused():
    w = World()
    raises("unknown payment", w.escrow.get_payment, "p-999999")


# --- response -------------------------------------------------------------


def test_only_a_party_to_the_payment_may_record():
    w = World()
    w.register()
    pid = w.pay()
    w.sender(w.STRANGER)
    raises("not a party", w.escrow.record_response, pid, "body", "sig")


def test_the_seller_records_and_the_signature_is_kept():
    w = World()
    w.register()
    pid = w.pay()
    w.record(pid, '{"price":1}', "0xabc")
    row = w.payment(pid)
    assert row["response"] == '{"price":1}'
    assert row["response_sig"] == "0xabc"
    assert row["recorded_by"].lower() == w.SELLER.lower()


def test_the_buyer_may_record_when_the_seller_has_not():
    """
    Closes the path where a seller takes payment, delivers nothing on chain and
    leaves the buyer unable to contest. A response the seller never signed is
    stored without a signature, so it is visibly not one they stood behind.
    """
    w = World()
    w.register()
    pid = w.pay()
    w.sender(w.BUYER)
    w.escrow.record_response(pid, '{"results":[]}', "0xbuyerclaims")
    row = w.payment(pid)
    assert row["response"] == '{"results":[]}'
    assert row["response_sig"] == "", "only the seller's signature is ever kept"
    assert row["recorded_by"].lower() == w.BUYER.lower()


def test_a_response_cannot_be_recorded_twice():
    w = World()
    w.register()
    pid = w.pay()
    w.record(pid)
    w.sender(w.SELLER)
    raises("response already recorded", w.escrow.record_response, pid, "second", "sig")


def test_the_buyer_cannot_overwrite_the_sellers_response():
    w = World()
    w.register()
    pid = w.pay()
    w.record(pid, "the delivered body")
    w.sender(w.BUYER)
    raises("response already recorded", w.escrow.record_response, pid, "a forgery", "sig")


def test_an_empty_response_is_refused():
    """Otherwise the response field stays empty and the dispute path stays shut."""
    w = World()
    w.register()
    pid = w.pay()
    w.sender(w.SELLER)
    raises("empty response", w.escrow.record_response, pid, "", "sig")


def test_a_response_cannot_be_recorded_after_the_window():
    w = World()
    w.register()
    pid = w.pay()
    w.advance(301)
    w.sender(w.SELLER)
    raises("window closed", w.escrow.record_response, pid, "late", "sig")


def test_a_response_over_the_cap_is_rejected():
    w = World()
    w.register()
    pid = w.pay()
    w.sender(w.SELLER)
    raises("response too long", w.escrow.record_response, pid, "x" * 4001, "sig")


def test_a_signature_over_the_cap_is_rejected():
    # The one party written field that had no bound. A real secp256k1 signature
    # is 130 hex characters, so anything approaching this is not a signature.
    w = World()
    w.register()
    pid = w.pay()
    w.sender(w.SELLER)
    raises("signature too long", w.escrow.record_response, pid, "body", "0x" + "1" * 400)


def test_a_real_length_signature_is_accepted():
    w = World()
    w.register()
    pid = w.pay()
    w.sender(w.SELLER)
    w.escrow.record_response(pid, "body", "0x" + "ab" * 65)
    assert w.payment(pid)["response_sig"] == "0x" + "ab" * 65


def test_the_stored_response_matches_byte_for_byte():
    w = World()
    w.register()
    pid = w.pay()
    body = '{"pair":"ETH-USD","price":4182.10,"sources":3,"ts":"2026-09-04T18:19:58Z"}'
    w.record(pid, body)
    assert w.payment(pid)["response"] == body


def test_a_response_cannot_be_recorded_once_disputed():
    w = World().wired()
    w.register()
    pid = w.pay()
    w.record(pid)
    w.dispute_it(pid)
    w.sender(w.SELLER)
    raises("not open", w.escrow.record_response, pid, "another", "sig")


# --- withdraw -------------------------------------------------------------


def test_withdraw_is_rejected_before_the_window_ends():
    w = World()
    w.register()
    pid = w.pay()
    w.sender(w.SELLER)
    raises("window open", w.escrow.withdraw, pid)
    w.advance(300)
    w.sender(w.SELLER)
    raises("window open", w.escrow.withdraw, pid)


def test_withdraw_is_rejected_by_a_non_seller():
    w = World()
    w.register()
    pid = w.pay()
    w.advance(301)
    w.sender(w.BUYER)
    raises("not seller", w.escrow.withdraw, pid)


def test_withdraw_moves_exactly_the_amount():
    w = World()
    w.register()
    pid = w.pay(amount=4 * ONE_GEN)
    w.advance(301)
    w.sender(w.SELLER)
    w.escrow.withdraw(pid)
    assert w.paid_to(w.SELLER) == 4 * ONE_GEN
    assert w.payment(pid)["status"] == ST_WITHDRAWN
    assert w.seller()["live"] == 0
    w.check_invariants()


def test_withdraw_is_rejected_twice():
    w = World()
    w.register()
    pid = w.pay()
    w.advance(301)
    w.sender(w.SELLER)
    w.escrow.withdraw(pid)
    w.sender(w.SELLER)
    raises("not open", w.escrow.withdraw, pid)
    assert len(w.transfers()) == 1, "a second payout must not be emitted"


def test_a_withdrawn_payment_cannot_be_disputed():
    w = World().wired()
    w.register()
    pid = w.pay()
    w.record(pid)
    w.advance(301)
    w.sender(w.SELLER)
    w.escrow.withdraw(pid)
    w.sender(w.BUYER, ONE_GEN)
    raises("not open", w.escrow.open_dispute, pid)


# --- dispute --------------------------------------------------------------


def test_dispute_is_rejected_without_a_recorded_response():
    """Invariant three."""
    w = World().wired()
    w.register()
    pid = w.pay()
    w.sender(w.BUYER, ONE_GEN)
    raises("no response", w.escrow.open_dispute, pid)


def test_dispute_is_rejected_after_the_window():
    w = World().wired()
    w.register()
    pid = w.pay()
    w.record(pid)
    w.advance(301)
    w.sender(w.BUYER, ONE_GEN)
    raises("window closed", w.escrow.open_dispute, pid)


def test_dispute_is_rejected_with_the_wrong_bond():
    w = World().wired()
    w.register()
    pid = w.pay()
    w.record(pid)
    for wrong in (0, ONE_GEN - 1, ONE_GEN + 1, 2 * ONE_GEN):
        w.sender(w.BUYER, wrong)
        raises("wrong bond", w.escrow.open_dispute, pid)


def test_dispute_is_rejected_by_a_non_buyer():
    w = World().wired()
    w.register()
    pid = w.pay()
    w.record(pid)
    for who in (w.SELLER, w.STRANGER, w.OWNER):
        w.sender(who, ONE_GEN)
        raises("not buyer", w.escrow.open_dispute, pid)


def test_dispute_is_rejected_before_the_dispute_contract_is_wired():
    w = World()
    w.register()
    pid = w.pay()
    w.record(pid)
    w.sender(w.BUYER, ONE_GEN)
    raises("dispute contract not set", w.escrow.open_dispute, pid)


def test_opening_a_dispute_sets_the_status_and_emits_the_adjudication():
    w = World().wired()
    w.register()
    pid = w.pay()
    w.record(pid, '{"pair":"ETH-USD","price":4182.10,"sources":3,"ts":"stale"}')
    w.dispute_it(pid)
    row = w.payment(pid)
    assert row["status"] == ST_DISPUTED
    assert int(row["bond"]) == ONE_GEN
    emitted = w.gl.bus.emissions[-1]
    assert emitted.method == "adjudicate"
    assert emitted.to.lower() == w.DISPUTE.lower()
    assert emitted.args[0] == pid
    assert emitted.args[1] == w.PROMISE, "the promise travels with the case, frozen"
    assert emitted.args[3] == row["response"]
    w.check_invariants()


def test_a_dispute_cannot_be_opened_twice():
    w = World().wired()
    w.register()
    pid = w.pay()
    w.record(pid)
    w.dispute_it(pid)
    w.sender(w.BUYER, ONE_GEN)
    raises("not open", w.escrow.open_dispute, pid)


# --- settle ---------------------------------------------------------------


def test_settle_is_rejected_from_every_address_except_the_dispute_contract():
    """
    Invariant five, and the single most important access check in the project.
    Without it any account could name its own verdict and drain the escrow.
    """
    w = World().wired()
    w.register()
    pid = w.pay()
    w.record(pid)
    w.dispute_it(pid)
    for who in (w.OWNER, w.SELLER, w.BUYER, w.STRANGER, w.ESCROW):
        w.sender(who)
        raises("not authorised", w.escrow.settle, pid, D.u8(V_NOT_HONORED), "mine now")
    assert w.transfers() == [], "no value may leave on a refused settlement"
    w.check_invariants()


def _settle(w: World, pid: str, verdict: int) -> None:
    """Call settle exactly as an emitted message from the dispute contract does."""
    w.gl.message.sender_address = D.Address(w.DISPUTE)
    w.gl.message.origin_address = D.Address(w.DISPUTE)
    w.gl.message.contract_address = D.Address(w.ESCROW)
    w.gl.bus.current = D.Address(w.ESCROW)
    w.gl.message.value = 0
    w.escrow.settle(pid, D.u8(verdict), "because")


def test_not_honored_returns_the_payment_and_the_bond_to_the_buyer():
    w = World().wired()
    w.register()
    pid = w.pay(amount=4 * ONE_GEN)
    w.record(pid)
    w.dispute_it(pid)
    _settle(w, pid, V_NOT_HONORED)
    assert w.paid_to(w.BUYER) == 5 * ONE_GEN
    assert w.paid_to(w.SELLER) == 0
    assert w.seller()["upheld"] == 1
    assert w.payment(pid)["status"] == ST_RESOLVED
    assert w.payment(pid)["verdict"] == V_NOT_HONORED
    w.check_invariants()


def test_honored_sends_the_payment_and_the_bond_to_the_seller():
    w = World().wired()
    w.register()
    pid = w.pay(amount=4 * ONE_GEN)
    w.record(pid)
    w.dispute_it(pid)
    _settle(w, pid, V_HONORED)
    assert w.paid_to(w.SELLER) == 5 * ONE_GEN
    assert w.paid_to(w.BUYER) == 0
    assert w.seller()["upheld"] == 0, "a won dispute must not move the counter"
    w.check_invariants()


def test_unclear_leaves_the_payment_and_returns_the_bond():
    w = World().wired()
    w.register()
    pid = w.pay(amount=4 * ONE_GEN)
    w.record(pid)
    w.dispute_it(pid)
    _settle(w, pid, V_UNCLEAR)
    assert w.paid_to(w.SELLER) == 4 * ONE_GEN
    assert w.paid_to(w.BUYER) == ONE_GEN
    assert w.seller()["upheld"] == 0, "nobody is penalised by an unclear verdict"
    w.check_invariants()


def test_the_upheld_counter_moves_only_on_not_honored():
    for verdict, expected in ((V_HONORED, 0), (V_NOT_HONORED, 1), (V_UNCLEAR, 0)):
        w = World().wired()
        w.register()
        pid = w.pay()
        w.record(pid)
        w.dispute_it(pid)
        _settle(w, pid, verdict)
        assert w.seller()["upheld"] == expected, f"verdict {verdict}"


def test_settle_refuses_a_verdict_outside_the_three():
    w = World().wired()
    w.register()
    pid = w.pay()
    w.record(pid)
    w.dispute_it(pid)
    for bad in (V_NONE, 4, 255):
        w.gl.message.sender_address = D.Address(w.DISPUTE)
        w.gl.bus.current = D.Address(w.ESCROW)
        raises("bad verdict", w.escrow.settle, pid, D.u8(bad), "nonsense")
    assert w.transfers() == []


def test_settle_is_rejected_on_a_payment_that_is_not_disputed():
    w = World().wired()
    w.register()
    pid = w.pay()
    w.gl.message.sender_address = D.Address(w.DISPUTE)
    w.gl.bus.current = D.Address(w.ESCROW)
    raises("not disputed", w.escrow.settle, pid, D.u8(V_NOT_HONORED), "early")


def test_settle_cannot_be_replayed():
    w = World().wired()
    w.register()
    pid = w.pay()
    w.record(pid)
    w.dispute_it(pid)
    _settle(w, pid, V_NOT_HONORED)
    w.gl.message.sender_address = D.Address(w.DISPUTE)
    w.gl.bus.current = D.Address(w.ESCROW)
    raises("not disputed", w.escrow.settle, pid, D.u8(V_NOT_HONORED), "again")
    assert w.paid_to(w.BUYER) == 5 * ONE_GEN, "the second call must move nothing"


# --- routes out -----------------------------------------------------------
# A refusal, or a judgment that never arrives, has to leave the refused party
# somewhere to go. Each of these is tested as a journey to the end, not as a
# single call, and the other half is tested too: somewhere to go must not mean
# asking the same question until the answer suits.


def test_a_dispute_that_never_decides_can_be_unwound_by_either_party():
    for who in ("BUYER", "SELLER"):
        w = World(dispute=3600).wired()
        w.register()
        pid = w.pay(amount=4 * ONE_GEN)
        w.record(pid)
        w.dispute_it(pid)
        assert w.payment(pid)["dispute_ends"] == w.t + 3600

        w.advance(3601)
        w.sender(getattr(w, who))
        w.escrow.reclaim(pid)

        row = w.payment(pid)
        assert row["status"] == ST_RESOLVED
        assert row["verdict"] == V_UNCLEAR, "a failed judgment is not a finding against anyone"
        assert w.paid_to(w.SELLER) == 4 * ONE_GEN
        assert w.paid_to(w.BUYER) == ONE_GEN
        assert w.seller()["upheld"] == 0
        assert w.seller()["live"] == 0
        w.check_invariants()


def test_reclaim_is_refused_while_the_judgment_could_still_land():
    w = World(dispute=3600).wired()
    w.register()
    pid = w.pay()
    w.record(pid)
    w.dispute_it(pid)
    for offset in (0, 1, 3600):
        w.at(w.payment(pid)["dispute_ends"] - 3600 + offset)
        w.sender(w.BUYER)
        raises("judgment still running", w.escrow.reclaim, pid)
    assert w.transfers() == []


def test_reclaim_is_refused_by_a_stranger_and_on_an_undisputed_payment():
    w = World(dispute=10).wired()
    w.register()
    pid = w.pay()
    w.record(pid)
    w.sender(w.BUYER)
    raises("not disputed", w.escrow.reclaim, pid)
    w.dispute_it(pid)
    w.advance(11)
    for who in (w.STRANGER, w.OWNER):
        w.sender(who)
        raises("not a party", w.escrow.reclaim, pid)


def test_a_late_verdict_cannot_pay_a_reclaimed_payment_twice():
    """
    The whole point of the guard. A judgment that arrives after the unwind finds
    the payment RESOLVED and is refused by settle's own status check.
    """
    w = World(dispute=10).wired()
    w.register()
    pid = w.pay(amount=4 * ONE_GEN)
    w.record(pid)
    w.dispute_it(pid)
    w.advance(11)
    w.sender(w.BUYER)
    w.escrow.reclaim(pid)
    paid_once = sum(t.value for t in w.transfers())

    w.gl.message.sender_address = D.Address(w.DISPUTE)
    w.gl.bus.current = D.Address(w.ESCROW)
    raises("not disputed", w.escrow.settle, pid, D.u8(V_NOT_HONORED), "late")
    assert sum(t.value for t in w.transfers()) == paid_once
    w.check_invariants()


def test_a_seller_the_gate_refused_can_change_the_promise_and_ask_again():
    w = World().wired()
    w.register()
    w.gl.message.sender_address = D.Address(w.DISPUTE)
    w.gl.bus.current = D.Address(w.ESCROW)
    w.escrow.set_judgeable(w.SELLER, False)

    w.sender(w.BUYER, ONE_GEN)
    raises("promise not judgeable", w.escrow.pay, w.SELLER, "GET /quote")

    fresh = "Returns at least ten items, each with a title and a url, refreshed within ten seconds."
    w.sender(w.SELLER)
    w.escrow.update_promise(fresh)
    w.sender(w.SELLER)
    w.escrow.request_review()

    emitted = w.gl.bus.emissions[-1]
    assert emitted.method == "check_promise"
    assert emitted.to.lower() == w.DISPUTE.lower()
    assert emitted.args[1] == fresh, "the escrow sends its own stored promise"


def test_a_review_cannot_be_asked_for_twice_on_a_promise_already_ruled_on():
    """
    Somewhere to go must not mean asking the same question until the answer
    suits. The way back is to change the thing that was judged.
    """
    w = World().wired()
    w.register()
    w.sender(w.SELLER)
    w.escrow.request_review()

    # The ruling comes back. Only now is this promise recorded as reviewed.
    w.gl.message.sender_address = D.Address(w.DISPUTE)
    w.gl.bus.current = D.Address(w.ESCROW)
    w.escrow.set_judgeable(w.SELLER, False)

    w.sender(w.SELLER)
    raises("promise unchanged", w.escrow.request_review)

    w.sender(w.SELLER)
    w.escrow.update_promise("A different promise, stated with a number: at least three venues.")
    w.sender(w.SELLER)
    w.escrow.request_review()


def test_a_gate_ruling_that_never_arrives_does_not_burn_the_promise():
    """
    The dead end this method exists to remove, reintroduced by recording the
    review on the request rather than on the ruling. A gate transaction that
    fails for any reason would otherwise leave the seller unable to have that
    promise reviewed ever again, and changing it back would hash the same.
    """
    w = World().wired()
    w.register()
    w.sender(w.SELLER)
    w.escrow.request_review()
    w.gl.bus.emissions.clear()  # the ruling never lands

    w.sender(w.SELLER)
    w.escrow.request_review()
    assert w.gl.bus.emissions[-1].method == "check_promise"
    assert w.seller()["reviewed"] == "", "nothing was ruled, so nothing is recorded"


def test_request_review_needs_a_registration_a_wiring_and_no_live_payments():
    w = World()
    w.sender(w.STRANGER)
    raises("not registered", w.escrow.request_review)

    w.register()
    w.sender(w.SELLER)
    raises("dispute contract not set", w.escrow.request_review)

    w2 = World().wired()
    w2.register()
    w2.pay()
    w2.sender(w2.SELLER)
    raises("open payments", w2.escrow.request_review)


def test_the_seller_cannot_submit_a_promise_it_does_not_serve_under():
    """
    request_review takes no argument. The promise reviewed is the one in storage,
    so a seller cannot have a good promise judged and serve against another.
    """
    import inspect

    source = inspect.getsource(World().escrow_mod.RecourseEscrow.request_review)
    assert "def request_review(self) -> None:" in source
    assert "entry.promise" in source


# --- admin ----------------------------------------------------------------


def test_only_the_owner_may_wire_the_dispute_contract():
    w = World()
    for who in (w.SELLER, w.BUYER, w.STRANGER):
        w.sender(who)
        raises("not owner", w.escrow.set_dispute_contract, w.DISPUTE)


def test_the_dispute_contract_can_only_be_set_once():
    w = World()
    w.sender(w.OWNER)
    w.escrow.set_dispute_contract(w.DISPUTE)
    w.sender(w.OWNER)
    raises("dispute contract already set", w.escrow.set_dispute_contract, w.STRANGER)


def test_the_dispute_contract_cannot_be_the_zero_address():
    w = World()
    w.sender(w.OWNER)
    raises("zero address", w.escrow.set_dispute_contract, "0x" + "0" * 40)


# --- invariants and solvency ---------------------------------------------


def test_money_is_conserved_across_a_mixed_run():
    """
    Every path in one scenario: a quiet close, each of the three verdicts, and a
    payment still open. Whatever came in is either still held or was paid out.
    """
    w = World().wired()
    w.register()

    quiet = w.pay(amount=2 * ONE_GEN)
    honored = w.pay(amount=3 * ONE_GEN)
    refused = w.pay(amount=4 * ONE_GEN)
    unclear = w.pay(amount=5 * ONE_GEN)
    open_still = w.pay(amount=6 * ONE_GEN)

    for pid in (honored, refused, unclear):
        w.record(pid)
        w.dispute_it(pid)
    _settle(w, honored, V_HONORED)
    _settle(w, refused, V_NOT_HONORED)
    _settle(w, unclear, V_UNCLEAR)
    w.check_invariants()

    w.advance(301)
    w.sender(w.SELLER)
    w.escrow.withdraw(quiet)
    w.check_invariants()

    taken = (2 + 3 + 4 + 5 + 6) * ONE_GEN + 3 * ONE_GEN
    out = sum(t.value for t in w.transfers())
    assert out + int(w.escrow.held) == taken
    assert int(w.escrow.held) == 6 * ONE_GEN, "only the open payment is still held"
    assert w.payment(open_still)["status"] == ST_OPEN
    assert w.seller()["live"] == 1
    assert w.seller()["upheld"] == 1


def test_a_settled_payment_never_leaves_its_terminal_state():
    """Invariant one, driven from every direction that could move it."""
    w = World().wired()
    w.register()
    pid = w.pay()
    w.record(pid)
    w.dispute_it(pid)
    _settle(w, pid, V_UNCLEAR)
    assert w.payment(pid)["status"] == ST_RESOLVED

    w.sender(w.SELLER)
    raises("not open", w.escrow.withdraw, pid)
    w.sender(w.BUYER, ONE_GEN)
    raises("not open", w.escrow.open_dispute, pid)
    w.sender(w.SELLER)
    raises("not open", w.escrow.record_response, pid, "late", "sig")
    assert w.payment(pid)["status"] == ST_RESOLVED


# --- the contract's own shape --------------------------------------------


def test_no_model_call_reaches_the_escrow():
    """
    The money path must reproduce byte for byte on every validator. A mismatch
    is a deterministic violation, which opens a tribunal and can slash a leader.
    """
    source = (pathlib.Path(__file__).resolve().parents[2] / "contracts" / "escrow.py").read_text(
        encoding="utf-8"
    )
    for banned in ("exec_prompt", "run_nondet", "eq_principle", "nondet.web", "get_webpage"):
        assert banned not in source, f"{banned} must never appear in the escrow"


def test_every_write_checks_who_is_calling():
    """
    A static check over the source, so a write added later cannot be left
    ungated by omission - only on purpose, in a diff.
    """
    import ast

    path = pathlib.Path(__file__).resolve().parents[2] / "contracts" / "escrow.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    contract = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == "RecourseEscrow"
    )
    # register_seller writes only the caller's own row and is open on purpose:
    # anyone may list an endpoint. pay is open on purpose: anyone may buy.
    allowed_open = {"register_seller", "pay"}
    for node in contract.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        decorators = [ast.unparse(d) for d in node.decorator_list]
        if not any("public.write" in d for d in decorators):
            continue
        if node.name in allowed_open:
            continue
        body = ast.unparse(node)
        assert "sender_address" in body, f"{node.name} is a write that checks no caller"


def test_the_public_surface_is_exactly_the_specified_one():
    w = World()
    assert sorted(w.gl.public.views) == [
        "get_payment",
        "get_seller",
        "recent",
        "recent_rows",
        "stats",
    ]
    assert sorted(w.gl.public.writes) == [
        "open_dispute",
        "pay",
        "reclaim",
        "record_response",
        "register_seller",
        "request_review",
        "set_active",
        "set_dispute_contract",
        "set_judgeable",
        "settle",
        "update_promise",
        "withdraw",
    ]
    assert sorted(w.gl.public.payables) == ["open_dispute", "pay"]


def test_transaction_time_is_read_from_the_message_and_not_a_clock():
    w = World()
    w.at(1757009000)
    w.register()
    assert w.seller()["registered_at"] == 1757009000
    w.at(1800000000)
    pid = w.pay()
    assert w.payment(pid)["created_at"] == 1800000000


def test_the_iso_parser_accepts_the_shapes_a_node_can_send():
    w = World()
    seconds = w.escrow_mod._seconds
    assert seconds("1970-01-01T00:00:00Z") == 0
    assert seconds("2026-09-04T18:20:00Z") == 1788546000
    assert seconds("2026-09-04T18:20:00+00:00") == 1788546000
    assert seconds("2026-09-04T18:20:00") == 1788546000, "a naive stamp is read as UTC"
    assert seconds("2026-09-04T19:20:00+01:00") == 1788546000
    assert seconds(" 2026-09-04T18:20:00Z ") == 1788546000


if __name__ == "__main__":
    import sys as _sys

    failures = []
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for name, fn in tests:
        try:
            fn()
        except Exception as error:  # noqa: BLE001
            failures.append(f"{name}: {error}")
    print(f"{len(tests) - len(failures)}/{len(tests)} escrow tests passed")
    for line in failures:
        print("  FAIL", line)
    _sys.exit(1 if failures else 0)
