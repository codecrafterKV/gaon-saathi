"""Public complaint tracking and reporter follow-up."""

from __future__ import annotations

from sqlalchemy import select

from app.models import Complaint, ComplaintNote
from tests.conftest import jpeg_bytes, solved_challenge, submit


def _track(client, complaint_id, token):
    return client.post("/api/public/track", json={"complaint_id": complaint_id, "tracking_token": token})


def test_track_with_id_and_token(client):
    created = submit(client).json()
    response = _track(client, created["complaint_id"], created["tracking_token"])
    assert response.status_code == 200
    data = response.json()
    assert data["complaint_id"] == created["complaint_id"]
    assert data["status"] == "received"
    assert data["category_label"] == "Illegal Tree Cutting"
    assert data["progress_message"]
    assert data["submitted_on"] and data["last_updated"]
    # Never exposed publicly: description, location detail, evidence, notes, hashes.
    text = response.text.lower()
    for secret in ("neem", "canal road", "description", "approximate_location", "evidence_count", "\"evidence\"",
                   "internal_note", "verification_findings", "tracking_token", "village", "district"):
        assert secret not in text, secret
    assert set(data) == {"complaint_id", "category", "category_label", "submitted_on", "status", "status_label",
                         "last_updated", "progress_message", "info_requested", "can_add_information",
                         "progress_steps", "timeline", "is_demo"}


def test_track_is_forgiving_about_format(client):
    created = submit(client).json()
    token = created["tracking_token"].replace("-", " ").lower()
    response = _track(client, " " + created["complaint_id"].lower() + " ", token)
    assert response.status_code == 200


def test_wrong_token_gives_generic_404(client):
    created = submit(client).json()
    wrong = "2222-2222-2222-2222"
    a = _track(client, created["complaint_id"], wrong)
    b = _track(client, "GS-2026-ZZZZZZZZ", wrong)
    c = _track(client, "nonsense", "also nonsense")
    assert a.status_code == b.status_code == 404
    # Same message whether or not the ID exists (no enumeration).
    assert a.json() == b.json()
    assert c.status_code in (404, 422)


def test_internal_notes_never_reach_public_view(client, admin_client):
    created = submit(client).json()
    admin_client.post(f"/api/admin/complaints/{created['complaint_id']}/notes",
                      json={"kind": "internal_note", "body": "SECRET-INTERNAL-NOTE about the investigation"})
    admin_client.post(f"/api/admin/complaints/{created['complaint_id']}/status",
                      json={"to_status": "under_review", "internal_note": "SECRET-STATUS-REASON",
                            "public_message": "We are looking into this."})
    data = _track(client, created["complaint_id"], created["tracking_token"])
    assert data.status_code == 200
    assert "SECRET" not in data.text
    assert "asha" not in data.text  # admin identity never shown
    assert data.json()["progress_message"] == "We are looking into this."
    assert [t["status"] for t in data.json()["timeline"]] == ["received", "under_review"]


def test_reporter_can_add_information(client, db):
    created = submit(client).json()
    form = {"complaint_id": created["complaint_id"], "tracking_token": created["tracking_token"],
            "message": "The cutting happened again yesterday near the same spot.", **solved_challenge(client)}
    response = client.post("/api/public/complaints/supplement", data=form,
                           files=[("files", ("x.jpg", jpeg_bytes(), "image/jpeg"))])
    assert response.status_code == 200, response.text
    complaint = db.scalar(select(Complaint))
    db.refresh(complaint)
    assert complaint.has_unread_update is True
    assert len(complaint.evidence) == 1
    note = db.scalar(select(ComplaintNote).where(ComplaintNote.kind == "reporter_update"))
    assert "again yesterday" in note.body and note.author_id is None


def test_supplement_requires_correct_token(client):
    created = submit(client).json()
    form = {"complaint_id": created["complaint_id"], "tracking_token": "2222-2222-2222-2222",
            "message": "hello there, more details", **solved_challenge(client)}
    assert client.post("/api/public/complaints/supplement", data=form).status_code == 404


def test_supplement_blocked_after_closing(client, admin_client):
    created = submit(client).json()
    admin_client.post(f"/api/admin/complaints/{created['complaint_id']}/status",
                      json={"to_status": "closed", "internal_note": "Duplicate complaint"})
    form = {"complaint_id": created["complaint_id"], "tracking_token": created["tracking_token"],
            "message": "More details about the problem", **solved_challenge(client)}
    assert client.post("/api/public/complaints/supplement", data=form).status_code == 409
