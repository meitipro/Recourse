"""
docs/DESIGN.md states numbers about the page, and the page is code. A number
there goes false the day the code changes, and nothing fails: the linter's copy
button read "Copied" for 1.6 seconds while this file said 1.2, in a section it
called binding. These hold the numbers that have one literal source to that
source. The quoted copy is prose, and section 12 of the file lists what a
check by hand found there.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOC = (ROOT / "docs" / "DESIGN.md").read_text(encoding="utf-8")
DESIGN = " ".join(DOC.split())
HERO = (ROOT / "web" / "components" / "site" / "Hero.tsx").read_text(encoding="utf-8")
CHAIN = (ROOT / "web" / "lib" / "chain.ts").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "app" / "globals.css").read_text(encoding="utf-8")

SPELLED = {"ten": 10, "twenty": 20, "thirty": 30, "sixty": 60}


def said(pattern: str) -> float:
    found = re.search(pattern, DESIGN)
    assert found, f"docs/DESIGN.md no longer says {pattern!r}"
    value = found.group(1)
    return float(SPELLED.get(value, value))


def runs(source: str, pattern: str) -> int:
    found = re.search(pattern, source)
    assert found, f"the code no longer matches {pattern!r}"
    return int(found.group(1).replace("_", ""))


def test_the_timings_and_caps_in_design_md_are_the_ones_the_page_runs_on():
    pairs = {
        "the rewrite's Copy label, in ms": (
            said(r'reads "Copied" for (\d+(?:\.\d+)?) seconds') * 1000,
            runs(HERO, r"setSugCopied\(false\), ([\d_]+)\)"),
        ),
        "an address's COPIED tip, in ms": (
            said(r"COPIED tip shows for (\d+(?:\.\d+)?) seconds") * 1000,
            runs(HERO, r'setCopied\(""\), ([\d_]+)\)'),
        ),
        "the linter's ceiling, in ms": (
            said(r"a hard (\d+) second ceiling") * 1000,
            runs(HERO, r"controller\.abort\(\), ([\d_]+)\)"),
        ),
        "the feed's wait on the chain, in ms": (
            said(r"for at most (\w+) seconds") * 1000,
            runs(CHAIN, r"LIVE_DEADLINE_MS = ([\d_]+)"),
        ),
        "the box's cap": (said(r"takes at most (\d+) characters"), runs(HERO, r"maxLength=\{(\d+)\}")),
        "the counter's limit": (
            said(r"reads against the (\d+) the contract stores"),
            runs(HERO, r"text\.length\} / (\d+)`"),
        ),
    }
    for name, (stated, code) in pairs.items():
        assert round(stated) == code, f"{name}: docs/DESIGN.md says {stated:g}, the page runs on {code}"


def luminance(value: str) -> float:
    channels = [int(value[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def test_the_token_table_is_globals_css_and_its_contrast_figures_follow_from_it():
    stated = dict(re.findall(r"\| `(--[a-z0-9-]+)`(?: / `--[a-z0-9-]+`)? \| `(#[0-9a-f]{6})` \|", DOC))
    start = CSS.index(":root")
    defined = dict(re.findall(r"(--[a-z0-9-]+):\s*(#[0-9a-f]{6});", CSS[start : CSS.index("}", start)]))
    assert len(stated) >= 14, f"the token tables in docs/DESIGN.md were not found: {stated}"
    for token, value in stated.items():
        assert defined.get(token) == value, f"{token} is {defined.get(token)} in globals.css and {value} in docs/DESIGN.md"

    def contrast(front: str, back: str) -> str:
        light, dark = sorted((luminance(defined[front]), luminance(defined[back])), reverse=True)
        return f"{(light + 0.05) / (dark + 0.05):.2f}:1"

    assert f"{contrast('--dim', '--ground')} on ground, {contrast('--dim', '--panel')} on panel" in DESIGN
    assert f"`--muted`, {contrast('--muted', '--ground')} on ground and {contrast('--muted', '--panel')} on panel" in DESIGN


def test_a_verdict_wears_one_colour_wherever_the_page_names_it():
    """
    The upheld tile counts not honored verdicts and was green while the badge
    for the same verdict one screen below was red, and the clerk named honored
    in a solid accent fill while the table named it green. Same fact, two
    colours. The badges in the feed's table are the reference.
    """
    feed = (ROOT / "web" / "components" / "site" / "FeedPanel.tsx").read_text(encoding="utf-8")
    clerk = (ROOT / "web" / "components" / "site" / "Clerk.tsx").read_text(encoding="utf-8")

    def badge(verdict: str) -> str:
        found = re.search(r'verdict === "' + verdict + r'"\) \{\s*return \{ \.\.\.PILL, color: "(#[0-9A-F]{6})"', feed)
        assert found, f"the feed's {verdict} badge colour was not found"
        return found.group(1)

    tile = re.search(r'stat3Color: known \? "(#[0-9A-F]{6})"', feed)
    assert tile and tile.group(1) == badge("not_honored"), "the not honored tile must wear the not honored badge's colour"
    disputes = re.search(r'stat2Color: known \? "(#[0-9A-F]{6})"', feed)
    assert disputes and disputes.group(1) not in {badge("honored"), badge("not_honored")}, "disputes opened mixes states and names none"
    for verdict, label in (("honored", "Honored"), ("not_honored", "Not honored")):
        chip = re.search(r'color: "(#[0-9A-F]{6})"[^>]*>' + label + "</span>", clerk)
        assert chip and chip.group(1) == badge(verdict), f"the clerk's {label} chip is not the colour of the {verdict} badge"


def test_the_boot_screen_names_only_what_the_page_did():
    """
    The canvas's boot screen stepped "Reading eval/cases.json - case 07 of 18"
    past on a 44 millisecond clock while nothing was read. The port says "Read
    from" for what the server read to render the page, steps through the ids it
    read, waits on the fonts and the lane for the two labels that name them,
    and cannot trap the page.
    """
    site = ROOT / "web" / "components" / "site"
    boot = (site / "Boot.tsx").read_text(encoding="utf-8")
    code = re.sub(r"^\s*//.*$", "", re.sub(r"/\*.*?\*/", "", boot, flags=re.S), flags=re.M)
    lane = (site / "LaneCanvas.tsx").read_text(encoding="utf-8")
    page = (ROOT / "web" / "app" / "page.tsx").read_text(encoding="utf-8")
    assert "Reading " not in code, "a boot label says it is reading while only a clock runs"
    assert "Read from eval/cases.json - case ${cases[i]} of ${cases.length}" in code
    assert "cases.map((one) => one.id)" in page, "the ids the boot screen steps through are not the ones the page read"
    assert "Read from contracts/FROZEN.json" in code
    assert "await document.fonts" in code, "the fonts label no longer waits on the fonts"
    assert "await laneStarted" in code and lane.count("markStarted()") == 2, "the lane label no longer waits on the lane"
    assert "setTimeout(finish, 3600)" in code, "the failsafe that finishes the boot screen is gone"
    assert re.search(r"\.rc-boot \{ animation: rc-boot-out [^}]*4s forwards; \}", CSS), "nothing removes the boot screen when no script runs"
    # The label names three families. The page's inline styles ask for
    # 'Source Serif 4' and 'Work Sans', while fontsource's variable packages
    # register them as 'Source Serif 4 Variable' and 'Work Sans Variable', so
    # globals.css answers the names the page uses with the same files. Geist
    # Mono's package registers the name the page uses.
    assert "Loading Source Serif 4, Work Sans, Geist Mono" in code
    for family in ("Source Serif 4", "Work Sans"):
        assert re.search(r'@font-face \{[^}]*font-family: "' + family + r'";', CSS), f"no face answers to {family!r}"
