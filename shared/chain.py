"""
One place that talks to GenLayer, used by the deploy script, the buyer agent and
the evaluation runner.

Studio drops connections. The SDK's provider makes a single attempt and turns a
dropped TLS handshake into a hard failure, so every call here is wrapped in a
retry with backoff. Only calls that clearly failed before submission are
retried; a write that may already be in flight is never sent twice.

Two networks, two SDK lines. studionet runs the consensus genlayer-py 0.18 and
earlier speak. Studio Next runs consensus v0.6, charges a fee deposit on every
write, and needs genlayer-py 0.19.0rc2, which in turn cannot read studionet.
This module works with either, keys every difference off the network rather
than the installed SDK, and refuses by name a network the installed SDK cannot
talk to.
"""

from __future__ import annotations

import importlib.metadata
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

try:
    # genlayer-py 0.19, the consensus v0.6 line: the only SDK that can write to
    # Studio Next.
    from genlayer_py.chains import studio_devnet as _studio_devnet
except ImportError:  # genlayer-py 0.18 and earlier, which studionet needs
    _studio_devnet = None


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

SDK_VERSION = importlib.metadata.version("genlayer_py")

#: Studio Next. studio-next.genlayer.com and studio-dev.genlayer.com are one
#: network, chain 61997 with one validator set; the organisers name the first,
#: so the RPC is pinned to it rather than to the SDK's default.
STUDIO_NEXT_RPC = "https://studio-next.genlayer.com/api"

CHAINS = {
    "studionet": studionet,
    "bradbury": testnet_bradbury,
    "asimov": testnet_asimov,
}
if _studio_devnet is not None:
    _studio_devnet.rpc_urls = {"default": {"http": [STUDIO_NEXT_RPC]}}
    CHAINS["studio-next"] = _studio_devnet

#: Every network name this repository knows, whether or not the installed SDK
#: can reach it. A name outside this set is a typo; a name inside it that is
#: missing from CHAINS needs the other SDK line, and is told so.
KNOWN_NETWORKS = set(CHAINS) | {"studio-next"}

#: The networks whose consensus is v0.6: fees on every write, `wait_until`
#: rather than `status` when waiting, a lifecycle in every receipt, and reads
#: that need an account. Everything below that differs is keyed off this set.
V06_NETWORKS = {"studio-next"}

#: Which recorded pair of contracts each network runs. The frozen pair's runtime
#: fails on a v0.6 network whatever its first line says, so Studio Next runs
#: the ported pair in contracts/v06/, which scripts/port.py makes from it.
PAIR_OF_NETWORK = {"studionet": "frozen", "studio-next": "v06"}
PAIR_DIRS = {"frozen": ROOT / "contracts", "v06": ROOT / "contracts" / "v06"}

# Studio allows roughly thirty requests a minute. Past that the RPC answers an
# unknown error, which reads as a broken contract and is not one.
RETRIES = 10
BACKOFF = 1.6


#: The chain ids the SDK reports, pinned here so a freeze entry that names a
#: network with the wrong id fails the gate. bradbury is listed so that an
#: entry for it, if one were ever added, would be checked against the right id
#: rather than trusted.
KNOWN_CHAIN_IDS = {"studionet": 61999, "studio-next": 61997, "bradbury": 4221}

#: Where GEN comes from on each network. Both Studios have a programmatic
#: faucet. bradbury's is a browser page and cannot be automated, so a deploy
#: there, if one were ever run, stops and names it rather than trying.
FAUCETS = {
    "studionet": "sim_fundAccount over the RPC (scripts call it for you)",
    "studio-next": "sim_fundAccount over the RPC (scripts call it for you)",
    "bradbury": "https://testnet-faucet.genlayer.foundation",
}

#: The networks scripts may fund on their own, one faucet call per account.
PROGRAMMATIC_FAUCET = {"studionet", "studio-next"}

EXPLORERS = {
    "studionet": "https://explorer-studio.genlayer.com",
    "studio-next": "https://explorer-studio-dev.genlayer.com",
    "bradbury": "https://explorer-bradbury.genlayer.com",
    "asimov": "https://explorer-asimov.genlayer.com",
}

