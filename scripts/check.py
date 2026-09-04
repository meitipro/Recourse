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

    if not offenders:
        print(f"house style clean ({len(BANNED)} characters checked across {scanned} files)")
        return 0

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
