#!/usr/bin/env python3
"""
docs/HAND-CHECK.md, regenerated: every number in the README and every link a
reader can click, laid out to be checked by hand, and the order a stranger
meets them in.

    python scripts/hand_check.py             links checked over the network
    python scripts/hand_check.py --offline   links on disk only, nothing fetched

The judging is by hand. Compiling the list is not, so this compiles it. Every
number in the README gets a row, in the order it appears, with the file it
comes from and what that file says now. A number with no single file behind it
says so in that column instead of guessing, and those rows are the ones worth
the closest reading. Every link in the README, both repositories' READMEs, the
skill's six reference files and docs/ gets a row with what it resolved to on
this run. The hosted URLs are grouped apart, because until the Vercel imports
they fail, and that is expected rather than a finding.

A number written as a word counts, since this README spells most of them out.
A bare "one" does not, because it is nearly always an article; "one of three"
does. List numbering, commit hashes, addresses and version strings inside
names are not numbers here.

It reads and never asserts. Nothing here fails, it is not part of
scripts/test.py, and it must not become a gate. Run it again rather than
editing what it writes.
"""

from __future__ import annotations

import argparse
import bisect
import concurrent.futures
import datetime
import functools
import json
import pathlib
import re
import subprocess
import sys
import typing
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT.parent / "recourse-skill"
OUT = ROOT / "docs" / "HAND-CHECK.md"
HOSTED = ".vercel.app"
NO_FILE = "no single file behind it"

sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def literal(rel: str, pattern: str, base: pathlib.Path = ROOT) -> str:
    found = re.search(pattern, read(base / rel))
    return found.group(1) if found else "not found"


def iso(epoch: int) -> str:
    return datetime.datetime.fromtimestamp(int(epoch), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp(text: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))


# --- what the files say now ----------------------------------------------------


class Sources:
    def __init__(self) -> None:
        self.readme = read(ROOT / "README.md")
        self.snapshot = json.loads(read(ROOT / "evidence" / "snapshot.json"))
        self.totals = self.snapshot["totals"]
        self.payments = {p["pid"]: p for p in self.snapshot["payments"]}
        self.r1 = json.loads(read(ROOT / "eval" / "results.json"))
        self.r2 = json.loads(read(ROOT / "eval" / "results-v2.json"))
        self.cases = {c["id"]: c for c in json.loads(read(ROOT / "eval" / "cases.json"))}
        self.cases2 = json.loads(read(ROOT / "eval" / "cases-v2.json"))
        self.frozen = json.loads(read(ROOT / "contracts" / "FROZEN.json"))
        self.feed = json.loads(read(ROOT / "docs" / "images" / "feed.json"))["tiles"]

    @property
    def committee(self) -> int:
        return int(self.totals["committee"])

    @functools.cached_property
    def direct_tests(self) -> str:
        collected = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/direct/", "--collect-only", "-q", "-p", "no:gltest", "-p", "no:gltest_direct"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stdout
        found = re.search(r"(\d+) tests? collected", collected)
        return f"pytest collects {found.group(1)}" if found else "pytest collected nothing readable"

    @functools.cached_property
    def prompts(self) -> tuple[int, int, int]:
        sys.path.insert(0, str(ROOT / "tests" / "direct"))
        from harness import World  # the direct tests' double, which loads the frozen contract

        module = World().with_dispute().dispute_mod
        sizes = [
            len(module.build_prompt(c["promise"], c["request"], c["response"], c["timing"], reverse=reverse))
            for c in self.cases.values()
            for reverse in (False, True)
        ]
        return min(sizes), max(sizes), int(round(sum(sizes) / len(sizes) / 4, -1))

    @functools.cached_property
    def script_end(self) -> str:
        rows = re.findall(r"(?m)^\| (\d:\d\d) to (\d:\d\d) \|", read(ROOT / "docs" / "SCRIPT.md"))
        return rows[-1][1] if rows else "not found"

    def row(self, pid: str) -> str:
        payment = self.payments.get(pid)
        if not payment:
            return f"{pid} is not in the snapshot"
        return f"{pid}: {payment['status_name']}, verdict {payment['verdict_name']}"

    def seller_promise(self, pid: str) -> str:
        payment = self.payments[pid]
        sellers = self.snapshot.get("sellers", {})
        entry = sellers.get(payment["seller"]) if isinstance(sellers, dict) else None
        return f'{pid}\'s seller promised "{entry["promise"]}"' if entry and "promise" in entry else "the promise is not in the snapshot"

    def stale(self, pid: str) -> str:
        payment = self.payments[pid]
        served = stamp(json.loads(payment["response"])["ts"])
        recorded = datetime.datetime.fromtimestamp(int(payment["responded_at"]), datetime.timezone.utc)
        hours = (recorded - served).total_seconds() / 3600
        return f"{pid}'s response is stamped {served:%Y-%m-%dT%H:%M:%SZ} and was recorded {iso(payment['responded_at'])}: {hours:.1f} hours"

    def case(self, number: str) -> str:
        entry = self.cases.get(number)
        return f"case {number}, expected {entry['expected']}: {entry['note']}" if entry else f"no case {number}"

    def case_age(self, number: str) -> str:
        entry = self.cases[number]
        served = stamp(json.loads(entry["response"])["ts"])
        recorded = stamp(re.search(r"Response recorded on chain at (\S+?)\.?$", entry["timing"]).group(1))
        return f"case {number}'s response is stamped {served:%H:%M:%S}, recorded {recorded:%H:%M:%S}: {int((recorded - served).total_seconds())} seconds; its promise says \"no more than five seconds old\""

    def held_out(self) -> str:
        return ", ".join(f"case {row['id']} {'correct' if row['correct'] else 'missed'}{', stable' if row.get('stable') else ''}" for row in self.r2["rows"])

    def cited_hashes(self) -> str:
        cited = set(re.findall(r"0x[0-9a-f]{64}", self.readme))
        snapshot = json.dumps(self.snapshot)
        return f"{len(cited)} transaction hashes cited in the README, {sum(1 for h in cited if h in snapshot)} of them in evidence/snapshot.json"

    def refusals(self) -> str:
        section = self.readme.split("### Refusals on chain", 1)[1].split("\n### ", 1)[0]
        cited = re.findall(r"0x[0-9a-f]{64}", section)
        recorded = json.dumps(self.snapshot.get("refusals", []))
        return f"{len(cited)} rows in the refusal table, {sum(1 for h in cited if h in recorded)} of them among the snapshot's {self.totals['refusals']} refusals"

    def transactions(self, pid: str) -> str:
        """The snapshot keeps a payment's transactions keyed by the method that sent them."""
        sent = self.payments[pid].get("transactions", {})
        steps = [name for name in ("pay", "record_response", "open_dispute", "adjudicate", "settle", "reclaim", "withdraw") if sent.get(name)]
        return f"{pid}'s transactions: {', '.join(steps)}, then {len(sent.get('payouts') or [])} payouts"

    def commit_files(self, commit: str) -> str:
        shown = subprocess.run(["git", "show", "--name-status", "--format=", commit], cwd=ROOT, capture_output=True, text=True).stdout.split()
        names = shown[1::2]
        return f"git show {commit}: {len(names)} files, {', '.join(names)}" if names else f"git has no {commit} here"

    def payment_fields(self) -> str:
        keys = set(next(iter(self.payments.values())).keys()) - {"status_name", "verdict_name", "transactions"}
        return f"{len(keys)} fields in a payment row as the chain returns it (the snapshot adds three names of its own)"

    def examples(self) -> str:
        from linter.examples import EXAMPLES
        from linter.rules import precheck

        passing = sum(1 for example in EXAMPLES if precheck(str(example.get("promise", ""))).ok)
        return f"{passing} of the {len(EXAMPLES)} examples pass stage 1 and need a model"

    def hosting_sections(self) -> str:
        sections = re.findall(r"(?m)^## \d\. (.+)$", read(ROOT / "docs" / "HOSTING.md"))
        return f"{len(sections)} numbered sections, one per import: {', '.join(sections)}"

    def receipts_policy(self) -> str:
        hits = [p for p in (ROOT / "evidence" / "receipts").rglob("*.json") if "qwen" in read(p) and re.search(r"0\.2\b", read(p))]
        return f"a policy naming qwen with a 0.2 floor appears in {len(hits)} receipt files"