#: The most time units one phase may be allocated. Studio Next's consensus
#: contract refuses anything outside 30 to 600 before the transaction exists:
#: a deploy asking for 2000 reverted with PhaseTimeoutOutOfBounds(2000,30,600).
MAX_TIMEUNITS = 600

#: What a deploy asks for on a fee charging network. A deploy runs the
#: constructor and emits nothing, and the unused deposit is refunded, so the
#: allocation is the most the contract accepts rather than risking one that
#: runs out.
DEPLOY_FEES = {
    "leaderTimeunitsAllocation": MAX_TIMEUNITS,
    "validatorTimeunitsAllocation": MAX_TIMEUNITS,
    "totalMessageFees": 0,
    "rotations": [1],
}

#: The allocation for a write Studio cannot estimate. Studio estimates a write
#: by simulating it, and a write it expects to be refused cannot be simulated.
#: A refusal emits no messages, so this flat allocation is enough to put it on
#: chain, where the refusal is recorded like any other.
WRITE_FEES = {
    "leaderTimeunitsAllocation": MAX_TIMEUNITS,
    "validatorTimeunitsAllocation": MAX_TIMEUNITS,
    "totalMessageFees": 0,
    "rotations": [1],
}

#: Writes whose messages emit messages of their own. Studio estimates a write
#: by simulating it, which funds the messages that write emits and nothing
#: below them: open_dispute emits adjudicate, and adjudicate emits settle when
#: it finishes. Consensus v0.6 wants every internal message in that chain
#: allocated by the transaction that starts it, and a child with no allocation
#: for what it emits fails with "fee no_matching_allocation". Measured on
#: Studio Next: adjudicate ran the whole judgment, then failed on the settle.
#: Each entry maps a message the estimate already funds to the internal
#: messages it emits in turn: (method, the deployment role it goes to, whether
#: it fires on acceptance rather than on finality).
CASCADES = {
    "open_dispute": {"adjudicate": [("settle", "escrow", False)]},
}

#: Writes that pay out from the top of their own transaction. Studio cannot
#: simulate them ("execution failed"), and the flat allocation funds no
#: message, so each payout needs an External node at the root of the tree:
#: the payee as recipient and the unnamed call key of a plain value transfer.
#: Consensus v0.6 accepts an external message only at the root, which is why
#: this works here and cannot work for settle's payouts, two messages down.
#: Measured on Studio Next: withdraw with no such node finished "fee
#: no_matching_allocation # external", and with one it paid the seller.
ROOT_PAYOUTS = ("withdraw", "reclaim")
EXTERNAL_BUDGET = 10**15
EXTERNAL_GAS = {"gasLimit": 100000, "maxGasPrice": 10**9}


def _external_node(recipient: str) -> dict:
    """One External allocation at the root of the tree, for a value transfer to recipient."""
    from genlayer_py.transactions.fees import (
        MESSAGE_ALLOCATION_ROOT_PARENT_INDEX,
        MessageType,
        derive_external_message_call_key,
        encode_external_message_fee_params,
    )

    return {
        "messageType": int(MessageType.External),
        "onAcceptance": False,
        "parentIndex": MESSAGE_ALLOCATION_ROOT_PARENT_INDEX,
        "recipient": recipient,
        "callKey": derive_external_message_call_key("0x"),
        "budget": EXTERNAL_BUDGET,
        "feeParams": encode_external_message_fee_params(EXTERNAL_GAS),
    }

FROZEN = pathlib.Path(__file__).resolve().parent.parent / "contracts" / "FROZEN.json"


#: The network everything defaults to when no --network is given.
DEFAULT_NETWORK = "studionet"


def network_name() -> str:
    return os.environ.get("RECOURSE_NETWORK", DEFAULT_NETWORK)


