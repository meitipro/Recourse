"""
The linter as a Vercel Python function, so the hosted site, the MCP server and
the bot all reach the same implementation at one URL.

This file holds no logic. It imports linter/service.py from this repository
and answers the same shape linter/serve.py answers locally. Deploying this
directory is deploying the repository's linter, not a copy of it.

Stage 2 needs ANTHROPIC_API_KEY in the project's environment. Without it, the
answer is a 503 saying so, never an invented judgeability.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
# A hosted function has no CLI to fall back to. Say api or nothing.
os.environ.setdefault("RECOURSE_LINTER_BACKEND", "api" if os.environ.get("ANTHROPIC_API_KEY") else "none")

from linter.examples import EXAMPLES  # noqa: E402
from linter.service import ModelUnavailable, backend_status, lint  # noqa: E402

MAX_BODY = 8192


class handler(BaseHTTPRequestHandler):  # noqa: N801  Vercel looks for this name
    def log_message(self, fmt: str, *args) -> None:
        # Method, path, status. Never the body.
        sys.stderr.write(f"linter {self.command} {self.path} {args[1] if len(args) > 1 else ''}\n")

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(204, {})

    def do_GET(self) -> None:  # noqa: N802
        if self.path.endswith("/examples"):
            self._send(200, {"examples": EXAMPLES})
            return
        self._send(200, {"ok": True, **backend_status()})

    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._send(400, {"error": "bad content length"})
            return
        if length < 0 or length > MAX_BODY:
            self._send(413, {"error": "body too large"})
            return
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            self._send(400, {"error": "bad json"})
            return
        promise = payload.get("promise") if isinstance(payload, dict) else None
        if not isinstance(promise, str):
            self._send(400, {"error": "promise must be a string"})
            return
        try:
            self._send(200, lint(promise))
        except ModelUnavailable as error:
            self._send(503, {"error": str(error)})
        except ValueError as error:
            self._send(502, {"error": f"the model gave no usable answer: {error}"})
