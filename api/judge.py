"""
The clerk's judge as a Vercel Python function, beside api/lint.py.

The site's clerk route derives its judge from LINTER_URL by turning /api/lint
into /api/judge. A hosted linter without this file leaves the clerk asking a URL
that does not exist, and nothing says so: the page loads, the panel renders,
and every judgment comes back "Could not reach the clerk". It worked locally
only because linter/serve.py answers /judge itself.

This file holds no logic. It answers through linter/judgment.py:answer, the
function linter/serve.py answers /judge with, which runs the frozen contract's
own judge() on one model.

It needs ANTHROPIC_API_KEY in the project's environment. Without it every
request is a 503 saying so, never an invented verdict.
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

from linter.judgment import answer  # noqa: E402
from linter.service import backend_status  # noqa: E402

#: Three strings of at most 4000 characters and a timing block, with room to spare.
MAX_BODY = 20000


class handler(BaseHTTPRequestHandler):  # noqa: N801  Vercel looks for this name
    def log_message(self, fmt: str, *args) -> None:
        # Method, path, status. Never the body: it holds a party's strings.
        sys.stderr.write(f"judge {self.command} {self.path} {args[1] if len(args) > 1 else ''}\n")

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
        if not isinstance(payload, dict):
            self._send(400, {"error": "body must be an object"})
            return
        code, body = answer(payload)
        self._send(code, body)
