#!/bin/bash

# Setup MCP-optimized Ollama model
set -e

echo "🚀 Setting up MCP-optimized Ollama model..."

# Check if Ollama is available
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed or not in PATH"
    echo "Please install Ollama first: https://ollama.ai"
    exit 1
fi

# Set Ollama host if running in Docker
export OLLAMA_HOST=${OLLAMA_HOST:-http://localhost:11434}

echo "📦 Building custom MCP model from Modelfile..."

# Copy the Modelfile to a temporary location
TEMP_DIR=$(mktemp -d)
cp src/privategpt/services/mcp/Modelfile "$TEMP_DIR/"

# Build the custom model
cd "$TEMP_DIR"
ollama create privategpt-mcp -f Modelfile

if [ $? -eq 0 ]; then
    echo "✅ MCP model 'privategpt-mcp' created successfully!"
    echo ""
    echo "🔧 Model configuration:"
    echo "  - Base model: qwen2.5:3b"
    echo "  - System prompt: Optimized for MCP tool usage"
    echo "  - Temperature: 0.7"
    echo "  - Context length: 8192 tokens"
    echo ""
    echo "🎯 Usage:"
    echo "  ollama run privategpt-mcp"
    echo "  or use in your application with model name: 'privategpt-mcp'"
    echo ""
    echo "📋 Available tools when using this model:"
    echo "  - Document search and RAG"
    echo "  - File management"
    echo "  - System monitoring"
    echo "  - Service health checks"
else
    echo "❌ Failed to create MCP model"
    exit 1
fi

# Cleanup
rm -rf "$TEMP_DIR"

echo "🎉 MCP model setup complete!"