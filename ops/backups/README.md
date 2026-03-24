# Postgres Backup Scripts

This directory contains backup and restore scripts for the Homelab Postgres database.

## Files

- `backup_postgres.sh`  
  Creates a timestamped `.sql` backup of the Postgres database on the internal backup drive.
  If the USB backup drive is mounted, it also copies the backup there.

- `restore_postgres.sh`  
  Restores a `.sql` backup into the running Postgres container.

- `backup_postgres.env.example`  
  Example machine-specific configuration file.

## Setup

Copy the example env file:

```bash
cp ops/backups/backup_postgres.env.example ops/backups/backup_postgres.env
