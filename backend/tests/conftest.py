"""Test fixtures.

By default tests use a temporary SQLite database. To run them against
PostgreSQL set TEST_DATABASE_URL, e.g.

    TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/gaon_test pytest

(the database will be wiped).
"""

from __future__ import annotations

import base64
import hashlib
import os
import shutil
import tempfile
from io import BytesIO
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="gaon-tests-"))
os.environ.update({
    "APP_ENV": "test",
    "DATABASE_URL": os.environ.get("TEST_DATABASE_URL", f"sqlite:///{(_TMP / 'test.db').as_posix()}"),
    "SECRET_KEY": "test-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz",
    "DATA_ENCRYPTION_KEY": base64.b64encode(b"\x01" * 32).decode(),
    "EVIDENCE_DIR": str(_TMP / "evidence"),
    "POW_DIFFICULTY": "6",
    "POW_MIN_SOLVE_SECONDS": "0",
    "RATE_LIMIT_ENABLED": "false",
    "SERVE_FRONTEND": "false",
    "ENABLE_API_DOCS": "false",
})

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import get_engine, get_sessionmaker  # noqa: E402
from app.main import app  # noqa: E402
from app.models import AdminUser, Base  # noqa: E402
from app.security.passwords import hash_password  # noqa: E402
from app.security.pow import leading_zero_bits  # noqa: E402
from app.security.ratelimit import limiter  # noqa: E402

ADMIN_PASSWORD = "Strong-Test-Passw0rd!"


@pytest.fixture(scope="session", autouse=True)
def _database():
    from alembic import command
    from alembic.config import Config

    engine = get_engine()
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
    backend = Path(__file__).resolve().parent.parent
    cfg = Config(str(backend / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend / "migrations"))
    command.upgrade(cfg, "head")  # tests run against the real migrations
    yield
    engine.dispose()
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    engine = get_engine()
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    limiter.reset()
    get_settings().rate_limit_enabled = False
    shutil.rmtree(get_settings().evidence_dir, ignore_errors=True)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    session = get_sessionmaker()()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def solve(challenge: str, difficulty: int) -> str:
    counter = 0
    while True:
        digest = hashlib.sha256(f"{challenge}:{counter}".encode()).digest()
        if leading_zero_bits(digest) >= difficulty:
            return str(counter)
        counter += 1


def solved_challenge(client) -> dict:
    data = client.get("/api/public/challenge").json()
    return {"pow_challenge": data["challenge"], "pow_solution": solve(data["challenge"], data["difficulty"])}


VALID_FORM = {
    "category": "illegal_tree_cutting",
    "village": "Rampur Kalan",
    "district": "Sitapur",
    "state": "Uttar Pradesh",
    "description": "Six neem trees on panchayat land near the canal were cut at night without permission.",
    "approximate_location": "Canal road, east side",
    "consent": "true",
}


def submit(client, files=None, **overrides):
    form = {**VALID_FORM, **solved_challenge(client), **overrides}
    form = {k: v for k, v in form.items() if v is not None}
    return client.post("/api/public/complaints", data=form, files=files or None)


def jpeg_bytes(size=(64, 48), color="red", exif=None) -> bytes:
    buf = BytesIO()
    img = Image.new("RGB", size, color)
    if exif is not None:
        img.save(buf, "JPEG", exif=exif)
    else:
        img.save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture
def make_admin(db):
    def _make(username="asha", role="admin", password=ADMIN_PASSWORD, must_change=False):
        user = AdminUser(username=username, role=role, password_hash=hash_password(password),
                         must_change_password=must_change)
        db.add(user)
        db.commit()
        return user
    return _make


def login(client, username="asha", password=ADMIN_PASSWORD):
    response = client.post("/api/admin/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response


@pytest.fixture
def admin_client(client, make_admin):
    make_admin()
    login(client)
    return client
