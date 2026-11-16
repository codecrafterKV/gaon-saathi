"""Admin complaint management, evidence access, statistics and exports."""

from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import date, datetime, time, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from app.constants import (
    CATEGORIES,
    ROLE_ADMIN,
    ROLE_REVIEWER,
    ROLE_VIEWER,
    STATUSES,
    VERIFICATION_STATUSES,
)
from app.database import get_db
from app.models import Complaint, EvidenceFile
from app.schemas import ForwardingCreate, InfoRequest, NoteCreate, StatusUpdate, VerificationUpdate, clean_line
from app.security.auth import AdminContext, require_roles
from app.security.crypto import DecryptionError, get_keyring
from app.services import audit, stats
from app.services import complaints as svc
from app.services.complaints import IST, WorkflowError
from app.services.identifiers import normalise_public_id
from app.services.maintenance import delete_complaints
from app.services.storage import StorageError, get_storage

router = APIRouter(prefix="/api/admin", tags=["admin"])

READ = require_roles(ROLE_ADMIN, ROLE_REVIEWER, ROLE_VIEWER)
WRITE = require_roles(ROLE_ADMIN, ROLE_REVIEWER)
ADMIN_ONLY = require_roles(ROLE_ADMIN)

Dataset = Literal["live", "demo", "all"]


def _get_complaint(db: Session, public_id: str) -> Complaint:
    pid = normalise_public_id(public_id)
    complaint = db.scalar(select(Complaint).where(Complaint.public_id == pid)) if pid else None
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return complaint


def _like(term: str) -> str:
    return "%" + re.sub(r"([\\%_])", r"\\\1", term) + "%"


# ---------------------------------------------------------------------------
# Listing and filters
# ---------------------------------------------------------------------------
def _list_conditions(dataset, search, category, status, state, district, village, verification,
                     date_from, date_to, has_evidence):
    conds = stats.dataset_conditions(dataset)
    if search:
        term = _like(clean_line(search) or "")
        conds.append(or_(Complaint.public_id.ilike(term, escape="\\"),
                         Complaint.village.ilike(term, escape="\\"),
                         Complaint.district.ilike(term, escape="\\")))
    if category:
        conds.append(Complaint.category == category)
    if status:
        if status == "open":
            conds.append(Complaint.status.not_in(["resolved", "rejected", "closed"]))
        else:
            conds.append(Complaint.status == status)
    if state:
        conds.append(Complaint.state == state)
    if district:
        conds.append(Complaint.district == district)
    if village:
        conds.append(Complaint.village == village)
    if verification:
        conds.append(Complaint.verification_status == verification)
    if date_from:
        conds.append(Complaint.submitted_at >= datetime.combine(date_from, time.min, tzinfo=IST))
    if date_to:
        conds.append(Complaint.submitted_at < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=IST))
    has_ev = exists().where(EvidenceFile.complaint_id == Complaint.id)
    if has_evidence is not None:
        conds.append(has_ev if has_evidence else ~has_ev)
    return conds, has_ev


_SORTS = {
    "newest": [Complaint.submitted_at.desc()],
    "oldest": [Complaint.submitted_at.asc()],
    "status": [Complaint.status.asc(), Complaint.submitted_at.desc()],
    "category": [Complaint.category.asc(), Complaint.submitted_at.desc()],
    "village": [Complaint.village.asc(), Complaint.submitted_at.desc()],
    "updated": [Complaint.updated_at.desc()],
}