# --- rules: which file each README number comes from ---------------------------

Value = typing.Union[str, typing.Callable[[Sources], str]]

#: (words that must be in the sentence, the number as written, which occurrence
#: in that sentence or 0 for any, the file, what the file says). First match wins.
RULES: list[tuple[str, str, int, str | None, Value]] = [
    (r"Python 3\.12", r"3\.12", 0, ".github/workflows/test.yml",
     lambda s: "python-version " + literal(".github/workflows/test.yml", r'python-version: "([^"]+)"')),
    (r"11 September", r"11", 0, None, "a date: the day the clean clone ran, which no file records"),
    (r"funds three accounts", r"three", 0, "scripts/prepare.py",
     lambda s: "funds " + ", ".join(re.findall(r'"(\w+)"', literal("scripts/prepare.py", r"for name, account in (\(\(.+?\)\)):")))),
    (r"price it served was nine hours old|the price was nine hours old|on the nine hour old price", r"nine", 0,
     "evidence/snapshot.json", lambda s: s.stale("p-000014")),
    (r"nine hour|nine hours", r"nine", 0, "seller/main.py", lambda s: "STALE_HOURS = " + literal("seller/main.py", r"STALE_HOURS = (\d+)")),
    (r"ninety second recording script", r"ninety", 0, "docs/SCRIPT.md", lambda s: f"its last shot ends at {s.script_end}"),
    (r"read from the chain when the page opened", r"nineteen", 0, "evidence/snapshot.json",
     lambda s: f"totals.payments = {s.totals['payments']}; docs/images/feed.json shows {s.feed.get('Payments')}"),
    (r"read from the chain when the page opened", r"ten", 0, "evidence/snapshot.json",
     lambda s: f"totals.disputes_opened = {s.totals['disputes_opened']}; docs/images/feed.json shows {s.feed.get('Disputes opened')}"),
    (r"read from the chain when the page opened", r"eight of ten", 0, "evidence/snapshot.json",
     lambda s: f"totals.upheld = {s.totals['upheld']} of {s.totals['decided']} decided; docs/images/feed.json shows {s.feed.get('Not honored')}"),
    (r"dispute to verdict", r"67", 0, "evidence/snapshot.json", lambda s: f"totals.median_dispute_to_verdict_seconds = {s.totals['median_dispute_to_verdict_seconds']}"),
    (r"dispute to money back", r"100", 0, "evidence/snapshot.json", lambda s: f"totals.median_dispute_to_money_back_seconds = {s.totals['median_dispute_to_money_back_seconds']}"),
    (r"finalizes a median of", r"30", 0, "evidence/snapshot.json", lambda s: f"totals.median_finality_seconds = {s.totals['median_finality_seconds']}"),
    (r"4 modes", r"4", 0, "seller/main.py", lambda s: "MODES = " + literal("seller/main.py", r"MODES = (\([^)]*\))")),
    (r"2 model calls", r"2", 0, "contracts/dispute.py", "judge() asks once in each presentation order"),
    (r"3 frozen strings|three frozen strings", r"3|three", 0, "contracts/dispute.py", "build_prompt takes the promise, the request and the response, then the chain's timing"),
    (r"two parties agreed", r"two", 0, None, "a definition of the call Recourse is not for, not a count of anything"),
    (r"1 narrow question", r"1", 0, "contracts/dispute.py", "judge() asks one question: did this response honor the promise"),
    (r"HTTP 200", r"200", 0, "seller/main.py", lambda s: literal("seller/main.py", r"(402 without payment proof, 200 with)")),
    (r"Eighteen disputes", r"eighteen", 0, "eval/cases.json", lambda s: f"{len(s.cases)} cases"),
    (r"two files, neither is code", r"two", 0, "git", lambda s: s.commit_files("b50757f")),
    (r"three further cases", r"three", 0, "eval/cases-v2.json", lambda s: f"{len(s.cases2)} cases"),
    (r"accuracy\s+17/18", r"17/18", 0, "eval/results.json", lambda s: f"accuracy {s.r1['accuracy']} of n {s.r1['n']}"),
    (r"stability\s+17/18", r"17/18", 0, "eval/results.json", lambda s: f"stability {s.r1['stability']} of n {s.r1['n']}"),
    (r"unclear\s+3/18", r"3/18", 0, "eval/results.json", lambda s: f"unclear {s.r1['unclear']} of n {s.r1['n']}"),
    (r"held out\s+1/3", r"1/3", 0, "eval/results-v2.json", lambda s: f"accuracy {s.r2['accuracy']} of n {s.r2['n']}"),
    (r"accuracy\s+1/3", r"1/3", 0, "eval/results-v2.json", lambda s: f"accuracy {s.r2['accuracy']} of n {s.r2['n']}"),
    (r"stability\s+2/3", r"2/3", 0, "eval/results-v2.json", lambda s: f"stability {s.r2['stability']} of n {s.r2['n']}"),
    (r"missed", r"19|20|21", 0, "eval/results-v2.json", lambda s: s.held_out()),
    (r"two accuracy figures", r"two", 0, "eval/results.json, eval/results-v2.json",
     lambda s: f"{s.r1['accuracy']}/{s.r1['n']} and {s.r2['accuracy']}/{s.r2['n']}"),
    (r"measured on the set the judgment question", r"17 of 18", 0, "eval/results.json", lambda s: f"accuracy {s.r1['accuracy']} of n {s.r1['n']}"),
    (r"Three held out cases", r"three", 0, "eval/cases-v2.json", lambda s: f"{len(s.cases2)} cases"),
    (r"They score", r"1 of 3", 0, "eval/results-v2.json", lambda s: f"accuracy {s.r2['accuracy']} of n {s.r2['n']}"),
    (r"Case 12", r"12", 0, "eval/results.json",
     lambda s: next((f"case 12: expected {r.get('expected')}, correct {r.get('correct')}" for r in s.r1["rows"] if r["id"] == "12"), "no case 12")),
    (r"Two transaction hashes", r"two", 0, None, "a past count, which this row reports as wrong"),
    (r"all ten now verify", r"ten", 0, "README.md, evidence/snapshot.json", lambda s: s.cited_hashes()),
    (r"89 seconds", r"89", 0, None, "the figure this row reports as wrong"),
    (r"stated as 231", r"231", 0, None, "the count this row reports as wrong"),
    (r"1771 to 1961", r"1771 to 1961", 0, None, "the range this row reports as wrong"),
    (r"1814 to 2004", r"1814 to 2004", 0, "tests/direct/test_dispute.py",
     lambda s: "{0} to {1}, rebuilt now through the frozen build_prompt".format(*s.prompts)),
    (r"fourteen payments", r"fourteen", 0, None, "the count this row reports as wrong"),
    (r"said nineteen", r"nineteen", 0, "evidence/snapshot.json", lambda s: f"totals.payments = {s.totals['payments']}"),
    (r"Four claims on the site", r"four", 0, None, "a past count, which this row reports as wrong"),
    (r"Three cases, aimed", r"three", 0, "eval/cases-v2.json", lambda s: f"{len(s.cases2)} cases"),
    (r"distribution the question was narrowed against", r"17/18", 0, "eval/results.json", lambda s: f"accuracy {s.r1['accuracy']} of n {s.r1['n']}"),
    (r"three cases it had never seen", r"1/3", 0, "eval/results-v2.json", lambda s: f"accuracy {s.r2['accuracy']} of n {s.r2['n']}"),
    (r"three cases it had never seen", r"three", 0, "eval/cases-v2.json", lambda s: f"{len(s.cases2)} cases"),
    (r"misses", r"one of the two", 0, "eval/results-v2.json", lambda s: s.held_out()),
    (r"runs three times", r"three", 0, "eval/results.json", lambda s: f"runs {s.r1['runs']}"),
    (r"scored 16 of 18", r"16 of 18|2 of 18", 0, None, "an earlier run, before both orders were asked"),
    (r"4 expected", r"4", 0, "eval/cases.json", lambda s: f"{sum(1 for c in s.cases.values() if c['expected'] == 'unclear')} cases expect unclear"),
    (r"Case 07", r"07", 0, "eval/cases.json", lambda s: s.case("07")),
    (r"six second timestamp", r"six", 0, "eval/cases.json", lambda s: s.case_age("07")),
    (r"six second timestamp against a five second promise", r"five", 0, "eval/cases.json", lambda s: s.case_age("07")),
    (r"Case 16", r"16", 0, "eval/cases.json", lambda s: s.case("16")),
    (r"17 inside the promise", r"17", 0, "eval/cases.json", lambda s: s.case("17")),
    (r"18 inside the request", r"18", 0, "eval/cases.json", lambda s: s.case("18")),
    (r"three adversarial cases", r"three", 0, "eval/cases.json", lambda s: "; ".join(s.case(n) for n in ("16", "17", "18"))),
    (r"direct tests", r"272", 0, "pytest, which scripts/test.py reads", lambda s: s.direct_tests),
    (r"defences", r"32|32 of 32", 0, "docs/MUTATIONS.md", lambda s: literal("docs/MUTATIONS.md", r"\*\*(\d+ of \d+) defences verified")),
    (r"32 of 32 are caught", r"32 of 32", 0, "docs/MUTATIONS.md", lambda s: literal("docs/MUTATIONS.md", r"\*\*(\d+ of \d+) defences verified")),
    (r"26 checks", r"26", 0, None,
     lambda s: f"what one live run checks: tests/integration/test_cycle.py has "
     f"{read(ROOT / 'tests' / 'integration' / 'test_cycle.py').count('check(') - 1} check() call sites, several the two "
     "branches of one check and one inside a loop, so only a run with RECOURSE_INTEGRATION=1 can confirm it"),
    (r"--runs 3", r"3", 0, "eval/results.json", lambda s: f"runs {s.r1['runs']}"),
    (r"six worked examples", r"six", 0, "linter/examples.py", lambda s: s.examples()),
    (r"two real coverage gaps", r"two", 0, "docs/SECURITY.md", "names the two tests that exist only because mutation found the gap"),
    (r"six reference files", r"six", 0, "recourse-skill/reference/",
     lambda s: f"{len(list((SKILL / 'reference').glob('0[0-9]-*.md')))} numbered reference files"),
    (r"five read only tools", r"five", 0, "recourse-skill/mcp/app/api/mcp/route.ts",
     lambda s: f"{read(SKILL / 'mcp' / 'app' / 'api' / 'mcp' / 'route.ts').count('server.registerTool(')} tools registered"),
    (r"4504", r"4504", 0, "recourse-skill/mcp/package.json", lambda s: literal("mcp/package.json", r'"dev": "([^"]+)"', SKILL)),
    (r"4503", r"4503", 0, "linter/serve.py", lambda s: "default port " + literal("linter/serve.py", r"default=(\d+)")),
    (r"port 4500", r"4500", 0, "web/package.json", lambda s: literal("web/package.json", r'"dev": "([^"]+)"')),
    (r"Two files, frozen", r"two", 0, "contracts/FROZEN.json", lambda s: f"frozen: {', '.join(k for k in ('escrow', 'dispute') if k in s.frozen)}"),
    (r"two hashes", r"two", 0, "contracts/FROZEN.json",
     lambda s: f"{sum(1 for k in ('escrow', 'dispute') if 'sha256' in s.frozen.get(k, {}))} sha256 entries"),
    (r"61999", r"61999", 0, "contracts/FROZEN.json", lambda s: f"chain_id {s.frozen['deployments']['studionet']['chain_id']}"),
    (r"The two evaluation scores", r"two", 0, "eval/results.json, eval/results-v2.json", "one results file for each set"),
    (r"six disputes and six", r"six", 0, None, "the chain's count at the time this sentence describes"),
    (r"hundred percent", r"a hundred", 0, None, "the rate at the time this sentence describes"),
    (r"a nine hour old price against a five second promise", r"five", 0, "evidence/snapshot.json", lambda s: s.seller_promise("p-000003")),
    (r"evaluation case 08", r"08", 0, "eval/cases.json", lambda s: s.case("08")),
    (r"three transactions through consensus", r"three", 0, "evidence/snapshot.json", lambda s: s.transactions("p-000014")),
    (r"eighteen committed cases", r"eighteen", 0, "eval/cases.json", lambda s: f"{len(s.cases)} cases"),
    (r"committee of five", r"five", 0, "evidence/snapshot.json", lambda s: f"totals.committee = {s.committee}"),
    (r"Six judgments a minute", r"six", 0, "web/app/api/clerk/route.ts", lambda s: "PER_ADDRESS = " + literal("web/app/api/clerk/route.ts", r"PER_ADDRESS = (\d+)")),
    (r"Six judgments a minute", r"thirty", 1, "web/app/api/clerk/route.ts", lambda s: "GLOBAL = " + literal("web/app/api/clerk/route.ts", r"GLOBAL = (\d+)")),
    (r"Six judgments a minute", r"thirty", 2, "web/app/api/lint/route.ts", lambda s: "PER_ADDRESS = " + literal("web/app/api/lint/route.ts", r"PER_ADDRESS = (\d+)")),
    (r"Six judgments a minute", r"a hundred and twenty", 0, "web/app/api/lint/route.ts", lambda s: "GLOBAL = " + literal("web/app/api/lint/route.ts", r"GLOBAL = (\d+)")),
    (r"at least two model calls", r"two", 0, "contracts/dispute.py", "judge() asks once in each presentation order"),
    (r"402 character signature", r"402", 0, "scripts/evidence.py",
     lambda s: f'"0x" + "1" * {literal("scripts/evidence.py", r"\"0x\" \+ \"1\" \* (\d+)")}, so {2 + int(literal("scripts/evidence.py", r"\"0x\" \+ \"1\" \* (\d+)"))} characters'),
    (r"twenty seconds", r"twenty", 0, "web/lib/chain.ts", lambda s: "LIVE_DEADLINE_MS = " + literal("web/lib/chain.ts", r"LIVE_DEADLINE_MS = ([\d_]+)")),
    (r"four refusals above", r"four", 0, "README.md, evidence/snapshot.json", lambda s: s.refusals()),
    (r"four attackers", r"four", 0, "docs/SECURITY.md", "its opening says four attackers; count its sections by hand"),
    (r"all three were", r"three", 0, None, "the three paragraphs that follow it in this section"),
    (r"Six of the eighteen cases", r"six of the eighteen", 0, None,
     lambda s: "counted from eval/cases.json by the rule docs/SECURITY.md states, which names "
     + literal("docs/SECURITY.md", r"turn on freshness: in ([0-9, and\n]+?) every other term").replace("\n", " ")),
    (r"a five second promise", r"five", 0, "evidence/snapshot.json", lambda s: s.seller_promise("p-000003")),
    (r"from 16 of 18 to 17", r"16 of 18", 0, None, "the earlier run, before both orders were asked"),
    (r"from 16 of 18 to 17", r"17", 0, "eval/results.json", lambda s: f"accuracy {s.r1['accuracy']} of n {s.r1['n']}"),
    (r"from 2 to 3", r"2 to 3", 0, "eval/results.json", lambda s: f"unclear {s.r1['unclear']} now; 2 was the earlier run"),
    (r"from 2 to 3 of 18", r"18", 0, "eval/cases.json", lambda s: f"{len(s.cases)} cases"),
    (r"402, scheme external-settlement", r"402", 0, "seller/main.py", lambda s: literal("seller/main.py", r"(402 without payment proof, 200 with)")),
    (r"4502", r"4502", 0, None, "an argument in the command itself"),
    (r"fifteen fields", r"fifteen", 0, "evidence/snapshot.json", lambda s: s.payment_fields()),
    (r"gasUsed", r"8000000", 0, "evidence/snapshot.json",
     lambda s: f"gasUsed {sorted({int(r['gasUsed'], 16) for r in s.snapshot['fees']['receipts']})} across {len(s.snapshot['fees']['receipts'])} sampled receipts"),
    (r"ten model calls|round of ten|those ten calls|model calls per adjudication", r"ten|10", 0, "evidence/snapshot.json, contracts/dispute.py",
     lambda s: f"committee {s.committee} x 2 orders = {s.committee * 2}"),
    (r"committee\s+5 nodes", r"5", 0, "evidence/snapshot.json", lambda s: f"totals.committee = {s.committee}"),
    (r"model calls per node", r"2", 0, "contracts/dispute.py", "judge() asks once in each presentation order"),
    (r"about 480 tokens", r"480", 0, "tests/direct/test_dispute.py", lambda s: "about {2}, rebuilt now at four characters a token".format(*s.prompts)),
    (r"about 4800", r"4800", 0, "tests/direct/test_dispute.py", lambda s: "about {0}, ten calls a dispute".format(s.prompts[2] * 10)),
    (r"so five more|would cost five", r"five", 0, "evidence/snapshot.json", lambda s: f"totals.committee = {s.committee}"),
    (r"rule 04", r"04", 0, "docs/RULES.md", lambda s: "rule 04: " + literal("docs/RULES.md", r"\*\*04 - ([^*]+)\*\*")),
    (r"at least 0\.2", r"0\.2", 0, "evidence/receipts/", lambda s: s.receipts_policy()),
    (r"three passing worked examples", r"three", 0, "linter/examples.py", lambda s: s.examples()),
    (r"larger than three", r"three", 0, "eval/cases-v2.json", lambda s: f"the held out set has {len(s.cases2)}"),
    (r"all three runs of a case", r"three", 0, "eval/results.json", lambda s: f"runs {s.r1['runs']}"),
    (r"works through all three", r"three", 0, "eval/cases-v2.json", lambda s: f"{len(s.cases2)} cases"),
    (r"Three strings in|the three strings", r"three", 0, "contracts/dispute.py", "build_prompt takes the promise, the request and the response, then the chain's timing"),
    (r"disagreement between the two", r"two", 0, "contracts/dispute.py", "judge() asks once in each presentation order"),
    (r"The same two files", r"two", 0, "contracts/FROZEN.json", lambda s: f"frozen: {', '.join(k for k in ('escrow', 'dispute') if k in s.frozen)}"),
    (r"print the two figures together", r"two", 0, "eval/results.json, eval/results-v2.json",
     lambda s: f"{s.r1['accuracy']}/{s.r1['n']} and {s.r2['accuracy']}/{s.r2['n']}"),
    (r"the two chain timestamps", r"two", 0, "contracts/dispute.py", "a case's opened_at and decided_at"),
    (r"the other two verdicts", r"two", 0, "evidence/snapshot.json", lambda s: "; ".join(s.row(p) for p in ("p-000013", "p-000014"))),
    (r"three failure modes", r"three", 0, "seller/main.py", lambda s: "MODES = " + literal("seller/main.py", r"MODES = (\([^)]*\))") + ", less correct"),
    (r"held out set scores", r"1 of 3", 0, "eval/results-v2.json", lambda s: f"accuracy {s.r2['accuracy']} of n {s.r2['n']}"),
    (r"all three are ruled on the merits", r"three", 0, "eval/cases.json", lambda s: "; ".join(s.case(n) for n in ("16", "17", "18"))),
    (r"all three verdicts", r"three", 0, "evidence/snapshot.json", lambda s: "; ".join(s.row(p) for p in ("p-000003", "p-000013", "p-000014"))),
    (r"Three things we got wrong first", r"three", 0, None, "the three paragraphs of this section"),
    (r"five nodes agreeing|five nodes being right", r"five", 0, "evidence/snapshot.json", lambda s: f"totals.committee = {s.committee}"),
    (r"three strings and a timing block", r"three", 0, "contracts/dispute.py", "build_prompt takes the promise, the request and the response, then the chain's timing"),
    (r"four characters a token", r"four", 0, "tests/direct/test_dispute.py", "the test divides the mean prompt length by four"),
    (r"three projects|three imports", r"three", 0, "docs/HOSTING.md", lambda s: s.hosting_sections()),
    (r"these two repositories", r"two", 0, None, "this repository and recourse-skill"),
    (r"stage 1", r"1", 0, "linter/rules.py", "stage 1 is precheck(): deterministic, and no model is asked"),
    (r"stage 2", r"2", 0, "linter/service.py", "stage 2 asks the deployed gate's question of one model"),
    (r"", r"17 of 18|17/18", 0, "eval/results.json", lambda s: f"accuracy {s.r1['accuracy']} of n {s.r1['n']}"),
    (r"", r"1 of 3|1/3", 0, "eval/results-v2.json", lambda s: f"accuracy {s.r2['accuracy']} of n {s.r2['n']}"),
    (r"", r"eighteen", 0, "eval/cases.json", lambda s: f"{len(s.cases)} cases"),
    (r"", r"p-\d{6}", 0, "evidence/snapshot.json", None),
]


