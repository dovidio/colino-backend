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
	poetry run flake8 src/ tests/
	poetry run mypy src/

format: ## Format code
	poetry run black src/ tests/

validate-template: ## Validate SAM template
	sam validate --template template.yaml

build: ## Build SAM application
	sam build --template template.yaml

deploy: build ## Deploy to AWS
	sam deploy --guided

deploy-prod: build ## Deploy to production
	sam deploy --config-env production

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
	echo '{"httpMethod":"GET","path":"/callback","headers":{},"queryStringParameters":{"code":"sample_code","state":"sample_state"}}' > events/auth-callback.json

setup-dev: install create-events ## Set up development environment
	@echo "Development environment setup complete!"
	@echo "1. Copy .env.example to .env and fill in your values"
	@echo "2. Set up Google OAuth credentials"
	@echo "3. Run 'make local-api' to test locally"

# CI/CD targets
ci-test: ## Run CI tests locally
	PYTHONPATH=src poetry run pytest tests/ -v --cov=src --cov-report=term-missing
	poetry run flake8 src/ tests/ --max-line-length=88 --extend-ignore=E203,W503
	poetry run black --check src/ tests/
	poetry run mypy src/ --ignore-missing-imports

ci-security: ## Run security scans locally
	poetry add --group dev bandit safety
	poetry run bandit -r src/ -ll
	poetry run safety check

deploy-dev: ## Deploy to development environment
	./scripts/deploy.sh dev

deploy-staging: ## Deploy to staging environment
	./scripts/deploy.sh staging

deploy-production: ## Deploy to production environment
	./scripts/deploy.sh production

deploy-force: ## Force deploy without tests (use with caution)
	./scripts/deploy.sh $(ENV) --force

create-s3-bucket: ## Create S3 bucket for SAM deployments
	@read -p "Enter S3 bucket name: " bucket_name; \
	aws s3 mb s3://$$bucket_name --region $(AWS_REGION) && \
	aws s3api put-bucket-versioning --bucket $$bucket_name --versioning-configuration Status=Enabled

setup-github-secrets: ## Show instructions for setting up GitHub secrets
	@echo "Set up the following secrets in your GitHub repository:"
	@echo ""
	@echo "AWS Credentials:"
	@echo "  AWS_ACCESS_KEY_ID"
	@echo "  AWS_SECRET_ACCESS_KEY"
	@echo ""
	@echo "SAM Deployment:"
	@echo "  SAM_S3_BUCKET"
	@echo ""
	@echo "Google OAuth (Staging):"
	@echo "  GOOGLE_CLIENT_ID_STAGING"
	@echo "  GOOGLE_CLIENT_SECRET_STAGING"
	@echo "  ALLOWED_ORIGINS_STAGING"
	@echo ""
	@echo "Google OAuth (Production):"
	@echo "  GOOGLE_CLIENT_ID_PRODUCTION"
	@echo "  GOOGLE_CLIENT_SECRET_PRODUCTION"
	@echo "  ALLOWED_ORIGINS_PRODUCTION"
	@echo ""
	@echo "Go to: https://github.com/YOUR_USERNAME/YOUR_REPO/settings/secrets/actions"

check-env: ## Check if required environment variables are set
	@echo "Checking environment variables..."
	@[ -n "$$SAM_S3_BUCKET" ] && echo "✓ SAM_S3_BUCKET is set" || echo "✗ SAM_S3_BUCKET is not set"
	@[ -n "$$GOOGLE_CLIENT_ID" ] && echo "✓ GOOGLE_CLIENT_ID is set" || echo "✗ GOOGLE_CLIENT_ID is not set"
	@[ -n "$$GOOGLE_CLIENT_SECRET" ] && echo "✓ GOOGLE_CLIENT_SECRET is set" || echo "✗ GOOGLE_CLIENT_SECRET is not set"
	@[ -n "$$AWS_REGION" ] && echo "✓ AWS_REGION is set to $$AWS_REGION" || echo "ℹ AWS_REGION not set (will use us-east-1)"

logs-staging: ## View CloudWatch logs for staging functions
	@echo "Auth Initiate Function logs:"
	aws logs tail /aws/lambda/colino-backend-staging-AuthInitiateFunction --follow
	@echo "Auth Callback Function logs:"
	aws logs tail /aws/lambda/colino-backend-staging-AuthCallbackFunction --follow

logs-production: ## View CloudWatch logs for production functions
	@echo "Auth Initiate Function logs:"
	aws logs tail /aws/lambda/colino-backend-production-AuthInitiateFunction --follow
	@echo "Auth Callback Function logs:"
	aws logs tail /aws/lambda/colino-backend-production-AuthCallbackFunction --follow

health-check-staging: ## Run health check for staging environment
	./scripts/health-check.sh staging

health-check-production: ## Run health check for production environment
	./scripts/health-check.sh production

# Git workflow helpers
create-feature: ## Create a new feature branch
	@read -p "Enter feature name: " feature_name; \
	git checkout develop && git pull && git checkout -b feature/$$feature_name

create-release: ## Create a release branch from develop
	@read -p "Enter version number (e.g., 1.0.0): " version; \
	git checkout develop && git pull && git checkout -b release/v$$version

# Documentation
docs-serve: ## Serve documentation locally (if using mkdocs)
	@command -v mkdocs >/dev/null 2>&1 && mkdocs serve || echo "Install mkdocs to serve documentation"

# Cleanup
clean-all: clean ## Clean everything including caches
	poetry cache clear pypi --all
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf coverage.xml
