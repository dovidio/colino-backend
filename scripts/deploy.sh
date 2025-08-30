#!/bin/bash

# Deployment script for AWS Lambda functions
# Usage: ./scripts/deploy.sh [environment] [options]

set -e

# Default values
ENVIRONMENT="dev"
FORCE_DEPLOY=false
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Function to show usage
show_usage() {
    echo "Usage: $0 [environment] [options]"
    echo ""
    echo "Environments:"
    echo "  dev         Deploy to development (default)"
    echo "  staging     Deploy to staging"
    echo "  production  Deploy to production"
    echo ""
    echo "Options:"
    echo "  --force     Force deployment without running tests"
    echo "  --verbose   Enable verbose output"
    echo "  --help      Show this help message"
    echo ""
    echo "Required Environment Variables:"
    echo "  SAM_S3_BUCKET                S3 bucket for SAM deployments"
    echo "  GOOGLE_CLIENT_ID             Google OAuth Client ID"
    echo "  GOOGLE_CLIENT_SECRET         Google OAuth Client Secret"
    echo ""
    echo "Optional Environment Variables:"
    echo "  ALLOWED_ORIGINS              Comma-separated allowed CORS origins"
    echo "  AWS_REGION                   AWS region (default: us-east-1)"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        dev|staging|production)
            ENVIRONMENT="$1"
            shift
            ;;
        --force)
            FORCE_DEPLOY=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Set verbose mode
if [ "$VERBOSE" = true ]; then
    set -x
fi

print_info "Starting deployment to $ENVIRONMENT environment..."

# Check required tools
if ! command -v sam &> /dev/null; then
    print_error "AWS SAM CLI not found. Please install it first."
    exit 1
fi

if ! command -v poetry &> /dev/null; then
    print_error "Poetry not found. Please install it first."
    exit 1
fi

# Check required environment variables
if [ -z "$SAM_S3_BUCKET" ]; then
    print_error "SAM_S3_BUCKET environment variable is required"
    exit 1
fi

if [ -z "$GOOGLE_CLIENT_ID" ]; then
    print_error "GOOGLE_CLIENT_ID environment variable is required"
    exit 1
fi

if [ -z "$GOOGLE_CLIENT_SECRET" ]; then
    print_error "GOOGLE_CLIENT_SECRET environment variable is required"
    exit 1
fi

# Set default values for optional variables
AWS_REGION=${AWS_REGION:-"us-east-1"}
ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-"http://localhost:3000"}

# Run tests unless force deploy is enabled
if [ "$FORCE_DEPLOY" != true ]; then
    print_info "Running tests..."
    if ! poetry run pytest tests/ -v; then
        print_error "Tests failed. Use --force to deploy anyway."
        exit 1
    fi
    print_success "Tests passed!"
fi

# Install dependencies
print_info "Installing dependencies..."
poetry install --only=main

# Validate SAM template
print_info "Validating SAM template..."
if ! sam validate --template template.yaml; then
    print_error "SAM template validation failed"
    exit 1
fi
print_success "SAM template is valid!"

# Build SAM application
print_info "Building SAM application..."
if ! sam build --template template.yaml; then
    print_error "SAM build failed"
    exit 1
fi
print_success "SAM build completed!"

# Deploy to AWS
print_info "Deploying to AWS ($ENVIRONMENT)..."

STACK_NAME="colino-backend-$ENVIRONMENT"

sam deploy \
    --stack-name "$STACK_NAME" \
    --s3-bucket "$SAM_S3_BUCKET" \
    --s3-prefix "$ENVIRONMENT" \
    --region "$AWS_REGION" \
    --capabilities CAPABILITY_IAM \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset \
    --parameter-overrides \
        GoogleClientId="$GOOGLE_CLIENT_ID" \
        GoogleClientSecret="$GOOGLE_CLIENT_SECRET" \
        AllowedOrigins="$ALLOWED_ORIGINS"

if [ $? -eq 0 ]; then
    print_success "Deployment to $ENVIRONMENT completed successfully!"
    
    # Get stack outputs
    print_info "Getting stack outputs..."
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$AWS_REGION" \
        --query 'Stacks[0].Outputs' \
        --output table
else
    print_error "Deployment failed!"
    exit 1
fi

print_success "All done! 🚀"
