#!/bin/bash

# Health check script for deployed Lambda functions
# Usage: ./scripts/health-check.sh [environment]

set -e

ENVIRONMENT=${1:-"staging"}
AWS_REGION=${AWS_REGION:-"us-east-1"}

print_info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
print_success() { echo -e "\033[0;32m[SUCCESS]\033[0m $1"; }
print_error() { echo -e "\033[0;31m[ERROR]\033[0m $1"; }

print_info "Checking health of $ENVIRONMENT environment..."

STACK_NAME="colino-backend-$ENVIRONMENT"

# Check if stack exists
if ! aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
    print_error "Stack $STACK_NAME not found in region $AWS_REGION"
    exit 1
fi

print_success "Stack $STACK_NAME exists"

# Get stack outputs
OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs' \
    --output json)

AUTH_INITIATE_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="AuthInitiateApi") | .OutputValue')
AUTH_CALLBACK_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="AuthCallbackApi") | .OutputValue')

if [ "$AUTH_INITIATE_URL" = "null" ] || [ -z "$AUTH_INITIATE_URL" ]; then
    print_error "Could not get AuthInitiateApi URL from stack outputs"
    exit 1
fi

if [ "$AUTH_CALLBACK_URL" = "null" ] || [ -z "$AUTH_CALLBACK_URL" ]; then
    print_error "Could not get AuthCallbackApi URL from stack outputs"
    exit 1
fi

print_info "Testing Auth Initiate endpoint..."
RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/response "$AUTH_INITIATE_URL")

if [ "$RESPONSE" = "200" ]; then
    print_success "Auth Initiate endpoint is healthy"
    if grep -q "authorization_url" /tmp/response; then
        print_success "Response contains expected authorization_url field"
    else
        print_error "Response does not contain expected authorization_url field"
        cat /tmp/response
    fi
else
    print_error "Auth Initiate endpoint returned HTTP $RESPONSE"
    cat /tmp/response
    exit 1
fi

print_info "Testing Auth Callback endpoint (without code - should return 400)..."
CALLBACK_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/callback_response "$AUTH_CALLBACK_URL")

if [ "$CALLBACK_RESPONSE" = "400" ]; then
    print_success "Auth Callback endpoint correctly rejects requests without code"
else
    print_error "Auth Callback endpoint returned unexpected HTTP $CALLBACK_RESPONSE"
    cat /tmp/callback_response
fi

# Check Lambda function logs for errors
print_info "Checking recent Lambda function logs for errors..."

INITIATE_FUNCTION_NAME="colino-backend-$ENVIRONMENT-AuthInitiateFunction"
CALLBACK_FUNCTION_NAME="colino-backend-$ENVIRONMENT-AuthCallbackFunction"

# Check for recent errors in logs (last 5 minutes)
START_TIME=$(date -u -d '5 minutes ago' '+%Y-%m-%dT%H:%M:%S')

INITIATE_ERRORS=$(aws logs filter-log-events \
    --log-group-name "/aws/lambda/$INITIATE_FUNCTION_NAME" \
    --start-time "$(date -d "$START_TIME" +%s)000" \
    --filter-pattern "ERROR" \
    --query 'events[].message' \
    --output text 2>/dev/null || echo "")

CALLBACK_ERRORS=$(aws logs filter-log-events \
    --log-group-name "/aws/lambda/$CALLBACK_FUNCTION_NAME" \
    --start-time "$(date -d "$START_TIME" +%s)000" \
    --filter-pattern "ERROR" \
    --query 'events[].message' \
    --output text 2>/dev/null || echo "")

if [ -n "$INITIATE_ERRORS" ]; then
    print_error "Recent errors found in Auth Initiate function logs:"
    echo "$INITIATE_ERRORS"
else
    print_success "No recent errors in Auth Initiate function logs"
fi

if [ -n "$CALLBACK_ERRORS" ]; then
    print_error "Recent errors found in Auth Callback function logs:"
    echo "$CALLBACK_ERRORS"
else
    print_success "No recent errors in Auth Callback function logs"
fi

print_info "Environment URLs:"
echo "  Auth Initiate: $AUTH_INITIATE_URL"
echo "  Auth Callback: $AUTH_CALLBACK_URL"

print_success "Health check completed for $ENVIRONMENT environment"

# Cleanup
rm -f /tmp/response /tmp/callback_response
