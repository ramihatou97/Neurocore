#!/bin/bash
#
# Cleanup Old Containers Script
# Safely removes old "theneurosurgicalcoreofknowledge" containers while preserving DCS
#

set -e  # Exit on error

echo "======================================"
echo "Neurocore Container Cleanup Script"
echo "======================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

print_info "Docker is running"
echo ""

# List current containers
print_info "Current Docker containers:"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Check for old containers
OLD_CONTAINERS=$(docker ps -a --filter "name=neurosurgery-" --format "{{.Names}}" 2>/dev/null || true)

if [ -z "$OLD_CONTAINERS" ]; then
    print_info "No old 'neurosurgery-*' containers found to clean up"
else
    print_warning "Found old containers to remove:"
    echo "$OLD_CONTAINERS"
    echo ""

    read -p "Do you want to stop and remove these containers? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Stopping old containers..."
        docker ps -a --filter "name=neurosurgery-" --format "{{.Names}}" | xargs -r docker stop 2>/dev/null || true

        print_info "Removing old containers..."
        docker ps -a --filter "name=neurosurgery-" --format "{{.Names}}" | xargs -r docker rm 2>/dev/null || true

        print_info "Old containers removed successfully"
    else
        print_warning "Skipping container cleanup"
    fi
fi

echo ""

# Check for neurocore containers
NEUROCORE_CONTAINERS=$(docker ps -a --filter "name=neurocore-" --format "{{.Names}}" 2>/dev/null || true)

if [ -n "$NEUROCORE_CONTAINERS" ]; then
    print_info "Neurocore containers found:"
    docker ps -a --filter "name=neurocore-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""

    # Check if they're running
    RUNNING_NEUROCORE=$(docker ps --filter "name=neurocore-" --format "{{.Names}}" 2>/dev/null | wc -l)

    if [ "$RUNNING_NEUROCORE" -gt 0 ]; then
        print_info "$RUNNING_NEUROCORE neurocore containers are running"
    else
        print_warning "Neurocore containers exist but are not running"
        read -p "Do you want to remove them and start fresh? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Removing stopped neurocore containers..."
            docker ps -a --filter "name=neurocore-" --format "{{.Names}}" | xargs -r docker rm 2>/dev/null || true
            print_info "Neurocore containers removed. Run 'docker-compose up -d' to start fresh"
        fi
    fi
fi

echo ""

# Check port allocation
print_info "Checking port allocation..."
echo ""

print_info "Port 5432 (System PostgreSQL):"
lsof -i :5432 2>/dev/null || echo "  Not in use"

print_info "Port 5433 (DCS PostgreSQL):"
lsof -i :5433 2>/dev/null || echo "  Not in use"

print_info "Port 5434 (Neurocore PostgreSQL - TARGET):"
lsof -i :5434 2>/dev/null || echo "  Not in use"

print_info "Port 6379 (System Redis - if any):"
lsof -i :6379 2>/dev/null || echo "  Not in use"

print_info "Port 6380 (DCS Redis):"
lsof -i :6380 2>/dev/null || echo "  Not in use"

print_info "Port 6381 (Neurocore Redis - TARGET):"
lsof -i :6381 2>/dev/null || echo "  Not in use"

print_info "Port 8002 (Neurocore API):"
lsof -i :8002 2>/dev/null || echo "  Not in use"

print_info "Port 3002 (Neurocore Frontend):"
lsof -i :3002 2>/dev/null || echo "  Not in use"

print_info "Port 5555 (Neurocore Flower):"
lsof -i :5555 2>/dev/null || echo "  Not in use"

echo ""

# Check DCS containers (should not be touched)
DCS_CONTAINERS=$(docker ps --filter "name=dcs-" --format "{{.Names}}" 2>/dev/null | wc -l)
if [ "$DCS_CONTAINERS" -gt 0 ]; then
    print_info "✅ DCS containers are running (preserved)"
    docker ps --filter "name=dcs-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
else
    print_info "No DCS containers running (this is fine if you haven't started DCS)"
fi

echo ""
print_info "Cleanup complete!"
print_info ""
print_info "Next steps:"
print_info "  1. Review .env file to ensure ports are: 5434, 6381, 8002, 3002, 5555"
print_info "  2. Run: docker-compose up -d"
print_info "  3. Check health: docker-compose ps"
print_info "  4. View logs: docker-compose logs -f"
echo ""
