#!/usr/bin/env python3
"""
Break the escrow on purpose, seven ways, and check the suite goes red each time.

    python scripts/mutate.py

A green suite says the tests agree with the code. It does not say the tests
would notice if the code were wrong, and those are different claims. Every guard
in a contract is worth exactly as much as the test that fails when you delete
it, so this deletes them one at a time and reports any that nothing catches.

It never edits the repository. The contract and tests are copied to a scratch
directory, mutated there, and the copy is thrown away.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: (what is being broken, the code to replace, what to replace it with).
#: Each one is a real bug someone could write, not a syntactic mangling.
MUTANTS = [
    (
        "settle accepts any caller",
        'if gl.message.sender_address != self.dispute_contract:\n'
        '            raise gl.vm.UserError(E + "not authorised")',
        'if False:\n            raise gl.vm.UserError(E + "not authorised")',
    ),
    (
        "withdraw before the window closes",
        'if self._now() <= payment.window_ends:\n'
        '            raise gl.vm.UserError(E + "window open")',
        'if False:\n            raise gl.vm.UserError(E + "window open")',
    ),
    (
        "dispute without a recorded response",
        'if payment.response == "":\n            raise gl.vm.UserError(E + "no response")',
        'if False:\n            raise gl.vm.UserError(E + "no response")',
    ),
    (
        "settle pays the buyer twice",
        "self._send(payment.buyer, u256(payment.amount + payment.bond))",
        "self._send(payment.buyer, payment.amount)\n"
        "            self._send(payment.buyer, payment.bond)\n"
        "            self._send(payment.buyer, u256(0))",
    ),
    (
        "the bond is never added to held",
        "self.held = u256(self.held + gl.message.value)",
        "self.held = u256(self.held + u256(0))",
    ),
    (
        "a response can be overwritten",
        'if payment.response != "":\n'
        '            raise gl.vm.UserError(E + "response already recorded")',
        'if False:\n            raise gl.vm.UserError(E + "response already recorded")',
    ),
    (
        "paying does not count as a live payment",
        "self.sellers[addr].live = u32(entry.live + u32(1))",
        "self.sellers[addr].live = u32(entry.live + u32(0))",
    ),
]


def main() -> int:
    work = pathlib.Path(tempfile.mkdtemp(prefix="recourse-mutate-"))
    try:
        for name in ("contracts", "tests", "eval"):
            shutil.copytree(ROOT / name, work / name, dirs_exist_ok=True)
        target = work / "contracts" / "escrow.py"
        original = target.read_text(encoding="utf-8")

        survived: list[str] = []
        for label, old, new in MUTANTS:
            if old not in original:
                print(f"  SKIP     {label}: the code it mutates has moved")
                survived.append(f"{label} (mutation no longer applies)")
                continue
            target.write_text(original.replace(old, new, 1), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/direct/", "-q",
                 "-p", "no:gltest", "-p", "no:gltest_direct"],
                cwd=work,
                capture_output=True,
                text=True,
            )
            killed = result.returncode != 0
            print(f"  {'KILLED  ' if killed else 'SURVIVED'} {label}")
            if not killed:
                survived.append(label)
        target.write_text(original, encoding="utf-8")

        print("\n" + "=" * 62)
        if survived:
            print(f"{len(survived)} of {len(MUTANTS)} mutants survived, which is a coverage gap:")
            for item in survived:
                print(f"  - {item}")
            print("\nWrite the test that would have caught it.")
            return 1
        print(f"all {len(MUTANTS)} mutants killed by the direct tests")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