def settlement_moves(network: str) -> bool:
    """
    Whether a verdict's settlement pays out on this network.

    On consensus v0.6 a value transfer can be funded only at the root of the
    allocation tree a transaction is submitted with, and settle's transfers sit
    two messages below the transaction that funds them: open_dispute, then
    adjudicate, then settle. So there the verdict is written to the case and
    the escrow keeps the payment and the bond. Measured on Studio Next on 14
    September: every settle ended "fee no_matching_allocation # external".
    """
    return network not in V06_NETWORKS


def sdk_problem(name: str) -> str | None:
    """
    Why the installed SDK cannot reach this network at all, or None when it can.

    Only the one case that has no client to build: a v0.6 network under an SDK
    that does not know it. The opposite case, studionet under 0.19, builds a
    client and fails at the first read, and read() says why when it does.
    """
    if name in V06_NETWORKS and _studio_devnet is None:
        return (
            f"{name} runs consensus v0.6, which needs genlayer-py 0.19.0rc2; this interpreter "
            f"has {SDK_VERSION}. Install requirements.txt in a virtual environment and run from it."
        )
    return None


#: What a studionet read under the v0.6 SDK fails with, measured, and what it means.
STUDIONET_UNDER_V06 = (
    "genlayer-py {version} cannot read studionet: its gen_call fails there with "
    "'execution failed' whatever the contract. Run studionet from an interpreter with "
    "genlayer-py 0.18 or earlier."
)


def deployed_networks() -> list[str]:
    """The networks contracts/FROZEN.json has an entry for."""
    return sorted(frozen_record().get("deployments", {}))


def require_deployed(name: str) -> None:
    """
    Stop, in one sentence, when the chosen network has never had the contracts
    deployed to it. This is what --network bradbury hits: the fact, at the first
    line, rather than a missing deployed.json three calls later.
    """
    have = deployed_networks()
    if name in have:
        return
    only = ", ".join(have) if have else "none"
    raise SystemExit(
        f"the frozen contracts have never been deployed on {name}. "
        f"The deployments are: {only}, and nothing here runs against {name}. "
        f"Drop --network, or pass --network {have[0] if have else DEFAULT_NETWORK}. "
        "scripts/deploy.py --network is the one command that changes this."
    )


def select_network(name: str | None, *, allow_undeployed: bool = False) -> str:
    """
    Set the network for this process from a --network flag, and return it.

    A network the contracts are not deployed on is refused here, whether it
    came from the flag or from RECOURSE_NETWORK, so every script stops at its
    first line with the reason. deploy.py is the one caller that passes
    allow_undeployed, because deploying is how a network gets an entry.
    """
    if name:
        if name not in KNOWN_NETWORKS:
            raise SystemExit(f"unknown network {name}, expected one of {sorted(KNOWN_NETWORKS)}")
        os.environ["RECOURSE_NETWORK"] = name
    chosen = network_name()
    if not allow_undeployed:
        require_deployed(chosen)
    return chosen


def frozen_record() -> dict:
    if not FROZEN.exists():
        raise SystemExit("contracts/FROZEN.json is missing")
    return json.loads(FROZEN.read_text(encoding="utf-8"))


def frozen_deployment(network: str | None = None) -> dict:
    """
    One network's contract addresses, from contracts/FROZEN.json.

    The freeze is over the bytes of each recorded pair; a network is where one
    pair lives. A network with no entry has not been deployed to yet, and the
    message says which script does that.
    """
    name = network or network_name()
    entry = frozen_record().get("deployments", {}).get(name)
    if not entry:
        require_deployed(name)
        raise SystemExit(f"the {name} entry in contracts/FROZEN.json is empty")
    return entry


def pair_paths(network: str) -> dict[str, pathlib.Path]:
    """escrow.py and dispute.py of the pair this network runs."""
    folder = PAIR_DIRS[PAIR_OF_NETWORK.get(network, "frozen")]
    return {name: folder / f"{name}.py" for name in ("escrow", "dispute")}


