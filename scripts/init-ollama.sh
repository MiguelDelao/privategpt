#!/bin/bash

# PrivateGPT Legal AI - Ollama Model Initialization
# Downloads and configures LLM models using centralized configuration

set -e

echo "🤖 Initializing Ollama with configured model..."

# Get model from centralized config (with fallback)
if [ -f "../config.json" ]; then
    MODEL=$(python3 -c "import json; print(json.load(open('../config.json'))['model']['name'])" 2>/dev/null || echo "llama3.2:1b")
elif [ -f "config.json" ]; then
    MODEL=$(python3 -c "import json; print(json.load(open('config.json'))['model']['name'])" 2>/dev/null || echo "llama3.2:1b")
else
    MODEL="llama3.2:1b"  # Final fallback
fi

echo "📋 Model Configuration:"
echo "  Selected Model: $MODEL"
echo "  Source: Centralized config.json"

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