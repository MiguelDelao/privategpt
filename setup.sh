#!/bin/bash

# PrivateGPT Legal AI - Complete Setup Script
# Version: 2.0-complete

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
    echo "║         Complete Setup v2.0              ║"
    echo "╚══════════════════════════════════════════╝"
    echo -e "${NC}"
}

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VERSION=$VERSION_ID
    else
        print_error "Cannot detect Linux distribution"
    fi
    
    echo -e "${BLUE}Detected OS:${NC} $OS $VERSION"
}

check_sudo() {
    if [ "$EUID" -eq 0 ]; then
        SUDO=""
        print_warning "Running as root"
    else
        SUDO="sudo"
        if ! command -v sudo &> /dev/null; then
            print_error "sudo is required but not installed. Please run as root or install sudo."
        fi
        
        # Test sudo access
        if ! $SUDO -n true 2>/dev/null; then
            echo -e "${YELLOW}This script requires sudo privileges. You may be prompted for your password.${NC}"
            $SUDO -v || print_error "Failed to obtain sudo privileges"
        fi
    fi
}

update_system() {
    print_step "1" "Updating system packages..."
    
    case "$OS" in
        "Ubuntu"*|"Debian"*)
            print_substep "Updating apt package index"
            $SUDO apt-get update -y
            
            print_substep "Installing essential packages"
            $SUDO apt-get install -y \
                curl \
                wget \
                gnupg \
                lsb-release \
                ca-certificates \
                software-properties-common \
                apt-transport-https \
                openssl
            ;;
        "CentOS"*|"Red Hat"*|"Fedora"*)
            print_substep "Updating yum/dnf package index"
            if command -v dnf &> /dev/null; then
                $SUDO dnf update -y
                $SUDO dnf install -y curl wget gnupg2 openssl
            else
                $SUDO yum update -y
                $SUDO yum install -y curl wget gnupg2 openssl
            fi
            ;;
        *)
            print_warning "Unsupported OS: $OS. Attempting to continue..."
            ;;
    esac
    
    echo -e "${GREEN}✓ System packages updated${NC}"
}

install_docker() {
    print_step "2" "Installing Docker..."
    
    if command -v docker &> /dev/null; then
        print_substep "Docker is already installed"
        docker --version
        
        # Check if Docker service is running
        if ! $SUDO systemctl is-active --quiet docker; then
            print_substep "Starting Docker service"
            $SUDO systemctl start docker
            $SUDO systemctl enable docker
        fi
        
        echo -e "${GREEN}✓ Docker ready${NC}"
        return
    fi
    
    case "$OS" in
        "Ubuntu"*|"Debian"*)
            print_substep "Adding Docker GPG key"
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | $SUDO gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
            
            print_substep "Adding Docker repository"
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | $SUDO tee /etc/apt/sources.list.d/docker.list > /dev/null
            
            print_substep "Installing Docker"
            $SUDO apt-get update -y
            $SUDO apt-get install -y docker-ce docker-ce-cli containerd.io
            ;;
        "CentOS"*|"Red Hat"*)
            print_substep "Adding Docker repository"
            $SUDO yum install -y yum-utils
            $SUDO yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            
            print_substep "Installing Docker"
            $SUDO yum install -y docker-ce docker-ce-cli containerd.io
            ;;
        "Fedora"*)
            print_substep "Adding Docker repository"
            $SUDO dnf install -y dnf-plugins-core
            $SUDO dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
            
            print_substep "Installing Docker"
            $SUDO dnf install -y docker-ce docker-ce-cli containerd.io
            ;;
        *)
            print_error "Unsupported OS for Docker installation: $OS"
            ;;
    esac
    
    print_substep "Starting and enabling Docker service"
    $SUDO systemctl start docker
    $SUDO systemctl enable docker
    
    # Wait a moment for Docker to fully start
    sleep 3
    
    print_substep "Adding current user to docker group"
    $SUDO usermod -aG docker $USER
    
    # Fix Docker socket permissions
    print_substep "Setting Docker socket permissions"
    $SUDO chmod 666 /var/run/docker.sock || true
    
    echo -e "${GREEN}✓ Docker installed successfully${NC}"
    echo -e "${YELLOW}Note: You may need to log out and back in for Docker group changes to take effect${NC}"
}