@router.get("/complaints")
def list_complaints(
    ctx: AdminContext = Depends(READ),
    db: Session = Depends(get_db),
    dataset: Dataset = "all",
    search: str | None = Query(None, max_length=100),
    category: str | None = Query(None, max_length=40),
    status: str | None = Query(None, max_length=32),
    state: str | None = Query(None, max_length=80),
    district: str | None = Query(None, max_length=120),
    village: str | None = Query(None, max_length=120),
    verification: str | None = Query(None, max_length=24),
    date_from: date | None = None,
    date_to: date | None = None,
    has_evidence: bool | None = None,
    sort: Literal["newest", "oldest", "status", "category", "village", "updated"] = "newest",
    page: int = Query(1, ge=1, le=100000),
    page_size: int = Query(20, ge=1, le=100),
):
    conds, has_ev = _list_conditions(dataset, search, category, status, state, district, village,
                                     verification, date_from, date_to, has_evidence)
    total = db.scalar(select(func.count()).select_from(Complaint).where(*conds)) or 0
    rows = db.execute(
        select(Complaint, has_ev.label("has_evidence")).where(*conds)
        .order_by(*_SORTS[sort]).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [svc.list_item(c, bool(ev)) for c, ev in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, -(-total // page_size)),
    }


@router.get("/complaints/filters")
def complaint_filters(ctx: AdminContext = Depends(READ), db: Session = Depends(get_db), dataset: Dataset = "all"):
    cond = stats.dataset_conditions(dataset)
    districts = db.execute(select(Complaint.district, Complaint.state).where(*cond).distinct()
                           .order_by(Complaint.district)).all()
    villages = db.execute(select(Complaint.village, Complaint.district).where(*cond).distinct()
                          .order_by(Complaint.village)).all()
    states = db.scalars(select(Complaint.state).where(*cond).distinct().order_by(Complaint.state)).all()
    return {
        "categories": [{"value": k, "label": v} for k, v in CATEGORIES.items()],
        "statuses": [{"value": k, "label": v} for k, v in STATUSES.items()],
        "verification_statuses": [{"value": k, "label": v} for k, v in VERIFICATION_STATUSES.items()],
        "states": states,
        "districts": [{"district": d, "state": s} for d, s in districts],
        "villages": [{"village": v, "district": d} for v, d in villages],
    }


# ---------------------------------------------------------------------------
# Details and workflow
# ---------------------------------------------------------------------------
def _can_view_evidence(ctx: AdminContext) -> bool:
    return ctx.user.role in (ROLE_ADMIN, ROLE_REVIEWER)


@router.get("/complaints/{public_id}")
def complaint_detail(public_id: str, ctx: AdminContext = Depends(READ), db: Session = Depends(get_db)):
    complaint = _get_complaint(db, public_id)
    if complaint.has_unread_update and ctx.user.role in (ROLE_ADMIN, ROLE_REVIEWER):
        complaint.has_unread_update = False
    audit.record(db, ctx.user, "complaint.viewed", "complaint", complaint.public_id)
    db.commit()
    return svc.detail(complaint, _can_view_evidence(ctx))


def _commit_or_400(db: Session, action) -> None:
    try:
        action()
        db.commit()
    except WorkflowError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/complaints/{public_id}/status")
def update_status(public_id: str, body: StatusUpdate, ctx: AdminContext = Depends(WRITE),
                  db: Session = Depends(get_db)):
    complaint = _get_complaint(db, public_id)
    _commit_or_400(db, lambda: svc.change_status(db, complaint, ctx.user, body.to_status, body.internal_note,
                                                 body.public_message, body.resolution_summary))
    return svc.detail(complaint, _can_view_evidence(ctx))


@router.post("/complaints/{public_id}/notes", status_code=201)
def add_note(public_id: str, body: NoteCreate, ctx: AdminContext = Depends(WRITE), db: Session = Depends(get_db)):
    complaint = _get_complaint(db, public_id)
    _commit_or_400(db, lambda: svc.add_note(db, complaint, ctx.user, body.kind, body.body))
    return svc.detail(complaint, _can_view_evidence(ctx))


@router.post("/complaints/{public_id}/request-info")
def request_info(public_id: str, body: InfoRequest, ctx: AdminContext = Depends(WRITE),
                 db: Session = Depends(get_db)):
    complaint = _get_complaint(db, public_id)
    _commit_or_400(db, lambda: svc.request_information(db, complaint, ctx.user, body))
    return svc.detail(complaint, _can_view_evidence(ctx))


@router.put("/complaints/{public_id}/verification")
def update_verification(public_id: str, body: VerificationUpdate, ctx: AdminContext = Depends(WRITE),
                        db: Session = Depends(get_db)):
    complaint = _get_complaint(db, public_id)
    _commit_or_400(db, lambda: svc.update_verification(db, complaint, ctx.user, body))
    return svc.detail(complaint, _can_view_evidence(ctx))


@router.post("/complaints/{public_id}/forwardings", status_code=201)
def record_forwarding(public_id: str, body: ForwardingCreate, ctx: AdminContext = Depends(WRITE),
                      db: Session = Depends(get_db)):
    complaint = _get_complaint(db, public_id)
    _commit_or_400(db, lambda: svc.record_forwarding(db, complaint, ctx.user, body))
    return svc.detail(complaint, _can_view_evidence(ctx))


class DeleteRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=500)
    confirm_id: str = Field(max_length=40)


@router.post("/complaints/{public_id}/delete")
def delete_complaint(public_id: str, body: DeleteRequest, ctx: AdminContext = Depends(ADMIN_ONLY),
                     db: Session = Depends(get_db)):
    complaint = _get_complaint(db, public_id)
    if normalise_public_id(body.confirm_id) != complaint.public_id:
        raise HTTPException(status_code=400, detail="Type the complaint ID exactly to confirm deletion.")
    ref, was_demo = complaint.public_id, complaint.is_demo
    audit.record(db, ctx.user, "complaint.deleted", "complaint", ref,
                 {"reason": clean_line(body.reason), "demo": was_demo})
    delete_complaints(db, [complaint])
    return {"ok": True}


# ---------------------------------------------------------------------------
# Evidence (authenticated, never public)
# ---------------------------------------------------------------------------
_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


@router.get("/evidence/{evidence_id}")
def get_evidence(evidence_id: str, request: Request, download: bool = False,
                 ctx: AdminContext = Depends(WRITE), db: Session = Depends(get_db)):
    try:
        ev_uuid = uuid.UUID(evidence_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Evidence not found.") from exc
    evidence = db.get(EvidenceFile, ev_uuid)
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence not found.")
    try:
        data = get_keyring().decrypt_blob(get_storage().get(evidence.storage_key), aad=evidence.storage_key)
    except (StorageError, DecryptionError) as exc:
        raise HTTPException(status_code=410, detail="This evidence file is no longer available.") from exc

    range_header = request.headers.get("range")
    if not range_header or range_header.startswith("bytes=0-"):
        audit.record(db, ctx.user, "evidence.viewed", "complaint", evidence.complaint.public_id,
                     {"evidence": evidence.display_name, "download": download})
        db.commit()

    inline = evidence.media_kind in ("image", "video") and not download
    headers = {
        "Content-Disposition": f'{"inline" if inline else "attachment"}; filename="{evidence.display_name}"',
        "Cache-Control": "private, no-store",
        "Content-Security-Policy": "default-src 'none'; img-src 'self'; media-src 'self'; style-src 'unsafe-inline'; sandbox",
        "Accept-Ranges": "bytes",
        "X-Content-Type-Options": "nosniff",
    }
    total = len(data)
    match = _RANGE_RE.match(range_header or "")
    if match and (match.group(1) or match.group(2)):
        if match.group(1):
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else total - 1
        else:
            start = max(0, total - int(match.group(2)))
            end = total - 1
        end = min(end, total - 1)
        if start > end or start >= total:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{total}"})
        headers["Content-Range"] = f"bytes {start}-{end}/{total}"
        return Response(content=data[start:end + 1], status_code=206, media_type=evidence.mime_type, headers=headers)
    return Response(content=data, media_type=evidence.mime_type, headers=headers)


# ---------------------------------------------------------------------------
# Statistics and CSV export
# ---------------------------------------------------------------------------
@router.get("/stats")
def get_stats(ctx: AdminContext = Depends(READ), db: Session = Depends(get_db), dataset: Dataset = "all"):
    return stats.compute(db, dataset)


def _csv_safe(value) -> str:
    """Prevent spreadsheet formula injection (CSV injection)."""
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def _csv_response(rows: list[list], filename: str) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for row in rows:
        writer.writerow([_csv_safe(v) for v in row])
    return Response(
        content="﻿" + buffer.getvalue(),  # BOM so Excel opens UTF-8 correctly
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/statistics.csv")
def export_statistics(ctx: AdminContext = Depends(WRITE), db: Session = Depends(get_db), dataset: Dataset = "all"):
    data = stats.compute(db, dataset)
    rows: list[list] = [["section", "item", "count"]]
    rows.append(["summary", "total_complaints", data["total"]])
    rows.append(["summary", "complaints_with_evidence", data["with_evidence"]])
    rows.append(["summary", "distinct_villages", data["distinct_villages"]])
    rows += [["status", r["label"], r["count"]] for r in data["by_status"]]
    rows += [["category", r["label"], r["count"]] for r in data["by_category"]]
    rows += [["verification", r["label"], r["count"]] for r in data["by_verification"]]
    rows += [["district", f'{r["district"]} ({r["state"]})', r["count"]] for r in data["top_districts"]]
    rows += [["village", f'{r["village"]}, {r["district"]} ({r["state"]})', r["count"]] for r in data["top_villages"]]
    rows += [["month", r["month"], r["count"]] for r in data["monthly"]]
    audit.record(db, ctx.user, "export.statistics_csv", details={"dataset": dataset})
    db.commit()
    return _csv_response(rows, f"gaon-saathi-statistics-{dataset}-{date.today().isoformat()}.csv")


@router.get("/export/complaints.csv")
def export_complaints(ctx: AdminContext = Depends(WRITE), db: Session = Depends(get_db), dataset: Dataset = "all"):
    """Complaint register WITHOUT descriptions, notes or evidence."""
    has_ev = exists().where(EvidenceFile.complaint_id == Complaint.id)
    result = db.execute(
        select(Complaint, has_ev).where(*stats.dataset_conditions(dataset)).order_by(Complaint.submitted_at.desc())
    ).all()
    rows: list[list] = [["complaint_id", "category", "village", "district", "state", "submitted_on",
                         "status", "verification", "evidence_available", "last_updated", "demo_data"]]
    for c, ev in result:
        rows.append([c.public_id, CATEGORIES[c.category], c.village, c.district, c.state,
                     svc.ist_date(c.submitted_at), STATUSES[c.status], VERIFICATION_STATUSES[c.verification_status],
                     "Yes" if ev else "No", svc.ist_date(c.updated_at), "Yes" if c.is_demo else "No"])
    audit.record(db, ctx.user, "export.complaints_csv", details={"dataset": dataset, "rows": len(result)})
    db.commit()
    return _csv_response(rows, f"gaon-saathi-complaints-{dataset}-{date.today().isoformat()}.csv")
