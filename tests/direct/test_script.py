"""
docs/SCRIPT.md is read aloud and filmed, and every number in it comes from
somewhere in this repository: the frozen record, the seller's stale mode, the
agent's default payment, the evaluation results, the snapshot. A number that
drifts from its source goes wrong on camera, where nothing fails. These hold
each one to where it comes from, the way tests/direct/test_design.py holds
docs/DESIGN.md.
"""

from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = " ".join((ROOT / "docs" / "SCRIPT.md").read_text(encoding="utf-8").split())
FROZEN = json.loads((ROOT / "contracts" / "FROZEN.json").read_text(encoding="utf-8"))
RESULTS = json.loads((ROOT / "eval" / "results.json").read_text(encoding="utf-8"))
HELD_OUT = json.loads((ROOT / "eval" / "results-v2.json").read_text(encoding="utf-8"))
TOTALS = json.loads((ROOT / "evidence" / "snapshot.json").read_text(encoding="utf-8"))["totals"]

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
        "the bond posted": (shown(r"bond (\d+) GEN posted"), (bond,)),
        "the refund, payment and bond": (shown(r"refund (\d+) GEN returned"), (amount + bond,)),
        "the settlement window": (shown(r"window \((\d+) s\)"), (FROZEN["window_seconds"],)),
        "the chain id": (shown(r"studionet / chain (\d+)"), (FROZEN["deployments"]["studionet"]["chain_id"],)),
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