def require_funds(chain: "Chain", accounts: dict, minimum_wei: int) -> None:
    """
    Stop, clearly, when accounts on a network with a browser faucet hold too
    little to proceed. Never retries and never calls a faucet: the only ones
    that can be called are Studio's, handled by fund().
    """
    name = network_name()
    if name in PROGRAMMATIC_FAUCET:
        return
    short = []
    for label, account in accounts.items():
        balance = chain.balance(account.address)
        if balance < minimum_wei:
            short.append((label, account.address, balance))
    if not short:
        return
    print(f"\nThese accounts need GEN on {name} before this can continue.")
    print(f"The faucet is a browser page: {FAUCETS.get(name, 'see the network documentation')}")
    print("Fund each address below, then run this again. Nothing was sent.\n")
    for label, address, balance in short:
        print(f"  {label:7} {address}   {balance / GEN:.2f} GEN, needs {minimum_wei / GEN:.0f}")
    raise SystemExit(2)


def chain():
    name = network_name()
    if name not in KNOWN_NETWORKS:
        raise SystemExit(f"unknown network {name}, expected one of {sorted(KNOWN_NETWORKS)}")
    problem = sdk_problem(name)
    if problem:
        raise SystemExit(problem)
    return CHAINS[name]


def retry(what: str, fn, *args, **kwargs):
    """
    Call fn again on a transient failure. For READS and WAITS only.

    This used to claim that a timeout after submission was not retried. It was
    not true: nothing here can tell whether a write reached the node, and a
    write retried after a lost response is a second transaction. Writes and
    deploys go through Chain._guarded, which reads the nonce before and after
    and refuses to resend once it has moved.
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
                # A view that refuses comes back through gen_call as a bare
                # "execution failed", not as the contract's message. It is
                # deterministic, and a clean clone spent ten attempts on
                # "unknown seller" before this line existed.
                or "execution failed" in text
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


_READER = None


def _reader():
    """
    A throwaway account for reads on a v0.6 network, which refuses a read with
    no account. It never signs a transaction and is never funded.
    """
    global _READER
    if _READER is None:
        _READER = create_account()
    return _READER


def _fee_options(estimate: dict) -> dict:
    """The part of an SDK fee estimate a transaction carries."""
    options = {"distribution": estimate["distribution"], "feeValue": estimate["feeValue"]}
    allocations = estimate.get("messageAllocations")
    if allocations:
        options["messageAllocations"] = allocations
    return options


class Chain:
    def __init__(self, account=None, client=None):
        self.account = account
        self.v06 = network_name() in V06_NETWORKS
        # Injectable so the retry policy can be tested against a client that
        # fails on purpose, without a network.
        self.client = client if client is not None else create_client(chain=chain(), account=account)

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
        # One attempt, never a retry. The faucet has been measured crediting the
        # account and THEN returning an error, so a retry loop on error credits
        # again on every pass. The balance difference below is the only evidence
        # that counts, in either direction.
        try:
            self.client.fund_account(address, amount)
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
        print(f"  deploying {path.relative_to(ROOT).as_posix()} ({size} bytes)")
        if size > 55_000:
            print("  warning: Studio resets request bodies near 60KB, this may need retries")
        call = {"code": code, "args": args}
        if self.v06:
            call["fees"] = _fee_options(retry("deploy fee estimate", self.client.estimate_transaction_fees, DEPLOY_FEES))
        # Same guard as write(): a deploy resent after a lost response is a
        # second contract, and the first one is then the one nobody can find.
        tx = self._guarded("deploy", lambda: self.client.deploy_contract(**call))
        receipt = self.wait(tx, "FINALIZED", retries=150)
        # On a v0.6 network a deploy of code the runtime refuses still
        # finalizes, with FINISHED_WITH_ERROR, so finality is not success.
        outcome = check(receipt)
        if not outcome["ok"]:
            raise RuntimeError(f"deploy of {path.name} did not succeed: {outcome['detail']}")
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
        if self.v06:
            return retry(
                "read " + method,
                lambda: self.client.read_contract(
                    address=address, function_name=method, args=args or [],
                    account=self.account or _reader(),
                ),
            )
        try:
            return retry("read " + method, self.client.read_contract, address, method, args or [])
        except Exception as error:
            if _studio_devnet is not None and network_name() == "studionet" and "gen_call failed" in str(error):
                raise RuntimeError(STUDIONET_UNDER_V06.format(version=SDK_VERSION)) from error
            raise

    def read_json(self, address: str, method: str, args: list | None = None) -> dict:
        return json.loads(self.read(address, method, args))

    def write(self, address: str, method: str, args: list | None = None, value: int = 0) -> str:
        """
        A write, retried only while it is provably unsent.

        The SDK fetches the nonce and signs inside every write_contract call. So
        a plain retry around it, on a response lost AFTER the node accepted the
        transaction, fetches nonce N+1 and sends a second transaction, and for
        `pay` that is a second payment. The docstring on retry() used to claim
        this could not happen. It could.

        The nonce is the evidence. It is read before the attempt and again after
        a failure: unchanged means nothing reached the node and a retry is safe;
        advanced means the transaction exists and is not sent again, whatever
        the error said. One extra read per write is what that costs.
        """
        def attempt():
            call = {"address": address, "function_name": method, "args": args or [], "value": value}
            if self.v06:
                call["fees"] = self._write_fees(address, method, args or [], value)
            return self.client.write_contract(**call)

        return self._guarded("write " + method, attempt)

    def _write_fees(self, address: str, method: str, args: list, value: int) -> dict:
        """
        The fee deposit for one write on a v0.6 network, from Studio's own
        estimate of that call. The estimate includes the budget for the messages
        the call emits, which a flat allocation would leave unfunded: pay and
        open_dispute emit, and an emitted message with no budget never runs.
        """
        try:
            estimate = retry(
                "fee estimate for " + method,
                self.client.estimate_transaction_fees_for_write,
                address=address, function_name=method, account=self.account,
                args=args, value=value,
            )
        except RuntimeError:
            raise
        except Exception:  # noqa: BLE001  a write Studio expects to be refused, or cannot simulate
            flat = dict(WRITE_FEES)
            payees = self._root_payees(address, method, args) if method in ROOT_PAYOUTS else []
            if payees:
                # The SDK derives the message total from the allocations. A
                # stated 0 beside a budget reverts at submission with
                # MessageAllocationsNotEqualBudget.
                del flat["totalMessageFees"]
                flat["messageAllocations"] = [_external_node(payee) for payee in payees]
            estimate = retry("flat fee estimate", self.client.estimate_transaction_fees, flat)
        else:
            if method in CASCADES:
                estimate = self._cascade(estimate, CASCADES[method])
        return _fee_options(estimate)

    def _root_payees(self, address: str, method: str, args: list) -> list[str]:
        """
        Who a top-level payout pays. withdraw pays its caller, who must be the
        seller. reclaim pays the payment to the seller and the bond to the
        buyer. A payment that cannot be read gets no allocation, and the write
        goes on chain to be refused there, where the refusal is recorded.
        """
        if method == "withdraw" and self.account is not None:
            return [self.account.address]
        if method == "reclaim" and args:
            try:
                row = self.read_json(address, "get_payment", [args[0]])
            except Exception:  # noqa: BLE001
                return []
            return [row["seller"], row["buyer"]]
        return []

    def _cascade(self, estimate: dict, cascade: dict) -> dict:
        """
        Studio's estimate, with the messages below its first emissions
        allocated as well.

        Each message a cascade names goes in as a child of the allocation that
        emits it, with that allocation's own fee parameters and its own
        minimum budget, and the parent's budget grows by the child's: a
        parent must carry what its children spend. Unused budget is refunded
        at finalization, so erring high costs nothing but the deposit.
        """
        from genlayer_py.transactions.fees import derive_internal_message_call_key

        nodes = [dict(node) for node in estimate.get("messageAllocations") or []]
        if not nodes:
            return estimate
        deployment = load_deployment()
        roles = {name: deployment[name] for name in ("escrow", "dispute")}
        for parent_method, children in cascade.items():
            wanted = str(derive_internal_message_call_key(parent_method)).lower()
            for index in range(len(nodes)):
                key = nodes[index]["callKey"]
                key = "0x" + bytes(key).hex() if isinstance(key, (bytes, bytearray)) else str(key)
                if key.lower() != wanted:
                    continue
                own = int(nodes[index]["budget"])
                for method, role, on_acceptance in children:
                    nodes.append({
                        "messageType": 1,
                        "onAcceptance": on_acceptance,
                        "parentIndex": index,
                        "recipient": roles[role],
                        "callKey": derive_internal_message_call_key(method),
                        "budget": own,
                        "feeParams": nodes[index]["feeParams"],
                    })
                    nodes[index]["budget"] = int(nodes[index]["budget"]) + own
        options = {k: v for k, v in (estimate.get("distribution") or {}).items() if k != "totalMessageFees"}
        options["messageAllocations"] = nodes
        return retry("cascade fee estimate", self.client.estimate_transaction_fees, options)

    def _guarded(self, what: str, attempt):
        sender = self.account.address if self.account else None
        last: Exception | None = None
        for index in range(RETRIES):
            before = self._nonce(sender)
            try:
                return attempt()
            except Exception as error:  # noqa: BLE001
                text = str(error)
                if (
                    "reverted" in text
                    or "UserError" in text
                    or "[EXPECTED]" in text
                    or "insufficient" in text
                ):
                    raise
                last = error
                after = self._nonce(sender)
                if sender is not None and (before is None or after is None):
                    # Cannot tell whether it was sent. The only safe default
                    # when a payment may exist is not to make another one.
                    raise RuntimeError(
                        f"{what}: failed and the nonce could not be read before and "
                        f"after, so it may or may not have been sent: {text[:120]}. "
                        "Not resending."
                    ) from error
                if before is not None and after is not None and after > before:
                    raise RuntimeError(
                        f"{what}: the node accepted a transaction (nonce {before} -> {after}) "
                        f"and then the response was lost: {text[:120]}. Not resending. "
                        "Find it by nonce rather than paying twice."
                    ) from error
                if index == RETRIES - 1:
                    break
                wait = BACKOFF**index
                print(f"  retry {index + 1}/{RETRIES} on {what}: {text[:110]}")
                time.sleep(wait)
        raise RuntimeError(f"{what} failed after {RETRIES} attempts: {last}")

    def _nonce(self, sender) -> int | None:
        """The account's transaction count, or None if it cannot be read right now."""
        if sender is None:
            return None
        try:
            return int(retry("nonce", self.client.get_current_nonce, address=sender))
        except Exception:  # noqa: BLE001
            # Unknown is not the same as unchanged. The caller treats None as
            # "cannot tell" and does not resend on it either way, because the
            # only safe default when a payment may exist is not to make another.
            return None

    def wait(self, tx_hash, status: str = "ACCEPTED", retries: int = 40) -> dict:
        if self.v06:
            # consensus v0.6 names the two points "decided" and "finalized".
            # ACCEPTED is a decision the committee reached; FINALIZED is the
            # same after the appeal window.
            return retry(
                "wait",
                self.client.wait_for_transaction_receipt,
                transaction_hash=tx_hash,
                wait_until="finalized" if status == "FINALIZED" else "decided",
                interval=3000,
                retries=retries,
            )
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
    # A v0.6 receipt nests it further down, under names that have moved between
    # SDK releases. The first address-shaped value under either name is it.
    found = _find_key(receipt, ("contract_address", "contractAddress"))
    return found if isinstance(found, str) and found.startswith("0x") else None


