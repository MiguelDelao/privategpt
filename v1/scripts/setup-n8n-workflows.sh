#!/bin/bash

# PrivateGPT - n8n Workflow Setup Script
# Sets up testing workflows for Llama LLM integration using centralized config

echo "🚀 Setting up n8n workflows for PrivateGPT..."

# Get model from centralized config (with fallback)
if [ -f "../config.json" ]; then
    MODEL=$(python3 -c "import json; print(json.load(open('../config.json'))['model']['name'])" 2>/dev/null || echo "llama3.2:1b")
elif [ -f "config.json" ]; then
    MODEL=$(python3 -c "import json; print(json.load(open('config.json'))['model']['name'])" 2>/dev/null || echo "llama3.2:1b")
else
    MODEL="llama3.2:1b"  # Final fallback
fi

echo "📋 Using model from centralized config: $MODEL"

# Create directories
mkdir -p config/n8n
mkdir -p data/n8n-workflows

echo "📁 Created n8n directories"

# Update workflow files with configured model
if [ -f "config/n8n/simple-llama-test.json" ]; then
    echo "🔧 Updating simple-llama-test.json with model: $MODEL"
    sed -i.bak "s/\"model\":\"[^\"]*\"/\"model\":\"$MODEL\"/g" config/n8n/simple-llama-test.json
fi

if [ -f "config/n8n/llama-test-workflow.json" ]; then
    echo "🔧 Updating llama-test-workflow.json with model: $MODEL"
    sed -i.bak "s/\"model\":\"[^\"]*\"/\"model\":\"$MODEL\"/g" config/n8n/llama-test-workflow.json
fi

# Check if n8n is running
if ! docker-compose ps | grep -q "n8n-automation.*Up"; then
    echo "⚠️  n8n service is not running. Starting it..."
    docker-compose up -d n8n
    echo "⏳ Waiting for n8n to start..."
    sleep 30
fi

echo "✅ n8n workflows are ready to import!"
echo ""
echo "📋 Manual Import Instructions:"
echo "1. Access n8n at: http://localhost:8081/n8n"
echo "2. Login with: admin / admin"
echo "3. Go to: Workflows → Import from File"
echo "4. Import these files:"
echo "   - config/n8n/simple-llama-test.json (Manual trigger)"
echo "   - config/n8n/llama-test-workflow.json (Webhook trigger)"
echo ""
echo "🧪 Testing Commands:"
echo "# Test the webhook workflow:"
echo "curl -X POST http://localhost:8081/n8n/webhook/test-llama \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"query\": \"What is contract law?\"}'"
echo ""
echo "# Check if Ollama is ready:"
echo "curl http://localhost:8081/ollama/api/tags"
echo ""
echo "# Test Ollama directly:"
echo "curl -X POST http://localhost:8081/ollama/api/generate \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"model\": \"$MODEL\", \"prompt\": \"Hello!\", \"stream\": false}'" 