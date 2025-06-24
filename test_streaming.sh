#!/bin/bash

# Test two-phase streaming

# Get auth token first
echo "Getting auth token..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@admin.com", "password": "admin"}' | jq -r '.access_token')

echo "Token: ${TOKEN:0:20}..."

# Create a conversation
echo -e "\nCreating conversation..."
CONVERSATION_ID=$(curl -s -X POST http://localhost:8000/api/chat/conversations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Two-Phase Streaming", "model_name": "tinyllama:1.1b"}' | jq -r '.id')

echo "Conversation ID: $CONVERSATION_ID"

# Phase 1: Prepare stream
echo -e "\nPhase 1: Preparing stream..."
PREPARE_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/chat/conversations/$CONVERSATION_ID/messages/prepare" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello! What model are you?", "model": "tinyllama:1.1b"}')

echo "Prepare response: $PREPARE_RESPONSE"

STREAM_TOKEN=$(echo "$PREPARE_RESPONSE" | jq -r '.stream_token')
STREAM_URL=$(echo "$PREPARE_RESPONSE" | jq -r '.stream_url')

echo "Stream token: $STREAM_TOKEN"
echo "Stream URL: $STREAM_URL"

# Phase 2: Connect to stream
echo -e "\nPhase 2: Connecting to stream..."
echo "URL: http://localhost:8000${STREAM_URL}?token=$TOKEN"

# Use curl to test the stream
curl -N -H "Accept: text/event-stream" \
  "http://localhost:8000${STREAM_URL}?token=$TOKEN" 2>&1 | head -20