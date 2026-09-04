#!/usr/bin/env python3
"""
Everything that can fail without touching the network.

    python scripts/test.py

House style, then both contracts through the linter, then the direct tests. It
runs in about ten seconds and it is what should be green before any deploy.

The direct tests are run with the gltest plugins disabled. genlayer-test is
installed globally here and registers two auto loading pytest plugins; one of
them reads any gltest config in the working directory and aborts the whole run
before collection, so a plain pytest repo fails in a way that looks like a repo
defect and is not one.
"""

from __future__ import annotations

import os
import pathlib
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


def main() -> int:
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

    failed = [label for label, command, env in steps if not run(label, command, env)]

    # The feed is only checked when it has been installed. A judge cloning this
    # to read the contracts should not be told the repository is broken because
    # they have not run npm install.
    if (ROOT / "web" / "node_modules").is_dir():
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
