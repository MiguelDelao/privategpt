# PrivateGPT Legal AI - Makefile
# Simple commands for development and deployment

.PHONY: help install setup start stop restart build clean reset nuke logs status shell setup-elk elk-status logs-elk kibana kibana-tunnel logs-search logs-errors-elk verify-elk restart-elk

# Default target
help:
	@echo "PrivateGPT Legal AI - Development Commands"
	@echo "==========================================="
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
	@echo "  make setup-elk     - Show ELK data access info (no pre-built dashboards)"
	@echo "  make setup-elk-dashboards - Install pre-built dashboards (optional)"
	@echo "  make kibana        - Show Kibana dashboard access info"
	@echo "  make logs-elk      - Show ELK stack service logs"
	@echo "  make elk-status    - Check ELK stack health"
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
	@echo "  make switch-mode   - Switch between dev/prod models"
	@echo "  make download-models - Download models for current mode"

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
	@echo "Setting up PrivateGPT..."
	@mkdir -p data/uploads logs/{auth,app,ollama,weaviate,n8n,grafana}
	@echo "Created directories"
	@$(MAKE) start
	@echo "ELK Stack is ready for custom dashboards"
	@$(MAKE) kibana

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

# Development commands
start:
	@echo "Starting all services..."
	@docker-compose up -d
	@echo "✅ Services started"
	@echo "Access at: http://localhost/"
	@echo "Login: admin / admin"

stop:
	@echo "Stopping all services..."
	@docker-compose down
	@echo "✅ Services stopped"

restart: stop start
	@echo "restarting..."

build:
	@echo "Building and starting services..."
	@docker-compose up -d --build
	@echo "✅ Services built and started"
	@echo "ELK Stack ready for custom dashboards"

go: reset build
	@echo "✅ System fully reset and rebuilt"

# Cleanup commands
clean:
	@echo "Cleaning up containers..."
	@docker-compose down
	@docker container prune -f
	@echo "✅ Containers cleaned"

reset:
	@echo "Resetting environment..."
	@docker-compose down -v
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
	@echo "🚀 Ready Dashboard:"
	@echo "  📊 PrivateGPT System Monitor"
	@echo "  🔗 URL: http://localhost/kibana/app/dashboards#/view/d72e7c30-3f8a-11f0-8fcb-13b28cd3f8fa"
	@echo ""
	@echo "📋 Container-Specific Panels:"
	@echo "  🔐 Auth Service       - Authentication logs"
	@echo "  🖥️ Streamlit App     - Main application logs"  
	@echo "  🧠 Ollama LLM        - AI model interactions"
	@echo "  ⚡ N8N Workflows     - Automation task logs"
	@echo "  🗄️ Database Service  - Vector DB operations"
	@echo "  📊 ELK Stack         - Monitoring infrastructure"
	@echo "  ⚡ System Metrics    - Live system performance"
	@echo "  📋 All App Logs     - Combined application view"
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

dashboard: ## 📊 Open PrivateGPT System Monitor Dashboard
	@echo "📊 Opening PrivateGPT System Monitor Dashboard..."
	@echo "🚀 Dashboard URL: http://localhost/kibana/app/dashboards#/view/d72e7c30-3f8a-11f0-8fcb-13b28cd3f8fa"
	@command -v xdg-open >/dev/null && xdg-open "http://localhost/kibana/app/dashboards#/view/d72e7c30-3f8a-11f0-8fcb-13b28cd3f8fa" || echo "Manually open: http://localhost/kibana/app/dashboards#/view/d72e7c30-3f8a-11f0-8fcb-13b28cd3f8fa"

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

# Enhanced ELK logging
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
	@MODE=$$(grep "MODEL_MODE" .env 2>/dev/null | cut -d'=' -f2 || echo "dev"); \
	if [ "$$MODE" = "prod" ]; then \
		MODEL=$$(grep "OLLAMA_MODEL_PROD" .env 2>/dev/null | cut -d'=' -f2 || echo "llama3.1:70b"); \
	else \
		MODEL=$$(grep "OLLAMA_MODEL_DEV" .env 2>/dev/null | cut -d'=' -f2 || echo "llama3.2:8b"); \
	fi; \
	echo "Using $$MODE mode with model: $$MODEL"; \
	curl -X POST http://localhost:8081/ollama/api/generate \
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
show-model:
	@echo "Current Model Configuration:"
	@echo "============================"
	@if [ -f .env ]; then \
		echo "From .env file:"; \
		grep "MODEL_MODE\|OLLAMA_MODEL" .env | sed 's/^/  /'; \
	else \
		echo "From env.example (no .env file found):"; \
		grep "MODEL_MODE\|OLLAMA_MODEL" env.example | sed 's/^/  /'; \
	fi
	@echo ""
	@echo "Active model in Ollama:"
	@docker exec ollama-service ollama list 2>/dev/null | head -5 || echo "  ❌ Ollama not running"

switch-mode:
	@echo "Model Mode Switch Tool"
	@echo "======================"
	@if [ -f .env ]; then \
		current_mode=$$(grep "MODEL_MODE" .env | cut -d'=' -f2); \
		echo "Current mode: $$current_mode"; \
		echo "Available modes:"; \
		echo "  dev  - Development (llama3.2:8b)"; \
		echo "  prod - Production (llama3.1:70b)"; \
		echo ""; \
		read -p "Enter new mode (dev/prod): " new_mode; \
		if [ "$$new_mode" = "dev" ] || [ "$$new_mode" = "prod" ]; then \
			sed -i.bak "s/MODEL_MODE=.*/MODEL_MODE=$$new_mode/" .env; \
			echo "✅ Switched to $$new_mode mode"; \
			echo "🔄 Restart services with 'make restart' to apply changes"; \
		else \
			echo "❌ Invalid mode. Use 'dev' or 'prod'"; \
		fi; \
	else \
		echo "⚠️  No .env file found. Run 'make init' first"; \
		exit 1; \
	fi

download-models:
	@echo "Downloading models for current mode..."
	@if docker ps | grep -q ollama-service; then \
		docker exec ollama-service /scripts/init-ollama.sh; \
	else \
		echo "❌ Ollama service not running. Start with 'make start' first"; \
		exit 1; \
	fi

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