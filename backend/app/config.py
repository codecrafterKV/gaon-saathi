"""Application configuration.

All secrets come from environment variables (or a local, git-ignored ``.env``
file). Nothing secret is hard-coded. Run ``python -m app.cli init-env`` to
generate a development ``.env`` with fresh random keys.
"""

from __future__ import annotations

import base64
import binascii
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent


class ConfigError(RuntimeError):
    """Raised when the configuration is unsafe or incomplete."""


def decode_key(value: str) -> bytes:
    """Decode a base64 / base64url encoded key."""
    value = value.strip()
    padded = value + "=" * (-len(value) % 4)
    for decoder in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            return decoder(padded)
        except (binascii.Error, ValueError):
            continue
    raise ConfigError("Key is not valid base64.")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- General -----------------------------------------------------------
    app_env: Literal["development", "production", "test"] = "development"
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'gaon_saathi.db').as_posix()}"

    # --- Secrets (required) -----------------------------------------------
    # SECRET_KEY: >= 32 random bytes, used (via HKDF) for HMAC of tracking
    # tokens, session tokens and anti-spam challenges.
    secret_key: str = Field(default="", repr=False)
    # DATA_ENCRYPTION_KEY: base64 of exactly 32 random bytes, used (via HKDF)
    # for AES-256-GCM encryption of complaint text and evidence files.
    data_encryption_key: str = Field(default="", repr=False)

    # --- Evidence storage --------------------------------------------------
    storage_backend: Literal["local", "s3"] = "local"
    evidence_dir: Path = BACKEND_DIR / "storage" / "evidence"
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_endpoint_url: str | None = None
    s3_prefix: str = "evidence/"

    # --- Upload limits -----------------------------------------------------
    max_files_per_submission: int = 5
    max_evidence_per_complaint: int = 15
    max_image_mb: int = 10
    max_pdf_mb: int = 10
    max_video_mb: int = 50
    max_total_upload_mb: int = 80
    max_pdf_pages: int = 300

    # --- Malware scanning (optional ClamAV daemon) -------------------------
    clamav_host: str | None = None
    clamav_port: int = 3310
    clamav_timeout_seconds: int = 60

    # --- Video metadata removal -------------------------------------------
    # Path to ffmpeg. If empty we try PATH and then the bundled imageio-ffmpeg.
    ffmpeg_path: str | None = None

    # --- Anti-spam ---------------------------------------------------------
    pow_difficulty: int = 16  # leading zero bits of SHA-256 (~65k hashes on average)
    pow_ttl_seconds: int = 1800
    pow_min_solve_seconds: int = 3
    rate_limit_enabled: bool = True
    # Only enable when running behind a reverse proxy you control. When false,
    # the TCP peer address is used (and never stored).
    trust_proxy_headers: bool = False

    # --- Admin authentication ---------------------------------------------
    session_idle_minutes: int = 30
    session_max_hours: int = 8
    cookie_secure: bool | None = None  # defaults to True in production
    login_max_failures: int = 5
    login_lockout_minutes: int = 15

    # --- HTTP --------------------------------------------------------------
    hsts_enabled: bool = False
    enable_api_docs: bool | None = None  # defaults to True only in development
    serve_frontend: bool = True
    frontend_dist: Path = PROJECT_DIR / "frontend" / "dist"

    # --- Public support contact (optional, shown on the Contact page) -------
    support_email: str | None = None
    support_phone: str | None = None

    # ------------------------------------------------------------------------
    @field_validator("database_url")
    @classmethod
    def _normalise_db_url(cls, value: str) -> str:
        # Accept plain postgres:// URLs (as given by many hosts) and use psycopg 3.
        if value.startswith("postgres://"):
            value = "postgresql+psycopg://" + value[len("postgres://"):]
        elif value.startswith("postgresql://"):
            value = "postgresql+psycopg://" + value[len("postgresql://"):]
        return value

    @field_validator("evidence_dir", "frontend_dist")
    @classmethod
    def _relative_to_backend(cls, value: Path) -> Path:
        return value if value.is_absolute() else (BACKEND_DIR / value).resolve()

    @model_validator(mode="after")
    def _apply_defaults(self) -> "Settings":
        if self.cookie_secure is None:
            self.cookie_secure = self.app_env == "production"
        if self.enable_api_docs is None:
            self.enable_api_docs = self.app_env == "development"
        return self

    # ------------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def session_cookie_name(self) -> str:
        # The __Host- prefix makes browsers enforce Secure, Path=/ and no Domain.
        return "__Host-gs_session" if self.cookie_secure else "gs_session"

    def mb(self, value: int) -> int:
        return value * 1024 * 1024

    def validate_secrets(self) -> None:
        """Fail fast with a clear message if secrets are missing or weak."""
        if not self.secret_key or len(self.secret_key) < 32:
            raise ConfigError(
                "SECRET_KEY is missing or shorter than 32 characters. "
                "Run `python -m app.cli init-env` to create a development .env file."
            )
        if not self.data_encryption_key:
            raise ConfigError(
                "DATA_ENCRYPTION_KEY is missing. "
                "Run `python -m app.cli init-env` to create a development .env file."
            )
        if len(decode_key(self.data_encryption_key)) != 32:
            raise ConfigError("DATA_ENCRYPTION_KEY must be base64 of exactly 32 random bytes.")
        if self.is_production:
            if not self.cookie_secure:
                raise ConfigError("COOKIE_SECURE must be true in production (serve over HTTPS).")
            if self.is_sqlite:
                raise ConfigError("Use PostgreSQL (DATABASE_URL) in production, not SQLite.")
            if self.storage_backend == "s3" and not self.s3_bucket:
                raise ConfigError("S3_BUCKET is required when STORAGE_BACKEND=s3.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
