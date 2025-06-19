# PrivateGPT Legal AI - Makefile
# Simple commands for development and deployment

.PHONY: help install setup start stop restart build clean reset nuke logs status shell setup-elk elk-status logs-elk kibana kibana-tunnel logs-search logs-errors-elk verify-elk restart-elk setup-dashboard discover install-model show-model switch-mode download-models env-info

# Auto-detect environment and set appropriate Docker Compose file
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
	COMPOSE_FILE = docker-compose-mac.yml
	ENV_TYPE = Mac M1
else
	COMPOSE_FILE = docker-compose.yml
	ENV_TYPE = Linux
endif

# Docker Compose command with auto-detected file
DOCKER_COMPOSE = docker-compose -f $(COMPOSE_FILE)

# Default target
help:
	@echo "PrivateGPT Legal AI - Development Commands"
	@echo "==========================================="
	@echo "Environment: $(ENV_TYPE) (using $(COMPOSE_FILE))"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make install       - Install Docker & Docker Compose (Ubuntu/Debian)"
	@echo "  make setup         - Initialize environment and start services"
	@echo "  make init          - Create .env file from template"
	@echo "  make go            - Full reset and rebuild for fresh deployment"
	@echo ""
	@echo "Development Commands:"
	@echo "  make start         - Start all services"
	@echo "  make stop          - Stop all services"
	@echo "  make restart       - Restart all services"
	@echo "  make build         - Rebuild and start services"
	@echo ""
	@echo "Cleanup Commands:"
	@echo "  make clean         - Stop and remove containers"
	@echo "  make reset         - Complete reset (containers + volumes)"
	@echo "  make nuke          - Nuclear option (everything gone)"
	@echo ""
	@echo "Monitoring & Logging (ELK Stack):"
	@echo "  make elk-status    - Check ELK stack health and dashboard info"
	@echo "  make setup-elk     - Show ELK data access info"
	@echo "  make setup-dashboard - Create data views for log access"
	@echo "  make discover      - Open Kibana Discover for log analysis"
	@echo "  make kibana        - Show Kibana dashboard access info"
	@echo "  make logs-elk      - Show ELK stack service logs"
	@echo "  make dashboard     - Open PrivateGPT System Monitor Dashboard"
	@echo ""
	@echo "Utility Commands:"
	@echo "  make logs          - Show all service logs"
	@echo "  make logs-auth     - Show auth service logs"
	@echo "  make logs-app      - Show streamlit app logs"
	@echo "  make logs-ollama   - Show ollama logs (model downloads)"
	@echo "  make status        - Show service status"
	@echo "  make shell         - Open shell in streamlit container"
	@echo "  make test          - Test all endpoints"
	@echo ""
	@echo "Model Management:"
	@echo "  make show-model    - Show current model configuration"

	@echo "  make download-models - Download models for current mode"
	@echo "  make install-model MODEL=<name> - Install specific model (e.g., make install-model MODEL=llama3:8b)"
	@echo ""
	@echo "Environment Commands:"
	@echo "  make env-info      - Show detected environment and compose file"

# Installation commands
install:
	@echo "Installing Docker and Docker Compose..."
	@if command -v docker >/dev/null 2>&1; then \
		echo "✅ Docker already installed"; \
	else \
		echo "Installing Docker..."; \
		sudo apt-get update; \
		sudo apt-get install -y docker.io docker-compose; \
		sudo systemctl start docker; \
		sudo systemctl enable docker; \
		sudo usermod -aG docker $$USER; \
		echo "Warning: Log out and back in for Docker group changes"; \
	fi

# Setup commands
init:
	@echo "Creating .env file..."
	@if [ ! -f .env ]; then \
		cp env.example .env; \
		echo "✅ Created .env from template"; \
	else \
		echo "Warning: .env already exists"; \
	fi

setup: init
	@echo "Setting up PrivateGPT...
	@mkdir -p data/uploads logs/{auth,app,ollama,weaviate,n8n,grafana}
	@echo "Created directories"
	@$(MAKE) start
	@echo "Waiting for Ollama service to be ready..."
	@$(MAKE) wait-for-ollama
	@echo "Downloading required models..."
	@$(MAKE) download-models
	@echo "Creating custom dashboard..."
	@chmod +x scripts/setup-dashboard.sh
	@./scripts/setup-dashboard.sh > /dev/null 2>&1 && echo "✅ Dashboard ready" || echo "⚠️ Dashboard setup had issues"
	@echo "✅ Setup complete - access dashboard via 'make elk-status'"

