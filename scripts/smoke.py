#!/usr/bin/env python3
"""
The hosted smoke tests, in one command, for after the three Vercel imports.

    python scripts/smoke.py
    python scripts/smoke.py --site https://recourse-site.vercel.app

Every failure this can find is a dashboard setting, so each check names the
setting that fixes it, chosen from what actually came back, and the person
running it should be the one who can change it. Most of these fail quietly on a
live site: the page loads and a panel says something reasonable. That is why
each check looks at what came back, not at whether anything answered.

Two checks spend model calls, a stage 2 lint and a dry run of the judge, once
direct and once through the site's clerk, a few cents in all. Nothing here
writes to the chain.

When every check passes, a section lists the sentences in this repository
written for a world with no hosting. They became false the moment these checks
started passing, and nothing else would say so.

The last section is printed whether the checks passed or not. It names what
this run did not prove and how to prove each by hand, because a script silent
about where it stops gets read as proving more than it does: a stale sentence,
one layer up.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Refused at stage 1, before any model: proves the function runs, not the key.
VAGUE = "Accurate market data."
#: Passes stage 1, so the answer comes from stage 2: proves the key reached the linter.
SPECIFIC = "Prices aggregated from at least three venues, refreshed within five seconds."
VERDICTS = ("honored", "not_honored", "unclear")

#: What a page says when it was served from the recorded snapshot rather than a
#: read of the chain: the feed's notice, and the case page's.
RECORDED = "Recorded snapshot, not a live read"
#: The feed's notice when it did read the chain.
LIVE = "Chain, reading the escrow contract"

#: Sentences written for a world with no hosted services. True until the
#: imports land, false the hour they do, and nothing fails when they become so.
UNHOSTED = [
    ("README.md", "run locally today"),
    ("README.md", "are a dashboard step for the account owner"),
    ("docs/SCRIPT.md", "if the imports are done"),
]

LINTER_SETUP = "recourse-linter is not serving its functions: framework preset Other (not Python, not Next.js), root directory the repository root, then redeploy."
KEY = "ANTHROPIC_API_KEY is missing on recourse-linter, or set for Preview only: add it for Production and redeploy."


def call(method: str, url: str, body: dict | None = None, timeout: int = 120) -> tuple[int, str, float]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json", "User-Agent": "recourse-smoke"},
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            first = time.time() - started
            return response.status, response.read().decode("utf-8", "replace"), first
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace"), time.time() - started
    except Exception as error:  # noqa: BLE001 - reported as the check's result
        return 0, f"{type(error).__name__}: {error}", time.time() - started


def parsed(raw: str) -> dict:
    try:
        value = json.loads(raw)
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def visible(html: str) -> str:
    """
    The page's text as a reader sees it. React separates adjacent text nodes
    with comment markers and wraps words in inline tags, so "fixed bond of 1
    GEN" is on the page and not in the HTML. A raw grep calls that page broken.
    """
    return re.sub(r"<[^>]+>", "", re.sub(r"<!--.*?-->", "", html, flags=re.S))


def short(raw: str) -> str:
    flat = " ".join(raw.split())
    return flat[:140] + (" ..." if len(flat) > 140 else "")


def committed_case() -> dict:
    """Case 01 from the committed set, with the timing block it was judged against."""
    cases = json.loads((ROOT / "eval" / "cases.json").read_text(encoding="utf-8"))
    first = cases[0]
    return {key: first[key] for key in ("promise", "request", "response", "timing")}


def judged(code: int, body: dict) -> bool:
    return code == 200 and body.get("verdict") in VERDICTS and body.get("recorded_on_chain") is False


def run(site: str, linter: str, mcp: str) -> tuple[list[tuple[str, bool]], list[tuple[str, str]]]:
    lint_url = f"{linter}/api/lint"
    results: list[tuple[str, bool]] = []
    unread: list[str] = []

    def record(name: str, ok: bool, detail: str, fix: str) -> bool:
        results.append((name, ok))
        print(f"  {'PASS' if ok else 'FAIL'}  {name:48} {detail}")
        if not ok:
            print(f"        fix: {fix}")
        return ok

    code, raw, _ = call("POST", lint_url, {"promise": VAGUE})
    body = parsed(raw)
    record(
        "linter answers stage 1 without a model",
        code == 200 and body.get("judgeable") is False and body.get("failed_check") == "no measurable term" and body.get("stage") == 1,
        f"HTTP {code} {short(raw)}",
        LINTER_SETUP,
    )

    code, raw, _ = call("POST", lint_url, {"promise": SPECIFIC})
    body = parsed(raw)
    stage2 = record(
        "linter reaches stage 2, so the key is there",
        code == 200 and body.get("stage") == 2,
        f"HTTP {code} {short(raw)}",
        LINTER_SETUP if code in (0, 404) else KEY + " A vague promise cannot show this: stage 1 refuses it before any model is asked.",
    )

    case = committed_case()
    code, raw, _ = call("POST", f"{linter}/api/judge", case, timeout=150)
    body = parsed(raw)
    judge = record(
        "linter answers /api/judge, the clerk's judge",
        judged(code, body),
        f"HTTP {code} {short(raw)}",
        "The deployment predates api/judge.py, or the preset is wrong: redeploy recourse-linter from main with preset Other."
        if code in (0, 404) else KEY if code == 503 else "The judge answered without a verdict: read the body above.",
    )

    code, raw, first = call("GET", f"{site}/", timeout=60)
    record(
        "site answers",
        code == 200,
        f"HTTP {code}, first byte {first:.2f}s" + ("" if first < 2 else " (slow: a cold start, or the chain read is holding the page)"),
        "recourse-site is not serving: root directory web, framework Next.js, then redeploy.",
    )
    text = visible(raw)
    record(
        "site shipped the files outside web/",
        "The number, published whatever it is" in text and "fixed bond of" in text,
        "evaluation section and the bond both rendered" if code == 200 else f"HTTP {code}",
        "Include source files outside the root directory is off on recourse-site: the results files and FROZEN.json did not ship, "
        "so the evaluation section is missing and the bond is unnamed. Turn it on and redeploy.",
    )
    if code == 200 and RECORDED in text:
        unread.append("the feed came from the recorded snapshot")
    elif code == 200 and LIVE not in text:
        unread.append("the feed did not read the chain")

    code, raw, _ = call("POST", f"{site}/api/lint", {"promise": "High quality results."})
    body = parsed(raw)
    record(
        "site reaches the linter through LINTER_URL",
        code == 200 and body.get("judgeable") is False,
        f"HTTP {code} {short(raw)}",
        f"LINTER_URL is missing on recourse-site: set it to {lint_url} and redeploy."
        if "not configured" in str(body.get("error", "")) else f"The site cannot reach the linter: LINTER_URL must be exactly {lint_url}.",
    )

    code, raw, _ = call("POST", f"{site}/api/clerk", case, timeout=180)
    body = parsed(raw)
    error = str(body.get("error", ""))
    if "not configured" in error:
        fix = f"LINTER_URL is missing on recourse-site: set it to {lint_url} and redeploy."
    elif "reach the clerk" in error:
        fix = "The clerk derives its judge by turning LINTER_URL's /api/lint into /api/judge: LINTER_URL must end in /api/lint, and the /api/judge check above must pass."
    elif code == 429:
        fix = "Rate limited by the clerk's own limit: wait a minute and run this again."
    elif code in (502, 503):
        fix = "The clerk reached the judge and the judge has no model. " + KEY
    else:
        fix = "The clerk answered without a verdict: read the body above."
    clerk = record("site's clerk reaches the judge", judged(code, body), f"HTTP {code} {short(raw)}", fix)

    code, raw, _ = call("GET", f"{site}/case/RC-2026-0003", timeout=60)
    shown = visible(raw)
    record(
        "site renders a case permalink",
        code == 200 and "not honored" in shown,
        f"HTTP {code}",
        "The case page did not render p-000003: leave NEXT_PUBLIC_RECOURSE_NETWORK unset or studionet, and check the outside root switch, "
        "which also ships evidence/snapshot.json for when the chain is slow.",
    )
    if code == 200 and RECORDED in shown:
        unread.append("the case page came from the recorded snapshot")

    probe = ROOT.parent / "recourse-skill" / "mcp" / "test" / "probe.mjs"
    node = shutil.which("node")
    mcp_ran = bool(node and probe.exists())
    if mcp_ran:
        try:
            finished = subprocess.run(
                [node, str(probe), mcp], cwd=probe.parent.parent, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=300,
            )
            tail = (finished.stdout.strip().splitlines() or [finished.stderr.strip()[:140]])[-1]
            ok = finished.returncode == 0
        except subprocess.TimeoutExpired:
            ok, tail = False, "the probe did not finish in five minutes"
        record(
            "MCP answers every tool",
            ok,
            short(tail),
            "recourse-mcp is not answering: root directory mcp, framework Next.js, LINTER_URL set, and the project named exactly "
            "recourse-mcp, or the skill's addresses file and plugin manifest point at nothing.",
        )
    else:
        print(f"  SKIP  MCP answers every tool                          run by hand: cd recourse-skill/mcp && node test/probe.mjs {mcp}")
    return results, blind_spots(stage2 or judge or clerk, unread, mcp_ran, mcp)


def blind_spots(key_proven: bool, unread: list[str], mcp_ran: bool, mcp: str) -> list[tuple[str, str]]:
    """
    What a run did not prove, each with the way to prove it by hand.

    The bot and the key's spend limit are out of reach every run. The key, the
    site's own read of the chain and the MCP server are listed only when this
    run left them unproven, because a line calling a proven thing unproven is
    as stale as the sentences this script hunts.
    """
    spots = [
        (
            "the bot",
            "not hosted by any of these three projects, so nothing here reached it, and its host needs a key of its own, "
            "because it runs the linter in its own process. Once it runs: a plain question in a direct message must get an "
            "answer rather than the reply that free text has no model, and in a group it must answer only when named.",
        ),
        ("the key's spend limit", "no request can see one. Set it, and read it back, in the Anthropic console."),
    ]
    if not key_proven:
        spots.append((
            "the model key",
            "nothing above proves it. Only a promise that reaches stage 2, or the clerk returning a verdict, can: "
            "a vague promise is refused at stage 1 before any model is asked, key or no key.",
        ))
    if unread:
        spots.append((
            "the site's own read of studionet",
            f"{' and '.join(unread)}, so this run never saw the server read the chain. Run it again in a minute: "
            "a page still saying so means the server cannot reach studionet.",
        ))
    if not mcp_ran:
        spots.append(("the MCP server", f"the probe was skipped. Run it by hand: cd recourse-skill/mcp && node test/probe.mjs {mcp}"))
    return spots


def unhosted_sentences() -> list[str]:
    found = []
    for name, phrase in UNHOSTED:
        path = ROOT / name
        if not path.exists():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if phrase in line:
                found.append(f"{name}:{number}  {line.strip()[:110]}")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site", default="https://recourse-site.vercel.app")
    parser.add_argument("--linter", default="https://recourse-linter.vercel.app")
    parser.add_argument("--mcp", default="https://recourse-mcp.vercel.app/api/mcp")
    args = parser.parse_args()
    site, linter = args.site.rstrip("/"), args.linter.rstrip("/")

    print(f"recourse smoke  site {site}  linter {linter}  mcp {args.mcp}\n")
    results, spots = run(site, linter, args.mcp)
    passed = sum(1 for _, ok in results if ok)
    print(f"\n{passed} of {len(results)} passed")
    if passed == len(results):
        stale = unhosted_sentences()
        if stale:
            print("\nEverything is live, so these sentences are now false. Fix them before submitting:")
            for row in stale:
                print(f"  {row}")

    print("\nNot proven by this run, and how to prove each by hand:")
    for what, how in spots:
        print(f"  {what}: {how}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
