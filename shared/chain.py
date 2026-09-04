"""
One place that talks to GenLayer, used by the deploy script, the buyer agent and
the evaluation runner.

Studio drops connections. The SDK's provider makes a single attempt and turns a
dropped TLS handshake into a hard failure, so every call here is wrapped in a
retry with backoff. Only calls that clearly failed before submission are
retried; a write that may already be in flight is never sent twice.
"""

from __future__ import annotations

import json
import os
import pathlib
import time
import typing

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from genlayer_py import create_account, create_client, studionet
from genlayer_py.chains import testnet_asimov, testnet_bradbury


# --- transport ------------------------------------------------------------
# genlayer_py's provider calls requests.post once per RPC method and turns any
# connection failure into a hard error. Studio drops TLS handshakes in bursts:
# measured from this machine, a plain post succeeds three times in four and can
# fail ten times running. One dropped handshake then fails a whole deploy, which
# reads as a broken contract and is not one.
#
# This replaces the module's `requests` reference with a session that retries at
# the connection layer, so a burst is absorbed below the SDK rather than above
# it. The retry above still exists, for the failures a session cannot see.
_SESSION = requests.Session()
_SESSION.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=12,
            connect=12,
            read=6,
            backoff_factor=0.7,
            backoff_max=20,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=frozenset(["POST", "GET"]),
            raise_on_status=False,
        ),
        pool_connections=2,
        pool_maxsize=8,
    ),
)


def _install_session() -> None:
    from genlayer_py.provider import provider as _provider

    if getattr(_provider, "_recourse_session", False):
        return
    _provider.requests = _SESSION
    # The session has no `exceptions` attribute of its own, and the provider
    # catches requests.exceptions.RequestException by that path.
    _SESSION.exceptions = requests.exceptions
    _provider._recourse_session = True


_install_session()

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEPLOYED = ROOT / "deployed.json"
KEYS = ROOT / ".accounts.json"

GEN = 10**18

CHAINS = {
    "studionet": studionet,
    "bradbury": testnet_bradbury,
    "asimov": testnet_asimov,
}

# Studio allows roughly thirty requests a minute. Past that the RPC answers an
# unknown error, which reads as a broken contract and is not one.
RETRIES = 10
BACKOFF = 1.6


def network_name() -> str:
    return os.environ.get("RECOURSE_NETWORK", "studionet")


def chain():
    name = network_name()
    if name not in CHAINS:
        raise SystemExit(f"unknown network {name}, expected one of {sorted(CHAINS)}")
    return CHAINS[name]


