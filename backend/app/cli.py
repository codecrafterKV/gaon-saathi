"""Gaon Saathi command line tool.

Usage (from the backend folder, with the virtual environment active):

    python -m app.cli init-env            # create .env with fresh random secrets
    python -m app.cli migrate             # create / upgrade database tables
    python -m app.cli create-admin --username asha --role admin
    python -m app.cli reset-password --username asha
    python -m app.cli seed-demo           # add clearly marked DEMO DATA
    python -m app.cli clear-demo          # remove all demo data
    python -m app.cli purge-expired       # apply the data retention policy
    python -m app.cli check-config        # show (non-secret) configuration
    python -m app.cli serve               # run the server without access logs
"""

from __future__ import annotations

import argparse
import base64
import getpass
import os
import secrets
import sys
from pathlib import Path

from app.config import BACKEND_DIR

ENV_PATH = BACKEND_DIR / ".env"


def cmd_init_env(args) -> int:
    if ENV_PATH.exists() and not args.force:
        print(f"{ENV_PATH} already exists. Not overwriting it.\n"
              "WARNING: replacing DATA_ENCRYPTION_KEY makes existing complaints and evidence unreadable.\n"
              "Use --force only on a fresh installation.")
        return 1
    example = (BACKEND_DIR / ".env.example").read_text(encoding="utf-8")
    secret_key = secrets.token_urlsafe(48)
    data_key = base64.b64encode(os.urandom(32)).decode("ascii")
    lines = []
    for line in example.splitlines():
        if line.startswith("SECRET_KEY="):
            line = f"SECRET_KEY={secret_key}"
        elif line.startswith("DATA_ENCRYPTION_KEY="):
            line = f"DATA_ENCRYPTION_KEY={data_key}"
        lines.append(line)
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        os.chmod(ENV_PATH, 0o600)
    except OSError:
        pass
    print(f"Created {ENV_PATH} with new random secrets.\n"
          "Keep a secure backup of DATA_ENCRYPTION_KEY: without it, stored complaints cannot be decrypted.")
    return 0


def cmd_migrate(_args) -> int:
    from alembic import command  # noqa: PLC0415
    from alembic.config import Config  # noqa: PLC0415

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(cfg, "head")
    print("Database is up to date.")
    return 0


def _read_new_password(username: str) -> str:
    from app.security.passwords import password_problems  # noqa: PLC0415

    while True:
        password = getpass.getpass("New password (min 12 characters, input hidden): ")
        problems = password_problems(password, username)
        if problems:
            print("\n".join(f"  - {p}" for p in problems))
            continue
        if getpass.getpass("Repeat password: ") != password:
            print("  - Passwords do not match.")
            continue
        return password


def cmd_create_admin(args) -> int:
    from sqlalchemy import select  # noqa: PLC0415

    from app.database import get_sessionmaker  # noqa: PLC0415
    from app.models import AdminUser  # noqa: PLC0415
    from app.schemas import USERNAME_RE  # noqa: PLC0415
    from app.security.passwords import hash_password  # noqa: PLC0415
    from app.services import audit  # noqa: PLC0415

    username = args.username.strip().lower()
    if not USERNAME_RE.match(username):
        print("Username must be 3-50 characters: lowercase letters, numbers, dot, dash or underscore.")
        return 1
    with get_sessionmaker()() as db:
        if db.scalar(select(AdminUser).where(AdminUser.username == username)):
            print(f"Administrator '{username}' already exists.")
            return 1
        password = _read_new_password(username)
        user = AdminUser(username=username, role=args.role, password_hash=hash_password(password))
        db.add(user)
        db.flush()
        audit.record(db, None, "admin.created_via_cli", "admin", username, {"role": args.role},
                     actor_username="cli")
        db.commit()
    print(f"Administrator '{username}' created with role '{args.role}'.")
    return 0


def cmd_reset_password(args) -> int:
    from sqlalchemy import select  # noqa: PLC0415

    from app.database import get_sessionmaker  # noqa: PLC0415
    from app.db_types import utcnow  # noqa: PLC0415
    from app.models import AdminUser  # noqa: PLC0415
    from app.security.auth import revoke_all_sessions  # noqa: PLC0415
    from app.security.passwords import hash_password  # noqa: PLC0415
    from app.services import audit  # noqa: PLC0415

    username = args.username.strip().lower()
    with get_sessionmaker()() as db:
        user = db.scalar(select(AdminUser).where(AdminUser.username == username))
        if user is None:
            print(f"Administrator '{username}' not found.")
            return 1
        user.password_hash = hash_password(_read_new_password(username))
        user.failed_login_count = 0
        user.locked_until = None
        user.is_active = True
        user.must_change_password = False
        user.password_changed_at = utcnow()
        revoke_all_sessions(db, user.id)
        audit.record(db, None, "admin.password_reset_via_cli", "admin", username, actor_username="cli")
        db.commit()
    print(f"Password for '{username}' was reset and all their sessions were signed out.")
    return 0


