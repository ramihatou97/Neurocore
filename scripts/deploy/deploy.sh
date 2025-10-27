#!/bin/bash
#
# Deployment Automation Script
# Automates the deployment process with safety checks and rollback capability
#
# Usage:
#   ./deploy.sh [environment] [version]
#
# Examples:
#   ./deploy.sh staging
#   ./deploy.sh production v1.2.0
#
# Environment Variables:
#   SKIP_BACKUP      - Skip pre-deployment backup (default: false)
#   SKIP_TESTS       - Skip health checks (default: false)
#   AUTO_ROLLBACK    - Automatic rollback on failure (default: true)
#

set -euo pipefail

# ==================== Configuration ====================

ENVIRONMENT="${1:-staging}"
VERSION="${2:-latest}"
SKIP_BACKUP="${SKIP_BACKUP:-false}"
SKIP_TESTS="${SKIP_TESTS:-false}"
AUTO_ROLLBACK="${AUTO_ROLLBACK:-true}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEPLOYMENT_LOG="/var/log/neurocore/deploy-$(date +%Y%m%d-%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ==================== Functions ====================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "${DEPLOYMENT_LOG}"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "${DEPLOYMENT_LOG}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "${DEPLOYMENT_LOG}"
}

log_section() {
    echo "" | tee -a "${DEPLOYMENT_LOG}"
    echo -e "${BLUE}========================================${NC}" | tee -a "${DEPLOYMENT_LOG}"
    echo -e "${BLUE}  $1${NC}" | tee -a "${DEPLOYMENT_LOG}"
    echo -e "${BLUE}========================================${NC}" | tee -a "${DEPLOYMENT_LOG}"
}

rollback() {
    log_error "Deployment failed! Initiating rollback..."
    "${SCRIPT_DIR}/rollback.sh" "${ENVIRONMENT}" || log_error "Rollback failed!"
    exit 1
}

# ==================== Pre-Deployment Checks ====================

log_section "Deployment Starting"

log_info "Environment: ${ENVIRONMENT}"
log_info "Version: ${VERSION}"
log_info "Date: $(date -Iseconds)"
log_info "User: $(whoami)"
log_info "Host: $(hostname)"

# Validate environment
if [[ ! "${ENVIRONMENT}" =~ ^(staging|production)$ ]]; then
    log_error "Invalid environment: ${ENVIRONMENT}"
    log_error "Must be: staging or production"
    exit 1
fi

# Validate version for production
if [ "${ENVIRONMENT}" = "production" ] && [ "${VERSION}" = "latest" ]; then
    log_error "Production deployments must specify a version tag"
    log_error "Usage: ./deploy.sh production v1.2.0"
    exit 1
fi

# Production safety check
if [ "${ENVIRONMENT}" = "production" ]; then
    log_warn "==================== PRODUCTION DEPLOYMENT ===================="
    log_warn "You are about to deploy to PRODUCTION"
    log_warn "Version: ${VERSION}"
    log_warn "=============================================================="
    read -p "Type 'DEPLOY' to continue: " CONFIRM
    if [ "${CONFIRM}" != "DEPLOY" ]; then
        log_info "Deployment cancelled by user"
        exit 0
    fi
fi

# Create log directory
mkdir -p "$(dirname "${DEPLOYMENT_LOG}")"

# Change to project directory
cd "${PROJECT_ROOT}"

# ==================== Pre-Deployment Backup ====================

log_section "1. Pre-Deployment Backup"

if [ "${SKIP_BACKUP}" = "true" ]; then
    log_warn "Skipping backup (SKIP_BACKUP=true)"
else
    log_info "Creating pre-deployment backup..."

    BACKUP_NAME="pre-deploy-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"

    if "${SCRIPT_DIR}/../backup/backup-database.sh" "${BACKUP_NAME}"; then
        log_info "Backup created: ${BACKUP_NAME}"
        echo "${BACKUP_NAME}" > /tmp/last-backup.txt
    else
        log_error "Backup failed!"
        if [ "${AUTO_ROLLBACK}" = "true" ]; then
            rollback
        else
            exit 1
        fi
    fi
fi

# ==================== Pull Latest Code ====================

log_section "2. Pull Latest Code"

log_info "Pulling latest code from repository..."

if [ -d ".git" ]; then
    git fetch --all --tags
    if [ "${VERSION}" != "latest" ]; then
        git checkout "tags/${VERSION}" -b "deploy-${VERSION}" 2>/dev/null || git checkout "${VERSION}"
        log_info "Checked out version: ${VERSION}"
    else
        git pull origin develop
        log_info "Pulled latest from develop branch"
    fi
else
    log_warn "Not a git repository, skipping code pull"
fi

