#!/bin/bash

echo "Testing PrivateGPT Authentication Flow"
echo "======================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get JWT token
echo -e "${YELLOW}1. Getting JWT token...${NC}"
JWT_TOKEN=$(bash scripts/get-jwt-token.sh 2>/dev/null | grep -oE 'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*')

if [ -z "$JWT_TOKEN" ]; then
    echo -e "${RED}Failed to get JWT token${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Got JWT token${NC}"

# Test auth verification
echo -e "\n${YELLOW}2. Testing auth verification...${NC}"
VERIFY_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/verify \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H "Content-Type: application/json")

echo "Response: $VERIFY_RESPONSE"

if echo "$VERIFY_RESPONSE" | grep -q '"valid":true'; then
    echo -e "${GREEN}✓ Auth verification passed${NC}"
else
    echo -e "${RED}✗ Auth verification failed${NC}"
fi

# Test conversation listing
echo -e "\n${YELLOW}3. Testing conversation listing...${NC}"
CONV_RESPONSE=$(curl -s -X GET "http://localhost:8000/api/chat/conversations?limit=5" \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H "Content-Type: application/json")

if echo "$CONV_RESPONSE" | grep -q '\['; then
    echo -e "${GREEN}✓ Successfully listed conversations${NC}"
    echo "Response: $CONV_RESPONSE"
else
    echo -e "${RED}✗ Failed to list conversations${NC}"
    echo "Response: $CONV_RESPONSE"
fi

# Test conversation creation
echo -e "\n${YELLOW}4. Testing conversation creation...${NC}"
CONV_CREATE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/chat/conversations \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "title": "Test Conversation",
        "model_name": "dolphin-phi:2.7b",
        "data": {}
    }')

if echo "$CONV_CREATE_RESPONSE" | grep -q '"id"'; then
    echo -e "${GREEN}✓ Successfully created conversation${NC}"
    CONV_ID=$(echo "$CONV_CREATE_RESPONSE" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
    echo "Conversation ID: $CONV_ID"
    
    # Test prepare stream
    echo -e "\n${YELLOW}5. Testing prepare stream...${NC}"
    STREAM_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/chat/conversations/$CONV_ID/prepare-stream" \
        -H "Authorization: Bearer $JWT_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "message": "Hello, this is a test",
            "model": "dolphin-phi:2.7b"
        }')
    
    if echo "$STREAM_RESPONSE" | grep -q '"stream_token"'; then
        echo -e "${GREEN}✓ Successfully prepared stream${NC}"
        echo "Stream response: $STREAM_RESPONSE"
    else
        echo -e "${RED}✗ Failed to prepare stream${NC}"
        echo "Response: $STREAM_RESPONSE"
    fi
else
    echo -e "${RED}✗ Failed to create conversation${NC}"
    echo "Response: $CONV_CREATE_RESPONSE"
fi

echo -e "\n${YELLOW}Authentication flow test complete!${NC}"