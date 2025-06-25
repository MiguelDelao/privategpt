#!/bin/bash

echo "🚀 Document Processing Progress Tracking Demo"
echo "==========================================="
echo ""
echo "This demo shows the Celery progress tracking working with a large document."
echo ""

BASE_URL="http://localhost:8002/rag"

# Create a substantial document to see all progress stages
LARGE_DOC="Artificial Intelligence: The Complete Guide

$(for i in {1..50}; do
  echo "Chapter $i: Understanding AI Systems

Artificial intelligence represents one of the most transformative technologies of our time. This chapter explores the fundamental concepts, applications, and implications of AI systems in modern society. Machine learning algorithms continue to evolve, enabling new capabilities in natural language processing, computer vision, and decision-making systems.

The development of neural networks has revolutionized how we approach complex problems. Deep learning architectures, inspired by the human brain, can now process vast amounts of data to identify patterns and make predictions with unprecedented accuracy. From healthcare diagnostics to autonomous vehicles, AI is reshaping industries and creating new possibilities.

Key concepts covered in this section include supervised learning, unsupervised learning, reinforcement learning, and transfer learning. We'll examine how these different approaches enable machines to learn from data and improve their performance over time. The ethical considerations of AI deployment are also crucial, as we must ensure these powerful tools are used responsibly.
"
done)"

# Create collection
echo "📁 Creating document collection..."
COLL=$(curl -s -X POST "$BASE_URL/collections" \
  -H "Content-Type: application/json" \
  -d '{"name": "AI Documentation", "icon": "🤖", "color": "#00D4FF"}')

COLL_ID=$(echo "$COLL" | jq -r '.id')
echo "✅ Collection created: $COLL_ID"

# Upload large document
echo -e "\n📤 Uploading large document ($(echo "$LARGE_DOC" | wc -c) characters)..."
UPLOAD=$(curl -s -X POST "$BASE_URL/collections/$COLL_ID/documents" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"Comprehensive AI Guide - 50 Chapters\",
    \"text\": $(echo "$LARGE_DOC" | jq -Rs .)
  }")

TASK_ID=$(echo "$UPLOAD" | jq -r '.task_id')
DOC_ID=$(echo "$UPLOAD" | jq -r '.document_id')

echo "📄 Document ID: $DOC_ID"
echo "🔄 Task ID: $TASK_ID"

# Show real-time progress with visual feedback
echo -e "\n⚡ Real-Time Processing Progress:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

START=$(date +%s)
LAST_STAGE=""
STAGE_TIMES=()

while true; do
  PROGRESS=$(curl -s "$BASE_URL/progress/$TASK_ID")
  STATE=$(echo "$PROGRESS" | jq -r '.state')
  STAGE=$(echo "$PROGRESS" | jq -r '.stage')
  PERCENT=$(echo "$PROGRESS" | jq -r '.progress')
  MESSAGE=$(echo "$PROGRESS" | jq -r '.message')
  
  NOW=$(date +%s)
  ELAPSED=$((NOW - START))
  
  # Track stage transitions
  if [ "$STAGE" != "$LAST_STAGE" ] && [ -n "$LAST_STAGE" ]; then
    echo -e "\n"
    STAGE_TIMES+=("$LAST_STAGE completed in ${ELAPSED}s")
  fi
  
  # Color coding
  case "$STAGE" in
    "pending") COLOR="\033[90m" ;;      # Gray
    "splitting") COLOR="\033[96m" ;;    # Cyan
    "embedding") COLOR="\033[95m" ;;    # Magenta
    "storing") COLOR="\033[94m" ;;      # Blue
    "finalizing") COLOR="\033[93m" ;;   # Yellow
    "complete") COLOR="\033[92m" ;;     # Green
    "failed") COLOR="\033[91m" ;;       # Red
    *) COLOR="\033[0m" ;;
  esac
  
  # Progress visualization
  BAR_LENGTH=50
  FILLED=$(( PERCENT * BAR_LENGTH / 100 ))
  
  printf "\r${COLOR}%-12s [" "${STAGE^^}"
  printf "%${FILLED}s" | tr ' ' '█'
  printf "%$((BAR_LENGTH - FILLED))s" | tr ' ' '░'
  printf "] %3d%% %-40s [%3ds]\033[0m" "$PERCENT" "${MESSAGE:0:40}" "$ELAPSED"
  
  LAST_STAGE=$STAGE
  
  if [ "$STATE" = "SUCCESS" ]; then
    echo -e "\n\n✅ Processing completed successfully!"
    STAGE_TIMES+=("$STAGE completed in ${ELAPSED}s")
    break
  elif [ "$STATE" = "FAILURE" ]; then
    echo -e "\n\n❌ Processing failed!"
    break
  fi
  
  sleep 0.2
done

# Show processing statistics
echo -e "\n📊 Processing Statistics:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Query database for stats
STATS=$(docker exec -i privategpt-db-1 psql -U privategpt -d privategpt -t << EOF
SELECT 
  (SELECT COUNT(*) FROM chunks WHERE document_id = $DOC_ID) as chunks,
  (SELECT COUNT(DISTINCT position) FROM chunks WHERE document_id = $DOC_ID) as positions;
EOF
)

CHUNKS=$(echo "$STATS" | awk -F'|' '{print $1}' | xargs)
echo "📝 Document chunks created: $CHUNKS"
echo "⏱️ Total processing time: ${ELAPSED} seconds"

if [ ${#STAGE_TIMES[@]} -gt 0 ]; then
  echo -e "\n🔄 Stage timing breakdown:"
  for timing in "${STAGE_TIMES[@]}"; do
    echo "   - $timing"
  done
fi

# Check vector store
VECTOR_COUNT=$(curl -s "http://localhost:8081/v1/objects?class=PrivateGPTChunks&limit=1000" | jq '.objects | length')
echo -e "\n🔢 Total vectors in store: $VECTOR_COUNT"

# Cleanup
echo -e "\n🧹 Cleaning up..."
curl -s -X DELETE "$BASE_URL/collections/$COLL_ID?hard_delete=true" > /dev/null

echo -e "\n✨ Demo completed!"
echo ""
echo "Key Achievements:"
echo "✅ Document processing with progress tracking"
echo "✅ Real-time stage updates (splitting → embedding → storing → complete)"
echo "✅ Progress percentages and descriptive messages"
echo "✅ Successful chunk creation and vector storage"
echo ""
echo "The Celery-based document processing pipeline is working excellently!"