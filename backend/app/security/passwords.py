"""Admin password hashing (Argon2id) and password policy."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# argon2-cffi defaults to Argon2id with RFC 9106 "low memory" parameters
# (t=3, m=64 MiB, p=4).
_hasher = PasswordHasher()

# A dummy hash used to keep login timing similar for unknown usernames.
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing-equalisation")

MIN_LENGTH = 12
MAX_LENGTH = 128

_COMMON = {
    "password", "password1", "password123", "123456789012", "qwertyuiop", "letmein",
    "welcome", "admin", "administrator", "gaonsaathi", "gaon saathi", "iloveyou",
    "changeme", "passw0rd", "india123", "qwerty123456", "1q2w3e4r5t6y", "abc123456789",
    "password@123", "admin@123", "admin12345", "welcome@123",
}


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> tuple[bool, bool]:
    """Return (is_valid, needs_rehash). Always does the expensive work."""
    try:
        _hasher.verify(password_hash or _DUMMY_HASH, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False, False
    if password_hash is None:
        return False, False
    return True, _hasher.check_needs_rehash(password_hash)


def password_problems(password: str, username: str | None = None) -> list[str]:
    """Return human readable reasons why a password is not acceptable."""
    problems: list[str] = []
    if len(password) < MIN_LENGTH:
        problems.append(f"Password must be at least {MIN_LENGTH} characters long.")
    if len(password) > MAX_LENGTH:
        problems.append(f"Password must be at most {MAX_LENGTH} characters long.")
    lowered = password.lower()
    if lowered in _COMMON or lowered.strip("0123456789!@#") in _COMMON:
        problems.append("Password is too common. Choose a less predictable password.")
    if username and len(username) >= 3 and username.lower() in lowered:
        problems.append("Password must not contain the username.")
    if len(set(password)) < 6:
        problems.append("Password uses too few different characters.")
    return problems
