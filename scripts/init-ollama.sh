#!/bin/bash

# PrivateGPT v2 - Ollama Model Initialization
# Downloads and configures LLM models using settings configuration

set -e

echo "🤖 Initializing Ollama with configured model..."

# Get model from settings (with fallback)
MODEL=${OLLAMA_MODEL:-"llama3.2:1b"}
OLLAMA_URL=${OLLAMA_URL:-"http://ollama:11434"}

echo "📋 Model Configuration:"
echo "  Selected Model: $MODEL"
echo "  Ollama URL: $OLLAMA_URL"
echo "  Source: Environment variables"

# Wait for Ollama service to be ready
echo "⏳ Waiting for Ollama service at $OLLAMA_URL..."
for i in {1..60}; do
    if curl -s "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
        echo "✅ Ollama service is ready"
        break
    fi
    echo "Waiting for Ollama to start... (attempt $i/60)"
    sleep 5
done

# Final check
if ! curl -s "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
    echo "❌ Ollama failed to start after 60 attempts"
    exit 1
fi

# Check if model already exists
echo "🔍 Checking for existing models..."
if curl -s "$OLLAMA_URL/api/tags" | grep -q "$MODEL"; then
    echo "✅ Model $MODEL already exists"
else
    echo "📥 Downloading model: $MODEL"
    echo "⚠️  This may take several minutes depending on model size..."
    
    # Pull model using Ollama API
    curl -X POST "$OLLAMA_URL/api/pull" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"$MODEL\"}" \
        --progress-bar
    
    echo "✅ Model $MODEL downloaded successfully"
fi

# Verify model is available
echo "🎯 Verifying model availability..."
if curl -s "$OLLAMA_URL/api/tags" | grep -q "$MODEL"; then
    echo "✅ Model $MODEL is ready for use"
else
    echo "❌ Model verification failed"
    exit 1
fi

echo "🚀 Ollama initialization complete!"
echo "📊 Available models:"
curl -s "$OLLAMA_URL/api/tags" | jq -r '.models[]?.name // "No models found"' 2>/dev/null || echo "Could not list models"

echo "🔗 Ollama is ready at: $OLLAMA_URL"