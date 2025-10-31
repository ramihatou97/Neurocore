#!/bin/bash
# Phase 5 Background Processing Pipeline Test Script

set -e

echo "================================================================================================"
echo "  Phase 5: Background Processing Pipeline End-to-End Test"
echo "================================================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

API_URL="http://localhost:8002/api/v1"

echo -e "${BLUE}Step 1: Get Authentication Token${NC}"

# Generate unique email for this test run
TEST_EMAIL="phase5_test_$(date +%s)@neurocore.ai"

REGISTER_RESPONSE=$(curl -s -X POST "${API_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "email": "${TEST_EMAIL}",
  "password": "TestPass123!",
  "full_name": "Phase 5 Test User"
}
EOF
)

echo "$REGISTER_RESPONSE" | python3 -m json.tool || echo "$REGISTER_RESPONSE"

# Extract access token from registration response
ACCESS_TOKEN=$(echo "$REGISTER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null || echo "")

if [ -z "$ACCESS_TOKEN" ]; then
  echo -e "${RED}✗ Failed to get access token${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Access token obtained (user: ${TEST_EMAIL})${NC}"
echo ""

echo -e "${BLUE}Step 2: Upload Test PDF${NC}"
# Use one of the existing PDFs from host path
TEST_PDF="./storage/pdfs/2025/10/27/e9ae1c83-2e0f-49ad-8bf5-ad5c2ca43bb4.pdf"

if [ ! -f "$TEST_PDF" ]; then
  echo -e "${RED}✗ Test PDF not found: ${TEST_PDF}${NC}"
  exit 1
fi

echo "Uploading: $(basename $TEST_PDF)"
UPLOAD_RESPONSE=$(curl -s -X POST "${API_URL}/pdfs/upload" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@${TEST_PDF}")

echo "$UPLOAD_RESPONSE" | python3 -m json.tool
PDF_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")

if [ -z "$PDF_ID" ]; then
  echo -e "${RED}✗ Failed to upload PDF${NC}"
  exit 1
fi

echo -e "${GREEN}✓ PDF uploaded successfully: ${PDF_ID}${NC}"
echo ""

echo -e "${BLUE}Step 3: Trigger Background Processing${NC}"
PROCESS_RESPONSE=$(curl -s -X POST "${API_URL}/pdfs/${PDF_ID}/process" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "$PROCESS_RESPONSE" | python3 -m json.tool
TASK_ID=$(echo "$PROCESS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])" 2>/dev/null || echo "")

if [ -z "$TASK_ID" ]; then
  echo -e "${YELLOW}⚠ Task ID not found in response (may be processing inline)${NC}"
else
  echo -e "${GREEN}✓ Background processing triggered: ${TASK_ID}${NC}"
fi
echo ""

echo -e "${BLUE}Step 4: Monitor Task Progress${NC}"
echo "Waiting for processing to complete..."

for i in {1..30}; do
  sleep 2

  if [ -n "$TASK_ID" ]; then
    TASK_STATUS=$(curl -s "${API_URL}/tasks/${TASK_ID}" \
      -H "Authorization: Bearer $ACCESS_TOKEN")

    STATUS=$(echo "$TASK_STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "unknown")
    PROGRESS=$(echo "$TASK_STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('progress', 0))" 2>/dev/null || echo "0")

    echo -e "${BLUE}[$i/30]${NC} Status: $STATUS, Progress: $PROGRESS%"

    if [ "$STATUS" = "completed" ]; then
      echo -e "${GREEN}✓ Task completed successfully!${NC}"
      break
    elif [ "$STATUS" = "failed" ]; then
      echo -e "${RED}✗ Task failed${NC}"
      echo "$TASK_STATUS" | python3 -m json.tool
      break
    fi
  else
    # Check PDF status directly
    PDF_STATUS=$(curl -s "${API_URL}/pdfs/${PDF_ID}" \
      -H "Authorization: Bearer $ACCESS_TOKEN")

    INDEXING_STATUS=$(echo "$PDF_STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('indexing_status', 'unknown'))" 2>/dev/null || echo "unknown")
    echo -e "${BLUE}[$i/30]${NC} PDF Status: $INDEXING_STATUS"

    if [ "$INDEXING_STATUS" = "completed" ]; then
      echo -e "${GREEN}✓ PDF processing completed!${NC}"
      break
    fi
  fi
done

echo ""
echo -e "${BLUE}Step 5: Verify Results${NC}"

# Check PDF details
echo "PDF Details:"
PDF_DETAILS=$(curl -s "${API_URL}/pdfs/${PDF_ID}" \
  -H "Authorization: Bearer $ACCESS_TOKEN")
echo "$PDF_DETAILS" | python3 -m json.tool

# Check database directly
echo ""
echo "Database Verification:"
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT
  id,
  filename,
  indexing_status,
  text_extracted,
  images_extracted,
  embeddings_generated,
  total_pages
FROM pdfs
WHERE id = '$PDF_ID';"

echo ""
echo "Images Extracted:"
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT COUNT(*) as total_images
FROM images
WHERE pdf_id = '$PDF_ID';"

echo ""
echo -e "${GREEN}================================================================================================"
echo "  Phase 5 Pipeline Test Complete"
echo "================================================================================================${NC}"
