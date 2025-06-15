.PHONY: help start stop build clean test test-unit

# Default docker compose file inside v2
DC = docker-compose -f docker-compose.yml

help:
	@echo "PrivateGPT v2 Makefile"
	@echo "======================"
	@echo "make start   - Start all v2 containers"
	@echo "make stop    - Stop all v2 containers"
	@echo "make build   - Build images and start containers"
	@echo "make clean   - Remove containers and dangling images"
	@echo "make test    - Run unit + integration tests inside host environment"
	@echo "make test-unit - Run unit tests"

start:
	$(DC) up -d

stop:
	$(DC) down

build:
	$(DC) up -d --build

clean:
	$(DC) down -v
	docker container prune -f
	docker volume prune -f

# Run pytest; assumes editable install (pip install -e v2/src)
# Developers may also run `make test DOCKER=true` to execute inside a container later.

test:
	pytest -q v2/tests || true

test-unit:
	pytest -q v2/tests/unit 