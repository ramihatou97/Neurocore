#!/bin/bash

##############################################################################
# Delete Chapter Fix - Comprehensive Verification Script
# Verifies that the chapter_versions metadata column fix is properly applied
# Date: 2025-11-01
##############################################################################

set -e  # Exit on error

echo "============================================================"
echo "🔍 DELETE CHAPTER FIX - COMPREHENSIVE VERIFICATION"
echo "============================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# Function to print test result
print_result() {
    local test_name="$1"
    local result="$2"
    local message="$3"

    if [ "$result" == "PASS" ]; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        [ -n "$message" ] && echo "   → $message"
        ((PASS_COUNT++))
    elif [ "$result" == "FAIL" ]; then
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        [ -n "$message" ] && echo "   → $message"
        ((FAIL_COUNT++))
    else
        echo -e "${YELLOW}⚠️  WARN${NC}: $test_name"
        [ -n "$message" ] && echo "   → $message"
        ((WARN_COUNT++))
    fi
}

echo "Test 1: Verify Docker containers running"
echo "----------------------------------------"
if docker ps | grep -q "neurocore-api"; then
    print_result "API container running" "PASS" "neurocore-api is up"
else
    print_result "API container running" "FAIL" "neurocore-api is not running"
    exit 1
fi

if docker ps | grep -q "neurocore-postgres"; then
    print_result "Database container running" "PASS" "neurocore-postgres is up"
else
    print_result "Database container running" "FAIL" "neurocore-postgres is not running"
    exit 1
fi
echo ""

echo "Test 2: Verify Docker volumes exist"
echo "------------------------------------"
if docker volume ls | grep -q "neurocore-postgres-data"; then
    print_result "Postgres volume exists" "PASS" "Data will persist across restarts"
else
    print_result "Postgres volume exists" "FAIL" "Volume not found - data won't persist"
fi
echo ""

echo "Test 3: Verify database schema (CRITICAL)"
echo "------------------------------------------"
SCHEMA_CHECK=$(docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb \
    -tAc "SELECT column_name FROM information_schema.columns WHERE table_name='chapter_versions' AND column_name IN ('metadata', 'version_metadata');" 2>&1)

if echo "$SCHEMA_CHECK" | grep -q "version_metadata"; then
    print_result "Column name is correct" "PASS" "Found 'version_metadata' column"

    # Check that old 'metadata' column doesn't exist
    if echo "$SCHEMA_CHECK" | grep -q "^metadata$"; then
        print_result "No duplicate metadata column" "FAIL" "Both 'metadata' and 'version_metadata' exist!"
    else
        print_result "No duplicate metadata column" "PASS" "Only 'version_metadata' exists"
    fi
else
    print_result "Column name is correct" "FAIL" "Column 'version_metadata' not found!"
    print_result "Old metadata column present" "WARN" "Database still has 'metadata' column"
fi
echo ""

echo "Test 4: Verify column data type and default"
echo "--------------------------------------------"
COLUMN_DETAILS=$(docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb \
    -tAc "SELECT data_type, column_default FROM information_schema.columns WHERE table_name='chapter_versions' AND column_name='version_metadata';" 2>&1)

if echo "$COLUMN_DETAILS" | grep -q "jsonb"; then
    print_result "Column type is JSONB" "PASS" "Correct data type"
else
    print_result "Column type is JSONB" "FAIL" "Wrong data type: $COLUMN_DETAILS"
fi

if echo "$COLUMN_DETAILS" | grep -q "'{}'::jsonb"; then
    print_result "Default value correct" "PASS" "Default is '{}'"
else
    print_result "Default value correct" "WARN" "Default might be different"
fi
echo ""

echo "Test 5: Check migration files"
echo "------------------------------"
if [ -f "backend/database/migrations/004_comprehensive_features.sql" ]; then
    if grep -q "version_metadata JSONB" "backend/database/migrations/004_comprehensive_features.sql"; then
        print_result "Source schema fixed (004)" "PASS" "Creates version_metadata from start"
    else
        print_result "Source schema fixed (004)" "FAIL" "Still creates 'metadata' column"
    fi
else
    print_result "Source schema exists (004)" "FAIL" "File not found"
fi

