#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load optional local env file if present
if [ -f "$SCRIPT_DIR/backup_postgres.env" ]; then
  set -a
  . "$SCRIPT_DIR/backup_postgres.env"
  set +a
fi

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")

PRIMARY_DIR="${PRIMARY_DIR:-/mnt/storage/postgres_backups}"
SECONDARY_DIR="${SECONDARY_DIR:-/mnt/backup/postgres_backups}"

PRIMARY_MOUNT="${PRIMARY_MOUNT:-/mnt/storage}"
SECONDARY_MOUNT="${SECONDARY_MOUNT:-/mnt/backup}"

CONTAINER_NAME="${CONTAINER_NAME:-homelab-postgres}"
DB_NAME="${DB_NAME:-homelab}"
DB_USER="${DB_USER:-homelab}"
DOCKER_BIN="${DOCKER_BIN:-/usr/bin/docker}"

PRIMARY_RETENTION_DAYS="${INTERNAL_RETENTION_DAYS:-7}"
SECONDARY_RETENTION_DAYS="${USB_RETENTION_DAYS:-14}"

# Ensure required commands exist
if [ ! -x "$DOCKER_BIN" ]; then
  echo "ERROR: docker binary not found at $DOCKER_BIN" >&2
  exit 1
fi

# Ensure internal backup drive is mounted
if ! mountpoint -q "$PRIMARY_MOUNT"; then
  echo "ERROR: Internal backup drive is not mounted at $PRIMARY_MOUNT" >&2
  exit 1
fi

mkdir -p "$PRIMARY_DIR"

BACKUP_FILE="$PRIMARY_DIR/${DB_NAME}_$TIMESTAMP.sql"

echo "Creating Postgres backup: $BACKUP_FILE"
"$DOCKER_BIN" exec "$CONTAINER_NAME" \
  pg_dump -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_FILE"

echo "Backup created successfully."

# Copy to USB drive if mounted
if mountpoint -q "$SECONDARY_MOUNT"; then
  mkdir -p "$SECONDARY_DIR"
  cp "$BACKUP_FILE" "$SECONDARY_DIR/"
  echo "Backup copied to USB drive at $SECONDARY_DIR"
else
  echo "USB backup drive not mounted at $SECONDARY_MOUNT. Skipping external copy."
fi

# Retention cleanup: primary
find "$PRIMARY_DIR" -type f -name "*.sql" -mtime +"$PRIMARY_RETENTION_DAYS" -delete

# Retention cleanup: USB
if mountpoint -q "$SECONDARY_MOUNT"; then
  find "$SECONDARY_DIR" -type f -name "*.sql" -mtime +"$SECONDARY_RETENTION_DAYS" -delete
fi

echo "Backup job complete."
