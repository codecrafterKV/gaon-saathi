"""Privacy-friendly anti-spam: a small proof-of-work challenge.

Instead of a third-party CAPTCHA (which would send visitor data to another
company), the browser solves a small SHA-256 puzzle in the background while
the person fills the form. One submission costs a phone well under a second;
a spam bot sending thousands of complaints must pay that cost thousands of
times.

Challenge format:  v1.<base64url(json payload)>.<base64url(hmac)>
Solution: a decimal counter such that SHA-256("<challenge>:<counter>") starts
with at least ``d`` zero bits.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.database import get_sessionmaker
from app.models import SpentChallenge
from app.security.crypto import get_keyring


class ChallengeError(Exception):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _sign(payload_b64: str) -> str:
    return _b64(hmac.new(get_keyring().pow_key, payload_b64.encode("ascii"), hashlib.sha256).digest())


def issue_challenge() -> dict:
    settings = get_settings()
    now = int(time.time())
    payload = {
        "n": secrets.token_hex(16),
        "iat": now,
        "exp": now + settings.pow_ttl_seconds,
        "d": settings.pow_difficulty,
    }
    payload_b64 = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return {
        "challenge": f"v1.{payload_b64}.{_sign(payload_b64)}",
        "difficulty": settings.pow_difficulty,
        "expires_in": settings.pow_ttl_seconds,
    }


def leading_zero_bits(digest: bytes) -> int:
    bits = 0
    for byte in digest:
        if byte == 0:
            bits += 8
            continue
        bits += 8 - byte.bit_length()
        break
    return bits


def verify_and_spend(challenge: str, solution: str) -> None:
    """Validate a solved challenge and mark it as used. Raises ChallengeError.

    The challenge is spent in its own short transaction, so it stays spent
    even if the rest of the submission fails (the browser simply solves a
    new one), and concurrent replays are rejected by the primary key.
    """
    settings = get_settings()
    if not challenge or not solution or len(challenge) > 400 or len(solution) > 20 or not solution.isdigit():
        raise ChallengeError("Security check missing or invalid.")
    try:
        version, payload_b64, signature = challenge.split(".")
    except ValueError as exc:
        raise ChallengeError("Security check invalid.") from exc
    if version != "v1" or not hmac.compare_digest(signature, _sign(payload_b64)):
        raise ChallengeError("Security check invalid.")
    try:
        payload = json.loads(_unb64(payload_b64))
        nonce, issued, expires, difficulty = payload["n"], int(payload["iat"]), int(payload["exp"]), int(payload["d"])
    except (ValueError, KeyError, TypeError) as exc:
        raise ChallengeError("Security check invalid.") from exc

    now = int(time.time())
    if now > expires:
        raise ChallengeError("Security check expired. Please try again.")
    if now - issued < settings.pow_min_solve_seconds:
        raise ChallengeError("Submitted too quickly. Please try again.")
    if difficulty < settings.pow_difficulty:
        raise ChallengeError("Security check invalid.")
    digest = hashlib.sha256(f"{challenge}:{solution}".encode("ascii")).digest()
    if leading_zero_bits(digest) < difficulty:
        raise ChallengeError("Security check failed. Please try again.")

    # Single use: the nonce is the primary key, so a replay violates uniqueness.
    with get_sessionmaker()() as db:
        db.execute(delete(SpentChallenge).where(SpentChallenge.expires_at < datetime.now(timezone.utc)))
        db.add(SpentChallenge(nonce=str(nonce)[:64],
                              expires_at=datetime.fromtimestamp(expires, timezone.utc) + timedelta(minutes=5)))
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ChallengeError("This security check was already used. Please try again.") from exc
