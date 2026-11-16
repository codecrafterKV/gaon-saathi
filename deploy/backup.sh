#!/usr/bin/env bash
# Encrypted backup of the Gaon Saathi database and evidence store.
#
# Evidence files and complaint text are already encrypted by the application,
# but the backup is encrypted AGAIN with a separate passphrase (GPG, AES-256)
# so a stolen backup is useless on its own. Store DATA_ENCRYPTION_KEY and the
# backup passphrase separately from the backups (e.g. a password manager).
#
# Usage: BACKUP_PASSPHRASE_FILE=/root/.gaon-backup-pass ./backup.sh /var/backups/gaon
set -euo pipefail

DEST="${1:?destination folder required}"
APP=/opt/gaon-saathi/backend
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
umask 077

# shellcheck disable=SC1091
set -a; source "$APP/.env"; set +a
PGURL="${DATABASE_URL/postgresql+psycopg/postgresql}"

pg_dump --format=custom --no-owner --file "$WORK/db.dump" "$PGURL"
tar -C "$APP" -cf "$WORK/evidence.tar" storage/evidence
tar -C "$WORK" -czf "$WORK/gaon-$STAMP.tar.gz" db.dump evidence.tar
gpg --batch --yes --symmetric --cipher-algo AES256 \
    --passphrase-file "${BACKUP_PASSPHRASE_FILE:?}" \
    --output "$DEST/gaon-$STAMP.tar.gz.gpg" "$WORK/gaon-$STAMP.tar.gz"

# Keep 14 days of backups (backups must also respect the retention policy).
find "$DEST" -name 'gaon-*.tar.gz.gpg' -mtime +14 -delete
echo "Backup written: $DEST/gaon-$STAMP.tar.gz.gpg"
