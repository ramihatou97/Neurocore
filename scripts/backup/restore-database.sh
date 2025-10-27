#!/bin/bash
#
# Database Restore Script
# Restores PostgreSQL database from backup
#
# Usage:
#   ./restore-database.sh <backup_file>
#
# Example:
#   ./restore-database.sh /opt/neurocore/backups/database/backup-20250127-143000.sql.gz
#
# Environment Variables:
#   DB_CONTAINER   - Database container name (default: neurocore_postgres)
#   DB_NAME        - Database name (default: neurosurgery_kb)
#   DB_USER        - Database user (default: neurosurgery_admin)
#   FORCE_RESTORE  - Skip confirmation prompt (default: false)
#

set -euo pipefail

# ==================== Configuration ====================

DB_CONTAINER="${DB_CONTAINER:-neurocore_postgres}"
DB_NAME="${DB_NAME:-neurosurgery_kb}"
DB_USER="${DB_USER:-neurosurgery_admin}"
FORCE_RESTORE="${FORCE_RESTORE:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

usage() {
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Example:"
    echo "  $0 /opt/neurocore/backups/database/backup-20250127-143000.sql.gz"
    echo ""
    echo "Environment Variables:"
    echo "  DB_CONTAINER   - Database container name (default: neurocore_postgres)"
    echo "  DB_NAME        - Database name (default: neurosurgery_kb)"
    echo "  DB_USER        - Database user (default: neurosurgery_admin)"
    echo "  FORCE_RESTORE  - Skip confirmation (default: false)"
    exit 1
}

# ==================== Argument Validation ====================

if [ $# -lt 1 ]; then
    log_error "Missing backup file argument"
    usage
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "${BACKUP_FILE}" ]; then
    log_error "Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

# ==================== Pre-flight Checks ====================

log_warn "========================================="
log_warn "  DATABASE RESTORE"
log_warn "========================================="
log_warn ""
log_warn "⚠️  WARNING: This will OVERWRITE the current database!"
log_warn ""
log_warn "Backup file: ${BACKUP_FILE}"
log_warn "Database: ${DB_NAME}"
log_warn "Container: ${DB_CONTAINER}"
log_warn ""

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    log_error "Database container '${DB_CONTAINER}' is not running"
    log_error "Start the container first: docker compose up -d postgres"
    exit 1
fi

# Verify backup file integrity
log_info "Verifying backup file integrity..."
if ! gzip -t "${BACKUP_FILE}"; then
    log_error "Backup file is corrupted or invalid"
    exit 1
fi
log_info "Backup file integrity OK"

# Get backup metadata if available
METADATA_FILE="${BACKUP_FILE}.meta"
if [ -f "${METADATA_FILE}" ]; then
    log_info "Backup metadata:"
    cat "${METADATA_FILE}" | grep -E "(Created|Size|Database)" || true
    echo ""
fi

# ==================== Confirmation ====================

if [ "${FORCE_RESTORE}" != "true" ]; then
    echo ""
    read -p "Are you sure you want to restore? This will overwrite the current database. (yes/no): " CONFIRM
    if [ "${CONFIRM}" != "yes" ]; then
        log_info "Restore cancelled by user"
        exit 0
    fi
fi

# ==================== Create Pre-Restore Backup ====================

log_info "Creating pre-restore backup..."

PRE_RESTORE_BACKUP="/tmp/pre-restore-${TIMESTAMP}.sql.gz"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

if docker exec -t "${DB_CONTAINER}" pg_dump \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --clean \
    --if-exists \
    2>&1 | gzip > "${PRE_RESTORE_BACKUP}"; then
    log_info "Pre-restore backup created: ${PRE_RESTORE_BACKUP}"
else
    log_warn "Failed to create pre-restore backup (continuing anyway)"
fi

# ==================== Stop Application ====================

log_info "Stopping application containers..."

# Stop API and workers to prevent database access during restore
docker compose stop api celery-worker celery-beat 2>/dev/null || true

log_info "Application containers stopped"

# ==================== Terminate Active Connections ====================

log_info "Terminating active database connections..."

docker exec -t "${DB_CONTAINER}" psql -U "${DB_USER}" -d postgres << EOF
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '${DB_NAME}'
  AND pid <> pg_backend_pid();
EOF

log_info "Active connections terminated"

# ==================== Drop and Recreate Database ====================

log_info "Dropping and recreating database..."

docker exec -t "${DB_CONTAINER}" psql -U "${DB_USER}" -d postgres << EOF
DROP DATABASE IF EXISTS ${DB_NAME};
CREATE DATABASE ${DB_NAME};
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
EOF

log_info "Database recreated"

# ==================== Restore Database ====================

log_info "Restoring database from backup..."
log_info "This may take several minutes depending on database size..."

# Restore database
if gunzip -c "${BACKUP_FILE}" | docker exec -i "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" > /dev/null 2>&1; then
    log_info "Database restore completed successfully"
else
    log_error "Database restore failed"
    log_error "Attempting to restore from pre-restore backup..."

    if [ -f "${PRE_RESTORE_BACKUP}" ]; then
        gunzip -c "${PRE_RESTORE_BACKUP}" | docker exec -i "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" > /dev/null 2>&1
        log_info "Rolled back to pre-restore state"
    fi

    exit 1
fi

# ==================== Enable Extensions ====================

log_info "Enabling required extensions..."

docker exec -t "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" << EOF
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
EOF

log_info "Extensions enabled"

# ==================== Run Migrations ====================

log_info "Running database migrations..."

docker compose run --rm api alembic upgrade head 2>/dev/null || log_warn "Migrations skipped or failed"

# ==================== Verify Restore ====================

log_info "Verifying database restore..."

# Check table count
TABLE_COUNT=$(docker exec -t "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | xargs)

log_info "Tables restored: ${TABLE_COUNT}"

if [ "${TABLE_COUNT}" -eq 0 ]; then
    log_error "No tables found after restore - restore may have failed"
    exit 1
fi

# Check record counts in key tables
log_info "Record counts:"
for TABLE in users pdfs chapters images; do
    COUNT=$(docker exec -t "${DB_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT COUNT(*) FROM ${TABLE};" 2>/dev/null | xargs || echo "N/A")
    log_info "  ${TABLE}: ${COUNT}"
done

# ==================== Restart Application ====================

log_info "Starting application containers..."

docker compose start api celery-worker celery-beat 2>/dev/null || true

# Wait for application to be ready
log_info "Waiting for application to be ready..."
sleep 5

# ==================== Health Check ====================

log_info "Performing health check..."

if curl -f http://localhost:8002/health > /dev/null 2>&1; then
    log_info "Application health check passed"
else
    log_warn "Application health check failed - manual verification needed"
fi

# ==================== Cleanup ====================

# Remove pre-restore backup after successful restore
if [ -f "${PRE_RESTORE_BACKUP}" ]; then
    log_info "Removing pre-restore backup: ${PRE_RESTORE_BACKUP}"
    rm -f "${PRE_RESTORE_BACKUP}"
fi

# ==================== Summary ====================

log_info "========================================="
log_info "  Database Restore Completed"
log_info "========================================="
log_info ""
log_info "Database: ${DB_NAME}"
log_info "Restored from: ${BACKUP_FILE}"
log_info "Tables: ${TABLE_COUNT}"
log_info ""
log_info "Next steps:"
log_info "  1. Verify data integrity"
log_info "  2. Check application logs: docker compose logs -f api"
log_info "  3. Test application functionality"

exit 0
