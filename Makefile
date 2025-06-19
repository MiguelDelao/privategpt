.PHONY: help start stop build build-base clean clean-all test test-unit test-api stack-logs import-dashboard status ensure-dashboard install-model list-models remove-model

# Default docker compose file inside v2
DC = docker-compose -f docker-compose.yml

help:
	@echo "PrivateGPT v2 Makefile"
	@echo "======================"
	@echo "make start   - Start all v2 containers"
	@echo "make stop    - Stop all v2 containers"
	@echo "make build   - Build images and start containers"
	@echo "make build-base - Build (or rebuild) the common base image"
	@echo "make clean   - Remove containers (preserves Ollama models)"
	@echo "make clean-all - Remove containers and ALL volumes (including models)"
	@echo "make test    - Run unit + integration tests inside host environment"
	@echo "make test-unit - Run unit tests"
	@echo "make test-api - Run API tests"
	@echo "make stack-logs - Start Elasticsearch, Kibana, and Filebeat"
	@echo "make import-dashboard - Import a Kibana dashboard"
	@echo "make status - Show the status of all containers"
	@echo "make ensure-dashboard - Import dashboard and verify"
	@echo ""
	@echo "Model Management:"
	@echo "make install-model MODEL=<name> - Install specific Ollama model"
	@echo "make list-models - Show available Ollama models"
	@echo "make remove-model MODEL=<name> - Remove specific Ollama model"

start:
	$(DC) up -d

stop:
	$(DC) down

build-base:
	docker build -f docker/base/Dockerfile -t privategpt-base .

build: build-base
	$(DC) up -d --build
	@echo "Setting up Keycloak realm and users..."
	$(DC) up --no-deps keycloak-setup
	@echo "Setting up Ollama models..."
	$(DC) up --no-deps ollama-setup
	@echo "✅ Build complete! UI available at http://localhost:8501"
	@echo "🔐 Login with: admin@admin.com / admin"
	@echo "🔑 Keycloak admin: http://localhost:8180"
	@echo "🤖 LLM service: http://localhost:8003"

clean:
	$(DC) down
	docker container prune -f
	# Note: Preserving ollama_data volume to keep downloaded models
	# Use 'make clean-all' to remove all volumes including models

clean-all:
	$(DC) down -v
	docker container prune -f
	docker volume prune -f



# Run pytest; assumes editable install (pip install -e .)
# Developers may also run `

## ADD TEST TARGETS ##

test:
	docker compose run --rm tests


test-unit:
	pytest -q tests/unit


test-api:
	docker compose run --rm tests

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