"""
Loads the REAL contract files against the doubles in genvm_double.py.

Nothing is copied or re-implemented here, so a change to contracts/escrow.py is
a change to what these tests exercise. The magic comment on line one of each
contract is a runner declaration and is ignored by CPython, so the file imports
as ordinary Python.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import types

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CONTRACTS = ROOT / "contracts"

sys.path.insert(0, str(HERE))

import genvm_double as D  # noqa: E402

GEN = "1" + "0" * 18
ONE_GEN = int(GEN)


#: The two pairs the contract tests run against. "frozen" is contracts/, the
#: pair deployed on studionet. "v06" is contracts/v06/, the same files ported
#: to the runtime Studio Next runs by scripts/port.py, with
#: contracts/v06/PORT.diff as the whole difference. conftest.py runs every
#: contract test once per pair by setting PAIR for the length of the test.
PAIRS = {"frozen": CONTRACTS, "v06": CONTRACTS / "v06"}
PAIR = "frozen"

#: The test modules that execute or read a contract, and so run once per pair.
#: scripts/mutate.py runs its mutants against these same modules.
CONTRACT_MODULES = ("test_dispute", "test_escrow", "test_gate_question_has_not_drifted", "test_parity")


def contract_path(name: str) -> pathlib.Path:
    """The pair under test's <name>.py."""
    return PAIRS[PAIR] / f"{name}.py"


def _install(gl: D.GL) -> None:
    """
    Publish a `genlayer` module shaped like the runtime the pair under test was
    written for, so each pair's imports resolve the way they would on a node
    and an import the port left out fails here rather than on chain.
    """
    sys.modules.pop("genlayer.storage", None)
    module = types.ModuleType("genlayer")
    module.Address = D.Address
    module.u8 = D.u8
    module.u32 = D.u32
    module.u64 = D.u64
    module.u256 = D.u256
    if PAIR == "v06":
        # py-genlayer:5jycge4q. The star import brings Address and the integer
        # types but not gl, the storage types or the decorator: `gl` is the
        # package itself, and the storage names live in genlayer.storage.
        storage = types.ModuleType("genlayer.storage")
        storage.DynArray = D.DynArray
        storage.TreeMap = D.TreeMap
        storage.allow = D.allow_storage
        for name in ("contract", "vm", "message", "public", "nondet", "evm"):
            setattr(module, name, getattr(gl, name))
        module.storage = storage
        module.__all__ = [
            "contract", "vm", "message", "public", "nondet", "evm", "storage",
            "Address", "u8", "u32", "u64", "u256",
        ]
        sys.modules["genlayer"] = module
        sys.modules["genlayer.storage"] = storage
        return
    # py-genlayer:1jb45, the frozen pair's runtime: the star import gives gl
    # and the storage names directly.
    module.gl = gl
    module.allow_storage = D.allow_storage
    module.DynArray = D.DynArray
    module.TreeMap = D.TreeMap
    module.__all__ = [
        "gl",
        "Address",
        "allow_storage",
        "DynArray",
        "TreeMap",
        "u8",
        "u32",
        "u64",
        "u256",
    ]
    sys.modules["genlayer"] = module