# --- the README's numbers ------------------------------------------------------

NUMBER_WORDS = [
    "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
    "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
    "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred",
]
WORDS = "|".join(sorted(NUMBER_WORDS, key=len, reverse=True))
TOKEN = re.compile(
    r"(?<![\w./=-])(?:"
    r"p-\d{6}"
    r"|\d+ ?/ ?\d+"
    rf"|(?:{WORDS}|one|\d+) of (?:the )?(?:{WORDS}|\d+)"
    r"|\d+ to \d+"
    r"|\d+(?:\.\d+)*(?:s|%)?"
    rf"|a hundred(?: and (?:{WORDS}))?"
    rf"|(?:{WORDS})"
    r")(?![\w-])",
    re.IGNORECASE,
)


class Number(typing.NamedTuple):
    line: int
    written: str
    around: str
    source: str
    now: str


def plain(text: str) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return text.replace("**", "").replace("*", "")


def units(text: str) -> typing.Iterator[tuple[int, str]]:
    """Sentences of prose, cells of tables and lines of code, with a line number each."""
    fenced = False
    paragraph: list[tuple[int, str]] = []

    def flush() -> typing.Iterator[tuple[int, str]]:
        if not paragraph:
            return
        starts, joined = [], ""
        for number, line in paragraph:
            starts.append(len(joined))
            joined += line.strip() + " "
        offset = 0
        for sentence in re.split(r"(?<=[.!?:])\s+(?=[A-Z`(\[])", joined.strip()):
            offset = joined.find(sentence, offset)
            yield paragraph[max(0, bisect.bisect_right(starts, offset) - 1)][0], sentence
            offset += len(sentence)
        paragraph.clear()

    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith("```"):
            yield from flush()
            fenced = not fenced
            continue
        if fenced:
            yield number, line
            continue
        if line.startswith("|"):
            yield from flush()
            if set(line) <= set("|- "):
                continue
            for cell in line.strip().strip("|").split(" | "):
                yield number, plain(cell.strip())
            continue
        if line.startswith("#"):
            yield from flush()
            yield number, plain(line.lstrip("#").strip())
            continue
        if not line.strip() or line.startswith("---"):
            yield from flush()
            continue
        if line.startswith("!["):
            yield from flush()
            yield number, plain(line)
            continue
        paragraph.append((number, plain(re.sub(r"^\s*\d+\.\s+", "", line))))
    yield from flush()


