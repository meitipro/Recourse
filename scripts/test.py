#!/usr/bin/env python3
"""
Everything that can fail without the chain.

    python scripts/test.py               # all of it
    python scripts/test.py --no-lint     # without genvm-lint: CI's direct job
    python scripts/test.py --only-lint   # genvm-lint alone: CI's lint job

Freeze and house style, then both contracts through the linter, then the
direct tests, then the feed's types when web/node_modules exists.

House style and the direct tests need no network. The contract lint step does
on a cold cache: genvm-lint fetches a 134MB runner the first time. Use --no-lint
for a genuinely offline run. CI splits the two for the same reason.

The direct tests are run with the gltest plugins disabled. genlayer-test is
installed globally here and registers two auto loading pytest plugins; one of
them reads any gltest config in the working directory and aborts the whole run
before collection, so a plain pytest repo fails in a way that looks like a repo
defect and is not one.
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def run(label: str, command: list[str], env: dict | None = None) -> bool:
    print(f"\n=== {label} " + "=" * max(0, 56 - len(label)))
    merged = dict(os.environ)
    if env:
        merged.update(env)
    # Never shell=True: these repos live under a path with a space in it and the
    # shell splits on it, so the tool reports an unrecognised argument for every
    # file and it reads as a broken tool.
    result = subprocess.run(command, cwd=ROOT, env=merged)
    if result.returncode != 0:
        print(f"--- {label} FAILED (exit {result.returncode})")
    return result.returncode == 0


def readme_states_the_test_count(python: str) -> bool:
    """
    The README says how many direct tests there are. A count typed once goes
    stale the day a test is added, and it did, so the gate reads it off pytest.
    """
    print("\n=== readme test count " + "=" * 35)
    collected = subprocess.run(
        [python, "-m", "pytest", "tests/direct/", "--collect-only", "-q", "-p", "no:gltest", "-p", "no:gltest_direct"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    found = re.search(r"(\d+) tests? collected", collected.stdout)
    stated = set(re.findall(r"(\d+) direct tests", (ROOT / "README.md").read_text(encoding="utf-8")))
    if not found:
        print("--- could not read a count from pytest")
        return False
    if stated != {found.group(1)}:
        print(f"--- README states {sorted(stated)} direct tests, pytest collects {found.group(1)}")
        return False
    print(f"README and pytest agree: {found.group(1)} direct tests")
    return True


def main() -> int:
    skip_lint = "--no-lint" in sys.argv
    only_lint = "--only-lint" in sys.argv
    python = sys.executable
    # The linter prints a tick and dies on it under the ansi codepage Windows
    # gives a child process, reporting a passing contract as failed.
    lint_env = {"PYTHONIOENCODING": "utf-8"}

    steps = [
        ("house style", [python, "scripts/check.py"], None),
        ("lint escrow", ["genvm-lint", "lint", "contracts/escrow.py"], lint_env),
        ("lint dispute", ["genvm-lint", "lint", "contracts/dispute.py"], lint_env),
        ("validate escrow", ["genvm-lint", "validate", "contracts/escrow.py"], lint_env),
        ("validate dispute", ["genvm-lint", "validate", "contracts/dispute.py"], lint_env),
        (
            "direct tests",
            [
                python, "-m", "pytest", "tests/direct/", "-q",
                "-p", "no:gltest", "-p", "no:gltest_direct",
            ],
            None,
        ),
    ]

    if skip_lint:
        steps = [step for step in steps if not step[0].startswith(("lint ", "validate "))]
    if only_lint:
        steps = [step for step in steps if step[0].startswith(("lint ", "validate "))]

    failed = [label for label, command, env in steps if not run(label, command, env)]
    if not only_lint and not readme_states_the_test_count(python):
        failed.append("readme test count")

    # The feed is only checked when it has been installed. A judge cloning this
    # to read the contracts should not be told the repository is broken because
    # they have not run npm install.
    if only_lint:
        pass
    elif (ROOT / "web" / "node_modules").is_dir():
        npx = "npx.cmd" if os.name == "nt" else "npx"
        result = subprocess.run(
            [npx, "tsc", "--noEmit"], cwd=ROOT / "web", env=dict(os.environ)
        )
        print("\n=== feed types " + "=" * 47)
        if result.returncode != 0:
            print("--- feed types FAILED")
            failed.append("feed types")
    else:
        print("\n=== feed types: skipped, web/node_modules is not installed")

    print("\n" + "=" * 62)
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print("all green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
