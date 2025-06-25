#!/bin/bash

BASE_URL="http://localhost:8002/rag"

echo "🚀 Complete Document Processing Demo with Progress Tracking"
echo "=========================================================="

# Create collection
echo -e "\n📁 Creating Technical Documents Collection..."
COLLECTION=$(curl -s -X POST "$BASE_URL/collections" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Technical Documents",
    "description": "AI and Technology Reports",
    "icon": "🔬",
    "color": "#FF6B6B"
  }')

COLLECTION_ID=$(echo "$COLLECTION" | jq -r '.id')
echo "✅ Collection created: $COLLECTION_ID"

# Create a more substantial document to show progress stages
DOCUMENT_TEXT="Artificial Intelligence and Machine Learning: A Comprehensive Overview

Introduction:
The field of artificial intelligence has undergone tremendous transformation in recent years, driven by advances in deep learning, increased computational power, and the availability of large datasets. This document provides a comprehensive overview of the current state of AI and ML technologies.

Chapter 1: Foundations of Machine Learning
Machine learning represents a paradigm shift in how we approach problem-solving. Instead of explicitly programming rules, we train models to learn patterns from data. The three main types of machine learning are:

1. Supervised Learning: Models learn from labeled examples to make predictions. Common algorithms include decision trees, random forests, support vector machines, and neural networks.

2. Unsupervised Learning: Models discover hidden patterns in unlabeled data. Clustering algorithms like K-means and hierarchical clustering, as well as dimensionality reduction techniques like PCA and t-SNE, fall into this category.

3. Reinforcement Learning: Agents learn to make decisions by receiving rewards or penalties. This approach has achieved remarkable success in game playing, robotics, and autonomous systems.

Chapter 2: Deep Learning Revolution
Deep learning has revolutionized AI by enabling models to automatically learn hierarchical representations from raw data. Key architectures include:

- Convolutional Neural Networks (CNNs): Specialized for processing grid-like data such as images. CNNs use convolutional layers to detect features at different scales.

- Recurrent Neural Networks (RNNs): Designed for sequential data processing. Variants like LSTM and GRU address the vanishing gradient problem.

- Transformers: The attention mechanism has transformed natural language processing. Models like BERT, GPT, and T5 have set new benchmarks across various NLP tasks.

Chapter 3: Natural Language Processing
NLP has seen dramatic improvements with the advent of large language models. Key developments include:

- Pre-trained Models: Transfer learning has made it possible to fine-tune powerful models for specific tasks with limited data.

- Contextual Embeddings: Unlike static word embeddings, contextual representations capture meaning based on surrounding text.

- Few-shot Learning: Modern language models can perform tasks with minimal examples, approaching human-like flexibility.

Chapter 4: Computer Vision
Computer vision has matured to enable practical applications across industries:

- Object Detection: Models can identify and localize multiple objects in images with high accuracy.

- Image Segmentation: Pixel-level classification enables precise understanding of image content.

- Generative Models: GANs and diffusion models can create photorealistic images from text descriptions.

Chapter 5: Practical Applications
AI is transforming various sectors:

Healthcare: AI assists in diagnosis, drug discovery, and personalized treatment plans. Medical imaging analysis has shown particular promise.

Finance: Machine learning powers fraud detection, algorithmic trading, and credit risk assessment.

Transportation: Autonomous vehicles use computer vision and reinforcement learning for navigation and decision-making.

Manufacturing: Predictive maintenance and quality control benefit from AI-powered anomaly detection.

Chapter 6: Challenges and Considerations
Despite progress, significant challenges remain:

- Interpretability: Black-box models make it difficult to understand decision-making processes.

- Bias and Fairness: Models can perpetuate or amplify societal biases present in training data.

- Data Privacy: The need for large datasets raises concerns about personal information protection.

- Computational Resources: Training large models requires significant energy and computing power.

Chapter 7: Future Directions
The future of AI holds exciting possibilities:

- Multimodal Learning: Models that seamlessly integrate text, vision, and audio understanding.

- Continual Learning: Systems that can learn new tasks without forgetting previous knowledge.

- AI Safety: Research into alignment and robustness to ensure beneficial AI development.

- Neuromorphic Computing: Hardware designed to mimic brain architecture for efficient AI processing.

Conclusion:
Artificial intelligence and machine learning continue to advance at a rapid pace. As these technologies become more sophisticated and accessible, they will increasingly shape how we work, communicate, and solve complex problems. The key to harnessing their potential lies in responsible development and deployment, ensuring that AI serves humanity's best interests."

# Upload document
echo -e "\n📤 Uploading comprehensive AI/ML document..."
UPLOAD=$(curl -s -X POST "$BASE_URL/collections/$COLLECTION_ID/documents" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"AI and Machine Learning: Comprehensive Overview\",
    \"text\": $(echo "$DOCUMENT_TEXT" | jq -Rs .)
  }")

TASK_ID=$(echo "$UPLOAD" | jq -r '.task_id')
DOC_ID=$(echo "$UPLOAD" | jq -r '.document_id')

echo "📋 Document ID: $DOC_ID"
echo "🔄 Task ID: $TASK_ID"