def source_of(sentence: str, written: str, nth: int, sources: Sources) -> tuple[str, str]:
    for pattern, token, occurrence, file, value in RULES:
        if not re.search(pattern, sentence, re.IGNORECASE) or not re.fullmatch(token, written, re.IGNORECASE):
            continue
        if occurrence and occurrence != nth:
            continue
        if value is None:
            return file or NO_FILE, sources.row(written)
        try:
            now = value(sources) if callable(value) else value
        except Exception as error:  # noqa: BLE001 - reported in the row, never raised
            now = f"could not read it: {type(error).__name__}: {error}"
        return (file or NO_FILE), now
    return NO_FILE, ""


def around(sentence: str, start: int, end: int) -> str:
    left, right = sentence[:start], sentence[end:]
    if len(left) > 55:
        left = "(cut) " + left[-55:].split(" ", 1)[-1]
    if len(right) > 55:
        right = right[:55].rsplit(" ", 1)[0] + " (cut)"
    return (left + "**" + sentence[start:end] + "**" + right).replace("|", "\\|")


def numbers(sources: Sources) -> list[Number]:
    rows = []
    for line, sentence in units(sources.readme):
        seen: dict[str, int] = {}
        for match in TOKEN.finditer(sentence):
            written = match.group(0)
            seen[written.lower()] = seen.get(written.lower(), 0) + 1
            file, now = source_of(sentence, written, seen[written.lower()], sources)
            rows.append(Number(line, written, around(sentence, match.start(), match.end()), file, now))
    return rows


