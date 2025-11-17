.PHONY: help install test lint format deploy clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	poetry install

test: ## Run tests
	PYTHONPATH=src poetry run pytest tests/ -v

lint: ## Run linting
	poetry run ruff check src/ tests/
	poetry run mypy src/

lint-fix: ## Run linting with auto-fix
	poetry run ruff check --fix --unsafe-fixes src/ tests/
	poetry run mypy src/

format: ## Format code
	poetry run ruff format src/ tests/

validate-template: ## Validate SAM template
	sam validate --template template.yaml

build: ## Build SAM application
	sam build --template template.yaml

deploy-prod: build ## Deploy to production with custom domain
	sam deploy \
		--parameter-overrides \
			Stage=Prod \
			CustomDomainName=colino.umberto.xyz

deploy: ## Deploy to AWS (uses deploy.sh script)
	./deploy.sh

deploy-guided: build ## Deploy with guided prompts (first time setup)
	sam deploy --guided

local-api: build ## Start local API for testing
	sam local start-api --port 3001

invoke-initiate: ## Test auth initiate function locally
	sam local invoke AuthInitiateFunction --event events/auth-initiate.json

invoke-callback: ## Test auth callback function locally
	sam local invoke AuthCallbackFunction --event events/auth-callback.json

clean: ## Clean build artifacts
	rm -rf .aws-sam/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

create-events: ## Create sample event files for testing
	mkdir -p events
	echo '{"httpMethod":"GET","path":"/auth/initiate","headers":{},"queryStringParameters":null}' > events/auth-initiate.json
	echo '{"httpMethod":"GET","path":"/auth/callback","headers":{},"queryStringParameters":{"code":"test-code","state":"test-state"}}' > events/auth-callback.json

# CI targets (for local testing)
ci-test: ## Run CI tests locally  
	PYTHONPATH=src poetry run pytest tests/ -v --cov=src --cov-report=term-missing
	poetry run ruff check src/ tests/
	poetry run ruff format --check src/ tests/
	poetry run mypy src/ --ignore-missing-imports

ci-security: ## Run security scans locally
	poetry add --group dev bandit safety
	poetry run bandit -r src/ -ll
	poetry run safety check

# Cleanup
clean-all: clean ## Clean everything including caches
	poetry cache clear pypi --all
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf coverage.xml
