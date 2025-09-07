# Colino Backend

AWS Lambda functions for Google YouTube OAuth authentication proxy.

## Overview

This project provides the backend for [colino-cli](https://github.com/dovidio/colino).
It comprises a few lambda functions to handle Google OAuth flows and token management, so that the CLI can interact with YouTube APIs without embedding sensitive credentials.
The backend is designed to be stateless and secure, using DynamoDB only for temporary token storage.

## Architecture

- **Lambda 1 (`auth_initiate`)**: Generates Google OAuth authorization URL
- **Lambda 2 (`auth_callback`)**: Handles OAuth callback and exchanges authorization code for tokens
- **Lambda 3 (`auth_refresh`)**: Refreshes expired access tokens using refresh tokens
- **Lambda 4 (`poll`)**: Polls the status of the OAuth flow
- **Shared utilities**: Common code for configuration and HTTP response handling

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- Poetry
- AWS CLI configured
- Google Cloud Console project with YouTube API enabled

### Installation

1. Install dependencies:
```bash
make install
```

### Running Tests

```bash
poetry run pytest
```

### Code Formatting & Linting

```bash
make lint        # Run linting and type checking
make lint-fix    # Auto-fix linting issues
make format      # Format code
```

## 🔒 Security

This project includes automated security monitoring:

- **Dependabot**: Automatically creates PRs for dependency updates and security patches
- **Security Workflow**: Weekly security scans using Bandit and Safety
- **Dependency Review**: Reviews new dependencies in PRs for known vulnerabilities

### Running Security Scans Locally

```bash
make ci-security
```

## License

This project is licensed under the MIT License.