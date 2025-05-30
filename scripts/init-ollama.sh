#!/bin/bash

# PrivateGPT Legal AI - Ollama Model Initialization
# Automatically downloads and configures LLM models based on MODEL_MODE

set -e

echo "🤖 Initializing Ollama with configured models..."

# Get configuration from environment
MODE=${MODEL_MODE:-"dev"}
DEV_MODEL=${OLLAMA_MODEL_DEV:-"llama3.2:8b"}
PROD_MODEL=${OLLAMA_MODEL_PROD:-"llama3.1:70b"}

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

# Wait for Ollama service to be ready
echo "⏳ Waiting for Ollama service..."
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    echo "Waiting for Ollama to start..."
    sleep 2
done

echo "✅ Ollama service is ready"

# Check if model already exists
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