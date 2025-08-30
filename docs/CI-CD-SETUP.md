# CI/CD Setup Guide

This guide will help you set up the complete CI/CD pipeline for deploying your AWS Lambda functions using GitHub Actions.

## 🚀 Quick Setup

1. **Fork/Clone the repository**
2. **Set up AWS credentials**
3. **Configure GitHub secrets**
4. **Create S3 bucket for deployments**
5. **Push to trigger deployment**

## 📋 Prerequisites

- AWS Account with appropriate permissions
- GitHub repository
- Google Cloud Console project with YouTube API enabled
- AWS CLI installed locally (for setup)

## 🔧 AWS Setup

### 1. Create IAM User for GitHub Actions

Create an IAM user with the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudformation:*",
                "lambda:*",
                "apigateway:*",
                "iam:*",
                "dynamodb:*",
                "s3:*"
            ],
            "Resource": "*"
        }
    ]
}
```

**Note**: For production, use more restrictive permissions following the principle of least privilege.

### 2. Create S3 Bucket for SAM Deployments

```bash
# Replace 'your-sam-deployment-bucket' with a unique bucket name
export SAM_S3_BUCKET="your-sam-deployment-bucket"
aws s3 mb s3://$SAM_S3_BUCKET --region us-east-1
aws s3api put-bucket-versioning --bucket $SAM_S3_BUCKET --versioning-configuration Status=Enabled
```

Or use the Makefile:
```bash
make create-s3-bucket
```

## 🔐 GitHub Secrets Configuration

Go to your repository settings: `https://github.com/YOUR_USERNAME/YOUR_REPO/settings/secrets/actions`

### Required Secrets

#### AWS Credentials
- `AWS_ACCESS_KEY_ID`: Your AWS access key ID
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret access key

#### SAM Deployment
- `SAM_S3_BUCKET`: S3 bucket name for SAM deployments

#### Google OAuth - Staging Environment
- `GOOGLE_CLIENT_ID_STAGING`: Google OAuth client ID for staging
- `GOOGLE_CLIENT_SECRET_STAGING`: Google OAuth client secret for staging
- `ALLOWED_ORIGINS_STAGING`: Comma-separated CORS origins (e.g., `https://staging.yourapp.com`)

#### Google OAuth - Production Environment
- `GOOGLE_CLIENT_ID_PRODUCTION`: Google OAuth client ID for production
- `GOOGLE_CLIENT_SECRET_PRODUCTION`: Google OAuth client secret for production
- `ALLOWED_ORIGINS_PRODUCTION`: Comma-separated CORS origins (e.g., `https://yourapp.com`)

### Quick Setup Command
```bash
make setup-github-secrets
```

## 🌟 Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **YouTube Data API v3**
4. Create **OAuth 2.0 credentials**:
   - Application type: Web application
   - Authorized redirect URIs:
     - `https://your-staging-api.execute-api.us-east-1.amazonaws.com/Prod/callback`
     - `https://your-production-api.execute-api.us-east-1.amazonaws.com/Prod/callback`

## 🔄 CI/CD Workflows

### 1. Main CI/CD Pipeline (`.github/workflows/ci-cd.yml`)

**Triggers:**
- Push to `main` → Deploy to production
- Push to `develop` → Deploy to staging
- Pull requests → Run tests and security scans

**Jobs:**
- **Test**: Run pytest, linting, type checking
- **Security**: Bandit security scan, safety dependency check
- **Build**: Build SAM application
- **Deploy Staging**: Deploy to staging environment (develop branch)
- **Deploy Production**: Deploy to production environment (main branch)

### 2. Pull Request Checks (`.github/workflows/pr-checks.yml`)

**Triggers:**
- Pull requests to `main` or `develop`

**Jobs:**
- **Change Detection**: Detect which files changed
- **Lint and Test**: Run tests only if source/test files changed
- **Security Scan**: Security checks for source changes
- **SAM Validation**: Validate template for infrastructure changes
- **PR Summary**: Generate summary comment

