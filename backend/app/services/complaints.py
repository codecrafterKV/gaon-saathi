"""Complaint creation, lookup, workflow and serialisation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import (
    AUTHORITY_LEVELS,
    CATEGORIES,
    DEFAULT_PUBLIC_MESSAGES,
    FORWARDED,
    FORWARDING_CHANNELS,
    NOTE_KINDS,
    PUBLIC_PROGRESS_STEPS,
    RECEIVED,
    RESOLVED,
    STATUS_TRANSITIONS,
    STATUSES,
    TERMINAL_STATUSES,
    VERIFICATION_STATUSES,
)
from app.db_types import utcnow
from app.models import (
    AdminUser,
    Authority,
    Complaint,
    ComplaintForwarding,
    ComplaintNote,
    ComplaintStatusHistory,
    EvidenceFile,
)
from app.schemas import ComplaintCreate, ForwardingCreate, InfoRequest, VerificationUpdate
from app.security.crypto import constant_time_equals, get_keyring, hash_tracking_token
from app.services import audit
from app.services.evidence import ProcessedFile
from app.services.identifiers import new_public_id, new_tracking_token, normalise_public_id, normalise_token
from app.services.storage import get_storage, new_storage_key

IST = timezone(timedelta(hours=5, minutes=30), name="IST")


class WorkflowError(Exception):
    """An admin action that is not allowed in the complaint's current state."""


def ist_date(value: datetime | None) -> str | None:
    return value.astimezone(IST).date().isoformat() if value else None