install_docker_compose() {
    print_step "3" "Installing Docker Compose..."
    
    if command -v docker-compose &> /dev/null; then
        print_substep "Docker Compose is already installed"
        docker-compose --version
        echo -e "${GREEN}✓ Docker Compose ready${NC}"
        return
    fi
    
    print_substep "Downloading Docker Compose"
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    $SUDO curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    
    print_substep "Making Docker Compose executable"
    $SUDO chmod +x /usr/local/bin/docker-compose
    
    # Create symlink if needed
    if [ ! -f /usr/bin/docker-compose ]; then
        $SUDO ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    fi
    
    echo -e "${GREEN}✓ Docker Compose installed successfully${NC}"
    docker-compose --version
}

install_nvidia_docker() {
    print_step "4" "Checking for NVIDIA GPU and installing NVIDIA Container Toolkit..."
    
    if ! command -v nvidia-smi &> /dev/null; then
        print_warning "NVIDIA drivers not detected. Skipping NVIDIA Container Toolkit installation."
        echo -e "${YELLOW}If you have an NVIDIA GPU, please install the drivers first.${NC}"
        return
    fi
    
    print_substep "NVIDIA GPU detected"
    nvidia-smi --query-gpu=name --format=csv,noheader
    
    case "$OS" in
        "Ubuntu"*|"Debian"*)
            print_substep "Adding NVIDIA Container Toolkit repository"
            distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
                && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | $SUDO gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
                && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
                    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
                    $SUDO tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
            
            print_substep "Installing NVIDIA Container Toolkit"
            $SUDO apt-get update -y
            $SUDO apt-get install -y nvidia-container-toolkit
            ;;
        *)
            print_warning "NVIDIA Container Toolkit auto-installation not supported for $OS"
            echo -e "${YELLOW}Please install NVIDIA Container Toolkit manually if you plan to use GPU acceleration${NC}"
            return
            ;;
    esac
    
    print_substep "Configuring Docker for NVIDIA"
    $SUDO nvidia-ctk runtime configure --runtime=docker
    $SUDO systemctl restart docker
    
    print_substep "Testing NVIDIA Docker integration"
    if docker run --rm --gpus all nvidia/cuda:11.0-base-ubuntu20.04 nvidia-smi; then
        echo -e "${GREEN}✓ NVIDIA Container Toolkit configured successfully${NC}"
    else
        print_warning "NVIDIA Docker test failed. GPU acceleration may not work properly."
    fi
}

verify_docker_access() {
    print_step "5" "Verifying Docker access..."
    
    # Ensure Docker service is running
    if ! $SUDO systemctl is-active --quiet docker; then
        print_substep "Starting Docker service"
        $SUDO systemctl start docker
        sleep 5
    fi
    
    # Try to run docker without sudo first
    if docker ps &> /dev/null; then
        echo -e "${GREEN}✓ Docker access verified${NC}"
        return
    fi
    
    # If that fails, try with newgrp docker
    print_substep "Attempting to refresh Docker group membership"
    if newgrp docker <<< "docker ps" &> /dev/null; then
        echo -e "${GREEN}✓ Docker access verified with group refresh${NC}"
        return
    fi
    
    # If still failing, try fixing socket permissions
    print_substep "Fixing Docker socket permissions"
    $SUDO chmod 666 /var/run/docker.sock
    
    if docker ps &> /dev/null; then
        echo -e "${GREEN}✓ Docker access verified after permission fix${NC}"
        return
    fi
    
    # Last resort - check with sudo
    print_warning "Docker requires sudo access. Checking if Docker works with sudo..."
    if $SUDO docker ps &> /dev/null; then
        echo -e "${YELLOW}✓ Docker works with sudo${NC}"
        echo -e "${YELLOW}Setting up temporary docker alias for this session${NC}"
        
        # Create a function to use sudo docker for this session
        export DOCKER_SUDO=1
        alias docker="$SUDO docker"
        alias docker-compose="$SUDO docker-compose"
        
        echo -e "${YELLOW}Note: You may need to log out and back in for non-sudo Docker access${NC}"
        echo -e "${YELLOW}Or run: newgrp docker${NC}"
    else
        print_error "Docker is not working properly. Please check Docker installation."
    fi
}

