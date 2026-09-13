"""
The recorded snapshot: what the chain held, written down so a testnet reset
cannot take the evidence with it.

These hold evidence/snapshot.json to the numbers the repository publishes
elsewhere. Re-run the evaluation, cite a new transaction in the README, or
change a refusal, and the gate fails here until python scripts/snapshot.py is
run again. Nothing here touches a network.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import re
import subprocess

import pytest

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


#: What each labelled receipt set must be a cycle of: (status, verdict or None).
#: A label present in the snapshot but not here is a label nobody defined.
CYCLE_SHAPES = {
    "contested": ("resolved", "not_honored"),
    "honest": ("withdrawn", None),
    "honored": ("resolved", "honored"),
    "unclear": ("resolved", "unclear"),
}


def test_the_receipts_are_raw_and_belong_to_the_cycles_named():
    by_pid = {p["pid"]: p for p in payments()}
    assert SNAPSHOT["receipts"], "the snapshot names no receipt sets"
    for label, info in SNAPSHOT["receipts"].items():
        assert label in CYCLE_SHAPES, f"{label} is a receipt set with no defined shape"
        status, verdict = CYCLE_SHAPES[label]
        payment = by_pid[info["pid"]]
        assert payment["status_name"] == status, f"{label}: {info['pid']} is {payment['status_name']}"
        if verdict:
            assert payment["verdict_name"] == verdict, f"{label}: {info['pid']} ruled {payment['verdict_name']}"
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
    honest = by_pid[SNAPSHOT["receipts"]["honest"]["pid"]]
    assert not honest["transactions"]["open_dispute"], "the honest cycle was disputed"
    assert honest["transactions"]["withdraw"], "the honest cycle was never withdrawn"


def test_the_public_record_carries_all_three_verdicts():
    """
    A record of nothing but not_honored reads as a buyer-side tool rather than
    an adjudicator, whatever the evaluation set shows. All three verdicts are on
    chain, and each one has its raw receipts.
    """
    verdicts = SNAPSHOT["totals"]["verdicts"]
    for name in ("honored", "not_honored", "unclear"):
        assert verdicts[name] >= 1, f"no dispute on the public record was ruled {name}"
    assert sum(verdicts.values()) == SNAPSHOT["totals"]["decided"]
    assert SNAPSHOT["totals"]["upheld_rate"] < 1.0, "every dispute on the record went the buyer's way"
    for label in ("contested", "honored", "unclear"):
        assert label in SNAPSHOT["receipts"], f"no raw receipts for the {label} cycle"


def test_the_snapshot_carries_no_private_material():
    text = SNAPSHOT_PATH.read_text(encoding="utf-8").lower()
    keys = ROOT / ".accounts.json"
    if keys.exists():
        for account in json.loads(keys.read_text(encoding="utf-8")).values():
            secret = account if isinstance(account, str) else account.get("private_key") or account.get("key") or ""
            if isinstance(secret, str) and len(secret) >= 32:
                assert secret.lower().removeprefix("0x") not in text
    assert "private_key" not in text


def _epoch(value: str) -> float:
    return datetime.datetime.fromisoformat(value).timestamp()


def test_the_settlement_timings_the_site_and_readme_state_are_the_chains_own():
    """
    The README's timing block, the site's section 04 and its section 07 state
    four numbers about settlement. All four are totals here, each recomputed
    from the transactions by walking the hashes that link them, open_dispute
    to adjudicate to settle to payout, and each is held to where it is printed.
    """
    txs = SNAPSHOT["transactions"]
    by_hash = {t["hash"]: t for t in txs}
    verdict = {p["pid"]: p["verdict_name"] for p in payments()}
    to_verdict, money_back, finality, committee = [], [], [], []
    for judged in txs:
        if judged["method"] != "adjudicate" or judged["execution"] != "SUCCESS":
            continue
        if judged.get("validators"):
            committee.append(judged["validators"])
        opener = by_hash.get(judged.get("triggered_by") or "")
        settles = [
            t for t in txs
            if t.get("triggered_by") == judged["hash"] and t["method"] == "settle" and t["execution"] == "SUCCESS"
        ]
        if not opener or not settles:
            continue
        assert opener["method"] == "open_dispute", judged["hash"]
        settle = settles[0]
        if judged.get("accepted_at"):
            finality.append(_epoch(settle["created_at"]) - judged["accepted_at"])
        if settle.get("accepted_at"):
            to_verdict.append(settle["accepted_at"] - _epoch(opener["created_at"]))
        payouts = [t for t in txs if t.get("triggered_by") == settle["hash"] and t["method"] == "transfer"]
        if payouts and settle.get("accepted_at"):
            finality.append(min(_epoch(t["created_at"]) for t in payouts) - settle["accepted_at"])
        if payouts and verdict[judged["pid"]] == "not_honored":
            money_back.append(min(_epoch(t["created_at"]) for t in payouts) - _epoch(opener["created_at"]))
    assert to_verdict and money_back and finality and committee, "the snapshot predates the settlement timings; re-take it"

    def median(values):
        ordered = sorted(values)
        return round(ordered[len(ordered) // 2])

    totals = SNAPSHOT["totals"]
    assert totals["median_dispute_to_verdict_seconds"] == median(to_verdict)
    assert totals["median_dispute_to_money_back_seconds"] == median(money_back)
    assert totals["median_finality_seconds"] == median(finality)
    assert totals["committee"] == median(committee)
    # The committee a listed record reports is the one the raw receipts name.
    for label in ("contested", "honored", "unclear"):
        for rel in SNAPSHOT["receipts"][label]["files"]:
            if "-adjudicate-" in rel:
                receipt = json.loads((ROOT / rel).read_text(encoding="utf-8"))
                assert len(receipt["last_round"]["round_validators"]) == totals["committee"], rel
    # Printed where they are stated.
    flat = " ".join(README.split())
    assert f"dispute to verdict {totals['median_dispute_to_verdict_seconds']} seconds" in flat
    assert f"dispute to money back {totals['median_dispute_to_money_back_seconds']} seconds" in flat
    assert f"finalizes a median of {totals['median_finality_seconds']} seconds" in flat
    assert f"committee {totals['committee']} nodes per round" in flat
    # And typed nowhere on the site.
    sections = (ROOT / "web" / "components" / "site" / "Sections.tsx").read_text(encoding="utf-8")
    for typed in ("about 90 seconds", "half a minute", "committee of five", "ten model calls"):
        assert typed not in sections, f"the site types {typed!r} instead of reading it"


def test_the_readmes_fee_figures_are_the_receipts_the_snapshot_keeps():
    """
    What judgment costs on studionet is stated from receipts. The snapshot
    keeps eth_gasPrice and the receipt of the first success of each method
    and of the first refusal, and the README's figures must be exactly what
    those say.
    """
    fees = SNAPSHOT["fees"]
    assert fees["eth_gasPrice"] == "0x0"
    methods = {r["method"] for r in fees["receipts"]}
    assert "adjudicate" in methods, "no receipt of a transaction that ran the judgment"
    assert any(r["execution"] == "ERROR" for r in fees["receipts"]), "no refusal in the sample"
    for receipt in fees["receipts"]:
        assert receipt["effectiveGasPrice"] is not None and int(receipt["effectiveGasPrice"], 16) == 0, receipt["hash"]
        assert receipt["gasUsed"] is not None and int(receipt["gasUsed"], 16) == 8000000, receipt["hash"]
    flat = " ".join(README.split())
    assert "`eth_gasPrice` returns `0x0`" in flat
    assert "a `gasUsed` of exactly `8000000`" in flat


WORDS = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
)


def spell(n: int) -> str:
    """A count written the way the copy writes numbers, as the site's spell() does."""
    return WORDS[n] if 0 <= n < len(WORDS) else str(n)


