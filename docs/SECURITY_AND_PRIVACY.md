# Gaon Saathi — Security and Privacy Design

This document explains how Gaon Saathi protects the people who report problems, the information they share, and the integrity of the complaint process. It is written for the team, reviewers and anyone deploying the platform.

---

## 1. Who and what we protect

| Asset | Why it matters |
|---|---|
| **Reporter identity** | Exposure can lead to threats, violence or social pressure in the village. This is the most important asset. |
| **Complaint content and evidence** | It can indirectly identify the reporter, and it can also be misused against the people it describes. |
| **Integrity of the workflow** | False "forwarded" or "resolved" claims would destroy trust. |
| **Admin accounts** | They can read every complaint. |

**Threats considered**
- A powerful local person trying to learn who reported them, by guessing tracking codes, getting access to the database, logs, backups or an admin account, or by asking an insider.
- Mass spam or fake complaints to bury real ones.
- Malicious uploads aimed at the team's computers.
- A stolen database, server disk or backup.
- Ordinary web attacks: XSS, CSRF, SQL injection, clickjacking and brute-force login.

---

## 2. Privacy by design

### 2.1 Data we never collect
- No reporter accounts, profiles, names, phone numbers, emails, Aadhaar numbers, home addresses or photos. **The database has no table or column for reporters.** An automated test (`test_no_personal_data_columns`) fails if such a column is ever added.
- **No IP addresses.** HTTP access logs are disabled (`python -m app.cli serve` sets `access_log=False`). The nginx example also disables access logging, and no database column holds an IP address.
- No user-agent or device fingerprint, no cookies for visitors (only admins get a session cookie), no analytics, no advertising and no third-party scripts.
- **Fonts are self-hosted**, because loading Google Fonts would send every visitor's IP to Google.
- **Original file names are discarded.** Phone file names can include a name or phone number, so evidence is stored as `evidence-1.jpg`, `evidence-2.pdf` and so on.

### 2.2 Data we do store

| Data | Protection |
|---|---|
| Category, village, district, state | Plain text, needed for filtering and statistics. This is the location of the *problem*, not of the person. |
| Description, approximate location, internal notes, verification findings, resolution summary, forwarding acknowledgement details | **AES-256-GCM encrypted** in the database (`EncryptedText` column type). |
| Evidence files | Sanitised, then **AES-256-GCM encrypted** before being written to storage. The key is bound to the random storage key (AAD). |
| Tracking code | Only a **keyed HMAC-SHA256** is stored, never the code itself. |
| Complaint ID | Random, not secret by itself. Viewing status requires the tracking code as well. |
| Timestamps | Submission and status changes, needed for the workflow and statistics. Shown publicly only as dates. |

Keys are derived with HKDF from two separate secrets:
- `DATA_ENCRYPTION_KEY` derives the field encryption key and the evidence encryption key.
- `SECRET_KEY` derives the tracking-code HMAC key, the session HMAC key and the anti-spam signing key.

A leaked database alone reveals neither complaint text nor tracking codes.

### 2.3 Metadata removal from evidence

| Type | What happens |
|---|---|
| Photos (JPG/PNG/WebP) | **On the phone:** the browser redraws the photo on a canvas, which removes EXIF and GPS data before upload and shrinks large photos for slow networks. **On the server:** the image is decoded, rotated upright, and rebuilt from raw pixels (`Image.frombytes`). No EXIF, GPS, XMP, ICC or PNG text chunks survive, and data appended to the file (polyglots) is discarded. |
| Videos (MP4/MOV/3GP/WebM) | Re-muxed with ffmpeg without global or stream metadata, chapters or data tracks such as GPS tracks. If ffmpeg is unavailable, the file is kept, flagged "metadata may remain", and the reporter is told. |
| PDF | Rebuilt page by page with pypdf. This drops document metadata (author and so on), JavaScript, open actions, embedded files and launch/submit actions in annotations. Encrypted PDFs are rejected. |

**Limits:** visible content such as faces, voices, house fronts or handwriting cannot be removed automatically. The form warns users about this at the upload step.

### 2.4 Tracking without accounts
- **Complaint ID:** `GS-YYYY-` plus 8 random characters from a 32-symbol alphabet (40 bits).
- **Tracking code:** 16 random characters (80 bits), shown once and stored only as an HMAC.
- Both come from Python's `secrets` CSPRNG. The alphabet has no 0/O or 1/I, so codes can be copied by hand. Lookups compare in constant time.
- A wrong ID and a wrong code return the **same message**, so the existence of a complaint ID cannot be confirmed. Lookups are rate limited.
- The public view returns **only** the ID, category, dates, status, progress message and status timeline. It never returns the description, location detail, evidence, notes or admin names. A test asserts the exact set of returned fields.
- The success page keeps the codes only in memory and removes them from browser history state, so they are not shown again after a refresh on a shared phone.

