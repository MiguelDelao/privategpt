#!/bin/bash

BASE_URL="http://localhost:8002/rag"
PDF_PATH="./nvidareport.pdf"

echo "📄 Processing Real PDF: NVIDIA Report"
echo "===================================="

# Check if PDF exists
if [ ! -f "$PDF_PATH" ]; then
  echo "❌ PDF not found at $PDF_PATH"
  exit 1
fi

# Get PDF info
FILE_SIZE=$(stat -f%z "$PDF_PATH" 2>/dev/null || stat -c%s "$PDF_PATH" 2>/dev/null)
FILE_SIZE_MB=$(echo "scale=2; $FILE_SIZE / 1048576" | bc)

echo "📁 File: nvidareport.pdf"
echo "📏 Size: $FILE_SIZE_MB MB"

# Extract text from PDF using Python (if available) or use a large sample
echo -e "\n📖 Extracting text from PDF..."

# Try to extract text using Python if available
if command -v python3 &> /dev/null && python3 -c "import PyPDF2" 2>/dev/null; then
  PDF_TEXT=$(python3 << 'EOF'
import PyPDF2
import sys

try:
    with open('./nvidareport.pdf', 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page_num in range(min(len(pdf_reader.pages), 20)):  # First 20 pages
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n\n"
        print(text[:50000])  # Limit to 50k chars for processing
except Exception as e:
    print(f"Error extracting PDF: {e}", file=sys.stderr)
    sys.exit(1)
EOF
)
  
  if [ $? -eq 0 ] && [ -n "$PDF_TEXT" ]; then
    echo "✅ Extracted $(echo "$PDF_TEXT" | wc -w) words from PDF"
  else
    echo "⚠️ Could not extract PDF text, using sample content"
    PDF_TEXT="NVIDIA Corporation Annual Report - Sample Content

This is a sample representation of the NVIDIA annual report. In a real scenario, this would contain the full text extracted from the PDF, including financial data, business overview, risk factors, and forward-looking statements.

$(cat << 'SAMPLE'
NVIDIA Corporation Financial Highlights and Business Overview

Executive Summary:
NVIDIA Corporation has established itself as the world leader in accelerated computing. The company's invention of the GPU in 1999 sparked the growth of the PC gaming market and has redefined modern computer graphics, high performance computing, and artificial intelligence.

Business Segments:

1. Data Center
The Data Center segment includes hardware and software solutions for AI, HPC, and accelerated computing. Key products include:
- NVIDIA H100 Tensor Core GPU
- NVIDIA A100 Tensor Core GPU
- DGX systems and DGX Cloud
- NVIDIA AI Enterprise software
- InfiniBand and Ethernet networking solutions

Revenue in this segment has grown exponentially due to the rapid adoption of generative AI and large language models. Major cloud service providers and enterprises are investing heavily in NVIDIA's data center infrastructure to power AI workloads.

2. Gaming
The Gaming segment includes:
- GeForce RTX 40 Series GPUs
- GeForce RTX 30 Series GPUs
- Game development tools and technologies
- GeForce NOW cloud gaming service

Despite market fluctuations, gaming remains a core business with consistent innovation in ray tracing, DLSS, and content creation capabilities.

3. Professional Visualization
This segment serves:
- Design and manufacturing industries
- Media and entertainment
- Scientific visualization
- Virtual production

Products include RTX professional GPUs and virtual workstation software.

4. Automotive
NVIDIA DRIVE platform powers:
- Autonomous vehicle development
- In-vehicle AI computing
- Simulation and validation tools

Partnerships with major automotive manufacturers position NVIDIA at the forefront of the autonomous vehicle revolution.

Financial Performance:
- Record revenue driven by data center growth
- Strong gross margins reflecting product differentiation
- Significant R&D investment to maintain technology leadership
- Robust cash flow generation

Market Dynamics:
The accelerated computing market is experiencing unprecedented growth driven by:
- Generative AI adoption across industries
- Digital transformation initiatives
- Edge computing expansion
- Metaverse and virtual world development

Competitive Advantages:
1. CUDA software ecosystem
2. Full-stack approach from silicon to software
3. Strong developer community
4. Continuous innovation in GPU architecture
5. Strategic partnerships with cloud providers

Risk Factors:
- Geopolitical tensions affecting supply chain
- Export control regulations
- Competition from custom silicon
- Manufacturing capacity constraints
- Cryptocurrency market volatility

Future Outlook:
NVIDIA is well-positioned to capitalize on the AI revolution. The company's roadmap includes:
- Next-generation GPU architectures
- Expanded software offerings
- Greater integration of AI into all products
- Continued investment in research and development

Environmental, Social, and Governance (ESG):
- Commitment to carbon neutrality
- Diversity and inclusion initiatives
- Responsible AI development
- Community engagement programs

This comprehensive overview demonstrates NVIDIA's transformation from a graphics company to a full-stack computing platform company powering the world's most important technological advances.
SAMPLE
)"
  fi
else
  echo "⚠️ PyPDF2 not available, using large sample content"
  # Use a substantial sample that represents PDF content
  PDF_TEXT="$(cat << 'LARGE_SAMPLE'
NVIDIA CORPORATION ANNUAL REPORT 2024

UNITED STATES SECURITIES AND EXCHANGE COMMISSION
Washington, D.C. 20549

FORM 10-K

ANNUAL REPORT PURSUANT TO SECTION 13 OR 15(d) OF THE SECURITIES EXCHANGE ACT OF 1934

For the fiscal year ended January 28, 2024

Commission File Number: 0-23985

NVIDIA CORPORATION
(Exact name of registrant as specified in its charter)

Delaware                                           94-3177549
(State or other jurisdiction of                     (I.R.S. Employer
incorporation or organization)                      Identification No.)

2788 San Tomas Expressway, Santa Clara, CA 95051
(408) 486-2000

PART I

Item 1. Business

Overview

NVIDIA pioneered accelerated computing to help solve the most challenging computational problems. Since our original focus on PC graphics, we have expanded to several other large and important computationally intensive fields. Fueled by the sustained demand for exceptional 3D graphics and the scale of the gaming market, NVIDIA has leveraged its GPU architecture to create platforms for scientific computing, AI, data science, autonomous vehicles, robotics, and augmented and virtual reality.

Our two operating segments are "Compute & Networking" and "Graphics." Our Compute & Networking segment includes our Data Center accelerated computing platform; networking; automotive AI Cockpit and autonomous driving development agreements; electric vehicle computing platforms; Jetson for robotics and other embedded platforms; NVIDIA AI Enterprise software; and cryptocurrency mining processors, or CMPs.

Industry Overview

The world's data centers are evolving from general-purpose computing to accelerated computing. This transition has been driven by the exponential growth of data and the computational requirements of AI, scientific computing, and data analytics. Traditional CPU-based architectures are struggling to keep pace with these demands, creating a massive opportunity for accelerated computing solutions.

Generative AI Revolution

The launch of ChatGPT in late 2022 marked a watershed moment for artificial intelligence, demonstrating the transformative potential of large language models to the general public. This has triggered an unprecedented wave of investment in AI infrastructure, with enterprises and governments recognizing AI as a critical strategic capability.

NVIDIA's position at the intersection of hardware and software for AI has made us the primary beneficiary of this trend. Our GPUs are the de facto standard for training and deploying large language models, and our CUDA software ecosystem provides the tools developers need to build AI applications.

Products and Technologies

Data Center

Our Data Center products and services are designed to help customers accelerate their most important workloads, including AI, data analytics, graphics and scientific computing. Key products include:

NVIDIA H100 Tensor Core GPU: Based on the Hopper architecture, the H100 delivers unprecedented performance for large language models and recommender systems. With innovations like the Transformer Engine and support for FP8 precision, the H100 can deliver up to 9x faster AI training and up to 30x faster AI inference compared to the prior generation.

NVIDIA Grace CPU: Our first data center CPU, Grace is designed to deliver outstanding performance for AI and HPC applications. When combined with Hopper GPUs in our Grace Hopper Superchip, it provides a revolutionary new architecture for giant-scale AI and HPC applications.

DGX Systems: These purpose-built AI supercomputers provide the compute infrastructure needed for AI development at scale. The DGX H100 system features eight H100 GPUs interconnected with NVLink and NVSwitch, delivering 32 petaflops of AI performance.

NVIDIA AI Enterprise: This software suite includes frameworks, pretrained models, and tools to streamline AI development and deployment. It provides enterprise-grade support, security, and API stability for production AI applications.

Networking

Our networking products, based on our acquisition of Mellanox, are critical for building AI infrastructure at scale:

InfiniBand: The leading interconnect for AI supercomputers, InfiniBand provides the ultra-low latency and high bandwidth needed for distributed AI training.

Ethernet: Our Spectrum Ethernet switches and BlueField DPUs enable cloud providers to build efficient, secure, and scalable data center networks.

Gaming and Creative

GeForce RTX 40 Series: Based on the Ada Lovelace architecture, our latest gaming GPUs deliver revolutionary performance through third-generation RT Cores, fourth-generation Tensor Cores, and DLSS 3 with Frame Generation.

Studio Platform: NVIDIA Studio provides creators with RTX-accelerated creative applications, Studio drivers optimized for creative workflows, and exclusive features in popular creative apps.

Automotive

NVIDIA DRIVE: Our end-to-end platform for autonomous vehicles includes:
- DRIVE Orin: The system-on-chip delivering up to 254 TOPS for autonomous driving
- DRIVE Hyperion: Reference architecture for autonomous vehicles
- DRIVE Sim: Physics-based simulation platform for AV development
- DRIVE Map: Multi-modal mapping platform

Professional Visualization

RTX Professional GPUs: Our workstation GPUs power design, engineering, and content creation workflows across industries including architecture, engineering, construction, media and entertainment, and scientific visualization.

Omniverse: Our platform for creating and operating metaverse applications enables real-time collaboration and physically accurate simulation, transforming how teams design and create.

Financial Information

(Selected financial data would appear here in the actual report, including revenue by segment, gross margins, operating expenses, and other key metrics)

Competition

The markets for our products are competitive and evolving rapidly. We face competition from:

Intel and AMD: In CPUs and GPUs for data center and PC markets
Custom silicon: Cloud service providers developing their own AI chips
Arm-based processors: In edge computing and automotive markets
Other accelerator companies: Specialized AI chip startups

Our competitive advantages include:
- CUDA ecosystem with millions of developers
- Full-stack approach from silicon to systems to software
- Continuous innovation in GPU architecture
- Strong relationships with ecosystem partners
- Scale advantages in manufacturing and R&D

Risk Factors

Investing in our common stock involves a high degree of risk. Key risks include:

Geopolitical and Regulatory Risks:
- Export controls limiting sales to certain countries
- Trade tensions affecting global supply chains
- Regulatory changes affecting AI deployment

Market Risks:
- Dependency on growth in AI and data center markets
- Cryptocurrency market volatility
- Gaming market cyclicality

Operational Risks:
- Reliance on third-party foundries
- Supply chain constraints
- Intellectual property disputes
- Cybersecurity threats

Technology Risks:
- Rapid technological change
- Development of alternative computing architectures
- Open-source software competition

Environmental, Social and Governance

We are committed to using our technology and resources to benefit society while minimizing our environmental impact:

Climate Action: We have committed to achieving net-zero emissions by 2050 and are investing in renewable energy and energy-efficient technologies.

Diversity and Inclusion: We strive to build a diverse workforce that reflects our global community and fosters innovation through varied perspectives.

Responsible AI: We work to ensure AI technology is developed and deployed ethically, with consideration for privacy, fairness, and transparency.

Community Engagement: Through our NVIDIA Foundation, we support education, research, and humanitarian efforts worldwide.

Forward-Looking Statements

This report contains forward-looking statements that involve risks and uncertainties. Actual results may differ materially from those anticipated in these forward-looking statements as a result of various factors, including those described in the Risk Factors section and elsewhere in this report.

LARGE_SAMPLE
)"
fi

