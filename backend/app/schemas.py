"""Request validation schemas.

All free text is normalised (Unicode NFC, control characters removed) and
length-limited. Output encoding for HTML is handled by React on the client,
which escapes all text by default; the API never returns HTML.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.constants import (
    ADMIN_NOTE_KINDS,
    AUTHORITY_LEVELS,
    CATEGORIES,
    FORWARDING_CHANNELS,
    RESOLVED,
    ROLES,
    STATES_AND_UTS,
    STATUSES,
    VERIFICATION_STATUSES,
)

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f​-‏‪-‮⁦-⁩]")


def clean_multiline(value: str | None) -> str | None:
    if value is None:
        return None
    value = unicodedata.normalize("NFC", value).replace("\r\n", "\n").replace("\r", "\n")
    value = _CONTROL.sub("", value)
    value = re.sub(r"\n{4,}", "\n\n\n", value)
    return value.strip()


def clean_line(value: str | None) -> str | None:
    if value is None:
        return None
    value = unicodedata.normalize("NFC", value)
    value = _CONTROL.sub("", value)
    return re.sub(r"\s+", " ", value).strip()


def tidy_place_name(value: str) -> str:
    """Normalise case so 'RAMPUR' and 'rampur' are counted as the same village."""
    if value.isupper() or value.islower():
        return value.title()
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_max_length=10000)


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------
class ComplaintCreate(StrictModel):
    category: str
    village: str = Field(min_length=2, max_length=100)
    district: str = Field(min_length=2, max_length=100)
    state: str
    description: str = Field(min_length=20, max_length=5000)
    approximate_location: str | None = Field(default=None, max_length=200)

    @field_validator("category")
    @classmethod
    def _category(cls, v: str) -> str:
        if v not in CATEGORIES:
            raise ValueError("Please choose a valid problem category.")
        return v

    @field_validator("state")
    @classmethod
    def _state(cls, v: str) -> str:
        v = clean_line(v) or ""
        if v not in STATES_AND_UTS:
            raise ValueError("Please choose a valid state or union territory.")
        return v

    @field_validator("village", "district", mode="before")
    @classmethod
    def _place(cls, v):
        if not isinstance(v, str):
            return v
        v = clean_line(v) or ""
        if v and not re.search(r"\w", v):
            raise ValueError("Please enter a valid name.")
        return tidy_place_name(v)

    @field_validator("description", mode="before")
    @classmethod
    def _description(cls, v):
        return clean_multiline(v) if isinstance(v, str) else v

    @field_validator("approximate_location", mode="before")
    @classmethod
    def _approx(cls, v):
        if isinstance(v, str):
            v = clean_line(v)
            return v or None
        return v


class TrackRequest(StrictModel):
    complaint_id: str = Field(min_length=5, max_length=40)
    tracking_token: str = Field(min_length=10, max_length=40)


# ---------------------------------------------------------------------------
# Admin auth
# ---------------------------------------------------------------------------
class LoginRequest(StrictModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(StrictModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)


# ---------------------------------------------------------------------------
# Complaint workflow
# ---------------------------------------------------------------------------
class StatusUpdate(StrictModel):
    to_status: str
    internal_note: str = Field(min_length=5, max_length=4000)
    public_message: str | None = Field(default=None, max_length=500)
    resolution_summary: str | None = Field(default=None, max_length=4000)

    @field_validator("to_status")
    @classmethod
    def _status(cls, v: str) -> str:
        if v not in STATUSES:
            raise ValueError("Unknown status.")
        return v

    @field_validator("internal_note", "resolution_summary", mode="before")
    @classmethod
    def _clean_ml(cls, v):
        return clean_multiline(v) if isinstance(v, str) else v

    @field_validator("public_message", mode="before")
    @classmethod
    def _clean_pm(cls, v):
        if isinstance(v, str):
            return clean_multiline(v) or None
        return v

    @model_validator(mode="after")
    def _resolution(self):
        if self.to_status == RESOLVED and (not self.resolution_summary or len(self.resolution_summary) < 20):
            raise ValueError("A resolution summary of at least 20 characters is required to mark a complaint as Resolved.")
        return self


class NoteCreate(StrictModel):
    kind: str = "internal_note"
    body: str = Field(min_length=2, max_length=4000)

    @field_validator("kind")
    @classmethod
    def _kind(cls, v: str) -> str:
        if v not in ADMIN_NOTE_KINDS:
            raise ValueError("Unknown note type.")
        return v

    @field_validator("body", mode="before")
    @classmethod
    def _clean(cls, v):
        return clean_multiline(v) if isinstance(v, str) else v


class InfoRequest(StrictModel):
    public_message: str = Field(min_length=10, max_length=500)
    internal_note: str = Field(min_length=5, max_length=4000)

    @field_validator("public_message", "internal_note", mode="before")
    @classmethod
    def _clean(cls, v):
        return clean_multiline(v) if isinstance(v, str) else v


class VerificationUpdate(StrictModel):
    verification_status: str
    findings: str | None = Field(default=None, max_length=6000)
    authority_id: int | None = None

    @field_validator("verification_status")
    @classmethod
    def _vs(cls, v: str) -> str:
        if v not in VERIFICATION_STATUSES:
            raise ValueError("Unknown verification status.")
        return v

    @field_validator("findings", mode="before")
    @classmethod
    def _clean(cls, v):
        if isinstance(v, str):
            return clean_multiline(v) or None
        return v


class ForwardingCreate(StrictModel):
    authority_id: int | None = None
    authority_name: str | None = Field(default=None, max_length=200)
    channel: str
    submitted_on: date
    reference_number: str | None = Field(default=None, max_length=120)
    acknowledgement_details: str | None = Field(default=None, max_length=4000)
    internal_note: str = Field(min_length=5, max_length=4000)
    public_message: str | None = Field(default=None, max_length=500)

    @field_validator("channel")
    @classmethod
    def _channel(cls, v: str) -> str:
        if v not in FORWARDING_CHANNELS:
            raise ValueError("Unknown forwarding channel.")
        return v

    @field_validator("authority_name", "reference_number", mode="before")
    @classmethod
    def _line(cls, v):
        if isinstance(v, str):
            return clean_line(v) or None
        return v

    @field_validator("acknowledgement_details", "internal_note", "public_message", mode="before")
    @classmethod
    def _ml(cls, v):
        if isinstance(v, str):
            return clean_multiline(v) or None
        return v

    @model_validator(mode="after")
    def _check(self):
        if not self.authority_id and not self.authority_name:
            raise ValueError("Choose an authority or enter the authority's name.")
        if not self.reference_number and not self.acknowledgement_details:
            raise ValueError("Record the acknowledgement/reference number or the submission details. "
                             "A complaint can only be marked as forwarded after it was actually submitted.")
        if self.submitted_on > date.today():
            raise ValueError("The submission date cannot be in the future.")
        return self


# ---------------------------------------------------------------------------
# Authorities
# ---------------------------------------------------------------------------
class AuthorityIn(StrictModel):
    name: str = Field(min_length=2, max_length=200)
    department: str | None = Field(default=None, max_length=200)
    level: str = "district"
    state: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=120)
    grievance_channel: str | None = Field(default=None, max_length=200)
    website: str | None = Field(default=None, max_length=300)
    office_contact: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=4000)
    is_active: bool = True

    @field_validator("level")
    @classmethod
    def _level(cls, v: str) -> str:
        if v not in AUTHORITY_LEVELS:
            raise ValueError("Unknown authority level.")
        return v

    @field_validator("name", "department", "state", "district", "grievance_channel", "office_contact", mode="before")
    @classmethod
    def _line(cls, v):
        if isinstance(v, str):
            return clean_line(v) or None
        return v

    @field_validator("notes", mode="before")
    @classmethod
    def _notes(cls, v):
        if isinstance(v, str):
            return clean_multiline(v) or None
        return v

    @field_validator("website")
    @classmethod
    def _website(cls, v: str | None) -> str | None:
        if not v:
            return None
        v = v.strip()
        if not re.match(r"^https?://[^\s<>\"']+$", v, re.IGNORECASE):
            raise ValueError("Website must start with http:// or https://")
        return v


# ---------------------------------------------------------------------------
# Admin users and settings
# ---------------------------------------------------------------------------
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,49}$")


class AdminCreate(StrictModel):
    username: str
    role: str
    temporary_password: str = Field(min_length=1, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def _username(cls, v):
        v = (v or "").strip().lower()
        if not USERNAME_RE.match(v):
            raise ValueError("Username must be 3-50 characters: lowercase letters, numbers, dot, dash or underscore.")
        return v

    @field_validator("role")
    @classmethod
    def _role(cls, v: str) -> str:
        if v not in ROLES:
            raise ValueError("Unknown role.")
        return v


class AdminUpdate(StrictModel):
    role: str | None = None
    is_active: bool | None = None
    temporary_password: str | None = Field(default=None, max_length=128)

    @field_validator("role")
    @classmethod
    def _role(cls, v: str | None) -> str | None:
        if v is not None and v not in ROLES:
            raise ValueError("Unknown role.")
        return v


class SettingsUpdate(StrictModel):
    retention_days: int = Field(ge=30, le=3650)