def iso(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat() if value else None


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------
def _unique_public_id(db: Session, demo: bool) -> str:
    for _ in range(10):
        candidate = new_public_id(demo=demo)
        if db.scalar(select(Complaint.id).where(Complaint.public_id == candidate)) is None:
            return candidate
    raise RuntimeError("Could not generate a unique complaint ID")  # practically impossible


def attach_evidence(complaint: Complaint, processed: ProcessedFile, index: int, source: str) -> str:
    """Encrypt and store a processed file; returns the storage key."""
    key = new_storage_key()
    get_storage().put(key, get_keyring().encrypt_blob(processed.data, aad=key))
    complaint.evidence.append(EvidenceFile(
        storage_key=key,
        display_name=f"evidence-{index}.{processed.extension}",
        media_kind=processed.media_kind,
        mime_type=processed.mime_type,
        size_bytes=len(processed.data),
        sha256=processed.sha256,
        metadata_stripped=processed.metadata_stripped,
        scan_status=processed.scan_status,
        source=source,
    ))
    return key


def create_complaint(
    db: Session,
    data: ComplaintCreate,
    files: list[ProcessedFile],
    *,
    is_demo: bool = False,
    submitted_at: datetime | None = None,
) -> tuple[Complaint, str]:
    """Persist a new complaint. Returns (complaint, display tracking token)."""
    now = submitted_at or utcnow()
    token = new_tracking_token()
    complaint = Complaint(
        public_id=_unique_public_id(db, is_demo),
        tracking_token_hash=hash_tracking_token(normalise_token(token)),
        category=data.category,
        village=data.village,
        district=data.district,
        state=data.state,
        description=data.description,
        approximate_location=data.approximate_location,
        status=RECEIVED,
        is_demo=is_demo,
        submitted_at=now,
        updated_at=now,
    )
    complaint.history.append(ComplaintStatusHistory(
        from_status=None, to_status=RECEIVED,
        internal_note="Complaint submitted through the public form.", changed_at=now,
    ))
    stored: list[str] = []
    try:
        for index, processed in enumerate(files, start=1):
            stored.append(attach_evidence(complaint, processed, index, "demo" if is_demo else "initial"))
        db.add(complaint)
        db.commit()
    except Exception:
        db.rollback()
        for key in stored:
            get_storage().delete(key)
        raise
    return complaint, token


# ---------------------------------------------------------------------------
# Public tracking
# ---------------------------------------------------------------------------
def find_for_tracking(db: Session, public_id: str, token: str) -> Complaint | None:
    pid = normalise_public_id(public_id)
    tok = normalise_token(token)
    complaint = db.scalar(select(Complaint).where(Complaint.public_id == pid)) if pid else None
    expected = complaint.tracking_token_hash if complaint else "0" * 64
    supplied = hash_tracking_token(tok or "invalid-token")  # always compute: similar timing
    if complaint is None or tok is None or not constant_time_equals(supplied, expected):
        return None
    return complaint


def public_view(complaint: Complaint) -> dict:
    """The ONLY complaint data ever shown publicly. No description, evidence or notes."""
    timeline = []
    for entry in complaint.history:
        timeline.append({
            "status": entry.to_status,
            "label": STATUSES[entry.to_status],
            "date": ist_date(entry.changed_at),
            "message": entry.public_message,
        })
    return {
        "complaint_id": complaint.public_id,
        "category": complaint.category,
        "category_label": CATEGORIES[complaint.category],
        "submitted_on": ist_date(complaint.submitted_at),
        "status": complaint.status,
        "status_label": STATUSES[complaint.status],
        "last_updated": ist_date(complaint.updated_at),
        "progress_message": complaint.public_message or DEFAULT_PUBLIC_MESSAGES[complaint.status],
        "info_requested": complaint.info_requested,
        "can_add_information": complaint.status not in TERMINAL_STATUSES,
        "progress_steps": [{"status": s, "label": STATUSES[s]} for s in PUBLIC_PROGRESS_STEPS],
        "timeline": timeline,
        "is_demo": complaint.is_demo,
    }


def add_reporter_update(db: Session, complaint: Complaint, message: str | None, files: list[ProcessedFile]) -> None:
    if complaint.status in TERMINAL_STATUSES:
        raise WorkflowError("This complaint is closed and cannot receive new information.")
    stored: list[str] = []
    start = len(complaint.evidence) + 1
    try:
        for offset, processed in enumerate(files):
            stored.append(attach_evidence(complaint, processed, start + offset, "supplement"))
        summary = message or ""
        if files:
            summary = (summary + "\n\n" if summary else "") + f"[{len(files)} new evidence file(s) attached]"
        complaint.notes.append(ComplaintNote(kind="reporter_update", body=summary, author_id=None))
        complaint.info_requested = False
        complaint.has_unread_update = True
        complaint.updated_at = utcnow()
        db.commit()
    except Exception:
        db.rollback()
        for key in stored:
            get_storage().delete(key)
        raise


# ---------------------------------------------------------------------------
# Admin workflow
# ---------------------------------------------------------------------------
def change_status(
    db: Session,
    complaint: Complaint,
    admin: AdminUser,
    to_status: str,
    internal_note: str,
    public_message: str | None = None,
    resolution_summary: str | None = None,
    *,
    via_forwarding: bool = False,
) -> None:
    current = complaint.status
    if to_status == current:
        raise WorkflowError(f"The complaint is already '{STATUSES[current]}'.")
    if to_status not in STATUS_TRANSITIONS[current]:
        raise WorkflowError(f"A complaint cannot move from '{STATUSES[current]}' to '{STATUSES[to_status]}'.")
    if to_status == FORWARDED and not via_forwarding and not complaint.forwardings:
        raise WorkflowError("Record the forwarding details (authority, date and acknowledgement) first. "
                            "Use 'Record forwarding' to mark a complaint as forwarded.")
    if to_status == RESOLVED and (not resolution_summary or len(resolution_summary.strip()) < 20):
        raise WorkflowError("A resolution summary is required before marking a complaint as Resolved.")

    now = utcnow()
    complaint.history.append(ComplaintStatusHistory(
        from_status=current, to_status=to_status, internal_note=internal_note,
        public_message=public_message, changed_by_id=admin.id, changed_at=now,
    ))
    complaint.status = to_status
    complaint.public_message = public_message
    complaint.updated_at = now
    if to_status == RESOLVED:
        complaint.resolution_summary = resolution_summary
    if to_status in TERMINAL_STATUSES:
        complaint.closed_at = now
        complaint.info_requested = False
    else:
        complaint.closed_at = None
    audit.record(db, admin, "complaint.status_changed", "complaint", complaint.public_id,
                 {"from": current, "to": to_status})


def add_note(db: Session, complaint: Complaint, admin: AdminUser, kind: str, body: str) -> ComplaintNote:
    note = ComplaintNote(kind=kind, body=body, author_id=admin.id)
    complaint.notes.append(note)
    complaint.updated_at = utcnow() if kind == "follow_up" else complaint.updated_at
    audit.record(db, admin, "complaint.note_added", "complaint", complaint.public_id, {"kind": kind})
    return note


def request_information(db: Session, complaint: Complaint, admin: AdminUser, data: InfoRequest) -> None:
    if complaint.status in TERMINAL_STATUSES:
        raise WorkflowError("Re-open the complaint before requesting more information.")
    complaint.info_requested = True
    complaint.verification_status = "needs_more_info"
    complaint.public_message = data.public_message
    complaint.updated_at = utcnow()
    complaint.notes.append(ComplaintNote(
        kind="evidence_request", author_id=admin.id,
        body=f"{data.internal_note}\n\nMessage shown to reporter: {data.public_message}",
    ))
    audit.record(db, admin, "complaint.info_requested", "complaint", complaint.public_id)


def update_verification(db: Session, complaint: Complaint, admin: AdminUser, data: VerificationUpdate) -> None:
    if data.authority_id is not None and db.get(Authority, data.authority_id) is None:
        raise WorkflowError("The selected authority does not exist.")
    previous = complaint.verification_status
    complaint.verification_status = data.verification_status
    if data.findings:
        complaint.verification_findings = data.findings
    complaint.authority_id = data.authority_id
    if data.verification_status != "needs_more_info":
        complaint.info_requested = False
    body = f"Verification: {VERIFICATION_STATUSES[data.verification_status]}."
    if data.findings:
        body += f"\n{data.findings}"
    complaint.notes.append(ComplaintNote(kind="verification", body=body, author_id=admin.id))
    audit.record(db, admin, "complaint.verification_updated", "complaint", complaint.public_id,
                 {"from": previous, "to": data.verification_status, "authority_id": data.authority_id})


def record_forwarding(db: Session, complaint: Complaint, admin: AdminUser, data: ForwardingCreate) -> None:
    authority = None
    if data.authority_id is not None:
        authority = db.get(Authority, data.authority_id)
        if authority is None:
            raise WorkflowError("The selected authority does not exist.")
    if complaint.status != FORWARDED and FORWARDED not in STATUS_TRANSITIONS[complaint.status]:
        raise WorkflowError(f"A complaint in '{STATUSES[complaint.status]}' cannot be forwarded. "
                            "Review it first (Under Review or Action in Progress).")
    complaint.forwardings.append(ComplaintForwarding(
        authority_id=authority.id if authority else None,
        authority_name=data.authority_name or authority.name,
        channel=data.channel,
        submitted_on=data.submitted_on,
        reference_number=data.reference_number,
        acknowledgement_details=data.acknowledgement_details,
        created_by_id=admin.id,
    ))
    if authority is not None:
        complaint.authority_id = authority.id
    audit.record(db, admin, "complaint.forwarding_recorded", "complaint", complaint.public_id,
                 {"channel": data.channel, "authority_id": data.authority_id})
    if complaint.status == FORWARDED:
        complaint.notes.append(ComplaintNote(kind="follow_up", author_id=admin.id,
                                             body=f"Also forwarded to {data.authority_name or authority.name}. {data.internal_note}"))
        complaint.updated_at = utcnow()
    else:
        change_status(db, complaint, admin, FORWARDED, data.internal_note, data.public_message, via_forwarding=True)


# ---------------------------------------------------------------------------
# Admin serialisation
# ---------------------------------------------------------------------------
def _who(user: AdminUser | None) -> str | None:
    return user.username if user else None


def authority_dict(a: Authority) -> dict:
    return {
        "id": a.id, "name": a.name, "department": a.department, "level": a.level,
        "level_label": AUTHORITY_LEVELS.get(a.level, a.level), "state": a.state, "district": a.district,
        "grievance_channel": a.grievance_channel, "website": a.website, "office_contact": a.office_contact,
        "notes": a.notes, "is_active": a.is_active, "is_demo": a.is_demo,
        "updated_at": iso(a.updated_at),
    }


def evidence_dict(e: EvidenceFile) -> dict:
    return {
        "id": str(e.id), "display_name": e.display_name, "media_kind": e.media_kind,
        "mime_type": e.mime_type, "size_bytes": e.size_bytes, "sha256": e.sha256,
        "metadata_stripped": e.metadata_stripped, "scan_status": e.scan_status,
        "source": e.source, "created_at": iso(e.created_at),
    }


def list_item(c: Complaint, has_evidence: bool) -> dict:
    return {
        "complaint_id": c.public_id,
        "category": c.category,
        "category_label": CATEGORIES[c.category],
        "village": c.village,
        "district": c.district,
        "state": c.state,
        "submitted_at": iso(c.submitted_at),
        "status": c.status,
        "status_label": STATUSES[c.status],
        "verification_status": c.verification_status,
        "has_evidence": has_evidence,
        "has_unread_update": c.has_unread_update,
        "info_requested": c.info_requested,
        "is_demo": c.is_demo,
    }


def detail(c: Complaint, can_view_evidence: bool) -> dict:
    return {
        **list_item(c, bool(c.evidence)),
        "description": c.description,
        "approximate_location": c.approximate_location,
        "public_message": c.public_message,
        "public_message_effective": c.public_message or DEFAULT_PUBLIC_MESSAGES[c.status],
        "verification_status_label": VERIFICATION_STATUSES[c.verification_status],
        "verification_findings": c.verification_findings,
        "resolution_summary": c.resolution_summary,
        "authority": authority_dict(c.authority) if c.authority else None,
        "updated_at": iso(c.updated_at),
        "closed_at": iso(c.closed_at),
        "allowed_transitions": [
            {"status": s, "label": STATUSES[s], "requires_forwarding_record": s == FORWARDED and not c.forwardings}
            for s in STATUSES if s in STATUS_TRANSITIONS[c.status]
        ],
        "evidence": [evidence_dict(e) for e in c.evidence] if can_view_evidence else [],
        "evidence_count": len(c.evidence),
        "history": [{
            "id": h.id, "from_status": h.from_status, "to_status": h.to_status,
            "to_label": STATUSES[h.to_status], "internal_note": h.internal_note,
            "public_message": h.public_message, "changed_by": _who(h.changed_by),
            "changed_at": iso(h.changed_at),
        } for h in c.history],
        "notes": [{
            "id": n.id, "kind": n.kind, "kind_label": NOTE_KINDS[n.kind], "body": n.body,
            "author": _who(n.author) if n.kind != "reporter_update" else "Reporter (anonymous)",
            "created_at": iso(n.created_at),
        } for n in c.notes],
        "forwardings": [{
            "id": f.id, "authority_id": f.authority_id, "authority_name": f.authority_name,
            "channel": f.channel, "channel_label": FORWARDING_CHANNELS[f.channel],
            "submitted_on": f.submitted_on.isoformat(), "reference_number": f.reference_number,
            "acknowledgement_details": f.acknowledgement_details, "recorded_by": _who(f.created_by),
            "created_at": iso(f.created_at),
        } for f in c.forwardings],
    }