# Create collection
echo -e "\n📁 Creating collection for PDF document..."
COLLECTION=$(curl -s -X POST "$BASE_URL/collections" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "PDF Reports",
    "description": "Technical and Financial Reports",
    "icon": "📊",
    "color": "#76B900"
  }')

COLLECTION_ID=$(echo "$COLLECTION" | jq -r '.id' 2>/dev/null || echo "")
if [ -z "$COLLECTION_ID" ] || [ "$COLLECTION_ID" = "null" ]; then
  echo "❌ Failed to create collection"
  echo "Response: $COLLECTION"
  exit 1
fi
echo "✅ Collection created: $COLLECTION_ID"

# Upload document
echo -e "\n📤 Uploading PDF content to RAG system..."
echo "📝 Document size: $(echo "$PDF_TEXT" | wc -c) characters"

# Properly escape the text for JSON
ESCAPED_TEXT=$(echo "$PDF_TEXT" | jq -Rs .)

UPLOAD=$(curl -s -X POST "$BASE_URL/collections/$COLLECTION_ID/documents" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"NVIDIA Annual Report 2024\",
    \"text\": $ESCAPED_TEXT
  }")

TASK_ID=$(echo "$UPLOAD" | jq -r '.task_id' 2>/dev/null || echo "")
DOC_ID=$(echo "$UPLOAD" | jq -r '.document_id' 2>/dev/null || echo "")

