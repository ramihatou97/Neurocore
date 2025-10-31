#!/bin/bash
#
# Phase 2 Week 6: Test Runner Script
# Runs integration tests and performance benchmarks for Phase 2
#
# Usage:
#   ./run_phase2_tests.sh [option]
#
# Options:
#   integration  - Run integration tests only
#   benchmarks   - Run performance benchmarks only
#   all          - Run both (default)
#   quick        - Run quick integration tests only
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_header() {
    echo -e "\n${BLUE}================================================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}================================================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Parse arguments
TEST_TYPE="${1:-all}"

print_header "Phase 2 Week 6: Integration Testing & Benchmarking"

# Check Docker containers are running
print_header "Checking System Health"
if docker ps | grep -q "neurocore-api"; then
    print_success "API container is running"
else
    print_error "API container is not running"
    print_warning "Start containers with: docker-compose up -d"
    exit 1
fi

if docker ps | grep -q "neurocore-postgres"; then
    print_success "Database container is running"
else
    print_error "Database container is not running"
    exit 1
fi

# Check Python dependencies
print_header "Checking Dependencies"
if docker exec neurocore-api python -c "import pytest" 2>/dev/null; then
    print_success "pytest is installed"
else
    print_warning "Installing pytest..."
    docker exec neurocore-api pip install pytest pytest-asyncio
fi

# Run Integration Tests
if [ "$TEST_TYPE" = "integration" ] || [ "$TEST_TYPE" = "all" ]; then
    print_header "Running Integration Tests"

    if [ "$TEST_TYPE" = "quick" ]; then
        print_warning "Running quick tests only (performance and stress tests skipped)"
        docker exec neurocore-api pytest tests/integration/test_phase2_integration.py \
            -v -s \
            -m "not performance and not stress" \
            --tb=short \
            2>&1 | tee test_integration_results.log
    else
        print_warning "This may take 10-20 minutes for full integration tests..."
        docker exec neurocore-api pytest tests/integration/test_phase2_integration.py \
            -v -s \
            --tb=short \
            2>&1 | tee test_integration_results.log
    fi

    if [ $? -eq 0 ]; then
        print_success "Integration tests completed"
    else
        print_error "Some integration tests failed - check test_integration_results.log"
    fi
fi

# Run Performance Benchmarks
if [ "$TEST_TYPE" = "benchmarks" ] || [ "$TEST_TYPE" = "all" ]; then
    print_header "Running Performance Benchmarks"

    print_warning "This may take 5-10 minutes..."
    docker exec neurocore-api python tests/benchmarks/phase2_performance_benchmarks.py \
        2>&1 | tee test_benchmark_results.log

    if [ $? -eq 0 ]; then
        print_success "Performance benchmarks completed"

        # Check if results file was created
        if docker exec neurocore-api test -f tests/benchmarks/phase2_benchmark_results.json; then
            print_success "Benchmark results saved to tests/benchmarks/phase2_benchmark_results.json"

            # Copy results to host
            docker cp neurocore-api:/app/tests/benchmarks/phase2_benchmark_results.json \
                ./phase2_benchmark_results.json 2>/dev/null || true

            if [ -f "./phase2_benchmark_results.json" ]; then
                print_success "Copied results to ./phase2_benchmark_results.json"
            fi
        fi
    else
        print_error "Performance benchmarks failed - check test_benchmark_results.log"
    fi
fi

# Summary
print_header "Testing Summary"

echo -e "Test logs saved:"
if [ -f "test_integration_results.log" ]; then
    echo -e "  - Integration tests: ${GREEN}test_integration_results.log${NC}"
fi
if [ -f "test_benchmark_results.log" ]; then
    echo -e "  - Performance benchmarks: ${GREEN}test_benchmark_results.log${NC}"
fi
if [ -f "phase2_benchmark_results.json" ]; then
    echo -e "  - Benchmark metrics: ${GREEN}phase2_benchmark_results.json${NC}"
fi

echo -e "\nNext steps:"
echo -e "  1. Review test results in log files"
echo -e "  2. Analyze performance metrics in JSON file"
echo -e "  3. Document findings in PHASE2_QUALITY_METRICS.md"
echo -e "  4. Create final Phase 2 completion report"

print_header "Testing Complete!"