def test_the_feed_image_and_its_caption_are_of_the_totals_the_snapshot_keeps():
    """
    docs/images/feed.png is a photograph of the chain: true the day it is taken,
    and false the next time a payment lands, with nothing failing. The README
    showed fourteen payments while the snapshot said nineteen. docs/shots.py
    writes what the tiles read beside the image, so the picture and its caption
    are held to the snapshot here. The median tile is left out: it moves only
    when a dispute does, and the counts catch that.

    When this fails, retake the image with docs/shots.py and rewrite the caption
    in the same commit, as docs/RUNBOOK.md says.
    """
    totals = SNAPSHOT["totals"]
    shot = json.loads((ROOT / "docs" / "images" / "feed.json").read_text(encoding="utf-8"))
    read = {label.lower(): value for label, value in shot["tiles"].items()}
    expected = {
        "payments": str(totals["payments"]),
        "disputes opened": str(totals["disputes_opened"]),
        "not honored": f"{totals['upheld']}/{totals['decided']}",
    }
    for label, value in expected.items():
        assert read.get(label) == value, (
            f"docs/images/feed.png shows {label} {read.get(label)} and the snapshot says {value}: "
            "retake it with docs/shots.py against a production build, then rewrite its caption"
        )
    caption = re.search(r"!\[([^\]]*)\]\(docs/images/feed\.png\)", README)
    assert caption, "the README no longer shows the feed image"
    stated = (
        f"{spell(totals['payments'])} payments, {spell(totals['disputes_opened'])} disputes opened, "
        f"{spell(totals['upheld'])} of {spell(totals['decided'])} not honored"
    )
    assert stated in " ".join(caption.group(1).split()), f"the feed caption should say {stated!r}"


def test_the_evaluation_prose_on_the_site_is_held_to_what_it_describes():
    """
    The evaluation section names the one miss and the two commits that put the
    answer key before the judge. Neither is a count a template can read, so the
    miss is held to results.json and the commits to git's own history, where a
    clone has history to read.
    """
    sections = (ROOT / "web" / "components" / "site" / "Sections.tsx").read_text(encoding="utf-8")
    results = json.loads((ROOT / "eval" / "results.json").read_text(encoding="utf-8"))
    misses = [row["id"] for row in results["rows"] if not row["correct"]]
    assert misses == ["12"], f"the site explains case 12 as the one miss, and results.json records {misses}"
    assert "The one miss in the first set is case 12," in sections
    shallow = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    if shallow != "false":
        pytest.skip("a shallow clone has no history to hold the commits to")
    for path, named in (("eval/cases.json", "b50757f"), ("eval/cases-v2.json", "04ca928")):
        added = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%H", "--", path],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.split()
        assert added and added[-1].startswith(named), f"{path} was added in {added[-1:]}, and the site says {named}"
        assert named in sections
