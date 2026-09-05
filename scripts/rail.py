#!/usr/bin/env python3
"""
Prove the rail claim instead of asserting it.

    python scripts/rail.py

Starts a second seller on port 4502 whose 402 challenge names an outside
settlement system rather than x402, buys from it presenting that system's own
opaque reference, contests the response, and reads the verdict off the chain.

The claim under test is that Recourse judges evidence rather than a settlement
method. The test is whether anything in either contract has to change for a
payment that did not arrive over x402. The answer is recorded here rather than
in prose: the contracts are checked for any mention of a rail, and the evidence
written on chain by this cycle is compared field by field with the shape the
x402 seller writes.

A finding, if one appears, is reported and not patched around.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Chain and model text is printed here. A Windows console hands a child process
# an ansi codepage that cannot encode all of it.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from shared.chain import Chain, load_accounts, load_deployment  # noqa: E402

PORT = 4502
ENDPOINT = f"http://localhost:{PORT}"

#: An opaque reference in the shape an outside settlement system hands out.
#: Deliberately nothing like a Recourse payment id, so that an endpoint or a
#: contract quietly depending on the escrow's own identifier would fail here
#: rather than pass by coincidence.
SETTLEMENT_ID = "set_3PxQrLbGk29fVn"


def rule(title: str) -> None:
    print("\n" + "=" * 66)
    print(f"  {title}")
    print("=" * 66)


def get(path: str, headers: dict | None = None):
    request = urllib.request.Request(ENDPOINT + path, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8")


def wait_for_endpoint(seconds: int = 20) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            code, _ = get("/health")
            if code == 200:
                return True
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    return False


def contracts_mention_a_rail() -> list[str]:
    """Any settlement vocabulary in either contract, which would sink the claim."""
    found = []
    for name in ("escrow", "dispute"):
        text = (ROOT / "contracts" / f"{name}.py").read_text(encoding="utf-8").lower()
        for term in ("x402", "settlement_id", "x-payment", "stripe", "card", "rail"):
            if term in text:
                found.append(f"{name}.py contains {term!r}")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", default="stale", help="the failure to inject")
    parser.add_argument("--keep", action="store_true", help="leave the endpoint running")
    args = parser.parse_args()

    deployment = load_deployment()
    accounts = load_accounts()
    reader = Chain(accounts["buyer"])
    escrow = deployment["escrow"]

    rule("1. Neither contract knows what a rail is")
    findings = contracts_mention_a_rail()
    if findings:
        # Reported, not patched. A contract that names a settlement method is
        # the whole claim failing, and hiding it behind a rename would leave the
        # claim false and the evidence gone.
        print("  FINDING: the contracts are not rail free")
        for item in findings:
            print(f"    {item}")
        return 1
    print("  escrow.py and dispute.py mention no settlement method at all")
    print("  pay(seller, request) takes no payment reference: the escrow is the settlement")

    rule(f"2. A seller settling somewhere else, on port {PORT}")
    process = subprocess.Popen(
        [sys.executable, "seller/main.py", "--rail", "external",
         "--port", str(PORT), "--mode", args.mode],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_for_endpoint():
            raise SystemExit(f"the endpoint on {PORT} did not come up")

        code, body = get("/quote?pair=ETH-USD")
        challenge = json.loads(body)
        offer = challenge["accepts"][0]
        print(f"  unpaid request   HTTP {code}")
        print(f"  scheme           {offer['scheme']}")
        print(f"  proof header     {offer['header']}")
        if offer["scheme"] == "recourse-escrow" or offer["header"] == "x-payment-proof":
            raise SystemExit("the external rail is still advertising the x402 challenge")

        code, _ = get("/quote?pair=ETH-USD", {offer["header"]: SETTLEMENT_ID})
        print(f"  with {offer['header']}  HTTP {code}, served against an id the chain never sees")

        rule("3. One full contested cycle against it")
        command = [
            sys.executable, "agent/run.py", "--json",
            "--endpoint", ENDPOINT, "--mode", args.mode,
            "--settlement-id", SETTLEMENT_ID,
        ]
        started = time.time()
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        sys.stderr.write(result.stderr)
        try:
            report = json.loads(result.stdout)
        except ValueError:
            print(result.stdout[-2000:])
            raise SystemExit("the agent produced no report")

        elapsed = time.time() - started
        pid = report.get("pid", "")
        print(f"  rail negotiated  {report.get('rail', {}).get('scheme')}")
        print(f"  presented        {report.get('settlement_reference')}")
        print(f"  payment          {pid}")
        print(f"  verdict          {report.get('verdict')}")
        print(f"  elapsed          {elapsed:.0f}s")
        for key in ("pay_hash", "record_hash", "dispute_hash"):
            if report.get(key):
                print(f"  {key:16} {report[key]}")

        rule("4. What the chain actually stored")
        row = reader.read_json(escrow, "get_payment", [pid])
        # The settlement reference must be absent from the stored evidence. If
        # it appears anywhere, the rail leaked onto the chain and the claim that
        # judgment is rail free is not true.
        stored = json.dumps(row)
        if SETTLEMENT_ID in stored:
            print(f"  FINDING: the settlement id reached the chain in {pid}")
            print(f"  {stored[:400]}")
            return 1
        print(f"  fields           {', '.join(sorted(row))}")
        print("  the settlement id appears in none of them")
        print(f"  request          {row.get('request')}")
        print(f"  verdict          {report.get('verdict')}")

        rule("Result")
        print("  Neither contract changed and neither contract could tell.")
        print("  The rail decided how the buyer proved payment to the endpoint.")
        print("  It decided nothing about what was judged.")

        record = {
            "rail": "external-settlement",
            "settlement_id": SETTLEMENT_ID,
            "pid": pid,
            "verdict": report.get("verdict"),
            "seconds": round(elapsed),
            "hashes": {k: report[k] for k in ("pay_hash", "record_hash", "dispute_hash")
                       if report.get(k)},
            "contracts_changed": False,
        }
        out = ROOT / "docs" / "rail-proof.json"
        out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"\n  wrote {out.relative_to(ROOT)}")
        return 0
    finally:
        if not args.keep:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