### 3. Manual Deployment (`.github/workflows/manual-deploy.yml`)

**Triggers:**
- Manual workflow dispatch

**Features:**
- Choose environment (staging/production)
- Option to force deploy (skip tests)
- Interactive deployment control

## 🛠 Local Development

### Environment Setup
```bash
# Install dependencies
make install

# Set up development environment
make setup-dev

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your values
```

### Testing
```bash
# Run all tests
make test

# Run CI tests locally
make ci-test

# Run security scans
make ci-security

# Check environment variables
make check-env
```

### Local Deployment
```bash
# Deploy to development
make deploy-dev

# Deploy to staging
make deploy-staging

# Deploy to production (be careful!)
make deploy-production

# Force deploy without tests (use with caution)
ENV=staging make deploy-force
```

### Local SAM Testing
```bash
# Build and start local API
make local-api

# Test individual functions
make invoke-initiate
make invoke-callback
```

## 📊 Monitoring and Logs

### View CloudWatch Logs
```bash
# Staging logs
make logs-staging

# Production logs
make logs-production
```

### Manual Log Access
```bash
# Staging
aws logs tail /aws/lambda/colino-backend-staging-AuthInitiateFunction --follow
aws logs tail /aws/lambda/colino-backend-staging-AuthCallbackFunction --follow

# Production
aws logs tail /aws/lambda/colino-backend-production-AuthInitiateFunction --follow
aws logs tail /aws/lambda/colino-backend-production-AuthCallbackFunction --follow
```

## 🔒 Security Best Practices

1. **Use least privilege IAM policies**
2. **Rotate AWS credentials regularly**
3. **Store sensitive data in AWS Secrets Manager** (consider upgrading from environment variables)
4. **Enable CloudTrail for audit logging**
5. **Use VPC endpoints for private subnet deployments**
6. **Enable Lambda function monitoring and alerting**

## 🌍 Environment Configuration

### Development
- Stack: `colino-backend-dev`
- Purpose: Local development and testing
- Secrets: Use `.env` file

### Staging
- Stack: `colino-backend-staging`
- Purpose: Pre-production testing
- Secrets: GitHub repository secrets with `_STAGING` suffix
- Deployment: Automatic on push to `develop` branch

### Production
- Stack: `colino-backend-production`
- Purpose: Live production environment
- Secrets: GitHub repository secrets with `_PRODUCTION` suffix
- Deployment: Automatic on push to `main` branch

## 🚨 Troubleshooting

### Common Issues

1. **Deployment fails with S3 bucket error**
   - Ensure bucket exists and is accessible
   - Check bucket region matches AWS_REGION

2. **Lambda function timeout**
   - Increase timeout in `template.yaml`
   - Check for cold start issues

3. **Google OAuth errors**
   - Verify redirect URIs in Google Console
   - Check client ID/secret configuration

4. **DynamoDB permission errors**
   - Ensure IAM role has DynamoDB permissions
   - Check table name configuration

### Debug Commands
```bash
# Validate SAM template
make validate-template

# Check AWS credentials
aws sts get-caller-identity

# Test Google OAuth locally
poetry run python -c "from src.shared.config import GOOGLE_CLIENT_CONFIG; print(GOOGLE_CLIENT_CONFIG)"
```

## 📈 Next Steps

1. **Set up monitoring and alerting**
2. **Implement proper logging and observability**
3. **Add integration tests**
4. **Set up automated backups**
5. **Implement blue/green deployments for zero downtime**
6. **Add performance testing**

## 🤝 Contributing

1. Create a feature branch from `develop`
2. Make your changes
3. Ensure all tests pass: `make ci-test`
4. Create a pull request to `develop`
5. After review, merge to `develop` for staging deployment
6. Create a release PR from `develop` to `main` for production deployment
