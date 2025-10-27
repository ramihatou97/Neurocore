#!/bin/bash
#
# Health Check Script
# Comprehensive health validation for deployed application
#
# Usage:
#   ./health-check.sh [api_url]
#
# Examples:
#   ./health-check.sh
#   ./health-check.sh http://localhost:8002
#   ./health-check.sh https://api.neurosurgery-kb.com
#

set -euo pipefail

# ==================== Configuration ====================

API_URL="${1:-http://localhost:8002}"
TIMEOUT=10
MAX_RETRIES=3

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

check_endpoint() {
    local ENDPOINT="$1"
    local EXPECTED_STATUS="${2:-200}"
    local DESCRIPTION="$3"

    log_info "Checking: ${DESCRIPTION}"

    local STATUS_CODE
    STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time ${TIMEOUT} "${API_URL}${ENDPOINT}" || echo "000")

    if [ "${STATUS_CODE}" = "${EXPECTED_STATUS}" ]; then
        log_info "  ✓ ${DESCRIPTION} (${STATUS_CODE})"
        return 0
    else
        log_error "  ✗ ${DESCRIPTION} (expected ${EXPECTED_STATUS}, got ${STATUS_CODE})"
        return 1
    fi
}

check_json_field() {
    local ENDPOINT="$1"
    local FIELD="$2"
    local EXPECTED="$3"
    local DESCRIPTION="$4"

    log_info "Checking: ${DESCRIPTION}"

    local RESPONSE
    RESPONSE=$(curl -s --max-time ${TIMEOUT} "${API_URL}${ENDPOINT}" || echo "{}")

    local ACTUAL
    ACTUAL=$(echo "${RESPONSE}" | jq -r ".${FIELD}" 2>/dev/null || echo "null")

    if [ "${ACTUAL}" = "${EXPECTED}" ]; then
        log_info "  ✓ ${DESCRIPTION} (${ACTUAL})"
        return 0
    else
        log_warn "  ⚠ ${DESCRIPTION} (expected ${EXPECTED}, got ${ACTUAL})"
        return 1
    fi
}

# ==================== Health Checks ====================

echo ""
echo "========================================="
echo "  Application Health Checks"
echo "========================================="
echo ""
log_info "API URL: ${API_URL}"
log_info "Timeout: ${TIMEOUT}s"
echo ""

TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# ==================== Basic Connectivity ====================

echo "--- Basic Connectivity ---"

# Root endpoint
if check_endpoint "/" "200" "Root endpoint"; then
    ((PASSED_CHECKS++))
else
    ((FAILED_CHECKS++))
fi
((TOTAL_CHECKS++))

# ==================== Health Endpoints ====================

echo ""
echo "--- Health Endpoints ---"

# Basic health check
if check_endpoint "/health" "200" "Basic health check"; then
    ((PASSED_CHECKS++))
else
    ((FAILED_CHECKS++))
fi
((TOTAL_CHECKS++))

# Readiness check
if check_endpoint "/ready" "200" "Readiness check"; then
    ((PASSED_CHECKS++))
else
    ((FAILED_CHECKS++))
fi
((TOTAL_CHECKS++))

# Startup check
if check_endpoint "/startup" "200" "Startup check"; then
    ((PASSED_CHECKS++))
else
    ((FAILED_CHECKS++))
fi
((TOTAL_CHECKS++))

# Detailed health check
if check_endpoint "/health/detailed" "200" "Detailed health check"; then
    ((PASSED_CHECKS++))
else
    ((FAILED_CHECKS++))
fi
((TOTAL_CHECKS++))

# ==================== API Documentation ====================

echo ""
echo "--- API Documentation ---"

# OpenAPI docs
if check_endpoint "/api/docs" "200" "OpenAPI documentation"; then
    ((PASSED_CHECKS++))
else
    ((FAILED_CHECKS++))
fi
((TOTAL_CHECKS++))

# ReDoc
if check_endpoint "/api/redoc" "200" "ReDoc documentation"; then
    ((PASSED_CHECKS++))
else
    ((FAILED_CHECKS++))
fi
((TOTAL_CHECKS++))

# ==================== Core API Endpoints ====================

echo ""
echo "--- Core API Endpoints ---"

# Authentication health (should return 200 even without auth)
if check_endpoint "/api/v1/auth/health" "200" "Authentication service"; then
    ((PASSED_CHECKS++))
else
    ((FAILED_CHECKS++))
fi
((TOTAL_CHECKS++))

# PDFs endpoint (should return 401 without auth)
if check_endpoint "/api/v1/pdfs" "401" "PDFs endpoint (auth required)"; then
    ((PASSED_CHECKS++))
else
    ((FAILED_CHECKS++))
fi
((TOTAL_CHECKS++))

# Chapters endpoint (should return 401 without auth)
if check_endpoint "/api/v1/chapters" "401" "Chapters endpoint (auth required)"; then
    ((PASSED_CHECKS++))
