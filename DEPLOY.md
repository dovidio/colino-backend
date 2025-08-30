# Quick Deployment Guide

## Prerequisites

1. **AWS CLI** configured with appropriate permissions
2. **SAM CLI** installed (`pip install aws-sam-cli`)
3. **Google OAuth credentials** from Google Cloud Console

## Setup Steps

### 1. Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new OAuth 2.0 Client ID (Web application)
3. Note down your Client ID and Client Secret
4. **Important**: You'll need to add the callback URL later (after deployment)

### 2. Set Environment Variables

```bash
export SAM_S3_BUCKET="your-unique-bucket-name"
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"
export AWS_REGION="us-east-1"  # optional, defaults to us-east-1
```

### 3. Create S3 Bucket (one-time setup)

```bash
aws s3 mb s3://your-unique-bucket-name --region us-east-1
```

### 4. Deploy

```bash
make deploy
```

Or manually:
```bash
./deploy.sh
```

### 5. Configure Google OAuth Redirect URI

After deployment, you'll get two URLs:
- **Initiate URL**: `https://xxx.execute-api.us-east-1.amazonaws.com/Prod/auth/initiate`
- **Callback URL**: `https://xxx.execute-api.us-east-1.amazonaws.com/Prod/callback`

Add the **Callback URL** to your Google OAuth configuration as an authorized redirect URI.

## That's It!

Your OAuth proxy is now deployed and ready to use. The initiate URL is what your clients will call to start the OAuth flow.

## Environment Variables Summary

| Variable | Required | Description |
|----------|----------|-------------|
| `SAM_S3_BUCKET` | ✅ | S3 bucket for SAM deployment artifacts |
| `GOOGLE_CLIENT_ID` | ✅ | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | ✅ | From Google Cloud Console |
| `AWS_REGION` | ❌ | AWS region (defaults to us-east-1) |
| `ALLOWED_ORIGINS` | ❌ | CORS origins (defaults to *) |
