"""
A test double for the parts of `genlayer` these two contracts touch.

WHAT THIS PROVES, AND WHAT IT DOES NOT.

It proves the contracts' own logic: which guard fires first, what a method
writes, how a payment moves between states, whether a refusal is the sentence it
should be, and whether the settlement table moves the right money to the right
party. Every bug found in this project so far has lived there.

It does NOT prove anything about GenVM. Storage here is plain Python objects, so
it says nothing about slot layout, about calldata encoding, or about consensus.
A test passing here and a transaction succeeding on chain are different claims,
and this file can only ever support the first. Consensus behaviour is measured
by the evaluation set and by the integration tests, not here.

It exists because `genlayer-test` downloads a GenVM binary and there is no
Windows build, so without it none of the contract logic could be executed at all
on this machine.

The doubles are deliberately thin. Anything clever would be a second
implementation to be wrong in its own way.
"""

from __future__ import annotations

import typing


class UserError(Exception):
    """`gl.vm.UserError`. The refusal a caller reads."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class VMError(Exception):
    """A VM level failure. The contracts never raise one; the validator reads it."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message


class Return:
    """`gl.vm.Return`. Wraps a leader result that came back successfully."""

    def __init__(self, value: typing.Any) -> None:
        self.calldata = value


class Address:
    """A 20 byte address. Compares by value, which is what the contracts rely on."""

    def __init__(self, value: typing.Any) -> None:
        text = str(value).strip()
        if not text.startswith("0x") or len(text) != 42:
            raise ValueError(f"not an address: {text}")
        self._hex = text

    @property
    def as_hex(self) -> str:
        return self._hex

    def __eq__(self, other: typing.Any) -> bool:
        return isinstance(other, Address) and other._hex.lower() == self._hex.lower()

    def __ne__(self, other: typing.Any) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self._hex.lower())

    def __repr__(self) -> str:
        return f"Address({self._hex})"


def _sized(bits: int, signed: bool = False):
    limit = 1 << bits

    def make(value: typing.Any = 0) -> int:
        number = int(value)
        if not signed and (number < 0 or number >= limit):
            raise ValueError(f"u{bits} out of range: {number}")
        return number

    return make


u8 = _sized(8)
u32 = _sized(32)
u64 = _sized(64)
u256 = _sized(256)


class _Generic:
    """Makes `DynArray[str]` and `TreeMap[Address, Seller]` valid annotations."""

    def __init__(self, empty) -> None:
        self._empty = empty

    def __getitem__(self, _item) -> "_Generic":
        return self

    def empty(self):
        return self._empty()


DynArray = _Generic(list)
TreeMap = _Generic(dict)


def allow_storage(cls):
    """Marks a dataclass as storable. Nothing to do here."""
    return cls


class _Write:
    """`@gl.public.write` and `@gl.public.write.payable`."""

    def __init__(self, surface: "_Public") -> None:
        self._surface = surface

    def __call__(self, fn):
        self._surface.writes.append(fn.__name__)
        fn.__gl_kind__ = "write"
        return fn

    def payable(self, fn):
        self._surface.writes.append(fn.__name__)
        self._surface.payables.append(fn.__name__)
        fn.__gl_kind__ = "payable"
        return fn


class _Public:
    """Records the public surface so a test can assert what is callable."""

    def __init__(self) -> None:
        self.writes: list[str] = []
        self.views: list[str] = []
        self.payables: list[str] = []
        self.write = _Write(self)

    def view(self, fn):
        self.views.append(fn.__name__)
        fn.__gl_kind__ = "view"
        return fn


class _Vm:
    UserError = UserError
    VMError = VMError
    Return = Return

    def __init__(self, bus: "Bus") -> None:
        self._bus = bus

    def run_nondet_unsafe(self, leader_fn, validator_fn):
        """
        One leader run, then the validator's own independent run against it.

        Real consensus runs the validator on several nodes. Here one is enough,
        because what is under test is what the contract DOES with the answer and
        how the validator decides, not how votes are counted. A validator that
        returns False is a Disagree, which terminates the VM, so it is raised.
        """
        self._bus.nondet_runs += 1
        try:
            leader_result: typing.Any = Return(leader_fn())
        except UserError as error:
            leader_result = error
        except VMError as error:  # pragma: no cover - the double never raises one
            leader_result = error

        agreed = validator_fn(leader_result)
        self._bus.validator_votes.append(bool(agreed))
        if not agreed:
            raise VMError("validator disagreed")
        if isinstance(leader_result, Return):
            return leader_result.calldata
        raise leader_result


class _Message:
    """Mutable, so a test can act as different senders and send value."""

    def __init__(self) -> None:
        self.sender_address = Address("0x" + "11" * 20)
        self.origin_address = Address("0x" + "11" * 20)
        self.contract_address = Address("0x" + "cc" * 20)
        self.value = 0
        self.chain_id = 61999


class Transfer(typing.NamedTuple):
    sender: str
    to: str
    value: int