### 2.5 Asking for more information without contact details
The team cannot contact reporters. Instead, an admin can **Request more information**, and the reporter sees the request on the Track page. They can add text or files there, proving ownership with the tracking code. This is protected by the same anti-spam checks, and their identity is still never collected.

### 2.6 Honest communication
The interface never promises "complete anonymity". The homepage, FAQ and Privacy Policy explain the remaining risks: what users write or upload, their device or network, people around them, and hosting infrastructure.

---

## 3. Application security

### 3.1 Administrator authentication
- **No public registration.** The first admin is created with the CLI using a hidden password prompt. Further admins are created by administrators and must change their temporary password at first login.
- **Passwords:** Argon2id (argon2-cffi, RFC 9106 parameters) with automatic rehashing when parameters change. The policy requires at least 12 characters, blocks common passwords, rejects passwords containing the username, and requires a minimum number of distinct characters.
- **Login protection:**
  - per-account lockout: 5 failures lock the account for 15 minutes
  - per-client rate limit
  - the same error message for an unknown user, a wrong password and a locked account
  - a dummy hash check for unknown users, to equalise timing
- **Sessions:**
  - a 256-bit random token in an `HttpOnly`, `SameSite=Strict` cookie, which is `Secure` and `__Host-` prefixed in production
  - the server stores only an HMAC of the token
  - 30 minutes idle timeout and 8 hours maximum lifetime
  - logout revokes the session server-side; password changes and admin deactivation revoke the other sessions
- **CSRF:** every state-changing admin request requires an `X-CSRF-Token` header equal to an HMAC of the session token, on top of SameSite=Strict cookies and same-origin JSON requests.
- **Role-based access:**

  | Role | Access |
  |---|---|
  | `admin` | Everything, including users, settings, audit log, deletion and demo data |
  | `reviewer` | Complaint workflow, evidence, authorities, exports |
  | `viewer` | Read-only. Cannot open evidence or change anything. |

  Roles are enforced on the server for every endpoint. The last active administrator cannot be demoted or deactivated.

### 3.2 Input, output and injection
- All input is validated with Pydantic: types, lengths, allowed values, a state list and category list, and Unicode normalisation. Control characters and bidirectional-override characters are removed.
- **SQL injection:** only SQLAlchemy parameterised queries are used. LIKE wildcards in search are escaped.
- **XSS:**
  - React escapes all output, and the API never returns HTML.
  - Strict CSP: `script-src 'self'` with no inline scripts and no `eval`. The end-to-end test confirms no violations, and it confirmed that the CSP blocks `eval`.
  - `assetsInlineLimit: 0` keeps the build free of `data:` scripts and fonts.
- **CSV injection:** exported cells starting with `= + - @`, a tab or a carriage return are prefixed with `'`.
- **Validation errors** never echo the submitted values back.

### 3.3 File upload security
1. A request body limit is enforced before parsing (413), with per-type file limits, a file count limit, a total size limit, and a per-complaint evidence cap.
2. An extension allow-list, **plus content sniffing (magic bytes)**: the detected type must match the extension family. Executables, scripts, HTML, SVG, archives, Office files and HEIC are rejected.
3. Decompression-bomb protection (60 MP pixel cap) and a PDF page cap.
4. Sanitisation (see 2.3) and an optional **ClamAV** scan, where infected files are rejected.
5. Encrypted storage under random keys, outside any web root. Files are never available through a public URL.
6. Evidence is served only through an authenticated, role-checked endpoint with:
   - `Content-Security-Policy: default-src 'none'; sandbox`
   - `X-Content-Type-Options: nosniff`
   - `Cache-Control: private, no-store`
   - PDFs as attachments
   - range support for video

   Every view is written to the audit log.

### 3.4 Anti-spam
- **Proof-of-work.** The server issues an HMAC-signed challenge. The browser finds a nonce so that SHA-256 has 16 leading zero bits (about 65,000 hashes, under a second on a phone, computed while the form is being filled). Challenges expire, cannot be used within 3 seconds, and are **single-use**: they are recorded in `spent_challenges`, and replays are rejected.
- A **honeypot** field.
- **Privacy-preserving rate limits.** The client address is turned into an HMAC with a random in-memory key that rotates every 24 hours. Only timestamps are kept, only in memory, and never written anywhere. Behind a proxy, only the address appended by our own proxy is used, never client-supplied values.
- No third-party CAPTCHA, so no visitor data is shared.