# --- links -----------------------------------------------------------------------


class Link(typing.NamedTuple):
    file: str
    text: str
    target: str
    path: pathlib.Path


MARKDOWN_LINK = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)\)")
BADGE = re.compile(r"\[!\[([^\]]*)\]\(([^)\s]+)\)\]\(([^)\s]+)\)")
BARE_URL = re.compile(r"https?://[^\s)`'\"<>\]]+")


def link_files() -> list[tuple[str, pathlib.Path]]:
    files = [("README.md", ROOT / "README.md")]
    files += [(f"docs/{p.name}", p) for p in sorted((ROOT / "docs").glob("*.md")) if p != OUT]
    files.append(("recourse-skill/README.md", SKILL / "README.md"))
    files += [(f"recourse-skill/reference/{p.name}", p) for p in sorted((SKILL / "reference").glob("0[0-9]-*.md"))]
    return [(label, path) for label, path in files if path.exists()]


def links() -> tuple[list[Link], list[Link]]:
    ordinary: list[Link] = []
    hosted: list[Link] = []
    for label, path in link_files():
        text = read(path)
        seen: set[tuple[str, str]] = set()
        for url in BARE_URL.findall(text):
            url = url.rstrip(".,;:")
            if HOSTED in url and ("", url) not in seen:
                seen.add(("", url))
                hosted.append(Link(label, "", url, path))
        prose = re.sub(r"(?ms)^```.*?^```", "", text)
        prose = re.sub(r"`[^`\n]*`", "", prose)
        # A badge is an image inside a link: two targets, and the plain pattern
        # would read the image's alt text as the link's.
        for alt, image, target in BADGE.findall(prose):
            ordinary.append(Link(label, f"badge: {alt}", target, path))
            ordinary.append(Link(label, f"image: {alt}", image, path))
        prose = BADGE.sub("", prose)
        for bang, anchor, target in MARKDOWN_LINK.findall(prose):
            if HOSTED in target:
                continue
            key = (anchor, target)
            if key not in seen:
                seen.add(key)
                ordinary.append(Link(label, ("image: " if bang else "") + (anchor or "(no text)"), target, path))
        for url in BARE_URL.findall(MARKDOWN_LINK.sub("", prose)):
            url = url.rstrip(".,;:")
            if HOSTED not in url and ("", url) not in seen:
                seen.add(("", url))
                ordinary.append(Link(label, "(bare URL)", url, path))
    return ordinary, hosted


