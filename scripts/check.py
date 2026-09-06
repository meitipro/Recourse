#!/usr/bin/env python3
"""
House style, as a check that fails.

    python scripts/check.py

Nine characters are banned. The spaced hyphen is the only connector. Intending
to remember this does not work: the rule has been broken on six projects, always
because it was read after the work was done. A check that fails catches it
without anyone having to think of it, which is the only mechanism that has ever
worked.

Two rules about the checker itself, both learned the hard way:

  1 Build the patterns from escape sequences. Written literally, this file would
    contain every character it bans and report itself on every clean run, which
    is how a check becomes noise people skip.
  2 Scan for HTML entities too. A source scan sees the entity as ascii letters
    and passes it; the browser renders the character.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

BANNED = {
    "—": ("em dash", " - "),
    "–": ("en dash", " - "),
    "‐": ("hyphen", "-"),
    "‒": ("figure dash", "-"),
    "―": ("horizontal bar", "-"),
    "−": ("minus sign", "-"),
    "·": ("middle dot", " - "),
    "•": ("bullet", " - "),
    "…": ("ellipsis", "..."),
}

ENTITIES = ["mdash", "ndash", "hellip", "bull", "middot", "minus"]

SCAN = {".py", ".ts", ".tsx", ".js", ".mjs", ".jsx", ".json", ".md", ".css", ".html", ".sh", ".txt"}

SKIP_DIRS = {
    ".git", "node_modules", ".next", "__pycache__", ".venv", "out", "dist", "build",
}

# Files exempt by name, each with the reason written out. A blanket pattern here
# would quietly stop checking things nobody meant to exempt.
EXEMPT = {
    # This file names every character it bans, in the table above.
    "scripts/check.py",
}


def files():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SCAN:
            continue
        relative = path.relative_to(ROOT).as_posix()
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if relative in EXEMPT:
            continue
        yield relative, path


def frozen_contracts() -> list[str]:
    """
    The contracts are frozen at the deployed bytes, and this is the check rather
    than the promise.

    Every published number is tied to one pair of addresses: verify.py lints the
    deployed bytes against these files, both evaluation reports name the instance
    they were measured on, and the refusal and rail transactions in the README
    were recorded against these contracts. An edit here, however small, is a
    redeploy, and a redeploy is 63 consensus transactions to restore the
    evidence plus the chance that a re-run moves a number already published.

    Hashes are taken over LF-normalised bytes. deploy.py reads with universal
    newlines, so that is what is on chain, and it is the only form that is the
    same on a Windows checkout with autocrlf and on anything else.
    """
    record_path = ROOT / "contracts" / "FROZEN.json"
    if not record_path.exists():
        return ["contracts/FROZEN.json is missing, so the freeze cannot be checked"]
    record = json.loads(record_path.read_text(encoding="utf-8"))
    problems: list[str] = []
    for name in ("escrow", "dispute"):
        path = ROOT / "contracts" / f"{name}.py"
        normalised = path.read_bytes().replace(b"\r\n", b"\n")
        actual = hashlib.sha256(normalised).hexdigest()
        if actual != record[name]["sha256"]:
            problems.append(
                f"contracts/{name}.py is FROZEN at the deployed bytes and has been edited.\n"
                f"    now     {actual}\n"
                f"    frozen  {record[name]['sha256']}  ({record[name]['address']})"
            )
    # A deployment on disk that is not the frozen one means a redeploy happened
    # without the rest of the repository following it.
    deployed_path = ROOT / "deployed.json"
    if deployed_path.exists():
        try:
            deployed = json.loads(deployed_path.read_text(encoding="utf-8"))
            for name in ("escrow", "dispute"):
                if deployed.get(name, "").lower() != record[name]["address"].lower():
                    problems.append(
                        f"deployed.json names {name} {deployed.get(name)} but the frozen "
                        f"deployment is {record[name]['address']}"
                    )
        except (ValueError, KeyError):
            problems.append("deployed.json could not be read against the freeze")
    if problems:
        problems.append(
            "Every published number is tied to the frozen pair. If a change is genuinely\n"
            "  required: change it, redeploy, re-run BOTH evaluation sets, re-run\n"
            "  scripts/evidence.py and scripts/rail.py, and update contracts/FROZEN.json\n"
            "  and every published number in the same commit. The exact commands are\n"
            "  listed in FROZEN.json under if_a_change_is_genuinely_required."
        )
    return problems


def main() -> int:
    entity_pattern = re.compile(
        chr(38) + "(?:" + "|".join(ENTITIES) + "|#8212|#8211|#8230|#183|#8226);"
    )
    offenders: dict[str, list[str]] = {}
    scanned = 0

    for relative, path in files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        hits: list[str] = []
        for line_number, line in enumerate(text.splitlines(), 1):
            for character, (name, replacement) in BANNED.items():
                if character in line:
                    hits.append(f"    line {line_number}: {name}, use {replacement.strip() or '-'}")
            found = entity_pattern.search(line)
            if found:
                hits.append(f"    line {line_number}: html entity {found.group(0)}")
        if hits:
            offenders[relative] = hits

    freeze = frozen_contracts()
    if freeze:
        print("contracts are frozen:")
        for line in freeze:
            print(f"  {line}")
    else:
        print("contracts frozen at the deployed bytes, unchanged")

    if not offenders:
        print(f"house style clean ({len(BANNED)} characters checked across {scanned} files)")
        return 1 if freeze else 0

    total = sum(len(hits) for hits in offenders.values())
    print(f"house style: {total} across {len(offenders)} files")
    for name, hits in offenders.items():
        print(f"  {name}")
        for hit in hits[:8]:
            print(hit)
        if len(hits) > 8:
            print(f"    and {len(hits) - 8} more")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
