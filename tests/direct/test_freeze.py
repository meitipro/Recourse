"""
The freeze record: hashes stay put, deployments are keyed by network, and the
gate's check refuses the mistakes a second network makes possible.

The check itself is tested as a pure function so no test ever touches the
real FROZEN.json or deployed.json.
"""

from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import check  # noqa: E402  scripts/check.py
from shared import chain  # noqa: E402

RECORD = json.loads((ROOT / "contracts" / "FROZEN.json").read_text(encoding="utf-8"))


def real_hashes() -> dict:
    return {
        name: hashlib.sha256((ROOT / "contracts" / f"{name}.py").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for name in ("escrow", "dispute")
    }


def test_the_two_hashes_are_where_they_were_and_match_the_files():
    hashes = real_hashes()
    assert RECORD["escrow"]["sha256"] == hashes["escrow"]
    assert RECORD["dispute"]["sha256"] == hashes["dispute"]
    # Addresses live under deployments now, not beside the hashes.
    assert "address" not in RECORD["escrow"] and "address" not in RECORD["dispute"]


def test_studionet_entry_is_the_frozen_pair_on_chain_61999():
    entry = RECORD["deployments"]["studionet"]
    assert entry["chain_id"] == 61999
    assert entry["escrow"] == "0x5125De939F7373eAE741B133FB32B7E9915C8F78"
    assert entry["dispute"] == "0x80A98929EcA334804dbB04d31F6050bca42C0Cc4"
    assert entry["frozen_at_commit"] == "ccc470a"


def test_the_real_record_passes_the_gate():
    assert check.freeze_problems(RECORD, real_hashes(), None) == []


def test_the_gate_and_the_chain_module_agree_on_chain_ids():
    assert check.KNOWN_CHAIN_IDS == chain.KNOWN_CHAIN_IDS


def test_an_edited_contract_fails_whatever_the_deployments_say():
    hashes = real_hashes()
    hashes["escrow"] = "0" * 64
    problems = check.freeze_problems(RECORD, hashes, None)
    assert any("escrow.py is FROZEN" in p for p in problems)


def test_a_network_with_the_wrong_chain_id_fails():
    record = copy.deepcopy(RECORD)
    record["deployments"]["bradbury"] = dict(record["deployments"]["studionet"], chain_id=61999)
    problems = check.freeze_problems(record, real_hashes(), None)
    assert any("bradbury.chain_id is 61999, but bradbury is chain 4221" in p for p in problems)


def test_an_unknown_network_fails():
    record = copy.deepcopy(RECORD)
    record["deployments"]["mainnet"] = dict(record["deployments"]["studionet"], chain_id=1)
    problems = check.freeze_problems(record, real_hashes(), None)
    assert any("mainnet names a network this repository does not know" in p for p in problems)


def test_a_second_network_with_the_right_id_extends_the_record_without_breaking_it():
    record = copy.deepcopy(RECORD)
    record["deployments"]["bradbury"] = dict(
        record["deployments"]["studionet"],
        chain_id=4221,
        escrow="0x" + "ab" * 20,
        dispute="0x" + "cd" * 20,
    )
    assert check.freeze_problems(record, real_hashes(), None) == []


def test_deployed_json_must_point_at_a_frozen_deployment_of_its_own_network():
    good = {"network": "studionet", **{k: RECORD["deployments"]["studionet"][k] for k in ("escrow", "dispute")}}
    assert check.freeze_problems(RECORD, real_hashes(), good) == []
    wrong_network = dict(good, network="bradbury")
    assert any("has no frozen deployment" in p for p in check.freeze_problems(RECORD, real_hashes(), wrong_network))
    wrong_address = dict(good, escrow="0x" + "ee" * 20)
    assert any("names escrow" in p for p in check.freeze_problems(RECORD, real_hashes(), wrong_address))


def test_load_deployment_refuses_a_record_for_another_network(monkeypatch, tmp_path):
    record = tmp_path / "deployed.json"
    record.write_text(json.dumps({"network": "studionet", "escrow": "0x0", "dispute": "0x0"}), encoding="utf-8")
    monkeypatch.setattr(chain, "DEPLOYED", record)
    monkeypatch.setenv("RECOURSE_NETWORK", "bradbury")
    import pytest

    with pytest.raises(SystemExit, match="deployed.json is for studionet but RECOURSE_NETWORK is bradbury"):
        chain.load_deployment()
    monkeypatch.setenv("RECOURSE_NETWORK", "studionet")
    assert chain.load_deployment()["network"] == "studionet"
