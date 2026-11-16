"""Public, anonymous endpoints. No login, no personal information, no IP storage."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import CATEGORIES, STATES_AND_UTS, STATUSES
from app.database import get_db
from app.routers.common import friendly_validation_error, read_and_process_uploads
from app.schemas import ComplaintCreate, TrackRequest, clean_multiline
from app.security.pow import ChallengeError, issue_challenge, verify_and_spend
from app.security.ratelimit import rate_limit
from app.services import complaints as complaint_service
from app.services.complaints import WorkflowError

router = APIRouter(prefix="/api/public", tags=["public"])

NOT_FOUND_MESSAGE = ("No complaint was found for this Complaint ID and Tracking Code. "
                     "Please check both and try again.")


@router.get("/config")
def public_config():
    s = get_settings()
    return {
        "categories": [{"value": k, "label": v} for k, v in CATEGORIES.items()],
        "statuses": [{"value": k, "label": v} for k, v in STATUSES.items()],
        "states": list(STATES_AND_UTS),
        "uploads": {
            "max_files": s.max_files_per_submission,
            "max_image_mb": s.max_image_mb,
            "max_video_mb": s.max_video_mb,
            "max_pdf_mb": s.max_pdf_mb,
            "max_total_mb": s.max_total_upload_mb,
            "accept": ".jpg,.jpeg,.png,.webp,.mp4,.m4v,.mov,.3gp,.webm,.pdf",
        },
        "support": {"email": s.support_email, "phone": s.support_phone},
    }


@router.get("/challenge", dependencies=[Depends(rate_limit("challenge", 60, 600))])
def challenge():
    return issue_challenge()


def _check_spam_guards(website: str, pow_challenge: str, pow_solution: str) -> None:
    if website:
        # Honeypot field: invisible to people, often filled by bots.
        raise HTTPException(status_code=400, detail="Your submission could not be accepted. Please try again.")
    try:
        verify_and_spend(pow_challenge, pow_solution)
    except ChallengeError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc), "code": "challenge_failed"}) from exc


@router.post("/complaints", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(rate_limit("submit", 10, 3600))])
def submit_complaint(
    category: Annotated[str, Form(max_length=60)] = "",
    village: Annotated[str, Form(max_length=300)] = "",
    district: Annotated[str, Form(max_length=300)] = "",
    state: Annotated[str, Form(max_length=100)] = "",
    description: Annotated[str, Form(max_length=12000)] = "",
    approximate_location: Annotated[str, Form(max_length=600)] = "",
    consent: Annotated[str, Form(max_length=10)] = "",
    pow_challenge: Annotated[str, Form(max_length=400)] = "",
    pow_solution: Annotated[str, Form(max_length=20)] = "",
    website: Annotated[str, Form(max_length=200)] = "",
    files: Annotated[list[UploadFile] | None, File()] = None,
    db: Session = Depends(get_db),
):
    if consent.lower() not in ("true", "yes", "on", "1"):
        raise HTTPException(status_code=400, detail="Please confirm that you understand how your complaint will be reviewed.")
    try:
        data = ComplaintCreate(
            category=category, village=village, district=district, state=state,
            description=description, approximate_location=approximate_location or None,
        )
    except ValidationError as exc:
        raise friendly_validation_error(exc) from exc

    _check_spam_guards(website, pow_challenge, pow_solution)
    processed = read_and_process_uploads(files, get_settings().max_files_per_submission)

    complaint, token = complaint_service.create_complaint(db, data, processed)
    notices = sorted({n for p in processed for n in p.notices})
    return {
        "complaint_id": complaint.public_id,
        "tracking_token": token,
        "category": complaint.category,
        "category_label": CATEGORIES[complaint.category],
        "status": complaint.status,
        "status_label": STATUSES[complaint.status],
        "submitted_on": complaint_service.ist_date(complaint.submitted_at),
        "evidence_count": len(processed),
        "notices": notices,
    }


@router.post("/track", dependencies=[Depends(rate_limit("track", 30, 600))])
def track(body: TrackRequest, db: Session = Depends(get_db)):
    complaint = complaint_service.find_for_tracking(db, body.complaint_id, body.tracking_token)
    if complaint is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MESSAGE)
    return complaint_service.public_view(complaint)


@router.post("/complaints/supplement", dependencies=[Depends(rate_limit("supplement", 10, 3600))])
def add_information(
    complaint_id: Annotated[str, Form(max_length=40)] = "",
    tracking_token: Annotated[str, Form(max_length=40)] = "",
    message: Annotated[str, Form(max_length=8000)] = "",
    pow_challenge: Annotated[str, Form(max_length=400)] = "",
    pow_solution: Annotated[str, Form(max_length=20)] = "",
    website: Annotated[str, Form(max_length=200)] = "",
    files: Annotated[list[UploadFile] | None, File()] = None,
    db: Session = Depends(get_db),
):
    """Let a reporter add information to their own complaint, proven by the tracking code."""
    complaint = complaint_service.find_for_tracking(db, complaint_id, tracking_token)
    if complaint is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND_MESSAGE)
    text = clean_multiline(message) or None
    if text and len(text) > 3000:
        raise HTTPException(status_code=422, detail="Your message is too long (at most 3000 characters).")
    _check_spam_guards(website, pow_challenge, pow_solution)

    settings = get_settings()
    remaining = settings.max_evidence_per_complaint - len(complaint.evidence)
    if remaining <= 0 and any(f is not None and f.filename for f in (files or [])):
        raise HTTPException(status_code=400, detail="This complaint already has the maximum number of evidence files.")
    processed = read_and_process_uploads(files, max(0, min(settings.max_files_per_submission, remaining)))
    if not text and not processed:
        raise HTTPException(status_code=422, detail="Please write a message or attach at least one file.")
    try:
        complaint_service.add_reporter_update(db, complaint, text, processed)
    except WorkflowError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "ok": True,
        "message": "Thank you. Your information was added to the complaint.",
        "notices": sorted({n for p in processed for n in p.notices}),
    }
