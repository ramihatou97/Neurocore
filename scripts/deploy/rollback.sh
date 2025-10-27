#!/bin/bash
#
# Rollback Script
# Rolls back to previous deployment state
#
# Usage:
#   ./rollback.sh [environment]
#
# Examples:
#   ./rollback.sh staging
#   ./rollback.sh production
#

set -euo pipefail

# ==================== Configuration ====================

ENVIRONMENT="${1:-staging}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ROLLBACK_LOG="/var/log/neurocore/rollback-$(date +%Y%m%d-%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ==================== Functions ====================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "${ROLLBACK_LOG}"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "${ROLLBACK_LOG}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "${ROLLBACK_LOG}"
}

log_section() {
    echo "" | tee -a "${ROLLBACK_LOG}"
    echo -e "${BLUE}========================================${NC}" | tee -a "${ROLLBACK_LOG}"
    echo -e "${BLUE}  $1${NC}" | tee -a "${ROLLBACK_LOG}"
    echo -e "${BLUE}========================================${NC}" | tee -a "${ROLLBACK_LOG}"
}

# ==================== Pre-Rollback Checks ====================

log_section "Rollback Starting"

log_warn "========================================="
log_warn "  ROLLBACK INITIATED"
log_warn "========================================="
log_warn ""
log_warn "Environment: ${ENVIRONMENT}"
log_warn "Date: $(date -Iseconds)"
log_warn "User: $(whoami)"
log_warn ""

# Validate environment
if [[ ! "${ENVIRONMENT}" =~ ^(staging|production)$ ]]; then
    log_error "Invalid environment: ${ENVIRONMENT}"
    log_error "Must be: staging or production"
    exit 1
fi

# Production safety check
if [ "${ENVIRONMENT}" = "production" ]; then
    log_warn "You are about to ROLLBACK PRODUCTION"
    read -p "Type 'ROLLBACK' to continue: " CONFIRM
    if [ "${CONFIRM}" != "ROLLBACK" ]; then
        log_info "Rollback cancelled by user"
        exit 0
    fi
fi

# Create log directory
mkdir -p "$(dirname "${ROLLBACK_LOG}")"

# Change to project directory
cd "${PROJECT_ROOT}"

# ==================== Identify Last Backup ====================

log_section "1. Identify Last Backup"

LAST_BACKUP_FILE="/tmp/last-backup.txt"

if [ -f "${LAST_BACKUP_FILE}" ]; then
    BACKUP_NAME=$(cat "${LAST_BACKUP_FILE}")
    log_info "Last backup: ${BACKUP_NAME}"
else
    log_warn "No last backup recorded, finding latest backup..."
    BACKUP_NAME=$(ls -t /opt/neurocore/backups/database/backup-*.sql.gz 2>/dev/null | head -1 || echo "")
    if [ -z "${BACKUP_NAME}" ]; then
        log_error "No backups found!"
        exit 1
    fi
    log_info "Using backup: ${BACKUP_NAME}"
fi

# ==================== Get Previous Docker Images ====================

log_section "2. Identify Previous Version"

# Get current image tags
CURRENT_API_IMAGE=$(docker inspect neurocore_api --format='{{.Config.Image}}' 2>/dev/null || echo "unknown")
CURRENT_FRONTEND_IMAGE=$(docker inspect neurocore_frontend --format='{{.Config.Image}}' 2>/dev/null || echo "unknown")

log_info "Current API image: ${CURRENT_API_IMAGE}"
log_info "Current frontend image: ${CURRENT_FRONTEND_IMAGE}"

# List available images
log_info "Available images:"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}" | grep neurocore || true

# ==================== Stop Current Services ====================

log_section "3. Stop Current Services"

log_info "Stopping current services..."

COMPOSE_FILE="docker-compose.yml"
COMPOSE_OVERRIDE="docker-compose.${ENVIRONMENT}.yml"

docker compose -f "${COMPOSE_FILE}" -f "${COMPOSE_OVERRIDE}" down --timeout 30

log_info "Services stopped"

# ==================== Restore Database ====================

log_section "4. Restore Database"

log_info "Restoring database from backup: ${BACKUP_NAME}"

# Start database only
docker compose -f "${COMPOSE_FILE}" up -d postgres redis

