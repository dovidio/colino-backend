# Colino Backend

AWS Lambda functions for Google YouTube OAuth authentication proxy.

## Overview

This project provides two AWS Lambda functions that act as a proxy for Google OAuth authentication to obtain YouTube API tokens. These tokens can then be used by the colino command-line application to fetch user subscriptions and other YouTube data.
Colino is privacy-focused, so we won't store any user data or tokens. Instead, the API token is sent back to the command-line app so it can make authenticated requests directly to the YouTube API.

## Architecture

- **Lambda 1 (`auth_initiate`)**: Generates Google OAuth authorization URL
- **Lambda 2 (`auth_callback`)**: Handles OAuth callback and exchanges authorization code for tokens
- **Shared utilities**: Common code for configuration, token storage, and YouTube API operations

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Poetry
- AWS CLI configured
- Google Cloud Console project with YouTube API enabled

### Installation

1. Install dependencies:
```bash
make install
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your values
```

3. Set up development environment:
```bash
make setup-dev
```

## 🔄 CI/CD Pipeline

This project includes a complete CI/CD pipeline using GitHub Actions for automated testing and deployment.

### Quick Setup
1. **Configure GitHub Secrets** - See [CI/CD Setup Guide](docs/CI-CD-SETUP.md)
2. **Push to `develop`** - Automatically deploys to staging
3. **Push to `main`** - Automatically deploys to production

### Manual Deployment
```bash
# Deploy to development
make deploy-dev

# Deploy to staging
make deploy-staging

# Deploy to production
make deploy-production
```

For detailed CI/CD setup instructions, see **[docs/CI-CD-SETUP.md](docs/CI-CD-SETUP.md)**

## Usage

### Authentication Flow

**Important**: The OAuth flow uses your AWS Lambda functions as the redirect endpoint, NOT localhost!

1. **Authenticate once:**
   ```bash
   python cli.py --user-id your-unique-id auth --auth-url https://your-api.amazonaws.com/Prod/auth/initiate
   ```

2. **Use CLI commands:**
   ```bash
   # Check status
   python cli.py --user-id your-unique-id status
   
   # Get subscriptions
   python cli.py --user-id your-unique-id subscriptions
   
   # Search channels
   python cli.py --user-id your-unique-id search "python tutorials"
   ```

📖 **Detailed OAuth Flow**: See **[docs/OAUTH-FLOW.md](docs/OAUTH-FLOW.md)** for complete authentication setup and troubleshooting.

### Command Line Usage

```python
from src.shared.youtube_client import YouTubeClient

# Initialize client with user ID
client = YouTubeClient('user123')

# Get user subscriptions
subscriptions = client.get_subscriptions(max_results=100)

# Search for channels
channels = client.search_channels('python tutorials')
```

## Project Structure

```
colino-backend/
├── src/
│   ├── lambdas/
│   │   ├── auth_initiate.py      # OAuth initiation Lambda
│   │   └── auth_callback.py      # OAuth callback Lambda
│   └── shared/
│       ├── config.py             # Configuration settings
│       ├── response_utils.py     # API response utilities
│       ├── token_storage.py      # Token storage operations
│       └── youtube_client.py     # YouTube API client
├── tests/
├── pyproject.toml
└── README.md
```

## Environment Variables

- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `REDIRECT_URI`: OAuth callback URL
- `DYNAMODB_TABLE_NAME`: DynamoDB table for token storage
- `AWS_REGION`: AWS region
- `USE_DYNAMODB`: Use DynamoDB for storage (default: true)
- `ALLOWED_ORIGINS`: CORS allowed origins

## Development

### Running Tests

```bash
poetry run pytest
```

### Code Formatting

```bash
poetry run black src/
poetry run flake8 src/
```

### Type Checking

```bash
poetry run mypy src/
```

## Deployment

The Lambda functions can be deployed using various methods:

- AWS SAM
- Serverless Framework
- AWS CDK
- Manual deployment with ZIP files

Make sure to include all dependencies in the deployment package and set appropriate IAM permissions for DynamoDB access.

## Security Considerations

- Store Google client credentials securely (AWS Secrets Manager recommended)
- Use least privilege IAM policies
- Enable CloudTrail logging
- Consider encrypting tokens in DynamoDB
- Validate and sanitize all inputs
- Implement rate limiting

## License

This project is licensed under the MIT License.
