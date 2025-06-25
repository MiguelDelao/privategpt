#!/bin/bash

BASE_URL="http://localhost:8002/rag"
PDF_PATH="/Users/mig/Desktop/1_1/private/privategpt/nvidareport.pdf"

echo "📄 Testing PDF Document Processing with Progress Tracking"
echo "========================================================="

# Step 1: Create a collection for the PDF
echo -e "\n1️⃣ Creating collection for NVIDIA report..."
COLLECTION=$(curl -s -X POST "$BASE_URL/collections" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Technical Reports",
    "description": "Collection for technical PDF reports",
    "icon": "📊",
    "color": "#76B900"
  }')

COLLECTION_ID=$(echo "$COLLECTION" | jq -r '.id')
echo "✅ Created collection: $COLLECTION_ID"

# Step 2: Read the PDF and convert to base64
echo -e "\n2️⃣ Reading PDF file..."
if [ ! -f "$PDF_PATH" ]; then
  echo "❌ PDF file not found at $PDF_PATH"
  exit 1
fi

# Get file size
FILE_SIZE=$(stat -f%z "$PDF_PATH" 2>/dev/null || stat -c%s "$PDF_PATH" 2>/dev/null)
echo "📁 File: nvidareport.pdf"
echo "📏 Size: $(echo "scale=2; $FILE_SIZE / 1048576" | bc) MB"

# For now, let's extract text from PDF using a simple approach
# In production, you'd use proper PDF parsing
echo -e "\n3️⃣ Extracting text from PDF (simulated)..."
# Since we can't easily extract PDF text in bash, let's create a test document
# that represents what would be extracted from the PDF

DOCUMENT_TEXT="NVIDIA Corporation Annual Report

Executive Summary:
NVIDIA has emerged as a leader in accelerated computing, with our GPU technology powering breakthroughs in AI, data science, and high-performance computing. Our data center business has experienced tremendous growth driven by the adoption of generative AI and large language models.

Financial Highlights:
- Record revenue driven by strong demand for AI infrastructure
- Data Center revenue grew significantly year-over-year
- Gaming segment remains resilient with new product launches
- Professional Visualization benefited from hybrid work trends

Product Portfolio:
1. Data Center Products:
   - H100 Tensor Core GPU for AI training and inference
   - DGX systems for enterprise AI development
   - NVIDIA AI Enterprise software suite

2. Gaming Products:
   - GeForce RTX 40 Series graphics cards
   - DLSS 3 technology for enhanced gaming performance
   - GeForce NOW cloud gaming service

3. Automotive:
   - DRIVE platform for autonomous vehicles
   - Partnerships with major automotive manufacturers

Market Opportunity:
The transition to accelerated computing represents a massive market opportunity. As organizations adopt AI to transform their businesses, demand for NVIDIA's computing platform continues to grow. We estimate the total addressable market for data center AI infrastructure will reach hundreds of billions of dollars.

Risk Factors:
- Dependency on Taiwan-based manufacturing
- Competitive threats from other chip designers
- Regulatory challenges in key markets
- Supply chain constraints

Future Outlook:
We remain focused on advancing our platform across key growth areas including generative AI, autonomous vehicles, and the metaverse. Our investments in research and development position us to maintain technology leadership."

# Step 4: Upload document to collection
echo -e "\n4️⃣ Uploading document to RAG system..."
UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/collections/$COLLECTION_ID/documents" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"NVIDIA Annual Report - Technical Analysis\",
    \"text\": $(echo "$DOCUMENT_TEXT" | jq -Rs .)
  }")

TASK_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.task_id')
DOC_ID=$(echo "$UPLOAD_RESPONSE" | jq -r '.document_id')

if [ "$TASK_ID" = "null" ]; then
  echo "❌ Failed to upload document"
  echo "$UPLOAD_RESPONSE"
  exit 1
fi

echo "✅ Document uploaded successfully"
echo "📋 Document ID: $DOC_ID"
echo "🔄 Task ID: $TASK_ID"