# Monitor progress with detailed display
echo -e "\n⚡ Real-Time Processing Progress:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

LAST_STAGE=""
START_TIME=$(date +%s)

while true; do
  PROGRESS=$(curl -s "$BASE_URL/progress/$TASK_ID")
  STATE=$(echo "$PROGRESS" | jq -r '.state')
  STAGE=$(echo "$PROGRESS" | jq -r '.stage // "unknown"')
  PERCENT=$(echo "$PROGRESS" | jq -r '.progress // 0')
  MESSAGE=$(echo "$PROGRESS" | jq -r '.message // ""')
  
  # Calculate time
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))
  
  # Stage transition message
  if [ "$STAGE" != "$LAST_STAGE" ] && [ "$LAST_STAGE" != "" ]; then
    echo
  fi
  
  # Progress bar
  BAR_LENGTH=50
  FILLED=$(printf "%.0f" $(echo "scale=2; $PERCENT * $BAR_LENGTH / 100" | bc))
  
  # Color based on stage
  case "$STAGE" in
    "splitting") COLOR="\033[96m" ;;    # Bright Cyan
    "embedding") COLOR="\033[95m" ;;    # Bright Magenta
    "storing") COLOR="\033[94m" ;;      # Bright Blue
    "finalizing") COLOR="\033[93m" ;;   # Bright Yellow
    "complete") COLOR="\033[92m" ;;     # Bright Green
    "failed") COLOR="\033[91m" ;;       # Bright Red
    *) COLOR="\033[0m" ;;
  esac
  
  # Display progress
  printf "\r${COLOR}%-12s [" "$STAGE"
  printf "%${FILLED}s" | tr ' ' '█'
  printf "%$((BAR_LENGTH - FILLED))s" | tr ' ' '░'
  printf "] %3d%% %-40s [%ds]\033[0m" "$PERCENT" "${MESSAGE:0:40}" "$ELAPSED"
  
  LAST_STAGE=$STAGE
  
  if [ "$STATE" = "SUCCESS" ]; then
    echo -e "\n\n✅ Processing completed successfully in ${ELAPSED} seconds!"
    break
  elif [ "$STATE" = "FAILURE" ]; then
    echo -e "\n\n❌ Processing failed!"
    ERROR=$(echo "$PROGRESS" | jq -r '.error // "Unknown error"')
    echo "Error: $ERROR"
    break
  fi
  
  sleep 0.2
done

# Get detailed status
echo -e "\n📊 Final Document Status:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

DOC_STATUS=$(curl -s "$BASE_URL/documents/$DOC_ID/status")
if [ $? -eq 0 ] && [ -n "$DOC_STATUS" ]; then
  echo "Title: $(echo "$DOC_STATUS" | jq -r '.title // "N/A"')"
  echo "Status: $(echo "$DOC_STATUS" | jq -r '.status // "N/A"')"
  echo "Chunks: $(echo "$DOC_STATUS" | jq -r '.chunk_count // 0')"
  echo "Processing Time: ${ELAPSED} seconds"
  
  # Parse processing_progress if it's a string
  PROGRESS_DATA=$(echo "$DOC_STATUS" | jq -r '.processing_progress // "{}"')
  if [ "$PROGRESS_DATA" != "{}" ]; then
    echo -e "\nProcessing Details:"
    echo "$PROGRESS_DATA" | jq '.' 2>/dev/null || echo "$PROGRESS_DATA"
  fi
fi

# Test search
echo -e "\n🔍 Testing RAG Search:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "Query: \"What are the main types of machine learning?\""
SEARCH=$(curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{
    \"question\": \"What are the main types of machine learning?\",
    \"collection_ids\": [\"$COLLECTION_ID\"]
  }")

if [ $? -eq 0 ] && [ -n "$SEARCH" ]; then
  ANSWER=$(echo "$SEARCH" | jq -r '.answer // "No answer"')
  echo -e "\nAnswer:"
  echo "$ANSWER" | fold -s -w 70
  
  CITATIONS=$(echo "$SEARCH" | jq -r '.citations // []' 2>/dev/null)
  if [ "$CITATIONS" != "[]" ] && [ "$CITATIONS" != "" ]; then
    echo -e "\nCitations found: $(echo "$CITATIONS" | jq '. | length' 2>/dev/null || echo "0")"
  fi
fi

# Show collection stats
echo -e "\n📈 Collection Statistics:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

COLLECTION_INFO=$(curl -s "$BASE_URL/collections/$COLLECTION_ID")
if [ $? -eq 0 ] && [ -n "$COLLECTION_INFO" ]; then
  echo "Collection: $(echo "$COLLECTION_INFO" | jq -r '.name // "N/A"')"
  echo "Documents: $(echo "$COLLECTION_INFO" | jq -r '.document_count // 0')"
  echo "Total Documents (including subfolders): $(echo "$COLLECTION_INFO" | jq -r '.total_document_count // 0')"
fi

# Cleanup
echo -e "\n🧹 Cleanup..."
curl -s -X DELETE "$BASE_URL/collections/$COLLECTION_ID?hard_delete=true" > /dev/null
echo "✅ Test completed successfully!"