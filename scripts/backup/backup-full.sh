#!/bin/bash
#
# Full Backup Script
# Creates comprehensive backup of database, files, and configuration
#
# Usage:
#   ./backup-full.sh [backup_name]
#
# Environment Variables:
#   BACKUP_ROOT_DIR - Root directory for backups (default: /opt/neurocore/backups)
#   BACKUP_RETAIN   - Number of full backups to retain (default: 5)
#

set -euo pipefail

# ==================== Configuration ====================

BACKUP_ROOT_DIR="${BACKUP_ROOT_DIR:-/opt/neurocore/backups}"
BACKUP_RETAIN="${BACKUP_RETAIN:-5}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_NAME="${1:-full-backup-${TIMESTAMP}}"
BACKUP_DIR="${BACKUP_ROOT_DIR}/full/${BACKUP_NAME}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# ==================== Pre-flight Checks ====================

log_section "Full Backup Starting"

log_info "Backup name: ${BACKUP_NAME}"
log_info "Backup directory: ${BACKUP_DIR}"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Check disk space (require at least 5GB free)
AVAILABLE_SPACE=$(df "${BACKUP_ROOT_DIR}" | tail -1 | awk '{print $4}')
if [ "${AVAILABLE_SPACE}" -lt 5242880 ]; then
    log_error "Insufficient disk space in ${BACKUP_ROOT_DIR}"
    log_error "Available: ${AVAILABLE_SPACE}KB, Required: 5GB"
    exit 1
fi

log_info "Available disk space: $(numfmt --to=iec-i --suffix=B $((AVAILABLE_SPACE * 1024)) 2>/dev/null || echo "${AVAILABLE_SPACE}KB")"

# ==================== Database Backup ====================

log_section "1. Database Backup"

DB_BACKUP_FILE="${BACKUP_DIR}/database.sql.gz"
export BACKUP_DIR="${BACKUP_ROOT_DIR}/database"

if "${SCRIPT_DIR}/backup-database.sh" "database-${TIMESTAMP}"; then
    log_info "Database backup completed"
    # Copy to full backup directory
    cp "${BACKUP_ROOT_DIR}/database/backup-${TIMESTAMP}.sql.gz" "${DB_BACKUP_FILE}"
    cp "${BACKUP_ROOT_DIR}/database/backup-${TIMESTAMP}.sql.gz.meta" "${DB_BACKUP_FILE}.meta"
else
    log_error "Database backup failed"
    exit 1
fi

# ==================== Files Backup ====================

log_section "2. Files Backup"

FILES_BACKUP_FILE="${BACKUP_DIR}/files.tar.gz"
export BACKUP_DIR="${BACKUP_ROOT_DIR}/files"

if "${SCRIPT_DIR}/backup-files.sh" "files-${TIMESTAMP}"; then
    log_info "Files backup completed"
    # Copy to full backup directory
    cp "${BACKUP_ROOT_DIR}/files/files-backup-${TIMESTAMP}.tar.gz" "${FILES_BACKUP_FILE}"
    cp "${BACKUP_ROOT_DIR}/files/files-backup-${TIMESTAMP}.tar.gz.meta" "${FILES_BACKUP_FILE}.meta"
else
    log_error "Files backup failed"
    exit 1
fi

# ==================== Configuration Backup ====================

log_section "3. Configuration Backup"

CONFIG_BACKUP_FILE="${BACKUP_DIR}/config.tar.gz"
PROJECT_ROOT="/opt/neurocore"

log_info "Backing up configuration files..."

# Create tar archive of configuration files
tar -czf "${CONFIG_BACKUP_FILE}" \
    -C "${PROJECT_ROOT}" \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='node_modules' \
    --exclude='.git' \
    --exclude='data' \
    --exclude='logs' \
    --exclude='backups' \
    .env \
    .env.example \
    docker-compose.yml \
    docker-compose.prod.yml \
    docker-compose.staging.yml \
    docker-compose.monitoring.yml \
    monitoring/ \
    scripts/ \
    2>/dev/null || true

if [ -f "${CONFIG_BACKUP_FILE}" ]; then
    log_info "Configuration backup completed"
else
    log_warn "Configuration backup had issues, but continuing..."
fi

# ==================== Docker Volumes Backup ====================

log_section "4. Docker Volumes Backup"

VOLUMES_BACKUP_FILE="${BACKUP_DIR}/volumes.tar.gz"

log_info "Backing up Docker volumes..."

# List of volumes to backup
VOLUMES=(
    "neurocore_postgres_data"
    "neurocore_redis_data"
    "neurocore_prometheus_data"
    "neurocore_grafana_data"
)

# Create temporary directory for volume exports
TEMP_VOLUME_DIR=$(mktemp -d)

