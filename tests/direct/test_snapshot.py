"""
The recorded snapshots: what the chain held, written down so a testnet reset
cannot take the evidence with it.

Each network has one. evidence/snapshot.json is studionet's, where the frozen
pair runs, and evidence/snapshot-studio-next.json is Studio Next's, where the
port runs. These hold both to the numbers the repository publishes elsewhere.
Re-run an evaluation, cite a new transaction in the README, or change a
refusal, and the gate fails here until python scripts/snapshot.py is run again
for that network. Nothing here touches a network.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
FROZEN = json.loads((ROOT / "contracts" / "FROZEN.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")

#: Every network with a deployment has a snapshot of its own, studionet's under
#: the name the README has always cited.
NETWORKS = ("studionet", "studio-next")
PATHS = {
    network: ROOT / "evidence" / ("snapshot.json" if network == "studionet" else f"snapshot-{network}.json")
    for network in NETWORKS
}
SNAPSHOTS = {network: json.loads(path.read_text(encoding="utf-8")) for network, path in PATHS.items()}
RECEIPTS = {
    network: ROOT / "evidence" / "receipts" if network == "studionet" else ROOT / "evidence" / "receipts" / network
    for network in NETWORKS
}
SNAPSHOT_PATH = PATHS["studionet"]
SNAPSHOT = SNAPSHOTS["studionet"]

HASH = re.compile(r"0x[0-9a-f]{64}")


def payments(snapshot: dict | None = None) -> list[dict]:
    return (snapshot or SNAPSHOT)["payments"]


def decided(snapshot: dict | None = None) -> list[dict]:
    return [p for p in payments(snapshot) if int(p["status"]) == 3]


def pair_record(network: str) -> dict:
    """The recorded hashes of the pair this network runs: the frozen one, or the one its deployment names."""
    pair = FROZEN["deployments"][network].get("pair", "frozen")
    return FROZEN if pair == "frozen" else FROZEN[pair]


@pytest.mark.parametrize("network", NETWORKS)
def test_each_snapshot_is_of_its_recorded_pair_on_its_deployment(network):
    snapshot = SNAPSHOTS[network]
    entry = FROZEN["deployments"][network]
    assert snapshot["network"] == network
    assert snapshot["chain_id"] == entry["chain_id"]
    assert snapshot["escrow"] == entry["escrow"]
    assert snapshot["dispute"] == entry["dispute"]
    record = pair_record(network)
    assert snapshot["frozen"]["escrow_sha256"] == record["escrow"]["sha256"]
    assert snapshot["frozen"]["dispute_sha256"] == record["dispute"]["sha256"]
    assert snapshot["recorded_at_iso"].endswith("Z")
    assert "temporary testnet" in snapshot["note"]


@pytest.mark.parametrize("network", NETWORKS)
def test_the_totals_are_recomputable_from_the_rows_by_the_feeds_rules(network):
    snapshot = SNAPSHOTS[network]
    totals = snapshot["totals"]
    rows = payments(snapshot)
    assert totals["payments"] == len(rows) == int(snapshot["stats"]["payments"])
    assert totals["disputes_opened"] == sum(1 for p in rows if int(p["status"]) in (2, 3))
    judged = decided(snapshot)
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
    assert totals["transactions"] == len(snapshot["transactions"])
    assert totals["refusals"] == len(snapshot["refusals"])
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


def test_on_studio_next_every_case_is_judged_and_none_settled_and_the_readme_says_why():
    """
    On Studio Next judgment runs and settlement cannot pay out: settle's
    transfers sit two messages below the transaction that funds them, and
    consensus v0.6 accepts an external message only at the root of the
    allocation tree. The chain's own record says exactly that: every case
    carries a verdict, all three verdicts among them, every payment behind a
    case is still disputed, and every settle that ran ended on the allocation.
    The README says it in the same words.
    """
    snapshot = SNAPSHOTS["studio-next"]
    by_pid = {p["pid"]: p for p in payments(snapshot)}
    assert snapshot["cases"], "Studio Next has no judged case to hold this to"
    assert {case["verdict_name"] for case in snapshot["cases"]} == {"honored", "not_honored", "unclear"}
    for case in snapshot["cases"]:
        assert by_pid[case["pid"]]["status_name"] == "disputed", f"{case['pid']} settled"
    txs = snapshot["transactions"]
    settles = [t for t in txs if t["method"] == "settle" and not t["refusal"]]
    assert settles, "no settle ran on Studio Next"
    for t in settles:
        assert t["execution"] == "ERROR" and t["vm_error"] == "fee no_matching_allocation # external", t["hash"]
    assert not any(t["method"] == "settle" and t["execution"] == "SUCCESS" for t in txs)
    assert snapshot["totals"]["median_dispute_to_money_back_seconds"] is None
    assert "`fee no_matching_allocation # external`" in " ".join(README.split())


def test_on_studio_next_the_payouts_sent_from_the_root_ran_and_the_readme_cites_them():
    """withdraw and reclaim pay from the top of their own transaction, where the transfer can be allocated."""
    snapshot = SNAPSHOTS["studio-next"]
    by_pid = {p["pid"]: p for p in payments(snapshot)}
    for pid, method, status in (("p-000004", "withdraw", "withdrawn"), ("p-000002", "reclaim", "resolved")):
        assert by_pid[pid]["status_name"] == status, pid
        ran = [
            t for t in snapshot["transactions"]
            if t["method"] == method and t.get("pid") == pid and t["execution"] == "SUCCESS"
        ]
        assert ran, f"no successful {method} of {pid}"
        assert ran[0]["hash"] in README, f"the README does not cite the {method} of {pid}"


@pytest.mark.parametrize("network", NETWORKS)
def test_every_payment_has_its_pay_transaction_and_only_settled_ones_have_settle(network):
    for payment in payments(SNAPSHOTS[network]):
        tx = payment["transactions"]
        assert tx["pay"] and HASH.fullmatch(tx["pay"]), payment["pid"]
        assert tx["pay"] in tx["every_attempt"]
        if payment["status_name"] == "withdrawn":
            assert tx["withdraw"] and not tx["open_dispute"], payment["pid"]
        if payment["status_name"] == "open":
            assert not tx["settle"] and not tx["withdraw"], payment["pid"]


def test_every_transaction_the_readme_cites_is_in_a_snapshot():
    cited = set(HASH.findall(README))
    assert cited, "the README cites no transactions, which is not what it does"
    have = {t["hash"] for snapshot in SNAPSHOTS.values() for t in snapshot["transactions"]}
    missing = sorted(cited - have)
    assert not missing, f"the README cites transactions no snapshot has: {missing}. Run python scripts/snapshot.py"


#: One row of a refusal table, with the explorer host that says which network it is on.
REFUSAL_ROW = re.compile(
    r"\| `([a-z_]+)`[^|]*\| `(\[EXPECTED\][^`]*)` \| \[0x[0-9a-f]+\.\.\.\]\(https://([^/)]+)/tx/(0x[0-9a-f]{64})\)"
)
HOSTS = {network: FROZEN["deployments"][network]["explorer"].removeprefix("https://") for network in NETWORKS}


@pytest.mark.parametrize("network", NETWORKS)
def test_each_networks_refusal_table_is_in_its_snapshot_word_for_word(network):
    snapshot = SNAPSHOTS[network]
    table = [(method, refusal, h) for method, refusal, host, h in REFUSAL_ROW.findall(README) if host == HOSTS[network]]
    assert len(table) == 4, f"the README publishes four refusals on {network}"
    by_hash = {r["hash"]: r for r in snapshot["refusals"]}
    for method, refusal, tx_hash in table:
        assert tx_hash in by_hash, f"{method} refusal {tx_hash} is not a refusal in the {network} snapshot"
        assert by_hash[tx_hash]["method"] == method
        assert by_hash[tx_hash]["refusal"] == refusal
    # Every refusal in the snapshot is one the contract wrote, in its own words.
    for refusal in snapshot["refusals"]:
        assert refusal["refusal"].startswith("[EXPECTED]")


@pytest.mark.parametrize("network", NETWORKS)
def test_the_evaluation_numbers_match_the_measurement_files_and_the_reports(network):
    snapshot = SNAPSHOTS[network]
    suffix = "" if network == "studionet" else f".{network}"
    for name, base, report in (("v1", "results", "RESULTS.md"), ("v2", "results-v2", "RESULTS-V2.md")):
        measured = json.loads((ROOT / "eval" / f"{base}{suffix}.json").read_text(encoding="utf-8"))
        recorded = snapshot["evaluation"][name]
        for key in ("instance", "network", "n", "runs", "accuracy", "stability", "unclear", "measured_at"):
            assert recorded[key] == measured[key], f"{network} {name}.{key}: snapshot {recorded[key]}, measurement {measured[key]}"
        text = (ROOT / "eval" / report).read_text(encoding="utf-8")
        assert f"**{recorded['accuracy']}/{recorded['n']}**" in text, f"{report} does not carry {network}'s accuracy"
        assert f"| {recorded['stability']}/{recorded['n']} |" in text, f"{report} does not carry {network}'s stability"
        assert f"`{recorded['instance']}`" in text
    v1, v2 = snapshot["evaluation"]["v1"], snapshot["evaluation"]["v2"]
    assert f"{v1['accuracy']}/{v1['n']}" in README
    assert f"{v2['accuracy']}/{v2['n']}" in README


#: What each labelled receipt set must be a cycle of: (status, verdict or None).
#: A label present in the snapshot but not here is a label nobody defined.
#: Fields a receipt carries only as the RPC returned it. Consensus v0.6 reports
#: a transaction's state under lifecycle, where the earlier receipt had status.
RAW_FIELDS = {
    "studionet": ("consensus_data", "status", "from_address", "to_address", "created_at"),
    "studio-next": ("consensus_data", "lifecycle", "from_address", "to_address", "created_at"),
}

CYCLE_SHAPES = {
    "contested": ("resolved", "not_honored"),
    "honest": ("withdrawn", None),
    "honored": ("resolved", "honored"),
    "unclear": ("resolved", "unclear"),
}


@pytest.mark.parametrize("network", NETWORKS)
def test_the_receipts_are_raw_and_belong_to_the_cycles_named(network):
    snapshot = SNAPSHOTS[network]
    by_pid = {p["pid"]: p for p in payments(snapshot)}
    assert snapshot["receipts"], "the snapshot names no receipt sets"
    for label, info in snapshot["receipts"].items():
        assert label in CYCLE_SHAPES, f"{label} is a receipt set with no defined shape"
        status, verdict = CYCLE_SHAPES[label]
        payment = by_pid[info["pid"]]
        assert payment["status_name"] == status, f"{label}: {info['pid']} is {payment['status_name']}"
        if verdict:
            assert payment["verdict_name"] == verdict, f"{label}: {info['pid']} ruled {payment['verdict_name']}"
            assert payment.get("case"), f"{label}: {info['pid']} carries no case, so no committee ruled it"
        assert info["files"], f"no {label} receipts"
        folder = RECEIPTS[network] / f"{label}-{info['pid']}"
        on_disk = sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in folder.glob("*.json"))
        assert on_disk == sorted(info["files"]), f"{label}: files on disk and files listed differ"
        for rel in info["files"]:
            receipt = json.loads((ROOT / rel).read_text(encoding="utf-8"))
            assert receipt["hash"] in payment["transactions"]["every_attempt"], rel
            assert receipt["hash"][2:14] in rel
            # The RPC's own fields, present because nothing was edited out.
            for key in RAW_FIELDS[network]:
                assert key in receipt, f"{rel} lacks {key}"
    honest = by_pid[snapshot["receipts"]["honest"]["pid"]]
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


@pytest.mark.parametrize("network", NETWORKS)
def test_the_snapshot_carries_no_private_material(network):
    text = PATHS[network].read_text(encoding="utf-8").lower()
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
    The README's timing block, the site's section 04 and its section 08 state
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
    # Studio Next's settles all fail, so the verdict is written to the case and
    # never reaches the escrow, and its one timing is the dispute to the
    # adjudication's acceptance. It heads the README's timing block, because
    # the site reads Studio Next, and studionet's is the record's own.
    studio = SNAPSHOTS["studio-next"]
    linked = {t["hash"]: t for t in studio["transactions"]}
    to_case = [
        t["accepted_at"] - _epoch(linked[t["triggered_by"]]["created_at"])
        for t in studio["transactions"]
        if t["method"] == "adjudicate" and t["execution"] == "SUCCESS" and t.get("accepted_at") and t.get("triggered_by") in linked
    ]
    assert to_case, "the Studio Next snapshot predates its verdict timing; re-take it"
    assert studio["totals"]["median_dispute_to_case_seconds"] == median(to_case)
    assert f"dispute to verdict written {studio['totals']['median_dispute_to_case_seconds']} seconds" in flat
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

    The image is of whichever network the site was built for, which shots.py
    reads off the footer and writes beside the tiles. The Not honored tile
    counts the committee's rulings, the cases, because on Studio Next a case is
    judged and never settled. On studionet every case settled, so the two
    counts are the same there.
    """
    shot = json.loads((ROOT / "docs" / "images" / "feed.json").read_text(encoding="utf-8"))
    snapshot = SNAPSHOTS[shot.get("network", "studionet")]
    totals = snapshot["totals"]
    ruled = len(snapshot["cases"])
    not_honored = sum(1 for case in snapshot["cases"] if case["verdict_name"] == "not_honored")
    read = {label.lower(): value for label, value in shot["tiles"].items()}
    expected = {
        "payments": str(totals["payments"]),
        "disputes opened": str(totals["disputes_opened"]),
        "not honored": f"{not_honored}/{ruled}",
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
        f"{spell(not_honored)} of {spell(ruled)} not honored"
    )
    assert stated in " ".join(caption.group(1).split()), f"the feed caption should say {stated!r}"


