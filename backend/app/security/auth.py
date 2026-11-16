"""Admin sessions, CSRF protection and role-based access control.

* Session tokens are 256-bit random values sent only in an HttpOnly,
  SameSite=Strict cookie (``__Host-`` prefixed and Secure in production).
  The database stores only an HMAC of the token.
* Every state-changing admin request must carry an ``X-CSRF-Token`` header.
  The CSRF token is an HMAC of the session token, so it is unique per
  session, cannot be computed by an attacker, and needs no storage.
* Sessions expire after inactivity and after an absolute maximum lifetime.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import timedelta

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.db_types import utcnow
from app.models import AdminSession, AdminUser
from app.security.crypto import constant_time_equals, hash_session_token

CSRF_HEADER = "x-csrf-token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
_LAST_SEEN_RESOLUTION = timedelta(seconds=60)


@dataclass
class AdminContext:
    user: AdminUser
    session: AdminSession
    csrf_token: str


def csrf_for(session_token: str) -> str:
    return hash_session_token("csrf:" + session_token)


def create_session(db: Session, user: AdminUser, response: Response) -> str:
    """Create a session, set the cookie and return the CSRF token."""
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    now = utcnow()
    db.add(AdminSession(
        token_hash=hash_session_token(token),
        admin_id=user.id,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(hours=settings.session_max_hours),
    ))
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_max_hours * 3600,
        path="/",
        secure=bool(settings.cookie_secure),
        httponly=True,
        samesite="strict",
    )
    return csrf_for(token)


def clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name, path="/", secure=bool(settings.cookie_secure),
        httponly=True, samesite="strict",
    )


def revoke_all_sessions(db: Session, admin_id: int, except_session_id: int | None = None) -> None:
    stmt = update(AdminSession).where(AdminSession.admin_id == admin_id, AdminSession.revoked_at.is_(None))
    if except_session_id is not None:
        stmt = stmt.where(AdminSession.id != except_session_id)
    db.execute(stmt.values(revoked_at=utcnow()))


_UNAUTHENTICATED = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Please sign in.")


def _load_session(request: Request, db: Session) -> AdminContext:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if not token or len(token) > 128:
        raise _UNAUTHENTICATED
    session = db.scalar(select(AdminSession).where(AdminSession.token_hash == hash_session_token(token)))
    now = utcnow()
    if session is None or session.revoked_at is not None or session.expires_at <= now:
        raise _UNAUTHENTICATED
    if now - session.last_seen_at > timedelta(minutes=settings.session_idle_minutes):
        session.revoked_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Your session expired because of inactivity. Please sign in again.")
    user = session.admin
    if not user.is_active:
        raise _UNAUTHENTICATED

    expected_csrf = csrf_for(token)
    if request.method not in SAFE_METHODS:
        supplied = request.headers.get(CSRF_HEADER, "")
        if not supplied or not constant_time_equals(supplied, expected_csrf):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Security token missing or invalid. Please reload the page.")

    if now - session.last_seen_at > _LAST_SEEN_RESOLUTION:
        session.last_seen_at = now
        db.commit()
    return AdminContext(user=user, session=session, csrf_token=expected_csrf)


def get_admin_allow_password_change(request: Request, db: Session = Depends(get_db)) -> AdminContext:
    """Authenticated admin, even if they still have to change their password."""
    return _load_session(request, db)


def get_admin(request: Request, db: Session = Depends(get_db)) -> AdminContext:
    ctx = _load_session(request, db)
    if ctx.user.must_change_password:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="password_change_required")
    return ctx


def require_roles(*roles: str):
    def dependency(ctx: AdminContext = Depends(get_admin)) -> AdminContext:
        if ctx.user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You do not have permission to do this.")
        return ctx

    return dependency
