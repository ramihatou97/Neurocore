#!/bin/bash
#
# Files Restore Script
# Restores uploaded files (PDFs, images) from backup
#
# Usage:
#   ./restore-files.sh <backup_file>
#
# Example:
#   ./restore-files.sh /opt/neurocore/backups/files/files-backup-20250127-143000.tar.gz
#
# Environment Variables:
#   TARGET_PDF_DIR    - PDF storage directory (default: /opt/neurocore/data/pdfs)
#   TARGET_IMAGE_DIR  - Image storage directory (default: /opt/neurocore/data/images)
#   FORCE_RESTORE     - Skip confirmation prompt (default: false)
#

set -euo pipefail

# ==================== Configuration ====================

TARGET_PDF_DIR="${TARGET_PDF_DIR:-/opt/neurocore/data/pdfs}"
TARGET_IMAGE_DIR="${TARGET_IMAGE_DIR:-/opt/neurocore/data/images}"
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
    echo "  $0 /opt/neurocore/backups/files/files-backup-20250127-143000.tar.gz"
    echo ""
    echo "Environment Variables:"
    echo "  TARGET_PDF_DIR    - PDF storage directory (default: /opt/neurocore/data/pdfs)"
    echo "  TARGET_IMAGE_DIR  - Image storage directory (default: /opt/neurocore/data/images)"
    echo "  FORCE_RESTORE     - Skip confirmation (default: false)"
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
log_warn "  FILES RESTORE"
log_warn "========================================="
log_warn ""
log_warn "⚠️  WARNING: This will OVERWRITE existing files!"
log_warn ""
log_warn "Backup file: ${BACKUP_FILE}"
log_warn "Target directories:"
log_warn "  - ${TARGET_PDF_DIR}"
log_warn "  - ${TARGET_IMAGE_DIR}"
log_warn ""

# Verify backup file integrity
log_info "Verifying backup file integrity..."
if ! tar -tzf "${BACKUP_FILE}" > /dev/null 2>&1; then
    log_error "Backup file is corrupted or invalid"
    exit 1
fi
log_info "Backup file integrity OK"

# Get backup metadata if available
METADATA_FILE="${BACKUP_FILE}.meta"
if [ -f "${METADATA_FILE}" ]; then
    log_info "Backup metadata:"
    cat "${METADATA_FILE}" | grep -E "(Created|Backup Size|File Count)" || true
    echo ""
fi

# Count files in backup
FILE_COUNT=$(tar -tzf "${BACKUP_FILE}" | wc -l)
log_info "Files in backup: ${FILE_COUNT}"

# ==================== Confirmation ====================

if [ "${FORCE_RESTORE}" != "true" ]; then
    echo ""
    read -p "Are you sure you want to restore? This will overwrite existing files. (yes/no): " CONFIRM
    if [ "${CONFIRM}" != "yes" ]; then
        log_info "Restore cancelled by user"
        exit 0
    fi
fi

# ==================== Create Pre-Restore Backup ====================

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
PRE_RESTORE_BACKUP="/tmp/pre-restore-files-${TIMESTAMP}.tar.gz"

log_info "Creating pre-restore backup of existing files..."

# Create backup of current files
TAR_PATHS=""
if [ -d "${TARGET_PDF_DIR}" ]; then
    TAR_PATHS="${TAR_PATHS} ${TARGET_PDF_DIR}"
fi
if [ -d "${TARGET_IMAGE_DIR}" ]; then
    TAR_PATHS="${TAR_PATHS} ${TARGET_IMAGE_DIR}"
fi

if [ -n "${TAR_PATHS}" ]; then
    tar -czf "${PRE_RESTORE_BACKUP}" ${TAR_PATHS} 2>/dev/null || true
    log_info "Pre-restore backup created: ${PRE_RESTORE_BACKUP}"
else
    log_warn "No existing files to backup"
fi

# ==================== Stop Application ====================

log_info "Stopping application containers..."

# Stop API and workers to prevent file access during restore
docker compose stop api celery-worker celery-beat 2>/dev/null || true

log_info "Application containers stopped"

# ==================== Restore Files ====================

log_info "Restoring files from backup..."
log_info "This may take several minutes depending on backup size..."

# Extract files to root directory
# The tar archive contains full paths like /opt/neurocore/data/pdfs/...
if tar -xzf "${BACKUP_FILE}" -C / --overwrite 2>&1; then
    log_info "Files restore completed successfully"
else
    log_error "Files restore failed"

    # Attempt rollback
    if [ -f "${PRE_RESTORE_BACKUP}" ]; then
        log_error "Attempting to restore from pre-restore backup..."
        tar -xzf "${PRE_RESTORE_BACKUP}" -C / --overwrite 2>/dev/null || true
        log_info "Rolled back to pre-restore state"
    fi

    exit 1
fi

# ==================== Set Permissions ====================

log_info "Setting file permissions..."

# Set correct ownership and permissions
if [ -d "${TARGET_PDF_DIR}" ]; then
    chown -R 1000:1000 "${TARGET_PDF_DIR}" 2>/dev/null || sudo chown -R 1000:1000 "${TARGET_PDF_DIR}"
    chmod -R 755 "${TARGET_PDF_DIR}"
    log_info "PDF directory permissions set"
fi

if [ -d "${TARGET_IMAGE_DIR}" ]; then
    chown -R 1000:1000 "${TARGET_IMAGE_DIR}" 2>/dev/null || sudo chown -R 1000:1000 "${TARGET_IMAGE_DIR}"
    chmod -R 755 "${TARGET_IMAGE_DIR}"
    log_info "Image directory permissions set"
fi

# ==================== Verify Restore ====================

log_info "Verifying files restore..."

# Count restored files
PDF_COUNT=0
IMAGE_COUNT=0

if [ -d "${TARGET_PDF_DIR}" ]; then
    PDF_COUNT=$(find "${TARGET_PDF_DIR}" -type f -name "*.pdf" 2>/dev/null | wc -l)
fi

if [ -d "${TARGET_IMAGE_DIR}" ]; then
    IMAGE_COUNT=$(find "${TARGET_IMAGE_DIR}" -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" \) 2>/dev/null | wc -l)
fi

log_info "Restored files:"
log_info "  PDFs: ${PDF_COUNT}"
log_info "  Images: ${IMAGE_COUNT}"

# Calculate disk usage
if [ -d "${TARGET_PDF_DIR}" ]; then
    PDF_SIZE=$(du -sh "${TARGET_PDF_DIR}" 2>/dev/null | cut -f1)
    log_info "  PDF storage: ${PDF_SIZE}"
fi

if [ -d "${TARGET_IMAGE_DIR}" ]; then
    IMAGE_SIZE=$(du -sh "${TARGET_IMAGE_DIR}" 2>/dev/null | cut -f1)
    log_info "  Image storage: ${IMAGE_SIZE}"
fi

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
log_info "  Files Restore Completed"
log_info "========================================="
log_info ""
log_info "Restored from: ${BACKUP_FILE}"
log_info "PDFs: ${PDF_COUNT}"
log_info "Images: ${IMAGE_COUNT}"
log_info ""
log_info "Next steps:"
log_info "  1. Verify file integrity"
log_info "  2. Check application logs: docker compose logs -f api"
log_info "  3. Test file access through application"

exit 0
