"""Administrator authentication. There is no public registration."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import ROLES
from app.database import get_db
from app.db_types import utcnow
from app.models import AdminUser
from app.schemas import ChangePasswordRequest, LoginRequest
from app.security.auth import (
    AdminContext,
    clear_session_cookie,
    create_session,
    get_admin_allow_password_change,
    revoke_all_sessions,
)
from app.security.passwords import hash_password, password_problems, verify_password
from app.security.ratelimit import rate_limit
from app.services import audit
from app.services.complaints import iso

router = APIRouter(prefix="/api/admin/auth", tags=["admin-auth"])

LOGIN_FAILED = "Incorrect username or password, or too many attempts. Please try again later."


def user_dict(user: AdminUser) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "role_label": ROLES[user.role],
        "must_change_password": user.must_change_password,
        "last_login_at": iso(user.last_login_at),
    }


@router.post("/login", dependencies=[Depends(rate_limit("login", 10, 900))])
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    username = body.username.strip().lower()
    user = db.scalar(select(AdminUser).where(AdminUser.username == username))
    now = utcnow()

    if user is not None and user.locked_until is not None and user.locked_until > now:
        verify_password(None, body.password)  # equalise timing
        audit.record(db, None, "auth.login_blocked_locked", "admin", user.username, actor_username=user.username)
        db.commit()
        raise HTTPException(status_code=401, detail=LOGIN_FAILED)

    usable = user is not None and user.is_active
    valid, needs_rehash = verify_password(user.password_hash if usable else None, body.password)
    if not valid:
        if usable:
            user.failed_login_count += 1
            audit.record(db, None, "auth.login_failed", "admin", user.username, actor_username=user.username)
            if user.failed_login_count >= settings.login_max_failures:
                user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
                user.failed_login_count = 0
                audit.record(db, None, "auth.account_locked", "admin", user.username, actor_username=user.username,
                             details={"minutes": settings.login_lockout_minutes})
        else:
            # Do not store the typed username: it may be a mistyped password.
            audit.record(db, None, "auth.login_failed_unknown_user", "admin")
        db.commit()
        raise HTTPException(status_code=401, detail=LOGIN_FAILED)

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    if needs_rehash:
        user.password_hash = hash_password(body.password)
    csrf = create_session(db, user, response)
    audit.record(db, user, "auth.login", "admin", user.username)
    db.commit()
    return {"user": user_dict(user), "csrf_token": csrf}


@router.post("/logout")
def logout(response: Response, ctx: AdminContext = Depends(get_admin_allow_password_change),
           db: Session = Depends(get_db)):
    ctx.session.revoked_at = utcnow()
    audit.record(db, ctx.user, "auth.logout", "admin", ctx.user.username)
    db.commit()
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
def me(ctx: AdminContext = Depends(get_admin_allow_password_change)):
    return {"user": user_dict(ctx.user), "csrf_token": ctx.csrf_token}


@router.post("/change-password")
def change_password(body: ChangePasswordRequest, ctx: AdminContext = Depends(get_admin_allow_password_change),
                    db: Session = Depends(get_db)):
    user = ctx.user
    valid, _ = verify_password(user.password_hash, body.current_password)
    if not valid:
        raise HTTPException(status_code=400, detail="Your current password is incorrect.")
    problems = password_problems(body.new_password, user.username)
    if body.new_password == body.current_password:
        problems.append("The new password must be different from the current password.")
    if problems:
        raise HTTPException(status_code=422, detail=" ".join(problems))
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    user.password_changed_at = utcnow()
    revoke_all_sessions(db, user.id, except_session_id=ctx.session.id)
    audit.record(db, user, "auth.password_changed", "admin", user.username)
    db.commit()
    return {"ok": True, "user": user_dict(user)}