setup_environment() {
    print_step "6" "Setting up environment..."
    
    # Copy environment template if needed
    if [ ! -f ".env" ]; then
        if [ ! -f "env.example" ]; then
            print_error "env.example file not found. Please ensure you're in the correct directory."
        fi
        cp env.example .env
        echo -e "${YELLOW}Created .env from template${NC}"
    fi
    
    # Generate secure secrets if still default
    if grep -q "your-super-secret-jwt-key" .env; then
        JWT_SECRET=$(openssl rand -hex 32)
        sed -i.backup "s/your-super-secret-jwt-key-change-this-in-production/$JWT_SECRET/" .env
        print_substep "Generated JWT secret"
    fi
    
    if grep -q "your-weaviate-api-key" .env; then
        WEAVIATE_KEY=$(openssl rand -hex 16)
        sed -i.backup "s/your-weaviate-api-key-change-this/$WEAVIATE_KEY/" .env
        print_substep "Generated Weaviate API key"
    fi
    
    # Use simple admin passwords
    if grep -q "secure-grafana-password" .env; then
        sed -i.backup "s/secure-grafana-password-change-this/admin/" .env
        print_substep "Set Grafana password to: admin"
    fi
    
    if grep -q "secure-n8n-password" .env; then
        sed -i.backup "s/secure-n8n-password-change-this/admin/" .env
        print_substep "Set n8n password to: admin"
    fi
    
    # Clean up backup files
    rm -f .env.backup
    
    echo -e "${GREEN}✓ Environment ready${NC}"
}

create_directories() {
    print_step "7" "Creating directories..."
    
    mkdir -p data/uploads
    mkdir -p logs/{auth,app,ollama,weaviate,n8n,grafana}
    
    # Set proper permissions
    chmod -R 755 data
    chmod -R 755 logs
    
    echo -e "${GREEN}✓ Directories created${NC}"
}

deploy_services() {
    print_step "8" "Starting services..."
    
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml not found. Please ensure you're in the correct directory."
    fi
    
    # Use sudo for docker commands if needed
    DOCKER_CMD="docker-compose"
    if [ ! -z "$DOCKER_SUDO" ]; then
        DOCKER_CMD="$SUDO docker-compose"
    fi
    
    print_substep "Pulling Docker images"
    $DOCKER_CMD pull || print_warning "Some images may not have pulled successfully"
    
    print_substep "Starting services"
    $DOCKER_CMD up -d
    
    echo -e "${GREEN}✓ Services started${NC}"
}

wait_for_services() {
    print_step "9" "Waiting for services to be ready..."
    
    echo "Waiting 90 seconds for services to start..."
    for i in {1..90}; do
        echo -n "."
        sleep 1
        if [ $((i % 30)) -eq 0 ]; then
            echo " ${i}s"
        fi
    done
    echo ""
    
    print_substep "Checking service health"
    docker-compose ps
    
    echo -e "${GREEN}✓ Services should be ready${NC}"
}

download_model() {
    print_step "10" "Downloading AI model..."
    
    # Use sudo for docker commands if needed
    DOCKER_CMD="docker"
    if [ ! -z "$DOCKER_SUDO" ]; then
        DOCKER_CMD="$SUDO docker"
    fi
    
    print_substep "Checking if Ollama service is ready"
    for i in {1..30}; do
        if $DOCKER_CMD exec ollama-service ollama list &> /dev/null; then
            break
        fi
        echo -n "."
        sleep 2
    done
    echo ""
    
    print_substep "Downloading LLaMA 3 8B model (this will take several minutes)"
    if $DOCKER_CMD exec ollama-service ollama pull llama3:8b; then
        echo -e "${GREEN}✓ Model downloaded successfully${NC}"
    else
        print_warning "Model download failed or is incomplete. You can retry later with:"
        if [ ! -z "$DOCKER_SUDO" ]; then
            echo "$SUDO docker exec ollama-service ollama pull llama3:8b"
        else
            echo "docker exec ollama-service ollama pull llama3:8b"
        fi
    fi
}

