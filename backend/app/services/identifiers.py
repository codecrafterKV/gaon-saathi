"""Complaint IDs and secret tracking tokens.

Both use Python's ``secrets`` module (a CSPRNG) and an alphabet without
easily confused characters (no 0/O, 1/I) so people can copy them by hand.

* Complaint ID:   GS-2026-K7QM4XRT   (8 random chars = 40 bits, not sequential)
* Tracking code:  9PWD-H3NC-T6JA-ZB2E (16 random chars = 80 bits, shown once,
  stored only as an HMAC). Both are required to see a complaint's status.
"""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # 32 symbols -> 5 bits each
ID_RANDOM_LENGTH = 8
TOKEN_LENGTH = 16

PUBLIC_ID_RE = re.compile(r"^GS-(\d{4}|DEMO)-[" + ALPHABET + r"]{8}$")
TOKEN_RE = re.compile(r"^[" + ALPHABET + r"]{16}$")


def _random(length: int) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def new_public_id(demo: bool = False, when: datetime | None = None) -> str:
    middle = "DEMO" if demo else str((when or datetime.now(timezone.utc)).year)
    return f"GS-{middle}-{_random(ID_RANDOM_LENGTH)}"


def new_tracking_token() -> str:
    """Return a token formatted for display (XXXX-XXXX-XXXX-XXXX)."""
    raw = _random(TOKEN_LENGTH)
    return "-".join(raw[i:i + 4] for i in range(0, TOKEN_LENGTH, 4))


def normalise_public_id(value: str) -> str | None:
    cleaned = re.sub(r"\s+", "", value or "").upper()
    return cleaned if PUBLIC_ID_RE.match(cleaned) else None


def normalise_token(value: str) -> str | None:
    cleaned = re.sub(r"[\s\-]+", "", value or "").upper()
    return cleaned if TOKEN_RE.match(cleaned) else None
