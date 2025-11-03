#!/bin/bash

# Real-world textbook upload test script
# Tests the complete upload pipeline with a real neurosurgery PDF

set -e  # Exit on error

# Configuration
API_URL="http://localhost:8002"
EMAIL="test.upload@neurocore.com"
PASSWORD="TestUpload123!"
FULL_NAME="Upload Test User"
PDF_FILE="/Users/ramihatoum/Desktop/Neurosurgery /reference library /Entire books/Keyhole Approaches in Neurosurgery - Volume 1 (2008) - Perneczky.pdf"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Real-World Textbook Upload Test${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if PDF exists
if [ ! -f "$PDF_FILE" ]; then
    echo -e "${RED}✗ PDF file not found: ${PDF_FILE}${NC}"
    exit 1
fi

FILE_SIZE=$(du -h "$PDF_FILE" | cut -f1)
echo -e "${GREEN}✓ Found PDF: $(basename "$PDF_FILE") (${FILE_SIZE})${NC}"
echo ""

# Step 1: Check API health
echo -e "${YELLOW}Step 1: Checking API health...${NC}"
HEALTH=$(curl -s "${API_URL}/health")
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✓ API is healthy${NC}"
else
    echo -e "${RED}✗ API is not healthy${NC}"
    echo "$HEALTH"
    exit 1
fi
echo ""

# Step 2: Register or Login
echo -e "${YELLOW}Step 2: Authenticating...${NC}"

# Try to login first
LOGIN_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"${EMAIL}\", \"password\": \"${PASSWORD}\"}" 2>&1)

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null || echo "")

if [ -z "$ACCESS_TOKEN" ]; then
    # Login failed, try to register
    echo -e "${YELLOW}→ User not found, registering new account...${NC}"

    REGISTER_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/auth/register" \
        -H "Content-Type: application/json" \
        -d "{\"email\": \"${EMAIL}\", \"password\": \"${PASSWORD}\", \"full_name\": \"${FULL_NAME}\"}")

    ACCESS_TOKEN=$(echo "$REGISTER_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null || echo "")

    if [ -z "$ACCESS_TOKEN" ]; then
        echo -e "${RED}✗ Registration failed${NC}"
        echo "$REGISTER_RESPONSE" | python3 -m json.tool
        exit 1
    fi
    echo -e "${GREEN}✓ Registered new user${NC}"
else
    echo -e "${GREEN}✓ Logged in successfully${NC}"
fi

echo -e "${BLUE}Access Token: ${ACCESS_TOKEN:0:20}...${NC}"
echo ""

# Step 3: Upload textbook
echo -e "${YELLOW}Step 3: Uploading textbook...${NC}"
echo -e "File: $(basename "$PDF_FILE")"

UPLOAD_START=$(date +%s)

UPLOAD_RESPONSE=$(curl -s -X POST "${API_URL}/api/v1/textbooks/upload" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -F "file=@${PDF_FILE}")

UPLOAD_END=$(date +%s)
UPLOAD_TIME=$((UPLOAD_END - UPLOAD_START))

echo ""
echo -e "${BLUE}Upload Response:${NC}"
echo "$UPLOAD_RESPONSE" | python3 -m json.tool

BOOK_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('book_id', ''))" 2>/dev/null || echo "")

if [ -z "$BOOK_ID" ]; then
    echo -e "${RED}✗ Upload failed${NC}"
    exit 1
fi

CHAPTERS=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('chapters_created', 0))" 2>/dev/null || echo "0")
PDF_TYPE=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('pdf_type', 'unknown'))" 2>/dev/null || echo "unknown")
PAGES=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_pages', 0))" 2>/dev/null || echo "0")
TASKS=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('embedding_tasks_queued', 0))" 2>/dev/null || echo "0")

echo ""
echo -e "${GREEN}✓ Upload successful! (${UPLOAD_TIME}s)${NC}"
echo -e "${GREEN}  Book ID: ${BOOK_ID}${NC}"
echo -e "${GREEN}  Type: ${PDF_TYPE}${NC}"
echo -e "${GREEN}  Pages: ${PAGES}${NC}"
echo -e "${GREEN}  Chapters: ${CHAPTERS}${NC}"
echo -e "${GREEN}  Embedding tasks queued: ${TASKS}${NC}"
echo ""

# Step 4: Monitor progress
echo -e "${YELLOW}Step 4: Monitoring processing progress...${NC}"
echo -e "${BLUE}(Checking every 5 seconds, Ctrl+C to stop)${NC}"
echo ""

MONITOR_START=$(date +%s)
MAX_CHECKS=60
CHECK_INTERVAL=5

for i in $(seq 1 $MAX_CHECKS); do
    sleep $CHECK_INTERVAL

    PROGRESS_RESPONSE=$(curl -s "${API_URL}/api/v1/textbooks/upload-progress/${BOOK_ID}" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}")

    PERCENT=$(echo "$PROGRESS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('embedding_progress_percent', 0))" 2>/dev/null || echo "0")
    CHAPTERS_DONE=$(echo "$PROGRESS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('chapters_with_embeddings', 0))" 2>/dev/null || echo "0")
    TOTAL_CHAPTERS=$(echo "$PROGRESS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_chapters', 0))" 2>/dev/null || echo "0")
    CHUNKS_DONE=$(echo "$PROGRESS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_chunks_with_embeddings', 0))" 2>/dev/null || echo "0")
    TOTAL_CHUNKS=$(echo "$PROGRESS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_chunks', 0))" 2>/dev/null || echo "0")

    ELAPSED=$(($(date +%s) - MONITOR_START))

    printf "${BLUE}[%02d] ${NC}%3.0f%% | Chapters: %2d/%2d | Chunks: %4d/%4d | Elapsed: %ds\n" \
        $i "$PERCENT" "$CHAPTERS_DONE" "$TOTAL_CHAPTERS" "$CHUNKS_DONE" "$TOTAL_CHUNKS" "$ELAPSED"

    if (( $(echo "$PERCENT >= 100" | bc -l 2>/dev/null || echo "0") )); then
        echo ""
        echo -e "${GREEN}✓ Processing complete! (${ELAPSED}s total)${NC}"
        break
    fi

    if [ $i -eq $MAX_CHECKS ]; then
        echo ""
        echo -e "${YELLOW}⚠ Monitoring timeout reached (processing continues in background)${NC}"
    fi
done

echo ""

# Step 5: Get final book details
echo -e "${YELLOW}Step 5: Fetching book details...${NC}"

BOOK_DETAILS=$(curl -s "${API_URL}/api/v1/textbooks/library-stats" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo "$BOOK_DETAILS" | python3 -m json.tool

echo ""

# Step 6: Check database
echo -e "${YELLOW}Step 6: Verifying database records...${NC}"

docker exec neurocore-postgres psql -U neurocore -d neurocore -c "
SELECT
    'Book' as type,
    title,
    total_pages,
    total_chapters,
    pdf_type,
    created_at
FROM pdf_books
WHERE id = '${BOOK_ID}';
" 2>/dev/null || echo "Could not query database"

docker exec neurocore-postgres psql -U neurocore -d neurocore -c "
SELECT
    COUNT(*) as total_chapters,
    COUNT(CASE WHEN has_embeddings THEN 1 END) as with_embeddings,
    SUM(chunk_count) as total_chunks
FROM pdf_chapters
WHERE book_id = '${BOOK_ID}';
" 2>/dev/null || echo "Could not query database"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Test Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}View your book at:${NC}"
echo -e "${BLUE}http://localhost:3002/books/${BOOK_ID}${NC}"
echo ""
