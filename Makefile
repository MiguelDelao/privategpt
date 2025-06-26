.PHONY: help start stop restart restart-rag restart-llm restart-gateway restart-celery restart-mcp build build-base clean clean-all test test-unit test-api stack-logs import-dashboard status ensure-dashboard install-model list-models remove-model logs logs-follow logs-gateway logs-rag logs-llm logs-ui logs-db logs-redis logs-weaviate logs-ollama logs-keycloak logs-keycloak-db logs-keycloak-setup logs-elasticsearch logs-kibana logs-filebeat logs-traefik logs-n8n logs-tests logs-auth logs-vector logs-database diagnose nuke hard-build build-ui dev-ui restart-ui start-ui-only stop-ui rebuild-ui start-with-nextjs logs-nextjs ui-shell ui-install ui-clean

# Default docker compose file inside v2
DC = docker-compose -f docker-compose.yml

help:
	@echo "PrivateGPT v2 Makefile"
	@echo "======================"
	@echo "make start   - Start all v2 containers"
	@echo "make stop    - Stop all v2 containers"
	@echo "make restart - Restart all running containers (fast reload for code changes)"
	@echo ""
	@echo "Quick Restart Commands (for development):"
	@echo "make restart-rag     - Restart RAG service only"
	@echo "make restart-llm     - Restart LLM service only"
	@echo "make restart-gateway - Restart Gateway service only"
	@echo "make restart-celery  - Restart Celery worker only"
	@echo "make restart-mcp     - Restart MCP service only"
	@echo ""
	@echo "Build Commands:"
	@echo "make build   - Smart build using Docker cache (FAST, recommended)"
	@echo "make build-safe - Force rebuild without cache (SLOW, guaranteed clean)"
	@echo "make build-base - Build (or rebuild) the common base image"
	@echo ""
	@echo "Clean Commands:"
	@echo "make clean   - Remove containers + dangling images (preserves base images)"
	@echo "make clean-deep - Remove containers + ALL project images (preserves volumes)"
	@echo "make clean-all - Remove containers and ALL volumes (including models)"
	@echo "Testing:"
	@echo "make test         - Run all tests (unit + integration)"
	@echo "make test-unit    - Run unit tests only"
	@echo "make test-integration - Run integration tests only"
	@echo "make test-conversation - Run conversation management tests"
	@echo "make test-auth    - Run authentication tests"
	@echo "make test-quick   - Run core tests (conversation + auth)"
	@echo "make stack-logs - Start Elasticsearch, Kibana, and Filebeat"
	@echo "make import-dashboard - Import a Kibana dashboard"
	@echo "make status - Show the status of all containers"
	@echo "make ensure-dashboard - Import dashboard and verify"
	@echo ""
	@echo "Model Management:"
	@echo "make install-model MODEL=<name> - Install specific Ollama model"
	@echo "make setup-mcp-model - Setup MCP-optimized model"
	@echo "make list-models - Show available Ollama models"
	@echo "make remove-model MODEL=<name> - Remove specific Ollama model"
	@echo ""
	@echo "UI Development:"
	@echo "make build-ui - Build Next.js UI service"
	@echo "make dev-ui - Start full development environment with UI"
	@echo "make restart-ui - Restart just the UI service"
	@echo "make start-ui-only - Start only the UI container"
	@echo "make stop-ui - Stop the UI service"
	@echo "make rebuild-ui - Rebuild UI from scratch (no cache)"
	@echo "make start-with-nextjs - Start system with Next.js UI as primary"
	@echo "make logs-nextjs - Follow Next.js UI logs"
	@echo "make ui-shell - Open shell in UI container"
	@echo "make ui-install - Install/update UI dependencies"
	@echo "make ui-clean - Clean and reinstall UI dependencies"
	@echo ""
	@echo "Logs:"
	@echo "make logs - Show logs for all services"
	@echo "make logs-follow - Follow logs for all services"
	@echo "make logs-gateway - Gateway service logs"
	@echo "make logs-rag - RAG service logs"
	@echo "make logs-llm - LLM service logs"
	@echo "make logs-ui - UI service logs"
	@echo "make logs-ollama - Ollama logs"
	@echo "make logs-mcp - MCP service logs"
	@echo "make logs-celery - Celery worker logs"
	@echo "make logs-keycloak - Keycloak authentication logs"
	@echo "make logs-db - Database logs"
	@echo "... (and more: logs-redis, logs-weaviate, etc.)"
	@echo ""
	@echo "Troubleshooting:"
	@echo "make diagnose - Diagnose Docker and system issues"
	@echo "make nuke - Nuclear option: delete EVERYTHING"
	@echo "make hard-build - Force complete rebuild after nuke"

