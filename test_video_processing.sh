#!/bin/bash
# Test script for video processing flow
# This simulates the complete flow: create job -> upload -> process -> check status

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Video Processing Flow Test ===${NC}\n"

# Get API URL from CDK stack
STAGE="${STAGE:-dev}"
STACK_NAME="VideoProcessingStack-${STAGE}"

echo -e "${YELLOW}Getting API URL from stack: ${STACK_NAME}${NC}"
API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
    --output text 2>/dev/null || echo "")

if [ -z "$API_URL" ]; then
    echo -e "${YELLOW}Could not get API URL from stack. Trying config.json...${NC}"
    if [ -f "config.json" ]; then
        API_URL=$(python3 -c "import json; print(json.load(open('config.json'))['ApiUrl'])")
    else
        echo "Error: Could not find API URL. Please deploy the stack first."
        exit 1
    fi
fi

echo -e "${GREEN}API URL: ${API_URL}${NC}\n"

# Step 1: Create job and get presigned URL
echo -e "${BLUE}Step 1: Creating job and getting presigned URL...${NC}"
JOB_RESPONSE=$(curl -s -X POST "${API_URL}/jobs" \
    -H "Content-Type: application/json" \
    -d '{
        "filename": "test-video.mp4"
    }')

echo "Response: $JOB_RESPONSE" | python3 -m json.tool

JOB_ID=$(echo "$JOB_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])")
PRESIGNED_URL=$(echo "$JOB_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['presigned_url'])")

echo -e "${GREEN}Job ID: ${JOB_ID}${NC}"
echo -e "${GREEN}Presigned URL: ${PRESIGNED_URL:0:80}...${NC}\n"

# Step 2: Upload a small test file (simulating video upload)
echo -e "${BLUE}Step 2: Uploading test file to S3...${NC}"
# Create a small test file
echo "This is a simulated video file for testing" > /tmp/test-video.mp4

curl -X PUT "$PRESIGNED_URL" \
    --upload-file /tmp/test-video.mp4 \
    -H "Content-Type: video/mp4"

echo -e "${GREEN}Upload completed${NC}\n"

# Step 3: Wait a moment for S3 event to trigger SQS
echo -e "${BLUE}Step 3: Waiting for S3 event to trigger processing...${NC}"
sleep 3

# Step 4: Poll job status
echo -e "${BLUE}Step 4: Polling job status...${NC}"
MAX_POLLS=30
POLL_COUNT=0

while [ $POLL_COUNT -lt $MAX_POLLS ]; do
    STATUS_RESPONSE=$(curl -s "${API_URL}/jobs/${JOB_ID}")
    STATUS=$(echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'UNKNOWN'))")
    
    echo -e "${YELLOW}Poll ${POLL_COUNT}: Status = ${STATUS}${NC}"
    echo "$STATUS_RESPONSE" | python3 -m json.tool
    
    if [ "$STATUS" = "COMPLETED" ]; then
        echo -e "${GREEN}✓ Processing completed!${NC}"
        break
    elif [ "$STATUS" = "FAILED" ]; then
        echo -e "${YELLOW}✗ Processing failed${NC}"
        break
    fi
    
    sleep 2
    POLL_COUNT=$((POLL_COUNT + 1))
done

if [ $POLL_COUNT -eq $MAX_POLLS ]; then
    echo -e "${YELLOW}Timeout waiting for processing to complete${NC}"
fi

# Cleanup
rm -f /tmp/test-video.mp4

echo -e "\n${BLUE}=== Test Complete ===${NC}"