# Wait for Ollama service to be ready
wait-for-ollama:
	@echo "Waiting for Ollama service to be ready..."
	@max_attempts=30; \
	attempt=0; \
	while [ $$attempt -lt $$max_attempts ]; do \
		if docker exec ollama-service ollama list >/dev/null 2>&1; then \
			echo "✅ Ollama service is ready"; \
			break; \
		fi; \
		attempt=$$((attempt + 1)); \
		echo "Attempt $$attempt/$$max_attempts - Ollama not ready yet, waiting 2 seconds..."; \
		sleep 2; \
	done; \
	if [ $$attempt -eq $$max_attempts ]; then \
		echo "❌ Ollama service failed to start within 60 seconds"; \
		exit 1; \
	fi

# Removed duplicate download-models target (see below for clean version)

# ELK Stack Setup Commands (Optional)

# Quick ELK data access (no pre-built dashboards)
setup-elk:
	@echo "ELK Stack Data Access"
	@echo "===================="
	@echo "✅ Your data is being collected automatically"
	@echo "Create custom dashboards in Kibana:"
	@echo "   - Go to Analytics → Dashboard → Create new dashboard"
	@echo "   - Use Analytics → Discover to explore your data first"
	@echo ""
	@echo "Available Data Indices:"
	@curl -s "http://localhost:9200/_cat/indices?h=index,docs.count" 2>/dev/null | grep -E "(filebeat|metricbeat)" | sed 's/^/   /' || echo "   Warning: Data collection starting (may take a few minutes)"
	@echo ""
	@$(MAKE) kibana

# Setup custom dashboard automatically
setup-dashboard:
	@echo "Setting up PrivateGPT Custom Dashboard..."
	@chmod +x scripts/setup-dashboard.sh
	@./scripts/setup-dashboard.sh

# Development commands
start:
	@echo "Starting all services on $(ENV_TYPE)..."
	@$(DOCKER_COMPOSE) up -d
	@echo "✅ Services started"
	@echo "Access at: http://localhost/"
	@echo "Login: admin / admin"

stop:
	@echo "Stopping all services..."
	@$(DOCKER_COMPOSE) down
	@echo "✅ Services stopped"

restart: stop start
	@echo "restarting..."

build:
	@echo "Building and starting services on $(ENV_TYPE)..."
	@$(DOCKER_COMPOSE) up -d --build
	@echo "Creating custom dashboard..."
	@chmod +x scripts/setup-dashboard.sh
	@./scripts/setup-dashboard.sh > /dev/null 2>&1 && echo "✅ Dashboard ready" || echo "⚠️ Dashboard setup had issues"
	@echo "✅ Services built and started"

go: reset clean build
	@echo "✅ System fully reset and rebuilt"

# Cleanup commands
clean:
	@echo "Cleaning up containers..."
	@$(DOCKER_COMPOSE) down
	@docker container prune -f
	@echo "✅ Containers cleaned"

reset:
	@echo "Resetting environment..."
	@$(DOCKER_COMPOSE) down -v
	@docker container prune -f
	@docker volume prune -f
	@docker network prune -f
	@echo "✅ Environment reset"

nuke:
	@echo "Nuclear cleanup (removes everything)..."
	@echo "Warning: This will remove ALL Docker containers, volumes, and images!"
	@read -p "Are you sure? (y/N) " confirm && [ "$$confirm" = "y" ]
	@docker stop $$(docker ps -aq) 2>/dev/null || true
	@docker rm $$(docker ps -aq) 2>/dev/null || true
	@docker volume rm $$(docker volume ls -q) 2>/dev/null || true
	@docker network rm $$(docker network ls -q) 2>/dev/null || true
	@docker image rm $$(docker image ls -aq) 2>/dev/null || true
	@echo "✅ Everything nuked"

