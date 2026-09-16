"""
docs/DESIGN.md states numbers about the page, and the page is code. A number
there goes false the day the code changes, and nothing fails: the linter's copy
button read "Copied" for 1.6 seconds while this file said 1.2, in a section it
called binding. These hold the numbers that have one literal source to that
source. The quoted copy is prose, and section 12 of the file lists what a
check by hand found there.
"""

from __future__ import annotations

import json
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


def test_studio_next_is_the_only_network_a_visitor_can_arrive_at():
    """
    The hackathon requires Studio Next. The site once read studionet when its
    address asked, and offered that address in its footer, its strip and its
    address cards: our own links took a judge to the wrong chain. Now a
    network in the address is redirected away, nothing on the page links to
    another network, and no environment variable can move the network or an
    address. studionet stays where it belongs, in the record: the footer names
    it with its chain, the first pair's addresses stay published as the record,
    and the evaluation keeps both columns.
    """
    web = ROOT / "web"
    networks = (web / "lib" / "networks.ts").read_text(encoding="utf-8")
    assert 'export const DEFAULT_NETWORK: NetworkName = "studio-next";' in networks
    assert "networkQuery" not in networks, "a helper for putting a network in the address is back"
    for name in ("lib/networks.ts", "lib/chain.ts", "lib/snapshot.ts", "app/page.tsx", "components/site/LaneCanvas.tsx"):
        source = (web / name).read_text(encoding="utf-8")
        assert "NEXT_PUBLIC_RECOURSE" not in source, f"web/{name} takes the network or an address from the environment"
    for path in [*web.joinpath("app").rglob("*.ts*"), *web.joinpath("components").rglob("*.tsx"), *web.joinpath("lib").glob("*.ts")]:
        text = path.read_text(encoding="utf-8")
        assert "?network=" not in text and "networkFor(" not in text, f"{path.relative_to(ROOT).as_posix()} still offers a network in the address"
    page = (web / "app" / "page.tsx").read_text(encoding="utf-8")
    assert 'permanentRedirect("/")' in page and "const network = DEFAULT_NETWORK;" in page
    assert "<ContractCards pairs={pairs} reading={network} />" in page, "one pair of addresses is no longer published"
    case = (web / "app" / "case" / "[id]" / "page.tsx").read_text(encoding="utf-8")
    assert "permanentRedirect(`/case/${id}`)" in case and "const network = DEFAULT_NETWORK;" in case
    footer = (web / "components" / "site" / "SiteFooter.tsx").read_text(encoding="utf-8")
    assert "Reading {network} / chain" in footer and "kept in the record" in footer and "<a href" not in footer.split("Also ran on")[1].split("</p>")[0]
    # The footer is the project's colophon, not a byline: the canvas's author
    # handle and its link to an article nobody published are both gone.
    assert "x.com" not in footer and "@meiti" not in footer, "the footer carries a personal handle again"
    cards = (web / "components" / "site" / "ContractCards.tsx").read_text(encoding="utf-8")
    assert "In the record" in cards and "href" not in cards
    frozen = json.loads((ROOT / "contracts" / "FROZEN.json").read_text(encoding="utf-8"))
    assert {"studio-next", "studionet"} <= set(frozen["deployments"]), "a network the page names has no deployment"


def test_the_mark_on_the_site_is_the_official_pack():
    """
    design/logo is the official mark: one path on a 32 unit grid, never inside
    a circle, and a wordmark in the serif at weight 600, all caps, never
    italic. The site drew a placeholder italic R inside a 1px circle in the
    navbar, the closing panel and the footer. Every one now draws the pack's
    path through components/site/Mark.tsx, and the favicon is the pack's.
    """
    web = ROOT / "web"
    pack = (ROOT / "design" / "logo" / "svg" / "mark-currentcolor.svg").read_text(encoding="utf-8")
    path = re.search(r'd="([^"]+)"', pack.split("</metadata>")[-1]).group(1)
    mark = (web / "components" / "site" / "Mark.tsx").read_text(encoding="utf-8")
    assert f'MARK_PATH = "{path}"' in mark, "the site's mark is not the pack's path"
    assert 'viewBox="0 0 32 32"' in mark and 'strokeLinecap="square"' in mark and "2.6" in mark and "3.4" in mark
    for name in ("SiteHeader.tsx", "SiteFooter.tsx", "Sections.tsx"):
        source = (web / "components" / "site" / name).read_text(encoding="utf-8")
        assert "<Mark " in source, f"{name} no longer draws the mark"
        assert ">R<" not in source and "\n                R\n" not in source, f"{name} draws the placeholder R again"
    assert (web / "app" / "icon.svg").read_bytes() == (ROOT / "design" / "logo" / "svg" / "favicon.svg").read_bytes()
    assert (web / "app" / "apple-icon.png").read_bytes() == (ROOT / "design" / "logo" / "png" / "apple-touch-icon-180.png").read_bytes()


def test_the_site_shows_no_api_the_repository_does_not_have():
    """
    The clerk's Integration section showed recourse.serve, recourse.pay,
    res.satisfies and res.contest: a wrapper nobody built, and the worst kind
    of claim, because it read as a shipped SDK. It is cut. So are the clerk's
    set mode, which was never built, and "in your browser", where the judge
    runs on the server. The curl call to /api/clerk is real and stays.
    """
    web = ROOT / "web"
    for path in [*web.joinpath("components").rglob("*.tsx"), *web.joinpath("app").rglob("*.tsx")]:
        text = path.read_text(encoding="utf-8")
        for name in ("recourse.serve", "recourse.pay", ".satisfies(", ".contest("):
            assert name not in text, f"{path.relative_to(ROOT).as_posix()} shows {name}, which nothing in the repository provides"
    clerk = (web / "components" / "site" / "Clerk.tsx").read_text(encoding="utf-8")
    for claim in ("run the whole committed set", "in your browser", "pinned per case"):
        assert claim not in clerk, f"the clerk says {claim!r} again, and the panel does not do it"
    assert "curl -s -X POST" in clerk and "/api/clerk" in clerk, "the real curl call to the clerk is gone"
