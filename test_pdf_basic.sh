#!/bin/bash

BASE_URL="http://localhost:8002/rag"

echo "📄 Testing PDF Document Processing with Real Progress"
echo "==================================================="

# Create test content representing PDF
PDF_CONTENT="NVIDIA Corporation Annual Report 2024

Executive Summary:
NVIDIA has emerged as the dominant force in AI computing infrastructure. Our GPU technology powers the training and deployment of large language models that are transforming industries worldwide. Revenue has grown exponentially, driven by unprecedented demand for our H100 and A100 data center GPUs.

Business Segments:

1. Data Center (87% of revenue)
- H100 Tensor Core GPU: Our flagship AI training processor
- A100 GPU: Widely deployed for AI inference 
- DGX systems: Integrated AI supercomputers
- InfiniBand networking: High-speed interconnects for AI clusters
- NVIDIA AI Enterprise: Software suite for production AI

2. Gaming (9% of revenue)  
- GeForce RTX 4090, 4080, 4070 series
- DLSS 3 with Frame Generation
- GeForce NOW cloud gaming
- Studio platform for creators

3. Professional Visualization (2% of revenue)
- RTX workstation GPUs
- Omniverse platform for 3D collaboration
- Virtual production tools

4. Automotive (2% of revenue)
- DRIVE Orin SoC for autonomous vehicles
- DRIVE Hyperion development platform
- Partnerships with Mercedes-Benz, Volvo, BYD

Financial Highlights:
- Record quarterly revenue of \$18.1 billion
- Data center revenue up 427% year-over-year
- Gross margins expanded to 75%
- Operating cash flow of \$28.7 billion

Market Opportunity:
The generative AI revolution is creating a \$1 trillion market opportunity. Every enterprise is racing to implement AI, driving demand for our full-stack accelerated computing platform. We estimate less than \$150 billion of data center infrastructure has been built for AI so far, with \$1 trillion needed over the next 4 years.

Competitive Position:
- CUDA ecosystem with 4 million developers
- 10+ year technology lead in AI training
- Full stack from chips to systems to software
- Partnerships with every major cloud provider

Risks:
- Export restrictions to China
- Competitive threats from custom chips
- Supply chain constraints
- Concentration in TSMC manufacturing"

# Create collection
echo -e "\n1️⃣ Creating collection..."
COLLECTION=$(curl -s -X POST "$BASE_URL/collections" \
  -H "Content-Type: application/json" \
  -d '{"name": "Financial Reports", "icon": "💰", "color": "#76B900"}')

COLLECTION_ID=$(echo "$COLLECTION" | jq -r '.id' 2>/dev/null)
if [ -z "$COLLECTION_ID" ] || [ "$COLLECTION_ID" = "null" ]; then
  echo "Failed to create collection"
  exit 1
fi
echo "✅ Collection: $COLLECTION_ID"

# Upload document
echo -e "\n2️⃣ Uploading document..."
UPLOAD=$(curl -s -X POST "$BASE_URL/collections/$COLLECTION_ID/documents" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"NVIDIA Annual Report 2024\",
    \"text\": $(echo "$PDF_CONTENT" | jq -Rs .)
  }")

TASK_ID=$(echo "$UPLOAD" | jq -r '.task_id' 2>/dev/null)
DOC_ID=$(echo "$UPLOAD" | jq -r '.document_id' 2>/dev/null)

echo "📄 Document ID: $DOC_ID"
echo "🔄 Task ID: $TASK_ID"

# Monitor progress
echo -e "\n3️⃣ Processing Progress:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

START_TIME=$(date +%s)
TIMEOUT=60

while true; do
  PROGRESS=$(curl -s "$BASE_URL/progress/$TASK_ID")
  STATE=$(echo "$PROGRESS" | jq -r '.state' 2>/dev/null || echo "UNKNOWN")
  STAGE=$(echo "$PROGRESS" | jq -r '.stage' 2>/dev/null || echo "unknown")
  PERCENT=$(echo "$PROGRESS" | jq -r '.progress' 2>/dev/null || echo "0")
  MESSAGE=$(echo "$PROGRESS" | jq -r '.message' 2>/dev/null || echo "")
  
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))
  
  # Progress bar
  BAR_LENGTH=40
  FILLED=$(( PERCENT * BAR_LENGTH / 100 ))
  
  printf "\r%-12s [" "$STAGE"
  printf "%${FILLED}s" | tr ' ' '█'
  printf "%$((BAR_LENGTH - FILLED))s" | tr ' ' '░'
  printf "] %3d%% %-30s [%ds]" "$PERCENT" "${MESSAGE:0:30}" "$ELAPSED"
  
  if [ "$STATE" = "SUCCESS" ]; then
    echo -e "\n✅ Completed!"
    break
  elif [ "$STATE" = "FAILURE" ]; then
    echo -e "\n❌ Failed!"
    break
  elif [ $ELAPSED -gt $TIMEOUT ]; then
    echo -e "\n⏱️ Timeout!"
    break
  fi
  
  sleep 0.5
done

# Get status
echo -e "\n\n4️⃣ Document Status:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

STATUS=$(curl -s "$BASE_URL/documents/$DOC_ID/status" 2>/dev/null || echo "{}")
echo "Status response: $STATUS"

# Test search
echo -e "\n5️⃣ Testing Search:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

QUESTIONS=(
  "What is NVIDIA H100?"
  "What are NVIDIA's revenue numbers?"
  "What are the main risks?"
)

for Q in "${QUESTIONS[@]}"; do
  echo -e "\n❓ $Q"
  RESULT=$(curl -s -X POST "$BASE_URL/chat" \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"$Q\"}" 2>/dev/null || echo "{}")
  
  ANSWER=$(echo "$RESULT" | jq -r '.answer' 2>/dev/null || echo "No answer")
  echo "💬 $ANSWER" | fold -s -w 70
done

# Cleanup
echo -e "\n6️⃣ Cleanup..."
curl -s -X DELETE "$BASE_URL/collections/$COLLECTION_ID?hard_delete=true" > /dev/null
echo "✅ Done!"