"""
A dry run of the judge: the frozen contract's own judge(), one model, no chain.

    dry_run(promise, request, response, timing=None, model=None) -> dict
    answer(payload, model=None) -> (status, body)     one /judge request

The contracts are frozen, so the judgment prompt cannot be lifted into a shared
module. What can be done is to run the contract's own code: contracts/dispute.py
is loaded through the same double the direct tests use, its gl.nondet.exec_prompt
is pointed at the linter's model backend, and judge() runs unchanged, both
presentation orders, the one retry on a malformed answer, and the resolution of
a disagreement to unclear. Nothing here paraphrases the judge.

That is why production code reaches into tests/direct: the double there is the
only thing that can import a GenVM contract on plain CPython, and using it is
what keeps this a dry run of the deployed code rather than a reimplementation.

It is still one model where the chain uses a committee of five. Every consumer
labels the result a dry run, no money, no consensus.
"""

from __future__ import annotations

import datetime
import pathlib
import sys
import time
import types

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests" / "direct"))

from linter.service import Model, ModelUnavailable, default_model  # noqa: E402

#: The longest any one of the three strings may be. The escrow caps the
#: response at 4000 and refuses more, so nothing longer could ever have been
#: judged on chain and there is no point asking a model about it.
MAX_STRING = 4000


def _load() -> tuple[types.ModuleType, object]:
    import genvm_double as double  # noqa: PLC0415
    import harness  # noqa: PLC0415

    gl = double.GL()
    module = harness.load("dispute", gl)
    return module, gl


def timing_now(clock: datetime.datetime | None = None) -> str:
    """
    The timing block the escrow would have written, with now as both stamps.

    A dry run has no chain record of when the response arrived, so freshness
    is judged against the moment of the check, and the reply says so.
    """
    moment = (clock or datetime.datetime.now(datetime.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"Request recorded on chain at {moment}. Response recorded on chain at {moment}."


def dry_run(
    promise: str,
    request: str,
    response: str,
    timing: str | None = None,
    model: Model | None = None,
) -> dict:
    """
    {"verdict": ..., "reason": ..., "agreed": "yes"|"no"}, exactly what judge()
    returns on chain. Raises ModelUnavailable with no model and ValueError when
    the model never produced a usable verdict.
    """
    module, gl = _load()
    asked = model if model is not None else default_model()
    gl.nondet.exec_prompt = lambda prompt, **_config: asked.ask(prompt)
    try:
        return module.judge(promise, request, response, timing or timing_now())
    except ModelUnavailable:
        raise
    except gl.vm.UserError as error:  # type: ignore[attr-defined]
        message = getattr(error, "message", str(error))
        raise ValueError(message) from error


def answer(payload: dict, model: Model | None = None) -> tuple[int, dict]:
    """
    One /judge request as a status and a body. linter/serve.py answers /judge
    through this locally and api/judge.py answers /api/judge through it on
    Vercel, so the clerk gets the same shape from either and the checks live in
    one place.

    One model where the chain uses a committee of five, and no chain at all, so
    every answer carries recorded_on_chain false. Nothing here is a verdict; it
    is what one model says the verdict would be.
    """
    strings = {name: payload.get(name) for name in ("promise", "request", "response")}
    for name, value in strings.items():
        if not isinstance(value, str) or not value.strip():
            return 400, {"error": f"{name} must be a non-empty string"}
        if len(value) > MAX_STRING:
            return 413, {"error": f"{name} is longer than the contract accepts"}
    # The chain writes the timing block, and a committed case carries the one
    # it was judged against. Without it a case from last week is judged against
    # this second's clock, and anything with a freshness bound comes back not
    # honored however good it was. A caller that sends none gets now, and the
    # reply says which was used.
    timing = payload.get("timing")
    if timing is not None and (not isinstance(timing, str) or len(timing) > MAX_STRING):
        return 400, {"error": "timing must be a string the contract would accept"}
    supplied = bool(timing and timing.strip())
    started = time.time()
    try:
        result = dry_run(
            strings["promise"], strings["request"], strings["response"],
            timing=timing if supplied else None, model=model,
        )
    except ModelUnavailable as error:
        return 503, {"error": str(error)}
    except ValueError as error:
        return 502, {"error": f"the model gave no usable answer: {error}"}
    return 200, {
        "verdict": result["verdict"],
        "reason": result["reason"],
        # judge() asks in both presentation orders and resolves a disagreement
        # to unclear in the value. Whether the two agreed is the interesting
        # part, so it is not swallowed here.
        "agreed": result.get("agreed", ""),
        "seconds": round(time.time() - started, 1),
        "recorded_on_chain": False,
        "timing_from": "the case" if supplied else "the clock now",
        "dry_run": "The frozen contract's own judge(), one model, no chain and no money.",
    }
