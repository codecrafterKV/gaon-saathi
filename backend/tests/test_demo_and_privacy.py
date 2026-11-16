"""Demo data separation and privacy of logs."""

from __future__ import annotations

import logging

from sqlalchemy import func, select

from app.models import Authority, Complaint
from app.services.demo import seed_demo_data
from app.services.maintenance import clear_demo_data
from tests.conftest import submit


def test_demo_data_is_marked_and_separable(client, admin_client, db):
    real = submit(client).json()["complaint_id"]
    result = seed_demo_data(db, count=12)
    assert result["complaints"] == 12

    demo = db.scalars(select(Complaint).where(Complaint.is_demo.is_(True))).unique().all()
    assert len(demo) == 12
    assert all(c.public_id.startswith("GS-DEMO-") for c in demo)
    assert all(c.description.startswith("[DEMO DATA]") for c in demo)

    live_stats = admin_client.get("/api/admin/stats?dataset=live").json()
    demo_stats = admin_client.get("/api/admin/stats?dataset=demo").json()
    all_stats = admin_client.get("/api/admin/stats?dataset=all").json()
    assert live_stats["total"] == 1 and demo_stats["total"] == 12 and all_stats["total"] == 13

    listing = admin_client.get("/api/admin/complaints?dataset=demo&page_size=100").json()
    assert all(i["is_demo"] for i in listing["items"])

    # Demo complaints can be tracked with their demo tracking codes.
    sample = result["sample_tracking"][0]
    tracked = client.post("/api/public/track", json={"complaint_id": sample["complaint_id"],
                                                     "tracking_token": sample["tracking_token"]})
    assert tracked.status_code == 200 and tracked.json()["is_demo"] is True

    # Seeding again replaces (not duplicates) demo data.
    seed_demo_data(db, count=5)
    assert db.scalar(select(func.count()).select_from(Complaint).where(Complaint.is_demo.is_(True))) == 5

    removed, _ = clear_demo_data(db)
    assert removed == 5
    remaining = db.scalars(select(Complaint)).unique().all()
    assert [c.public_id for c in remaining] == [real]
    assert db.scalar(select(func.count()).select_from(Authority).where(Authority.is_demo.is_(True))) == 0


def test_demo_workflow_history_is_consistent(db):
    from app.constants import STATUS_TRANSITIONS

    seed_demo_data(db, count=20)
    for complaint in db.scalars(select(Complaint)).unique().all():
        steps = [h.to_status for h in complaint.history]
        assert steps[0] == "received"
        assert steps[-1] == complaint.status
        for a, b in zip(steps, steps[1:]):
            assert b in STATUS_TRANSITIONS[a], (a, b)
        if complaint.status == "forwarded" or "forwarded" in steps:
            assert complaint.forwardings, "forwarded complaints must have a forwarding record"
        if complaint.status == "resolved":
            assert complaint.resolution_summary


def test_logs_contain_no_complaint_content(client, caplog):
    caplog.set_level(logging.DEBUG)
    marker = "UNIQUE-PRIVATE-DESCRIPTION-MARKER village tree cutting near pond"
    created = submit(client, description=marker).json()
    client.post("/api/public/track", json={"complaint_id": created["complaint_id"],
                                           "tracking_token": created["tracking_token"]})
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert "UNIQUE-PRIVATE-DESCRIPTION-MARKER" not in logged
    assert created["tracking_token"] not in logged
    assert "testclient" not in logged  # client address never logged


def test_unhandled_errors_are_generic(client, monkeypatch, caplog):
    from app.routers import public

    def boom(*_args, **_kwargs):
        raise RuntimeError("SENSITIVE-INTERNAL-DETAIL")

    monkeypatch.setattr(public.complaint_service, "find_for_tracking", boom)
    caplog.set_level(logging.ERROR)
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        response = c.post("/api/public/track", json={"complaint_id": "GS-2026-AAAAAAAA",
                                                     "tracking_token": "2222-2222-2222-2222"})
    assert response.status_code == 500
    assert "SENSITIVE" not in response.text
    assert "SENSITIVE-INTERNAL-DETAIL" not in "\n".join(r.getMessage() for r in caplog.records)
