#!/bin/bash
# Test chapter delete functionality

API_URL="http://localhost:8002/api/v1"

echo "=== Testing Chapter Delete Functionality ==="
echo ""

# Try to login with test user
echo "1. Attempting login..."
LOGIN_RESPONSE=$(curl -s -X POST ${API_URL}/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@neurocore.ai","password":"testpass123"}')

echo "Login response:"
echo "$LOGIN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$LOGIN_RESPONSE"
echo ""

# Extract token
TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c 'import sys, json; print(json.load(sys.stdin).get("access_token", ""))' 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to get auth token"
    exit 1
fi

echo "✅ Got auth token (length: ${#TOKEN})"
echo ""

# Get chapter ID
CHAPTER_ID="15bcf00c-a635-49d2-80d0-b0681253ffab"
echo "2. Testing delete for chapter: $CHAPTER_ID"
echo ""

# Try to delete
DELETE_RESPONSE=$(curl -s -X DELETE ${API_URL}/chapters/${CHAPTER_ID} \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json')

echo "Delete response:"
echo "$DELETE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$DELETE_RESPONSE"
echo ""

# Check if delete was successful
if echo "$DELETE_RESPONSE" | grep -q "deleted successfully"; then
    echo "✅ Chapter deleted successfully!"
else
    echo "❌ Delete failed or returned error"
fi