if [ -z "$TASK_ID" ] || [ "$TASK_ID" = "null" ]; then
  echo "❌ Failed to upload document"
  echo "Response: $UPLOAD"
  exit 1
fi

echo "✅ Document uploaded"
echo "📋 Document ID: $DOC_ID"
echo "🔄 Task ID: $TASK_ID"

# Monitor progress
echo -e "\n⚡ Processing Progress:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

LAST_STAGE=""
START_TIME=$(date +%s)
MAX_WAIT=120  # 2 minutes timeout

while true; do
  PROGRESS=$(curl -s "$BASE_URL/progress/$TASK_ID")
  
  # Parse progress data safely
  STATE=$(echo "$PROGRESS" | jq -r '.state' 2>/dev/null || echo "UNKNOWN")
  STAGE=$(echo "$PROGRESS" | jq -r '.stage' 2>/dev/null || echo "unknown")
  PERCENT=$(echo "$PROGRESS" | jq -r '.progress' 2>/dev/null || echo "0")
  MESSAGE=$(echo "$PROGRESS" | jq -r '.message' 2>/dev/null || echo "")
  
  # Calculate elapsed time
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))
  
  # Timeout check
  if [ $ELAPSED -gt $MAX_WAIT ]; then
    echo -e "\n\n⏱️ Processing timeout after ${MAX_WAIT} seconds"
    break
  fi
  
  # Progress bar
  BAR_LENGTH=50
  if [ "$PERCENT" -eq "$PERCENT" ] 2>/dev/null; then
    FILLED=$(( PERCENT * BAR_LENGTH / 100 ))
  else
    FILLED=0
  fi
  
  # Color based on stage
  case "$STAGE" in
    "splitting") COLOR="\033[96m" ;;
    "embedding") COLOR="\033[95m" ;;
    "storing") COLOR="\033[94m" ;;
    "finalizing") COLOR="\033[93m" ;;
    "complete") COLOR="\033[92m" ;;
    "failed") COLOR="\033[91m" ;;
    *) COLOR="\033[0m" ;;
  esac
  
  # Show stage change
  if [ "$STAGE" != "$LAST_STAGE" ] && [ "$LAST_STAGE" != "" ]; then
    echo
  fi
  
  # Display progress
  printf "\r${COLOR}%-12s [" "$STAGE"
  printf "%${FILLED}s" | tr ' ' '█'
  printf "%$((BAR_LENGTH - FILLED))s" | tr ' ' '░'
  printf "] %3d%% %-40s [%ds]\033[0m" "$PERCENT" "${MESSAGE:0:40}" "$ELAPSED"
  
  LAST_STAGE=$STAGE
  
  # Check completion
  if [ "$STATE" = "SUCCESS" ]; then
    echo -e "\n\n✅ Processing completed in ${ELAPSED} seconds!"
    break
  elif [ "$STATE" = "FAILURE" ]; then
    echo -e "\n\n❌ Processing failed!"
    ERROR=$(echo "$PROGRESS" | jq -r '.error' 2>/dev/null || echo "Unknown error")
    echo "Error: $ERROR"
    break
  fi
  
  sleep 0.5