start:
	$(DC) up -d

stop:
	$(DC) down

restart:
	@echo "🔄 Restarting all services..."
	$(DC) restart

restart-rag:
	@echo "🔄 Restarting RAG service..."
	$(DC) restart rag-service

restart-llm:
	@echo "🔄 Restarting LLM service..."
	$(DC) restart llm-service

restart-gateway:
	@echo "🔄 Restarting Gateway service..."
	$(DC) restart gateway-service

restart-celery:
	@echo "🔄 Restarting Celery worker..."
	$(DC) restart celery-worker

restart-mcp:
	@echo "🔄 Restarting MCP service..."
	$(DC) restart mcp-service

build-base:
	docker build -f docker/base/Dockerfile -t privategpt/base:latest .


# Smart build that uses Docker cache effectively (FAST)
build:
	@echo "🔨 Building services (using Docker cache)..."
	$(DC) build
	@echo "🚀 Starting services..."
	$(DC) up -d
	@echo "Setting up Keycloak realm and users..."
	$(DC) up --no-deps keycloak-setup
	@echo "✅ Build complete! UI available at http://localhost"
	@echo "🔐 Login with: admin@admin.com / admin"
	@echo "🔑 Keycloak admin: http://localhost:8180"
	@echo "🤖 LLM service: http://localhost:8003"
	@echo ""
	@echo "📥 To install Ollama models:"
	@echo "   make install-model MODEL=llama3.2:1b"
	@echo "   make install-model MODEL=llama3.2:3b"
	@echo "   make list-models"

# Safe build - forces complete rebuild without cache (SLOW but GUARANTEED)
build-safe: build-base
	@echo "🧹 Cleaning up any existing containers..."
	$(DC) down --remove-orphans || true
	@echo "🔨 Force rebuilding all services (no cache)..."
	$(DC) up -d --build --force-recreate
	@echo "Setting up Keycloak realm and users..."
	$(DC) up --no-deps keycloak-setup
	@echo "✅ Safe build complete! UI available at http://localhost"
	@echo "🔐 Login with: admin@admin.com / admin"
	@echo "🔑 Keycloak admin: http://localhost:8180"
	@echo "🤖 LLM service: http://localhost:8003"
	@echo ""
	@echo "📥 To install Ollama models:"
	@echo "   make install-model MODEL=llama3.2:1b"
	@echo "   make install-model MODEL=llama3.2:3b"
	@echo "   make list-models"

# Smart clean - removes containers and dangling images (preserves base images)
clean:
	@echo "🧹 Stopping and removing containers..."
	$(DC) down --remove-orphans
	@echo "🧹 Cleaning up dangling images..."
	docker image prune -f
	docker container prune -f
	docker network prune -f
	# Note: Preserving ollama_data volume and base images
	# Use 'make clean-all' to remove all volumes including models
	# Use 'make clean-deep' to also remove all images

# Deep clean - removes containers AND all project images (preserves volumes)
clean-deep:
	@echo "🧹 Stopping and removing containers..."
	$(DC) down --remove-orphans
	@echo "🧹 Removing ALL PrivateGPT images..."
	docker images | grep -E "privategpt|<none>" | awk '{print $$3}' | xargs -r docker rmi -f 2>/dev/null || true
	docker container prune -f
	docker network prune -f
	docker image prune -a -f
	@echo "✅ Deep clean complete! All images removed (volumes preserved)"

clean-all:
	$(DC) down -v --remove-orphans
	docker container prune -f
	docker network prune -f
	docker volume prune -f



# Run pytest; assumes editable install (pip install -e .)
# Developers may also run `

## ADD TEST TARGETS ##

test:
	@echo "🧪 Running all tests..."
	$(DC) build tests
	$(DC) run --rm tests pytest tests -v

test-unit:
	@echo "🧪 Running unit tests..."
	$(DC) build tests
	$(DC) run --rm tests pytest tests/unit -v