def cmd_seed_demo(args) -> int:
    from app.database import get_sessionmaker  # noqa: PLC0415
    from app.services.demo import seed_demo_data  # noqa: PLC0415

    with get_sessionmaker()() as db:
        result = seed_demo_data(db, count=args.count)
    out_file = BACKEND_DIR / "data" / "demo-tracking-codes.txt"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# DEMO DATA ONLY - tracking codes for the fictional demo complaints", ""]
    lines += [f"{t['complaint_id']}  {t['tracking_token']}  ({t['status']})" for t in result["sample_tracking"]]
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Created {result['complaints']} DEMO complaints and {result['authorities']} demo authority records.")
    print("Try tracking one of these demo complaints on the Track Complaint page:")
    for t in result["sample_tracking"][:5]:
        print(f"  {t['complaint_id']}   {t['tracking_token']}   ({t['status']})")
    print(f"All demo tracking codes: {out_file}")
    return 0


def cmd_clear_demo(_args) -> int:
    from app.database import get_sessionmaker  # noqa: PLC0415
    from app.services.maintenance import clear_demo_data  # noqa: PLC0415

    with get_sessionmaker()() as db:
        complaints, authorities = clear_demo_data(db)
    demo_file = BACKEND_DIR / "data" / "demo-tracking-codes.txt"
    if demo_file.exists():
        demo_file.unlink()
    print(f"Removed {complaints} demo complaints and {authorities} demo authority records.")
    return 0


def cmd_purge(_args) -> int:
    from app.database import get_sessionmaker  # noqa: PLC0415
    from app.services import audit  # noqa: PLC0415
    from app.services.maintenance import purge_expired  # noqa: PLC0415

    with get_sessionmaker()() as db:
        removed = purge_expired(db)
        audit.record(db, None, "maintenance.retention_purge", details={"removed": removed}, actor_username="cli")
        db.commit()
    print(f"Retention purge complete: {removed} finished complaint(s) removed.")
    return 0


def cmd_check_config(_args) -> int:
    from app.config import ConfigError, get_settings  # noqa: PLC0415
    from app.services.evidence import find_ffmpeg  # noqa: PLC0415

    s = get_settings()
    try:
        s.validate_secrets()
        secrets_ok = "OK"
    except ConfigError as exc:
        secrets_ok = f"PROBLEM - {exc}"
    db_display = s.database_url.split("@")[-1] if "@" in s.database_url else s.database_url
    print(f"Environment:        {s.app_env}")
    print(f"Database:           {db_display}")
    print(f"Secrets:            {secrets_ok}")
    print(f"Evidence storage:   {s.storage_backend} ({s.evidence_dir if s.storage_backend == 'local' else s.s3_bucket})")
    print(f"Secure cookies:     {s.cookie_secure}")
    print(f"HSTS:               {s.hsts_enabled}")
    print(f"API docs:           {'enabled' if s.enable_api_docs else 'disabled'}")
    print(f"Malware scanning:   {'ClamAV at ' + s.clamav_host if s.clamav_host else 'not configured'}")
    print(f"Video metadata:     {'ffmpeg found' if find_ffmpeg() else 'ffmpeg NOT found (video metadata kept)'}")
    print(f"Anti-spam:          proof-of-work {s.pow_difficulty} bits, rate limiting {'on' if s.rate_limit_enabled else 'OFF'}")
    print(f"Frontend build:     {'found' if (s.frontend_dist / 'index.html').is_file() else 'not built'} ({s.frontend_dist})")
    return 0 if secrets_ok == "OK" else 1


def cmd_serve(args) -> int:
    import uvicorn  # noqa: PLC0415

    from app.logging_config import LOG_CONFIG  # noqa: PLC0415

    uvicorn.run(
        "app.main:app", host=args.host, port=args.port, reload=args.reload,
        access_log=False, log_config=LOG_CONFIG, proxy_headers=False, server_header=False,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Gaon Saathi management commands")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init-env", help="create backend/.env with random secrets")
    p.add_argument("--force", action="store_true", help="overwrite an existing .env (DANGEROUS)")
    p.set_defaults(func=cmd_init_env)

    sub.add_parser("migrate", help="create or upgrade the database").set_defaults(func=cmd_migrate)

    p = sub.add_parser("create-admin", help="create an administrator account")
    p.add_argument("--username", required=True)
    p.add_argument("--role", choices=["admin", "reviewer", "viewer"], default="admin")
    p.set_defaults(func=cmd_create_admin)

    p = sub.add_parser("reset-password", help="reset an administrator's password and unlock the account")
    p.add_argument("--username", required=True)
    p.set_defaults(func=cmd_reset_password)

    p = sub.add_parser("seed-demo", help="replace demo data with fresh DEMO DATA")
    p.add_argument("--count", type=int, default=36)
    p.set_defaults(func=cmd_seed_demo)

    sub.add_parser("clear-demo", help="remove all demo data").set_defaults(func=cmd_clear_demo)
    sub.add_parser("purge-expired", help="delete finished complaints past the retention period").set_defaults(func=cmd_purge)
    sub.add_parser("check-config", help="print the (non-secret) configuration").set_defaults(func=cmd_check_config)

    p = sub.add_parser("serve", help="run the web server (access logs disabled)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true")
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
