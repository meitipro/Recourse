"""
One canonicaliser, imported by the seller, the buyer agent, the evaluation
runner and the demo.

This file exists specifically to prevent an hour lost to a signature mismatch.
The signature is over a canonical serialisation, the same string goes on chain,
and the same string is what the validators read. If the endpoint serialises one
way and the agent another, the signature check fails and nothing about the error
says so.

Import it. Never re-serialise a body that has already been canonicalised, and
never let a web framework do it for you.
"""

from __future__ import annotations

import hashlib
import json
import typing


def canonical(obj: typing.Any) -> str:
    """
    Sorted keys, no whitespace, unicode kept as written.

    ensure_ascii is off so a non-ascii value hashes as the characters it is
    rather than as an escape sequence, which is what any other language would
    produce reading the same bytes.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(obj: typing.Any) -> str:
    """sha256 over the canonical form, hex."""
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def digest_text(text: str) -> str:
    """sha256 over a string already in its final form. Used on the recorded body."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
