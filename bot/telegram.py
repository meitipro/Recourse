"""
The Telegram Bot API over the standard library. Long polling, two methods.

No dependency, because a bot that holds no key and keeps no state needs none.
Message text is never logged: the transport reports update ids and chat ids
and nothing a person typed.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{token}/{method}"


class Telegram:
    def __init__(self, token: str) -> None:
        if not token or ":" not in token:
            raise ValueError("TELEGRAM_BOT_TOKEN is missing or malformed")
        self._token = token
        self.offset = 0

    def _call(self, method: str, payload: dict, timeout: int = 40) -> dict:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            API.format(token=self._token, method=method),
            data=data, headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = json.loads(error.read().decode("utf-8") or "{}")
        if not body.get("ok"):
            raise RuntimeError(f"telegram {method}: {body.get('description', 'no description')}")
        return body["result"]

    def me(self) -> dict:
        return self._call("getMe", {})

    def updates(self) -> list[dict]:
        rows = self._call(
            "getUpdates",
            {"offset": self.offset, "timeout": 30, "allowed_updates": ["message"]},
            timeout=45,
        )
        if rows:
            self.offset = rows[-1]["update_id"] + 1
        return rows

    def send(self, chat_id: int, text: str) -> None:
        # Telegram caps a message at 4096 characters. Split on paragraphs
        # rather than truncating a verdict mid sentence.
        for chunk in _chunks(text, 4000):
            self._call("sendMessage", {"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True})

    def log(self, message: str) -> None:
        sys.stderr.write(f"  bot {message}\n")


def _chunks(text: str, size: int) -> list[str]:
    if len(text) <= size:
        return [text]
    out: list[str] = []
    current = ""
    for paragraph in text.split("\n\n"):
        candidate = paragraph if not current else current + "\n\n" + paragraph
        if len(candidate) > size and current:
            out.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        out.append(current)
    return [piece[:size] for piece in out]
