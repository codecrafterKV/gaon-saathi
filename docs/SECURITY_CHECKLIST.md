# Gaon Saathi — Security Checklist

Status of each requirement and how it was verified.

**Verification key**

| Code | How it was verified |
|---|---|
| **T** | automated backend test (`backend/tests`, 82 tests, run on SQLite and PostgreSQL 16) |
| **E** | end-to-end browser test (`backend/e2e/run_e2e.py`, Microsoft Edge) |
| **M** | manual verification during development |
| **D** | documented deployment step (the operator must do it) |

## Anonymity and privacy

| # | Requirement | Status | Verified |
|---|---|---|---|
| 1 | No name, phone, email, Aadhaar, address, photo or account requested | Done | T (`test_no_personal_data_columns`), E |
| 2 | No user account system for reporters | Done | Design (no table) |
| 3 | No IP addresses stored; HTTP access logs disabled | Done | T (`test_logs_contain_no_complaint_content`), E (server log check) |
| 4 | No analytics or third-party tracking; fonts self-hosted | Done | M (build output, no external requests), CSP `connect-src 'self'` |
| 5 | Evidence never on public URLs | Done | T (`test_evidence_requires_admin_login`) |
| 6 | Complaint info restricted to authorised admins (RBAC) | Done | T (`test_role_based_access`, `test_viewer_role_cannot_open_evidence`) |
| 7 | Encryption in storage (AES-256-GCM, text and files) | Done | T (`test_description_is_encrypted_at_rest`, `test_upload_through_api_is_encrypted_and_private`) |
| 8 | Encryption in transit (HTTPS) | Deployment | D (nginx example, `COOKIE_SECURE`, HSTS) |
| 9 | No complaint text, evidence or codes in logs | Done | T, E |
| 10 | EXIF/GPS removed from photos (client and server) | Done | T (`test_photo_exif_and_gps_are_removed`), E ("Hidden location data removed") |
| 11 | Metadata removed from videos and PDFs | Done | T (`test_video_metadata_removed`, `test_pdf_javascript_and_metadata_removed`) |
| 12 | Warnings not to include identifying info | Done | E (upload warning, personal-info detector) |
| 13 | Original file names discarded | Done | T |
| 14 | No claim of guaranteed anonymity | Done | M (Home, FAQ, Privacy) |

## Identifiers and tracking

| # | Requirement | Status | Verified |
|---|---|---|---|
| 15 | Complaint IDs random (CSPRNG), unique, not sequential | Done | T (`test_ids_are_unique_and_random`) |
| 16 | Secret tracking token shown once, stored only as a hash (HMAC) | Done | T, E (refresh shows nothing) |
| 17 | No enumeration: same error for wrong ID or wrong token | Done | T (`test_wrong_token_gives_generic_404`) |
| 18 | Public view limited to allowed fields | Done | T (exact field set), T (`test_internal_notes_never_reach_public_view`) |

## Authentication and sessions

| # | Requirement | Status | Verified |
|---|---|---|---|
| 19 | No public admin registration; CLI for the first admin | Done | Design, M |
| 20 | Argon2id password hashing | Done | T (`test_password_is_hashed_with_argon2id`) |
| 21 | Password policy (12+ characters, common passwords blocked) | Done | T |
| 22 | Login lockout and rate limiting; generic errors | Done | T (`test_account_lockout_after_failures`, `test_wrong_password_and_unknown_user_same_message`) |
| 23 | HttpOnly, SameSite=Strict, Secure (production) session cookie | Done | T (`test_login_sets_secure_session_cookie`) |
| 24 | Session tokens stored hashed; idle and absolute expiry; logout revokes | Done | T |
| 25 | CSRF protection on all admin state changes | Done | T (`test_csrf_token_required_for_changes`) |
| 26 | Forced password change for temporary passwords | Done | T |
| 27 | The last admin cannot be removed | Done | T |
| 28 | Two-factor authentication | **Not implemented** | Recommended next step |

## Web application security