done

# Get document status
echo -e "\n📊 Document Status:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

DOC_STATUS=$(curl -s "$BASE_URL/documents/$DOC_ID/status" 2>/dev/null)
if [ -n "$DOC_STATUS" ] && [ "$DOC_STATUS" != "null" ]; then
  # Try to parse JSON response
  TITLE=$(echo "$DOC_STATUS" | jq -r '.title' 2>/dev/null || echo "N/A")
  STATUS=$(echo "$DOC_STATUS" | jq -r '.status' 2>/dev/null || echo "N/A")
  CHUNKS=$(echo "$DOC_STATUS" | jq -r '.chunk_count' 2>/dev/null || echo "0")
  
  echo "Title: $TITLE"
  echo "Status: $STATUS"
  echo "Chunks: $CHUNKS"
  echo "Processing Time: ${ELAPSED} seconds"
  
  # Check if processing_progress is a string that needs parsing
  PROGRESS_STR=$(echo "$DOC_STATUS" | jq -r '.processing_progress' 2>/dev/null || echo "{}")
  if [ "$PROGRESS_STR" != "{}" ] && [ "$PROGRESS_STR" != "null" ]; then
    echo -e "\nProcessing Details:"
    # Try to parse as JSON, if it fails just print it
    echo "$PROGRESS_STR" | jq '.' 2>/dev/null || echo "$PROGRESS_STR"
  fi
