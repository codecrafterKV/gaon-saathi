"""Settings, deletion and data-retention helpers."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import TERMINAL_STATUSES
from app.db_types import utcnow
from app.models import AdminUser, AppSetting, Authority, Complaint
from app.services.storage import get_storage

DEFAULT_SETTINGS = {
    "retention_days": 365,
}


def get_setting(db: Session, key: str):
    row = db.get(AppSetting, key)
    return row.value if row is not None else DEFAULT_SETTINGS.get(key)


def set_setting(db: Session, key: str, value, admin: AdminUser | None) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        row = AppSetting(key=key)
        db.add(row)
    row.value = value
    row.updated_at = utcnow()
    row.updated_by_id = admin.id if admin else None


def all_settings(db: Session) -> dict:
    return {key: get_setting(db, key) for key in DEFAULT_SETTINGS}


def delete_complaints(db: Session, complaints: list[Complaint]) -> int:
    """Delete complaints (cascade: history, notes, forwardings, evidence rows) and their files.

    Files are removed after the database commit so that a failed commit never
    leaves database rows pointing at missing files.
    """
    keys = [e.storage_key for c in complaints for e in c.evidence]
    for complaint in complaints:
        db.delete(complaint)
    db.commit()
    storage = get_storage()
    for key in keys:
        storage.delete(key)
    return len(complaints)


def purge_expired(db: Session) -> int:
    """Delete finished complaints older than the retention period."""
    days = int(get_setting(db, "retention_days"))
    cutoff = utcnow() - timedelta(days=days)
    expired = db.scalars(
        select(Complaint).where(Complaint.status.in_(TERMINAL_STATUSES), Complaint.closed_at < cutoff)
    ).unique().all()
    return delete_complaints(db, list(expired))


def clear_demo_data(db: Session) -> tuple[int, int]:
    demo = db.scalars(select(Complaint).where(Complaint.is_demo.is_(True))).unique().all()
    removed = delete_complaints(db, list(demo))
    authorities = db.scalars(select(Authority).where(Authority.is_demo.is_(True))).all()
    for authority in authorities:
        db.delete(authority)
    db.commit()
    return removed, len(authorities)
