#!/bin/bash

# Test script for book title extraction fix
# This uploads a test PDF with a known filename to verify the title is extracted correctly

echo "========================================"
echo "Testing Book Title Extraction"
echo "========================================"
echo ""

# Get auth token
echo "1. Logging in..."
TOKEN=$(curl -s -X POST "http://localhost:8002/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test123" | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ Login failed!"
  exit 1
fi
echo "✅ Login successful"
echo ""

# Find a PDF to upload (use an existing one or create a test PDF)
TEST_PDF="/Users/ramihatoum/Desktop/Test PDFs/Keyhole Approaches in Neurosurgery - Volume 1.pdf"

if [ ! -f "$TEST_PDF" ]; then
  echo "❌ Test PDF not found: $TEST_PDF"
  echo "Please specify a valid PDF path"
  exit 1
fi

echo "2. Uploading PDF: $(basename "$TEST_PDF")"
UPLOAD_RESPONSE=$(curl -s -X POST "http://localhost:8002/textbooks/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@$TEST_PDF")

echo "Upload response:"
echo "$UPLOAD_RESPONSE" | jq '.'
echo ""

# Extract book_id
BOOK_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.book_id')

if [ "$BOOK_ID" = "null" ] || [ -z "$BOOK_ID" ]; then
  echo "❌ Upload failed!"
  exit 1
fi

echo "✅ Upload successful, book_id: $BOOK_ID"
echo ""

# Wait a moment for processing
sleep 2

# Get book details to check title
echo "3. Checking book title..."
BOOK_DETAILS=$(curl -s -X GET "http://localhost:8002/textbooks/books/$BOOK_ID" \
  -H "Authorization: Bearer $TOKEN")

echo "Book details:"
echo "$BOOK_DETAILS" | jq '{id, title, authors, total_pages, total_chapters}'
echo ""

# Extract title and check if it's the original filename (not UUID)
TITLE=$(echo "$BOOK_DETAILS" | jq -r '.title')
echo "Book title: $TITLE"

if [[ "$TITLE" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
  echo "❌ FAIL: Title is still a UUID!"
  echo "   Expected: Keyhole Approaches in Neurosurgery - Volume 1"
  echo "   Got:      $TITLE"
else
  echo "✅ SUCCESS: Title is using original filename!"
  echo "   Title: $TITLE"
fi

echo ""
echo "========================================"
echo "Test complete"
echo "========================================"
