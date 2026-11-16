# Deploying Gaon Saathi

This guide deploys Gaon Saathi on a single Linux server (Ubuntu 24.04 LTS or similar) with PostgreSQL, nginx, HTTPS and systemd. A small VM with 2 vCPU, 2–4 GB RAM and a 40 GB disk is enough for a pilot. Choose a hosting region in India if you can.

> The application serves both the API and the built React site from one process, behind nginx. There is no separate frontend server.

## 1. Server preparation

```bash
sudo apt update && sudo apt install -y python3 python3-venv postgresql nginx certbot python3-certbot-nginx git gnupg
# Optional but recommended malware scanning:
sudo apt install -y clamav-daemon && sudo systemctl enable --now clamav-daemon
sudo adduser --system --group --home /opt/gaon-saathi gaonsaathi
```

Install Node.js 20 or newer to build the frontend (for example from nodejs.org), or build it on your own computer and copy `frontend/dist` to the server.

## 2. Get the code and build

```bash
sudo -u gaonsaathi -H bash
cd /opt/gaon-saathi
git clone <your-repository-url> .          # or copy the project files
cd frontend && npm ci && npm run build && cd ..
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt  # add -r requirements-s3.txt for S3 storage
```

## 3. Database (least privilege)

```bash
# Edit the two passwords in deploy/postgres-setup.sql first.
sudo -u postgres psql -f /opt/gaon-saathi/deploy/postgres-setup.sql
```

## 4. Configuration

```bash
cd /opt/gaon-saathi/backend
.venv/bin/python -m app.cli init-env        # generates SECRET_KEY and DATA_ENCRYPTION_KEY
chmod 600 .env
```

Edit `.env`:

```ini
APP_ENV=production
DATABASE_URL=postgresql+psycopg://gaon_app:APP_PASSWORD@127.0.0.1:5432/gaon_saathi
COOKIE_SECURE=true
HSTS_ENABLED=true
TRUST_PROXY_HEADERS=true
CLAMAV_HOST=127.0.0.1
CLAMAV_PORT=3310
# For private object storage instead of the local disk:
# STORAGE_BACKEND=s3
# S3_BUCKET=gaon-saathi-evidence
# S3_REGION=ap-south-1
```

**Back up `DATA_ENCRYPTION_KEY` and `SECRET_KEY` now**, somewhere separate from the server and from backups. Without `DATA_ENCRYPTION_KEY`, the stored data cannot be decrypted.

ClamAV listens on a Unix socket by default. To use TCP, set `TCPSocket 3310` and `TCPAddr 127.0.0.1` in `/etc/clamav/clamd.conf`.

## 5. Migrate and create the first administrator

```bash
DATABASE_URL=postgresql+psycopg://gaon_owner:OWNER_PASSWORD@127.0.0.1:5432/gaon_saathi .venv/bin/python -m app.cli migrate
sudo -u postgres psql -d gaon_saathi -c "REVOKE UPDATE, DELETE ON admin_audit_logs FROM gaon_app;"
.venv/bin/python -m app.cli create-admin --username <your-name> --role admin
.venv/bin/python -m app.cli check-config
```

Repeat the `migrate` command with the owner URL after every upgrade.

## 6. Service, HTTPS and timers

```bash
sudo cp /opt/gaon-saathi/deploy/gaon-saathi.service /etc/systemd/system/
sudo cp /opt/gaon-saathi/deploy/gaon-saathi-purge.service /opt/gaon-saathi/deploy/gaon-saathi-purge.timer /etc/systemd/system/
sudo mkdir -p /opt/gaon-saathi/backend/storage /opt/gaon-saathi/backend/data && sudo chown -R gaonsaathi: /opt/gaon-saathi/backend
sudo systemctl daemon-reload
sudo systemctl enable --now gaon-saathi gaon-saathi-purge.timer

sudo cp /opt/gaon-saathi/deploy/nginx.conf.example /etc/nginx/sites-available/gaon-saathi
# edit server_name and certificate paths, then:
sudo ln -s /etc/nginx/sites-available/gaon-saathi /etc/nginx/sites-enabled/
sudo certbot certonly --nginx -d your-domain.example
sudo nginx -t && sudo systemctl reload nginx
```

Run **one** application worker, which is what the provided unit does. Rate limits and anti-spam counters are kept in memory per process.

## 7. Backups

```bash
sudo install -m 600 /dev/null /root/.gaon-backup-pass && sudo nano /root/.gaon-backup-pass   # long random passphrase
sudo mkdir -p /var/backups/gaon && sudo chmod 700 /var/backups/gaon
# daily at 02:00 via root's crontab:
0 2 * * * BACKUP_PASSPHRASE_FILE=/root/.gaon-backup-pass /opt/gaon-saathi/deploy/backup.sh /var/backups/gaon
```

Copy the encrypted backups off the server, for example to a private bucket. Test a restore regularly (see `SECURITY_AND_PRIVACY.md` section 6).

## 8. After deployment

- Visit `https://your-domain/api/health`, which should return `{"status":"ok"}`.
- Check the headers: `curl -sI https://your-domain/ | grep -i -E "strict-transport|content-security|x-frame"`.
- Submit a test complaint, track it, review it in `/admin`, then delete it.
- Remove demo data: `python -m app.cli clear-demo`.
- Work through the "Before going live" list in `SECURITY_CHECKLIST.md`.

## Upgrading

```bash
cd /opt/gaon-saathi && git pull
cd frontend && npm ci && npm run build
cd ../backend && .venv/bin/pip install -r requirements.txt
DATABASE_URL=<owner-url> .venv/bin/python -m app.cli migrate
sudo systemctl restart gaon-saathi
```

## Notes on other platforms

Any platform that runs a Python web process with PostgreSQL works, such as a managed VM, Render, Railway or AWS. If you use one, you must:

- build the frontend during the build step,
- run `python -m app.cli serve --host 0.0.0.0 --port $PORT` (this keeps access logs off),
- use a managed PostgreSQL database and private S3-compatible storage (local disks on many platforms are temporary),
- check the platform's own request logging and IP retention, disable or minimise it, and document what remains,
- set `TRUST_PROXY_HEADERS=true` only if the platform's proxy appends the client address to `X-Forwarded-For`.
