"""Database models.

Privacy by design: there is deliberately NO table for reporters/users. A
complaint row stores only the problem (category, problem location and
description) - never who reported it, their IP address or their device.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.constants import (
    AUTHORITY_LEVELS,
    CATEGORIES,
    FORWARDING_CHANNELS,
    MEDIA_KINDS,
    NOTE_KINDS,
    ROLES,
    SCAN_STATUSES,
    STATUSES,
    VERIFICATION_STATUSES,
    sql_in_list,
)
from app.db_types import EncryptedText, UTCDateTime, utcnow


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Complaints
# ---------------------------------------------------------------------------
class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    public_id: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    tracking_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    category: Mapped[str] = mapped_column(String(40), nullable=False)
    village: Mapped[str] = mapped_column(String(120), nullable=False)
    district: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(EncryptedText, nullable=False)
    approximate_location: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="received")
    public_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    verification_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    verification_findings: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    authority_id: Mapped[int | None] = mapped_column(
        ForeignKey("authorities.id", ondelete="SET NULL"), nullable=True
    )
    resolution_summary: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)

    info_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_unread_update: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    submitted_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    authority: Mapped["Authority | None"] = relationship(lazy="joined")
    evidence: Mapped[list["EvidenceFile"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan", order_by="EvidenceFile.created_at"
    )
    history: Mapped[list["ComplaintStatusHistory"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan", order_by="ComplaintStatusHistory.id"
    )
    notes: Mapped[list["ComplaintNote"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan", order_by="ComplaintNote.id"
    )
    forwardings: Mapped[list["ComplaintForwarding"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan", order_by="ComplaintForwarding.id"
    )

    __table_args__ = (
        CheckConstraint(f"category IN ({sql_in_list(CATEGORIES)})", name="ck_complaints_category"),
        CheckConstraint(f"status IN ({sql_in_list(STATUSES)})", name="ck_complaints_status"),
        CheckConstraint(
            f"verification_status IN ({sql_in_list(VERIFICATION_STATUSES)})",
            name="ck_complaints_verification_status",
        ),
        CheckConstraint("length(village) > 0 AND length(district) > 0 AND length(state) > 0",
                        name="ck_complaints_location_present"),
        Index("ix_complaints_status", "status"),
        Index("ix_complaints_category", "category"),
        Index("ix_complaints_submitted_at", "submitted_at"),
        Index("ix_complaints_district_village", "district", "village"),
        Index("ix_complaints_is_demo", "is_demo"),
    )


class ComplaintStatusHistory(Base):
    __tablename__ = "complaint_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complaint_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    internal_note: Mapped[str] = mapped_column(EncryptedText, nullable=False)
    public_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    changed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    complaint: Mapped[Complaint] = relationship(back_populates="history")
    changed_by: Mapped["AdminUser | None"] = relationship(lazy="joined")

    __table_args__ = (
        CheckConstraint(f"to_status IN ({sql_in_list(STATUSES)})", name="ck_history_to_status"),
    )


class ComplaintNote(Base):
    __tablename__ = "complaint_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complaint_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    body: Mapped[str] = mapped_column(EncryptedText, nullable=False)
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    complaint: Mapped[Complaint] = relationship(back_populates="notes")
    author: Mapped["AdminUser | None"] = relationship(lazy="joined")

    __table_args__ = (CheckConstraint(f"kind IN ({sql_in_list(NOTE_KINDS)})", name="ck_notes_kind"),)


class ComplaintForwarding(Base):
    """A record that the team actually submitted the complaint to an authority."""

    __tablename__ = "complaint_forwardings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complaint_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    authority_id: Mapped[int | None] = mapped_column(
        ForeignKey("authorities.id", ondelete="SET NULL"), nullable=True
    )
    authority_name: Mapped[str] = mapped_column(String(200), nullable=False)
    channel: Mapped[str] = mapped_column(String(24), nullable=False)
    submitted_on: Mapped[date] = mapped_column(Date, nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    acknowledgement_details: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    complaint: Mapped[Complaint] = relationship(back_populates="forwardings")
    created_by: Mapped["AdminUser | None"] = relationship(lazy="joined")

    __table_args__ = (
        CheckConstraint(f"channel IN ({sql_in_list(FORWARDING_CHANNELS)})", name="ck_forwardings_channel"),
    )


class EvidenceFile(Base):
    """Metadata for an encrypted evidence file held in private storage.

    The original file name is intentionally NOT stored, because phone file
    names can contain personal names, phone numbers or device identifiers.
    """

    __tablename__ = "evidence_files"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    complaint_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    media_kind: Mapped[str] = mapped_column(String(8), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_stripped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scan_status: Mapped[str] = mapped_column(String(16), nullable=False, default="not_scanned")
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="initial")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    complaint: Mapped[Complaint] = relationship(back_populates="evidence")

    __table_args__ = (
        CheckConstraint(f"media_kind IN ({sql_in_list(MEDIA_KINDS)})", name="ck_evidence_media_kind"),
        CheckConstraint(f"scan_status IN ({sql_in_list(SCAN_STATUSES)})", name="ck_evidence_scan_status"),
        CheckConstraint("source IN ('initial', 'supplement', 'demo')", name="ck_evidence_source"),
        CheckConstraint("size_bytes > 0", name="ck_evidence_size_positive"),
    )


# ---------------------------------------------------------------------------
# Authorities / departments
# ---------------------------------------------------------------------------
class Authority(Base):
    __tablename__ = "authorities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    department: Mapped[str | None] = mapped_column(String(200), nullable=True)
    level: Mapped[str] = mapped_column(String(24), nullable=False, default="district")
    state: Mapped[str | None] = mapped_column(String(80), nullable=True)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True)
    grievance_channel: Mapped[str | None] = mapped_column(String(200), nullable=True)
    website: Mapped[str | None] = mapped_column(String(300), nullable=True)
    office_contact: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint(f"level IN ({sql_in_list(AUTHORITY_LEVELS)})", name="ck_authorities_level"),
    )


# ---------------------------------------------------------------------------
# Administrators
# ---------------------------------------------------------------------------
class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    password_changed_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)

    __table_args__ = (CheckConstraint(f"role IN ({sql_in_list(ROLES)})", name="ck_admin_users_role"),)


class AdminSession(Base):
    """Server-side admin session. Only an HMAC of the session token is stored."""

    __tablename__ = "admin_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    admin_id: Mapped[int] = mapped_column(
        ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    admin: Mapped[AdminUser] = relationship(lazy="joined")


class AuditLog(Base):
    """Append-only record of important administrator actions.

    ``details`` must never contain complaint descriptions, evidence content or
    any reporter-identifying data - only references and status values.
    """

    __tablename__ = "admin_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_username: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_ref: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow, index=True)


# ---------------------------------------------------------------------------
# Settings and anti-spam bookkeeping
# ---------------------------------------------------------------------------
class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict | list | str | int | bool | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )


class SpentChallenge(Base):
    """Anti-spam challenges that were already used (prevents replay)."""

    __tablename__ = "spent_challenges"

    nonce: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
