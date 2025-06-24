#\!/bin/bash

# Get auth token from the user's browser session
TOKEN="$1"

if [ -z "$TOKEN" ]; then
  echo "Usage: ./create-test-conversations.sh <auth_token>"
  echo "Get auth token from browser localStorage: localStorage.getItem('auth_token')"
  exit 1
fi

# Create multiple test conversations
for i in {1..5}; do
  echo "Creating conversation $i..."
  curl -X POST http://localhost:8000/api/chat/conversations \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"title\": \"Test Conversation $i\"}"
  echo
done
