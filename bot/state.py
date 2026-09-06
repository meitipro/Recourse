"""
Per chat state and a per chat token bucket. In memory, nothing else.

State is keyed by chat id and cleared after ten minutes, because a half finished
/check is not worth a database and a restart losing one is acceptable. The
bucket exists because stage 2 of the linter costs real money and one person
with a loop can drain it.
"""

from __future__ import annotations

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


class Bucket:
    """
    A token bucket per chat id.

    `capacity` tokens, refilled at `per_minute` a minute. Free commands cost one,
    a command that reaches a model costs `expensive`, so a loop on /promise runs
    out long before the budget does.
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