def _find_key(node, names):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in names and value:
                return value
        for value in node.values():
            hit = _find_key(value, names)
            if hit:
                return hit
    elif isinstance(node, list):
        for value in node:
            hit = _find_key(value, names)
            if hit:
                return hit
    return None


def _summary(receipt) -> str:
    if not isinstance(receipt, dict):
        return str(receipt)[:300]
    keep = {k: receipt.get(k) for k in ("status", "lifecycle", "tx_id", "hash", "type") if k in receipt}
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


def receipt_status(receipt: dict) -> str:
    """
    The receipt's status as one of the names above.

    A genlayer-py 0.19 receipt carries no status field at all: it carries a
    lifecycle, a state (decided or finalized) and an outcome (accepted, or what
    went wrong). A decision the committee accepted is ACCEPTED, the same after
    finality is FINALIZED, and any other outcome is named for itself.
    """
    lifecycle = receipt.get("lifecycle")
    if isinstance(lifecycle, dict) and lifecycle.get("state"):
        state = str(lifecycle["state"]).lower()
        outcome = str(lifecycle.get("outcome") or "").lower()
        if outcome in ("", "accepted"):
            return {"decided": "ACCEPTED", "finalized": "FINALIZED"}.get(state, state.upper())
        return outcome.upper()
    return status_name(receipt.get("status", ""))


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

    status = receipt_status(receipt)
    consensus = receipt.get("consensus_data") or {}
    leader = (consensus.get("leader_receipt") or [{}])
    if isinstance(leader, dict):
        leader = [leader]
    first = leader[0] if leader else {}
    # A v0.6 receipt names the execution result at the top level; an older one
    # only in the leader's receipt.
    execution = str(
        receipt.get("txExecutionResultName")
        or receipt.get("tx_execution_result_name")
        or first.get("execution_result", "")
    ).upper()
    genvm = first.get("genvm_result") or {}
    stderr = str(genvm.get("stderr", ""))[:400]
    stdout = str(genvm.get("stdout", ""))[:400]

    # The sentence the contract raised is NOT in stderr, which is empty, and not
    # in any field named error. It is the payload of the leader's result, beside
    # a status of "rollback". Measured on Studio: a refused settle answers
    # execution_result ERROR, empty stderr, and
    # consensus_data.leader_receipt[0].result.payload == "[EXPECTED] not authorised".
    outcome = first.get("result") or {}
    refusal = ""
    if isinstance(outcome, dict) and str(outcome.get("status", "")).lower() in ("rollback", "user_error"):
        payload = outcome.get("payload")
        refusal = payload if isinstance(payload, str) else str(payload)

    ok = status in SETTLED and execution in ("SUCCESS", "FINISHED_WITH_RETURN", "")
    detail = ""
    if not ok:
        error = ""
        if isinstance(outcome, dict) and not refusal and outcome.get("status") not in (None, "return"):
            error = f"{outcome.get('status')}: {outcome.get('payload')}"
        detail = f"status={status} execution={execution} {refusal or error or stderr or stdout}".strip()
    return {
        "ok": ok,
        "status": status,
        "execution": execution,
        "detail": detail,
        "refusal": refusal,
        "stderr": stderr,
        "stdout": stdout,
        "receipt": receipt,
        "result": _returned(first),
    }


