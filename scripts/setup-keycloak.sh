#!/bin/bash

# Keycloak + Gateway Setup Script for PrivateGPT v2

set -e

echo "🔑 Setting up Keycloak + API Gateway for PrivateGPT v2"
echo "=================================================="

# Check if Docker and Docker Compose are available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating required directories..."
mkdir -p config/keycloak
mkdir -p logs

# Set environment variables for Keycloak
echo "🔧 Setting up environment variables..."
export KEYCLOAK_ADMIN_PASSWORD=${KEYCLOAK_ADMIN_PASSWORD:-admin123}
export N8N_PASSWORD=${N8N_PASSWORD:-changeme}

echo "   Keycloak Admin Password: $KEYCLOAK_ADMIN_PASSWORD"
echo "   N8N Password: $N8N_PASSWORD"

# Build base image first
echo "🏗️  Building base Docker image..."
docker build -f docker/base/Dockerfile -t privategpt/base:latest .

# Start the infrastructure services first
echo "🚀 Starting infrastructure services..."
docker-compose up -d keycloak-db keycloak redis db

# Wait for Keycloak to be ready
echo "⏳ Waiting for Keycloak to be ready..."
timeout 300 bash -c 'until curl -f http://localhost:8080/health/ready >/dev/null 2>&1; do sleep 5; done'

if [ $? -eq 0 ]; then
    echo "✅ Keycloak is ready!"
else
    echo "❌ Keycloak failed to start within 5 minutes"
    echo "Check logs with: docker-compose logs keycloak"
    exit 1
fi

# Configure Keycloak realm and users
echo "🔧 Configuring Keycloak realm and users..."
bash scripts/init-keycloak-realm.sh

# Start the application services
echo "🏃 Starting application services..."
docker-compose up -d gateway-service rag-service weaviate

# Wait for gateway to be ready
echo "⏳ Waiting for API Gateway to be ready..."
timeout 120 bash -c 'until curl -f http://localhost:8000/ >/dev/null 2>&1; do sleep 5; done'

if [ $? -eq 0 ]; then
    echo "✅ API Gateway is ready!"
else
    echo "❌ API Gateway failed to start within 2 minutes"
    echo "Check logs with: docker-compose logs gateway-service"
    exit 1
fi

# Start UI service
echo "🎨 Starting UI service..."
docker-compose up -d ui-service

# Wait for UI to be ready
echo "⏳ Waiting for UI to be ready..."
timeout 120 bash -c 'until curl -f http://localhost:8501 >/dev/null 2>&1; do sleep 5; done'

if [ $? -eq 0 ]; then
    echo "✅ UI is ready!"
else
    echo "❌ UI failed to start within 2 minutes"
    echo "Check logs with: docker-compose logs ui-service"
    exit 1
fi

# Start observability stack (optional)
read -p "🔍 Start observability stack (ELK)? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📊 Starting observability stack..."
    docker-compose up -d elasticsearch kibana filebeat
    
    # Wait for Kibana and import dashboard
    echo "⏳ Waiting for Kibana to be ready..."
    timeout 180 bash -c 'until curl -f http://localhost:5601/api/status >/dev/null 2>&1; do sleep 10; done'
    
    if [ $? -eq 0 ]; then
        echo "✅ Kibana is ready!"
        echo "📋 Importing dashboard..."
        bash scripts/import_dashboard.sh
    else
        echo "⚠️  Kibana took too long to start, but continuing..."
    fi
fi

echo ""
echo "🎉 PrivateGPT v2 with Keycloak + API Gateway is ready!"
echo "=================================================="
echo ""
echo "🌐 Access URLs:"
echo "   - PrivateGPT UI:     http://localhost:8501"
echo "   - API Gateway:       http://localhost:8000"
echo "   - Keycloak Admin:    http://localhost:8080"
echo "   - Weaviate:          http://localhost:8081"
echo ""
echo "🔐 Default Login Credentials:"
echo "   - Email:    admin@admin.com"
echo "   - Password: admin"
echo ""
echo "🔧 Keycloak Admin:"
echo "   - Username: admin"
echo "   - Password: $KEYCLOAK_ADMIN_PASSWORD"
echo ""
echo "📊 Observability (if enabled):"
echo "   - Kibana:           http://localhost/logs"
echo "   - Traefik Dashboard: http://localhost:8090/dashboard/"
echo ""
echo "🛠️  Useful Commands:"
echo "   - View logs:        docker-compose logs -f [service-name]"
echo "   - Stop all:         docker-compose down"
echo "   - Restart service:  docker-compose restart [service-name]"
echo "   - Check status:     docker-compose ps"
echo ""
echo "🔍 Troubleshooting:"
echo "   - Check gateway health: curl http://localhost:8000/"
echo "   - View service logs:    docker-compose logs [service-name]"