### 3.5 HTTP security headers
Every response carries:
- `Content-Security-Policy` (strict, with `frame-ancestors 'none'`)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy` (camera, microphone, geolocation and others disabled)
- `Cross-Origin-Opener-Policy` and `Cross-Origin-Resource-Policy: same-origin`
- `Cache-Control: no-store` on all API responses
- optional `Strict-Transport-Security` (`HSTS_ENABLED=true`)

The uvicorn `Server` header is removed, and API docs are disabled outside development.

### 3.6 Errors and logging
- Unexpected errors return a generic message. The log records **only the exception type and code location**, never the exception message, which could contain data.
- Application logs never contain request bodies, complaint text, tracking codes, IP addresses or user agents. Tests and the end-to-end run verify this.

### 3.7 Audit log
The audit log records logins (successful, failed and locked), logouts, password changes, complaint views, status changes, notes, verification, forwarding, information requests, **evidence views**, exports, deletions, user changes, settings changes, purges and demo-data actions. It stores the actor, action, target reference and non-sensitive details only. With the recommended PostgreSQL grants, the application **cannot modify or delete** audit entries (verified).

### 3.8 Workflow integrity
- Status changes follow an explicit transition map. Every change needs an internal explanation and is recorded in the status history with its timestamp and author.
- **Forwarded to Relevant Authority** is only possible through *Record forwarding*. That requires an authority, a channel, a submission date (not in the future) and a reference number or submission details. A complaint must be reviewed before it can be forwarded.
- **Resolved** requires a resolution summary of at least 20 characters.
- Public messages are kept separate from internal notes. The admin sees a "what the reporter sees" preview.

---

## 4. Infrastructure

- **HTTPS only** in production. Configure `COOKIE_SECURE=true` and `HSTS_ENABLED=true` (see `deploy/nginx.conf.example`).
- **Database least privilege:** see `deploy/postgres-setup.sql`. The app role can only read and write rows; schema changes need the separate owner role. This was verified against PostgreSQL 16.
- **Secrets** live only in environment variables or `.env`. Restrict `.env` to the service user (mode 600), never commit it (`.gitignore`), and never put secrets in frontend code.
- **Evidence storage:** the local folder lives outside the web root with mode 600 files. For S3, use a private bucket with "Block all public access" and server-side encryption. Objects are already encrypted by the app.
- **Infrastructure-level IP processing that cannot be fully disabled:**
  - Every TCP connection necessarily exposes the client IP to the network stack, the reverse proxy and any hosting or CDN provider.
  - The application uses it only transiently, as an in-memory HMAC for rate limiting.
  - Hosting providers, DDoS protection services and load balancers may keep their own connection logs. Choose providers carefully, disable their access logging where possible, and document their retention in the deployment record.
  - The nginx example writes no access log, and its error log level is `crit`.

---

## 5. Data retention and deletion

- **Finished complaints** (resolved, rejected, closed) are permanently deleted, including evidence files, after the retention period: 365 days by default, configurable from 30 to 3650 days in **Settings**. Run `python -m app.cli purge-expired` daily (`deploy/gaon-saathi-purge.timer`) or click *Run purge now*.
- Admins can delete individual complaints, for example spam or abusive content. This needs a reason and the complaint ID typed as confirmation, and it is audited.
- **Spent anti-spam challenges** are deleted automatically after expiry.
- **In-memory rate-limit data** expires within hours and is wiped on restart.
- **Admin sessions** expire after 8 hours at most.
- **Audit logs** are kept as an accountability record. They contain no complaint content.
- **Backups** must follow the same policy. `deploy/backup.sh` keeps 14 days of backups.

---

## 6. Backup and recovery

1. `deploy/backup.sh` dumps PostgreSQL (`pg_dump --format=custom`) and the encrypted evidence folder. It encrypts the bundle again with GPG (AES-256) using a passphrase file.
2. Store **`DATA_ENCRYPTION_KEY`, `SECRET_KEY` and the backup passphrase separately** from the backups, for example in a password manager held by two trusted team members. Without `DATA_ENCRYPTION_KEY`, complaints and evidence cannot be decrypted.
3. **Restore:**
   ```bash
   gpg --decrypt gaon-<stamp>.tar.gz.gpg > gaon.tar.gz
   tar -xzf gaon.tar.gz
   pg_restore --clean --no-owner -d "$DATABASE_URL" db.dump
   tar -C /opt/gaon-saathi/backend -xf evidence.tar
   ```
   Then restart the service with the same `.env` secrets.
4. Test a restore at least every quarter on a separate machine, then securely delete the test copy.

**Key rotation:** encrypted values carry a version prefix (`v1:` / `GSE1`) to allow future re-encryption. A rotation tool is not included yet. Until then, keep keys stable and well protected.

---

## 7. Incident response (short)
1. Revoke access: deactivate affected admins in Settings, which revokes their sessions. If server secrets may have leaked, rotate `SECRET_KEY`. This logs everyone out and invalidates tracking codes, so communicate carefully.
2. Preserve the audit log and system logs. Review `evidence.viewed`, `export.*` and `complaint.viewed` entries.
3. Patch, restore from a clean backup if needed, and document what happened.
4. Because reporters cannot be contacted, publish a notice on the website if their data may have been affected.
