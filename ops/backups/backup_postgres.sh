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

INTERNAL_DIR="${INTERNAL_DIR:-/mnt/backup/postgres_backups}"
USB_DIR="${USB_DIR:-/mnt/usb-backup/postgres_backups}"

INTERNAL_MOUNT="${INTERNAL_MOUNT:-/mnt/backup}"
USB_MOUNT="${USB_MOUNT:-/mnt/usb-backup}"

CONTAINER_NAME="${CONTAINER_NAME:-homelab-postgres}"
DB_NAME="${DB_NAME:-homelab}"
DB_USER="${DB_USER:-homelab}"
DOCKER_BIN="${DOCKER_BIN:-/usr/bin/docker}"

INTERNAL_RETENTION_DAYS="${INTERNAL_RETENTION_DAYS:-7}"
USB_RETENTION_DAYS="${USB_RETENTION_DAYS:-14}"

# Ensure required commands exist
if [ ! -x "$DOCKER_BIN" ]; then
  echo "ERROR: docker binary not found at $DOCKER_BIN" >&2
  exit 1
fi

# Ensure internal backup drive is mounted
if ! mountpoint -q "$INTERNAL_MOUNT"; then
  echo "ERROR: Internal backup drive is not mounted at $INTERNAL_MOUNT" >&2
  exit 1
fi

mkdir -p "$INTERNAL_DIR"

BACKUP_FILE="$INTERNAL_DIR/${DB_NAME}_$TIMESTAMP.sql"

echo "Creating Postgres backup: $BACKUP_FILE"
"$DOCKER_BIN" exec "$CONTAINER_NAME" \
  pg_dump -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_FILE"

echo "Backup created successfully."

# Copy to USB drive if mounted
if mountpoint -q "$USB_MOUNT"; then
  mkdir -p "$USB_DIR"
  cp "$BACKUP_FILE" "$USB_DIR/"
  echo "Backup copied to USB drive at $USB_DIR"
else
  echo "USB backup drive not mounted at $USB_MOUNT. Skipping external copy."
fi

# Retention cleanup: internal
find "$INTERNAL_DIR" -type f -name "*.sql" -mtime +"$INTERNAL_RETENTION_DAYS" -delete

# Retention cleanup: USB
if mountpoint -q "$USB_MOUNT"; then
  find "$USB_DIR" -type f -name "*.sql" -mtime +"$USB_RETENTION_DAYS" -delete
fi

echo "Backup job complete."
