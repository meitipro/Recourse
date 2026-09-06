"""
The one thing the bot does before reading a message: check it is not a secret.

A private key or a seed phrase pasted into a chat is compromised the moment it
is sent, whatever the bot does next. So the bot says exactly that, does not
repeat it, does not comment on anything else in the message, and does not
process the rest of it.
"""

from __future__ import annotations

import re

HEX_KEY = re.compile(r"(?<![0-9a-fA-F])(?:0x)?[0-9a-fA-F]{64}(?![0-9a-fA-F])")
MNEMONIC_LENGTHS = {12, 15, 18, 21, 24}

_WORDS: frozenset[str] | None = None


def bip39_words() -> frozenset[str]:
    """The English BIP39 list, from the eth_account package already installed."""
    global _WORDS
    if _WORDS is None:
        try:
            import importlib.resources as resources

            text = (resources.files("eth_account") / "hdaccount" / "wordlist" / "english.txt").read_text(encoding="utf-8")
            _WORDS = frozenset(text.split())
        except Exception:  # noqa: BLE001
            _WORDS = frozenset()
    return _WORDS


def looks_like_secret(text: str) -> str | None:
    """
    "private key", "seed phrase", or None.

    A 64 hex character run is a key whatever surrounds it. A seed phrase is a
    run of 12, 15, 18, 21 or 24 BIP39 words, in order, anywhere in the message,
    which catches "here is my phrase: abandon abandon ..." without flagging
    ordinary sentences that happen to contain a few dictionary words.
    """
    if HEX_KEY.search(text):
        return "private key"
    words = bip39_words()
    if not words:
        return None
    tokens = re.findall(r"[a-z]+", text.lower())
    run = 0
    for token in tokens:
        run = run + 1 if token in words else 0
        if run >= 12:
            # Any run of twelve is enough to say so; the exact length does not
            # change the advice.
            return "seed phrase"
    return None


COMPROMISED = (
    "That message contains what looks like a {what}. It is now compromised, "
    "whatever this bot does: it has passed through Telegram's servers and this "
    "process. Rotate it now, move anything it controls, and never paste one "
    "into a chat again. Nothing else in that message was read."
)
