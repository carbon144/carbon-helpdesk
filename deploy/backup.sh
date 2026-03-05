#!/bin/bash
# PostgreSQL backup script for Carbon Helpdesk
# Run via cron: 0 3 * * * /opt/carbon-helpdesk/deploy/backup.sh

set -e

BACKUP_DIR="/opt/carbon-helpdesk/backups"
CONTAINER_NAME="carbon-db"
DB_NAME="carbon_helpdesk"
DB_USER="carbon"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/helpdesk_$TIMESTAMP.sql.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Dump and compress
echo "[$(date)] Starting backup..."
docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"

# Verify backup
if [ -s "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "[$(date)] Backup completed: $BACKUP_FILE ($SIZE)"
else
    echo "[$(date)] ERROR: Backup file is empty!"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Clean old backups
find "$BACKUP_DIR" -name "helpdesk_*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "[$(date)] Old backups cleaned (retention: ${RETENTION_DAYS} days)"

# List current backups
echo "[$(date)] Current backups:"
ls -lh "$BACKUP_DIR"/helpdesk_*.sql.gz 2>/dev/null || echo "  No backups found"
