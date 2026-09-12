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
of it: api/lint.py and api/judge.py answer through the same two functions on
Vercel. It holds no state and keeps no log of what is sent to it: the access
log records the method, the path and the status, never the body, because
somebody will paste something commercially sensitive into the panel on day one.

Loopback only. Nothing here needs to be reachable from anywhere else.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from linter.examples import EXAMPLES  # noqa: E402
from linter.judgment import answer  # noqa: E402
from linter.service import ModelUnavailable, backend_name, backend_status, lint  # noqa: E402

#: Room for a /judge request at its largest: three strings of up to 4000
#: characters each and a timing block. The old limit of 8192 refused a case the
#: clerk's own route accepts.
MAX_BODY = 20000


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
        """A dry run of the frozen contract's own judge(), for the clerk: linter/judgment.py:answer."""
        payload = self._body()
        if payload is None:
            return
        code, body = answer(payload)
        self._send(code, body)


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
