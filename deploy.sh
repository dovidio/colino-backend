#!/bin/bash
set -e

# Simple deployment script for colino-backend
echo "🚀 Deploying Colino Backend to AWS..."

# Check required environment variables
if [ -z "$SAM_S3_BUCKET" ]; then
    echo "❌ Error: SAM_S3_BUCKET environment variable is required"
    echo "   Set it with: export SAM_S3_BUCKET=your-bucket-name"
    exit 1
fi

if [ -z "$GOOGLE_CLIENT_ID" ]; then
    echo "❌ Error: GOOGLE_CLIENT_ID environment variable is required"
    echo "   Get it from: https://console.cloud.google.com/apis/credentials"
    exit 1
fi

if [ -z "$GOOGLE_CLIENT_SECRET" ]; then
    echo "❌ Error: GOOGLE_CLIENT_SECRET environment variable is required"
    echo "   Get it from: https://console.cloud.google.com/apis/credentials"
    exit 1
fi

# Set defaults
AWS_REGION=${AWS_REGION:-us-east-1}
ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-"*"}

echo "📋 Deployment Configuration:"
echo "   Bucket: $SAM_S3_BUCKET"
echo "   Region: $AWS_REGION"
echo "   Client ID: ${GOOGLE_CLIENT_ID:0:20}..."
echo "   Allowed Origins: $ALLOWED_ORIGINS"
echo ""

# Create S3 bucket if it doesn't exist
echo "📦 Ensuring S3 bucket exists..."
if ! aws s3 ls "s3://$SAM_S3_BUCKET" 2>/dev/null; then
    echo "   Creating S3 bucket: $SAM_S3_BUCKET"
    aws s3 mb "s3://$SAM_S3_BUCKET" --region "$AWS_REGION"
else
    echo "   S3 bucket already exists: $SAM_S3_BUCKET"
fi

# Build and deploy
echo "🔨 Building Lambda package with Poetry..."
./build-lambda.sh

echo "🚢 Deploying to AWS..."
sam deploy \
    --s3-bucket "$SAM_S3_BUCKET" \
    --region "$AWS_REGION" \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
        "GoogleClientId=$GOOGLE_CLIENT_ID" \
        "GoogleClientSecret=$GOOGLE_CLIENT_SECRET" \
        "AllowedOrigins=$ALLOWED_ORIGINS" \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Your OAuth Endpoints:"
aws cloudformation describe-stacks \
    --stack-name colino-backend \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`AuthInitiateApi`].OutputValue' \
    --output text | sed 's/^/   Initiate: /'

aws cloudformation describe-stacks \
    --stack-name colino-backend \
    --region "$AWS_REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`AuthCallbackApi`].OutputValue' \
    --output text | sed 's/^/   Callback: /'

echo ""
echo "🔧 Next Steps:"
echo "1. Copy the Callback URL above"
echo "2. Go to Google Cloud Console → Credentials"
echo "3. Edit your OAuth 2.0 Client ID"
echo "4. Add the Callback URL to 'Authorized redirect URIs'"
echo "5. Save the changes"
echo ""
echo "🎉 Your OAuth proxy is ready to use!"
