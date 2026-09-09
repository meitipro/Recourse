#!/usr/bin/env python3
"""
The linter as a local HTTP service, on port 4503.

    python linter/serve.py

    POST /lint      {"promise": "..."}  ->  the linter shape, or {"error": "..."}
    POST /judge     {"promise", "request", "response", "timing" optional}  ->
                    a dry run of the frozen contract's judge(). One model, no
                    chain, no money. Without timing the clock now is used.
    GET  /health
    GET  /examples  the six worked examples, without running them

The site route, the bot and the MCP server all talk to this or to a hosted copy
of it. It holds no state and keeps no log of what is sent to it: the access log
records the method, the path and the status, never the body, because somebody
will paste something commercially sensitive into the panel on day one.

Loopback only. Nothing here needs to be reachable from anywhere else.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from linter.examples import EXAMPLES  # noqa: E402
from linter.judgment import dry_run  # noqa: E402
from linter.service import ModelUnavailable, backend_name, backend_status, lint  # noqa: E402

MAX_BODY = 8192

#: The longest any one of the three strings may be. The escrow caps the
#: response at 4000 and refuses more, so nothing longer could ever have been
#: judged on chain and there is no point asking a model about it.
MAX_STRING = 4000


class Handler(BaseHTTPRequestHandler):
    server_version = "recourse-linter"

    def log_message(self, fmt: str, *args) -> None:
        # The default log line includes the request line, which for POST is
        # just the path. Kept to that on purpose: no body, no promise, ever.
        sys.stderr.write(f"  linter {self.command} {self.path} {args[1] if len(args) > 1 else ''}\n")

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(200, {"ok": True, **backend_status()})
            return
        if self.path == "/examples":
            self._send(200, {"examples": EXAMPLES})
            return
        self._send(404, {"error": "not found"})

    def _body(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._send(400, {"error": "bad content length"})
            return None
        if length < 0 or length > MAX_BODY:
            self._send(413, {"error": "body too large"})
            return None
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            self._send(400, {"error": "bad json"})
            return None
        if not isinstance(payload, dict):
            self._send(400, {"error": "body must be an object"})
            return None
        return payload

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/lint":
            self._lint()
            return
        if self.path == "/judge":
            self._judge()
            return
        self._send(404, {"error": "not found"})

    def _lint(self) -> None:
        payload = self._body()
        if payload is None:
            return
        promise = payload.get("promise")
        if not isinstance(promise, str):
            self._send(400, {"error": "promise must be a string"})
            return
        try:
            self._send(200, lint(promise))
        except ModelUnavailable as error:
            self._send(503, {"error": str(error)})
        except ValueError as error:
            # The model answered twice without JSON. Say so; never guess.
            self._send(502, {"error": f"the model gave no usable answer: {error}"})

    def _judge(self) -> None:
        """
        A dry run of the frozen contract's own judge(), for the clerk.

        One model where the chain uses a committee of five, and no chain at all,
        so every answer carries recorded_on_chain false. Nothing here is a
        verdict; it is what one model says the verdict would be.
        """
        payload = self._body()
        if payload is None:
            return
        strings = {name: payload.get(name) for name in ("promise", "request", "response")}
        for name, value in strings.items():
            if not isinstance(value, str) or not value.strip():
                self._send(400, {"error": f"{name} must be a non-empty string"})
                return
            if len(value) > MAX_STRING:
                self._send(413, {"error": f"{name} is longer than the contract accepts"})
                return
        # The chain writes the timing block, and a committed case carries the
        # one it was judged against. Without it a case from last week is judged
        # against this second's clock, and anything with a freshness bound comes
        # back not honored however good it was. A caller that sends none gets
        # now, and the reply says which was used.
        timing = payload.get("timing")
        if timing is not None and (not isinstance(timing, str) or len(timing) > MAX_STRING):
            self._send(400, {"error": "timing must be a string the contract would accept"})
            return
        supplied = bool(timing and timing.strip())
        started = time.time()
        try:
            answer = dry_run(
                strings["promise"], strings["request"], strings["response"],
                timing=timing if supplied else None,
            )
        except ModelUnavailable as error:
            self._send(503, {"error": str(error)})
            return
        except ValueError as error:
            self._send(502, {"error": f"the model gave no usable answer: {error}"})
            return
        self._send(200, {
            "verdict": answer["verdict"],
            "reason": answer["reason"],
            # judge() asks in both presentation orders and resolves a
            # disagreement to unclear in the value. Whether the two agreed is
            # the interesting part, so it is not swallowed here.
            "agreed": answer.get("agreed", ""),
            "seconds": round(time.time() - started, 1),
            "recorded_on_chain": False,
            "timing_from": "the case" if supplied else "the clock now",
            "dry_run": "The frozen contract's own judge(), one model, no chain and no money.",
        })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4503)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"linter on http://{args.host}:{args.port}  backend={backend_name()}")
    print("  POST /lint   POST /judge   GET /health   GET /examples   (bodies are never logged)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
