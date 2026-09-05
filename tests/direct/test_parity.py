"""
Anything the repository states twice has to be checked against itself.

The feed maps the contracts' status and verdict codes to words, in TypeScript,
from memory. That is a second implementation of a table the contracts own, and
a second implementation drifts: the one project without a parity check was the
one where a module presented as "the rules, lifted out to be copied" kept an
unfenced prompt builder after the contract was fixed.

So this parses both sides and compares them. It is deliberately not a copy of
either table, because a copy would be a third implementation to be wrong in its
own way.
"""

from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from harness import World  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _contract_codes(module, prefix: str) -> dict:
    """The constants the contract actually defines, read off the loaded module."""
    return {
        name[len(prefix):].lower(): int(value)
        for name, value in vars(module).items()
        if name.startswith(prefix) and isinstance(value, int)
    }


def test_the_feed_and_the_contract_agree_on_the_verdict_codes():
    w = World().with_dispute()
    codes = _contract_codes(w.escrow_mod, "V_")
    assert codes == {"none": 0, "honored": 1, "not_honored": 2, "unclear": 3}

    feed = (ROOT / "web" / "components" / "Feed.tsx").read_text(encoding="utf-8")
    match = re.search(r"const VERDICT = \[(.*?)\] as const;", feed, re.S)
    assert match, "the feed no longer declares a VERDICT table, so this check is dead"
    names = [piece.strip().strip('"') for piece in match.group(1).split(",") if piece.strip()]

    # Index in the array must be the code the contract stores.
    for name, code in codes.items():
        expected = "pending" if name == "none" else name
        assert names[code] == expected, (
            f"the feed calls code {code} {names[code]!r}, the contract calls it {expected!r}"
        )
    assert len(names) == len(codes)


def test_the_feed_and_the_contract_agree_on_the_status_codes():
    w = World()
    codes = _contract_codes(w.escrow_mod, "ST_")
    assert codes == {"open": 0, "withdrawn": 1, "disputed": 2, "resolved": 3}

    feed = (ROOT / "web" / "components" / "Feed.tsx").read_text(encoding="utf-8")
    # The feed branches on the numbers directly rather than naming them, so what
    # is checked is that every code the contract can store is handled.
    handled = {int(n) for n in re.findall(r"row\.status === (\d)", feed)}
    unhandled = set(codes.values()) - handled
    assert not unhandled - {0}, (
        f"the feed has no branch for status code(s) {sorted(unhandled)}; "
        "0 is allowed because it is the fall-through"
    )


def test_the_dispute_contract_and_the_escrow_agree_on_the_verdict_codes():
    """
    Both contracts declare the table. They are deployed separately, so a change
    to one is not a change to the other, and a verdict code that means different
    things in the two halves would move money the wrong way with nothing to say
    it had.
    """
    w = World().with_dispute()
    escrow = _contract_codes(w.escrow_mod, "V_")
    dispute = _contract_codes(w.dispute_mod, "V_")
    assert escrow == dispute, f"escrow {escrow} against dispute {dispute}"

    # And the dispute contract's name table has to agree with its own codes.
    for name, code in dispute.items():
        if name == "none":
            continue
        assert w.dispute_mod.NAMES[code] == name
        assert w.dispute_mod.CODES[name] == code


def test_the_agent_and_the_feed_use_the_contract_ids_not_their_own():
    """The payment id shape is minted by the contract; nothing else invents one."""
    agent = (ROOT / "agent" / "run.py").read_text(encoding="utf-8")
    assert 'pid = paid["result"]' in agent, "the agent must use the id the contract returned"

    route = (ROOT / "web" / "app" / "api" / "evidence" / "route.ts").read_text(encoding="utf-8")
    assert "p-\d{6}" in route, "the evidence route must validate the contract's id shape"

    w = World()
    w.register()
    assert w.pay().startswith("p-")


if __name__ == "__main__":
    failures = []
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for name, fn in tests:
        try:
            fn()
        except Exception as error:  # noqa: BLE001
            failures.append(f"{name}: {type(error).__name__} {error}")
    print(f"{len(tests) - len(failures)}/{len(tests)} parity tests passed")
    for line in failures:
        print("  FAIL", line)
    sys.exit(1 if failures else 0)


# --- the simulator has to model the runtime it stands in for --------------


def test_the_double_compares_addresses_the_way_a_node_does():
    """
    A node compares twenty raw bytes. A simulator that compares hex strings
    case-sensitively passes a test the chain would fail, and the contract keys
    a TreeMap by Address, so a case difference would silently miss every lookup.
    """
    import genvm_double as D

    lower = D.Address("0x" + "ab" * 20)
    upper = D.Address("0x" + "AB" * 20)
    assert lower == upper
    assert hash(lower) == hash(upper)
    assert {lower: 1}[upper] == 1

    w = World()
    w.register(who="0x" + "ab" * 20)
    assert w.seller("0x" + "AB" * 20)["promise"] == w.PROMISE, (
        "a seller registered in one casing must be found in the other"
    )


def test_the_leader_and_the_validator_can_see_different_answers():
    """
    Every mocking framework feeds both nodes the same data by default, which is
    exactly why a contract that quietly assumes both see identical bytes passes
    its suite and fails on a real network. Here they draw from a queue
    separately, so they can and do differ, and the disagreement tests depend on
    it working that way.
    """
    import json as _json

    import genvm_double as D

    w = World().with_dispute()
    w.register()
    pid = w.pay()
    w.record(pid)
    w.dispute_it(pid)

    w.gl.nondet.answers = [
        _json.dumps({"verdict": "honored", "reason": "leader, both orders"}),
        _json.dumps({"verdict": "honored", "reason": "leader, both orders"}),
        _json.dumps({"verdict": "not_honored", "reason": "validator, both orders"}),
        _json.dumps({"verdict": "not_honored", "reason": "validator, both orders"}),
    ]
    try:
        w.gl.bus.deliver(w.gl)
    except D.VMError:
        pass
    else:
        raise AssertionError("two nodes reaching different verdicts must not agree")
    assert w.gl.bus.validator_votes == [False]
    assert len(w.gl.nondet.prompts) == 4