def slug(heading: str) -> str:
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def resolve_local(link: Link) -> str:
    target, _, anchor = link.target.partition("#")
    destination = (link.path.parent / target).resolve() if target else link.path
    if not destination.exists():
        return "missing: no such file"
    if anchor:
        if destination.is_dir():
            return "exists, a directory; the anchor is not checked"
        headings = {slug(h) for h in re.findall(r"(?m)^#+ (.+)$", read(destination))}
        return "exists, and the anchor is a heading there" if anchor in headings else "exists, but no heading makes that anchor"
    return "exists, a directory" if destination.is_dir() else "exists"


def fetch(url: str) -> str:
    headers = {"User-Agent": "recourse-hand-check (reads the README's links)"}
    last = ""
    for method in ("HEAD", "GET"):
        try:
            request = urllib.request.Request(url, method=method, headers=headers)
            with urllib.request.urlopen(request, timeout=8) as response:
                final = response.geturl()
                return f"{response.status}" + (f", redirected to {final}" if final.rstrip("/") != url.rstrip("/") else "")
        except urllib.error.HTTPError as error:
            last = f"{error.code} {error.reason}"
            if method == "HEAD" and error.code in (400, 403, 404, 405, 429, 501):
                continue
            return last
        except Exception as error:  # noqa: BLE001 - reported, never raised
            last = f"no answer: {type(error).__name__}"
    return last