def _returned(leader_receipt: dict) -> typing.Any:
    """
    The value the contract returned.

    A successful call answers {"status": "return", "payload": {"readable": ...}},
    where readable is the value as JSON text. A refusal answers status rollback
    and the payload is the message instead, which is why the status is checked
    before the payload is read as a value.
    """
    outcome = leader_receipt.get("result")
    if isinstance(outcome, dict) and str(outcome.get("status", "")).lower() == "return":
        payload = outcome.get("payload")
        if isinstance(payload, dict) and "readable" in payload:
            try:
                return json.loads(payload["readable"])
            except (ValueError, TypeError):
                return payload["readable"]
        return payload
    return outcome


# --- the deployment record ------------------------------------------------
def load_deployment() -> dict:
    """
    This machine's record for the network it is currently talking to.

    deployed.json is written for one network at a time. Reading it under a
    different RECOURSE_NETWORK would pay a seller registered on one network
    from a record written for another, so a mismatch stops here and says which
    script rewrites it.
    """
    if not DEPLOYED.exists():
        raise SystemExit(
            f"deployed.json is missing. Run: python scripts/prepare.py --network {network_name()}"
        )
    record = json.loads(DEPLOYED.read_text(encoding="utf-8"))
    recorded = record.get("network")
    if recorded and recorded != network_name():
        raise SystemExit(
            f"deployed.json is for {recorded} but RECOURSE_NETWORK is {network_name()}. "
            f"Run: python scripts/prepare.py --network {network_name()}"
        )
    return record


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
