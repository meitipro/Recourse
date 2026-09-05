# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""
RecourseEscrow - the money path.

Fully deterministic. No model call, no web access, no randomness, no float.
Every raise carries the [EXPECTED] prefix, because business logic errors must
match byte for byte across validators for them to agree that the same error is
the correct execution result.

Deterministic execution has to reproduce identically on every validator. A
mismatch is classified as a deterministic violation, which opens a tribunal and
can slash the leader by five percent of stake. That is why judgment lives in a
separate contract and nothing here reads a model, a clock of its own, or the web.
"""

import datetime
import hashlib
import json
from dataclasses import dataclass

from genlayer import *

# --- error prefixes -------------------------------------------------------
# Only one class of error can arise in this contract. External, transient and
# model errors are impossible here because nothing external is touched, and a
# prefix that can never fire is a prefix nobody maintains correctly.
E = "[EXPECTED] "

# --- payment status -------------------------------------------------------
ST_OPEN = u8(0)
ST_WITHDRAWN = u8(1)
ST_DISPUTED = u8(2)
ST_RESOLVED = u8(3)

# --- verdict codes --------------------------------------------------------
# Shared with the dispute contract. The escrow never produces one, it only
# applies the settlement table to one it is handed.
V_NONE = u8(0)
V_HONORED = u8(1)
V_NOT_HONORED = u8(2)
V_UNCLEAR = u8(3)

# --- limits ---------------------------------------------------------------
# Everything the contract stores ends up on chain and everything the promise
# and the response contain is read by validators, so both are capped.
MIN_PROMISE = 20
MAX_PROMISE = 500
MAX_REQUEST = 2000
MAX_RESPONSE = 4000
MAX_RECENT = 100
#: A secp256k1 signature is 130 hex characters, 132 with a prefix. This is the
#: one party written field that had no bound, which made it the one way to put
#: an arbitrary amount of data in a payment row. It degrades only the seller's
#: own evidence, since recent_rows returns whether a signature exists rather
#: than the signature, but every other string a party writes here is bounded
#: and an unbounded one is a gap whatever its blast radius.
MAX_SIG = 200

ZERO = Address("0x" + "0" * 40)

_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)


# --- time -----------------------------------------------------------------
def _seconds(iso: str) -> int:
    """
    Transaction time as whole seconds since the epoch.

    gl.message carries no timestamp. The deterministic time source is
    gl.message_raw['datetime'], an ISO 8601 string fixed for the transaction and
    therefore identical on every validator. Verified against the pinned SDK,
    genlayer/_internal/msg.py, field `datetime`.

    The subtraction is done against a fixed epoch rather than through
    .timestamp(), which returns a float. No float appears anywhere in this
    contract, including here.
    """
    text = iso.strip()
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    delta = parsed - _EPOCH
    return delta.days * 86400 + delta.seconds


def _iso(seconds: int) -> str:
    """The inverse, for the timing block the validators read. Integer only."""
    return (_EPOCH + datetime.timedelta(seconds=int(seconds))).strftime("%Y-%m-%dT%H:%M:%SZ")


def _digest(text: str) -> str:
    """
    sha256 of a promise, so the gate can tell a changed promise from a repeat
    request without a second copy of the string in storage.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- payout ---------------------------------------------------------------
# A buyer and a seller are ordinary accounts, and an ordinary account lives on
# the chain layer rather than in GenVM. gl.get_contract_at(addr).emit_transfer()
# delivers the value as a contract call, which an account cannot answer, so that
# payout fails as its own transaction. The external message form below is the
# one that addresses the chain layer. Its kwargs carry `value` only, with no
# `on`, verified against genlayer/py/evm/generate.py TransactionDataKwArgs.
@gl.evm.contract_interface
class _Payee:
    class View:
        pass

    class Write:
        pass


