#!/bin/bash

# PrivateGPT Legal AI - Ollama Model Initialization
# Automatically downloads and configures LLM models based on MODEL_MODE

set -e

echo "🤖 Initializing Ollama with configured models..."

# Get configuration from environment
MODE=${MODEL_MODE:-"dev"}
DEV_MODEL=${OLLAMA_MODEL_DEV:-"llama3:8b"}
PROD_MODEL=${OLLAMA_MODEL_PROD:-"llama3:70b"}

# Select model based on MODE
if [ "$MODE" = "prod" ]; then
    MODEL="$PROD_MODEL"
    echo "🏭 Production mode selected"
else
    MODEL="$DEV_MODEL"
    echo "🔧 Development mode selected"
fi

echo "📋 Model Configuration:"
echo "  Mode: $MODE"
echo "  Development Model: $DEV_MODEL"
echo "  Production Model: $PROD_MODEL"
echo "  Selected Model: $MODEL"

# Wait for Ollama service to be ready using ollama commands
echo "⏳ Waiting for Ollama service..."
for i in {1..30}; do
    if ollama list > /dev/null 2>&1; then
        echo "✅ Ollama service is ready"
        break
    fi
    echo "Waiting for Ollama to start... (attempt $i/30)"
    sleep 5
done

# Final check
if ! ollama list > /dev/null 2>&1; then
    echo "❌ Ollama failed to start after 30 attempts"
    exit 1
fi

# Check if model aLready exists
if ollama list | grep -q "$MODEL"; then
    echo "✅ Model $MODEL already exists"
else
    echo "📥 Downloading model: $MODEL"
    ollama pull "$MODEL"
    echo "✅ Model $MODEL downloaded successfully"
fi

# Set as default model
echo "🎯 Setting $MODEL as default model"
ollama run "$MODEL" --help > /dev/null 2>&1 || true

echo "🚀 Ollama initialization complete!"
echo "📊 Available models:"
ollama list 