# ==================== Build Docker Images ====================

log_section "3. Build Docker Images"

log_info "Building Docker images..."

COMPOSE_FILE="docker-compose.yml"
COMPOSE_OVERRIDE="docker-compose.${ENVIRONMENT}.yml"

if [ ! -f "${COMPOSE_OVERRIDE}" ]; then
    log_error "Compose override not found: ${COMPOSE_OVERRIDE}"
    if [ "${AUTO_ROLLBACK}" = "true" ]; then
        rollback
    else
        exit 1
    fi
fi

# Build images
if docker compose -f "${COMPOSE_FILE}" -f "${COMPOSE_OVERRIDE}" build --no-cache; then
    log_info "Docker images built successfully"
else
    log_error "Docker build failed!"
    if [ "${AUTO_ROLLBACK}" = "true" ]; then
        rollback
    else
        exit 1
    fi
fi

# ==================== Run Database Migrations ====================

log_section "4. Database Migrations"

log_info "Running database migrations..."

# Run migrations in a temporary container
if docker compose -f "${COMPOSE_FILE}" -f "${COMPOSE_OVERRIDE}" run --rm api alembic upgrade head; then
    log_info "Migrations completed successfully"
else
    log_error "Migrations failed!"
    if [ "${AUTO_ROLLBACK}" = "true" ]; then
        rollback
    else
        exit 1
    fi
fi

# ==================== Deploy New Version ====================

log_section "5. Deploy New Version"

log_info "Stopping old containers..."
docker compose -f "${COMPOSE_FILE}" -f "${COMPOSE_OVERRIDE}" down --timeout 30

log_info "Starting new containers..."
if docker compose -f "${COMPOSE_FILE}" -f "${COMPOSE_OVERRIDE}" up -d; then
    log_info "Containers started successfully"
else
    log_error "Failed to start containers!"
    if [ "${AUTO_ROLLBACK}" = "true" ]; then
        rollback
    else
        exit 1
    fi
fi

# ==================== Wait for Services ====================

log_section "6. Wait for Services"

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
        if [ "${AUTO_ROLLBACK}" = "true" ]; then
            rollback
        else
            exit 1
        fi
    fi

    log_info "Waiting for services... (${ELAPSED}/${MAX_WAIT}s)"
    sleep ${WAIT_INTERVAL}
    ELAPSED=$((ELAPSED + WAIT_INTERVAL))
done

# ==================== Health Checks ====================

log_section "7. Health Checks"

if [ "${SKIP_TESTS}" = "true" ]; then
    log_warn "Skipping health checks (SKIP_TESTS=true)"
else
    log_info "Running health checks..."

    if "${SCRIPT_DIR}/health-check.sh"; then
        log_info "Health checks passed"
    else
        log_error "Health checks failed!"
        if [ "${AUTO_ROLLBACK}" = "true" ]; then
            rollback
        else
            exit 1
        fi
    fi
fi

# ==================== Post-Deployment Tasks ====================

log_section "8. Post-Deployment Tasks"

# Restart workers to pick up new code
log_info "Restarting Celery workers..."
docker compose -f "${COMPOSE_FILE}" -f "${COMPOSE_OVERRIDE}" restart celery-worker celery-beat

# Clear cache
log_info "Clearing application cache..."
docker compose exec -T redis redis-cli FLUSHALL || log_warn "Cache clear failed"

# Clean up old images
log_info "Cleaning up old Docker images..."
docker image prune -af --filter "until=72h"

# Generate deployment report
log_info "Generating deployment report..."
cat > /tmp/deployment-report.txt << EOF
Deployment Report
=================
Environment: ${ENVIRONMENT}
Version: ${VERSION}
Date: $(date -Iseconds)
User: $(whoami)
Host: $(hostname)

Deployed Containers:
$(docker compose -f "${COMPOSE_FILE}" -f "${COMPOSE_OVERRIDE}" ps)

Health Status:
$(curl -s http://localhost:8002/health | jq '.' 2>/dev/null || echo "Not available")
EOF

log_info "Deployment report saved: /tmp/deployment-report.txt"

# ==================== Summary ====================

log_section "Deployment Completed Successfully"

log_info "Environment: ${ENVIRONMENT}"
log_info "Version: ${VERSION}"
log_info "Duration: $SECONDS seconds"
log_info "Log file: ${DEPLOYMENT_LOG}"

echo ""
log_info "Next steps:"
log_info "  1. Monitor logs: docker compose logs -f api"
log_info "  2. Check metrics: http://localhost:3003 (Grafana)"
log_info "  3. Verify functionality"
log_info "  4. Monitor for errors"

echo ""
log_info "Deployment successful! 🎉"

exit 0
