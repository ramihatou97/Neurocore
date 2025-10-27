#!/bin/bash
#
# File Backup Script
# Creates compressed backups of uploaded files (PDFs, images, etc.)
#
# Usage:
#   ./backup-files.sh [backup_name]
#
# Environment Variables:
#   BACKUP_DIR        - Directory to store backups (default: /opt/neurocore/backups/files)
#   BACKUP_RETAIN     - Number of backups to retain (default: 7)
#   SOURCE_PDF_DIR    - PDF storage directory (default: /opt/neurocore/data/pdfs)
#   SOURCE_IMAGE_DIR  - Image storage directory (default: /opt/neurocore/data/images)
#

set -euo pipefail

# ==================== Configuration ====================

BACKUP_DIR="${BACKUP_DIR:-/opt/neurocore/backups/files}"
BACKUP_RETAIN="${BACKUP_RETAIN:-7}"
SOURCE_PDF_DIR="${SOURCE_PDF_DIR:-/opt/neurocore/data/pdfs}"
SOURCE_IMAGE_DIR="${SOURCE_IMAGE_DIR:-/opt/neurocore/data/images}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_NAME="${1:-files-backup-${TIMESTAMP}}"
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"

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

# ==================== Pre-flight Checks ====================

log_info "Starting file backup..."

# Check if source directories exist
if [ ! -d "${SOURCE_PDF_DIR}" ]; then
    log_warn "PDF directory not found: ${SOURCE_PDF_DIR}"
fi

if [ ! -d "${SOURCE_IMAGE_DIR}" ]; then
    log_warn "Image directory not found: ${SOURCE_IMAGE_DIR}"
fi

if [ ! -d "${SOURCE_PDF_DIR}" ] && [ ! -d "${SOURCE_IMAGE_DIR}" ]; then
    log_error "No source directories found"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Check disk space (require at least 2GB free for file backups)
AVAILABLE_SPACE=$(df "${BACKUP_DIR}" | tail -1 | awk '{print $4}')
if [ "${AVAILABLE_SPACE}" -lt 2097152 ]; then
    log_error "Insufficient disk space in ${BACKUP_DIR}"
    log_error "Available: ${AVAILABLE_SPACE}KB, Required: 2GB"
    exit 1
fi

log_info "Pre-flight checks passed"

# ==================== Calculate Source Size ====================

log_info "Calculating source data size..."

TOTAL_SIZE=0
if [ -d "${SOURCE_PDF_DIR}" ]; then
    PDF_SIZE=$(du -sb "${SOURCE_PDF_DIR}" 2>/dev/null | cut -f1)
    log_info "PDFs: $(numfmt --to=iec-i --suffix=B ${PDF_SIZE} 2>/dev/null || echo "${PDF_SIZE} bytes")"
    TOTAL_SIZE=$((TOTAL_SIZE + PDF_SIZE))
fi

if [ -d "${SOURCE_IMAGE_DIR}" ]; then
    IMAGE_SIZE=$(du -sb "${SOURCE_IMAGE_DIR}" 2>/dev/null | cut -f1)
    log_info "Images: $(numfmt --to=iec-i --suffix=B ${IMAGE_SIZE} 2>/dev/null || echo "${IMAGE_SIZE} bytes")"
    TOTAL_SIZE=$((TOTAL_SIZE + IMAGE_SIZE))
fi

log_info "Total source size: $(numfmt --to=iec-i --suffix=B ${TOTAL_SIZE} 2>/dev/null || echo "${TOTAL_SIZE} bytes")"

# ==================== Create Backup ====================

log_info "Creating backup: ${BACKUP_FILE}"

# Create tar archive with compression
# Options:
#   -c: create archive
#   -z: compress with gzip
#   -f: output file
#   -v: verbose
#   --exclude: exclude patterns
#   -P: preserve absolute paths

TAR_ARGS="-czf ${BACKUP_FILE}"
TAR_PATHS=""

if [ -d "${SOURCE_PDF_DIR}" ]; then
    TAR_PATHS="${TAR_PATHS} ${SOURCE_PDF_DIR}"
fi

if [ -d "${SOURCE_IMAGE_DIR}" ]; then
    TAR_PATHS="${TAR_PATHS} ${SOURCE_IMAGE_DIR}"
fi

# Create backup with progress indicator
if tar ${TAR_ARGS} \
    --exclude='*.tmp' \
    --exclude='*.temp' \
    --exclude='.DS_Store' \
    --exclude='Thumbs.db' \
    ${TAR_PATHS} 2>&1 | while read -r line; do
        echo "${line}"
    done; then

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

# Calculate compression ratio
if [ "${TOTAL_SIZE}" -gt 0 ]; then
    COMPRESSION_RATIO=$(echo "scale=2; ${BACKUP_SIZE} * 100 / ${TOTAL_SIZE}" | bc)
    log_info "Compression ratio: ${COMPRESSION_RATIO}%"
fi

# Test backup integrity
if tar -tzf "${BACKUP_FILE}" > /dev/null 2>&1; then
    log_info "Backup integrity verified"
else
    log_error "Backup integrity check failed"
    exit 1
fi

# ==================== Create Metadata ====================

METADATA_FILE="${BACKUP_FILE}.meta"

# Count files in backup
FILE_COUNT=$(tar -tzf "${BACKUP_FILE}" | wc -l)

cat > "${METADATA_FILE}" << EOF
Backup Metadata
================
Backup File: ${BACKUP_FILE}
Created: $(date -Iseconds)
Backup Size: ${BACKUP_SIZE} bytes
Source Size: ${TOTAL_SIZE} bytes
Compression Ratio: ${COMPRESSION_RATIO:-N/A}%
File Count: ${FILE_COUNT}
Source Directories:
$([ -d "${SOURCE_PDF_DIR}" ] && echo "  - ${SOURCE_PDF_DIR}" || true)
$([ -d "${SOURCE_IMAGE_DIR}" ] && echo "  - ${SOURCE_IMAGE_DIR}" || true)
Hostname: $(hostname)
EOF

log_info "Metadata created: ${METADATA_FILE}"

# ==================== Cleanup Old Backups ====================

log_info "Cleaning up old backups (keeping last ${BACKUP_RETAIN})..."

# List backups sorted by modification time, keep newest N
OLD_BACKUPS=$(ls -t "${BACKUP_DIR}"/files-backup-*.tar.gz 2>/dev/null | tail -n +$((BACKUP_RETAIN + 1)) || true)

if [ -n "${OLD_BACKUPS}" ]; then
    while IFS= read -r OLD_BACKUP; do
        log_info "Removing old backup: $(basename "${OLD_BACKUP}")"
        rm -f "${OLD_BACKUP}" "${OLD_BACKUP}.meta"
    done <<< "${OLD_BACKUPS}"
else
    log_info "No old backups to remove"
fi

# ==================== Summary ====================

log_info "File backup completed successfully!"
log_info "Backup location: ${BACKUP_FILE}"
log_info "Total backups: $(ls -1 "${BACKUP_DIR}"/files-backup-*.tar.gz 2>/dev/null | wc -l)"

# List all backups
echo ""
echo "Available backups:"
ls -lh "${BACKUP_DIR}"/files-backup-*.tar.gz 2>/dev/null || echo "No backups found"

exit 0