# ELK Stack specific commands
elk-status: ## 📊 Check ELK Stack status and dashboard info
	@echo "📊 ELK Stack Status & Dashboard"
	@echo "================================"
	@echo ""
	@echo "🔧 Service Status:"
	@docker-compose ps elasticsearch logstash kibana filebeat metricbeat | tail -n +2 | sed 's/^/  /'
	@echo ""
	@echo "📈 Data Collection:"
	@curl -s "http://localhost:9200/_cat/indices?h=index,docs.count,store.size" 2>/dev/null | grep -E "(filebeat|metricbeat)" | sed 's/^/  /' || echo "  ⚠️  No data collected yet (may take 2-3 minutes after startup)"
	@echo ""
	@echo "🚀 Auto-Created Dashboard:"
	@echo "  📊 PrivateGPT System Monitor"
	@echo "  🔗 URL: http://localhost/kibana/app/dashboards#/view/53c5b260-3f89-11f0-b185-c1d217685ac0"
	@echo ""
	@echo "📋 Dashboard Panels:"
	@echo "  🔐 Auth Service - Authentication service logs (container.name: auth-service)"
	@echo "  🖥️ Streamlit App - Main application frontend logs (container.name: streamlit-app)"
	@echo "  🧠 Ollama LLM - Language model service logs (container.name: ollama-service)"
	@echo "  ⚡ N8N Workflows - Workflow automation logs (container.name: n8n-automation)"
	@echo "  🗄️ Database Service - Weaviate vector database logs (container.name: weaviate-db)"
	@echo "  📊 ELK Stack - Monitoring infrastructure logs (elasticsearch, logstash, kibana, etc.)"
	@echo "  ⚡ System Metrics - CPU, memory, and container metrics"
	@echo "  📋 All App Logs - Combined view of all application logs"
	@echo ""
	@echo "⚡ Quick Commands:"
	@echo "  make dashboard  - Open dashboard directly"
	@echo "  make kibana     - Open Kibana main interface"
	@echo "  make logs-elk   - View ELK service logs"

logs-elk:
	@echo "ELK Stack Service Logs"
	@echo "======================"
	@docker-compose logs --tail=20 elasticsearch logstash kibana filebeat metricbeat

kibana: ## 🔍 Open Kibana (ELK Stack Web Interface)
	@echo "🔍 Opening Kibana..."
	@echo "📊 Kibana URL: http://localhost/kibana/"
	@command -v xdg-open >/dev/null && xdg-open http://localhost/kibana/ || echo "Manually open: http://localhost/kibana/"

# Utility commands
logs:
	@echo "Showing all service logs..."
	@docker-compose logs -f

logs-auth:
	@echo "Showing auth service logs..."
	@docker-compose logs -f auth-service

logs-app:
	@echo "Showing streamlit app logs..."
	@docker-compose logs -f streamlit-app

logs-ollama:
	@echo "Showing ollama logs..."
	@docker-compose logs -f ollama

logs-weaviate:
	@echo "Showing weaviate db logs..."
	@docker-compose logs -f weaviate-db

logs-knowledge:
	@echo "Showing knowledge service logs..."
	@docker-compose logs -f knowledge-service

status:
	@echo "PrivateGPT Service Status"
	@echo "========================="
	@docker ps --filter "label=com.docker.compose.project=privategpt" --format "{{.Names}}: {{.Status}}" | while read line; do \
		name=$$(echo "$$line" | cut -d: -f1); \
		status=$$(echo "$$line" | cut -d: -f2-); \
		if echo "$$status" | grep -q "Up"; then \
			echo "🟢 $$name: $$status"; \
		else \
			echo "🔴 $$name: $$status"; \
		fi; \
	done

shell:
	@echo "Opening shell in streamlit container..."
	@docker-compose exec streamlit-app /bin/bash

shell-auth:
	@echo "Opening shell in auth service..."
	@docker-compose exec auth-service /bin/bash

# Testing commands
test:
	@echo "Testing endpoints..."
	@echo "Health check:"
	@curl -s http://localhost/health || echo "❌ Main app not responding"
	@echo "Auth service:"
	@curl -s http://localhost/api/auth/health || echo "❌ Auth service not responding"
	@echo "✅ Tests complete"

# Development helpers
dev-restart-app:
	@echo "Restarting just the app..."
	@docker-compose restart streamlit-app
	@echo "✅ App restarted"

dev-rebuild-app:
	@echo "Rebuilding just the app..."
	@docker-compose up -d --build streamlit-app
	@echo "✅ App rebuilt"

# Quick fixes
fix-permissions:
	@echo "Fixing permissions..."
	@sudo chmod 666 /var/run/docker.sock 2>/dev/null || true
	@sudo chown -R $$USER:$$USER . 2>/dev/null || true
	@echo "✅ Permissions fixed"

# Show configuration
config:
	@echo "Current configuration:"
	@echo "Project: $$(grep COMPOSE_PROJECT_NAME .env 2>/dev/null | cut -d= -f2 || echo 'privategpt')"
	@echo "Environment: $$(grep ENVIRONMENT .env 2>/dev/null | cut -d= -f2 || echo 'production')"
	@echo "Docker: $$(docker --version 2>/dev/null || echo 'Not installed')"
	@echo "Docker Compose: $$(docker-compose --version 2>/dev/null || echo 'Not installed')"