def load(name: str, gl: D.GL) -> types.ModuleType:
    """Import the pair under test's <name>.py fresh against this gl."""
    _install(gl)
    path = contract_path(name)
    spec = importlib.util.spec_from_file_location(f"recourse_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class World:
    """
    One escrow, optionally one dispute contract, and the accounts around them.

    Time is explicit. `at(seconds)` sets the transaction datetime the contracts
    read, because a window that expires is the single most important thing these
    tests need to control and nothing on chain moves it on its own.
    """

    OWNER = "0x" + "a1" * 20
    SELLER = "0x" + "b2" * 20
    BUYER = "0x" + "c3" * 20
    STRANGER = "0x" + "d4" * 20
    ESCROW = "0x" + "e5" * 20
    DISPUTE = "0x" + "f6" * 20

    PROMISE = (
        "Returns the spot price for the requested pair, aggregated from at "
        "least three venues, with a timestamp no more than five seconds old."
    )

    def __init__(self, window: int = 300, bond: int = ONE_GEN, dispute: int = 3600) -> None:
        self.gl = D.GL()
        self.t = 1757009000
        self.at(self.t)
        self.escrow_mod = load("escrow", self.gl)
        self.dispute_mod: types.ModuleType | None = None
        self.dispute = None

        self.sender(self.OWNER)
        self.gl.bus.current = D.Address(self.ESCROW)
        self.gl.message.contract_address = D.Address(self.ESCROW)
        self.escrow = self.escrow_mod.RecourseEscrow(D.u32(window), D.u256(bond), D.u32(dispute))
        self.gl.bus.register(self.ESCROW, self.escrow)

    # -- controls ----------------------------------------------------------

    def at(self, seconds: int) -> "World":
        """Set transaction time. Stored as the ISO string the contracts parse."""
        import datetime

        self.t = seconds
        stamp = datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc)
        self.gl.message_raw["datetime"] = stamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        return self

    def advance(self, seconds: int) -> "World":
        return self.at(self.t + seconds)

    def sender(self, address: str, value: int = 0) -> "World":
        self.gl.message.sender_address = D.Address(address)
        self.gl.message.origin_address = D.Address(address)
        self.gl.message.contract_address = D.Address(self.ESCROW)
        self.gl.bus.current = D.Address(self.ESCROW)
        self.gl.message.value = D.u256(value)
        return self

    # -- the dispute contract ----------------------------------------------

    def wired(self) -> "World":
        """
        Point the escrow at a dispute contract address without deploying one.

        The escrow's own tests need the address and nothing else. Loading the
        judgment contract to test the money path would couple the two halves the
        whole design exists to keep apart.
        """
        self.sender(self.OWNER)
        self.escrow.set_dispute_contract(self.DISPUTE)
        self.sender(self.OWNER)
        return self

    def with_dispute(self) -> "World":
        self.dispute_mod = load("dispute", self.gl)
        self.gl.bus.current = D.Address(self.DISPUTE)
        self.gl.message.contract_address = D.Address(self.DISPUTE)
        self.gl.message.sender_address = D.Address(self.OWNER)
        self.dispute = self.dispute_mod.RecourseDispute(self.ESCROW)
        self.gl.bus.register(self.DISPUTE, self.dispute)
        self.sender(self.OWNER)
        self.escrow.set_dispute_contract(self.DISPUTE)
        return self

    # -- shorthands --------------------------------------------------------

    def register(self, promise: str | None = None, who: str | None = None) -> None:
        self.sender(who or self.SELLER)
        self.escrow.register_seller(promise if promise is not None else self.PROMISE)

    def pay(self, amount: int = 4 * ONE_GEN, request: str = "GET /quote?pair=ETH-USD") -> str:
        self.sender(self.BUYER, amount)
        pid = self.escrow.pay(self.SELLER, request)
        self.sender(self.BUYER)
        return pid

    def record(self, pid: str, response: str = '{"pair":"ETH-USD"}', sig: str = "0xsig") -> None:
        self.sender(self.SELLER)
        self.escrow.record_response(pid, response, sig)

    def dispute_it(self, pid: str, bond: int = ONE_GEN) -> None:
        self.sender(self.BUYER, bond)
        self.escrow.open_dispute(pid)
        self.sender(self.BUYER)

    def transfers(self) -> list[D.Transfer]:
        return list(self.gl.bus.transfers)

    def paid_to(self, address: str) -> int:
        return sum(t.value for t in self.gl.bus.transfers if t.to.lower() == address.lower())

    def payment(self, pid: str) -> dict:
        import json

        return json.loads(self.escrow.get_payment(pid))

    def seller(self, address: str | None = None) -> dict:
        import json

        return json.loads(self.escrow.get_seller(address or self.SELLER))

    # -- invariants --------------------------------------------------------

    def check_invariants(self) -> None:
        """
        The five from the state machine, asserted after every scenario.

        1 a payment never leaves RESOLVED or WITHDRAWN
        2 the sum of all held amounts never exceeds what the contract holds
        3 open_dispute is impossible without a recorded response
        4 withdraw is impossible before window_ends
        5 settle is impossible from any address except dispute_contract

        Three and five are behavioural and have their own tests. One and two are
        properties of the whole state and are checked here, after every scenario,
        which is the only place they can be checked cheaply.
        """
        import json

        mod = self.escrow_mod
        held = 0
        for pid in self.escrow.payment_ids:
            row = json.loads(self.escrow.get_payment(pid))
            status = row["status"]
            assert status in (0, 1, 2, 3), f"{pid} has an unknown status {status}"
            if status in (int(mod.ST_OPEN), int(mod.ST_DISPUTED)):
                held += int(row["amount"]) + int(row["bond"])
            if status in (int(mod.ST_WITHDRAWN), int(mod.ST_RESOLVED)):
                assert row["verdict"] != -1
        assert int(self.escrow.held) == held, (
            f"held {int(self.escrow.held)} does not match the sum of live payments {held}"
        )
        paid_in = sum(
            int(json.loads(self.escrow.get_payment(pid))["amount"])
            + int(json.loads(self.escrow.get_payment(pid))["bond"])
            for pid in self.escrow.payment_ids
        )
        paid_out = sum(t.value for t in self.gl.bus.transfers)
        assert paid_out <= paid_in, (
            f"paid out {paid_out} against {paid_in} taken in"
        )
        assert int(self.escrow.held) + paid_out == paid_in, (
            "money is neither held nor paid out"
        )


def raises(prefix: str, fn, *args, **kwargs) -> str:
    """Assert the call is refused, and that the refusal is the sentence it should be."""
    try:
        fn(*args, **kwargs)
    except D.UserError as error:
        message = str(error)
        assert message.startswith("[EXPECTED] "), f"unprefixed refusal: {message}"
        assert prefix in message, f"expected {prefix!r}, got {message!r}"
        return message
    raise AssertionError(f"expected a refusal containing {prefix!r}, nothing was raised")
