#!/bin/bash

# Legal AI Weaviate FastAPI Service Startup Script

echo "🏛️ Starting Weaviate Service..."

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check if Weaviate is accessible
echo "🔍 Checking Weaviate connection..."
WEAVIATE_URL=${WEAVIATE_URL:-"http://localhost:8080"}

if curl -s "$WEAVIATE_URL/v1/schema" > /dev/null 2>&1; then
    echo "✅ Weaviate is accessible at $WEAVIATE_URL"
else
    echo "⚠️  Warning: Cannot connect to Weaviate at $WEAVIATE_URL"
    echo "   Make sure Weaviate is running before using the service"
fi

# Start the service
echo "🚀 Starting FastAPI service on http://localhost:8002"
echo "📖 API Documentation: http://localhost:8002/docs"
echo "🔍 Health Check: http://localhost:8002/health"
echo ""
echo "Press Ctrl+C to stop the service"
echo ""

# Run the service
python weaviate_service.py 