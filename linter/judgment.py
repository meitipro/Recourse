"""
A dry run of the judge: the frozen contract's own judge(), one model, no chain.

    dry_run(promise, request, response, timing=None, model=None) -> dict

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
import types

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests" / "direct"))

from linter.service import Model, ModelUnavailable, default_model  # noqa: E402


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
