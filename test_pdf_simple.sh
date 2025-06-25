#!/bin/bash

BASE_URL="http://localhost:8002/rag"

echo "📄 Testing PDF Document Processing with Real-Time Progress"
echo "=========================================================="

# Create collection
echo -e "\n1️⃣ Creating collection..."
COLLECTION_RESPONSE=$(curl -s -X POST "$BASE_URL/collections" \
  -H "Content-Type: application/json" \
  -d '{"name": "PDF Test Collection", "icon": "📑"}')

echo "Response: $COLLECTION_RESPONSE"
COLLECTION_ID=$(echo "$COLLECTION_RESPONSE" | jq -r '.id')

if [ "$COLLECTION_ID" = "null" ] || [ -z "$COLLECTION_ID" ]; then
  echo "❌ Failed to create collection"
  exit 1
fi

echo "✅ Created collection: $COLLECTION_ID"

# Upload document with simulated PDF content
echo -e "\n2️⃣ Uploading document..."
UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/collections/$COLLECTION_ID/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "NVIDIA Report - AI Computing Platform",
    "text": "NVIDIA has established itself as the leading provider of AI computing platforms. The company'\''s GPU technology powers the most demanding AI workloads including training large language models, computer vision systems, and autonomous vehicles. Key products include the H100 Tensor Core GPU for data centers, the DGX systems for enterprise AI, and the GeForce RTX series for gaming and content creation. The company continues to invest heavily in research and development to maintain its technological leadership in accelerated computing."
  }')

echo "Response: $UPLOAD_RESPONSE"
TASK_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.task_id')
DOC_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.document_id')

if [ "$TASK_ID" = "null" ]; then
  echo "❌ Failed to upload document"
  exit 1
fi

echo "✅ Document ID: $DOC_ID"
echo "✅ Task ID: $TASK_ID"

# Monitor progress
echo -e "\n3️⃣ Processing Progress:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for i in {1..60}; do
  PROGRESS=$(curl -s "$BASE_URL/progress/$TASK_ID")
  STATE=$(echo "$PROGRESS" | jq -r '.state')
  STAGE=$(echo "$PROGRESS" | jq -r '.stage')
  PERCENT=$(echo "$PROGRESS" | jq -r '.progress')
  MESSAGE=$(echo "$PROGRESS" | jq -r '.message')
  
  # Progress bar
  BAR_LENGTH=50
  FILLED=$(echo "scale=0; $PERCENT * $BAR_LENGTH / 100" | bc)
  
  printf "\r%-12s [" "$STAGE"
  printf "%${FILLED}s" | tr ' ' '█'
  printf "%$((BAR_LENGTH - FILLED))s" | tr ' ' '░'
  printf "] %3d%% - %s" "$PERCENT" "$MESSAGE"
  
  if [ "$STATE" = "SUCCESS" ]; then
    echo -e "\n\n✅ Processing completed!"
    break
  elif [ "$STATE" = "FAILURE" ]; then
    echo -e "\n\n❌ Processing failed!"
    echo "Error: $(echo "$PROGRESS" | jq -r '.error')"
    break
  fi
  
  sleep 0.5
done

# Get final status
echo -e "\n\n4️⃣ Final Document Status:"
DOC_STATUS=$(curl -s "$BASE_URL/documents/$DOC_ID/status")
echo "$DOC_STATUS" | jq

# Test search
echo -e "\n5️⃣ Testing Search:"
SEARCH=$(curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are NVIDIA key AI products?"}')

echo "Answer: $(echo "$SEARCH" | jq -r '.answer')"

# Cleanup
echo -e "\n6️⃣ Cleanup..."
curl -s -X DELETE "$BASE_URL/collections/$COLLECTION_ID?hard_delete=true" > /dev/null
echo "✅ Done!"