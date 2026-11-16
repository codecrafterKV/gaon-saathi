# GAON SAATHI — Your Voice, Our Responsibility.

Gaon Saathi is a secure, anonymous grievance platform for rural India. Villagers can report problems in their village, such as encroachment, illegal tree cutting, misuse of development funds or ration irregularities. **They do not register and give no personal information.** An authorised team then reviews each complaint, checks the evidence, finds the right authority and records every step. The villager follows progress using two codes.

> Gaon Saathi is an **independent** platform. It is **not an official government website**.

Built for **Tata InnoThon**.

---

## Contents

1. [Features](#features)
2. [Technology stack](#technology-stack)
3. [Project structure](#project-structure)
4. [Quick start (local demo)](#quick-start-local-demo)
5. [Environment variables](#environment-variables)
6. [Database setup](#database-setup)
7. [Running the backend](#running-the-backend)
8. [Running the frontend](#running-the-frontend)
9. [Creating the first administrator](#creating-the-first-administrator)
10. [Demo data](#demo-data)
11. [Running the tests](#running-the-tests)
12. [Deployment](#deployment)
13. [Security and privacy](#security-and-privacy)
14. [Known limitations](#known-limitations)

---

## Features

### For villagers (public site, no login)
- **Home, About, How It Works, Contact / Support, Privacy Policy, Terms** pages, all in simple English.
- **Report a Problem**, a 4-step form:
  1. Choose one of 8 categories, each with its own icon.
  2. Enter the problem's location (village, district, state) and a description. The form warns if the text looks like it contains a phone number, email, Aadhaar number or the person's name.
  3. Add optional evidence: photos, videos or PDFs, with previews, file sizes and remove buttons. Hidden **GPS and EXIF data is removed from photos on the phone before upload**, and again on the server.
  4. Review the complaint, give consent and submit, with an upload progress bar.
- **Success page.** It shows a random **Complaint ID** (`GS-2026-K7QM4XRT`) and a secret **Tracking Code** (`9PWD-H3NC-T6JA-ZB2E`) once, with copy, download and print options. The codes are never stored in the browser.
- **Track Complaint.** With both codes, the villager sees only limited public information: category, dates, status, a progress message and a timeline.
- **Add more information.** This is a privacy-preserving way for the team to ask for more evidence. The reporter adds details anonymously, proving ownership with the tracking code.

### For the team (admin dashboard, `/admin`)
- Secure login with no public registration, Argon2id password hashing, account lockout, session timeouts and CSRF protection.
- Three roles: **Administrator**, **Reviewer** and **Viewer** (read-only, cannot open evidence).
- **Dashboard.** Eight statistic cards plus charts: complaints by category, by status, over time (30 days / 12 months) and by village. Every chart has a table view, all numbers come from the database, and empty databases are handled.
- **Complaint management.** Search, filters (category, status, district, village, date range, evidence), sorting, pagination and a CSV export.
- **Complaint details:**
  - full description and secure evidence viewing (images, video streaming, PDF download), with metadata and virus-scan badges
  - a status workflow with **enforced transitions** and a required internal explanation for every change
  - verification (verified / unverified / needs more info) with findings and the responsible authority
  - **Forwarding records.** "Forwarded to Authority" can only be set after recording the authority, date and acknowledgement or reference number.
  - **Resolved** requires a written resolution summary
  - internal notes and follow-up updates, kept separate from public messages
  - a "what the reporter sees" preview
- **Authorities** directory of departments and official grievance channels.
- **Audit log** of every important admin action (logins, views, status changes, evidence views, exports, deletions).
- **Settings:** change password, manage team members, data retention period and purge, load or remove demo data, and a read-only security status panel.
- **CSV exports** of statistics and the complaint register. Descriptions are never exported, and the exports are protected against formula injection.

---

## Technology stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | **React 18 + Vite**, **Tailwind CSS**, **Lucide** icons, **Recharts** | As requested. Fast builds, a small bundle, and the admin area is lazy-loaded so the public site stays light on slow rural networks. |
| Fonts | Inter and Plus Jakarta Sans, **self-hosted** | No requests to Google Fonts or any CDN, so no visitor data reaches third parties. |
| Backend | **Python FastAPI** | As requested. Typed validation (Pydantic), automatic docs in development. |
| Database | **PostgreSQL** (production), SQLite (zero-setup development) | SQLAlchemy 2 + **Alembic migrations**. The test suite passes on both. |
| Passwords | **Argon2id** (`argon2-cffi`) | Current best practice (RFC 9106). |
| Encryption | **AES-256-GCM** (`cryptography`) | Complaint text, notes and evidence are encrypted at rest. |
| Media cleaning | Pillow (photos), ffmpeg via `imageio-ffmpeg` (videos), pypdf (PDFs) | Removes GPS, device and author metadata. |
| Anti-spam | Proof-of-work challenge + honeypot + privacy-preserving rate limits | No third-party CAPTCHA tracking villagers. |
| Evidence storage | Private local folder (development), private **S3-compatible** bucket (production) | Files are encrypted before they reach storage. |

---

## Project structure

```
Gaon sathi/
├── README.md                    ← you are here
├── .gitignore                   ← keeps .env, databases and evidence out of git
├── docs/
│   ├── SECURITY_AND_PRIVACY.md  ← threat model, privacy design, data retention, backups
│   ├── SECURITY_CHECKLIST.md    ← checklist with how each item was tested
│   └── DEPLOYMENT.md            ← production deployment guide
├── deploy/
│   ├── nginx.conf.example       ← HTTPS reverse proxy without IP logging
│   ├── gaon-saathi.service      ← systemd service (hardened)
│   ├── gaon-saathi-purge.*      ← daily retention purge timer
│   ├── postgres-setup.sql       ← least-privilege database roles
│   └── backup.sh                ← encrypted backups
├── backend/
│   ├── .env.example             ← all configuration options
│   ├── requirements*.txt
│   ├── alembic.ini, migrations/ ← database migrations
│   ├── app/
│   │   ├── main.py              ← FastAPI app, error handling, SPA serving
│   │   ├── config.py            ← settings from environment variables
│   │   ├── constants.py         ← categories, statuses, workflow transitions
│   │   ├── models.py            ← database tables (no reporter/user table!)
│   │   ├── schemas.py           ← input validation
│   │   ├── cli.py               ← management commands
│   │   ├── security/            ← crypto, passwords, sessions/CSRF/roles, rate limits, anti-spam, headers
│   │   ├── services/            ← complaints, evidence cleaning, storage, stats, demo data, retention
│   │   └── routers/             ← public API, admin auth, admin complaints, admin management
│   ├── tests/                   ← 82 automated tests (pytest)
│   └── e2e/run_e2e.py           ← real-browser end-to-end test
└── frontend/
    ├── package.json, vite.config.js, tailwind.config.js
    ├── public/favicon.svg       ← the Gaon Saathi logo
    └── src/
        ├── components/          ← Logo, header, footer, UI kit
        ├── pages/               ← public pages
        ├── admin/               ← admin dashboard (lazy-loaded)
        └── lib/                 ← API client, anti-spam solver, privacy helpers
```

---

## Quick start (local demo)

**You need:** Python 3.11 or newer and Node.js 20 or newer (Node 24 LTS recommended). On Windows, use PowerShell. Lines that differ on macOS and Linux are noted.

```powershell
# 1. Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
python -m app.cli init-env            # creates backend/.env with fresh random secrets
python -m app.cli migrate             # creates the database (SQLite by default)
python -m app.cli create-admin --username admin   # asks for a password (hidden)
python -m app.cli seed-demo           # optional: fictional DEMO DATA

# 2. Frontend (new terminal)
cd frontend
npm install
npm run build                         # backend serves the built site

# 3. Run
cd backend
python -m app.cli serve               # open http://127.0.0.1:8000
```

- Public site: <http://127.0.0.1:8000>
- Admin dashboard: <http://127.0.0.1:8000/admin>
- API docs (development only): <http://127.0.0.1:8000/api/docs>

For live-reload development, run `python -m app.cli serve --reload` and `npm run dev` together, then open <http://localhost:5173>. Vite forwards `/api` calls to the backend.

---

## Environment variables

All configuration comes from environment variables or `backend/.env`. See [`backend/.env.example`](backend/.env.example) for every option with comments. The most important are:

| Variable | Purpose |
|---|---|
| `APP_ENV` | `development`, `production` or `test`. Production enforces PostgreSQL and secure cookies. |
| `DATABASE_URL` | e.g. `postgresql+psycopg://gaon_app:PASSWORD@localhost:5432/gaon_saathi`. Defaults to a local SQLite file. |
| `SECRET_KEY` | At least 32 random characters. Used for HMAC of tracking codes, sessions and anti-spam challenges. |
| `DATA_ENCRYPTION_KEY` | Base64 of 32 random bytes. Encrypts complaint text and evidence. **Back it up securely: losing it makes data unreadable.** |
| `STORAGE_BACKEND` | `local` or `s3` (plus `S3_BUCKET`, `S3_REGION`, `S3_ENDPOINT_URL`). |
| `COOKIE_SECURE`, `HSTS_ENABLED` | Turn on when serving over HTTPS. |
| `TRUST_PROXY_HEADERS` | `true` only behind your own reverse proxy. |
| `CLAMAV_HOST` | Optional ClamAV daemon for malware scanning. |
| `SUPPORT_EMAIL`, `SUPPORT_PHONE` | Optional public contact shown on the Contact page. |

Secrets are **never** hard-coded. `python -m app.cli init-env` generates them, and `.gitignore` keeps `.env` out of git. The frontend contains no secrets.

---

## Database setup

**Development:** nothing to install. SQLite is used automatically (`backend/data/gaon_saathi.db`).

**PostgreSQL (recommended; required in production):**

1. Install PostgreSQL 14 or newer.
2. Edit the passwords in [`deploy/postgres-setup.sql`](deploy/postgres-setup.sql), then run `psql -U postgres -f deploy/postgres-setup.sql`. This creates:
   - `gaon_owner`, which owns the schema and is used only for migrations;
   - `gaon_app`, which can read and write rows but cannot change the schema.
3. Run migrations as the owner:

   ```powershell
   $env:DATABASE_URL="postgresql+psycopg://gaon_owner:OWNER_PASSWORD@localhost:5432/gaon_saathi"
   python -m app.cli migrate
   ```

4. Optional but recommended: make the audit log append-only. As `gaon_owner`, run `REVOKE UPDATE, DELETE ON admin_audit_logs FROM gaon_app;`
5. Put the **app** role in `.env`: `DATABASE_URL=postgresql+psycopg://gaon_app:APP_PASSWORD@localhost:5432/gaon_saathi`

---

## Running the backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.cli serve                  # http://127.0.0.1:8000, access logs disabled
python -m app.cli serve --reload         # auto-reload while developing
python -m app.cli check-config           # show non-secret configuration and warnings
```

Always start the server with `app.cli serve`, not plain `uvicorn`. It disables HTTP access logs, which would otherwise record visitor IP addresses.

## Running the frontend

```powershell
cd frontend
npm install
npm run dev        # development server on http://localhost:5173 (API proxied to :8000)
npm run build      # production build in frontend/dist (served by the backend)
npm test           # unit tests (Vitest)
```

---

## Creating the first administrator

There is **no public registration**. Create the first administrator on the server:

```powershell
cd backend
python -m app.cli create-admin --username asha --role admin
```

The password is typed into a hidden prompt, so it never appears in shell history or process lists. It must be at least 12 characters and not a common or easily guessed password. That administrator can then add more team members under **Settings → Team members**. New members get a temporary password and must change it at first login.

If someone is locked out or forgets their password, reset it with:

```powershell
python -m app.cli reset-password --username asha
```

---

## Demo data

```powershell
python -m app.cli seed-demo        # replaces existing demo data with ~36 fictional complaints
python -m app.cli clear-demo       # removes all demo data
```

- Every demo record is flagged in the database. Demo complaint IDs look like `GS-DEMO-XXXXXXXX`, descriptions start with `[DEMO DATA]`, and the dashboard shows a **DEMO** badge.
- The dashboard and complaint list have an **All data / Live only / Demo only** switch, so demo records never mix with real statistics unless you choose to include them.
- Demo complaints include realistic histories, verification notes, forwarding records and sample photos. The photos are generated images labelled "DEMO EVIDENCE".
- The seeder prints a few demo Complaint ID and Tracking Code pairs and writes all of them to `backend/data/demo-tracking-codes.txt`, so you can try the Track page.
- Administrators can also load or remove demo data from **Settings → Demo data**.

---

## Running the tests

```powershell
cd backend
python -m pytest                           # 82 backend tests (SQLite)
$env:TEST_DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/gaon_test"
python -m pytest                           # same tests against PostgreSQL (the database is wiped)

cd ..\frontend
npm test                                   # frontend unit tests

cd ..\backend
python e2e\run_e2e.py --screenshots ..\screenshots   # real-browser end-to-end test
```

The end-to-end test needs Microsoft Edge or Google Chrome installed (`E2E_BROWSER_CHANNEL=chrome` for Chrome). It starts an isolated server with a temporary database and drives the full journey: report with a photo, receipt, tracking, admin login, review, verification, request for more information, the reporter's reply, every admin page, mobile layout and logout. It **fails on any browser console error, page error or Content-Security-Policy violation**, and on any server log line containing client addresses or complaint text.

**What the backend tests cover:**
- submission and validation, random unique IDs, encrypted storage
- anti-spam: missing, tampered and replayed challenges, the honeypot, and rate limits
- evidence: EXIF/GPS removal, PNG text chunks, PDF JavaScript and metadata removal, video metadata removal, polyglot payloads, executables disguised as photos, wrong extensions, size and count limits, files encrypted on disk, admin-only access, video range requests
- tracking: correct and incorrect codes, no ID enumeration, no internal data leaking
- authentication: Argon2id, session tokens stored only as HMACs, cookie flags, lockout, CSRF, idle timeout, roles, forced password change, the last-admin safeguard
- workflow: allowed transitions only; Resolved needs a summary; Forwarded needs a forwarding record; an internal note is required; reporter information requests
- statistics: an empty database, and counts that match real rows
- CSV safety, deletion, retention purge, settings
- audit log free of sensitive text; application logs free of complaint text, codes and IPs; generic error messages
- demo data marking, separation and consistent workflow histories

All 82 tests pass on SQLite and on PostgreSQL 16, and the end-to-end browser test passes in Microsoft Edge.

---

## Deployment

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the full guide. It covers a Linux server with PostgreSQL, nginx + HTTPS, systemd, private S3 storage, backups and the retention timer. In short:

1. Create the PostgreSQL roles, set `APP_ENV=production`, and use strong secrets kept outside git.
2. `npm run build`, then `python -m app.cli migrate` as the owner role.
3. Run `python -m app.cli serve` under systemd, behind nginx with HTTPS (`COOKIE_SECURE=true`, `HSTS_ENABLED=true`).
4. Schedule `python -m app.cli purge-expired` daily and run encrypted backups.

---

## Security and privacy

See [`docs/SECURITY_AND_PRIVACY.md`](docs/SECURITY_AND_PRIVACY.md) for the design and [`docs/SECURITY_CHECKLIST.md`](docs/SECURITY_CHECKLIST.md) for the tested checklist. Highlights:

- **No reporter identity is collected.** There is no user table, no account, and no name, phone, email, Aadhaar or address field. IP addresses are not stored, and HTTP access logs are disabled.
- **Encryption:** AES-256-GCM for descriptions, notes, findings and evidence files. Tracking codes and session tokens are stored only as keyed HMACs.
- **Evidence:** the real file type is detected from content, dangerous formats are rejected, metadata is removed, original file names are discarded, optional ClamAV scanning, and files are served only to signed-in reviewers with a sandboxed CSP.
- **Web security:**
  - SQL injection: parameterised queries (SQLAlchemy)
  - XSS: React escaping plus a strict CSP with no inline scripts and no `eval`
  - CSRF: tokens plus SameSite=Strict cookies
  - clickjacking: `frame-ancestors 'none'`
  - security headers, request size limits, generic error messages
- **No third parties:** no analytics, no CDN fonts, no external CAPTCHA.

> **Honest limitation:** no system can guarantee complete anonymity. Text or media that reporters choose to share can identify them, as can their device, network or someone watching. Infrastructure such as hosting providers may briefly process connection data. The website says this clearly to users.

---

## Known limitations

These are explained in detail in the security documentation.

- **Malware scanning** works only when a ClamAV daemon is configured (`CLAMAV_HOST`). Otherwise evidence is marked "not virus scanned" in the dashboard. Photos are always fully re-encoded, which neutralises embedded payloads.
- **Video metadata** is removed with ffmpeg, which is bundled via `imageio-ffmpeg`. If ffmpeg is unavailable, videos are accepted but flagged "metadata may remain", and the reporter is told.
- **Supporting documents** are accepted as PDF only. Word and Excel files are rejected for safety, so users are asked to save them as PDF.
- **Rate limits** are in memory per process. Run a single worker, or replace them with a shared store such as Redis when scaling out.
- **S3 storage** is implemented, but in this project it was not tested against a live bucket.
- **Two-factor authentication for admins** is not yet implemented. It is recommended as a next step.
- The interface is English-only for now. Hindi and regional languages would be the most valuable next addition for villagers.
