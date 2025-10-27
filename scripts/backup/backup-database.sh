#!/bin/bash
#
# Database Backup Script
# Creates compressed backups of PostgreSQL database
#
# Usage:
#   ./backup-database.sh [backup_name]
#
# Environment Variables:
#   BACKUP_DIR     - Directory to store backups (default: /opt/neurocore/backups/database)
#   BACKUP_RETAIN  - Number of backups to retain (default: 10)
#   DB_CONTAINER   - Database container name (default: neurocore_postgres)
#   DB_NAME        - Database name (default: neurosurgery_kb)
#   DB_USER        - Database user (default: neurosurgery_admin)
#

set -euo pipefail

# ==================== Configuration ====================

BACKUP_DIR="${BACKUP_DIR:-/opt/neurocore/backups/database}"
BACKUP_RETAIN="${BACKUP_RETAIN:-10}"
DB_CONTAINER="${DB_CONTAINER:-neurocore_postgres}"
DB_NAME="${DB_NAME:-neurosurgery_kb}"
DB_USER="${DB_USER:-neurosurgery_admin}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_NAME="${1:-backup-${TIMESTAMP}}"
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.sql.gz"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ==================== Functions ====================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ==================== Pre-flight Checks ====================

log_info "Starting database backup..."

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    log_error "Database container '${DB_CONTAINER}' is not running"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Check disk space (require at least 1GB free)
AVAILABLE_SPACE=$(df "${BACKUP_DIR}" | tail -1 | awk '{print $4}')
if [ "${AVAILABLE_SPACE}" -lt 1048576 ]; then
    log_error "Insufficient disk space in ${BACKUP_DIR}"
    log_error "Available: ${AVAILABLE_SPACE}KB, Required: 1GB"
    exit 1
fi

log_info "Pre-flight checks passed"

# ==================== Create Backup ====================

log_info "Creating backup: ${BACKUP_FILE}"
log_info "Database: ${DB_NAME}"
log_info "User: ${DB_USER}"

# Create backup with pg_dump
# Options:
#   -U: database user
#   -F c: custom format (compressed and supports parallel restore)
#   --verbose: detailed output
#   --clean: include DROP commands before CREATE
#   --if-exists: use IF EXISTS for DROP commands
#   --create: include CREATE DATABASE command
#   --no-owner: don't output ownership commands
#   --no-acl: don't output ACL commands

if docker exec -t "${DB_CONTAINER}" pg_dump \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --verbose \
    --clean \
    --if-exists \
    --no-owner \
    --no-acl \
    2>&1 | gzip > "${BACKUP_FILE}"; then

    log_info "Backup created successfully"
else
    log_error "Backup failed"
    rm -f "${BACKUP_FILE}"
    exit 1
fi

# ==================== Verify Backup ====================

log_info "Verifying backup..."

# Check if backup file exists and is not empty
if [ ! -f "${BACKUP_FILE}" ]; then
    log_error "Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

BACKUP_SIZE=$(stat -f%z "${BACKUP_FILE}" 2>/dev/null || stat -c%s "${BACKUP_FILE}" 2>/dev/null)
if [ "${BACKUP_SIZE}" -lt 1024 ]; then
    log_error "Backup file is too small (${BACKUP_SIZE} bytes), likely failed"
    exit 1
fi

log_info "Backup size: $(numfmt --to=iec-i --suffix=B ${BACKUP_SIZE} 2>/dev/null || echo "${BACKUP_SIZE} bytes")"

# Test backup integrity
if gzip -t "${BACKUP_FILE}"; then
    log_info "Backup integrity verified"
else
    log_error "Backup integrity check failed"
    exit 1
fi

# ==================== Create Metadata ====================

METADATA_FILE="${BACKUP_FILE}.meta"
cat > "${METADATA_FILE}" << EOF
Backup Metadata
================
Backup File: ${BACKUP_FILE}
Database: ${DB_NAME}
User: ${DB_USER}
Container: ${DB_CONTAINER}
Created: $(date -Iseconds)
Size: ${BACKUP_SIZE} bytes
Hostname: $(hostname)
EOF

log_info "Metadata created: ${METADATA_FILE}"

# ==================== Cleanup Old Backups ====================

log_info "Cleaning up old backups (keeping last ${BACKUP_RETAIN})..."

# List backups sorted by modification time, keep newest N
OLD_BACKUPS=$(ls -t "${BACKUP_DIR}"/backup-*.sql.gz 2>/dev/null | tail -n +$((BACKUP_RETAIN + 1)) || true)

if [ -n "${OLD_BACKUPS}" ]; then
    while IFS= read -r OLD_BACKUP; do
        log_info "Removing old backup: $(basename "${OLD_BACKUP}")"
        rm -f "${OLD_BACKUP}" "${OLD_BACKUP}.meta"
    done <<< "${OLD_BACKUPS}"
else
    log_info "No old backups to remove"
fi

# ==================== Summary ====================

log_info "Backup completed successfully!"
log_info "Backup location: ${BACKUP_FILE}"
log_info "Total backups: $(ls -1 "${BACKUP_DIR}"/backup-*.sql.gz 2>/dev/null | wc -l)"

# List all backups
echo ""
echo "Available backups:"
ls -lh "${BACKUP_DIR}"/backup-*.sql.gz 2>/dev/null || echo "No backups found"

exit 0
