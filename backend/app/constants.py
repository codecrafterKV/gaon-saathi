"""Domain constants shared by models, validation, services and the API.

Keeping these in one module means the database CHECK constraints, the API
validation and the admin workflow can never drift apart.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Complaint categories
# --------------------------------------------------------------------------
CATEGORIES: dict[str, str] = {
    "public_space_encroachment": "Public Space Encroachment",
    "illegal_tree_cutting": "Illegal Tree Cutting",
    "development_fund_misuse": "Development Fund Misuse",
    "road_drainage": "Road and Drainage Problems",
    "ration_distribution": "Ration Distribution Irregularities",
    "public_resource_misuse": "Public Resource Misuse",
    "corruption_governance": "Corruption or Local Governance Issues",
    "other": "Other Village Problems",
}

# --------------------------------------------------------------------------
# Complaint status workflow
# --------------------------------------------------------------------------
RECEIVED = "received"
UNDER_REVIEW = "under_review"
EVIDENCE_VERIFICATION = "evidence_verification"
ACTION_IN_PROGRESS = "action_in_progress"
FORWARDED = "forwarded"
RESOLVED = "resolved"
REJECTED = "rejected"
CLOSED = "closed"

STATUSES: dict[str, str] = {
    RECEIVED: "Received",
    UNDER_REVIEW: "Under Review",
    EVIDENCE_VERIFICATION: "Evidence Verification",
    ACTION_IN_PROGRESS: "Action in Progress",
    FORWARDED: "Forwarded to Relevant Authority",
    RESOLVED: "Resolved",
    REJECTED: "Rejected",
    CLOSED: "Closed",
}

# Statuses after which the complaint is considered finished.
TERMINAL_STATUSES = frozenset({RESOLVED, REJECTED, CLOSED})

# Allowed transitions. Anything not listed here is rejected by the API.
STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    RECEIVED: frozenset({UNDER_REVIEW, REJECTED, CLOSED}),
    UNDER_REVIEW: frozenset({EVIDENCE_VERIFICATION, ACTION_IN_PROGRESS, FORWARDED, REJECTED, CLOSED}),
    EVIDENCE_VERIFICATION: frozenset({UNDER_REVIEW, ACTION_IN_PROGRESS, FORWARDED, REJECTED, CLOSED}),
    ACTION_IN_PROGRESS: frozenset({UNDER_REVIEW, FORWARDED, RESOLVED, CLOSED}),
    FORWARDED: frozenset({ACTION_IN_PROGRESS, RESOLVED, CLOSED}),
    RESOLVED: frozenset({UNDER_REVIEW, CLOSED}),
    REJECTED: frozenset({UNDER_REVIEW, CLOSED}),
    CLOSED: frozenset({UNDER_REVIEW}),
}

# Default public progress messages. Admins can override per update.
DEFAULT_PUBLIC_MESSAGES: dict[str, str] = {
    RECEIVED: "Your complaint has been received. Our team will review it soon.",
    UNDER_REVIEW: "Our team is reviewing the details of your complaint.",
    EVIDENCE_VERIFICATION: "Our team is checking the information and evidence provided.",
    ACTION_IN_PROGRESS: "Our team is working on the next steps for this complaint.",
    FORWARDED: "Your complaint has been sent to the relevant authority. We are following up.",
    RESOLVED: "This complaint has been marked as resolved.",
    REJECTED: "This complaint could not be taken forward.",
    CLOSED: "This complaint has been closed.",
}

# Public progress steps shown on the tracking page (the "happy path").
PUBLIC_PROGRESS_STEPS = [RECEIVED, UNDER_REVIEW, EVIDENCE_VERIFICATION, ACTION_IN_PROGRESS, FORWARDED, RESOLVED]

# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------
VERIFICATION_STATUSES: dict[str, str] = {
    "pending": "Not yet verified",
    "verified": "Verified",
    "unverified": "Could not be verified",
    "needs_more_info": "Needs more information",
}

# --------------------------------------------------------------------------
# Internal notes
# --------------------------------------------------------------------------
NOTE_KINDS: dict[str, str] = {
    "internal_note": "Internal note",
    "follow_up": "Follow-up update",
    "verification": "Verification finding",
    "evidence_request": "Request for more information",
    "reporter_update": "Information added by reporter",
}
ADMIN_NOTE_KINDS = frozenset({"internal_note", "follow_up"})

# --------------------------------------------------------------------------
# Forwarding channels
# --------------------------------------------------------------------------
FORWARDING_CHANNELS: dict[str, str] = {
    "online_portal": "Official online grievance portal",
    "email": "Official email",
    "letter": "Letter / written application",
    "in_person": "Submitted in person",
    "helpline": "Official helpline",
    "other": "Other official channel",
}

AUTHORITY_LEVELS: dict[str, str] = {
    "gram_panchayat": "Gram Panchayat",
    "block": "Block",
    "district": "District",
    "state": "State",
    "national": "National",
    "other": "Other",
}

# --------------------------------------------------------------------------
# Admin roles
# --------------------------------------------------------------------------
ROLE_ADMIN = "admin"
ROLE_REVIEWER = "reviewer"
ROLE_VIEWER = "viewer"
ROLES: dict[str, str] = {
    ROLE_ADMIN: "Administrator (full access)",
    ROLE_REVIEWER: "Reviewer (manage complaints)",
    ROLE_VIEWER: "Viewer (read only)",
}

# --------------------------------------------------------------------------
# Evidence
# --------------------------------------------------------------------------
MEDIA_KINDS = ("image", "video", "pdf")
SCAN_STATUSES = ("clean", "not_scanned", "error")

# --------------------------------------------------------------------------
# Indian states and union territories (for the location dropdown)
# --------------------------------------------------------------------------
STATES_AND_UTS: tuple[str, ...] = (
    "Andaman and Nicobar Islands",
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chandigarh",
    "Chhattisgarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jammu and Kashmir",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Ladakh",
    "Lakshadweep",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Puducherry",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
)


def sql_in_list(values) -> str:
    """Render values as a SQL IN list for CHECK constraints (static, trusted values only)."""
    return ", ".join(f"'{v}'" for v in values)
