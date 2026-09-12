"""
scripts/smoke.py without a network: what it says it did not prove.

The script turns the dashboard settings into one command that names the wrong
one. Its last lines name what a pass does not prove, and those lines are held
here to what a run actually proved, so they cannot become a stale sentence of
their own.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def smoke():
    spec = importlib.util.spec_from_file_location("recourse_smoke", ROOT / "scripts" / "smoke.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_blind_spots_name_what_a_run_left_unproven_and_nothing_it_proved():
    module = smoke()
    everything = dict(module.blind_spots(key_proven=True, unread=[], mcp_ran=True, mcp="https://m/api/mcp"))
    assert set(everything) == {"the bot", "the key's spend limit"}, "what no request here can reach, and nothing else"
    assert "not hosted" in everything["the bot"] and "key of its own" in everything["the bot"]
    little = dict(module.blind_spots(key_proven=False, unread=["the feed came from the recorded snapshot"], mcp_ran=False, mcp="https://m/api/mcp"))
    assert "stage 2" in little["the model key"] and "verdict" in little["the model key"]
    assert "recorded snapshot" in little["the site's own read of studionet"]
    assert little["the MCP server"].endswith("node test/probe.mjs https://m/api/mcp")


def test_the_blind_spots_are_printed_last_whether_or_not_the_checks_passed(monkeypatch, capsys):
    module = smoke()
    monkeypatch.setattr(sys, "argv", ["smoke.py"])
    monkeypatch.setattr(module, "run", lambda site, linter, mcp: ([("site answers", False)], module.blind_spots(False, [], True, mcp)))
    assert module.main() == 1
    out = capsys.readouterr().out
    assert "0 of 1 passed" in out
    last = out.split("Not proven by this run")[-1]
    assert "the bot:" in last and "the model key:" in last