for VOLUME in "${VOLUMES[@]}"; do
    if docker volume inspect "${VOLUME}" > /dev/null 2>&1; then
        log_info "Backing up volume: ${VOLUME}"
        docker run --rm \
            -v "${VOLUME}:/source:ro" \
            -v "${TEMP_VOLUME_DIR}:/backup" \
            alpine \
            tar czf "/backup/${VOLUME}.tar.gz" -C /source . 2>/dev/null || true
    else
        log_warn "Volume not found: ${VOLUME}"
    fi
done

# Combine all volume backups
tar -czf "${VOLUMES_BACKUP_FILE}" -C "${TEMP_VOLUME_DIR}" . 2>/dev/null || true
rm -rf "${TEMP_VOLUME_DIR}"

if [ -f "${VOLUMES_BACKUP_FILE}" ]; then
    log_info "Docker volumes backup completed"
else
    log_warn "Docker volumes backup had issues, but continuing..."
fi

# ==================== Create Backup Manifest ====================

log_section "5. Creating Backup Manifest"

MANIFEST_FILE="${BACKUP_DIR}/MANIFEST.txt"

cat > "${MANIFEST_FILE}" << EOF
================================
Neurocore Full Backup Manifest
================================

Backup Name: ${BACKUP_NAME}
Created: $(date -Iseconds)
Hostname: $(hostname)
Backup Directory: ${BACKUP_DIR}

================================
Backup Contents
================================

EOF

# Add file sizes and checksums
for FILE in "${BACKUP_DIR}"/*.{gz,txt}; do
    if [ -f "${FILE}" ]; then
        FILENAME=$(basename "${FILE}")
        FILESIZE=$(stat -f%z "${FILE}" 2>/dev/null || stat -c%s "${FILE}" 2>/dev/null)
        FILESIZE_HUMAN=$(numfmt --to=iec-i --suffix=B ${FILESIZE} 2>/dev/null || echo "${FILESIZE} bytes")
        CHECKSUM=$(shasum -a 256 "${FILE}" | cut -d' ' -f1)

        cat >> "${MANIFEST_FILE}" << EOF
File: ${FILENAME}
  Size: ${FILESIZE_HUMAN} (${FILESIZE} bytes)
  SHA256: ${CHECKSUM}

EOF
    fi
done

# Add system information
cat >> "${MANIFEST_FILE}" << EOF
================================
System Information
================================

OS: $(uname -s)
Kernel: $(uname -r)
Architecture: $(uname -m)

Docker Version: $(docker --version 2>/dev/null || echo "Not available")

================================
Application Information
================================

Running Containers:
$(docker ps --format "  - {{.Names}}: {{.Status}}" 2>/dev/null || echo "  Not available")

Database Size:
$(docker exec neurocore_postgres psql -U neurosurgery_admin -d neurosurgery_kb -c "SELECT pg_size_pretty(pg_database_size('neurosurgery_kb'));" -t 2>/dev/null | xargs || echo "  Not available")

================================
Restore Instructions
================================

To restore this backup, use:
  ./restore-full.sh ${BACKUP_NAME}

For partial restore:
  Database: ./restore-database.sh ${BACKUP_DIR}/database.sql.gz
  Files: ./restore-files.sh ${BACKUP_DIR}/files.tar.gz

EOF

log_info "Manifest created: ${MANIFEST_FILE}"

# ==================== Calculate Total Backup Size ====================

TOTAL_BACKUP_SIZE=$(du -sb "${BACKUP_DIR}" | cut -f1)
log_info "Total backup size: $(numfmt --to=iec-i --suffix=B ${TOTAL_BACKUP_SIZE} 2>/dev/null || echo "${TOTAL_BACKUP_SIZE} bytes")"

# ==================== Cleanup Old Backups ====================

log_section "6. Cleanup Old Backups"

log_info "Cleaning up old full backups (keeping last ${BACKUP_RETAIN})..."

OLD_BACKUPS=$(ls -td "${BACKUP_ROOT_DIR}"/full/full-backup-* 2>/dev/null | tail -n +$((BACKUP_RETAIN + 1)) || true)

if [ -n "${OLD_BACKUPS}" ]; then
    while IFS= read -r OLD_BACKUP; do
        log_info "Removing old backup: $(basename "${OLD_BACKUP}")"
        rm -rf "${OLD_BACKUP}"
    done <<< "${OLD_BACKUPS}"
else
    log_info "No old backups to remove"
fi

# ==================== Summary ====================

log_section "Backup Completed Successfully"

echo ""
log_info "Backup location: ${BACKUP_DIR}"
log_info "Total backups: $(ls -1d "${BACKUP_ROOT_DIR}"/full/full-backup-* 2>/dev/null | wc -l)"
log_info "Manifest: ${MANIFEST_FILE}"

echo ""
echo "Backup contents:"
ls -lh "${BACKUP_DIR}/" 2>/dev/null

echo ""
log_info "To restore this backup, run:"
log_info "  ./restore-full.sh ${BACKUP_NAME}"

exit 0