# Port forwarding helper (for SSH development)
tunnel:
	@echo "Setting up port forwarding..."
	@echo "Run this on your LOCAL machine:"
	@echo "ssh -p 51800 -i gpukey root@82.79.250.18 -L 8081:localhost:80"
	@echo "Then visit: http://localhost:8081"

# Monitoring and dashboards - now using ELK stack
kibana-tunnel:
	@echo "Kibana Dashboard Access via SSH tunnel:"
	@echo "Main: http://localhost:8081/kibana/app/dashboards"
	@echo "Logs: http://localhost:8081/kibana/app/discover"
	@echo "System Metrics: Check pre-built Metricbeat dashboards"
	@echo "Application Logs: Check pre-built Filebeat dashboards"

logs-all:
	@echo "Showing all service logs..."
	@docker-compose logs --tail=100 -f

logs-errors:
	@echo "Showing error logs..."
	@docker-compose logs --tail=50 | grep -i "error\|exception\|fail"

# Advanced ELK logging
logs-search:
	@echo "Searching logs for specific pattern..."
	@read -p "Enter search pattern: " pattern; \
	curl -s -X GET "http://localhost:9200/filebeat-*/_search" \
		-H 'Content-Type: application/json' \
		-d "{\"query\":{\"match\":{\"message\":\"$$pattern\"}},\"size\":10}" \
		2>/dev/null | jq '.hits.hits[]._source | {timestamp: .["@timestamp"], message: .message}' || \
		echo "❌ Search failed - check if Elasticsearch is running"

logs-errors-elk:
	@echo "Searching for errors in ELK..."
	@curl -s -X GET "http://localhost:9200/filebeat-*/_search" \
		-H 'Content-Type: application/json' \
		-d '{"query":{"bool":{"should":[{"match":{"message":"error"}},{"match":{"message":"exception"}},{"match":{"message":"fail"}}]}},"size":20}' \
		2>/dev/null | jq '.hits.hits[]._source | {timestamp: .["@timestamp"], container: .container.name, message: .message}' || \
		echo "❌ Error search failed - check if Elasticsearch is running"

# n8n and LLM testing
setup-n8n:
	@echo "Setting up n8n workflows..."
	@chmod +x scripts/setup-n8n-workflows.sh
	@./scripts/setup-n8n-workflows.sh

test-llm:
	@echo "Testing Llama LLM directly..."
	@MODEL="llama3.2:1b"; \
	echo "Using model: $$MODEL"; \
	curl -X POST http://localhost:11434/api/generate \
		-H 'Content-Type: application/json' \
		-d "{\"model\": \"$$MODEL\", \"prompt\": \"Hello! Please respond in one sentence.\", \"stream\": false}" \
		2>/dev/null | jq '.response' || echo "❌ LLM test failed"

test-n8n-webhook:
	@echo "Testing n8n webhook workflow..."
	@curl -X POST http://localhost:8081/n8n/webhook/test-llama \
		-H 'Content-Type: application/json' \
		-d '{"query": "What is the purpose of contract law?"}' \
		2>/dev/null | jq '.' || echo "❌ n8n webhook test failed"

n8n-access:
	@echo "n8n Access Information:"
	@echo "URL: http://localhost:8081/n8n"
	@echo "Login: admin / admin"
	@echo "Workflows to import:"
	@echo "  - config/n8n/simple-llama-test.json"
	@echo "  - config/n8n/llama-test-workflow.json"

# Model Management Commands
install-model:
	@if [ -z "$(MODEL)" ]; then \
		echo "❌ Error: MODEL parameter is required"; \
		echo "Usage: make install-model MODEL=<model_name>"; \
		echo "Examples:"; \
		echo "  make install-model MODEL=llama3:8b"; \
		echo "  make install-model MODEL=llama3.1:70b"; \
		echo "  make install-model MODEL=codellama:7b"; \
		echo "  make install-model MODEL=mistral:7b"; \
		echo "  make install-model MODEL=qwen2.5:7b"; \
		exit 1; \
	fi
	@echo "Installing model: $(MODEL)"
	@echo "=========================="
	@if docker ps | grep -q ollama-service; then \
		echo "🔍 Checking if model $(MODEL) already exists..."; \
		if docker exec ollama-service ollama list | grep -q "$(MODEL)"; then \
			echo "✅ Model $(MODEL) is already installed"; \
		else \
			echo "📥 Downloading model $(MODEL) (this may take several minutes)..."; \
			echo "⏳ Please wait while Ollama downloads the model..."; \
			if docker exec ollama-service ollama pull "$(MODEL)"; then \
				echo "✅ Model $(MODEL) downloaded successfully"; \
				echo "📋 Updated model list:"; \
				docker exec ollama-service ollama list; \
			else \
				echo "❌ Failed to download model $(MODEL)"; \
				echo "💡 Make sure the model name is correct and available"; \
				echo "🔗 Check available models at: https://ollama.com/library"; \
				exit 1; \
			fi; \
		fi; \
	else \
		echo "❌ Ollama service is not running"; \
		echo "💡 Start services first with: make start"; \
		exit 1; \
	fi