# Wait for database
log_info "Waiting for database to be ready..."
sleep 10

# Restore database
if "${SCRIPT_DIR}/../backup/restore-database.sh" "${BACKUP_NAME}"; then
    log_info "Database restored successfully"
else
    log_error "Database restore failed!"
    exit 1
fi

# ==================== Rollback Docker Images ====================

log_section "5. Rollback Docker Images"

log_info "Rolling back to previous Docker images..."

# Option 1: Use git to checkout previous version
if [ -d ".git" ]; then
    log_info "Checking out previous git commit..."
    CURRENT_COMMIT=$(git rev-parse HEAD)
    PREVIOUS_COMMIT=$(git rev-parse HEAD^)

    log_info "Current commit: ${CURRENT_COMMIT}"
    log_info "Previous commit: ${PREVIOUS_COMMIT}"

    git checkout "${PREVIOUS_COMMIT}"

    # Rebuild images from previous commit
    log_info "Rebuilding images from previous version..."
    docker compose -f "${COMPOSE_FILE}" -f "${COMPOSE_OVERRIDE}" build --no-cache
fi

# Option 2: Use previous images if available
# (This would require tagging images with version numbers)

# ==================== Start Services ====================

log_section "6. Start Services"

log_info "Starting rolled-back services..."

if docker compose -f "${COMPOSE_FILE}" -f "${COMPOSE_OVERRIDE}" up -d; then
    log_info "Services started successfully"
else
    log_error "Failed to start services!"
    exit 1
fi

# ==================== Wait for Services ====================

log_section "7. Wait for Services"

log_info "Waiting for services to be ready..."

MAX_WAIT=120
WAIT_INTERVAL=5
ELAPSED=0

while [ ${ELAPSED} -lt ${MAX_WAIT} ]; do
    if curl -f http://localhost:8002/health > /dev/null 2>&1; then
        log_info "Services are ready (${ELAPSED}s)"
        break
    fi

    if [ ${ELAPSED} -ge ${MAX_WAIT} ]; then
        log_error "Services failed to become ready after ${MAX_WAIT}s"
        exit 1
    fi

    log_info "Waiting for services... (${ELAPSED}/${MAX_WAIT}s)"
    sleep ${WAIT_INTERVAL}
    ELAPSED=$((ELAPSED + WAIT_INTERVAL))
done

# ==================== Health Checks ====================

log_section "8. Health Checks"

log_info "Running health checks..."

if "${SCRIPT_DIR}/health-check.sh"; then
    log_info "Health checks passed"
else
    log_error "Health checks failed after rollback!"
    log_error "Manual intervention required!"
    exit 1
fi

# ==================== Clear Cache ====================

log_section "9. Clear Cache"

log_info "Clearing application cache..."
docker compose exec -T redis redis-cli FLUSHALL || log_warn "Cache clear failed"

# ==================== Generate Rollback Report ====================

log_section "10. Generate Report"

ROLLBACK_REPORT="/tmp/rollback-report.txt"

cat > "${ROLLBACK_REPORT}" << EOF
Rollback Report
===============
Environment: ${ENVIRONMENT}
Date: $(date -Iseconds)
User: $(whoami)
Host: $(hostname)

Backup Used: ${BACKUP_NAME}
Previous API Image: ${CURRENT_API_IMAGE}

Running Containers:
$(docker compose -f "${COMPOSE_FILE}" -f "${COMPOSE_OVERRIDE}" ps)

Health Status:
$(curl -s http://localhost:8002/health | jq '.' 2>/dev/null || echo "Not available")

Rollback Log: ${ROLLBACK_LOG}
EOF

log_info "Rollback report saved: ${ROLLBACK_REPORT}"

# ==================== Summary ====================

log_section "Rollback Completed Successfully"

log_info "Environment: ${ENVIRONMENT}"
log_info "Backup used: ${BACKUP_NAME}"
log_info "Duration: $SECONDS seconds"
log_info "Log file: ${ROLLBACK_LOG}"

echo ""
log_info "Next steps:"
log_info "  1. Monitor logs: docker compose logs -f api"
log_info "  2. Verify functionality"
log_info "  3. Investigate deployment failure"
log_info "  4. Plan remediation"

echo ""
log_warn "Rollback successful! System restored to previous state."

exit 0
