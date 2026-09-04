#!/usr/bin/env python3
"""
Check that what is deployed is what is in this repository.

    python scripts/verify.py

The deployment is the submission. A reviewer reads the bytes on chain, not the
repository, so a contract that was edited after deploying is a contract whose
published address no longer stands behind the published source. This reads the
code back with gen_getContractCode and compares it, and it also reads the live
state so the addresses in the README can be trusted.

The comparison normalises line endings before comparing. Git checks out CRLF on
Windows while the deploy sent whatever was on disk at the time, so a byte compare
that skips this reports a difference on every single line and tells you nothing.
"""

from __future__ import annotations

import base64
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# A Windows console hands a child process an ansi codepage. Anything that
# prints text from the chain or a model can die on it, so widen it here.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from shared.chain import Chain, load_accounts, load_deployment, retry  # noqa: E402


def normalise(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def deployed_source(chain: Chain, address: str) -> str:
    """gen_getContractCode takes a bare address string on Studio."""
    raw = retry(
        "gen_getContractCode",
        chain.client.provider.make_request,
        "gen_getContractCode",
        [address],
    )
    value = raw.get("result", raw)
    if isinstance(value, dict):
        value = value.get("code") or value.get("result") or ""
    if isinstance(value, str):
        try:
            return base64.b64decode(value).decode("utf-8")
        except Exception:  # noqa: BLE001
            return value
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", "replace")
    return str(value)


def main() -> int:
    deployment = load_deployment()
    chain = Chain(load_accounts()["owner"])
    failures = 0

    print(f"network  {deployment['network']}")
    for name, path in (("escrow", "contracts/escrow.py"), ("dispute", "contracts/dispute.py")):
        address = deployment[name]
        local = normalise((ROOT / path).read_text(encoding="utf-8"))
        print(f"\n{name}  {address}")
        try:
            onchain = normalise(deployed_source(chain, address))
        except Exception as error:  # noqa: BLE001
            print(f"  could not read the deployed code: {str(error)[:140]}")
            failures += 1
            continue

        if onchain == local:
            print(f"  source matches {path} ({len(local)} bytes)")
        else:
            failures += 1
            print(f"  MISMATCH against {path}")
            print(f"    on chain {len(onchain)} bytes, repository {len(local)} bytes")
            local_lines = local.splitlines()
            chain_lines = onchain.splitlines()
            for index in range(min(len(local_lines), len(chain_lines))):
                if local_lines[index] != chain_lines[index]:
                    print(f"    first difference at line {index + 1}")
                    print(f"      repo:     {local_lines[index][:90]}")
                    print(f"      on chain: {chain_lines[index][:90]}")
                    break

    print("\nlive state")
    try:
        stats = chain.read_json(deployment["escrow"], "stats")
        print(f"  payments      {stats['payments']}")
        print(f"  held          {int(stats['held']) / 10**18:.2f} GEN")
        print(f"  window        {stats['window_seconds']}s")
        print(f"  bond          {int(stats['bond_amount']) / 10**18:.2f} GEN")
        wired = stats["dispute_contract"].lower() == deployment["dispute"].lower()
        print(f"  wired         {'yes' if wired else 'NO'}")
        if not wired:
            failures += 1
        cases = chain.read_json(deployment["dispute"], "stats")
        print(f"  cases         {cases['cases']}")
    except Exception as error:  # noqa: BLE001
        print(f"  could not read live state: {str(error)[:140]}")
        failures += 1

    print("\n" + "=" * 56)
    if failures:
        print(f"{failures} problem(s). Redeploy, or fix the addresses in deployed.json.")
        return 1
    print("the deployment matches this repository")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