@allow_storage
@dataclass
class Seller:
    #: Plain language description of what a valid response contains. This is the
    #: standard the seller is judged against, so it is frozen while any payment
    #: is live.
    promise: str
    #: Sellers are never deleted, so listing one is a flag rather than a removal.
    active: bool
    #: Set by the judgeability gate. True until a gate says otherwise, so the
    #: field exists from day one and the gate can be wired without a migration.
    judgeable: bool
    registered_at: u64
    #: Payments received, all time.
    total: u32
    #: Disputes lost. The only counter a verdict can move.
    upheld: u32
    #: Payments currently OPEN or DISPUTED. Kept as a counter rather than
    #: derived by scanning payment_ids, because that scan grows without bound
    #: and would eventually make update_promise impossible to execute.
    live: u32
    #: sha256 of the promise the judgeability gate last ruled on, or empty.
    #: A seller the gate refused may change their promise and ask again; this is
    #: what stops them asking the same question until the answer suits.
    reviewed: str


@allow_storage
@dataclass
class Payment:
    buyer: Address
    seller: Address
    amount: u256
    #: Captured at pay time, before any response exists.
    request: str
    #: Recorded once and never changed. This is what makes the evidence frozen.
    response: str
    #: The seller's signature over sha256 of the canonical response body. Empty
    #: when the buyer recorded the response instead.
    response_sig: str
    #: Who wrote the response. The seller normally; the buyer when the seller
    #: declined to, which is the path that stops a seller blocking a dispute by
    #: staying silent.
    recorded_by: Address
    created_at: u64
    #: When the response was written on chain. Zero until it is. This is the
    #: tightest chain observed upper bound on when the response existed, and it
    #: is what a freshness promise has to be judged against.
    responded_at: u64
    window_ends: u64
    #: After this, a dispute that never produced a verdict can be unwound by
    #: either party. Zero until a dispute is opened. Without it a judgment that
    #: never lands holds both the payment and the bond permanently, and neither
    #: side has anywhere to go.
    dispute_ends: u64
    bond: u256
    status: u8
    verdict: u8


