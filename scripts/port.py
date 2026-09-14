#!/usr/bin/env python3
"""
The ported pair, generated from the frozen one.

    python scripts/port.py           # write contracts/v06/ from contracts/
    python scripts/port.py --check   # exit 1 unless contracts/v06/ is exactly that

Studio Next runs a newer GenVM runtime, py-genlayer:5jycge4q. Its standard
library renamed four APIs and stopped exporting `gl`, `TreeMap`, `DynArray`
and the storage decorator through `from genlayer import *`, so the frozen pair
cannot load there: a deploy finishes `invalid_contract runner malformed`, and
no first line changes that. This writes a second pair beside the first.

The port is a function of the frozen pair, not a second copy edited by hand.
Everything it changes is in the tables below: the runtime header, two import
lines, and four API names. The logic, the prompt and every string are the
frozen pair's. The gate runs this with --check, so contracts/v06/ cannot drift
from what the tables produce, and contracts/v06/PORT.diff, which this also
writes, is always the whole difference.
"""

from __future__ import annotations

import difflib
import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FROZEN_DIR = ROOT / "contracts"
PORT_DIR = ROOT / "contracts" / "v06"
NAMES = ("escrow", "dispute")
NL = "\n"

RUNTIME_FROZEN = "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6"
RUNTIME_PORTED = "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng"

#: The first line of each frozen file, and what replaces it. The version line
#: is how the executor reads which ABI a contract was written against; Studio's
#: own examples for this runtime open with the same two lines.
HEADER_FROZEN = '# { "Depends": "' + RUNTIME_FROZEN + '" }'
HEADER_PORTED = "# v0.3.0" + NL + '# { "Depends": "' + RUNTIME_PORTED + '" }'

#: The star import stays. Under the new runtime it no longer brings the storage
#: types or the decorator, so those are imported by name from genlayer.storage,
#: and `gl` is bound to the package itself. The decorator keeps its old name
#: through the alias, which is also the name genvm-lint's storage rule reads.
STAR = "from genlayer import *"

#: The four renames. Each is the same function under its new name:
#: run_nondet_unsafe and run_nondet have the same body line for line, and so do
#: allow_storage and allow; message_raw and message.raw are the same decoded
#: dict; contract.Contract and contract.get_at are the names the standard
#: library's own module docstring gives for declaring and calling a contract.
RENAMES = (
    ("gl.Contract)", "gl.contract.Contract)"),
    ("gl.get_contract_at", "gl.contract.get_at"),
    ("gl.vm.run_nondet_unsafe", "gl.vm.run_nondet"),
    ("gl.message_raw", "gl.message.raw"),
)

DIFF_HEADER = (
    "# contracts/v06/PORT.diff, written by scripts/port.py. Do not edit it.",
    "#",
    "# The whole difference between the frozen pair in contracts/, which runs on",
    "# studionet under " + RUNTIME_FROZEN + ",",
    "# and the ported pair in contracts/v06/, which runs on Studio Next under",
    "# " + RUNTIME_PORTED + ".",
    "#",
    "# Every changed line is the runtime header, an import, or differs only in one",
    "# of four API names: gl.Contract, gl.get_contract_at, gl.vm.run_nondet_unsafe",
    "# and gl.message_raw. The logic, the prompt and every string are unchanged.",
    "",
)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def frozen_text(name: str) -> str:
    """The frozen file as deployed: LF line endings, whatever the checkout wrote."""
    return (FROZEN_DIR / f"{name}.py").read_bytes().replace(b"\r\n", b"\n").decode("utf-8")


def storage_import(text: str) -> str:
    used = [kind for kind in ("DynArray", "TreeMap") if re.search(r"\b" + kind + r"\b", text)]
    return "from genlayer.storage import " + ", ".join(used + ["allow as allow_storage"])


def port(name: str, text: str) -> str:
    """One frozen file, ported. Refuses a file that is not shaped like the frozen pair."""
    if not text.startswith(HEADER_FROZEN + NL):
        raise SystemExit(f"contracts/{name}.py does not open with the frozen runtime header")
    if text.count(STAR) != 1:
        raise SystemExit(f"contracts/{name}.py does not have exactly one star import")
    out = HEADER_PORTED + text[len(HEADER_FROZEN):]
    out = out.replace(STAR, STAR + NL + storage_import(text) + NL + "import genlayer as gl", 1)
    for old, new in RENAMES:
        out = out.replace(old, new)
    return out


def render_diff(frozen: dict[str, str], ported: dict[str, str]) -> str:
    lines = list(DIFF_HEADER)
    for name in NAMES:
        lines.extend(
            difflib.unified_diff(
                frozen[name].split(NL),
                ported[name].split(NL),
                fromfile=f"contracts/{name}.py",
                tofile=f"contracts/v06/{name}.py",
                lineterm="",
                n=0,
            )
        )
    return NL.join(lines) + NL


def build() -> dict[str, str]:
    """Every file under contracts/v06/, keyed by name, as the tables produce it."""
    frozen = {name: frozen_text(name) for name in NAMES}
    ported = {name: port(name, frozen[name]) for name in NAMES}
    files = {f"{name}.py": ported[name] for name in NAMES}
    files["PORT.diff"] = render_diff(frozen, ported)
    return files


def stale() -> list[str]:
    """The files under contracts/v06/ that differ from the port, empty when current."""
    out = []
    for filename, text in build().items():
        path = PORT_DIR / filename
        on_disk = path.read_bytes().replace(b"\r\n", b"\n") if path.exists() else None
        if on_disk != text.encode("utf-8"):
            out.append(f"contracts/v06/{filename}")
    return out


def main() -> int:
    if "--check" in sys.argv:
        problems = stale()
        if problems:
            print("contracts/v06 is not the port of the frozen pair: " + ", ".join(problems))
            print("Run python scripts/port.py, and never edit contracts/v06/ by hand.")
            return 1
        print("contracts/v06 is exactly the port of the frozen pair")
        return 0
    PORT_DIR.mkdir(exist_ok=True)
    for filename, text in build().items():
        (PORT_DIR / filename).write_bytes(text.encode("utf-8"))
        size = len(text.encode("utf-8"))
        print(f"  contracts/v06/{filename:11} {size:6} bytes  sha256 {sha256(text)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
