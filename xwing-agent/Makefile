.PHONY: help install dev setup env app run test lint format clean

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip

env: $(VENV)/bin/activate ## Create virtual environment

install: env ## Install dependencies
	$(PIP) install -e .

dev: env ## Install with dev dependencies
	$(PIP) install -e ".[dev]"

setup: dev ## Full setup (env + deps + .env file)
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file - please add your ANTHROPIC_API_KEY"; \
	fi

app: install ## Run the application (port 33293)
	$(PYTHON) scripts/run_dev.py

run: app ## Alias for 'make app'

test: dev ## Run tests
	$(VENV)/bin/pytest tests/ -v

lint: dev ## Run linter
	$(VENV)/bin/ruff check src/ tests/

format: dev ## Format code
	$(VENV)/bin/ruff check --fix src/ tests/
	$(VENV)/bin/ruff format src/ tests/

index-rules: install ## Build rules vector index
	$(PYTHON) scripts/index_rules.py

clean: ## Remove virtual environment and cache
	rm -rf $(VENV)
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
