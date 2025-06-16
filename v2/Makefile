.PHONY: help start stop build build-base clean test test-unit test-api

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

start:
	$(DC) up -d

stop:
	$(DC) down

build-base:
	docker build -t privategpt/base:latest -f docker/base/Dockerfile ..

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