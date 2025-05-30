#!/bin/bash

# PrivateGPT Legal AI - Clean Setup Script
# Version: 2.1-clean

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${GREEN}[STEP $1]${NC} $2"
}

print_substep() {
    echo -e "${PURPLE}  → ${NC}$1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════╗"
    echo "║         PrivateGPT Legal AI              ║"
    echo "║         Clean Setup v2.1                 ║"
    echo "╚══════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_docker() {
    print_step "1" "Checking Docker..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
    fi
    
    # Test Docker access
    if docker ps &> /dev/null; then
        print_substep "Docker access verified"
    elif sudo docker ps &> /dev/null; then
        print_substep "Docker requires sudo - will use sudo for commands"
        export USE_SUDO=1
    else
        print_error "Docker is not accessible. Please check Docker installation."
    fi
    
    echo -e "${GREEN}✓ Docker ready${NC}"
}

setup_environment() {
    print_step "2" "Setting up environment..."
    
    # Copy environment template
    if [ ! -f ".env" ]; then
        if [ ! -f "env.example" ]; then
            print_error "env.example file not found. Please ensure you're in the correct directory."
        fi
        cp env.example .env
        print_substep "Created .env from template"
    else
        print_substep "Using existing .env file"
    fi
    
    # Set simple admin passwords
    sed -i.backup 's/your-super-secret-jwt-key-change-this-in-production/admin123456789abcdef/' .env
    sed -i.backup 's/your-weaviate-api-key-change-this/admin123456789/' .env  
    sed -i.backup 's/secure-grafana-password-change-this/admin/' .env
    sed -i.backup 's/secure-n8n-password-change-this/admin/' .env
    
    # Clean up backup file
    rm -f .env.backup
    
    print_substep "Set all passwords to 'admin'"
    echo -e "${GREEN}✓ Environment configured${NC}"
}

create_directories() {
    print_step "3" "Creating directories..."
    
    mkdir -p data/uploads
    mkdir -p logs/{auth,app,ollama,weaviate,n8n,grafana}
    
    print_substep "Created data and log directories"
    echo -e "${GREEN}✓ Directories ready${NC}"
}

start_services() {
    print_step "4" "Starting services..."
    
    # Use sudo if needed
    if [ "$USE_SUDO" = "1" ]; then
        DOCKER_CMD="sudo docker-compose"
    else
        DOCKER_CMD="docker-compose"
    fi
    
    print_substep "Pulling Docker images"
    $DOCKER_CMD pull
    
    print_substep "Starting all services"
    $DOCKER_CMD up -d
    
    echo -e "${GREEN}✓ Services started${NC}"
}

wait_for_services() {
    print_step "5" "Waiting for services..."
    
    print_substep "Giving services time to start (60 seconds)"
    for i in {1..60}; do
        echo -n "."
        sleep 1
        if [ $((i % 20)) -eq 0 ]; then
            echo " ${i}s"
        fi
    done
    echo ""
    
    echo -e "${GREEN}✓ Services should be ready${NC}"
}

download_model() {
    print_step "6" "Downloading AI model..."
    
    # Use sudo if needed
    if [ "$USE_SUDO" = "1" ]; then
        DOCKER_CMD="sudo docker"
    else
        DOCKER_CMD="docker"
    fi
    
    print_substep "Downloading LLaMA 3 8B model (this may take several minutes)"
    if $DOCKER_CMD exec ollama-service ollama pull llama3:8b; then
        print_substep "Model downloaded successfully"
    else
        print_warning "Model download failed. You can retry later with:"
        echo "  $DOCKER_CMD exec ollama-service ollama pull llama3:8b"
    fi
    
    echo -e "${GREEN}✓ Model setup complete${NC}"
}

show_completion() {
    print_step "7" "Setup complete! 🎉"
    
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
    echo -e "${YELLOW}🔑 All Logins:${NC}"
    echo "   Username: admin"
    echo "   Password: admin"
    echo ""
    echo -e "${GREEN}🔧 Useful Commands:${NC}"
    if [ "$USE_SUDO" = "1" ]; then
        echo "   • Check status: sudo docker-compose ps"
        echo "   • View logs: sudo docker-compose logs -f"
        echo "   • Stop all: sudo docker-compose down"
    else
        echo "   • Check status: docker-compose ps"
        echo "   • View logs: docker-compose logs -f"
        echo "   • Stop all: docker-compose down"
    fi
    echo ""
    echo -e "${GREEN}🎉 Your Legal AI system is ready!${NC}"
}

# Main execution
main() {
    print_header
    check_docker
    setup_environment
    create_directories
    start_services
    wait_for_services
    download_model
    show_completion
}

main "$@" 