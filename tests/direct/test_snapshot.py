"""
The recorded snapshot: what the chain held, written down so a testnet reset
cannot take the evidence with it.

These hold evidence/snapshot.json to the numbers the repository publishes
elsewhere. Re-run the evaluation, cite a new transaction in the README, or
change a refusal, and the gate fails here until python scripts/snapshot.py is
run again. Nothing here touches a network.
"""

from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = ROOT / "evidence" / "snapshot.json"
SNAPSHOT = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
FROZEN = json.loads((ROOT / "contracts" / "FROZEN.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")

HASH = re.compile(r"0x[0-9a-f]{64}")


def payments() -> list[dict]:
    return SNAPSHOT["payments"]


def decided() -> list[dict]:
    return [p for p in payments() if int(p["status"]) == 3]


def test_the_snapshot_is_of_the_frozen_pair_on_the_only_deployment():
    assert SNAPSHOT["network"] == "studionet"
    assert SNAPSHOT["chain_id"] == 61999
    entry = FROZEN["deployments"]["studionet"]
    assert SNAPSHOT["escrow"] == entry["escrow"]
    assert SNAPSHOT["dispute"] == entry["dispute"]
    assert SNAPSHOT["frozen"]["escrow_sha256"] == FROZEN["escrow"]["sha256"]
    assert SNAPSHOT["frozen"]["dispute_sha256"] == FROZEN["dispute"]["sha256"]
    assert SNAPSHOT["recorded_at_iso"].endswith("Z")
    assert "temporary testnet" in SNAPSHOT["note"]


def test_the_totals_are_recomputable_from_the_rows_by_the_feeds_rules():
    totals = SNAPSHOT["totals"]
    rows = payments()
    assert totals["payments"] == len(rows) == int(SNAPSHOT["stats"]["payments"])
    assert totals["disputes_opened"] == sum(1 for p in rows if int(p["status"]) in (2, 3))
    judged = decided()
    assert totals["decided"] == len(judged)
    assert totals["upheld"] == sum(1 for p in judged if int(p["verdict"]) == 2)
    assert totals["unjudgeable"] == sum(1 for p in judged if int(p["verdict"]) == 3)
    if judged:
        assert totals["upheld_rate"] == round(totals["upheld"] / len(judged), 4)
        assert totals["unjudgeable_rate"] == round(totals["unjudgeable"] / len(judged), 4)
    # The feed's median: sorted, the element at n // 2. web/components/Feed.tsx does the same.
    elapsed = sorted(
        p["case"]["decided_at"] - p["created_at"]
        for p in judged
        if p.get("case") and p["case"]["decided_at"] > p["created_at"]
    )
    assert totals["median_pay_to_dispute_seconds"] == (elapsed[len(elapsed) // 2] if elapsed else None)
    assert totals["transactions"] == len(SNAPSHOT["transactions"])
    assert totals["refusals"] == len(SNAPSHOT["refusals"])
    for name in ("open", "withdrawn", "disputed", "resolved"):
        assert totals["by_status"][name] == sum(1 for p in rows if p["status_name"] == name)


def test_every_case_sits_on_a_decided_payment_and_agrees_with_it():
    by_pid = {p["pid"]: p for p in payments()}
    assert len(SNAPSHOT["cases"]) == len(decided())
    for case in SNAPSHOT["cases"]:
        payment = by_pid[case["pid"]]
        assert payment["case"] == case
        assert payment["verdict_name"] == case["verdict_name"]
        assert int(payment["status"]) == 3
        # A settled case has the transactions that settled it.
        assert payment["transactions"]["open_dispute"], case["pid"]
        assert payment["transactions"]["adjudicate"], case["pid"]
        assert payment["transactions"]["settle"], case["pid"]


def test_every_payment_has_its_pay_transaction_and_only_settled_ones_have_settle():
    for payment in payments():
        tx = payment["transactions"]
        assert tx["pay"] and HASH.fullmatch(tx["pay"]), payment["pid"]
        assert tx["pay"] in tx["every_attempt"]
        if payment["status_name"] == "withdrawn":
            assert tx["withdraw"] and not tx["open_dispute"], payment["pid"]
        if payment["status_name"] == "open":
            assert not tx["settle"] and not tx["withdraw"], payment["pid"]


def test_every_transaction_the_readme_cites_is_in_the_snapshot():
    cited = set(HASH.findall(README))
    assert cited, "the README cites no transactions, which is not what it does"
    have = {t["hash"] for t in SNAPSHOT["transactions"]}
    missing = sorted(cited - have)
    assert not missing, f"the README cites transactions the snapshot does not have: {missing}. Run python scripts/snapshot.py"


def test_the_readmes_refusal_table_is_in_the_snapshot_word_for_word():
    table = re.findall(
        r"\| `([a-z_]+)`[^|]*\| `(\[EXPECTED\][^`]*)` \| \[0x[0-9a-f]+\.\.\.\]\([^)]*/tx/(0x[0-9a-f]{64})\)",
        README,
    )
    assert len(table) == 4, "the README publishes four refusals"
    by_hash = {r["hash"]: r for r in SNAPSHOT["refusals"]}
    for method, refusal, tx_hash in table:
        assert tx_hash in by_hash, f"{method} refusal {tx_hash} is not a refusal in the snapshot"
        assert by_hash[tx_hash]["method"] == method
        assert by_hash[tx_hash]["refusal"] == refusal
    # Every refusal in the snapshot is one the contract wrote, in its own words.
    for refusal in SNAPSHOT["refusals"]:
        assert refusal["refusal"].startswith("[EXPECTED]")


def test_the_evaluation_numbers_match_the_measurement_files_and_the_reports():
    for name, results, report in (("v1", "results.json", "RESULTS.md"), ("v2", "results-v2.json", "RESULTS-V2.md")):
        measured = json.loads((ROOT / "eval" / results).read_text(encoding="utf-8"))
        recorded = SNAPSHOT["evaluation"][name]
        for key in ("instance", "network", "n", "runs", "accuracy", "stability", "unclear", "measured_at"):
            assert recorded[key] == measured[key], f"{name}.{key}: snapshot {recorded[key]}, measurement {measured[key]}"
        text = (ROOT / "eval" / report).read_text(encoding="utf-8")
        assert f"**{recorded['accuracy']}/{recorded['n']}**" in text, f"{report} does not carry the snapshot's accuracy"
        assert f"| {recorded['stability']}/{recorded['n']} |" in text, f"{report} does not carry the snapshot's stability"
        assert f"`{recorded['instance']}`" in text
    v1, v2 = SNAPSHOT["evaluation"]["v1"], SNAPSHOT["evaluation"]["v2"]
    assert f"{v1['accuracy']}/{v1['n']}" in README
    assert f"{v2['accuracy']}/{v2['n']}" in README


def test_the_receipts_are_raw_and_belong_to_the_cycles_named():
    by_pid = {p["pid"]: p for p in payments()}
    for label in ("contested", "honest"):
        info = SNAPSHOT["receipts"][label]
        payment = by_pid[info["pid"]]
        assert info["files"], f"no {label} receipts"
        folder = ROOT / "evidence" / "receipts" / f"{label}-{info['pid']}"
        on_disk = sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in folder.glob("*.json"))
        assert on_disk == sorted(info["files"]), f"{label}: files on disk and files listed differ"
        for rel in info["files"]:
            receipt = json.loads((ROOT / rel).read_text(encoding="utf-8"))
            assert receipt["hash"] in payment["transactions"]["every_attempt"], rel
            assert receipt["hash"][2:14] in rel
            # The RPC's own fields, present because nothing was edited out.
            for key in ("consensus_data", "status", "from_address", "to_address", "created_at"):
                assert key in receipt, f"{rel} lacks {key}"
    contested = by_pid[SNAPSHOT["receipts"]["contested"]["pid"]]
    assert contested["status_name"] == "resolved" and contested["verdict_name"] == "not_honored"
    honest = by_pid[SNAPSHOT["receipts"]["honest"]["pid"]]
    assert honest["status_name"] == "withdrawn" and not honest["transactions"]["open_dispute"]


def test_the_snapshot_carries_no_private_material():
    text = SNAPSHOT_PATH.read_text(encoding="utf-8").lower()
    keys = ROOT / ".accounts.json"
    if keys.exists():
        for account in json.loads(keys.read_text(encoding="utf-8")).values():
            secret = account if isinstance(account, str) else account.get("private_key") or account.get("key") or ""
            if isinstance(secret, str) and len(secret) >= 32:
                assert secret.lower().removeprefix("0x") not in text
    assert "private_key" not in text
