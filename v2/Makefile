.PHONY: help start stop build build-base clean test test-unit test-api stack-logs import-dashboard status ensure-dashboard

# Default docker compose file inside v2
DC = docker-compose -f docker-compose.yml

help:
	@echo "PrivateGPT v2 Makefile"
	@echo "======================"
	@echo "make start   - Start all v2 containers"
	@echo "make stop    - Stop all v2 containers"
	@echo "make build   - Build images and start containers"
	@echo "make build-base - Build (or rebuild) the common base image"
	@echo "make clean   - Remove containers and dangling images"
	@echo "make test    - Run unit + integration tests inside host environment"
	@echo "make test-unit - Run unit tests"
	@echo "make test-api - Run API tests"
	@echo "make stack-logs - Start Elasticsearch, Kibana, and Filebeat"
	@echo "make import-dashboard - Import a Kibana dashboard"
	@echo "make status - Show the status of all containers"
	@echo "make ensure-dashboard - Import dashboard and verify"

start:
	$(DC) up -d

stop:
	$(DC) down

build-base:
	docker build -f docker/base/Dockerfile -t privategpt-base .

build: build-base
	$(DC) up -d --build

clean:
	$(DC) down -v
	docker container prune -f
	docker volume prune -f

# Run pytest; assumes editable install (pip install -e v2/src)
# Developers may also run `

## ADD TEST TARGETS ##

test:
	docker compose run --rm tests


test-unit:
	pytest -q v2/tests/unit


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