"""Conversation ID helpers with ULID-compatible formatting."""
from __future__ import annotations

import hashlib
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
    """Return a ULID-compatible conversation ID.

    Home Assistant's conversation API expects a strict ULID-like pattern.
    We therefore normalize all incoming IDs to this format:
    - valid ULID -> keep (uppercased)
    - non-empty custom ID -> deterministic ULID mapping
    - missing/empty -> random ULID
    """
    if isinstance(value, str):
        candidate = value.strip()
        if candidate:
            upper = candidate.upper()
            if is_valid_conversation_id(upper):
                return upper
            return _stable_ulid_from_text(candidate)
    return generate_ulid()


def _stable_ulid_from_text(text: str) -> str:
    """Map arbitrary text deterministically to a ULID-shaped identifier."""
    digest = hashlib.sha1(text.encode("utf-8")).digest()
    # Use 130 bits (exactly 26 Crockford base32 chars).
    value = int.from_bytes(digest[:17], "big") >> 6
    return _encode_crockford_base32(value, 26)
