"""Admin users, authorities, audit log, settings and maintenance."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import AUTHORITY_LEVELS, FORWARDING_CHANNELS, ROLE_ADMIN, ROLE_REVIEWER, ROLE_VIEWER, ROLES
from app.database import get_db
from app.db_types import utcnow
from app.models import AdminUser, AuditLog, Authority, Complaint
from app.schemas import AdminCreate, AdminUpdate, AuthorityIn, SettingsUpdate
from app.security.auth import AdminContext, revoke_all_sessions, require_roles
from app.security.passwords import hash_password, password_problems
from app.services import audit, maintenance
from app.services.complaints import authority_dict, iso
from app.services.evidence import find_ffmpeg

router = APIRouter(prefix="/api/admin", tags=["admin"])

READ = require_roles(ROLE_ADMIN, ROLE_REVIEWER, ROLE_VIEWER)
WRITE = require_roles(ROLE_ADMIN, ROLE_REVIEWER)
ADMIN_ONLY = require_roles(ROLE_ADMIN)


# ---------------------------------------------------------------------------
# Authorities
# ---------------------------------------------------------------------------
@router.get("/authorities")
def list_authorities(ctx: AdminContext = Depends(READ), db: Session = Depends(get_db),
                     include_inactive: bool = True):
    q = select(Authority).order_by(Authority.level, Authority.name)
    if not include_inactive:
        q = q.where(Authority.is_active.is_(True))
    return {
        "items": [authority_dict(a) for a in db.scalars(q).all()],
        "levels": [{"value": k, "label": v} for k, v in AUTHORITY_LEVELS.items()],
        "channels": [{"value": k, "label": v} for k, v in FORWARDING_CHANNELS.items()],
    }


@router.post("/authorities", status_code=201)
def create_authority(body: AuthorityIn, ctx: AdminContext = Depends(WRITE), db: Session = Depends(get_db)):
    authority = Authority(**body.model_dump())
    db.add(authority)
    db.flush()
    audit.record(db, ctx.user, "authority.created", "authority", str(authority.id))
    db.commit()
    return authority_dict(authority)


@router.put("/authorities/{authority_id}")
def update_authority(authority_id: int, body: AuthorityIn, ctx: AdminContext = Depends(WRITE),
                     db: Session = Depends(get_db)):
    authority = db.get(Authority, authority_id)
    if authority is None:
        raise HTTPException(status_code=404, detail="Authority not found.")
    for key, value in body.model_dump().items():
        setattr(authority, key, value)
    authority.updated_at = utcnow()
    audit.record(db, ctx.user, "authority.updated", "authority", str(authority.id))
    db.commit()
    return authority_dict(authority)


# ---------------------------------------------------------------------------
# Admin users (administrators only)
# ---------------------------------------------------------------------------
def _admin_dict(u: AdminUser) -> dict:
    return {
        "id": u.id, "username": u.username, "role": u.role, "role_label": ROLES[u.role],
        "is_active": u.is_active, "must_change_password": u.must_change_password,
        "locked": bool(u.locked_until and u.locked_until > utcnow()),
        "last_login_at": iso(u.last_login_at), "created_at": iso(u.created_at),
    }


def _active_admin_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(AdminUser)
                     .where(AdminUser.role == ROLE_ADMIN, AdminUser.is_active.is_(True))) or 0


@router.get("/users")
def list_users(ctx: AdminContext = Depends(ADMIN_ONLY), db: Session = Depends(get_db)):
    users = db.scalars(select(AdminUser).order_by(AdminUser.username)).all()
    return {"items": [_admin_dict(u) for u in users],
            "roles": [{"value": k, "label": v} for k, v in ROLES.items()]}


@router.post("/users", status_code=201)
def create_user(body: AdminCreate, ctx: AdminContext = Depends(ADMIN_ONLY), db: Session = Depends(get_db)):
    if db.scalar(select(AdminUser.id).where(AdminUser.username == body.username)) is not None:
        raise HTTPException(status_code=409, detail="That username is already taken.")
    problems = password_problems(body.temporary_password, body.username)
    if problems:
        raise HTTPException(status_code=422, detail=" ".join(problems))
    user = AdminUser(username=body.username, role=body.role, password_hash=hash_password(body.temporary_password),
                     must_change_password=True, is_active=True)
    db.add(user)
    db.flush()
    audit.record(db, ctx.user, "admin.created", "admin", user.username, {"role": user.role})
    db.commit()
    return _admin_dict(user)


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: AdminUpdate, ctx: AdminContext = Depends(ADMIN_ONLY),
                db: Session = Depends(get_db)):
    user = db.get(AdminUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Administrator not found.")
    changes: dict = {}
    removing_admin = (body.role is not None and body.role != ROLE_ADMIN and user.role == ROLE_ADMIN) or \
                     (body.is_active is False and user.role == ROLE_ADMIN and user.is_active)
    if removing_admin and _active_admin_count(db) <= 1:
        raise HTTPException(status_code=409, detail="At least one active administrator must remain.")
    if user.id == ctx.user.id and (body.is_active is False or (body.role and body.role != user.role)):
        raise HTTPException(status_code=409, detail="You cannot deactivate yourself or change your own role.")
    if body.role is not None and body.role != user.role:
        changes["role"] = [user.role, body.role]
        user.role = body.role
    if body.is_active is not None and body.is_active != user.is_active:
        changes["is_active"] = body.is_active
        user.is_active = body.is_active
        if not body.is_active:
            revoke_all_sessions(db, user.id)
    if body.temporary_password:
        problems = password_problems(body.temporary_password, user.username)
        if problems:
            raise HTTPException(status_code=422, detail=" ".join(problems))
        user.password_hash = hash_password(body.temporary_password)
        user.must_change_password = True
        user.failed_login_count = 0
        user.locked_until = None
        user.password_changed_at = utcnow()
        revoke_all_sessions(db, user.id)
        changes["password_reset"] = True
    audit.record(db, ctx.user, "admin.updated", "admin", user.username, changes)
    db.commit()
    return _admin_dict(user)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------
@router.get("/audit-logs")
def audit_logs(ctx: AdminContext = Depends(ADMIN_ONLY), db: Session = Depends(get_db),
               action: str | None = Query(None, max_length=64),
               target: str | None = Query(None, max_length=64),
               page: int = Query(1, ge=1, le=100000), page_size: int = Query(50, ge=1, le=200)):
    conds = []
    if action:
        conds.append(AuditLog.action.startswith(action))
    if target:
        conds.append(AuditLog.target_ref == target.strip().upper() if target.upper().startswith("GS-")
                     else AuditLog.target_ref == target.strip())
    total = db.scalar(select(func.count()).select_from(AuditLog).where(*conds)) or 0
    rows = db.scalars(select(AuditLog).where(*conds).order_by(AuditLog.id.desc())
                      .offset((page - 1) * page_size).limit(page_size)).all()
    actions = db.scalars(select(AuditLog.action).distinct().order_by(AuditLog.action)).all()
    return {
        "items": [{"id": r.id, "actor": r.actor_username, "action": r.action, "target_type": r.target_type,
                   "target_ref": r.target_ref, "details": r.details, "created_at": iso(r.created_at)} for r in rows],
        "total": total, "page": page, "page_size": page_size, "pages": max(1, -(-total // page_size)),
        "actions": actions,
    }


# ---------------------------------------------------------------------------
# Settings and maintenance
# ---------------------------------------------------------------------------
@router.get("/settings")
def get_app_settings(ctx: AdminContext = Depends(ADMIN_ONLY), db: Session = Depends(get_db)):
    s = get_settings()
    demo_complaints = db.scalar(select(func.count()).select_from(Complaint).where(Complaint.is_demo.is_(True))) or 0
    live_complaints = db.scalar(select(func.count()).select_from(Complaint).where(Complaint.is_demo.is_(False))) or 0
    return {
        "settings": maintenance.all_settings(db),
        "system": {
            "environment": s.app_env,
            "database": "SQLite (development only)" if s.is_sqlite else "PostgreSQL",
            "storage_backend": "Private object storage (S3)" if s.storage_backend == "s3" else "Private local storage",
            "evidence_encryption": "AES-256-GCM",
            "field_encryption": "AES-256-GCM (descriptions, notes, findings)",
            "malware_scanner": "ClamAV connected" if s.clamav_host else "Not configured",
            "video_metadata_removal": "Available (ffmpeg)" if find_ffmpeg() else "Not available",
            "session_idle_minutes": s.session_idle_minutes,
            "session_max_hours": s.session_max_hours,
            "secure_cookies": bool(s.cookie_secure),
            "hsts": s.hsts_enabled,
            "upload_limits": {"files": s.max_files_per_submission, "image_mb": s.max_image_mb,
                              "video_mb": s.max_video_mb, "pdf_mb": s.max_pdf_mb, "total_mb": s.max_total_upload_mb},
        },
        "data": {"live_complaints": live_complaints, "demo_complaints": demo_complaints},
    }


@router.put("/settings")
def update_app_settings(body: SettingsUpdate, ctx: AdminContext = Depends(ADMIN_ONLY), db: Session = Depends(get_db)):
    before = maintenance.all_settings(db)
    maintenance.set_setting(db, "retention_days", body.retention_days, ctx.user)
    audit.record(db, ctx.user, "settings.updated", details={"retention_days": [before["retention_days"], body.retention_days]})
    db.commit()
    return {"settings": maintenance.all_settings(db)}


@router.post("/maintenance/purge")
def run_purge(ctx: AdminContext = Depends(ADMIN_ONLY), db: Session = Depends(get_db)):
    removed = maintenance.purge_expired(db)
    audit.record(db, ctx.user, "maintenance.retention_purge", details={"removed": removed})
    db.commit()
    return {"removed": removed}


@router.post("/maintenance/seed-demo")
def seed_demo(ctx: AdminContext = Depends(ADMIN_ONLY), db: Session = Depends(get_db)):
    from app.services.demo import seed_demo_data  # noqa: PLC0415

    result = seed_demo_data(db, count=36)
    audit.record(db, ctx.user, "maintenance.demo_seeded", details={"complaints": result["complaints"]})
    db.commit()
    return {"complaints": result["complaints"], "sample_tracking": result["sample_tracking"][:3]}


@router.post("/maintenance/clear-demo")
def clear_demo(ctx: AdminContext = Depends(ADMIN_ONLY), db: Session = Depends(get_db)):
    complaints, authorities = maintenance.clear_demo_data(db)
    audit.record(db, ctx.user, "maintenance.demo_cleared", details={"complaints": complaints, "authorities": authorities})
    db.commit()
    return {"complaints": complaints, "authorities": authorities}
