#!/bin/bash

BASE_URL="http://localhost:8002/rag"

echo "🧪 Testing Celery Document Processing with Progress..."

# Create collection
echo -e "\n1. Creating collection..."
COLLECTION=$(curl -s -X POST "$BASE_URL/collections" \
  -H "Content-Type: application/json" \
  -d '{"name": "Progress Test Collection", "icon": "📈"}')

COLLECTION_ID=$(echo "$COLLECTION" | jq -r '.id')
echo "Created collection: $COLLECTION_ID"

# Upload document
echo -e "\n2. Uploading document..."
UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/collections/$COLLECTION_ID/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Document for Progress",
    "text": "This is a test document. It will be split into chunks, embedded, and stored. The process includes several stages: splitting text into manageable pieces, generating vector embeddings for each chunk, storing vectors in Weaviate, and saving chunks to the database. This allows for semantic search across documents."
  }')

TASK_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.task_id')
DOC_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.document_id')

echo "Document ID: $DOC_ID"
echo "Task ID: $TASK_ID"

# Monitor progress
echo -e "\n3. Monitoring progress..."
for i in {1..30}; do
  PROGRESS=$(curl -s "$BASE_URL/progress/$TASK_ID")
  STATE=$(echo "$PROGRESS" | jq -r '.state')
  STAGE=$(echo "$PROGRESS" | jq -r '.stage // "unknown"')
  PERCENT=$(echo "$PROGRESS" | jq -r '.progress // 0')
  MESSAGE=$(echo "$PROGRESS" | jq -r '.message // ""')
  
  echo "[$i] State: $STATE | Stage: $STAGE | Progress: $PERCENT% | $MESSAGE"
  
  if [ "$STATE" = "SUCCESS" ] || [ "$STATE" = "FAILURE" ]; then
    break
  fi
  
  sleep 1
done

# Check document status
echo -e "\n4. Checking document status..."
DOC_STATUS=$(curl -s "$BASE_URL/documents/$DOC_ID/status")
echo "$DOC_STATUS" | jq '.'

# Cleanup
echo -e "\n5. Cleaning up..."
curl -s -X DELETE "$BASE_URL/collections/$COLLECTION_ID?hard_delete=true" > /dev/null
echo "✅ Test complete!"