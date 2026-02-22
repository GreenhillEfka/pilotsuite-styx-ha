"""Conversation ID helpers with ULID-compatible formatting."""
from __future__ import annotations

import secrets
import time

_ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode_crockford_base32(value: int, length: int) -> str:
    chars: list[str] = []
    for _ in range(length):
        value, rem = divmod(value, 32)
        chars.append(_ULID_ALPHABET[rem])
    return "".join(reversed(chars))


def generate_ulid() -> str:
    """Generate a 26-char ULID string (uppercase Crockford base32)."""
    ts_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand = secrets.randbits(80)
    return f"{_encode_crockford_base32(ts_ms, 10)}{_encode_crockford_base32(rand, 16)}"


def is_valid_conversation_id(value: object) -> bool:
    """Validate ULID-like conversation IDs used by HA conversation APIs."""
    if not isinstance(value, str):
        return False
    candidate = value.strip()
    if len(candidate) != 26:
        return False
    return all(ch in _ULID_ALPHABET for ch in candidate)


def normalize_conversation_id(value: object) -> str:
    """Return a stable conversation ID; generate one when missing."""
    if isinstance(value, str):
        candidate = value.strip()
        if candidate:
            return candidate
    return generate_ulid()
