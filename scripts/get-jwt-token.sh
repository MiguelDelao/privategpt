#!/bin/bash
set -e

echo "Getting JWT token from Keycloak..."

# Default values
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8180}"
USERNAME="${USERNAME:-admin@admin.com}"
PASSWORD="${PASSWORD:-admin}"
CLIENT_ID="${CLIENT_ID:-privategpt-ui}"
CLIENT_SECRET="${CLIENT_SECRET:-privategpt-ui-secret-key}"

# Get token
TOKEN_RESPONSE=$(curl -s -X POST "$KEYCLOAK_URL/realms/privategpt/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$USERNAME" \
  -d "password=$PASSWORD" \
  -d "grant_type=password" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET")

# Check if request was successful
if echo "$TOKEN_RESPONSE" | jq -e '.access_token' > /dev/null; then
    ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')
    EXPIRES_IN=$(echo "$TOKEN_RESPONSE" | jq -r '.expires_in')
    
    echo "✅ Successfully obtained JWT token"
    echo "📋 Token Info:"
    echo "   - Expires in: $EXPIRES_IN seconds"
    echo "   - Token type: Bearer"
    echo ""
    echo "🔑 Access Token:"
    echo "$ACCESS_TOKEN"
    echo ""
    echo "📝 Usage:"
    echo "export ACCESS_TOKEN=\"$ACCESS_TOKEN\""
    echo "curl -H \"Authorization: Bearer \$ACCESS_TOKEN\" http://localhost:8000/api/chat/conversations"
    echo ""
    echo "🔍 Token payload (decoded):"
    echo "$ACCESS_TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | jq . || echo "Could not decode token payload"
    
else
    echo "❌ Failed to get token"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi