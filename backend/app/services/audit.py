"""Admin audit logging.

Only references and status values are recorded - never complaint text,
evidence content or anything that could identify a reporter.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AdminUser, AuditLog


def record(
    db: Session,
    admin: AdminUser | None,
    action: str,
    target_type: str | None = None,
    target_ref: str | None = None,
    details: dict | None = None,
    actor_username: str | None = None,
) -> None:
    db.add(AuditLog(
        admin_id=admin.id if admin else None,
        actor_username=admin.username if admin else actor_username,
        action=action,
        target_type=target_type,
        target_ref=target_ref,
        details=details or None,
    ))