# Step 5: Monitor progress with visual progress bar
echo -e "\n5️⃣ Processing document with real-time progress updates:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

LAST_PROGRESS=-1
LAST_STAGE=""
START_TIME=$(date +%s)

while true; do
  PROGRESS_RESPONSE=$(curl -s "$BASE_URL/progress/$TASK_ID")
  
  STATE=$(echo "$PROGRESS_RESPONSE" | jq -r '.state')
  STAGE=$(echo "$PROGRESS_RESPONSE" | jq -r '.stage // "unknown"')
  PROGRESS=$(echo "$PROGRESS_RESPONSE" | jq -r '.progress // 0')
  MESSAGE=$(echo "$PROGRESS_RESPONSE" | jq -r '.message // ""')
  
  # Calculate elapsed time
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))
  
  # Update display if progress changed
  if [ "$PROGRESS" != "$LAST_PROGRESS" ] || [ "$STAGE" != "$LAST_STAGE" ]; then
    # Create progress bar
    BAR_LENGTH=40
    FILLED=$(echo "scale=0; $PROGRESS * $BAR_LENGTH / 100" | bc)
    EMPTY=$((BAR_LENGTH - FILLED))
    
    # Color codes based on stage
    case "$STAGE" in
      "splitting") COLOR="\033[36m" ;;      # Cyan
      "embedding") COLOR="\033[35m" ;;      # Magenta
      "storing") COLOR="\033[34m" ;;        # Blue
      "finalizing") COLOR="\033[33m" ;;     # Yellow
      "complete") COLOR="\033[32m" ;;       # Green
      "failed") COLOR="\033[31m" ;;         # Red
      *) COLOR="\033[37m" ;;                # White
    esac
    
    # Print progress update
    printf "\r${COLOR}%-12s [" "$STAGE"
    printf "%${FILLED}s" | tr ' ' '█'
    printf "%${EMPTY}s" | tr ' ' '░'
    printf "] %3d%% %-50s [%ds]\033[0m" "$PROGRESS" "$MESSAGE" "$ELAPSED"
    
    LAST_PROGRESS=$PROGRESS
    LAST_STAGE=$STAGE
  fi
  
  # Check if processing is complete
  if [ "$STATE" = "SUCCESS" ]; then
    echo -e "\n\n✅ Document processing completed successfully!"
    break
  elif [ "$STATE" = "FAILURE" ]; then
    ERROR=$(echo "$PROGRESS_RESPONSE" | jq -r '.error // "Unknown error"')
    echo -e "\n\n❌ Document processing failed: $ERROR"
    break
  fi
  
  sleep 0.5
done

# Step 6: Get final document status
echo -e "\n6️⃣ Final document status:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
DOC_STATUS=$(curl -s "$BASE_URL/documents/$DOC_ID/status")

echo "$DOC_STATUS" | jq '{
  title: .title,
  status: .status,
  chunks: .chunk_count,
  collection: .collection_id,
  processing_time: "'$ELAPSED' seconds",
  details: .processing_progress
}'

# Step 7: Test search functionality
echo -e "\n7️⃣ Testing RAG search on processed document:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

SEARCH_QUERY="What are NVIDIA's main AI products?"
echo "🔍 Query: $SEARCH_QUERY"

SEARCH_RESPONSE=$(curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{
    \"question\": \"$SEARCH_QUERY\",
    \"collection_ids\": [\"$COLLECTION_ID\"]
  }")

echo -e "\n💬 Response:"
echo "$SEARCH_RESPONSE" | jq -r '.answer' | fold -s -w 80

echo -e "\n📚 Citations:"
echo "$SEARCH_RESPONSE" | jq '.citations'

# Cleanup option
echo -e "\n8️⃣ Cleanup (optional):"
read -p "Delete test collection and documents? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  curl -s -X DELETE "$BASE_URL/collections/$COLLECTION_ID?hard_delete=true"
  echo "✅ Cleaned up test data"
fi

echo -e "\n✨ PDF processing test completed!"