else
  echo "⚠️ Could not retrieve document status"
fi

# Test search functionality
echo -e "\n🔍 Testing RAG Search:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

QUESTIONS=(
  "What is NVIDIA's main AI product?"
  "What are the key business segments?"
  "What is the H100 GPU?"
)

for QUESTION in "${QUESTIONS[@]}"; do
  echo -e "\n❓ Query: \"$QUESTION\""
  
  SEARCH=$(curl -s -X POST "$BASE_URL/chat" \
    -H "Content-Type: application/json" \
    -d "{
      \"question\": \"$QUESTION\",
      \"collection_ids\": [\"$COLLECTION_ID\"]
    }" 2>/dev/null)
  
  if [ -n "$SEARCH" ] && [ "$SEARCH" != "null" ]; then
    ANSWER=$(echo "$SEARCH" | jq -r '.answer' 2>/dev/null || echo "")
    if [ -n "$ANSWER" ] && [ "$ANSWER" != "null" ]; then
      echo "💬 Answer: $ANSWER" | fold -s -w 80
      
      # Show citation count if available
      CITATION_COUNT=$(echo "$SEARCH" | jq '.citations | length' 2>/dev/null || echo "0")
      if [ "$CITATION_COUNT" -gt 0 ]; then
        echo "📎 Citations: $CITATION_COUNT sources"
      fi
    else
      echo "⚠️ No answer generated"
    fi
  else
    echo "⚠️ Search request failed"
  fi
done

# Collection statistics
echo -e "\n📈 Collection Statistics:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

COLL_INFO=$(curl -s "$BASE_URL/collections/$COLLECTION_ID" 2>/dev/null)
if [ -n "$COLL_INFO" ] && [ "$COLL_INFO" != "null" ]; then
  NAME=$(echo "$COLL_INFO" | jq -r '.name' 2>/dev/null || echo "N/A")
  DOC_COUNT=$(echo "$COLL_INFO" | jq -r '.document_count' 2>/dev/null || echo "0")
  
  echo "Collection: $NAME"
  echo "Documents in collection: $DOC_COUNT"
fi

# Cleanup option
echo -e "\n🧹 Cleanup?"
read -p "Delete test collection? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  curl -s -X DELETE "$BASE_URL/collections/$COLLECTION_ID?hard_delete=true" > /dev/null
  echo "✅ Collection deleted"
fi

echo -e "\n✨ PDF processing test completed!"