class RecourseEscrow(gl.Contract):
    #: Deployer. Holds one privilege only, wiring the dispute contract once.
    owner: Address
    #: The only address allowed to call settle. Set once and never again, so a
    #: compromised owner cannot redirect settlement later.
    dispute_contract: Address
    #: Settlement window in seconds. Minutes, not hours.
    window_seconds: u32
    #: How long a dispute may sit undecided before either party can unwind it.
    #: Long enough that a slow round is never mistaken for a dead one.
    dispute_seconds: u32
    #: What a buyer stakes to contest, sized to the cost of one adjudication.
    bond_amount: u256
    #: Monotonic payment counter. Payment ids are derived from it rather than
    #: from any value a caller controls.
    seq: u64
    #: Sum of amount plus bond across every payment not yet settled. Tracked so
    #: the solvency invariant is a read rather than a scan.
    held: u256
    sellers: TreeMap[Address, Seller]
    payments: TreeMap[str, Payment]
    #: Append only, newest last. The feed reads it through recent().
    payment_ids: DynArray[str]

    def __init__(self, window_seconds: u32, bond_amount: u256, dispute_seconds: u32 = u32(3600)):
        self.owner = gl.message.sender_address
        self.dispute_contract = ZERO
        self.window_seconds = window_seconds
        self.dispute_seconds = dispute_seconds
        self.bond_amount = bond_amount
        self.seq = u64(0)
        self.held = u256(0)

    # -- internals ---------------------------------------------------------

    def _now(self) -> u64:
        return u64(_seconds(gl.message_raw["datetime"]))

    def _next_id(self) -> str:
        self.seq = u64(self.seq + u64(1))
        return "p-" + str(int(self.seq)).zfill(6)

    def _payment(self, pid: str) -> Payment:
        if pid not in self.payments:
            raise gl.vm.UserError(E + "unknown payment")
        return self.payments[pid]

    def _send(self, to: Address, amount: u256) -> None:
        if amount == u256(0):
            return
        if amount > self.held:
            # Unreachable if the accounting is right. Kept because the failure
            # it guards against is paying out money that belongs to a different
            # payment, which is worse than a refused transaction.
            raise gl.vm.UserError(E + "payout exceeds held")
        self.held = u256(self.held - amount)
        _Payee(to).emit_transfer(value=amount)

    # -- admin -------------------------------------------------------------

    @gl.public.write
    def set_dispute_contract(self, addr: str) -> None:
        if gl.message.sender_address != self.owner:
            raise gl.vm.UserError(E + "not owner")
        if self.dispute_contract != ZERO:
            raise gl.vm.UserError(E + "dispute contract already set")
        target = Address(addr)
        if target == ZERO:
            raise gl.vm.UserError(E + "zero address")
        self.dispute_contract = target

    # -- seller ------------------------------------------------------------

    @gl.public.write
    def register_seller(self, promise: str) -> None:
        who = gl.message.sender_address
        if who in self.sellers:
            raise gl.vm.UserError(E + "already registered")
        if len(promise) < MIN_PROMISE or len(promise) > MAX_PROMISE:
            raise gl.vm.UserError(E + "promise length")
        self.sellers[who] = Seller(
            promise=promise,
            active=True,
            judgeable=True,
            registered_at=self._now(),
            total=u32(0),
            upheld=u32(0),
            live=u32(0),
            reviewed="",
        )

    @gl.public.write
    def update_promise(self, promise: str) -> None:
        who = gl.message.sender_address
        if who not in self.sellers:
            raise gl.vm.UserError(E + "not registered")
        if self.sellers[who].live != u32(0):
            raise gl.vm.UserError(E + "open payments")
        if len(promise) < MIN_PROMISE or len(promise) > MAX_PROMISE:
            raise gl.vm.UserError(E + "promise length")
        self.sellers[who].promise = promise

    @gl.public.write
    def set_judgeable(self, seller: str, ok: bool) -> None:
        """
        The judgeability gate's verdict on a promise.

        Only the dispute contract may call it. A seller who could clear their own
        promise would face no gate at all, and an owner who could unlist a seller
        would be an operator choosing which endpoints get judged.
        """
        if gl.message.sender_address != self.dispute_contract:
            raise gl.vm.UserError(E + "not authorised")
        key = Address(seller)
        if key not in self.sellers:
            raise gl.vm.UserError(E + "unknown seller")
        self.sellers[key].judgeable = ok
        # The ruling has landed, so this promise has now been reviewed. Recorded
        # here rather than when the review was requested, so a gate transaction
        # that never arrives leaves the seller able to ask again.
        self.sellers[key].reviewed = _digest(self.sellers[key].promise)

    @gl.public.write
    def set_active(self, active: bool) -> None:
        who = gl.message.sender_address
        if who not in self.sellers:
            raise gl.vm.UserError(E + "not registered")
        self.sellers[who].active = active

    # -- payment -----------------------------------------------------------

    @gl.public.write.payable
    def pay(self, seller: str, request: str) -> str:
        addr = Address(seller)
        if addr not in self.sellers:
            raise gl.vm.UserError(E + "unknown seller")
        entry = self.sellers[addr]
        if not entry.active:
            raise gl.vm.UserError(E + "seller inactive")
        if not entry.judgeable:
            raise gl.vm.UserError(E + "promise not judgeable")
        value = gl.message.value
        if value == u256(0):
            raise gl.vm.UserError(E + "zero value")
        if len(request) > MAX_REQUEST:
            raise gl.vm.UserError(E + "request too long")

        now = self._now()
        pid = self._next_id()
        self.payments[pid] = Payment(
            buyer=gl.message.sender_address,
            seller=addr,
            amount=value,
            request=request,
            response="",
            response_sig="",
            recorded_by=ZERO,
            created_at=now,
            responded_at=u64(0),
            window_ends=u64(now + u64(self.window_seconds)),
            dispute_ends=u64(0),
            bond=u256(0),
            status=ST_OPEN,
            verdict=V_NONE,
        )
        self.payment_ids.append(pid)
        self.sellers[addr].total = u32(entry.total + u32(1))
        self.sellers[addr].live = u32(entry.live + u32(1))
        self.held = u256(self.held + value)
        return pid

    @gl.public.write
    def record_response(self, pid: str, response: str, sig: str) -> None:
        """
        Freeze the evidence.

        The seller records normally and signs. The buyer may record instead when
        the seller has not, which closes the one path where an endpoint could
        take payment, deliver nothing on chain, and leave the buyer unable to
        contest. The recorder is stored, so a response with no seller signature
        is visibly a response the seller never stood behind.
        """
        payment = self._payment(pid)
        who = gl.message.sender_address
        if who != payment.seller and who != payment.buyer:
            raise gl.vm.UserError(E + "not a party")
        if payment.status != ST_OPEN:
            raise gl.vm.UserError(E + "not open")
        if payment.response != "":
            raise gl.vm.UserError(E + "response already recorded")
        if response == "":
            raise gl.vm.UserError(E + "empty response")
        if self._now() > payment.window_ends:
            raise gl.vm.UserError(E + "window closed")
        if len(response) > MAX_RESPONSE:
            raise gl.vm.UserError(E + "response too long")
        if len(sig) > MAX_SIG:
            raise gl.vm.UserError(E + "signature too long")

        self.payments[pid].response = response
        self.payments[pid].response_sig = sig if who == payment.seller else ""
        self.payments[pid].recorded_by = who
        self.payments[pid].responded_at = self._now()

    @gl.public.write
    def withdraw(self, pid: str) -> None:
        payment = self._payment(pid)
        if gl.message.sender_address != payment.seller:
            raise gl.vm.UserError(E + "not seller")
        if payment.status != ST_OPEN:
            raise gl.vm.UserError(E + "not open")
        if self._now() <= payment.window_ends:
            raise gl.vm.UserError(E + "window open")

        # Status moves before the value leaves, so a repeated call is refused by
        # the status check rather than racing the payout.
        self.payments[pid].status = ST_WITHDRAWN
        self.sellers[payment.seller].live = u32(self.sellers[payment.seller].live - u32(1))
        self._send(payment.seller, payment.amount)

    # -- dispute -----------------------------------------------------------

    @gl.public.write.payable
    def open_dispute(self, pid: str) -> None:
        payment = self._payment(pid)
        if gl.message.sender_address != payment.buyer:
            raise gl.vm.UserError(E + "not buyer")
        if payment.status != ST_OPEN:
            raise gl.vm.UserError(E + "not open")
        if payment.response == "":
            raise gl.vm.UserError(E + "no response")
        if self._now() > payment.window_ends:
            raise gl.vm.UserError(E + "window closed")
        if gl.message.value != self.bond_amount:
            raise gl.vm.UserError(E + "wrong bond")
        if self.dispute_contract == ZERO:
            raise gl.vm.UserError(E + "dispute contract not set")

        self.payments[pid].bond = gl.message.value
        self.payments[pid].status = ST_DISPUTED
        self.payments[pid].dispute_ends = u64(self._now() + u64(self.dispute_seconds))
        self.held = u256(self.held + gl.message.value)

        promise = self.sellers[payment.seller].promise
        # The three party strings travel exactly as recorded. The fourth is the
        # chain's own account of when each arrived, which is the reference clock
        # a freshness promise has to be judged against. Neither party writes it,
        # so neither party can move the boundary they are being judged on.
        timing = (
            "Request recorded on chain at "
            + _iso(int(payment.created_at))
            + ". Response recorded on chain at "
            + _iso(int(payment.responded_at))
            + "."
        )
        # Judgment starts on acceptance, money moves on finalization.
        #
        # Adjudicating writes a case row and emits a settlement message; it moves
        # nothing, so it is safe before finality. Waiting for this transaction to
        # finalize first would stack two appeal windows back to back and measured
        # 89 seconds end to end on Studio against 45 for this ordering.
        #
        # If an appeal later overturns this transaction the dispute is rolled
        # back, and the settlement message that judgment emitted is refused by
        # settle's own status check, because the payment is no longer DISPUTED.
        gl.get_contract_at(self.dispute_contract).emit(on="accepted").adjudicate(
            pid, promise, payment.request, payment.response, timing
        )

    @gl.public.write
    def reclaim(self, pid: str) -> None:
        """
        Unwind a dispute that never produced a verdict.

        A refusal has to leave the refused party somewhere to go, and so does a
        judgment that never arrives. Without this a round that cannot reach
        consensus holds the payment and the bond permanently, with neither side
        able to do anything about it, and the contract describes a settlement it
        can no longer perform.

        Either party may call it, because both are stuck and neither can force
        the other to. It applies the unclear split: the payment stands with the
        seller, the bond goes back to the buyer. That is the right answer when
        the judgment failed rather than when a party did, and it is deliberately
        not attractive to a buyer who might otherwise stall for it: contesting
        and then waiting out the clock gets the bond back and nothing else, which
        is exactly what dropping the dispute would have got them.

        A verdict that lands late finds the payment RESOLVED and is refused by
        settle's own status check, so this can never pay twice.
        """
        payment = self._payment(pid)
        who = gl.message.sender_address
        if who != payment.buyer and who != payment.seller:
            raise gl.vm.UserError(E + "not a party")
        if payment.status != ST_DISPUTED:
            raise gl.vm.UserError(E + "not disputed")
        if self._now() <= payment.dispute_ends:
            raise gl.vm.UserError(E + "judgment still running")

        self.payments[pid].status = ST_RESOLVED
        self.payments[pid].verdict = V_UNCLEAR
        self.sellers[payment.seller].live = u32(self.sellers[payment.seller].live - u32(1))
        self._send(payment.seller, payment.amount)
        self._send(payment.buyer, payment.bond)

    @gl.public.write
    def request_review(self) -> None:
        """
        Ask the judgeability gate to look again, after changing the promise.

        A seller the gate refused would otherwise have nowhere to go: pay refuses
        them, and only the dispute contract can clear the flag. This is the route
        out, and the guard is what stops it being a way to ask the same question
        until the answer suits. The promise must have changed since the last
        review, and the escrow sends the promise from its own storage rather than
        one the caller supplies, so a seller cannot submit one promise for review
        and serve against another.
        """
        who = gl.message.sender_address
        if who not in self.sellers:
            raise gl.vm.UserError(E + "not registered")
        entry = self.sellers[who]
        if self.dispute_contract == ZERO:
            raise gl.vm.UserError(E + "dispute contract not set")
        if entry.live != u32(0):
            raise gl.vm.UserError(E + "open payments")
        if entry.reviewed == _digest(entry.promise):
            raise gl.vm.UserError(E + "promise unchanged since the last review")

        # The digest is recorded by set_judgeable when a ruling actually comes
        # back, not here. Recording it on the request would mean a gate
        # transaction that failed for any reason burned that promise for good:
        # the seller could never have it reviewed again, and changing it back
        # would hash to the same value. That is a dead end, which is the thing
        # this method exists to remove.
        gl.get_contract_at(self.dispute_contract).emit(on="finalized").check_promise(
            who.as_hex, entry.promise
        )

    @gl.public.write
    def settle(self, pid: str, verdict: u8, reason: str) -> None:
        """
        Apply the settlement table. The single most important access check in
        the project: without it any account could name its own verdict and drain
        every payment held here.
        """
        if gl.message.sender_address != self.dispute_contract:
            raise gl.vm.UserError(E + "not authorised")
        payment = self._payment(pid)
        if payment.status != ST_DISPUTED:
            raise gl.vm.UserError(E + "not disputed")
        if verdict != V_HONORED and verdict != V_NOT_HONORED and verdict != V_UNCLEAR:
            raise gl.vm.UserError(E + "bad verdict")

        # State first, then value. Both payouts below can only be reached once.
        self.payments[pid].status = ST_RESOLVED
        self.payments[pid].verdict = verdict
        self.sellers[payment.seller].live = u32(self.sellers[payment.seller].live - u32(1))

        if verdict == V_NOT_HONORED:
            # The buyer is made whole and the loss lands on the seller's record.
            self.sellers[payment.seller].upheld = u32(
                self.sellers[payment.seller].upheld + u32(1)
            )
            self._send(payment.buyer, u256(payment.amount + payment.bond))
        elif verdict == V_HONORED:
            # Contesting a response that turned out to be good costs the bond,
            # or contesting everything would be free.
            self._send(payment.seller, u256(payment.amount + payment.bond))
        else:
            # Unclear is the promise's fault, not the buyer's, so the bond comes
            # back and no counter moves.
            self._send(payment.seller, payment.amount)
            self._send(payment.buyer, payment.bond)

    # -- views -------------------------------------------------------------
    # Every view answers JSON with sorted keys, so two reads of unchanged state
    # are byte identical and a diff between them means something.

    @gl.public.view
    def get_payment(self, pid: str) -> str:
        payment = self._payment(pid)
        return json.dumps(
            {
                "pid": pid,
                "buyer": payment.buyer.as_hex,
                "seller": payment.seller.as_hex,
                "amount": str(int(payment.amount)),
                "request": payment.request,
                "response": payment.response,
                "response_sig": payment.response_sig,
                "recorded_by": payment.recorded_by.as_hex,
                "created_at": int(payment.created_at),
                "responded_at": int(payment.responded_at),
                "window_ends": int(payment.window_ends),
                "dispute_ends": int(payment.dispute_ends),
                "bond": str(int(payment.bond)),
                "status": int(payment.status),
                "verdict": int(payment.verdict),
            },
            sort_keys=True,
        )

    @gl.public.view
    def get_seller(self, addr: str) -> str:
        key = Address(addr)
        if key not in self.sellers:
            raise gl.vm.UserError(E + "unknown seller")
        entry = self.sellers[key]
        return json.dumps(
            {
                "address": key.as_hex,
                "promise": entry.promise,
                "active": entry.active,
                "judgeable": entry.judgeable,
                "registered_at": int(entry.registered_at),
                "total": int(entry.total),
                "upheld": int(entry.upheld),
                "live": int(entry.live),
                "reviewed": entry.reviewed,
            },
            sort_keys=True,
        )

    @gl.public.view
    def recent(self, n: u32) -> list[str]:
        """Last n payment ids, newest first, capped at 100."""
        want = int(n)
        if want > MAX_RECENT:
            want = MAX_RECENT
        if want < 0:
            want = 0
        out: list[str] = []
        index = len(self.payment_ids) - 1
        while index >= 0 and len(out) < want:
            out.append(self.payment_ids[index])
            index -= 1
        return out

    @gl.public.view
    def recent_rows(self, n: u32) -> str:
        """
        The last n payments as one JSON array, newest first.

        The feed used to read recent() and then get_payment() once per id, which
        is one request per row. Studio allows thirty requests a minute, so a
        page with a dozen payments on it rate limited itself on a normal load
        and rendered an error. One call is the fix.

        The request and response bodies are deliberately left out. They are the
        largest fields by far and only one row's worth is ever on screen, so the
        evidence drawer fetches get_payment for the row being opened.
        """
        want = int(n)
        if want > MAX_RECENT:
            want = MAX_RECENT
        if want < 0:
            want = 0
        rows: list = []
        index = len(self.payment_ids) - 1
        while index >= 0 and len(rows) < want:
            pid = self.payment_ids[index]
            payment = self.payments[pid]
            rows.append(
                {
                    "pid": pid,
                    "buyer": payment.buyer.as_hex,
                    "seller": payment.seller.as_hex,
                    "amount": str(int(payment.amount)),
                    "bond": str(int(payment.bond)),
                    "created_at": int(payment.created_at),
                    "responded_at": int(payment.responded_at),
                    "window_ends": int(payment.window_ends),
                    "dispute_ends": int(payment.dispute_ends),
                    "has_response": payment.response != "",
                    "signed": payment.response_sig != "",
                    "recorded_by": payment.recorded_by.as_hex,
                    "status": int(payment.status),
                    "verdict": int(payment.verdict),
                }
            )
            index -= 1
        return json.dumps(rows, sort_keys=True)

    @gl.public.view
    def stats(self) -> str:
        return json.dumps(
            {
                "bond_amount": str(int(self.bond_amount)),
                "dispute_contract": self.dispute_contract.as_hex,
                "held": str(int(self.held)),
                "owner": self.owner.as_hex,
                "payments": len(self.payment_ids),
                "window_seconds": int(self.window_seconds),
            },
            sort_keys=True,
        )
