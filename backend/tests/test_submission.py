"""Complaint submission: validation, IDs, anti-spam and privacy."""

from __future__ import annotations

import hashlib
import re

from sqlalchemy import inspect, select, text

from app.models import Complaint, ComplaintStatusHistory
from app.security.pow import leading_zero_bits
from app.services.identifiers import ALPHABET, new_public_id, new_tracking_token
from tests.conftest import VALID_FORM, solved_challenge, submit

ID_RE = re.compile(r"^GS-\d{4}-[" + ALPHABET + r"]{8}$")
TOKEN_RE = re.compile(r"^([" + ALPHABET + r"]{4}-){3}[" + ALPHABET + r"]{4}$")


def test_submit_valid_complaint(client, db):
    response = submit(client)
    assert response.status_code == 201, response.text
    body = response.json()
    assert ID_RE.match(body["complaint_id"])
    assert TOKEN_RE.match(body["tracking_token"])
    assert body["status"] == "received"
    assert body["status_label"] == "Received"
    assert body["evidence_count"] == 0

    complaint = db.scalar(select(Complaint).where(Complaint.public_id == body["complaint_id"]))
    assert complaint is not None
    assert complaint.status == "received"
    assert complaint.description == VALID_FORM["description"]
    assert complaint.is_demo is False
    # Only a keyed hash of the tracking token is stored.
    assert body["tracking_token"].replace("-", "") not in complaint.tracking_token_hash
    assert len(complaint.tracking_token_hash) == 64
    history = db.scalars(select(ComplaintStatusHistory).where(ComplaintStatusHistory.complaint_id == complaint.id)).all()
    assert [h.to_status for h in history] == ["received"]


def test_ids_are_unique_and_random(client):
    ids = {submit(client).json()["complaint_id"] for _ in range(8)}
    assert len(ids) == 8
    generated = {new_public_id() for _ in range(5000)}
    assert len(generated) == 5000
    tokens = {new_tracking_token() for _ in range(5000)}
    assert len(tokens) == 5000


def test_description_is_encrypted_at_rest(client, db):
    submit(client)
    raw = db.execute(text("SELECT description, approximate_location FROM complaints")).one()
    assert raw[0].startswith("v1:")
    assert "neem" not in raw[0]
    assert raw[1].startswith("v1:")


def test_no_personal_data_columns():
    """Privacy by design: no column can hold reporter identity or network data."""
    forbidden = re.compile(r"(name$|^name|phone|mobile|email|aadhaar|ip_?addr|user_agent|address|device)")
    allowed = {"username", "display_name", "authority_name", "actor_username"}
    from app.database import get_engine

    inspector = inspect(get_engine())
    for table in inspector.get_table_names():
        if table in ("admin_users", "admin_sessions", "admin_audit_logs", "authorities"):
            continue  # staff accounts and public office records, not reporters
        for column in inspector.get_columns(table):
            name = column["name"]
            assert name in allowed or not forbidden.search(name), f"{table}.{name} looks like personal data"


def test_required_fields_and_validation(client):
    response = submit(client, village="")
    assert response.status_code == 422
    assert "village" in response.json()["detail"]["fields"]

    response = submit(client, description="too short")
    assert response.status_code == 422
    assert "description" in response.json()["detail"]["fields"]

    response = submit(client, category="not-a-category")
    assert response.status_code == 422

    response = submit(client, state="Atlantis")
    assert response.status_code == 422


def test_consent_is_required(client):
    response = submit(client, consent="")
    assert response.status_code == 400


def test_control_characters_are_removed(client, db):
    response = submit(client, description="Drain blocked\x00 for‮ three months near the school, water entering houses.")
    assert response.status_code == 201
    complaint = db.scalar(select(Complaint))
    assert "\x00" not in complaint.description and "‮" not in complaint.description


def test_village_name_case_is_normalised(client, db):
    submit(client, village="RAMPUR KALAN")
    submit(client, village="rampur kalan")
    villages = {c.village for c in db.scalars(select(Complaint)).all()}
    assert villages == {"Rampur Kalan"}


def test_html_is_stored_as_text_not_executed(client, db):
    payload = "<script>alert('x')</script> The road near the school is broken for many months."
    assert submit(client, description=payload).status_code == 201
    assert db.scalar(select(Complaint)).description == payload  # stored verbatim; React escapes on output


# ---------------------------------------------------------------------------
# Anti-spam
# ---------------------------------------------------------------------------
def test_missing_or_wrong_proof_of_work_is_rejected(client):
    form = {**VALID_FORM}
    assert client.post("/api/public/complaints", data=form).status_code == 400

    data = client.get("/api/public/challenge").json()
    challenge, difficulty = data["challenge"], data["difficulty"]
    wrong = next(str(n) for n in range(1000)
                 if leading_zero_bits(hashlib.sha256(f"{challenge}:{n}".encode()).digest()) < difficulty)
    bad = client.post("/api/public/complaints", data={**form, "pow_challenge": challenge, "pow_solution": wrong})
    assert bad.status_code == 400
    assert bad.json()["detail"]["code"] == "challenge_failed"


def test_tampered_challenge_is_rejected(client):
    solved = solved_challenge(client)
    version, payload, sig = solved["pow_challenge"].split(".")
    tampered = {**solved, "pow_challenge": f"{version}.{payload}x.{sig}"}
    response = client.post("/api/public/complaints", data={**VALID_FORM, **tampered})
    assert response.status_code == 400


def test_challenge_cannot_be_replayed(client):
    solved = solved_challenge(client)
    first = client.post("/api/public/complaints", data={**VALID_FORM, **solved})
    assert first.status_code == 201
    second = client.post("/api/public/complaints", data={**VALID_FORM, **solved})
    assert second.status_code == 400
    assert "already used" in second.json()["detail"]["message"]


def test_honeypot_rejects_bots(client):
    response = submit(client, website="http://spam.example")
    assert response.status_code == 400


def test_rate_limit(client):
    from app.config import get_settings

    get_settings().rate_limit_enabled = True
    statuses = [client.get("/api/public/challenge").status_code for _ in range(65)]
    assert statuses[:60] == [200] * 60
    assert statuses[-1] == 429


def test_public_config(client):
    data = client.get("/api/public/config").json()
    assert len(data["categories"]) == 8
    assert "Uttar Pradesh" in data["states"]
    assert data["uploads"]["max_files"] == 5
