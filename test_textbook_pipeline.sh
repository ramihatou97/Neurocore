#!/bin/bash
# Phase 5 Textbook Chapter-Level Vector Search Pipeline Test
# Tests: Upload → TextbookProcessor → Chapter Detection → Embedding Generation → Vector Search

set -e

echo "================================================================================================"
echo "  Phase 5: Textbook Chapter-Level Vector Search Pipeline Test"
echo "================================================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

API_URL="http://localhost:8002/api/v1"

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 1: Authentication${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

# Generate unique email for this test run
TEST_EMAIL="textbook_test_$(date +%s)@neurocore.ai"

REGISTER_RESPONSE=$(curl -s -X POST "${API_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "email": "${TEST_EMAIL}",
  "password": "TestPass123!",
  "full_name": "Textbook Test User"
}
EOF
)

echo "$REGISTER_RESPONSE" | python3 -m json.tool || echo "$REGISTER_RESPONSE"

# Extract access token
ACCESS_TOKEN=$(echo "$REGISTER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null || echo "")

if [ -z "$ACCESS_TOKEN" ]; then
  echo -e "${RED}✗ Failed to get access token${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Access token obtained (user: ${TEST_EMAIL})${NC}"
echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 2: Baseline Library Statistics${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

STATS_BEFORE=$(curl -s "${API_URL}/textbooks/library-stats" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "$STATS_BEFORE" | python3 -m json.tool
BOOKS_BEFORE=$(echo "$STATS_BEFORE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_books', 0))" 2>/dev/null || echo "0")
CHAPTERS_BEFORE=$(echo "$STATS_BEFORE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_chapters', 0))" 2>/dev/null || echo "0")

echo -e "${GREEN}✓ Baseline: ${BOOKS_BEFORE} books, ${CHAPTERS_BEFORE} chapters${NC}"
echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 3: Single PDF Upload (Textbook Processing)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

# Use existing test PDF
TEST_PDF="./storage/pdfs/2025/10/27/e9ae1c83-2e0f-49ad-8bf5-ad5c2ca43bb4.pdf"

if [ ! -f "$TEST_PDF" ]; then
  echo -e "${RED}✗ Test PDF not found: ${TEST_PDF}${NC}"
  echo "Looking for alternative PDFs..."
  TEST_PDF=$(find ./storage/pdfs -name "*.pdf" | head -1)
  if [ -z "$TEST_PDF" ]; then
    echo -e "${RED}✗ No PDFs found in storage${NC}"
    exit 1
  fi
  echo "Using: $TEST_PDF"
fi

echo "Uploading textbook: $(basename $TEST_PDF)"
UPLOAD_RESPONSE=$(curl -s -X POST "${API_URL}/textbooks/upload" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@${TEST_PDF}")

echo "$UPLOAD_RESPONSE" | python3 -m json.tool

# Extract book ID
BOOK_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('book_id', ''))" 2>/dev/null || echo "")

if [ -z "$BOOK_ID" ]; then
  echo -e "${RED}✗ Failed to upload textbook${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Textbook uploaded successfully: ${BOOK_ID}${NC}"

# Get upload statistics
CHAPTERS_DETECTED=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('chapters_detected', 0))" 2>/dev/null || echo "0")
CLASSIFICATION=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('classification', 'unknown'))" 2>/dev/null || echo "unknown")

echo -e "  Classification: ${BLUE}${CLASSIFICATION}${NC}"
echo -e "  Chapters Detected: ${BLUE}${CHAPTERS_DETECTED}${NC}"
echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 4: Verify Chapter Detection${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

echo "Fetching book details..."
BOOK_DETAILS=$(curl -s "${API_URL}/textbooks/books/${BOOK_ID}" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "$BOOK_DETAILS" | python3 -m json.tool

echo ""
echo "Fetching chapters..."
CHAPTERS_RESPONSE=$(curl -s "${API_URL}/textbooks/books/${BOOK_ID}/chapters" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "$CHAPTERS_RESPONSE" | python3 -m json.tool

ACTUAL_CHAPTERS=$(echo "$CHAPTERS_RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('chapters', [])))" 2>/dev/null || echo "0")

echo -e "${GREEN}✓ ${ACTUAL_CHAPTERS} chapters extracted${NC}"
echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 5: Monitor Embedding Generation Progress${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

echo "Waiting for background tasks to start (5 seconds)..."
sleep 5

echo "Monitoring embedding generation progress..."
for i in {1..30}; do
  sleep 3

  PROGRESS_RESPONSE=$(curl -s "${API_URL}/textbooks/upload-progress/${BOOK_ID}" \
    -H "Authorization: Bearer $ACCESS_TOKEN")

  TOTAL=$(echo "$PROGRESS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_chapters', 0))" 2>/dev/null || echo "0")
  COMPLETED=$(echo "$PROGRESS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('chapters_with_embeddings', 0))" 2>/dev/null || echo "0")
  PERCENT=$(echo "$PROGRESS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('embedding_progress', 0))" 2>/dev/null || echo "0")
  STATUS=$(echo "$PROGRESS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('processing_status', 'unknown'))" 2>/dev/null || echo "unknown")

  echo -e "${BLUE}[$i/30]${NC} Status: $STATUS | Embeddings: $COMPLETED/$TOTAL ($PERCENT%)"

  if [ "$PERCENT" = "100.0" ] || [ "$PERCENT" = "100" ]; then
    echo -e "${GREEN}✓ All embeddings generated!${NC}"
    echo "$PROGRESS_RESPONSE" | python3 -m json.tool
    break
  fi
done

echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 6: Verify Database State${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

echo "Checking pdf_books table:"
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT
  id,
  title,
  classification,
  processing_status,
  total_chapters
FROM pdf_books
WHERE id = '$BOOK_ID';"

echo ""
echo "Checking pdf_chapters table:"
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT
  COUNT(*) as total_chapters,
  COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as chapters_with_embeddings,
  COUNT(CASE WHEN is_duplicate = true THEN 1 END) as duplicates_found
FROM pdf_chapters
WHERE book_id = '$BOOK_ID';"

echo ""
echo "Checking pdf_chunks table:"
docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
SELECT
  COUNT(*) as total_chunks,
  COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as chunks_with_embeddings
FROM pdf_chunks
WHERE chapter_id IN (SELECT id FROM pdf_chapters WHERE book_id = '$BOOK_ID');"

echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 7: Test Vector Search with Uploaded Chapters${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

echo "Testing vector search query: 'brain tumor treatment'..."
SEARCH_RESPONSE=$(curl -s -X POST "${API_URL}/search/query" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "brain tumor treatment",
    "max_results": 5
  }')

echo "$SEARCH_RESPONSE" | python3 -m json.tool

RESULTS_COUNT=$(echo "$SEARCH_RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('results', [])))" 2>/dev/null || echo "0")

echo -e "${GREEN}✓ Vector search returned ${RESULTS_COUNT} results${NC}"
echo ""

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 8: Updated Library Statistics${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"

STATS_AFTER=$(curl -s "${API_URL}/textbooks/library-stats" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "$STATS_AFTER" | python3 -m json.tool

BOOKS_AFTER=$(echo "$STATS_AFTER" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_books', 0))" 2>/dev/null || echo "0")
CHAPTERS_AFTER=$(echo "$STATS_AFTER" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_chapters', 0))" 2>/dev/null || echo "0")

echo -e "${GREEN}✓ After upload: ${BOOKS_AFTER} books, ${CHAPTERS_AFTER} chapters${NC}"
echo -e "${GREEN}  Change: +$((BOOKS_AFTER - BOOKS_BEFORE)) books, +$((CHAPTERS_AFTER - CHAPTERS_BEFORE)) chapters${NC}"
echo ""

echo -e "${GREEN}================================================================================================"
echo "  Phase 5 Textbook Pipeline Test Complete"
echo "================================================================================================${NC}"
echo ""
echo "Summary:"
echo "  ✓ Authentication successful"
echo "  ✓ Textbook uploaded: $BOOK_ID"
echo "  ✓ Classification: $CLASSIFICATION"
echo "  ✓ Chapters detected: $CHAPTERS_DETECTED"
echo "  ✓ Chapters extracted: $ACTUAL_CHAPTERS"
echo "  ✓ Embedding generation monitored"
echo "  ✓ Vector search tested: $RESULTS_COUNT results"
echo "  ✓ Library stats updated"
echo ""
