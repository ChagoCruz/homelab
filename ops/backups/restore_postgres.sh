#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load optional local env file if present
if [ -f "$SCRIPT_DIR/backup_postgres.env" ]; then
  set -a
  . "$SCRIPT_DIR/backup_postgres.env"
  set +a
fi

DOCKER_BIN="${DOCKER_BIN:-/usr/bin/docker}"
CONTAINER_NAME="${CONTAINER_NAME:-homelab-postgres}"
DB_NAME="${DB_NAME:-homelab}"
DB_USER="${DB_USER:-homelab}"

if [ $# -ne 1 ]; then
  echo "Usage: $0 /full/path/to/backup.sql" >&2
  exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "ERROR: Backup file not found: $BACKUP_FILE" >&2
  exit 1
fi

if [ ! -x "$DOCKER_BIN" ]; then
  echo "ERROR: docker binary not found at $DOCKER_BIN" >&2
  exit 1
fi

echo "Restoring database '$DB_NAME' from $BACKUP_FILE"

cat "$BACKUP_FILE" | "$DOCKER_BIN" exec -i "$CONTAINER_NAME" \
  psql -U "$DB_USER" -d "$DB_NAME"

echo "Restore complete."
