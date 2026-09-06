"""
The dry run runs the contract's judge(), not a paraphrase of it.

Two answers per run, one per presentation order, from a model double that
records what it was asked. What is asserted is the contract's own behaviour:
agreement returns the verdict, disagreement resolves to unclear in the value,
and a malformed answer is retried once.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from linter.judgment import dry_run, timing_now  # noqa: E402
from linter.service import ModelUnavailable, NoModel  # noqa: E402


class Scripted:
    def __init__(self, *answers: str):
        self.answers = list(answers)
        self.asked: list[str] = []
        self.calls = 0

    def ask(self, prompt: str) -> str:
        self.calls += 1
        self.asked.append(prompt)
        return self.answers.pop(0)


NOT = '{"verdict": "not_honored", "reason": "nine hours old"}'
HON = '{"verdict": "honored", "reason": "fresh"}'


def test_agreement_in_both_orders_returns_the_verdict():
    model = Scripted(NOT, NOT)
    out = dry_run("P", "R", "X", timing="T", model=model)
    assert out["verdict"] == "not_honored" and out["agreed"] == "yes"
    assert model.calls == 2
    # Both orders were asked and they are different prompts.
    assert model.asked[0] != model.asked[1]
    assert "P" in model.asked[0] and "X" in model.asked[0]


def test_disagreement_between_orders_resolves_to_unclear():
    model = Scripted(NOT, HON)
    out = dry_run("P", "R", "X", timing="T", model=model)
    assert out["verdict"] == "unclear" and out["agreed"] == "no"
    assert "Read one way this was not_honored, read the other way honored" in out["reason"]


def test_a_malformed_answer_is_retried_once_like_the_contract():
    model = Scripted("no json", NOT, NOT)
    out = dry_run("P", "R", "X", timing="T", model=model)
    assert out["verdict"] == "not_honored" and model.calls == 3


def test_two_malformed_answers_are_an_error_not_a_verdict():
    model = Scripted("prose", "prose", NOT)
    with pytest.raises(ValueError):
        dry_run("P", "R", "X", timing="T", model=model)


def test_no_model_raises():
    with pytest.raises(ModelUnavailable):
        dry_run("P", "R", "X", timing="T", model=NoModel())


def test_the_timing_block_names_now_as_both_stamps():
    import datetime

    fixed = datetime.datetime(2026, 9, 6, 12, 0, 0, tzinfo=datetime.timezone.utc)
    block = timing_now(fixed)
    assert block == "Request recorded on chain at 2026-09-06T12:00:00Z. Response recorded on chain at 2026-09-06T12:00:00Z."
