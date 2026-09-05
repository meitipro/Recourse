#!/usr/bin/env python3
"""
The seller endpoint. A price API that can be told to misbehave.

    python seller/main.py                 # port 4501, x402 challenge
    python seller/main.py --rail external --port 4502

    GET  /quote?pair=ETH-USD              402 without payment proof, 200 with
    POST /admin/mode {"mode": "..."}      correct | stale | hollow | substituted
    GET  /promise                         the exact promise registered on chain
    GET  /health

The degradation switch is what makes the demo reproducible on camera, so it is a
first class feature rather than a test hack. Every mode returns HTTP 200 with a
well formed body and settles payment. That is the whole point: these are the
failures no deterministic check catches.

Deliberately dependency free. It runs on the standard library so a judge can
start it without installing anything.
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from seller.signing import sign_body
from shared.canonical import canonical

PROMISE = (
    "Returns the spot price for the requested pair, aggregated from at least "
    "three venues, with a timestamp no more than five seconds old."
)

MODES = ("correct", "stale", "hollow", "substituted")

#: How this endpoint expects payment to be proved. The chain never sees either
#: of these: `pay` takes a seller and a request and nothing else, so the rail is
#: a property of the conversation in front of the escrow, not of the escrow.
#:
#:   x402      the challenge names the escrow scheme, proof is x-payment-proof
#:   external  the challenge names an outside settlement system, proof is an
#:             opaque id in x-settlement-id, in the shape a card processor or a
#:             session rail hands out
#:
#: `external` exists to test the rail-agnostic claim rather than to assert it.
#: Nothing downstream of this dictionary changes with it, which is the finding.
RAILS = {
    "x402": {
        "scheme": "recourse-escrow",
        "header": "x-payment-proof",
        "description": "pay into the escrow, then present the payment id",
    },
    "external": {
        "scheme": "external-settlement",
        "header": "x-settlement-id",
        "description": "settle on your own rail, then present the settlement id",
    },
}

#: A fixed book, because the demo must produce the same thing every time it runs
#: and a live price feed would make the recording differ from the rehearsal. The
#: failure being demonstrated is about freshness and completeness, not about the
#: number being right.
BOOK = {"ETH-USD": 4182.10, "BTC-USD": 118400.00, "SOL-USD": 214.80}

STALE_HOURS = 9


class State:
    """Mode lives here so the switch is one assignment under a lock."""

    def __init__(self) -> None:
        self.mode = "correct"
        self.lock = threading.Lock()
        self.served = 0
        # Fixed at startup rather than switchable, because a rail is what the
        # endpoint is, not a state it passes through.
        self.rail = "x402"

    def set(self, mode: str) -> None:
        with self.lock:
            self.mode = mode

    def get(self) -> str:
        with self.lock:
            return self.mode


STATE = State()
KEY: str | None = None


def now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def stamp(moment: datetime.datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


#: The longest pair string this endpoint will look at. Anything the seller signs
#: becomes frozen evidence a validator reads, so the length is bounded before the
#: key touches it rather than after.
MAX_PAIR = 32

#: The admin body is one short JSON object. Content-Length is whatever the
#: caller says it is, so it is checked before it is used to size a read.
MAX_BODY = 4096


def build_body(pair: str, mode: str) -> dict:
    """
    One shape per failure mode. Each returns 200, each settles payment, and each
    passes every deterministic check that exists today.

    A pair this endpoint does not carry is refused, and that is a correctness
    fix rather than tidying. `BOOK.get(pair, 0.0)` used to answer a fabricated
    `{"price": 0.0, "sources": 3}` for anything it had never heard of, signed by
    the seller, against a promise reading "aggregated from at least three
    venues". Two things were wrong with that. The seller signed a claim it had
    not earned, and the BUYER picks the pair: paying, asking for a pair the
    seller never carried, and disputing the zero that came back is a way to
    manufacture a breach out of an honest endpoint. Refusing makes the frozen
    evidence an honest refusal, which is a thing a judge can rule on.
    """
    if pair not in BOOK:
        return {
            "error": "unsupported pair",
            "requested": pair[:MAX_PAIR],
            "supported": sorted(BOOK),
            "ts": stamp(now()),
        }
    if mode == "hollow":
        # Well formed, carrying nothing.
        return {"pair": pair, "results": [], "count": 0}
    if mode == "substituted":
        # Answers a different question than the one paid for.
        other = "BTC-USD" if pair != "BTC-USD" else "ETH-USD"
        return {
            "pair": other,
            "price": BOOK.get(other, 0.0),
            "sources": 3,
            "ts": stamp(now()),
        }
    if mode == "stale":
        # Correct shape, expired content.
        old = now() - datetime.timedelta(hours=STALE_HOURS)
        return {"pair": pair, "price": BOOK.get(pair, 0.0), "sources": 3, "ts": stamp(old)}
    return {"pair": pair, "price": BOOK.get(pair, 0.0), "sources": 3, "ts": stamp(now())}


class Handler(BaseHTTPRequestHandler):
    server_version = "recourse-seller"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"  seller {self.address_string()} {fmt % args}\n")

    def _send(self, code: int, payload: dict, headers: dict | None = None) -> None:
        body = canonical(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/health":
            self._send(
                200,
                {"ok": True, "mode": STATE.get(), "served": STATE.served, "rail": STATE.rail},
            )
            return

        if parsed.path == "/promise":
            # Served so the buyer agent can check that what this endpoint says
            # matches what is registered on chain. The chain is authoritative.
            self._send(200, {"promise": PROMISE})
            return

        if parsed.path == "/quote":
            pair = (query.get("pair") or ["ETH-USD"])[0][:MAX_PAIR]
            rail = RAILS[STATE.rail]
            proof = self.headers.get(rail["header"]) or (query.get("pid") or [""])[0]
            if not proof:
                # 402 shaped: say what payment is required and how. Which rail
                # is named here is the only thing that differs between the two,
                # and nothing on chain reads it.
                self._send(
                    402,
                    {
                        "error": "payment required",
                        "accepts": [
                            {
                                "scheme": rail["scheme"],
                                "network": "genlayer-studionet",
                                "description": rail["description"],
                                "header": rail["header"],
                            }
                        ],
                        "promise": PROMISE,
                    },
                )
                return

            mode = STATE.get()
            body = build_body(pair, mode)
            text, signature = sign_body(KEY, body) if KEY else (canonical(body), "")
            STATE.served += 1
            # The signed string is what goes on chain, so it is returned verbatim
            # rather than re-serialised by anything downstream.
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("x-response-sig", signature)
            self.send_header("x-response-mode", mode)
            self.send_header("Access-Control-Allow-Origin", "*")
            encoded = text.encode("utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            return

        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/admin/mode":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._send(400, {"error": "bad content length"})
            return
        if length < 0 or length > MAX_BODY:
            # Read what the header claims and a caller can name any number.
            self._send(413, {"error": "body too large"})
            return
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            self._send(400, {"error": "bad json"})
            return
        mode = str(payload.get("mode", "")).strip().lower()
        if mode not in MODES:
            self._send(400, {"error": f"mode must be one of {list(MODES)}"})
            return
        STATE.set(mode)
        print(f"  seller mode -> {mode}")
        self._send(200, {"mode": mode})


def main() -> int:
    global KEY
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4501)
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="interface to bind. Loopback by default: /admin/mode has no auth",
    )
    parser.add_argument("--mode", default="correct", choices=MODES)
    parser.add_argument(
        "--rail", default="x402", choices=sorted(RAILS),
        help="which settlement scheme the 402 challenge names",
    )
    args = parser.parse_args()

    STATE.set(args.mode)
    STATE.rail = args.rail

    try:
        from shared.chain import load_accounts

        KEY = load_accounts()["seller"].key.hex()
        print("  signing with the seller account from .accounts.json")
    except Exception as error:  # noqa: BLE001
        print(f"  no seller key ({str(error)[:70]}), responses will be unsigned")

    # Loopback by default. This process holds the seller's signing key and
    # exposes /admin/mode with no authentication, which is deliberate for a
    # demo and would be somebody else's switch on a conference network. Binding
    # every interface has to be asked for.
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    if args.host not in ("127.0.0.1", "localhost"):
        print(f"  WARNING: reachable on {args.host}, and /admin/mode has no auth")
    print(
        f"seller endpoint on http://{args.host}:{args.port}  "
        f"mode={STATE.get()}  rail={STATE.rail} ({RAILS[STATE.rail]['header']})"
    )
    print(f"  GET  /quote?pair=ETH-USD   POST /admin/mode   GET /promise")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
