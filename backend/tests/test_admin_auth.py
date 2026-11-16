"""Administrator authentication, sessions, CSRF and roles."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.db_types import utcnow
from app.models import AdminSession, AdminUser, AuditLog
from tests.conftest import ADMIN_PASSWORD, login


def test_login_sets_secure_session_cookie(client, make_admin):
    make_admin()
    response = login(client)
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert response.json()["user"]["username"] == "asha"
    assert client.get("/api/admin/auth/me").status_code == 200


def test_password_is_hashed_with_argon2id(make_admin, db):
    user = make_admin()
    assert user.password_hash.startswith("$argon2id$")
    assert ADMIN_PASSWORD not in user.password_hash


def test_session_token_not_stored_in_plaintext(client, make_admin, db):
    make_admin()
    response = login(client)
    cookie_value = response.cookies.get("gs_session")
    session = db.scalar(select(AdminSession))
    assert cookie_value and session.token_hash != cookie_value and cookie_value not in session.token_hash


def test_wrong_password_and_unknown_user_same_message(client, make_admin):
    make_admin()
    a = client.post("/api/admin/auth/login", json={"username": "asha", "password": "wrong-password-123"})
    b = client.post("/api/admin/auth/login", json={"username": "nobody", "password": "wrong-password-123"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_account_lockout_after_failures(client, make_admin, db):
    make_admin()
    for _ in range(5):
        client.post("/api/admin/auth/login", json={"username": "asha", "password": "wrong-password-123"})
    # Even the correct password is refused while locked.
    locked = client.post("/api/admin/auth/login", json={"username": "asha", "password": ADMIN_PASSWORD})
    assert locked.status_code == 401
    user = db.scalar(select(AdminUser).where(AdminUser.username == "asha"))
    db.refresh(user)
    assert user.locked_until is not None
    actions = set(db.scalars(select(AuditLog.action)).all())
    assert {"auth.login_failed", "auth.account_locked"} <= actions


def test_unauthenticated_requests_rejected(client):
    for path in ("/api/admin/complaints", "/api/admin/stats", "/api/admin/users", "/api/admin/audit-logs",
                 "/api/admin/settings", "/api/admin/authorities"):
        assert client.get(path).status_code == 401, path


def test_csrf_token_required_for_changes(admin_client):
    token = admin_client.headers.pop("X-CSRF-Token")
    response = admin_client.post("/api/admin/authorities", json={"name": "Test Office", "level": "district"})
    assert response.status_code == 403
    admin_client.headers["X-CSRF-Token"] = "forged-token"
    assert admin_client.post("/api/admin/authorities", json={"name": "Test Office", "level": "district"}).status_code == 403
    admin_client.headers["X-CSRF-Token"] = token
    assert admin_client.post("/api/admin/authorities", json={"name": "Test Office", "level": "district"}).status_code == 201


def test_logout_revokes_session(admin_client):
    assert admin_client.post("/api/admin/auth/logout").status_code == 200
    assert admin_client.get("/api/admin/auth/me").status_code == 401


def test_idle_session_expires(admin_client, db):
    session = db.scalar(select(AdminSession))
    session.last_seen_at = utcnow() - timedelta(hours=2)
    db.commit()
    response = admin_client.get("/api/admin/auth/me")
    assert response.status_code == 401
    assert "inactivity" in response.json()["detail"]


def test_role_based_access(client, make_admin):
    make_admin(username="viewer1", role="viewer")
    login(client, "viewer1")
    assert client.get("/api/admin/complaints").status_code == 200
    assert client.get("/api/admin/stats").status_code == 200
    assert client.get("/api/admin/users").status_code == 403
    assert client.get("/api/admin/audit-logs").status_code == 403
    assert client.post("/api/admin/authorities", json={"name": "X Office", "level": "district"}).status_code == 403


def test_must_change_password_flow(client, make_admin):
    make_admin(username="newbie", role="reviewer", must_change=True)
    login(client, "newbie")
    blocked = client.get("/api/admin/complaints")
    assert blocked.status_code == 403 and blocked.json()["detail"] == "password_change_required"
    weak = client.post("/api/admin/auth/change-password",
                       json={"current_password": ADMIN_PASSWORD, "new_password": "short"})
    assert weak.status_code == 422
    ok = client.post("/api/admin/auth/change-password",
                     json={"current_password": ADMIN_PASSWORD, "new_password": "A-much-better-passphrase-42"})
    assert ok.status_code == 200
    assert client.get("/api/admin/complaints").status_code == 200


def test_admin_user_management(admin_client):
    created = admin_client.post("/api/admin/users", json={"username": "ravi.k", "role": "reviewer",
                                                          "temporary_password": "Temporary-Pass-2026"})
    assert created.status_code == 201
    assert created.json()["must_change_password"] is True
    dup = admin_client.post("/api/admin/users", json={"username": "ravi.k", "role": "viewer",
                                                      "temporary_password": "Temporary-Pass-2026"})
    assert dup.status_code == 409
    weak = admin_client.post("/api/admin/users", json={"username": "weak1", "role": "viewer",
                                                       "temporary_password": "password123"})
    assert weak.status_code == 422
    user_id = created.json()["id"]
    assert admin_client.patch(f"/api/admin/users/{user_id}", json={"is_active": False}).json()["is_active"] is False


def test_last_admin_cannot_be_removed(admin_client, db):
    me = db.scalar(select(AdminUser).where(AdminUser.username == "asha"))
    response = admin_client.patch(f"/api/admin/users/{me.id}", json={"role": "viewer"})
    assert response.status_code == 409


def test_security_headers(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    headers = response.headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in headers["content-security-policy"]
    assert "geolocation=()" in headers["permissions-policy"]
    assert headers["cache-control"] == "no-store"
    assert "server" not in {k.lower() for k in headers if headers[k].lower().startswith("uvicorn")}


def test_api_docs_disabled_and_unknown_routes_404(client):
    assert client.get("/api/docs").status_code == 404
    assert client.get("/api/openapi.json").status_code == 404
    assert client.get("/api/does-not-exist").status_code == 404


def test_validation_errors_do_not_echo_input(client):
    response = client.post("/api/public/track", json={"complaint_id": "x", "tracking_token": "SECRET-VALUE-123"})
    assert response.status_code == 422
    assert "SECRET-VALUE-123" not in response.text