test-integration:
	@echo "🧪 Running integration tests..."
	$(DC) build tests
	$(DC) run --rm tests pytest tests/integration -v

test-conversation:
	@echo "🧪 Running conversation management tests..."
	$(DC) build tests
	$(DC) run --rm tests pytest tests/unit/conversation tests/integration/test_conversation_management.py -v

test-auth:
	@echo "🧪 Running authentication tests..."
	$(DC) build tests
	$(DC) run --rm tests pytest tests/integration/test_auth_integration.py tests/integration/test_jwt_keycloak_flow.py -v

test-quick:
	@echo "🧪 Running quick test suite (conversation + JWT)..."
	$(DC) build tests
	$(DC) run --rm tests pytest tests/unit/conversation tests/integration/test_conversation_management.py tests/integration/test_jwt_keycloak_flow.py -v

test-api: test-integration

# -------------------------------------------------------------------
# Observability helpers
# -------------------------------------------------------------------

stack-logs:   ## Start ES+Kibana+Filebeat and import dashboard automatically
	docker-compose up -d elasticsearch kibana filebeat
	bash scripts/wait_for_kibana.sh
	bash scripts/import_dashboard.sh

# Retained for manual re-imports if needed
import-dashboard:
	bash scripts/wait_for_kibana.sh
	curl -s -H "kbn-xsrf: true" \
	     -F "file=@docs/observability/kibana_dashboard.ndjson;type=application/ndjson" \
	     http://localhost:5601/api/saved_objects/_import?overwrite=true | cat

# -------------------------------------------------------------------
# Utility targets
# -------------------------------------------------------------------

status:
	docker-compose ps

ensure-dashboard:
	bash scripts/import_dashboard.sh

# -------------------------------------------------------------------
# Ollama Model Management
# -------------------------------------------------------------------

install-model:
	@if [ -z "$(MODEL)" ]; then \
		echo "❌ Error: MODEL parameter is required"; \
		echo "Usage: make install-model MODEL=<model_name>"; \
		echo "Examples:"; \
		echo "  make install-model MODEL=llama3.2:1b"; \
		echo "  make install-model MODEL=llama3.2:3b"; \
		echo "  make install-model MODEL=mistral:7b"; \
		echo "  make install-model MODEL=codellama:7b"; \
		echo "  make install-model MODEL=qwen2.5:7b"; \
		echo "Available models: https://ollama.com/library"; \
		exit 1; \
	fi
	@echo "🤖 Installing Ollama model: $(MODEL)"
	@echo "==============================================="
	@if ! $(DC) ps ollama | grep -q "Up"; then \
		echo "⚠️  Ollama service not running, starting..."; \
		$(DC) up -d ollama; \
		echo "⏳ Waiting for Ollama to be ready..."; \
		sleep 10; \
	fi
	@echo "🔍 Checking if model $(MODEL) already exists..."
	@if $(DC) exec ollama ollama list | grep -q "$(MODEL)"; then \
		echo "✅ Model $(MODEL) is already installed"; \
		$(DC) exec ollama ollama list; \
	else \
		echo "📥 Downloading model: $(MODEL)"; \
		echo "⚠️  This may take several minutes depending on model size..."; \
		if $(DC) exec ollama ollama pull "$(MODEL)"; then \
			echo "✅ Model $(MODEL) installed successfully"; \
			echo "📋 Current models:"; \
			$(DC) exec ollama ollama list; \
		else \
			echo "❌ Failed to install model $(MODEL)"; \
			echo "💡 Make sure the model name is correct"; \
			echo "🔗 Available models: https://ollama.com/library"; \
			exit 1; \
		fi; \
	fi
	@echo "🎯 Model $(MODEL) is ready for use"

setup-mcp-model:
	@echo "🤖 Setting up MCP-optimized Ollama model"
	@echo "========================================"
	@echo "This will create a custom model optimized for MCP tool usage"
	@if ! $(DC) ps ollama | grep -q "Up"; then \
		echo "⚠️  Ollama service not running, starting..."; \
		$(DC) up -d ollama; \
		echo "⏳ Waiting for Ollama to be ready..."; \
		sleep 10; \
	fi
	@echo "📥 Installing base model qwen2.5:3b (if not already present)..."
	@$(MAKE) install-model MODEL=qwen2.5:3b
	@echo "🔧 Building custom MCP model..."
	@bash scripts/setup-mcp-model.sh
	@echo "✅ MCP model setup complete!"
	@echo "🎯 You can now use 'privategpt-mcp' model in your applications"

