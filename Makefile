# PrivateGPT Legal AI - Makefile
# Simple commands for development and deployment

.PHONY: help install setup start stop restart build clean reset nuke logs status shell

# Default target
help:
	@echo "🚀 PrivateGPT Legal AI - Development Commands"
	@echo "============================================="
	@echo ""
	@echo "📦 Setup Commands:"
	@echo "  make install       - Install Docker & Docker Compose (Ubuntu/Debian)"
	@echo "  make setup         - Initialize environment and start services"
	@echo "  make init          - Create .env file from template"
	@echo ""
	@echo "🔄 Development Commands:"
	@echo "  make start         - Start all services"
	@echo "  make stop          - Stop all services"
	@echo "  make restart       - Restart all services"
	@echo "  make build         - Rebuild and start services"
	@echo ""
	@echo "🧹 Cleanup Commands:"
	@echo "  make clean         - Stop and remove containers"
	@echo "  make reset         - Complete reset (containers + volumes)"
	@echo "  make nuke          - Nuclear option (everything gone)"
	@echo ""
	@echo "🔍 Utility Commands:"
	@echo "  make logs          - Show all service logs"
	@echo "  make logs-auth     - Show auth service logs"
	@echo "  make logs-app      - Show streamlit app logs"
	@echo "  make status        - Show service status"
	@echo "  make shell         - Open shell in streamlit container"
	@echo "  make test          - Test all endpoints"

# Installation commands
install:
	@echo "🔧 Installing Docker and Docker Compose..."
	@if command -v docker >/dev/null 2>&1; then \
		echo "✅ Docker already installed"; \
	else \
		echo "📦 Installing Docker..."; \
		sudo apt-get update; \
		sudo apt-get install -y docker.io docker-compose; \
		sudo systemctl start docker; \
		sudo systemctl enable docker; \
		sudo usermod -aG docker $$USER; \
		echo "⚠️  Log out and back in for Docker group changes"; \
	fi

# Setup commands
init:
	@echo "📝 Creating .env file..."
	@if [ ! -f .env ]; then \
		cp env.example .env; \
		echo "✅ Created .env from template"; \
	else \
		echo "⚠️  .env already exists"; \
	fi

setup: init
	@echo "🚀 Setting up PrivateGPT Legal AI..."
	@mkdir -p data/uploads logs/{auth,app,ollama,weaviate,n8n,grafana}
	@echo "📁 Created directories"
	@$(MAKE) start

# Development commands
start:
	@echo "🚀 Starting all services..."
	@docker-compose up -d
	@echo "✅ Services started"
	@echo "🌐 Access at: http://localhost/"
	@echo "🔑 Login: admin / admin"

stop:
	@echo "⏹️  Stopping all services..."
	@docker-compose down
	@echo "✅ Services stopped"

restart: stop start

build:
	@echo "🔨 Building and starting services..."
	@docker-compose up -d --build
	@echo "✅ Services built and started"

# Cleanup commands
clean:
	@echo "🧹 Cleaning up containers..."
	@docker-compose down
	@docker container prune -f
	@echo "✅ Containers cleaned"

reset:
	@echo "🔄 Resetting environment..."
	@docker-compose down -v
	@docker container prune -f
	@docker volume prune -f
	@docker network prune -f
	@echo "✅ Environment reset"

nuke:
	@echo "💥 Nuclear cleanup (removes everything)..."
	@echo "⚠️  This will remove ALL Docker containers, volumes, and images!"
	@read -p "Are you sure? (y/N) " confirm && [ "$$confirm" = "y" ]
	@docker stop $$(docker ps -aq) 2>/dev/null || true
	@docker rm $$(docker ps -aq) 2>/dev/null || true
	@docker volume rm $$(docker volume ls -q) 2>/dev/null || true
	@docker network rm $$(docker network ls -q) 2>/dev/null || true
	@docker image rm $$(docker image ls -aq) 2>/dev/null || true
	@echo "💥 Everything nuked!"

# Utility commands
logs:
	@echo "📋 Showing all service logs..."
	@docker-compose logs -f

logs-auth:
	@echo "📋 Showing auth service logs..."
	@docker-compose logs -f auth-service

logs-app:
	@echo "📋 Showing streamlit app logs..."
	@docker-compose logs -f streamlit-app

logs-ollama:
	@echo "📋 Showing ollama logs..."
	@docker-compose logs -f ollama

status:
	@echo "📊 Service Status:"
	@docker-compose ps

shell:
	@echo "🐚 Opening shell in streamlit container..."
	@docker-compose exec streamlit-app /bin/bash

shell-auth:
	@echo "🐚 Opening shell in auth service..."
	@docker-compose exec auth-service /bin/bash

# Testing commands
test:
	@echo "🧪 Testing endpoints..."
	@echo "Health check:"
	@curl -s http://localhost/health || echo "❌ Main app not responding"
	@echo "Auth service:"
	@curl -s http://localhost/api/auth/health || echo "❌ Auth service not responding"
	@echo "✅ Tests complete"

# Development helpers
dev-restart-app:
	@echo "🔄 Restarting just the app..."
	@docker-compose restart streamlit-app
	@echo "✅ App restarted"

dev-rebuild-app:
	@echo "🔨 Rebuilding just the app..."
	@docker-compose up -d --build streamlit-app
	@echo "✅ App rebuilt"

# Quick fixes
fix-permissions:
	@echo "🔧 Fixing permissions..."
	@sudo chmod 666 /var/run/docker.sock 2>/dev/null || true
	@sudo chown -R $$USER:$$USER . 2>/dev/null || true
	@echo "✅ Permissions fixed"

# Show configuration
config:
	@echo "⚙️  Current configuration:"
	@echo "Project: $$(grep COMPOSE_PROJECT_NAME .env 2>/dev/null | cut -d= -f2 || echo 'privategpt')"
	@echo "Environment: $$(grep ENVIRONMENT .env 2>/dev/null | cut -d= -f2 || echo 'production')"
	@echo "Docker: $$(docker --version 2>/dev/null || echo 'Not installed')"
	@echo "Docker Compose: $$(docker-compose --version 2>/dev/null || echo 'Not installed')"

# Port forwarding helper (for SSH development)
tunnel:
	@echo "🌐 Setting up port forwarding..."
	@echo "Run this on your LOCAL machine:"
	@echo "ssh -p 51800 -i gpukey root@82.79.250.18 -L 8081:localhost:80"
	@echo "Then visit: http://localhost:8081"

# Monitoring and dashboards
grafana:
	@echo "📊 Grafana Dashboard Access:"
	@echo "Main System: http://localhost:8081/grafana/d/privategpt-main"
	@echo "Legal Compliance: http://localhost:8081/grafana/d/privategpt-compliance"
	@echo "Prometheus: http://localhost:8081/prometheus"
	@echo "Login: admin / admin"

logs-all:
	@echo "📋 Showing all service logs..."
	@docker-compose logs --tail=100 -f

logs-errors:
	@echo "🚨 Showing error logs..."
	@docker-compose logs --tail=50 | grep -i "error\|exception\|fail" 