"""Pure ASGI middleware: security headers and request body size limits."""

from __future__ import annotations

from app.config import get_settings

_CSP_APP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "media-src 'self' blob:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "worker-src 'self' blob:; "
    "manifest-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)


class SecurityHeadersMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        settings = get_settings()
        path: str = scope.get("path", "")

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                existing = {k.lower() for k, _ in headers}

                def add(name: str, value: str) -> None:
                    if name.encode() not in existing:
                        headers.append((name.encode(), value.encode()))

                add("x-content-type-options", "nosniff")
                add("x-frame-options", "DENY")
                add("referrer-policy", "no-referrer")
                add("permissions-policy",
                    "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=(), browsing-topics=()")
                add("cross-origin-opener-policy", "same-origin")
                add("cross-origin-resource-policy", "same-origin")
                add("x-permitted-cross-domain-policies", "none")
                add("content-security-policy", _CSP_APP)
                if settings.hsts_enabled:
                    add("strict-transport-security", "max-age=63072000; includeSubDomains")
                if path.startswith("/api/"):
                    add("cache-control", "no-store")
                    add("pragma", "no-cache")
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


class BodySizeLimitMiddleware:
    """Reject request bodies larger than allowed before they are parsed.

    Evidence submission endpoints get the evidence limit; every other
    endpoint gets a small JSON-sized limit.
    """

    SMALL_LIMIT = 256 * 1024

    def __init__(self, app) -> None:
        self.app = app

    def _limit_for(self, path: str) -> int:
        settings = get_settings()
        if path in ("/api/public/complaints", "/api/public/complaints/supplement"):
            return settings.mb(settings.max_total_upload_mb) + 2 * 1024 * 1024
        return self.SMALL_LIMIT

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit = self._limit_for(scope.get("path", ""))
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    if int(value) > limit:
                        await _send_413(send)
                        return
                except ValueError:
                    await _send_413(send)
                    return

        received = 0
        too_large = False
        replaced = False

        async def limited_receive():
            nonlocal received, too_large
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    too_large = True
                    raise _BodyTooLarge()
            return message

        async def guarded_send(message):
            # Body parsers may turn our exception into a generic 400; if the
            # body was too large, always answer with a clear 413 instead.
            nonlocal replaced
            if too_large:
                if not replaced:
                    replaced = True
                    await _send_413(send)
                return
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except _BodyTooLarge:
            if not replaced:
                await _send_413(send)


class _BodyTooLarge(Exception):
    pass


async def _send_413(send) -> None:
    body = b'{"detail":"The upload is too large. Please reduce the file sizes and try again."}'
    await send({
        "type": "http.response.start",
        "status": 413,
        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
    })
    await send({"type": "http.response.body", "body": body})