show_access_info() {
    print_step "11" "Setup complete!"
    
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
    echo "   Password: admin"
    echo ""
    
    # Get passwords from .env
    if [ -f ".env" ]; then
        echo -e "${YELLOW}🔐 Service Passwords:${NC}"
        echo "   Grafana: admin / admin"
        echo "   n8n: admin / admin"
    fi
    
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║          Post-Installation Notes         ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
    echo ""
    
    if [ "$SUDO" != "" ] || [ ! -z "$DOCKER_SUDO" ]; then
        echo -e "${YELLOW}⚠️  Important Docker Notes:${NC}"
        if [ ! -z "$DOCKER_SUDO" ]; then
            echo "   • Docker commands currently require sudo in this session"
            echo "   • To fix permanently, run: newgrp docker"
            echo "   • Or log out and back in to refresh group membership"
        else
            echo "   • You may need to log out and back in for Docker group changes"
            echo "   • If Docker commands require sudo, run: newgrp docker"
        fi
        echo ""
    fi
    
    echo -e "${GREEN}📚 Next Steps:${NC}"
    echo "   1. Access the application at http://localhost/"
    echo "   2. Log in with admin / admin"
    echo "   3. Upload your first document for analysis"
    echo "   4. Check system health in Grafana dashboards"
    echo ""
    
    echo -e "${GREEN}🔧 Useful Commands:${NC}"
    if [ ! -z "$DOCKER_SUDO" ]; then
        echo "   • Check services: $SUDO docker-compose ps"
        echo "   • View logs: $SUDO docker-compose logs -f [service-name]"
        echo "   • Restart services: $SUDO docker-compose restart"
        echo "   • Stop all: $SUDO docker-compose down"
    else
        echo "   • Check services: docker-compose ps"
        echo "   • View logs: docker-compose logs -f [service-name]"
        echo "   • Restart services: docker-compose restart"
        echo "   • Stop all: docker-compose down"
    fi
    echo ""
    
    echo -e "${GREEN}🎉 Your Legal AI system is ready!${NC}"
}

check_post_install() {
    print_step "12" "Final verification..."
    
    # Use sudo for docker commands if needed
    DOCKER_CMD="docker-compose"
    if [ ! -z "$DOCKER_SUDO" ]; then
        DOCKER_CMD="$SUDO docker-compose"
    fi
    
    print_substep "Checking service status"
    if $DOCKER_CMD ps | grep -q "Up"; then
        echo -e "${GREEN}✓ Services are running${NC}"
    else
        print_warning "Some services may not be fully started yet"
    fi
    
    print_substep "Testing web interface availability"
    for i in {1..10}; do
        if curl -s http://localhost/health &> /dev/null; then
            echo -e "${GREEN}✓ Web interface is accessible${NC}"
            break
        elif [ $i -eq 10 ]; then
            print_warning "Web interface is not yet accessible. Services may still be starting."
        else
            echo -n "."
            sleep 3
        fi
    done
    
    echo -e "${GREEN}✓ Installation verification complete${NC}"
}

# Main execution
main() {
    print_header
    detect_os
    check_sudo
    update_system
    install_docker
    install_docker_compose
    install_nvidia_docker
    verify_docker_access
    setup_environment
    create_directories
    deploy_services
    wait_for_services
    download_model
    check_post_install
    show_access_info
    
    echo ""
    echo -e "${GREEN}🚀 Installation completed successfully!${NC}"
    echo -e "${BLUE}For support and documentation, visit: https://github.com/your-repo/privategpt${NC}"
}

main "$@" 