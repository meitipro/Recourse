#!/usr/bin/env python3
"""
Ten questions through the bot's direct message path, against the live chain.

    python scripts/ask_bot.py

Each question is handed to bot.handlers.respond as a private chat update, the
function the Telegram loop calls, with the real reads (a throwaway chain
reader, the linter, the committed evaluation files) and the real model. For
each one it prints the reads the model made and the reply. Nothing is sent to
Telegram and nothing is written anywhere.

The only thing changed from a real chat is the bucket, which is widened so ten
questions in a row are not refused by the rate limit that a person asking
them in one minute would meet.
"""

from __future__ import annotations

import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from bot.agent import default_chat  # noqa: E402
from bot.handlers import Context, respond  # noqa: E402
from bot.main import LiveDeps  # noqa: E402
from bot.state import Bucket, Conversations, Seen, Threads  # noqa: E402

QUESTIONS = [
    "what is this",
    "is this promise any good: Returns accurate market data.",
    "is this promise any good: Returns the spot price for the requested pair, aggregated from at least three venues, with a timestamp no more than five seconds old.",
    "what happened with RC-2026-0014",
    "and the one before it",
    "how often does it rule for the seller",
    "how much is held in escrow right now, and what does losing a dispute cost the buyer",
    "has anything gone against seller 0x965c98389197055CFb3FD8b1E3e9a11AE6d40C99",
    "would this response pass",
    "should I pay an endpoint that has disputes upheld against it",
]

ME = {"id": 1, "username": "RecourseBot", "is_bot": True}
CHAT = 90001


def short(arguments: dict) -> str:
    return ", ".join(f"{key}={value[:48] + '...' if isinstance(value, str) and len(value) > 48 else value!r}" for key, value in arguments.items())


def main() -> int:
    chat = default_chat()
    ready, why = chat.ready()
    print(f"model   {chat.name if ready else 'not available: ' + str(why)}")
    ctx = Context(
        conversations=Conversations(),
        bucket=Bucket(capacity=200, per_minute=200),
        deps=LiveDeps(),
        threads=Threads(),
        seen=Seen(),
        chat=chat,
    )
    for number, question in enumerate(QUESTIONS, 1):
        trace: list = []
        update = {
            "update_id": number,
            "message": {
                "message_id": number,
                "chat": {"id": CHAT, "type": "private"},
                "from": {"id": CHAT, "is_bot": False},
                "text": question,
            },
        }
        started = time.time()
        out = respond(update, ME, ctx, trace=trace)
        print(f"\n[{number}] {question}")
        print("reads   " + ("; ".join(f"{name}({short(arguments)})" for name, arguments in trace) or "none"))
        print(f"took    {time.time() - started:.1f}s")
        print(out.text if out else "(no reply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
