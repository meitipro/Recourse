"""
The seller's signature over the response it delivered.

The signature is what stops a seller denying that a recorded response is theirs.
It is taken over sha256 of the canonical body, and the canonical body is the
exact string that goes on chain and the exact string the validators read. One
canonicaliser, in shared/, imported here and by the agent, because two
serialisations of the same object is the classic way to lose an hour to a
signature that should have matched.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from eth_account import Account
from eth_account.messages import encode_defunct

from shared.canonical import canonical, digest_text


def sign_body(private_key: str, body: dict) -> tuple[str, str]:
    """
    Returns (the exact string that must be recorded on chain, the signature).

    Sign the string, record the string. Never re-serialise between the two: a
    framework that reorders keys or adds a space produces a body whose hash no
    longer matches the signature, and nothing in the resulting error says so.
    """
    text = canonical(body)
    signed = Account.sign_message(
        encode_defunct(text=digest_text(text)), private_key=private_key
    )
    return text, signed.signature.hex()


def recover(text: str, signature: str) -> str:
    """The address that signed a recorded response, for anyone checking the record."""
    return Account.recover_message(
        encode_defunct(text=digest_text(text)), signature=signature
    )


def verify(text: str, signature: str, expected: str) -> bool:
    try:
        return recover(text, signature).lower() == expected.lower()
    except Exception:  # noqa: BLE001
        return False
