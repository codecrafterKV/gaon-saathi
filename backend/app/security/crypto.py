"""Encryption and keyed hashing.

* Complaint text fields and evidence files are encrypted with AES-256-GCM.
* Tracking tokens and admin session tokens are stored only as HMAC-SHA256
  digests keyed with a server secret, so a database leak alone does not
  reveal them and they cannot be checked offline.

Independent sub-keys are derived with HKDF so that one key is never reused
for two purposes.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from functools import lru_cache

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.config import decode_key, get_settings

FIELD_PREFIX = "v1:"
BLOB_MAGIC = b"GSE1"
NONCE_SIZE = 12


class DecryptionError(Exception):
    """Raised when ciphertext cannot be authenticated/decrypted."""


def _hkdf(master: bytes, info: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=b"gaon-saathi/v1", info=info).derive(master)


class KeyRing:
    def __init__(self, secret_key: str, data_encryption_key: str) -> None:
        data_master = decode_key(data_encryption_key)
        if len(data_master) != 32:
            raise ValueError("DATA_ENCRYPTION_KEY must decode to 32 bytes")
        secret_master = secret_key.encode("utf-8")
        self._field = AESGCM(_hkdf(data_master, b"field-encryption"))
        self._file = AESGCM(_hkdf(data_master, b"evidence-encryption"))
        self.token_key = _hkdf(secret_master, b"tracking-token-hmac")
        self.session_key = _hkdf(secret_master, b"admin-session-hmac")
        self.pow_key = _hkdf(secret_master, b"anti-spam-challenge-hmac")

    # -- Field encryption ---------------------------------------------------
    def encrypt_field(self, plaintext: str) -> str:
        nonce = os.urandom(NONCE_SIZE)
        ct = self._field.encrypt(nonce, plaintext.encode("utf-8"), FIELD_PREFIX.encode())
        return FIELD_PREFIX + base64.b64encode(nonce + ct).decode("ascii")

    def decrypt_field(self, token: str) -> str:
        if not token.startswith(FIELD_PREFIX):
            raise DecryptionError("Unknown field encryption format")
        raw = base64.b64decode(token[len(FIELD_PREFIX):])
        try:
            return self._field.decrypt(raw[:NONCE_SIZE], raw[NONCE_SIZE:], FIELD_PREFIX.encode()).decode("utf-8")
        except InvalidTag as exc:  # wrong key or tampered data
            raise DecryptionError("Field could not be decrypted") from exc

    # -- File encryption ----------------------------------------------------
    def encrypt_blob(self, data: bytes, aad: str) -> bytes:
        nonce = os.urandom(NONCE_SIZE)
        return BLOB_MAGIC + nonce + self._file.encrypt(nonce, data, aad.encode("utf-8"))

    def decrypt_blob(self, blob: bytes, aad: str) -> bytes:
        if not blob.startswith(BLOB_MAGIC):
            raise DecryptionError("Unknown evidence encryption format")
        body = blob[len(BLOB_MAGIC):]
        try:
            return self._file.decrypt(body[:NONCE_SIZE], body[NONCE_SIZE:], aad.encode("utf-8"))
        except InvalidTag as exc:
            raise DecryptionError("Evidence could not be decrypted") from exc


@lru_cache
def get_keyring() -> KeyRing:
    settings = get_settings()
    settings.validate_secrets()
    return KeyRing(settings.secret_key, settings.data_encryption_key)


def hmac_hex(key: bytes, message: str) -> str:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def hash_tracking_token(normalised_token: str) -> str:
    return hmac_hex(get_keyring().token_key, normalised_token)


def hash_session_token(token: str) -> str:
    return hmac_hex(get_keyring().session_key, token)
