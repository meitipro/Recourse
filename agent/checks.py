"""
The buyer agent's checks. Deterministic and deliberately dumb.

Three checks, no model call, no cleverness. It would be easy to have the agent
ask a model whether the response was good; that would make the demo show an
agent's opinion rather than the network's verdict, and a judge would notice. The
agent detects a mismatch with hardcoded checks and the actual judgment happens in
consensus, where neither party chose the judge.

Never raises. A check that throws on a malformed body would be a way for a seller
to stop the agent contesting.
"""

from __future__ import annotations

import datetime
import typing


class Verdict(typing.NamedTuple):
    ok: bool
    reason: str
    #: Which failure mode this is, when it is one: stale, hollow or substituted.
    #: Also "declined", which is not a failure mode and must never be contested.
    mode: str

    @property
    def contestable(self) -> bool:
        """
        Whether this is worth a bond.

        Not the same question as `ok`. An endpoint that refused a request the
        promise never covered has not honoured anything and has not broken
        anything either, so there is nothing for a committee to rule on.
        """
        return not self.ok and self.mode != "declined"


def _parse_ts(value: typing.Any) -> datetime.datetime | None:
    """
    UTC, always, with an explicit tzinfo.

    Comparing a naive datetime against an aware one raises, and comparing two
    naive ones across a timezone boundary silently gives the wrong age. Both
    failures look like the agent not noticing a stale response.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.astimezone(datetime.timezone.utc)


def check(
    body: typing.Any,
    requested_pair: str,
    max_age_s: int,
    min_sources: int,
    now: datetime.datetime | None = None,
) -> Verdict:
    """
    Returns (ok, reason, mode). Never raises.

    `now` is injectable so a test can pin the clock. Left out, it is the real
    current time in UTC.
    """
    moment = now or datetime.datetime.now(datetime.timezone.utc)

    if not isinstance(body, dict) or not body:
        return Verdict(False, "empty body", "hollow")

    # An endpoint saying plainly that it cannot serve this request is not a
    # breach, and contesting it is how a client manufactures a false dispute.
    # Without this branch a refusal falls through to the price check, comes back
    # "hollow: no price", and the agent contests an endpoint that did nothing
    # wrong. The promise governs what was promised; a request outside it was
    # never covered, so there is nothing here to rule on and the buyer picked
    # the pair.
    if isinstance(body.get("error"), str) and body.get("price") is None:
        return Verdict(
            False,
            f"declined: {body['error']}, which the promise never covered",
            "declined",
        )

    if "results" in body and len(body.get("results") or []) == 0:
        return Verdict(False, "hollow: empty result set", "hollow")

    pair = body.get("pair")
    if isinstance(pair, str) and pair and pair != requested_pair:
        return Verdict(
            False, f"substituted: asked {requested_pair}, got {pair}", "substituted"
        )

    price = body.get("price")
    if price is None or price == "" or price == 0:
        return Verdict(False, "hollow: no price", "hollow")
    if not isinstance(price, (int, float)):
        return Verdict(False, f"hollow: price is not a number, got {price!r}", "hollow")

    stamp = _parse_ts(body.get("ts"))
    if stamp is None:
        return Verdict(False, "no usable timestamp", "stale")
    age = int((moment - stamp).total_seconds())
    if age > max_age_s:
        return Verdict(
            False, f"stale: {age}s old, promise allows {max_age_s}s", "stale"
        )

    sources = body.get("sources")
    if not isinstance(sources, int) or sources < min_sources:
        return Verdict(
            False, f"sources: {sources} against a floor of {min_sources}", "hollow"
        )

    return Verdict(True, "ok", "")