def resolve(all_links: list[Link], offline: bool) -> dict[str, str]:
    remote = sorted({link.target for link in all_links if link.target.startswith("http")})
    results = {url: "not fetched: --offline" for url in remote}
    if not offline and remote:
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            for url, answer in zip(remote, pool.map(fetch, remote)):
                results[url] = answer
    for link in all_links:
        if not link.target.startswith("http"):
            results[f"{link.path}|{link.target}"] = resolve_local(link)
    return results


def resolved(link: Link, results: dict[str, str]) -> str:
    return results.get(link.target) if link.target.startswith("http") else results.get(f"{link.path}|{link.target}", "")


# --- the page ------------------------------------------------------------------


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def judges_path(sources: Sources, rows: list[Number], ordinary: list[Link], hosted: list[Link], results: dict[str, str]) -> list[str]:
    top = sources.readme.split("\n## ", 1)[0]
    tagline = re.search(r"\*\*(.+?)\*\*", top)
    first_sentence = re.split(r"(?<=\.)\s", " ".join(top.split("\n\n")[3].split()), maxsplit=1)[0] if len(top.split("\n\n")) > 3 else ""
    readme_links = [link for link in ordinary if link.file == "README.md"]
    clickable = [link for link in readme_links if not link.text.startswith("image: ")]
    prose_links = [link for link in clickable if not link.text.startswith("badge: ")]
    images = [link for link in readme_links if link.text.startswith("image: ") and not link.target.endswith(".svg")]
    backed = [row for row in rows if row.source != NO_FILE]
    first_numbers = "; ".join(f"{row.written} ({row.now})" for row in backed[:8])
    site = next((link.target for link in hosted if "recourse-site" in link.target), "https://recourse-site.vercel.app")
    headings = re.findall(r"(?m)^## (.+)$", sources.readme)
    lines = [
        "## The judge's path",
        "",
        "What a stranger meets in the first four minutes, in the order they meet it. A reading order, not a checklist: walk it as someone who has never seen the repository.",
        "",
        f"1. **The first screen.** The title, the CI badge, then the line in bold, \"{tagline.group(1) if tagline else ''}\", and the first sentence under it: \"{first_sentence}\"",
    ]
    if clickable and prose_links:
        first = clickable[0]
        name = f"The CI badge, alt text \"{first.text.removeprefix('badge: ')}\"," if first.text.startswith("badge: ") else f"{first.text},"
        lines.append(f"2. **The first link.** {name} to {first.target}, which answered {resolved(first, results)} on this run. The first link in the prose is {prose_links[0].text}, to {prose_links[0].target} ({resolved(prose_links[0], results)}).")
    lines.append(f"3. **The numbers.** The first eight with a file behind them, in the order a reader meets them: {first_numbers}. The table below has all {len(rows)}, the ones with no single file behind them included.")
    if images:
        lines.append(f"4. **The one image.** {images[0].target}, captioned \"{images[0].text.removeprefix('image: ')}\". A second, {images[1].target if len(images) > 1 else ''}, sits directly under it.")
    lines.append(f"5. **The live site.** {site}, which answered {results.get(site, 'not fetched')} on this run. Until the Vercel imports it does not exist, so a stranger today stops at the README, whose sections run in this order: {', '.join(headings)}.")
    return lines


