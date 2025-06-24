#\!/bin/bash

# Test the simple working streaming endpoint

# Get auth token first
echo "Getting auth token..."
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@admin.com", "password": "admin"}' | jq -r '.access_token')

echo "Token: ${TOKEN:0:20}..."

# Use existing conversation
CONVERSATION_ID="046003ab-8717-453a-a69b-637b60e0539f"

# Test the simple streaming endpoint with query param auth
echo -e "\nTesting simple streaming endpoint..."
echo "URL: http://localhost:8000/api/chat/conversations/$CONVERSATION_ID/chat/stream?token=$TOKEN"

# Send message and stream response
curl -N -X POST "http://localhost:8000/api/chat/conversations/$CONVERSATION_ID/chat/stream?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "Hello\! What model are you?",
    "model": "tinyllama:1.1b"
  }' 2>&1 | head -20
