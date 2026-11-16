"""Admin complaint workflow, verification, forwarding, stats and exports."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from app.models import AuditLog, Complaint, ComplaintStatusHistory
from tests.conftest import jpeg_bytes, submit


def _status(client, cid, to, note="Reason for change", **extra):
    return client.post(f"/api/admin/complaints/{cid}/status", json={"to_status": to, "internal_note": note, **extra})


def test_full_workflow_to_resolution(client, admin_client, db):
    cid = submit(client).json()["complaint_id"]

    detail = admin_client.get(f"/api/admin/complaints/{cid}").json()
    assert detail["description"].startswith("Six neem trees")
    assert {t["status"] for t in detail["allowed_transitions"]} == {"under_review", "rejected", "closed"}

    assert _status(admin_client, cid, "under_review").status_code == 200
    assert _status(admin_client, cid, "evidence_verification").status_code == 200

    verification = admin_client.put(f"/api/admin/complaints/{cid}/verification",
                                     json={"verification_status": "verified", "findings": "Stumps seen on site photo."})
    assert verification.status_code == 200
    assert verification.json()["verification_status"] == "verified"

    authority = admin_client.post("/api/admin/authorities", json={
        "name": "Divisional Forest Office", "level": "district", "website": "https://example.gov.in"}).json()

    forwarded = admin_client.post(f"/api/admin/complaints/{cid}/forwardings", json={
        "authority_id": authority["id"], "channel": "letter", "submitted_on": date.today().isoformat(),
        "reference_number": "ACK-2026-001", "internal_note": "Submitted at office counter",
        "public_message": "Your complaint was submitted to the forest office."})
    assert forwarded.status_code == 201, forwarded.text
    body = forwarded.json()
    assert body["status"] == "forwarded"
    assert body["forwardings"][0]["reference_number"] == "ACK-2026-001"

    # Resolution needs a proper summary.
    missing = _status(admin_client, cid, "resolved")
    assert missing.status_code == 422
    resolved = _status(admin_client, cid, "resolved",
                       resolution_summary="Forest office confirmed action and replanting on 10 Nov.")
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["closed_at"]

    history = db.scalars(select(ComplaintStatusHistory).order_by(ComplaintStatusHistory.id)).all()
    assert [h.to_status for h in history] == ["received", "under_review", "evidence_verification", "forwarded", "resolved"]
    assert all(h.internal_note for h in history)
    actions = db.scalars(select(AuditLog.action)).all()
    assert actions.count("complaint.status_changed") == 4
    assert "complaint.forwarding_recorded" in actions


def test_invalid_transition_rejected(client, admin_client):
    cid = submit(client).json()["complaint_id"]
    response = _status(admin_client, cid, "resolved", resolution_summary="x" * 30)
    assert response.status_code == 409  # received -> resolved is not allowed


def test_cannot_mark_forwarded_without_forwarding_record(client, admin_client):
    cid = submit(client).json()["complaint_id"]
    _status(admin_client, cid, "under_review")
    response = _status(admin_client, cid, "forwarded")
    assert response.status_code == 409
    assert "forwarding" in response.json()["detail"].lower()


def test_forwarding_requires_acknowledgement_details(client, admin_client):
    cid = submit(client).json()["complaint_id"]
    _status(admin_client, cid, "under_review")
    response = admin_client.post(f"/api/admin/complaints/{cid}/forwardings", json={
        "authority_name": "BDO Office", "channel": "letter", "submitted_on": date.today().isoformat(),
        "internal_note": "Sent by registered post"})
    assert response.status_code == 422
    future = admin_client.post(f"/api/admin/complaints/{cid}/forwardings", json={
        "authority_name": "BDO Office", "channel": "letter", "reference_number": "X1",
        "submitted_on": (date.today() + timedelta(days=3)).isoformat(), "internal_note": "Sent by registered post"})
    assert future.status_code == 422


def test_cannot_forward_unreviewed_complaint(client, admin_client):
    cid = submit(client).json()["complaint_id"]
    response = admin_client.post(f"/api/admin/complaints/{cid}/forwardings", json={
        "authority_name": "BDO Office", "channel": "letter", "reference_number": "R-1",
        "submitted_on": date.today().isoformat(), "internal_note": "Sent by registered post"})
    assert response.status_code == 409


def test_status_change_requires_internal_explanation(client, admin_client):
    cid = submit(client).json()["complaint_id"]
    response = admin_client.post(f"/api/admin/complaints/{cid}/status", json={"to_status": "under_review", "internal_note": ""})
    assert response.status_code == 422


def test_request_information_flow(client, admin_client):
    created = submit(client).json()
    cid = created["complaint_id"]
    response = admin_client.post(f"/api/admin/complaints/{cid}/request-info", json={
        "public_message": "Please add a photo of the site if it is safe.",
        "internal_note": "No evidence attached"})
    assert response.status_code == 200
    tracked = client.post("/api/public/track", json={"complaint_id": cid, "tracking_token": created["tracking_token"]}).json()
    assert tracked["info_requested"] is True
    assert tracked["progress_message"] == "Please add a photo of the site if it is safe."


def test_viewer_cannot_change_status(client, make_admin):
    from tests.conftest import login

    cid = submit(client).json()["complaint_id"]
    make_admin(username="viewer1", role="viewer")
    login(client, "viewer1")
    assert _status(client, cid, "under_review").status_code == 403
    detail = client.get(f"/api/admin/complaints/{cid}").json()
    assert detail["evidence"] == []


def test_list_search_filters_and_pagination(client, admin_client):
    submit(client, village="Rampur Kalan", category="illegal_tree_cutting")
    submit(client, village="Sonpur", district="Barabanki", category="road_drainage",
           files=[("files", ("a.jpg", jpeg_bytes(), "image/jpeg"))])
    submit(client, village="Chandanpur", district="Gaya", state="Bihar", category="ration_distribution")

    all_items = admin_client.get("/api/admin/complaints").json()
    assert all_items["total"] == 3
    assert admin_client.get("/api/admin/complaints?category=road_drainage").json()["total"] == 1
    assert admin_client.get("/api/admin/complaints?district=Gaya").json()["total"] == 1
    assert admin_client.get("/api/admin/complaints?search=sonp").json()["items"][0]["village"] == "Sonpur"
    assert admin_client.get("/api/admin/complaints?has_evidence=true").json()["total"] == 1
    assert admin_client.get("/api/admin/complaints?status=received").json()["total"] == 3
    today = date.today().isoformat()
    assert admin_client.get(f"/api/admin/complaints?date_from={today}&date_to={today}").json()["total"] == 3
    assert admin_client.get("/api/admin/complaints?date_to=2000-01-01").json()["total"] == 0
    page = admin_client.get("/api/admin/complaints?page_size=2&page=2").json()
    assert len(page["items"]) == 1 and page["pages"] == 2
    # LIKE wildcards are escaped
    assert admin_client.get("/api/admin/complaints?search=%25").json()["total"] == 0
    filters = admin_client.get("/api/admin/complaints/filters").json()
    assert {d["district"] for d in filters["districts"]} == {"Sitapur", "Barabanki", "Gaya"}


def test_stats_empty_database(admin_client):
    data = admin_client.get("/api/admin/stats").json()
    assert data["total"] == 0
    assert all(s["count"] == 0 for s in data["by_status"])
    assert len(data["daily"]) == 30 and len(data["monthly"]) == 12
    assert data["median_days_to_resolve"] is None


def test_stats_match_database(client, admin_client):
    for _ in range(3):
        submit(client, category="road_drainage")
    submit(client, category="ration_distribution", village="Sonpur")
    cid = submit(client).json()["complaint_id"]
    _status(admin_client, cid, "under_review")

    data = admin_client.get("/api/admin/stats").json()
    assert data["total"] == 5
    by_status = {s["status"]: s["count"] for s in data["by_status"]}
    assert by_status["received"] == 4 and by_status["under_review"] == 1
    by_cat = {c["category"]: c["count"] for c in data["by_category"]}
    assert by_cat["road_drainage"] == 3 and by_cat["ration_distribution"] == 1
    assert data["daily"][-1]["count"] == 5
    assert data["top_villages"][0] == {"village": "Rampur Kalan", "district": "Sitapur", "state": "Uttar Pradesh", "count": 4}


def test_csv_exports_are_safe(client, admin_client):
    submit(client, village="=HYPERLINK(\"http://evil\")")
    stats_csv = admin_client.get("/api/admin/export/statistics.csv")
    assert stats_csv.status_code == 200
    assert stats_csv.headers["content-type"].startswith("text/csv")
    register = admin_client.get("/api/admin/export/complaints.csv")
    assert register.status_code == 200
    text = register.text
    assert "'=Hyperlink" in text or "'=HYPERLINK" in text  # formula neutralised
    assert "neem" not in text  # descriptions never exported


def test_delete_complaint_removes_files(client, admin_client, db):
    from pathlib import Path

    from app.config import get_settings

    cid = submit(client, files=[("files", ("a.jpg", jpeg_bytes(), "image/jpeg"))]).json()["complaint_id"]
    assert any(p.is_file() for p in Path(get_settings().evidence_dir).rglob("*"))
    wrong = admin_client.post(f"/api/admin/complaints/{cid}/delete", json={"reason": "Spam complaint", "confirm_id": "GS-2026-XXXXXXXX"})
    assert wrong.status_code == 400
    ok = admin_client.post(f"/api/admin/complaints/{cid}/delete", json={"reason": "Spam complaint", "confirm_id": cid})
    assert ok.status_code == 200
    assert db.scalar(select(Complaint)) is None
    assert not any(p.is_file() for p in Path(get_settings().evidence_dir).rglob("*"))
    assert "complaint.deleted" in db.scalars(select(AuditLog.action)).all()


def test_retention_purge(client, admin_client, db):
    from app.db_types import utcnow

    cid = submit(client).json()["complaint_id"]
    keep = submit(client).json()["complaint_id"]
    _status(admin_client, cid, "closed", note="Duplicate")
    complaint = db.scalar(select(Complaint).where(Complaint.public_id == cid))
    complaint.closed_at = utcnow() - timedelta(days=400)
    db.commit()
    assert admin_client.post("/api/admin/maintenance/purge").json()["removed"] == 1
    remaining = [c.public_id for c in db.scalars(select(Complaint)).all()]
    assert remaining == [keep]


def test_settings_update(admin_client):
    assert admin_client.get("/api/admin/settings").json()["settings"]["retention_days"] == 365
    assert admin_client.put("/api/admin/settings", json={"retention_days": 10}).status_code == 422
    assert admin_client.put("/api/admin/settings", json={"retention_days": 730}).json()["settings"]["retention_days"] == 730


def test_audit_log_has_no_sensitive_text(client, admin_client):
    cid = submit(client).json()["complaint_id"]
    admin_client.get(f"/api/admin/complaints/{cid}")
    admin_client.post(f"/api/admin/complaints/{cid}/notes", json={"kind": "internal_note", "body": "CONFIDENTIAL-NOTE"})
    logs = admin_client.get("/api/admin/audit-logs").json()
    assert logs["total"] >= 3
    assert "CONFIDENTIAL-NOTE" not in str(logs) and "neem" not in str(logs)
