"""
docs/SCRIPT.md is read aloud and filmed, and every number in it comes from
somewhere in this repository: the frozen record, the seller's stale mode, the
agent's default payment, and the evaluation results and snapshot of the network
the take is on. A number that drifts from its source goes wrong on camera,
where nothing fails. These hold each one to where it comes from, the way
tests/direct/test_design.py holds docs/DESIGN.md.
"""

from __future__ import annotations

import json
import pathlib
import re

from shared.chain import settlement_moves

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = " ".join((ROOT / "docs" / "SCRIPT.md").read_text(encoding="utf-8").split())
FROZEN = json.loads((ROOT / "contracts" / "FROZEN.json").read_text(encoding="utf-8"))

#: The network the take is on is the one its footer shot names.
FOOTER = re.search(r"footer's `([a-z-]+) / chain (\d+)`", SCRIPT)
assert FOOTER, "docs/SCRIPT.md no longer names its network in the footer shot"
NETWORK = FOOTER.group(1)
SUFFIX = "" if NETWORK == "studionet" else f".{NETWORK}"
RESULTS = json.loads((ROOT / "eval" / f"results{SUFFIX}.json").read_text(encoding="utf-8"))
HELD_OUT = json.loads((ROOT / "eval" / f"results-v2{SUFFIX}.json").read_text(encoding="utf-8"))
SNAPSHOT = "snapshot.json" if NETWORK == "studionet" else f"snapshot-{NETWORK}.json"
TOTALS = json.loads((ROOT / "evidence" / SNAPSHOT).read_text(encoding="utf-8"))["totals"]

WORDS = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
)
GEN = 10**18


def code(path: str, pattern: str) -> int:
    found = re.search(pattern, (ROOT / path).read_text(encoding="utf-8"))
    assert found, f"{path} no longer matches {pattern!r}"
    return int(found.group(1))


def shown(pattern: str) -> tuple[int, ...]:
    found = re.search(pattern, SCRIPT)
    assert found, f"docs/SCRIPT.md no longer says {pattern!r}"
    return tuple(int(group) for group in found.groups())


def test_every_number_the_video_shows_or_says_is_the_one_its_source_holds():
    stale_hours = code("seller/main.py", r"STALE_HOURS = (\d+)")
    amount = code("agent/run.py", r'"--amount", type=int, default=(\d+)')
    bond = int(FROZEN["bond_wei"]) // GEN
    on_screen = {
        "the stale price's age": (shown(r"stale: (\d+)s old"), (stale_hours * 3600,)),
        "the age a second over": (shown(r"The age reads (\d+)s instead"), (stale_hours * 3600 + 1,)),
        "the honest payment": (shown(r"paid (\d+) GEN, payment"), (amount,)),
        "the bond posted": (shown(r"bond (\d+) GEN posted"), (bond,)),
        "the settlement window": (shown(r"window \((\d+) s\)"), (FROZEN["window_seconds"],)),
        "the chain id": ((int(FOOTER.group(2)),), (FROZEN["deployments"][NETWORK]["chain_id"],)),
        "the four evaluation figures": (
            shown(r"Four numbers at the same size: `(\d+) / (\d+)`, `(\d+) / (\d+)`, `(\d+) / (\d+)`, `(\d+) / (\d+)`"),
            (
                RESULTS["accuracy"], RESULTS["n"], RESULTS["stability"], RESULTS["n"],
                RESULTS["unclear"], RESULTS["n"], HELD_OUT["accuracy"], HELD_OUT["n"],
            ),
        ),
        "the gate's reason cap": (
            shown(r"at most (\d+) characters"),
            (code("linter/service.py", r'"reason", ""\)\)\[:(\d+)\]'),),
        ),
    }
    if settlement_moves(NETWORK):
        on_screen["the refund, payment and bond"] = (shown(r"refund (\d+) GEN returned"), (amount + bond,))
    for name, (script, source) in on_screen.items():
        assert script == source, f"{name}: docs/SCRIPT.md shows {script}, the repository holds {source}"
    spoken = [
        f"a {WORDS[stale_hours]} hour old price",
        f"a {WORDS[bond]} GEN bond",
        f"{WORDS[TOTALS['committee']].capitalize()} validators",
        f"{WORDS[RESULTS['accuracy']]} of {WORDS[RESULTS['n']]}",
        f"{WORDS[HELD_OUT['accuracy']]} of {WORDS[HELD_OUT['n']]}",
    ]
    for words in spoken:
        assert words in SCRIPT, f"docs/SCRIPT.md no longer says {words!r}, which is what its source holds"


def test_the_script_says_what_happens_to_the_money_on_its_network():
    """
    Where the settlement moves, the take films the refund, and its amount is the
    payment and the bond. Where it does not, the script says so in those words,
    quotes the settlement line the agent really prints, and never shows or
    speaks a refund: implying one on that runtime is the failure this guards.
    """
    if settlement_moves(NETWORK):
        assert re.search(r"refund \d+ GEN returned", SCRIPT)
        return
    assert "on this runtime the settlement does not move" in SCRIPT
    assert not re.search(r"\brefund", SCRIPT, re.IGNORECASE), "the script mentions a refund its network cannot pay"
    assert "money back" not in SCRIPT
    line = "settlement not moved: the escrow still holds the payment and the bond"
    assert line in SCRIPT, "the script no longer quotes the settlement line"
    agent = " ".join((ROOT / "agent" / "run.py").read_text(encoding="utf-8").split())
    assert line in agent, "the script quotes a settlement line agent/run.py does not print"