show-model:
	@echo "Current Model Configuration:"
	@echo "============================"
	@echo "Default model: llama3:8b"
	@echo ""
	@echo "Available models in Ollama:"
	@docker exec ollama-service ollama list 2>/dev/null || echo "  ❌ Ollama not running"
	@echo ""
	@echo "To download models manually:"
	@echo "  make install-model MODEL=<model_name>"

download-models:
	@echo "Available Models to Download:"
	@echo "============================"
	@echo "Popular models you can install:"
	@echo "  make install-model MODEL=llama3:8b      # Recommended default"
	@echo "  make install-model MODEL=llama3:70b     # Larger, more capable"
	@echo "  make install-model MODEL=codellama:7b   # Code-focused"
	@echo "  make install-model MODEL=mistral:7b     # Alternative LLM"
	@echo "  make install-model MODEL=qwen2.5:7b     # Multilingual"
	@echo ""
	@echo "To see all available models: https://ollama.com/library"

# Complete ELK setup verification
verify-elk:
	@echo "Complete ELK Stack Verification:"
	@echo "================================"
	@$(MAKE) elk-status
	@echo ""
	@echo "Dashboard Setup Status:"
	@docker exec filebeat filebeat export dashboard 2>/dev/null | grep -q "dashboard" && echo "✅ Filebeat dashboards ready" || echo "Warning: Filebeat dashboards pending"
	@docker exec metricbeat metricbeat export dashboard 2>/dev/null | grep -q "dashboard" && echo "✅ Metricbeat dashboards ready" || echo "Warning: Metricbeat dashboards pending"
	@echo ""
	@$(MAKE) kibana

# Quick ELK restart for troubleshooting
restart-elk:
	@echo "Restarting ELK Stack services only..."
	@docker-compose restart elasticsearch logstash kibana filebeat metricbeat
	@sleep 20
	@$(MAKE) setup-elk

# Add new direct access command
discover: ## 📊 Open Kibana Discover for log analysis
	@echo "📊 Opening Kibana Discover..."
	@echo "🔗 Container Logs: http://localhost/kibana/app/discover"
	@command -v xdg-open >/dev/null && xdg-open "http://localhost/kibana/app/discover" || echo "Manually open: http://localhost/kibana/app/discover"

# Add dashboard command back
dashboard: ## 📊 Open PrivateGPT System Monitor Dashboard
	@echo "📊 Opening PrivateGPT System Monitor Dashboard..."
	@echo "🚀 Dashboard URL: http://localhost/kibana/app/dashboards#/view/53c5b260-3f89-11f0-b185-c1d217685ac0"
	@command -v xdg-open >/dev/null && xdg-open "http://localhost/kibana/app/dashboards#/view/53c5b260-3f89-11f0-b185-c1d217685ac0" || echo "Manually open: http://localhost/kibana/app/dashboards#/view/53c5b260-3f89-11f0-b185-c1d217685ac0"

# Environment Information
env-info:
	@echo "PrivateGPT Environment Information"
	@echo "=================================="
	@echo "Detected OS: $(UNAME_S)"
	@echo "Environment Type: $(ENV_TYPE)"
	@echo "Docker Compose File: $(COMPOSE_FILE)"
	@echo "Docker Compose Command: $(DOCKER_COMPOSE)"
	@echo ""
	@echo "File Status:"
	@if [ -f $(COMPOSE_FILE) ]; then \
		echo "✅ $(COMPOSE_FILE) exists"; \
	else \
		echo "❌ $(COMPOSE_FILE) not found"; \
	fi
	@if [ -f docker-compose.yml ]; then \
		echo "✅ docker-compose.yml exists (for Linux)"; \
	else \
		echo "❌ docker-compose.yml not found"; \
	fi
	@echo ""
	@echo "Usage on different environments:"
	@echo "📱 Mac M1: All commands use docker-compose-mac.yml automatically"
	@echo "🐧 Linux: All commands use docker-compose.yml automatically"
	@echo "🚀 No need to remember different commands!" 