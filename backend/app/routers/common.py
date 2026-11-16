"""Helpers shared by routers."""

from __future__ import annotations

from fastapi import HTTPException, UploadFile
from pydantic import ValidationError

from app.config import get_settings
from app.services.evidence import EvidenceRejected, ProcessedFile, process_upload

_FIELD_NAMES = {
    "category": "Category",
    "village": "Village name",
    "district": "District",
    "state": "State",
    "description": "Problem description",
    "approximate_location": "Approximate location",
}


def friendly_validation_error(exc: ValidationError) -> HTTPException:
    """Turn a pydantic error into a short, user friendly message (never echoes input)."""
    fields: dict[str, str] = {}
    for err in exc.errors():
        loc = [str(p) for p in err.get("loc", []) if p not in ("body",)]
        name = loc[0] if loc else "form"
        message = err.get("msg", "Invalid value").removeprefix("Value error, ")
        if err.get("type") == "string_too_short":
            limit = (err.get("ctx") or {}).get("min_length")
            message = f"{_FIELD_NAMES.get(name, 'This field')} is too short" + (f" (at least {limit} characters)." if limit else ".")
        elif err.get("type") == "string_too_long":
            limit = (err.get("ctx") or {}).get("max_length")
            message = f"{_FIELD_NAMES.get(name, 'This field')} is too long" + (f" (at most {limit} characters)." if limit else ".")
        elif err.get("type") == "missing":
            message = f"{_FIELD_NAMES.get(name, 'This field')} is required."
        fields.setdefault(name, message)
    summary = next(iter(fields.values()), "Please check the form and try again.")
    return HTTPException(status_code=422, detail={"message": summary, "fields": fields})


def read_and_process_uploads(files: list[UploadFile] | None, max_count: int) -> list[ProcessedFile]:
    """Read, validate and sanitise uploaded evidence. Raises HTTPException(400)."""
    settings = get_settings()
    uploads = [f for f in (files or []) if f is not None and (f.filename or f.size)]
    if len(uploads) > max_count:
        raise HTTPException(status_code=400, detail=f"You can upload at most {max_count} files.")
    total = 0
    processed: list[ProcessedFile] = []
    per_file_cap = settings.mb(max(settings.max_image_mb, settings.max_pdf_mb, settings.max_video_mb))
    for upload in uploads:
        data = upload.file.read(per_file_cap + 1)
        if len(data) > per_file_cap:
            raise HTTPException(status_code=400, detail="A file is larger than the allowed size.")
        total += len(data)
        if total > settings.mb(settings.max_total_upload_mb):
            raise HTTPException(status_code=400,
                                detail=f"Total upload size is above {settings.max_total_upload_mb} MB.")
        try:
            processed.append(process_upload(upload.filename, data))
        except EvidenceRejected as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            upload.file.close()
    return processed
