#!/bin/bash

BASE_URL="http://localhost:8002/rag"
echo "🧪 Testing All Collection Endpoints..."

# Test 1: Create root collection
echo -e "\n📁 Test 1: Creating root collection..."
ROOT_RESPONSE=$(curl -s -X POST "$BASE_URL/collections" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Documents", "description": "Main test collection", "icon": "📚", "color": "#FF6B6B"}')

ROOT_ID=$(echo "$ROOT_RESPONSE" | jq -r '.id')
if [ "$ROOT_ID" != "null" ]; then
  echo "✅ Created root collection: $ROOT_ID"
else
  echo "❌ Failed to create root collection"
  echo "$ROOT_RESPONSE"
  exit 1
fi

# Test 2: Get collection by ID
echo -e "\n🔍 Test 2: Getting collection by ID..."
GET_RESPONSE=$(curl -s -X GET "$BASE_URL/collections/$ROOT_ID")
NAME=$(echo "$GET_RESPONSE" | jq -r '.name')
if [ "$NAME" = "Test Documents" ]; then
  echo "✅ Retrieved collection: $NAME"
else
  echo "❌ Failed to get collection"
  echo "$GET_RESPONSE"
fi

# Test 3: List root collections
echo -e "\n📋 Test 3: Listing root collections..."
LIST_RESPONSE=$(curl -s -X GET "$BASE_URL/collections")
COUNT=$(echo "$LIST_RESPONSE" | jq 'length')
echo "✅ Found $COUNT root collections"

# Test 4: Create child collection
echo -e "\n📂 Test 4: Creating child collection..."
CHILD_RESPONSE=$(curl -s -X POST "$BASE_URL/collections" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"Legal Cases\", \"parent_id\": \"$ROOT_ID\", \"icon\": \"⚖️\"}")

CHILD_ID=$(echo "$CHILD_RESPONSE" | jq -r '.id')
CHILD_PATH=$(echo "$CHILD_RESPONSE" | jq -r '.path')
if [ "$CHILD_ID" != "null" ]; then
  echo "✅ Created child: $CHILD_ID"
  echo "   Path: $CHILD_PATH"
else
  echo "❌ Failed to create child"
  echo "$CHILD_RESPONSE"
fi

# Test 5: List children
echo -e "\n👶 Test 5: Listing child collections..."
CHILDREN_RESPONSE=$(curl -s -X GET "$BASE_URL/collections/$ROOT_ID/children")
CHILD_COUNT=$(echo "$CHILDREN_RESPONSE" | jq 'length')
echo "✅ Found $CHILD_COUNT child collections"

# Test 6: Get breadcrumb path
echo -e "\n🍞 Test 6: Getting breadcrumb path..."
BREADCRUMB_RESPONSE=$(curl -s -X GET "$BASE_URL/collections/$CHILD_ID/path")
BREADCRUMB_COUNT=$(echo "$BREADCRUMB_RESPONSE" | jq 'length')
if [ "$BREADCRUMB_COUNT" = "2" ]; then
  echo "✅ Breadcrumb path has $BREADCRUMB_COUNT items:"
  echo "$BREADCRUMB_RESPONSE" | jq -r '.[] | "   - \(.name) (\(.path))"'
else
  echo "❌ Breadcrumb failed"
  echo "$BREADCRUMB_RESPONSE"
fi

# Test 7: Update collection
echo -e "\n✏️ Test 7: Updating collection..."
UPDATE_RESPONSE=$(curl -s -X PATCH "$BASE_URL/collections/$CHILD_ID" \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated legal cases", "color": "#4ECDC4"}')

UPDATED_DESC=$(echo "$UPDATE_RESPONSE" | jq -r '.description')
if [ "$UPDATED_DESC" = "Updated legal cases" ]; then
  echo "✅ Updated successfully"
else
  echo "❌ Update failed"
  echo "$UPDATE_RESPONSE"
fi

# Test 8: Upload document to collection
echo -e "\n📄 Test 8: Uploading document to collection..."
DOC_RESPONSE=$(curl -s -X POST "$BASE_URL/collections/$ROOT_ID/documents" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Legal Brief", "text": "This is a test document for the legal collection."}')

TASK_ID=$(echo "$DOC_RESPONSE" | jq -r '.task_id')
if [ "$TASK_ID" != "null" ]; then
  echo "✅ Document uploaded, task ID: $TASK_ID"
else
  echo "❌ Document upload failed"
  echo "$DOC_RESPONSE"
fi

# Clean up
echo -e "\n🧹 Cleaning up..."
curl -s -X DELETE "$BASE_URL/collections/$CHILD_ID?hard_delete=true"
curl -s -X DELETE "$BASE_URL/collections/$ROOT_ID?hard_delete=true"

echo -e "\n🎉 All tests completed!"