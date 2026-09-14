"""
The ported pair is the frozen pair with the runtime header, two imports and
four API names changed, and nothing else.

scripts/port.py generates contracts/v06/ from contracts/. These tests hold the
files on disk to that, hold FROZEN.json's second record to the files, and read
contracts/v06/PORT.diff line by line, so the claim a reader can check in ten
seconds is also one the gate checks on every run.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import port  # noqa: E402  scripts/port.py

RECORD = json.loads((ROOT / "contracts" / "FROZEN.json").read_text(encoding="utf-8"))


def test_the_ported_pair_on_disk_is_exactly_the_port_of_the_frozen_pair():
    assert port.stale() == []


def test_the_first_pair_keeps_its_hashes():
    assert RECORD["escrow"]["sha256"] == "d500b250355db5b87eb3014392444305e5a9c4e8fc78e58f49ad8312da8355cc"
    assert RECORD["dispute"]["sha256"] == "7781e46eddb165156499d47a60b708efeb1978e92f2c3fb977c47cc148fbc008"
    assert RECORD["runtime"] == port.RUNTIME_FROZEN


def test_frozen_json_records_the_ported_pair_its_runtime_and_its_diff():
    ported = RECORD["v06"]
    assert ported["runtime"] == port.RUNTIME_PORTED
    assert ported["diff"] == "contracts/v06/PORT.diff"
    for name in port.NAMES:
        data = (ROOT / ported[name]["path"]).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(data).hexdigest() == ported[name]["sha256"]
        assert len(data) == ported[name]["bytes"]


def test_every_line_the_diff_changes_is_the_header_an_import_or_an_api_name():
    diff = (ROOT / "contracts" / "v06" / "PORT.diff").read_text(encoding="utf-8")
    removed: list[str] = []
    added: list[str] = []
    for line in diff.splitlines():
        if not line or line.startswith(("#", "---", "+++", "@@")):
            continue
        (removed if line.startswith("-") else added).append(line[1:])

    depends = port.HEADER_PORTED.split("\n")[1]
    for old in removed:
        if old == port.HEADER_FROZEN:
            new = depends
        else:
            new = old
            for before, after in port.RENAMES:
                new = new.replace(before, after)
            assert new != old, f"the diff removes a line no rename explains: {old!r}"
        assert new in added, f"the diff changes {old!r} into something other than its rename"
        added.remove(new)

    # What is left is added outright: the version line and two imports, per file.
    assert sorted(added) == sorted(
        [
            "# v0.3.0",
            "from genlayer.storage import DynArray, TreeMap, allow as allow_storage",
            "import genlayer as gl",
        ]
        * len(port.NAMES)
    )
