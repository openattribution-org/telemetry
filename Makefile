.DEFAULT_GOAL := help

.PHONY: help test test-client test-server lint fmt dev-server migrate ci

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

test: test-client test-server ## Run all tests

test-client: ## Run SDK client tests
	python -m pytest tests/ -v

test-server: ## Run server tests
	cd server && python -m pytest tests/ -v

lint: ## Lint both packages with ruff
	ruff check src/ tests/ server/src/ server/tests/

fmt: ## Format both packages with ruff
	ruff format src/ tests/ server/src/ server/tests/
	ruff check --fix src/ tests/ server/src/ server/tests/

dev-server: ## Run server with auto-reload
	cd server && uvicorn openattribution.telemetry_server:app --reload --port 8007

migrate: ## Apply SQL migrations to $$DATABASE_URL
	psql "$(DATABASE_URL)" -f server/migrations/001_telemetry_schema.sql

ci: lint test ## Run lint + test (CI pipeline)
