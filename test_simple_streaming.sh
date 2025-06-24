#\!/bin/bash

# Test simple streaming endpoint

# Get auth token first
echo "Getting auth token..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@admin.com", "password": "admin"}' | jq -r '.access_token')

echo "Token: ${TOKEN:0:20}..."

# Use existing conversation or create one
CONVERSATION_ID="84d10177-8dc8-4e55-a9be-b1aa00aeef99"

# Test streaming
echo -e "\nTesting streaming endpoint..."
echo "URL: http://localhost:8000/api/chat/conversations/$CONVERSATION_ID/chat/stream?token=$TOKEN"

# Send message and stream response
curl -N -X POST "http://localhost:8000/api/chat/conversations/$CONVERSATION_ID/chat/stream?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "Hello\! What model are you?",
    "model": "tinyllama:1.1b"
  }' 2>&1 | head -30