class Emission(typing.NamedTuple):
    sender: str
    to: str
    method: str
    args: tuple
    on: str


class Bus:
    """
    Everything that leaves a contract: value transfers and emitted messages.

    Emitted messages are recorded rather than delivered, because on chain each
    one becomes its own transaction and the emitting call returns before it
    runs. A test that wants the cycle completed calls `deliver` explicitly, so
    the two halves stay visibly separate.
    """

    def __init__(self) -> None:
        self.transfers: list[Transfer] = []
        self.emissions: list[Emission] = []
        self.contracts: dict[str, typing.Any] = {}
        self.nondet_runs = 0
        self.validator_votes: list[bool] = []
        self.current: Address = Address("0x" + "cc" * 20)

    def register(self, address: str, instance: typing.Any) -> None:
        self.contracts[address.lower()] = instance

    def deliver(self, gl: "GL", index: int = -1) -> typing.Any:
        """
        Run one recorded emission as its own call.

        The sender becomes the emitting contract, which is what the receiving
        contract sees on chain. In an emitted message sender_address and
        origin_address are both the emitter, so both are set.
        """
        emission = self.emissions.pop(index)
        target = self.contracts.get(emission.to.lower())
        if target is None:
            raise AssertionError(f"nothing deployed at {emission.to}")
        previous_sender = gl.message.sender_address
        previous_origin = gl.message.origin_address
        previous_contract = gl.message.contract_address
        previous_value = gl.message.value
        gl.message.sender_address = Address(emission.sender)
        gl.message.origin_address = Address(emission.sender)
        gl.message.contract_address = Address(emission.to)
        gl.message.value = 0
        self.current = Address(emission.to)
        try:
            return getattr(target, emission.method)(*emission.args)
        finally:
            gl.message.sender_address = previous_sender
            gl.message.origin_address = previous_origin
            gl.message.contract_address = previous_contract
            gl.message.value = previous_value
            self.current = previous_contract


class _Sender:
    def __init__(self, bus: Bus, address: str, on: str) -> None:
        self._bus = bus
        self._address = address
        self._on = on

    def __getattr__(self, method: str):
        def call(*args, **kwargs):
            if kwargs:
                raise AssertionError("emitted calls are positional on chain")
            self._bus.emissions.append(
                Emission(
                    sender=self._bus.current.as_hex,
                    to=self._address,
                    method=method,
                    args=args,
                    on=self._on,
                )
            )

        return call


class _ContractProxy:
    def __init__(self, bus: Bus, address: Address) -> None:
        self._bus = bus
        self._address = address.as_hex

    def emit(self, *, value: int = 0, on: str = "finalized") -> _Sender:
        if value:
            self._bus.transfers.append(
                Transfer(self._bus.current.as_hex, self._address, int(value))
            )
        return _Sender(self._bus, self._address, on)

    def emit_transfer(self, *, value: int, on: str = "finalized") -> None:
        self._bus.transfers.append(
            Transfer(self._bus.current.as_hex, self._address, int(value))
        )


class _Evm:
    """`gl.evm.contract_interface`. The external message form, used for payouts."""

    def __init__(self, bus: Bus) -> None:
        self._bus = bus

    def contract_interface(self, declaration):
        bus = self._bus

        class Proxy:
            def __init__(self, address: Address) -> None:
                self.address = address

            def emit_transfer(self, *, value: int) -> None:
                bus.transfers.append(
                    Transfer(bus.current.as_hex, self.address.as_hex, int(value))
                )

        Proxy.__name__ = getattr(declaration, "__name__", "Proxy")
        return Proxy


class _Nondet:
    """`gl.nondet`. The model's answer is whatever the test queued."""

    def __init__(self) -> None:
        self.answers: list[typing.Any] = []
        self.prompts: list[str] = []

    def exec_prompt(self, prompt: str, **_config) -> str:
        self.prompts.append(prompt)
        if not self.answers:
            raise AssertionError("no model answer queued")
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


class GL:
    """The `gl` namespace, assembled."""

    def __init__(self) -> None:
        self.bus = Bus()
        self.vm = _Vm(self.bus)
        self.public = _Public()
        self.message = _Message()
        self.message_raw: dict = {
            "datetime": "2026-09-04T18:20:00Z",
            "is_init": True,
        }
        self.nondet = _Nondet()
        self.evm = _Evm(self.bus)
        self.Contract = Contract

    def get_contract_at(self, address: Address) -> _ContractProxy:
        return _ContractProxy(self.bus, address)


class Contract:
    """
    Base class. Zero-initialises annotated storage fields the way GenVM does, so
    a constructor that appends to a collection it never assigned still runs.
    """

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        for name, annotation in getattr(cls, "__annotations__", {}).items():
            if isinstance(annotation, _Generic):
                setattr(instance, name, annotation.empty())
            elif annotation is str:
                setattr(instance, name, "")
            elif annotation is bool:
                setattr(instance, name, False)
            else:
                setattr(instance, name, 0)
        return instance