| # | Requirement | Status | Verified |
|---|---|---|---|
| 29 | SQL injection: parameterised queries, LIKE escaping | Done | T (`test_list_search_filters_and_pagination` with `%`) |
| 30 | XSS: React escaping, strict CSP (no inline/eval scripts) | Done | T (HTML stored as text), E (no CSP violations; CSP blocked `eval`) |
| 31 | Input validation and normalisation | Done | T (`test_required_fields_and_validation`, `test_control_characters_are_removed`) |
| 32 | Validation errors do not echo input | Done | T |
| 33 | Security headers (CSP, XFO, nosniff, Referrer, Permissions, COOP, CORP, no-store) | Done | T (`test_security_headers`) |
| 34 | Clickjacking protection | Done | T (`frame-ancestors 'none'`, `X-Frame-Options: DENY`) |
| 35 | Request size limits | Done | T (`test_request_body_limit`) |
| 36 | Generic error handling | Done | T (`test_unhandled_errors_are_generic`) |
| 37 | API docs disabled in production; unknown API routes 404 | Done | T |
| 38 | CSV formula injection prevented | Done | T (`test_csv_exports_are_safe`) |

## File uploads

| # | Requirement | Status | Verified |
|---|---|---|---|
| 39 | Server-side type validation by content (magic bytes) | Done | T (parametrised dangerous-file tests) |
| 40 | Executables and dangerous formats rejected | Done | T (exe, disguised exe, html, svg, docx, zip, js) |
| 41 | Size and count limits | Done | T (`test_too_many_files_rejected`, `test_oversized_file_rejected`) |
| 42 | Polyglot / appended payloads neutralised | Done | T (`test_polyglot_payload_is_dropped`) |
| 43 | Private, encrypted storage | Done | T |
| 44 | Malware scanning (ClamAV) | **Optional** | Implemented (clamd INSTREAM); needs `CLAMAV_HOST`. Not tested against a live ClamAV here. |
| 45 | Failed uploads leave no partial complaint or files | Done | T (`test_failed_upload_does_not_create_complaint`) |

## Anti-spam

| # | Requirement | Status | Verified |
|---|---|---|---|
| 46 | Proof-of-work challenge (signed, expiring, single-use) | Done | T (missing, tampered and replayed challenges) |
| 47 | Honeypot | Done | T |
| 48 | Rate limiting without storing IPs | Done | T (`test_rate_limit`) |

## Workflow integrity

| # | Requirement | Status | Verified |
|---|---|---|---|
| 49 | Every status change recorded with time and internal explanation | Done | T |
| 50 | Only allowed transitions | Done | T (`test_invalid_transition_rejected`) |
| 51 | Resolved requires a resolution update | Done | T |
| 52 | Forwarded requires a recorded submission or acknowledgement | Done | T (`test_cannot_mark_forwarded_without_forwarding_record`, `test_forwarding_requires_acknowledgement_details`) |
| 53 | Internal notes separate from public messages | Done | T, E |
| 54 | Audit log of admin actions, free of sensitive text | Done | T (`test_audit_log_has_no_sensitive_text`) |

## Operations

| # | Requirement | Status | Verified |
|---|---|---|---|
| 55 | Secrets only in environment / `.env`, git-ignored | Done | M (`.gitignore`, `init-env`), D |
| 56 | Restricted database permissions | Done | M (verified on PostgreSQL 16: app role cannot run DDL or change the audit log) |
| 57 | Data retention and deletion | Done | T (`test_retention_purge`, `test_delete_complaint_removes_files`) |
| 58 | Encrypted backups and restore procedure | Documented | D (`deploy/backup.sh`, SECURITY_AND_PRIVACY.md section 6) |
| 59 | HTTPS / HSTS / secure cookies | Deployment | D |
| 60 | Dependency updates | Ongoing | D (run `pip list --outdated` and `npm audit` regularly) |

## Before going live

- [ ] `APP_ENV=production`, PostgreSQL with least-privilege roles, `check-config` shows no problems
- [ ] HTTPS certificate installed; `COOKIE_SECURE=true`, `HSTS_ENABLED=true`
- [ ] `TRUST_PROXY_HEADERS=true` only with the provided nginx config
- [ ] `.env` mode 600, owned by the service user; secrets backed up separately
- [ ] ClamAV installed and `CLAMAV_HOST` set (recommended)
- [ ] Hosting/CDN access logs disabled or minimised and their retention documented
- [ ] Daily purge timer and encrypted backups enabled; one restore tested
- [ ] Demo data removed (`python -m app.cli clear-demo`)
- [ ] All admin accounts use strong, unique passwords; unused accounts deactivated
