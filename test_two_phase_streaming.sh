#!/bin/bash

# Test script for two-phase streaming

set -e

echo "🧪 Testing Two-Phase Streaming Architecture"
echo "=========================================="

# Get auth token first
echo "1. Getting authentication token..."
AUTH_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@admin.com", "password": "admin"}')

TOKEN=$(echo $AUTH_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Failed to get auth token"
    echo "Response: $AUTH_RESPONSE"
    exit 1
fi

echo "✅ Got auth token: ${TOKEN:0:20}..."

# Create a test conversation
echo "2. Creating test conversation..."
CONV_RESPONSE=$(curl -s -X POST http://localhost:8000/api/chat/conversations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Streaming Conversation"}')

CONVERSATION_ID=$(echo $CONV_RESPONSE | jq -r '.id')

if [ "$CONVERSATION_ID" = "null" ] || [ -z "$CONVERSATION_ID" ]; then
    echo "❌ Failed to create conversation"
    echo "Response: $CONV_RESPONSE"
    exit 1
fi

echo "✅ Created conversation: $CONVERSATION_ID"

# Phase 1: Prepare streaming
echo "3. Phase 1 - Preparing stream..."
PREPARE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/chat/conversations/$CONVERSATION_ID/messages/prepare \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello! Can you tell me about yourself?", "model": "tinydolphin:latest"}')

echo "Prepare response: $PREPARE_RESPONSE"

STREAM_TOKEN=$(echo $PREPARE_RESPONSE | jq -r '.stream_token')
STREAM_URL=$(echo $PREPARE_RESPONSE | jq -r '.stream_url')

if [ "$STREAM_TOKEN" = "null" ] || [ -z "$STREAM_TOKEN" ]; then
    echo "❌ Failed to prepare stream"
    echo "Response: $PREPARE_RESPONSE"
    exit 1
fi

echo "✅ Stream prepared. Token: ${STREAM_TOKEN:0:20}..."
echo "✅ Stream URL: $STREAM_URL"

# Phase 2: Stream the response
echo "4. Phase 2 - Streaming response..."
echo "Connecting to stream..."

curl -s -N -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000$STREAM_URL" | while IFS= read -r line; do
    if [[ $line == data:* ]]; then
        # Extract the JSON data after "data: "
        json_data="${line:6}"
        if [[ $json_data == "{"* ]]; then
            echo "📡 $json_data"
        fi
    fi
done

echo ""
echo "✅ Two-phase streaming test completed!"