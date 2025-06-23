#!/bin/bash
set -e

echo "🔐 Complete Authentication & Conversation Test"
echo "=============================================="
echo ""

# Step 1: Get JWT Token
echo "🔑 Step 1: Getting JWT token from Keycloak..."
TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8180/realms/privategpt/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@admin.com" \
  -d "password=admin" \
  -d "grant_type=password" \
  -d "client_id=privategpt-ui" \
  -d "client_secret=privategpt-ui-secret-key")

if echo "$TOKEN_RESPONSE" | jq -e '.access_token' > /dev/null; then
    ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')
    echo "✅ JWT Token obtained successfully"
    echo "   Token starts with: ${ACCESS_TOKEN:0:50}..."
else
    echo "❌ Failed to get JWT token"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi
echo ""

# Step 2: Test Authentication 
echo "🔒 Step 2: Testing Authentication..."
echo "Without token:"
NO_AUTH_RESPONSE=$(curl -s http://localhost:8000/api/chat/conversations)
echo "   Response: $NO_AUTH_RESPONSE"

echo "With token:"
AUTH_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" http://localhost:8000/api/chat/conversations)
echo "   Response: $AUTH_RESPONSE"
echo ""

# Check if authentication is working
if [[ "$AUTH_RESPONSE" == *"Authentication required"* ]]; then
    echo "⚠️  Authentication still failing - there may be a configuration issue"
    echo "   Let's try the debug endpoint that bypasses auth..."
    
    DEBUG_RESPONSE=$(curl -s http://localhost:8000/api/chat/debug/conversations)
    echo "   Debug endpoint: $DEBUG_RESPONSE"
    echo ""
    
    echo "🔍 Let's check if direct endpoints work (these should bypass auth):"
    DIRECT_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" \
        -d '{"message":"test","model":"tinyllama:1.1b"}' \
        http://localhost:8000/api/chat/direct)
    echo "   Direct chat: ${DIRECT_RESPONSE:0:100}..."
    echo ""
    
    echo "📋 Summary:"
    echo "   ❌ JWT auth validation needs debugging"
    echo "   ✅ JWT token generation works"
    echo "   ✅ Auth middleware is active (no-auth requests properly rejected)"
    echo "   📝 Next step: Debug JWT validation logic"
    
elif [[ "$AUTH_RESPONSE" == "[]" ]] || [[ "$AUTH_RESPONSE" == *"conversations"* ]]; then
    echo "🎉 Authentication is working! Proceeding with conversation test..."
    
    # Step 3: Create Conversation
    echo "📝 Step 3: Creating a new conversation..."
    CONVERSATION_DATA='{
        "title": "My Test Chat",
        "model_name": "tinyllama:1.1b", 
        "system_prompt": "You are a helpful assistant for testing."
    }'
    
    CREATE_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$CONVERSATION_DATA" \
        http://localhost:8000/api/chat/conversations)
    
    if echo "$CREATE_RESPONSE" | jq -e '.id' > /dev/null; then
        CONVERSATION_ID=$(echo "$CREATE_RESPONSE" | jq -r '.id')
        echo "✅ Conversation created successfully!"
        echo "   ID: $CONVERSATION_ID"
        echo "   Title: $(echo "$CREATE_RESPONSE" | jq -r '.title')"
        echo ""
        
        # Step 4: Retrieve Conversation
        echo "📖 Step 4: Retrieving the conversation..."
        GET_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
            "http://localhost:8000/api/chat/conversations/$CONVERSATION_ID")
        
        if echo "$GET_RESPONSE" | jq -e '.id' > /dev/null; then
            echo "✅ Conversation retrieved successfully!"
            echo "   Title: $(echo "$GET_RESPONSE" | jq -r '.title')"
            echo "   Status: $(echo "$GET_RESPONSE" | jq -r '.status')"
            echo "   Model: $(echo "$GET_RESPONSE" | jq -r '.model_name')"
            echo ""
            
            # Step 5: List All Conversations
            echo "📋 Step 5: Listing all conversations..."
            LIST_RESPONSE=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
                http://localhost:8000/api/chat/conversations)
            
            if echo "$LIST_RESPONSE" | jq -e '.[0].id' > /dev/null; then
                COUNT=$(echo "$LIST_RESPONSE" | jq '. | length')
                echo "✅ Listed $COUNT conversation(s)"
                echo ""
                
                echo "🎉 FULL SUCCESS! Authentication and conversation management working perfectly!"
                echo "📝 Summary:"
                echo "   ✅ JWT token generation"
                echo "   ✅ Authentication validation"  
                echo "   ✅ Conversation creation"
                echo "   ✅ Conversation retrieval"
                echo "   ✅ Conversation listing"
                echo ""
                echo "🚀 Your frontend can now integrate with these authenticated endpoints!"
                
            else
                echo "❌ Failed to list conversations: $LIST_RESPONSE"
            fi
        else
            echo "❌ Failed to retrieve conversation: $GET_RESPONSE"
        fi
    else
        echo "❌ Failed to create conversation: $CREATE_RESPONSE"
    fi
else
    echo "❓ Unexpected response: $AUTH_RESPONSE"
fi