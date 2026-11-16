"""Custom SQLAlchemy column types."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Text
from sqlalchemy.types import TypeDecorator

from app.security.crypto import get_keyring


class EncryptedText(TypeDecorator):
    """Text column that is transparently encrypted with AES-256-GCM.

    The database only ever sees ``v1:<base64 nonce+ciphertext>``. Encrypted
    columns cannot be searched or sorted with SQL, so only use this for free
    text that should never be queried (descriptions, notes, findings).
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return get_keyring().encrypt_field(str(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return get_keyring().decrypt_field(value)


class UTCDateTime(TypeDecorator):
    """Timezone-aware UTC datetime on every database (SQLite stores naive values)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        value = value.astimezone(timezone.utc)
        if dialect.name == "sqlite":
            return value.replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
