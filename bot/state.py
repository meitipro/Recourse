"""
Per chat state, thread memory, answered messages and a per chat token bucket.
In memory, nothing else.

State is keyed by chat id and cleared after ten minutes, because a half
finished /check is not worth a database and a restart losing one is
acceptable. Thread memory follows the same rule. The bucket exists because
stage 2 of the linter and every free text turn cost real money, and one person
with a loop can drain it.
"""

from __future__ import annotations

import math
import threading
import time

TTL_SECONDS = 600


class Conversations:
    """What each chat is in the middle of. Ten minutes, then gone."""

    def __init__(self, ttl: int = TTL_SECONDS, clock=time.time) -> None:
        self.ttl = ttl
        self.clock = clock
        self._lock = threading.Lock()
        self._rows: dict[int, tuple[float, dict]] = {}

    def get(self, chat_id: int) -> dict | None:
        with self._lock:
            self._sweep()
            row = self._rows.get(chat_id)
            return dict(row[1]) if row else None

    def set(self, chat_id: int, state: dict) -> None:
        with self._lock:
            self._rows[chat_id] = (self.clock(), dict(state))

    def clear(self, chat_id: int) -> None:
        with self._lock:
            self._rows.pop(chat_id, None)

    def _sweep(self) -> None:
        cutoff = self.clock() - self.ttl
        for key in [k for k, (at, _) in self._rows.items() if at < cutoff]:
            del self._rows[key]

    def __len__(self) -> int:
        with self._lock:
            self._sweep()
            return len(self._rows)


class Threads:
    """
    The last six messages of each chat, so "and the one before it" resolves.

    Keyed by chat id and gone ten minutes after the last message, like the
    /check state beside it. The bot's replies are stored with every quantity
    masked (bot/agent.py:mask_quantities) before they get here, so a number
    from an earlier turn is never on hand to be repeated without a read.
    """

    def __init__(self, keep: int = 6, ttl: int = TTL_SECONDS, clock=time.time) -> None:
        self.keep = keep
        self.ttl = ttl
        self.clock = clock
        self._lock = threading.Lock()
        self._rows: dict[int, tuple[float, list[dict]]] = {}

    def history(self, chat_id: int) -> list[dict]:
        with self._lock:
            self._sweep()
            row = self._rows.get(chat_id)
            return [dict(item) for item in row[1]] if row else []

    def add(self, chat_id: int, said: str, replied: str) -> None:
        with self._lock:
            self._sweep()
            items = self._rows.get(chat_id, (0.0, []))[1]
            items = (items + [{"role": "user", "content": said}, {"role": "assistant", "content": replied}])[-self.keep :]
            self._rows[chat_id] = (self.clock(), items)
            if len(self._rows) > 10000:
                self._rows.clear()

    def clear(self, chat_id: int) -> None:
        with self._lock:
            self._rows.pop(chat_id, None)

    def _sweep(self) -> None:
        cutoff = self.clock() - self.ttl
        for key in [k for k, (at, _) in self._rows.items() if at < cutoff]:
            del self._rows[key]


class Seen:
    """
    Messages already answered. Telegram can deliver an update twice around a
    reconnect, and the rule is one reply per message.
    """

    def __init__(self, ttl: int = TTL_SECONDS, clock=time.time) -> None:
        self.ttl = ttl
        self.clock = clock
        self._lock = threading.Lock()
        self._at: dict[tuple[int, int], float] = {}

    def first(self, chat_id: int, message_id: int) -> bool:
        with self._lock:
            now = self.clock()
            if len(self._at) > 1000:
                cutoff = now - self.ttl
                self._at = {key: at for key, at in self._at.items() if at >= cutoff}
            key = (chat_id, message_id)
            if key in self._at:
                return False
            self._at[key] = now
            return True


class Bucket:
    """
    A token bucket per chat id.

    `capacity` tokens, refilled at `per_minute` a minute. Free commands cost one.
    A command that reaches a model, and every free text turn, costs `expensive`,
    so a loop runs out long before the budget does.
    """

    def __init__(self, capacity: float = 20, per_minute: float = 10, expensive: float = 5, clock=time.time) -> None:
        self.capacity = capacity
        self.rate = per_minute / 60.0
        self.expensive = expensive
        self.clock = clock
        self._lock = threading.Lock()
        self._level: dict[int, tuple[float, float]] = {}

    def take(self, chat_id: int, cost: float = 1.0) -> bool:
        with self._lock:
            now = self.clock()
            level, at = self._level.get(chat_id, (self.capacity, now))
            level = min(self.capacity, level + (now - at) * self.rate)
            if level < cost:
                self._level[chat_id] = (level, now)
                return False
            self._level[chat_id] = (level - cost, now)
            if len(self._level) > 10000:
                self._level.clear()
            return True

    def wait_seconds(self, chat_id: int, cost: float) -> int:
        """How long until this chat can afford `cost`, so a refusal can say when."""
        with self._lock:
            now = self.clock()
            level, at = self._level.get(chat_id, (self.capacity, now))
            level = min(self.capacity, level + (now - at) * self.rate)
            if level >= cost:
                return 0
            return max(1, math.ceil((cost - level) / self.rate))