def page(sources: Sources, rows: list[Number], ordinary: list[Link], hosted: list[Link], results: dict[str, str], offline: bool) -> str:
    when = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    unbacked = sum(1 for row in rows if row.source == NO_FILE)
    lines = [
        "# Hand check",
        "",
        f"Generated by `python scripts/hand_check.py` at {when}{', offline, so no link was fetched' if offline else ''}. It is rewritten whole on every run, so run it again rather than editing this page. It reads and never asserts, and it is not part of `scripts/test.py`.",
        "",
        *judges_path(sources, rows, ordinary, hosted, results),
        "",
        "## Every number in the README",
        "",
        f"{len(rows)} numbers, in the order they appear. {unbacked} have {NO_FILE}: those are marked in the \"from\" column and are the ones to read closest.",
        "",
        "| # | line | as written | around it | from | now | checked |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for index, row in enumerate(rows, 1):
        lines.append(f"| {index} | {row.line} | {cell(row.written)} | {row.around} | {cell(row.source)} | {cell(row.now)} | |")
    lines += [
        "",
        "## Every link",
        "",
        f"{len(ordinary)} links in the README, `docs/`, the skill's README and its six reference files, each with what it resolved to on this run.",
        "",
        "| file | text | target | resolved | checked |",
        "| --- | --- | --- | --- | --- |",
    ]
    for link in ordinary:
        lines.append(f"| {cell(link.file)} | {cell(link.text)} | {cell(link.target)} | {cell(resolved(link, results))} | |")
    lines += [
        "",
        "### The hosted URLs",
        "",
        f"{len(hosted)} mentions of a `{HOSTED}` address, code included. Until the three Vercel imports these fail, and that is expected rather than a finding; after them, each should answer.",
        "",
        "| file | target | resolved | checked |",
        "| --- | --- | --- | --- |",
    ]
    for link in hosted:
        lines.append(f"| {cell(link.file)} | {cell(link.target)} | {cell(resolved(link, results))} | |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="check links on disk only; fetch nothing")
    args = parser.parse_args()

    sources = Sources()
    rows = numbers(sources)
    ordinary, hosted = links()
    results = resolve(ordinary + hosted, args.offline)
    OUT.write_text(page(sources, rows, ordinary, hosted, results, args.offline), encoding="utf-8")

    unbacked = sum(1 for row in rows if row.source == NO_FILE)
    broken = [link for link in ordinary if not re.match(r"(exists|2\d\d|3\d\d)", resolved(link, results) or "")]
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} numbers ({unbacked} with {NO_FILE}), "
          f"{len(ordinary)} links ({len(broken)} not answering 2xx or present on disk), {len(hosted)} hosted mentions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
