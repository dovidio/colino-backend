# OAuth Flow Documentation

## 🔄 Understanding the OAuth Flow

This project uses a **server-to-server OAuth flow** where your AWS Lambda functions handle the OAuth process, not your local machine.

### Architecture Overview

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI App   │    │  AWS Lambda     │    │     Google      │    │  AWS Lambda     │
│ (Your Local │────│ auth_initiate   │────│   OAuth Server  │────│ auth_callback   │
│  Machine)   │    │                 │    │                 │    │                 │
└─────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Step-by-Step Flow

1. **CLI calls auth_initiate Lambda**
   ```bash
   python cli.py --user-id user123 auth --auth-url https://your-api.amazonaws.com/Prod/auth/initiate
   ```

2. **Lambda returns Google authorization URL**
   - URL points to Google OAuth server
   - Redirect URI points back to your `auth_callback` Lambda (NOT localhost!)
   - Example: `https://accounts.google.com/oauth2/auth?client_id=...&redirect_uri=https://your-api.amazonaws.com/Prod/callback`

3. **CLI opens browser with authorization URL**
   - User sees Google consent screen
   - User grants permissions for YouTube access

4. **Google redirects to auth_callback Lambda**
   - Google calls: `https://your-api.amazonaws.com/Prod/callback?code=AUTH_CODE&state=STATE`
   - Lambda exchanges code for tokens
   - Lambda shows success page to user

5. **CLI can now use stored tokens**
   ```bash
   python cli.py --user-id user123 subscriptions
   ```

## 🔧 Configuration

### Environment Variables

The `REDIRECT_URI` environment variable must be set to your auth_callback Lambda URL:

```bash
# For staging
REDIRECT_URI=https://your-staging-api.execute-api.us-east-1.amazonaws.com/Prod/callback

# For production  
REDIRECT_URI=https://your-production-api.execute-api.us-east-1.amazonaws.com/Prod/callback
```

### Google Cloud Console Setup

In your Google Cloud Console OAuth configuration, add these authorized redirect URIs:

- `https://your-staging-api.execute-api.us-east-1.amazonaws.com/Prod/callback`
- `https://your-production-api.execute-api.us-east-1.amazonaws.com/Prod/callback`

**Important**: Do NOT use `localhost` URLs in production!

## 🖥️ CLI Usage

### 1. Authenticate (One-time setup)

```bash
# Get your auth_initiate URL from AWS CloudFormation outputs
python cli.py --user-id your-unique-id auth --auth-url https://your-api.amazonaws.com/Prod/auth/initiate
```

### 2. Use CLI commands

```bash
# Check authentication status
python cli.py --user-id your-unique-id status

# Get subscriptions
python cli.py --user-id your-unique-id subscriptions

# Search channels
python cli.py --user-id your-unique-id search "python tutorials"
```

## 🔍 Troubleshooting

### Common Issues

1. **"redirect_uri_mismatch" error**
   - Check that REDIRECT_URI environment variable matches Google Console settings
   - Ensure URLs use HTTPS (except for localhost development)

2. **"REDIRECT_URI environment variable must be set"**
   - Set the REDIRECT_URI environment variable in your Lambda function
   - This should point to your auth_callback Lambda, not localhost

3. **"No tokens found for user"**
   - Run the auth command first
   - Check that the user_id is consistent between auth and CLI commands

### Development vs Production

#### Development (Local Testing)
- You can use `sam local start-api` for local testing
- Set `REDIRECT_URI=http://localhost:3000/callback` for local development
- Add `http://localhost:3000/callback` to Google Console for development

#### Production (AWS Deployment)
- Use actual AWS API Gateway URLs
- Always use HTTPS URLs
- Set proper CORS origins

## 🔒 Security Considerations
1. **State Parameter**: OAuth state prevents CSRF attacks
2. **HTTPS Only**: Always use HTTPS in production
3. **Scope Limitation**: Only request necessary YouTube scopes

## 🎯 Best Practices

1. **Consistent User IDs**: Use the same user_id for auth and CLI commands
2. **Token Expiry**: Check token expiry and handle refresh tokens
3. **Error Handling**: Always check command return codes
4. **Secure Storage**: Consider encrypting tokens in DynamoDB
5. **Logging**: Monitor CloudWatch logs for authentication issues
