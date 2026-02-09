#!/bin/bash

# Test script for AWS Serverless API
# This script tests all API endpoints

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get API URL from CDK output or use default
if [ -z "$API_URL" ]; then
    echo -e "${YELLOW}⚠️  API_URL not set. Getting from CDK stack...${NC}"
    API_URL=$(aws cloudformation describe-stacks \
        --stack-name AwsServerlessApiStack \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$API_URL" ]; then
        echo -e "${YELLOW}⚠️  Could not get API URL from stack.${NC}"
        echo "Please set API_URL environment variable:"
        echo "  export API_URL=https://your-api-id.execute-api.region.amazonaws.com/"
        exit 1
    fi
fi

echo -e "${BLUE}🧪 Testing AWS Serverless API${NC}"
echo "=================================="
echo -e "API URL: ${GREEN}$API_URL${NC}"
echo ""

# Test 1: Root endpoint (GET)
echo -e "${BLUE}Test 1: GET /${NC}"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_URL")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Status: $HTTP_CODE${NC}"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo -e "${YELLOW}⚠️  Status: $HTTP_CODE${NC}"
    echo "$BODY"
fi
echo ""

# Test 2: Hello endpoint (GET)
echo -e "${BLUE}Test 2: GET /hello${NC}"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_URL/hello")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Status: $HTTP_CODE${NC}"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo -e "${YELLOW}⚠️  Status: $HTTP_CODE${NC}"
    echo "$BODY"
fi
echo ""

# Test 3: Hello endpoint (POST)
echo -e "${BLUE}Test 3: POST /hello${NC}"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"name": "World", "test": true}' \
    "$API_URL/hello")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Status: $HTTP_CODE${NC}"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo -e "${YELLOW}⚠️  Status: $HTTP_CODE${NC}"
    echo "$BODY"
fi
echo ""

# Test 4: Invalid endpoint (should return 404 or similar)
echo -e "${BLUE}Test 4: GET /nonexistent${NC}"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_URL/nonexistent")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')

echo -e "${BLUE}Status: $HTTP_CODE${NC}"
echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
echo ""

echo -e "${GREEN}✨ Testing complete!${NC}"
echo ""
echo "To test with a custom API URL:"
echo "  export API_URL=https://your-api-id.execute-api.region.amazonaws.com/"
echo "  ./test_api.sh"
