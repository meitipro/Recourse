#!/usr/bin/env python3
"""
Which validators each network has, read from the network rather than assumed.

    python eval/validators.py            # -> eval/validators.json

The evaluation columns are two committees ruling on the same strings, so the
committees are part of the record: how many validators each network lists,
and how many run each provider and model. Read with sim_getAllValidators,
which needs no account. Nothing else a validator reports is kept.

This is the list when it was read, not when the sets ran. A network can add
or retire validators between the two, and the file says when it was read.
"""

from __future__ import annotations

import collections
import json
import pathlib
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
FROZEN = HERE.parent / "contracts" / "FROZEN.json"
OUT = HERE / "validators.json"


def read(rpc: str) -> list[dict]:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "sim_getAllValidators", "params": []}).encode()
    request = urllib.request.Request(
        rpc,
        data=body,
        # The RPC's edge refuses urllib's default agent with a 403.
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (recourse eval/validators.py)"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        answer = json.loads(response.read().decode("utf-8"))
    if "error" in answer:
        raise SystemExit(f"{rpc}: {answer['error']}")
    return answer["result"]


def main() -> int:
    deployments = json.loads(FROZEN.read_text(encoding="utf-8"))["deployments"]
    now = int(time.time())
    record = {
        "read_at": now,
        "read_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "method": "sim_getAllValidators",
        "networks": {},
    }
    for network, entry in deployments.items():
        validators = read(entry["rpc"])
        models = collections.Counter(f"{v.get('provider')}/{v.get('model')}" for v in validators)
        record["networks"][network] = {
            "rpc": entry["rpc"],
            "validators": len(validators),
            "models": dict(sorted(models.items())),
        }
        print(f"{network:12} {len(validators)} validators, {len(models)} provider and model pairs")
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