else
    ((FAILED_CHECKS++))
fi
((TOTAL_CHECKS++))

# Search endpoint (should return 401 without auth)
if check_endpoint "/api/v1/search" "401" "Search endpoint (auth required)"; then
    ((PASSED_CHECKS++))
else
    ((FAILED_CHECKS++))
fi
((TOTAL_CHECKS++))

# ==================== Service Health ====================

echo ""
echo "--- Service Health ---"

# Check database connectivity
if check_json_field "/ready" "checks.database.status" "healthy" "Database connectivity"; then
    ((PASSED_CHECKS++))
else
    ((FAILED_CHECKS++))
fi
((TOTAL_CHECKS++))

# Check Redis connectivity (degraded is acceptable)
REDIS_STATUS=$(curl -s --max-time ${TIMEOUT} "${API_URL}/ready" | jq -r ".checks.redis.status" 2>/dev/null || echo "unknown")
if [[ "${REDIS_STATUS}" =~ ^(healthy|degraded)$ ]]; then
    log_info "  ✓ Redis connectivity (${REDIS_STATUS})"
    ((PASSED_CHECKS++))
else
    log_warn "  ⚠ Redis connectivity (${REDIS_STATUS})"
    ((FAILED_CHECKS++))
fi
((TOTAL_CHECKS++))

# ==================== Performance Checks ====================

echo ""
echo "--- Performance Checks ---"

# Response time check
log_info "Checking: Response time"
RESPONSE_TIME=$(curl -o /dev/null -s -w "%{time_total}" --max-time ${TIMEOUT} "${API_URL}/health" || echo "0")
if (( $(echo "${RESPONSE_TIME} < 2.0" | bc -l) )); then
    log_info "  ✓ Response time: ${RESPONSE_TIME}s (< 2s)"
    ((PASSED_CHECKS++))
else
    log_warn "  ⚠ Response time: ${RESPONSE_TIME}s (slow)"
    ((FAILED_CHECKS++))
fi
((TOTAL_CHECKS++))

# ==================== Container Health ====================

echo ""
echo "--- Container Health ---"

# Check if containers are running
log_info "Checking: Container status"

REQUIRED_CONTAINERS=(
    "neurocore_api"
    "neurocore_postgres"
    "neurocore_redis"
)

CONTAINERS_OK=true
for CONTAINER in "${REQUIRED_CONTAINERS[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
        log_info "  ✓ ${CONTAINER} is running"
    else
        log_error "  ✗ ${CONTAINER} is not running"
        CONTAINERS_OK=false
    fi
done

if [ "${CONTAINERS_OK}" = "true" ]; then
    ((PASSED_CHECKS++))
else
    ((FAILED_CHECKS++))
fi
((TOTAL_CHECKS++))

# ==================== Resource Checks ====================

echo ""
echo "--- Resource Checks ---"

# Disk space
log_info "Checking: Disk space"
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "${DISK_USAGE}" -lt 90 ]; then
    log_info "  ✓ Disk usage: ${DISK_USAGE}% (< 90%)"
    ((PASSED_CHECKS++))
else
    log_warn "  ⚠ Disk usage: ${DISK_USAGE}% (high)"
    ((FAILED_CHECKS++))
fi
((TOTAL_CHECKS++))

# Memory usage
log_info "Checking: Memory usage"
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ "${MEMORY_USAGE}" -lt 90 ]; then
    log_info "  ✓ Memory usage: ${MEMORY_USAGE}% (< 90%)"
    ((PASSED_CHECKS++))
else
    log_warn "  ⚠ Memory usage: ${MEMORY_USAGE}% (high)"
    ((FAILED_CHECKS++))
fi
((TOTAL_CHECKS++))

# ==================== Summary ====================

echo ""
echo "========================================="
echo "  Health Check Summary"
echo "========================================="
echo ""
echo "Total checks: ${TOTAL_CHECKS}"
echo -e "${GREEN}Passed: ${PASSED_CHECKS}${NC}"
echo -e "${RED}Failed: ${FAILED_CHECKS}${NC}"
echo ""

# Calculate success rate
SUCCESS_RATE=$(echo "scale=2; ${PASSED_CHECKS} * 100 / ${TOTAL_CHECKS}" | bc)
echo "Success rate: ${SUCCESS_RATE}%"
echo ""

# Determine overall status
if [ "${FAILED_CHECKS}" -eq 0 ]; then
    log_info "Overall status: ✓ HEALTHY"
    exit 0
elif [ "${FAILED_CHECKS}" -le 2 ]; then
    log_warn "Overall status: ⚠ DEGRADED (${FAILED_CHECKS} issues)"
    exit 0
else
    log_error "Overall status: ✗ UNHEALTHY (${FAILED_CHECKS} failures)"
    exit 1
fi
