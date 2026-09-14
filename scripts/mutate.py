#!/usr/bin/env python3
"""
Break each defence on purpose and check the suite goes red.

    python scripts/mutate.py
    python scripts/mutate.py --table docs/MUTATIONS.md

A passing count is a claim. A table of mutations, each naming the test that
caught it, is evidence. A green suite says the tests agree with the code, not
that they would notice the code being wrong, and those are different claims.

Every guard is worth exactly as much as the test that fails when you delete it,
so this deletes them one at a time and reports any nothing catches. An escape
means either a missing test, or a later defence strict enough that an earlier
test can no longer fail, and a test that cannot fail is worse than no test.

**The table is not written when anything escapes.** A document that lists the
defences it could not verify is worse than no document, because it reads as
coverage.

Nothing here edits the repository. The contracts and tests are copied to a
scratch directory, mutated there, and the copy is removed.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests" / "direct"))

from harness import CONTRACT_MODULES  # noqa: E402  the modules that run once per pair

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Every mutant runs against both pairs: the frozen one, deployed on studionet,
#: and the ported one, deployed on Studio Next. The same defence has to be
#: caught in each, because a port that dropped a guard would pass everything
#: that only looked at the first pair.
PAIRS = {"frozen": "contracts", "v06": "contracts/v06"}

#: (file, what is being broken, the code to replace, what to replace it with).
#: Each is a bug somebody could plausibly ship, not a syntactic mangling. A
#: mutant nobody would write teaches nothing when it survives.
MUTANTS = [
    # -- the money path ----------------------------------------------------
    ("escrow", "settle accepts any caller",
     'if gl.message.sender_address != self.dispute_contract:\n'
     '            raise gl.vm.UserError(E + "not authorised")',
     'if False:\n            raise gl.vm.UserError(E + "not authorised")'),
    ("escrow", "withdraw before the window closes",
     'if self._now() <= payment.window_ends:\n'
     '            raise gl.vm.UserError(E + "window open")',
     'if False:\n            raise gl.vm.UserError(E + "window open")'),
    ("escrow", "dispute without a recorded response",
     'if payment.response == "":\n            raise gl.vm.UserError(E + "no response")',
     'if False:\n            raise gl.vm.UserError(E + "no response")'),
    # An earlier version of this mutant split the payout into two sends of the
    # same total, which pays the same money and is an equivalent mutant. It
    # escaped, correctly, and reading why is what turned it into a real one.
    ("escrow", "settle pays the buyer twice",
     "self._send(payment.buyer, u256(payment.amount + payment.bond))",
     "self._send(payment.buyer, u256(payment.amount + payment.bond))\n"
     "            self._send(payment.buyer, u256(payment.amount + payment.bond))"),
    ("escrow", "the bond is never added to held",
     "self.held = u256(self.held + gl.message.value)",
     "self.held = u256(self.held + u256(0))"),
    ("escrow", "a response can be overwritten",
     'if payment.response != "":\n'
     '            raise gl.vm.UserError(E + "response already recorded")',
     'if False:\n            raise gl.vm.UserError(E + "response already recorded")'),
    ("escrow", "a signature of any length can be stored",
     'if len(sig) > MAX_SIG:\n            raise gl.vm.UserError(E + "signature too long")',
     'if False:\n            raise gl.vm.UserError(E + "signature too long")'),
    ("escrow", "paying does not count as a live payment",
     "self.sellers[addr].live = u32(entry.live + u32(1))",
     "self.sellers[addr].live = u32(entry.live + u32(0))"),
    ("escrow", "the bond need not be exact",
     'if gl.message.value != self.bond_amount:\n'
     '            raise gl.vm.UserError(E + "wrong bond")',
     'if gl.message.value < u256(0):\n            raise gl.vm.UserError(E + "wrong bond")'),
    ("escrow", "anyone may open a dispute",
     'if gl.message.sender_address != payment.buyer:\n'
     '            raise gl.vm.UserError(E + "not buyer")',
     'if False:\n            raise gl.vm.UserError(E + "not buyer")'),
    ("escrow", "settle accepts a verdict outside the three",
     "if verdict != V_HONORED and verdict != V_NOT_HONORED and verdict != V_UNCLEAR:",
     "if False:"),
    ("escrow", "the dispute contract can be redirected later",
     'if self.dispute_contract != ZERO:\n'
     '            raise gl.vm.UserError(E + "dispute contract already set")',
     'if False:\n            raise gl.vm.UserError(E + "dispute contract already set")'),
    ("escrow", "a stranger may record a response",
     "if who != payment.seller and who != payment.buyer:\n"
     '            raise gl.vm.UserError(E + "not a party")',
     'if False:\n            raise gl.vm.UserError(E + "not a party")'),
    ("escrow", "a promise can be rewritten under a live payment",
     'if self.sellers[who].live != u32(0):\n'
     '            raise gl.vm.UserError(E + "open payments")',
     'if False:\n            raise gl.vm.UserError(E + "open payments")'),
    ("escrow", "a seller may clear their own judgeability flag",
     'if gl.message.sender_address != self.dispute_contract:\n'
     '            raise gl.vm.UserError(E + "not authorised")\n'
     "        key = Address(seller)",
     'if False:\n            raise gl.vm.UserError(E + "not authorised")\n'
     "        key = Address(seller)"),
    # -- the routes out ----------------------------------------------------
    ("escrow", "a dispute can be unwound while judgment still runs",
     'if self._now() <= payment.dispute_ends:\n'
     '            raise gl.vm.UserError(E + "judgment still running")',
     'if False:\n            raise gl.vm.UserError(E + "judgment still running")'),
    ("escrow", "a stranger may unwind a dispute",
     "if who != payment.buyer and who != payment.seller:\n"
     '            raise gl.vm.UserError(E + "not a party")\n'
     "        if payment.status != ST_DISPUTED:",
     'if False:\n            raise gl.vm.UserError(E + "not a party")\n'
     "        if payment.status != ST_DISPUTED:"),
    ("escrow", "unwinding pays the buyer the whole payment",
     "self._send(payment.seller, payment.amount)\n"
     "        self._send(payment.buyer, payment.bond)",
     "self._send(payment.buyer, payment.amount)\n"
     "        self._send(payment.buyer, payment.bond)"),
    ("escrow", "a review can be asked for repeatedly on one promise",
     "if entry.reviewed == _digest(entry.promise):", "if False:"),
    ("escrow", "a gate ruling that never lands still burns the promise",
     "self.sellers[key].reviewed = _digest(self.sellers[key].promise)",
     "self.sellers[key].reviewed = self.sellers[key].reviewed"),
    # -- the judgment ------------------------------------------------------
    ("dispute", "the promise reaches the model unfenced",
     "promise=_fence(promise),", "promise=promise,"),
    ("dispute", "the request reaches the model unfenced",
     "request=_fence(request),", "request=request,"),
    ("dispute", "the response reaches the model unfenced",
     "response=_fence(response),", "response=response,"),
    ("dispute", "the validator forgives a verdict mismatch",
     'return mine["verdict"] == their_verdict',
     'return mine["verdict"] == their_verdict or their_verdict == "unclear"'),
    ("dispute", "the validator accepts a verdict outside the closed set",
     "if their_verdict not in CODES:\n                return False",
     "if False:\n                return False"),
    ("dispute", "anyone may open a case",
     'if gl.message.sender_address != self.escrow:\n'
     '            raise gl.vm.UserError(E + "not authorised")',
     'if False:\n            raise gl.vm.UserError(E + "not authorised")'),
    ("dispute", "a case can be decided twice",
     'if pid in self.cases:\n            raise gl.vm.UserError(E + "case exists")',
     'if False:\n            raise gl.vm.UserError(E + "case exists")'),
    ("dispute", "anyone may run the judgeability gate",
     "if gl.message.sender_address != self.owner and gl.message.sender_address != self.escrow:\n"
     '            raise gl.vm.UserError(E + "not authorised")',
     'if False:\n            raise gl.vm.UserError(E + "not authorised")'),
    ("dispute", "the gate answer crosses consensus as a bool",
     '"judgeable": "yes" if value else "no",', '"judgeable": value,'),
    ("dispute", "only one presentation order is asked",
     "reverse = _ask(build_prompt(promise, request, response, timing, reverse=True))",
     "reverse = forward"),
    ("dispute", "a parse failure defaults to unclear",
     'raise gl.vm.UserError(L + "bad verdict")',
     'return {"verdict": "unclear", "reason": "unparseable"}'),
    ("dispute", "a model failure counts as agreement",
     "return _same_error(leader_message, getattr(error, \"message\", str(error)))",
     "return True"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", default="", help="write a markdown table to this path")
    args = parser.parse_args()

    work = pathlib.Path(tempfile.mkdtemp(prefix="recourse-mutate-"))
    try:
        # Everything the suite reads. Copying too little makes pytest fail to
        # collect, which exits non-zero with no FAILED line - and a runner that
        # reads any non-zero exit as a kill then reports a perfect score while
        # testing nothing. That happened here, and requiring a named test below
        # is what caught it. A list of folders went stale the same way once the
        # suite began reading the README, docs/, evidence/ and scripts/, so the
        # whole repository is copied, less what is enormous and irrelevant, and
        # never the keys or the local deployment record.
        shutil.copytree(
            ROOT, work, dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(
                ".git", ".venv", "node_modules", ".next", "out", "*.tsbuildinfo", "__pycache__",
                ".accounts.json", "deployed.json", ".env", ".env.local",
            ),
        )

        # The copy has no .git of its own, and git looking upward from a temp
        # folder can find an unrelated repository with none of this history,
        # where the commit order test reads an empty log. Pointing git at this
        # repository keeps the baseline the same suite the gate runs.
        env = dict(os.environ, GIT_DIR=str(ROOT / ".git"))

        baseline = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/direct/", "-q",
             "-p", "no:gltest", "-p", "no:gltest_direct"],
            cwd=work, capture_output=True, text=True, env=env,
        )
        if baseline.returncode != 0:
            print("The suite does not pass before any mutation, so nothing below means")
            print("anything. Fix that first.\n")
            print(baseline.stdout[-1500:])
            return 1
        print(f"baseline green: {baseline.stdout.strip().splitlines()[-1]}\n")
        originals = {
            (pair, name): (work / folder / f"{name}.py").read_text(encoding="utf-8")
            for pair, folder in PAIRS.items()
            for name in ("escrow", "dispute")
        }
        # Only the tests that execute or read a contract, and only their run
        # against the pair being mutated. Every module outside this list reads
        # the freeze record or the port, and would go red on ANY edit to a
        # contract file: a kill it scored would be a hash mismatch, not a
        # defence noticing it had gone.
        modules = [f"tests/direct/{name}.py" for name in CONTRACT_MODULES]

        rows: list[tuple[str, str, dict[str, str]]] = []
        escaped: list[str] = []
        for contract, label, old, new in MUTANTS:
            caught_by: dict[str, str] = {}
            for pair, folder in PAIRS.items():
                target = work / folder / f"{contract}.py"
                source = originals[(pair, contract)]
                if old not in source:
                    print(f"  STALE    {pair:6} {label}")
                    escaped.append(f"{label}, {pair} pair (the code it mutates has moved)")
                    continue
                target.write_text(source.replace(old, new, 1), encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", *modules, "-q", "-k", pair,
                     "-p", "no:gltest", "-p", "no:gltest_direct"],
                    cwd=work, capture_output=True, text=True, env=env,
                )
                target.write_text(source, encoding="utf-8")

                caught = [
                    line.split("::")[-1].split()[0]
                    for line in result.stdout.splitlines()
                    if line.startswith("FAILED")
                ]
                if result.returncode == 0 or not caught:
                    print(f"  ESCAPED  {pair:6} {label}")
                    escaped.append(f"{label}, {pair} pair")
                    continue
                print(f"  killed   {pair:6} {label}")
                # The id carries the pair in brackets; the table names the test.
                caught_by[pair] = caught[0].split("[")[0]
            if len(caught_by) == len(PAIRS):
                rows.append((contract, label, caught_by))

        print("\n" + "=" * 66)
        if escaped:
            print(f"{len(escaped)} mutant runs escaped, which is a coverage gap:")
            for item in escaped:
                print(f"  - {item}")
            print("\nWrite the test that would have caught it. No table is written.")
            return 1

        print(f"all {len(MUTANTS)} mutants killed on both pairs by the direct tests")
        if args.table:
            out = pathlib.Path(args.table)
            lines = [
                "# Mutations",
                "",
                "Generated by `python scripts/mutate.py --table docs/MUTATIONS.md`.",
                "",
                "Each row is a defence deleted on purpose and the test that noticed, once",
                "in the frozen pair (contracts/, deployed on studionet) and once in the",
                "ported pair (contracts/v06/, deployed on Studio Next). The generator",
                "refuses to write this file if anything escapes in either, so its",
                "existence is the claim and the rows are the evidence.",
                "",
                f"**{len(rows)} of {len(MUTANTS)} defences verified in both pairs.**",
                "",
                "| contract | defence removed | caught in the frozen pair by | caught in the ported pair by |",
                "| --- | --- | --- | --- |",
            ]
            for contract, label, caught_by in rows:
                lines.append(
                    f"| {contract} | {label} | `{caught_by['frozen']}` | `{caught_by['v06']}` |"
                )
            lines.append("")
            out.write_text("\n".join(lines), encoding="utf-8")
            print(f"wrote {out}")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
