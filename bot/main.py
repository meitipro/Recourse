#!/usr/bin/env python3
"""
Run the bot.

    TELEGRAM_BOT_TOKEN=123:abc python bot/main.py

Read only. The chain client runs on a throwaway account that holds nothing, so
this process cannot sign, pay, dispute or withdraw even by mistake, and
tests/direct/test_bot.py asserts that against the client object. Free text is
answered by a model handed the five reads and nothing else. Message text is
never logged.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from bot.agent import default_chat  # noqa: E402
from bot.handlers import Context, respond  # noqa: E402
from bot.records import Unavailable  # noqa: E402
from bot.state import Bucket, Conversations, Seen, Threads  # noqa: E402
from bot.telegram import Telegram  # noqa: E402


def reader():
    """
    A chain reader on a throwaway account.

    The Python SDK refuses a read without a sender address, so a reader with no
    account at all fails on its first call, which is what the first version of
    this did. The account here is generated at startup from nothing, holds no
    GEN, is never written to disk and is never handed to a write: bot/ names no
    write method, and tests/direct/test_bot.py holds it to that.
    """
    from genlayer_py import create_account

    from shared.chain import Chain

    return Chain(account=create_account())


class LiveDeps:
    """The real dependencies. Each failure becomes Unavailable, never a guess."""

    def __init__(self) -> None:
        from shared.chain import EXPLORERS, frozen_deployment, network_name

        self._chain = reader()
        self._network = network_name()
        self._entry = frozen_deployment(self._network)
        self._explorer = self._entry.get("explorer") or EXPLORERS.get(self._network, "")

    def addresses(self) -> dict:
        return {
            "network": self._network,
            "escrow": self._entry["escrow"],
            "dispute": self._entry["dispute"],
            "explorer": self._explorer,
        }

    def read_json(self, contract: str, method: str, args: list):
        try:
            return self._chain.read_json(contract, method, args)
        except Exception as error:  # noqa: BLE001
            raise Unavailable(str(error)[:160]) from error

    def lint(self, promise: str) -> dict:
        from linter.service import ModelUnavailable, lint

        try:
            return lint(promise)
        except ModelUnavailable as error:
            raise Unavailable(str(error)) from error
        except ValueError as error:
            raise Unavailable(f"the model gave no usable answer: {error}") from error

    def dry_run(self, promise: str, response: str) -> dict:
        from linter.judgment import dry_run
        from linter.service import ModelUnavailable

        try:
            return dry_run(promise, "as sent to the endpoint", response)
        except ModelUnavailable as error:
            raise Unavailable(str(error)) from error
        except ValueError as error:
            raise Unavailable(f"the model gave no usable answer: {error}") from error

    def evaluation(self) -> dict:
        out = {}
        for label, name in (("tuned", "results.json"), ("held_out", "results-v2.json")):
            path = ROOT / "eval" / name
            if not path.exists():
                raise Unavailable(f"{name} is not in the repository")
            data = json.loads(path.read_text(encoding="utf-8"))
            out[label] = {"accuracy": data["accuracy"], "n": data["n"], "stability": data["stability"]}
        return out


def main() -> int:
    import argparse

    from shared.chain import select_network

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network", default=None, help="the network to run against; default studionet, the only deployment")
    args = parser.parse_args()
    network = select_network(args.network)

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("TELEGRAM_BOT_TOKEN is not set. Create a bot with @BotFather and export its token.")
        return 2
    telegram = Telegram(token)
    me = telegram.me()
    chat = default_chat()
    ctx = Context(
        conversations=Conversations(),
        bucket=Bucket(),
        deps=LiveDeps(),
        threads=Threads(),
        seen=Seen(),
        chat=chat,
    )
    ready, why = chat.ready()
    print(f"bot @{me.get('username')} polling {network}. Read only, no key, nothing logged but ids.")
    print(f"free text: {chat.name if ready else 'off, ' + str(why)}")
    while True:
        try:
            for update in telegram.updates():
                out = respond(update, me, ctx)
                if out is None:
                    continue
                telegram.send(out.chat_id, out.text, reply_to=out.reply_to, thread_id=out.thread_id)
                telegram.log(f"update {update.get('update_id')} chat {out.chat_id} answered")
        except KeyboardInterrupt:
            print("\n  stopped")
            return 0
        except Exception as error:  # noqa: BLE001
            telegram.log(f"loop error: {str(error)[:120]}")
            time.sleep(3)


if __name__ == "__main__":
    raise SystemExit(main())
