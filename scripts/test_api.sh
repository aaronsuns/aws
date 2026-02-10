#!/bin/bash

# Test script for AWS Serverless API with RDS CRUD operations
# This script tests all API endpoints including CRUD operations

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get API URL from CDK output or use default
if [ -z "$API_URL" ]; then
    echo -e "${YELLOW}⚠️  API_URL not set. Getting from CDK stack...${NC}"
    API_URL=$(aws cloudformation describe-stacks \
        --stack-name VideoProcessingStack-${STAGE:-dev} \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$API_URL" ]; then
        echo -e "${YELLOW}⚠️  Could not get API URL from stack.${NC}"
        echo "Please set API_URL environment variable:"
        echo "  export API_URL=https://your-api-id.execute-api.region.amazonaws.com/"
        exit 1
    fi
fi

echo -e "${BLUE}🧪 Testing AWS Serverless API with RDS CRUD Operations${NC}"
echo "=============================================================="
echo -e "API URL: ${GREEN}$API_URL${NC}"
echo ""

# Helper function to make API calls
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    
    echo -e "${BLUE}$description${NC}"
    
    if [ -n "$data" ]; then
        RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
            -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_URL$endpoint")
    else
        RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
            -X "$method" \
            "$API_URL$endpoint")
    fi
    
    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
    
    if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
        echo -e "${GREEN}✅ Status: $HTTP_CODE${NC}"
        echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    else
        echo -e "${RED}❌ Status: $HTTP_CODE${NC}"
        echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    fi
    echo ""
}

# Test 1: Root endpoint
api_call "GET" "/" "" "Test 1: GET / (API Info)"

# Test 2: List items (should be empty initially)
api_call "GET" "/items" "" "Test 2: GET /items (List all items - should be empty)"

# Test 3: Create item
ITEM_DATA='{"name": "Test Item", "description": "This is a test item"}'
api_call "POST" "/items" "$ITEM_DATA" "Test 3: POST /items (Create new item)"

# Extract item ID from response (if available)
CREATED_ITEM=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d "$ITEM_DATA" \
    "$API_URL/items" | python3 -c "import sys, json; print(json.load(sys.stdin).get('item', {}).get('id', ''))" 2>/dev/null || echo "")

# Test 4: List items again (should have 1 item)
api_call "GET" "/items" "" "Test 4: GET /items (List items - should have 1 item)"

# Test 5: Get item by ID
if [ -n "$CREATED_ITEM" ]; then
    api_call "GET" "/items/$CREATED_ITEM" "" "Test 5: GET /items/$CREATED_ITEM (Get item by ID)"
    
    # Test 6: Update item
    UPDATE_DATA='{"name": "Updated Item", "description": "This item has been updated"}'
    api_call "PUT" "/items/$CREATED_ITEM" "$UPDATE_DATA" "Test 6: PUT /items/$CREATED_ITEM (Update item)"
    
    # Test 7: Verify update
    api_call "GET" "/items/$CREATED_ITEM" "" "Test 7: GET /items/$CREATED_ITEM (Verify update)"
    
    # Test 8: Create another item
    ITEM_DATA2='{"name": "Second Item", "description": "Another test item"}'
    api_call "POST" "/items" "$ITEM_DATA2" "Test 8: POST /items (Create second item)"
    
    # Test 9: List all items (should have 2 items)
    api_call "GET" "/items" "" "Test 9: GET /items (List all items - should have 2 items)"
    
    # Test 10: Delete item
    api_call "DELETE" "/items/$CREATED_ITEM" "" "Test 10: DELETE /items/$CREATED_ITEM (Delete item)"
    
    # Test 11: Verify deletion
    api_call "GET" "/items" "" "Test 11: GET /items (Verify deletion - should have 1 item)"
    
    # Test 12: Try to get deleted item (should return 404)
    api_call "GET" "/items/$CREATED_ITEM" "" "Test 12: GET /items/$CREATED_ITEM (Get deleted item - should return 404)"
else
    echo -e "${YELLOW}⚠️  Could not extract item ID, skipping some tests${NC}"
fi

# Test 13: Invalid endpoint
api_call "GET" "/nonexistent" "" "Test 13: GET /nonexistent (Invalid endpoint - should return 404)"

# Test 14: Create item without name (should fail)
api_call "POST" "/items" '{"description": "Missing name"}' "Test 14: POST /items (Create without name - should fail)"

echo -e "${GREEN}✨ Testing complete!${NC}"
echo ""
echo "To test with a custom API URL:"
echo "  export API_URL=https://your-api-id.execute-api.region.amazonaws.com/"
echo "  make test"
echo "  ./scripts/test_api.sh"
echo ""
echo "To use the web UI, open ui/index.html in your browser and set the API URL."