def retry(what: str, fn, *args, **kwargs):
    """
    Call fn, retrying only the failures that happened before anything was sent.

    A timeout after submission is not retried, because the transaction may
    already exist and a second one would be a second payment.
    """
    last: Exception | None = None
    for attempt in range(RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as error:  # noqa: BLE001
            text = str(error)
            fatal = (
                "reverted" in text
                or "UserError" in text
                or "[EXPECTED]" in text
                or "insufficient" in text
            )
            if fatal:
                raise
            last = error
            if attempt == RETRIES - 1:
                break
            wait = BACKOFF**attempt
            print(f"  retry {attempt + 1}/{RETRIES} on {what}: {text[:110]}")
            time.sleep(wait)
    raise RuntimeError(f"{what} failed after {RETRIES} attempts: {last}")


class Chain:
    def __init__(self, account=None):
        self.account = account
        self.client = create_client(chain=chain(), account=account)

    # -- accounts ----------------------------------------------------------

    def fund(self, address: str, amount: int) -> None:
        """
        Studio's programmatic faucet.

        It answers an error for a hex amount and credits the account anyway, and
        it answers a transaction hash for an address it has never seen and
        credits nothing. Neither the error nor the hash is evidence, so the
        balance is read before and after and the difference is what gets
        reported.
        """
        before = self.balance(address)
        try:
            retry("fund_account", self.client.fund_account, address, amount)
        except Exception as error:  # noqa: BLE001
            print(f"  fund_account reported {str(error)[:90]}, reading the balance instead")
        after = self.balance(address)
        print(f"  {address[:10]} {before / GEN:.2f} -> {after / GEN:.2f} GEN")

    def balance(self, address: str) -> int:
        try:
            return int(retry("get_balance", self.client.get_balance, address))
        except Exception:  # noqa: BLE001
            return 0

    # -- contracts ---------------------------------------------------------

    def deploy(self, path: pathlib.Path, args: list) -> str:
        code = path.read_text(encoding="utf-8")
        size = len(code.encode("utf-8"))
        print(f"  deploying {path.name} ({size} bytes)")
        if size > 55_000:
            print("  warning: Studio resets request bodies near 60KB, this may need retries")
        tx = retry("deploy", self.client.deploy_contract, code=code, args=args)
        receipt = self.wait(tx, "FINALIZED", retries=80)
        address = _contract_address(receipt)
        if not address:
            raise RuntimeError(f"deploy finalized with no address: {_summary(receipt)}")
        # A Ghost can exist before the GenVM deployment finalizes, so EVM code at
        # the address does not prove the Intelligent Contract deployed. Reading
        # the schema back is the readiness probe that does.
        retry("get_contract_schema", self.client.get_contract_schema, address)
        print(f"  {path.name} -> {address}")
        return address

    def read(self, address: str, method: str, args: list | None = None):
        return retry("read " + method, self.client.read_contract, address, method, args or [])

    def read_json(self, address: str, method: str, args: list | None = None) -> dict:
        return json.loads(self.read(address, method, args))

    def write(self, address: str, method: str, args: list | None = None, value: int = 0) -> str:
        return retry(
            "write " + method,
            self.client.write_contract,
            address=address,
            function_name=method,
            args=args or [],
            value=value,
        )

    def wait(self, tx_hash, status: str = "ACCEPTED", retries: int = 40) -> dict:
        return retry(
            "wait",
            self.client.wait_for_transaction_receipt,
            transaction_hash=tx_hash,
            status=status,
            interval=3000,
            retries=retries,
        )

    def send(
        self,
        address: str,
        method: str,
        args: list | None = None,
        value: int = 0,
        status: str = "ACCEPTED",
    ) -> dict:
        """Write and wait. Returns the receipt, already checked for a real success."""
        tx = self.write(address, method, args, value)
        receipt = self.wait(tx, status)
        outcome = check(receipt)
        if not outcome["ok"]:
            raise RuntimeError(f"{method} failed: {outcome['detail']}")
        outcome["hash"] = _hash(tx)
        return outcome


# --- reading a receipt honestly -------------------------------------------
def _hash(tx) -> str:
    if isinstance(tx, str):
        return tx
    return getattr(tx, "hex", lambda: str(tx))()


def _contract_address(receipt) -> str | None:
    if not isinstance(receipt, dict):
        return None
    for key in ("contract_address", "contractAddress"):
        if receipt.get(key):
            return receipt[key]
    data = receipt.get("data") or {}
    if isinstance(data, dict):
        for key in ("contract_address", "contractAddress"):
            if data.get(key):
                return data[key]
    return None


def _summary(receipt) -> str:
    if not isinstance(receipt, dict):
        return str(receipt)[:300]
    keep = {k: receipt.get(k) for k in ("status", "tx_id", "hash", "type") if k in receipt}
    return json.dumps(keep, default=str)[:300]


# Consensus v0.6 defines fourteen numeric statuses and a node answers with the
# number, not the name. Both forms appear depending on which call produced the
# receipt, so both are understood here and the name is what gets displayed.
STATUS_NAMES = {
    0: "UNINITIALIZED",
    1: "PENDING",
    2: "PROPOSING",
    3: "COMMITTING",
    4: "REVEALING",
    5: "ACCEPTED",
    6: "UNDETERMINED",
    7: "FINALIZED",
    8: "CANCELED",
    9: "APPEAL_REVEALING",
    10: "APPEAL_COMMITTING",
    11: "VALIDATORS_TIMEOUT",
    12: "LEADER_TIMEOUT",
    13: "LEADER_REVEALING",
}
SETTLED = ("ACCEPTED", "FINALIZED")


def status_name(raw) -> str:
    if isinstance(raw, bool):
        return str(raw).upper()
    if isinstance(raw, int):
        return STATUS_NAMES.get(raw, f"STATUS_{raw}")
    text = str(raw).strip()
    if text.isdigit():
        return STATUS_NAMES.get(int(text), f"STATUS_{text}")
    return text.upper()


def check(receipt) -> dict:
    """
    Accepted means the committee agreed on the receipt. It does not mean the
    contract returned successfully: a receipt containing a user error can be
    Accepted, because validators can agree that an error is the correct result.

    Treat a transaction as successful only when its status is ACCEPTED or
    FINALIZED and its execution result is a return.
    """
    if not isinstance(receipt, dict):
        return {"ok": False, "status": "?", "detail": str(receipt)[:300], "result": None}

    status = status_name(receipt.get("status", ""))
    consensus = receipt.get("consensus_data") or {}
    leader = (consensus.get("leader_receipt") or [{}])
    if isinstance(leader, dict):
        leader = [leader]
    first = leader[0] if leader else {}
    execution = str(first.get("execution_result", "")).upper()
    genvm = first.get("genvm_result") or {}
    stderr = str(genvm.get("stderr", ""))[:400]
    stdout = str(genvm.get("stdout", ""))[:400]

    ok = status in SETTLED and execution in ("SUCCESS", "FINISHED_WITH_RETURN", "")
    detail = ""
    if not ok:
        # A refusal the contract raised is plain text in stderr, not in any
        # error field, so it is surfaced here rather than left to be dug out.
        detail = f"status={status} execution={execution} stderr={stderr or stdout}"
    return {
        "ok": ok,
        "status": status,
        "execution": execution,
        "detail": detail,
        "stderr": stderr,
        "stdout": stdout,
        "receipt": receipt,
        "result": _returned(first),
    }


def _returned(leader_receipt: dict) -> typing.Any:
    """The value the contract returned, when the node exposes it decoded."""
    for key in ("result", "return_value", "returned"):
        if key in leader_receipt:
            return leader_receipt[key]
    return None


# --- the deployment record ------------------------------------------------
def load_deployment() -> dict:
    if not DEPLOYED.exists():
        raise SystemExit(
            "deployed.json is missing. Run scripts/deploy.py first, or set "
            "RECOURSE_ESCROW and RECOURSE_DISPUTE."
        )
    return json.loads(DEPLOYED.read_text(encoding="utf-8"))


def save_deployment(record: dict) -> None:
    DEPLOYED.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_accounts() -> dict:
    """
    Three keys, kept out of git.

    Studio persistence is temporary, so the same three accounts are reused
    across a redeploy and the demo reads the same way every morning.
    """
    if KEYS.exists():
        raw = json.loads(KEYS.read_text(encoding="utf-8"))
        return {name: create_account(account_private_key=key) for name, key in raw.items()}
    made = {name: create_account() for name in ("owner", "seller", "buyer")}
    KEYS.write_text(
        json.dumps({name: account.key.hex() for name, account in made.items()}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"  wrote three fresh accounts to {KEYS.name}, which git ignores")
    return made