list-models:
	@echo "📋 Available Ollama Models"
	@echo "========================="
	@if ! $(DC) ps ollama | grep -q "Up"; then \
		echo "⚠️  Ollama service not running"; \
		echo "💡 Start with: make start"; \
		exit 1; \
	fi
	@$(DC) exec ollama ollama list || echo "❌ Failed to list models"
	@echo ""
	@echo "💡 Install new models with: make install-model MODEL=<name>"
	@echo "🔗 Browse available models: https://ollama.com/library"

remove-model:
	@if [ -z "$(MODEL)" ]; then \
		echo "❌ Error: MODEL parameter is required"; \
		echo "Usage: make remove-model MODEL=<model_name>"; \
		echo "💡 Use 'make list-models' to see installed models"; \
		exit 1; \
	fi
	@echo "🗑️  Removing Ollama model: $(MODEL)"
	@echo "======================================="
	@if ! $(DC) ps ollama | grep -q "Up"; then \
		echo "⚠️  Ollama service not running"; \
		echo "💡 Start with: make start"; \
		exit 1; \
	fi
	@if $(DC) exec ollama ollama list | grep -q "$(MODEL)"; then \
		echo "🔍 Found model $(MODEL), removing..."; \
		if $(DC) exec ollama ollama rm "$(MODEL)"; then \
			echo "✅ Model $(MODEL) removed successfully"; \
			echo "📋 Remaining models:"; \
			$(DC) exec ollama ollama list; \
		else \
			echo "❌ Failed to remove model $(MODEL)"; \
			exit 1; \
		fi; \
	else \
		echo "⚠️  Model $(MODEL) not found"; \
		echo "📋 Available models:"; \
		$(DC) exec ollama ollama list; \
	fi

# -------------------------------------------------------------------
# Logging targets
# -------------------------------------------------------------------

logs:
	@echo "📋 All service logs (last 100 lines):"
	$(DC) logs --tail=100

logs-follow:
	@echo "📋 Following all service logs:"
	$(DC) logs -f

# Core application services
logs-gateway:
	@echo "📋 Gateway service logs:"
	$(DC) logs --tail=100 gateway-service

logs-rag:
	@echo "📋 RAG service logs:"
	$(DC) logs --tail=100 rag-service

logs-llm:
	@echo "📋 LLM service logs:"
	$(DC) logs --tail=100 llm-service

logs-ui:
	@echo "📋 UI service logs:"
	$(DC) logs --tail=100 nextjs-ui 

logs-mcp:
	@echo "📋 MCP service logs:"
	$(DC) logs --tail=100 mcp-service

logs-celery:
	@echo "📋 Celery worker logs:"
	$(DC) logs --tail=100 celery-worker

# Infrastructure services
logs-db:
	@echo "📋 Database logs:"
	$(DC) logs --tail=100 db

logs-redis:
	@echo "📋 Redis logs:"
	$(DC) logs --tail=100 redis

logs-weaviate:
	@echo "📋 Weaviate logs:"
	$(DC) logs --tail=100 weaviate

logs-ollama:
	@echo "📋 Ollama logs:"
	$(DC) logs --tail=100 ollama

# Authentication services
logs-keycloak:
	@echo "📋 Keycloak logs:"
	$(DC) logs --tail=100 keycloak

logs-keycloak-db:
	@echo "📋 Keycloak database logs:"
	$(DC) logs --tail=100 keycloak-db

logs-keycloak-setup:
	@echo "📋 Keycloak setup logs:"
	$(DC) logs keycloak-setup

# Observability services
logs-elasticsearch:
	@echo "📋 Elasticsearch logs:"
	$(DC) logs --tail=100 elasticsearch

logs-kibana:
	@echo "📋 Kibana logs:"
	$(DC) logs --tail=100 kibana

logs-filebeat:
	@echo "📋 Filebeat logs:"
	$(DC) logs --tail=100 filebeat

logs-traefik:
	@echo "📋 Traefik logs:"
	$(DC) logs --tail=100 traefik

logs-n8n:
	@echo "📋 n8n logs:"
	$(DC) logs --tail=100 n8n

# Setup and test services
logs-tests:
	@echo "📋 Tests logs:"
	$(DC) logs tests