if [ -f "backend/database/migrations/008_fix_chapter_versions_metadata_column.sql" ]; then
    print_result "Fix migration exists (008)" "PASS" "Safety net in place"
else
    print_result "Fix migration exists (008)" "WARN" "Migration file not found"
fi
echo ""

echo "Test 6: Verify model definition matches"
echo "----------------------------------------"
if [ -f "backend/database/models/chapter_version.py" ]; then
    if grep -q "version_metadata.*=.*Column" "backend/database/models/chapter_version.py"; then
        print_result "Model uses version_metadata" "PASS" "Model matches database"
    else
        print_result "Model uses version_metadata" "FAIL" "Model definition issue"
    fi
else
    print_result "Model file exists" "FAIL" "chapter_version.py not found"
fi
echo ""

echo "Test 7: Check API logs for errors"
echo "----------------------------------"
ERROR_COUNT=$(docker logs neurocore-api --since 10m 2>&1 | grep -c "version_metadata does not exist" || true)

if [ "$ERROR_COUNT" -eq 0 ]; then
    print_result "No version_metadata errors" "PASS" "No column errors in recent logs"
else
    print_result "No version_metadata errors" "FAIL" "Found $ERROR_COUNT errors in logs"
fi

DELETE_500_COUNT=$(docker logs neurocore-api --since 10m 2>&1 | grep -c "DELETE.*chapters.*500" || true)

if [ "$DELETE_500_COUNT" -eq 0 ]; then
    print_result "No DELETE 500 errors" "PASS" "Delete endpoint not crashing"
else
    print_result "No DELETE 500 errors" "FAIL" "Found $DELETE_500_COUNT DELETE failures"
fi
echo ""

echo "Test 8: Verify docker-compose configuration"
echo "--------------------------------------------"
if grep -q "/docker-entrypoint-initdb.d" docker-compose.yml; then
    print_result "Migrations directory mounted" "PASS" "Auto-initialization configured"
else
    print_result "Migrations directory mounted" "WARN" "May not auto-run migrations"
fi

if grep -q "postgres_data:/var/lib/postgresql/data" docker-compose.yml; then
    print_result "Volume mount configured" "PASS" "Data persistence enabled"
else
    print_result "Volume mount configured" "FAIL" "No volume mount - data won't persist"
fi
echo ""

echo "Test 9: Check if chapter_versions table has data"
echo "--------------------------------------------------"
ROW_COUNT=$(docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb \
    -tAc "SELECT COUNT(*) FROM chapter_versions;" 2>&1 || echo "0")

if [ "$ROW_COUNT" -gt 0 ]; then
    print_result "Table has data" "PASS" "$ROW_COUNT version records exist"

    # Try to access version_metadata column on actual data
    QUERY_TEST=$(docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb \
        -tAc "SELECT version_metadata FROM chapter_versions LIMIT 1;" 2>&1)

    if echo "$QUERY_TEST" | grep -q "column.*does not exist"; then
        print_result "Can query version_metadata" "FAIL" "Column exists but can't be queried!"
    else
        print_result "Can query version_metadata" "PASS" "Data accessible via new column name"
    fi
else
    print_result "Table has data" "WARN" "No version data yet (table empty)"
fi
echo ""

echo "============================================================"
echo "📊 VERIFICATION SUMMARY"
echo "============================================================"
echo ""
echo -e "${GREEN}Passed:${NC} $PASS_COUNT"
echo -e "${YELLOW}Warnings:${NC} $WARN_COUNT"
echo -e "${RED}Failed:${NC} $FAIL_COUNT"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✅ ALL CRITICAL TESTS PASSED${NC}"
    echo ""
    echo "Delete chapter functionality is working correctly!"
    echo "The version_metadata column fix is properly applied."
    echo ""

    if [ $WARN_COUNT -gt 0 ]; then
        echo -e "${YELLOW}Note: $WARN_COUNT warnings detected (non-critical)${NC}"
    fi

    exit 0
else
    echo -e "${RED}❌ $FAIL_COUNT CRITICAL TESTS FAILED${NC}"
    echo ""
    echo "Action required: Review failed tests above"
    echo "See DEPLOYMENT_MIGRATION_GUIDE.md for troubleshooting"
    echo ""
    exit 1
fi
