"""Privacy-preserving in-memory rate limiting.

Rate limiting normally needs the client IP address. To avoid storing it we:

* derive a short HMAC of the IP with a random key that exists only in memory
  and is replaced every 24 hours (and on every restart);
* keep only timestamps of recent requests per HMAC, in memory, and drop them
  as soon as the window passes.

Nothing here is written to disk, the database or the logs.

Note: limits are per process. With several worker processes each worker
keeps its own counters (see docs/DEPLOYMENT.md).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import threading
import time
from collections import deque

from fastapi import HTTPException, Request, status

from app.config import get_settings

_ROTATE_SECONDS = 24 * 60 * 60


class RateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = {}
        self._key = os.urandom(32)
        self._key_created = time.monotonic()
        self._last_sweep = time.monotonic()

    def _rotate_if_needed(self) -> None:
        now = time.monotonic()
        if now - self._key_created > _ROTATE_SECONDS:
            self._key = os.urandom(32)
            self._key_created = now
            self._hits.clear()

    def client_key(self, request: Request) -> str:
        settings = get_settings()
        ip = ""
        if settings.trust_proxy_headers:
            # Use the address appended by OUR proxy (right-most entry); earlier
            # entries are supplied by the client and can be forged.
            forwarded = request.headers.get("x-forwarded-for", "")
            ip = forwarded.split(",")[-1].strip()
        if not ip and request.client:
            ip = request.client.host
        with self._lock:
            self._rotate_if_needed()
            key = self._key
        return hmac.new(key, ip.encode("utf-8"), hashlib.sha256).hexdigest()[:24]

    def allow(self, bucket: str, limit: int, window_seconds: int) -> bool:
        now = time.monotonic()
        with self._lock:
            self._sweep(now)
            hits = self._hits.setdefault(bucket, deque())
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def _sweep(self, now: float) -> None:
        if now - self._last_sweep < 300:
            return
        self._last_sweep = now
        stale = [k for k, v in self._hits.items() if not v or now - v[-1] > 3600 * 2]
        for k in stale:
            del self._hits[k]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def rate_limit(name: str, limit: int, window_seconds: int):
    """FastAPI dependency factory enforcing ``limit`` requests per window."""

    def dependency(request: Request) -> None:
        if not get_settings().rate_limit_enabled:
            return
        bucket = f"{name}:{limiter.client_key(request)}"
        if not limiter.allow(bucket, limit, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please wait a few minutes and try again.",
            )

    return dependency
