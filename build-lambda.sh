#!/bin/bash
set -e

echo "🏗️  Building Lambda package with Poetry..."

# Clean up previous builds
rm -rf dist package .aws-sam

# Install dependencies with Poetry (production only)
echo "📦 Installing production dependencies..."
poetry install --only main --sync

# Build the wheel
echo "🔧 Building wheel..."
poetry build

# Create package directory
mkdir -p package

# Install the wheel and dependencies into package directory
echo "📦 Installing dependencies to package directory..."
poetry run pip install --upgrade -t package dist/*.whl

# Copy source code to package directory
echo "📁 Copying source code..."
cp -r src/* package/

# Create the deployment package
echo "📦 Creating deployment package..."
cd package
mkdir -p out
zip -r -q out/lambda.zip . -x '*.pyc' '__pycache__/*' '*.dist-info/*'

echo "✅ Lambda package built successfully: package/out/lambda.zip"

# Move back to root
cd ..

echo "🚀 Ready for deployment!"
