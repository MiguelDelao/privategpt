#!/bin/bash

# PrivateGPT Legal AI - Simple Setup Script
# Version: 1.5-simplified

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${GREEN}[STEP $1]${NC} $2"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════╗"
    echo "║         PrivateGPT Legal AI              ║"
    echo "║         Simple Setup v1.5                ║"
    echo "╚══════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_requirements() {
    print_step "1" "Checking requirements..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
    fi
    
    echo -e "${GREEN}✓ Requirements satisfied${NC}"
}

setup_environment() {
    print_step "2" "Setting up environment..."
    
    # Copy environment template if needed
    if [ ! -f ".env" ]; then
        cp env.example .env
        echo -e "${YELLOW}Created .env from template${NC}"
    fi
    
    # Generate secure secrets if still default
    if grep -q "your-super-secret-jwt-key" .env; then
        JWT_SECRET=$(openssl rand -hex 32)
        sed -i "s/your-super-secret-jwt-key-change-this-in-production/$JWT_SECRET/" .env
    fi
    
    if grep -q "your-weaviate-api-key" .env; then
        WEAVIATE_KEY=$(openssl rand -hex 16)
        sed -i "s/your-weaviate-api-key-change-this/$WEAVIATE_KEY/" .env
    fi
    
    if grep -q "secure-grafana-password" .env; then
        GRAFANA_PASS=$(openssl rand -base64 12)
        sed -i "s/secure-grafana-password-change-this/$GRAFANA_PASS/" .env
        echo "Grafana password: $GRAFANA_PASS"
    fi
    
    if grep -q "secure-n8n-password" .env; then
        N8N_PASS=$(openssl rand -base64 12)
        sed -i "s/secure-n8n-password-change-this/$N8N_PASS/" .env
        echo "n8n password: $N8N_PASS"
    fi
    
    echo -e "${GREEN}✓ Environment ready${NC}"
}

create_directories() {
    print_step "3" "Creating directories..."
    
    mkdir -p data/uploads
    mkdir -p logs/{auth,app,ollama,weaviate,n8n,grafana}
    
    echo -e "${GREEN}✓ Directories created${NC}"
}

deploy_services() {
    print_step "4" "Starting services..."
    
    docker-compose up -d
    
    echo -e "${GREEN}✓ Services started${NC}"
}

wait_for_services() {
    print_step "5" "Waiting for services to be ready..."
    
    echo "Waiting 60 seconds for services to start..."
    sleep 60
    
    echo -e "${GREEN}✓ Services should be ready${NC}"
}

download_model() {
    print_step "6" "Downloading AI model..."
    
    echo "Downloading LLaMA 3 8B model (this will take a few minutes)..."
    docker exec ollama-service ollama pull llama3:8b || echo "Model download will continue in background"
    
    echo -e "${GREEN}✓ Model download initiated${NC}"
}

show_access_info() {
    print_step "7" "Setup complete!"
    
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║            Access Information            ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}🌐 Main App:${NC}      http://localhost/"
    echo -e "${GREEN}📊 Grafana:${NC}       http://localhost/grafana"
    echo -e "${GREEN}🔄 n8n:${NC}           http://localhost/n8n"
    echo -e "${GREEN}📈 Prometheus:${NC}    http://localhost/prometheus"
    echo ""
    echo -e "${YELLOW}🔑 Default Login:${NC}"
    echo "   Email: admin@legal-ai.local"
    echo "   Password: admin123"
    echo ""
    
    # Get passwords from .env
    if [ -f ".env" ]; then
        GRAFANA_PASS=$(grep GRAFANA_ADMIN_PASSWORD .env | cut -d'=' -f2)
        N8N_PASS=$(grep N8N_PASSWORD .env | cut -d'=' -f2)
        echo -e "${YELLOW}🔐 Service Passwords:${NC}"
        echo "   Grafana: admin / $GRAFANA_PASS"
        echo "   n8n: admin / $N8N_PASS"
    fi
    
    echo ""
    echo -e "${GREEN}🎉 Your Legal AI system is ready!${NC}"
}

# Main execution
main() {
    print_header
    check_requirements
    setup_environment
    create_directories
    deploy_services
    wait_for_services
    download_model
    show_access_info
}

main "$@" 