def test_the_evaluation_prose_on_the_site_is_held_to_what_it_describes():
    """
    The evaluation section explains case 12, the miss both networks share, and
    names the two commits that put the answer key before the judge. Neither is
    a count a template can read, so the explanation is held to both networks'
    results and the commits to git's own history, where a clone has history to
    read. The page shows that paragraph only when the rows agree with it; this
    holds the rows to the paragraph it shows today.
    """
    sections = (ROOT / "web" / "components" / "site" / "Sections.tsx").read_text(encoding="utf-8")
    columns = {
        network: json.loads(
            (ROOT / "eval" / f"results{'' if network == 'studionet' else '.' + network}.json").read_text(encoding="utf-8")
        )
        for network in NETWORKS
    }
    # One sentence gives every network's runs per case, so they must be one number.
    assert len({results["runs"] for results in columns.values()}) == 1, "the networks ran different numbers of runs per case"
    misses = {network: [row["id"] for row in results["rows"] if not row["correct"]] for network, results in columns.items()}
    shared = [case for case in misses["studionet"] if all(case in missed for missed in misses.values())]
    assert shared == ["12"], f"the site explains case 12 as the miss both networks share, and the results record {shared}"
    for network, results in columns.items():
        twelve = next(row for row in results["rows"] if row["id"] == "12")
        assert twelve["stable"] and set(twelve["observed"]) == {"not_honored"}, f"{network} did not read case 12 as not honored every run"
    assert "Both networks read case 12 as not honored" in sections
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