# Convenience aliases
logs-auth: logs-keycloak
logs-vector: logs-weaviate
logs-database: logs-db

# -------------------------------------------------------------------
# Troubleshooting targets
# -------------------------------------------------------------------

diagnose:
	@echo "🔍 Docker System Diagnosis"
	@echo "=========================="
	@echo "Docker version:"
	@docker --version
	@echo ""
	@echo "Docker Compose version:"
	@docker-compose --version
	@echo ""
	@echo "Docker system info:"
	@docker system df
	@echo ""
	@echo "Running containers:"
	@docker ps
	@echo ""
	@echo "Docker networks:"
	@docker network ls
	@echo ""
	@echo "Docker volumes:"
	@docker volume ls
	@echo ""
	@echo "Compose project status:"
	@$(DC) ps

# Check disk usage and image count
disk-usage:
	@echo "💾 Docker Disk Usage Report"
	@echo "==========================="
	@docker system df
	@echo ""
	@echo "📊 PrivateGPT Images:"
	@docker images | grep -E "privategpt|REPOSITORY" | head -20
	@echo ""
	@echo "🗑️  Dangling Images:"
	@docker images -f "dangling=true" | head -10
	@echo ""
	@echo "💡 Tips:"
	@echo "- Run 'make clean' to remove containers and dangling images"
	@echo "- Run 'make clean-deep' to remove ALL project images"
	@echo "- Run 'docker system prune -a' to clean everything (careful!)"

nuke:
	@echo "💥 NUCLEAR OPTION: Delete EVERYTHING"
	@echo "This will remove:"
	@echo "- ALL containers (running and stopped)"
	@echo "- ALL images (including base images)"
	@echo "- ALL volumes (including Ollama models)"
	@echo "- ALL networks"
	@echo "- ALL build cache"
	@echo ""
	@echo "⚠️  WARNING: This includes your downloaded Ollama models!"
	@read -p "Are you absolutely sure? Type 'NUKE' to confirm: " confirm; \
	if [ "$$confirm" = "NUKE" ]; then \
		echo "💀 Nuking everything..."; \
		$(DC) down -v --remove-orphans || true; \
		docker stop $$(docker ps -aq) 2>/dev/null || true; \
		docker rm $$(docker ps -aq) 2>/dev/null || true; \
		docker rmi $$(docker images -q) 2>/dev/null || true; \
		docker volume prune -f; \
		docker network prune -f; \
		docker system prune -af; \
		echo "💀 Nuclear destruction complete"; \
	else \
		echo "❌ Cancelled (you must type exactly 'NUKE')"; \
	fi

hard-build:
	@echo "🔨 Hard build: Nuke + rebuild from scratch"
	$(MAKE) nuke
	@echo "🏗️  Starting fresh build..."
	$(MAKE) build

# Next.js UI Development Commands
build-ui:
	@echo "🔨 Building Next.js UI..."
	$(DC) build nextjs-ui

dev-ui:
	@echo "🚀 Starting UI development environment..."
	$(DC) up --build nextjs-ui gateway-service llm-service db redis keycloak

restart-ui:
	@echo "🔄 Restarting Next.js UI service..."
	$(DC) restart nextjs-ui

start-ui-only:
	@echo "🖥️  Starting just the UI service..."
	$(DC) up -d nextjs-ui

stop-ui:
	@echo "⏹️  Stopping UI service..."
	$(DC) stop nextjs-ui

rebuild-ui:
	@echo "🔄 Rebuilding UI from scratch..."
	$(DC) build --no-cache nextjs-ui
	$(DC) up -d nextjs-ui

start-with-nextjs:
	@echo "🚀 Starting system with Next.js UI..."
	$(DC) up -d db keycloak-db keycloak redis ollama gateway-service llm-service rag-service nextjs-ui

logs-nextjs:
	@echo "📋 Next.js UI logs:"
	$(DC) logs -f nextjs-ui

ui-shell:
	@echo "🐚 Opening shell in UI container..."
	$(DC) exec nextjs-ui sh

ui-install:
	@echo "📦 Installing UI dependencies..."
	$(DC) exec nextjs-ui npm install

ui-clean:
	@echo "🧹 Cleaning UI node_modules and .next..."
	$(DC) exec nextjs-ui rm -rf node_modules .next
	$(DC) exec nextjs-ui npm install