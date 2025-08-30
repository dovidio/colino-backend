# OAuth Flow Documentation

## 🔄 Understanding the OAuth Flow

This backend provides a **server-to-server OAuth proxy** that handles Google YouTube authentication on behalf of client applications. The flow uses four main endpoints to manage the complete OAuth lifecycle.

## 📋 API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/auth/initiate` | GET | Start OAuth flow, get authorization URL and session ID |
| `/callback` | GET | Handle OAuth callback from Google (browser redirect) |
| `/auth/poll/{session_id}` | GET | Poll for authentication status and retrieve tokens |
| `/auth/refresh` | POST | Refresh expired access tokens |

## 🏗️ Architecture Overview

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client    │    │  OAuth Proxy    │    │     Google      │    │   DynamoDB      │
│ Application │    │   (Lambda)      │    │ OAuth Server    │    │   Sessions      │
└─────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
       │                     │                       │                     │
       │                     │                       │                     │
```

## 🔄 Complete OAuth Flow

### Step 1: Initiate Authentication
```
Client Application → auth/initiate
```

**Request:**
```http
GET /auth/initiate
```

**Response:**
```json
{
  "authorization_url": "https://accounts.google.com/oauth2/auth?client_id=...",
  "session_id": "dd589ff7-e46b-42ed-a338-ebe59116075d"
}
```

**What happens:**
- Lambda generates Google OAuth authorization URL
- Creates session entry in DynamoDB with status "pending"
- Returns authorization URL and unique session ID

### Step 2: User Authentication (Browser)
```
Client opens authorization_url → Google OAuth → callback
```

**Flow:**
1. Client opens the `authorization_url` in a browser
2. User completes Google OAuth consent flow
3. Google redirects to `/callback` with authorization code
4. Callback Lambda exchanges code for tokens
5. Tokens are saved to DynamoDB with session ID

**User sees:**
- Google OAuth consent screen
- After completion: "Authentication successful" page with session ID

### Step 3: Poll for Tokens
```
Client Application → auth/poll/{session_id}
```

**Request:**
```http
GET /auth/poll/dd589ff7-e46b-42ed-a338-ebe59116075d
```

**Possible Responses:**

**3a. Pending (202):**
```json
{
  "status": "pending",
  "message": "Authentication in progress. Please complete the OAuth flow in your browser."
}
```

**3b. Success (200):**
```json
{
  "status": "completed",
  "access_token": "ya29.a0AfH6SMBq...",
  "refresh_token": "1//04vF_Zm8jNs_JCgYIARAAGAQSNwF...",
  "expires_in": 3599,
  "token_type": "Bearer",
  "scope": "https://www.googleapis.com/auth/youtube.readonly"
}
```

**3c. Not Found (404):**
```json
{
  "error": "Session not found"
}
```

### Step 4: Token Refresh (When Needed)
```
Client Application → auth/refresh
```

**Request:**
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "1//04vF_Zm8jNs_JCgYIARAAGAQSNwF..."
}
```

**Response:**
```json
{
  "access_token": "ya29.a0AfH6SMBq_NEW_TOKEN...",
  "expires_in": 3599,
  "token_type": "Bearer",
  "scope": "https://www.googleapis.com/auth/youtube.readonly"
}
```

## 📊 Flow Diagram

```
┌─────────────┐
│   Client    │
│ Application │
└──────┬──────┘
       │
       │ 1. GET /auth/initiate
       ▼
┌─────────────────┐
│ auth_initiate   │────────┐
│    Lambda       │        │ Save session
└─────────┬───────┘        ▼
          │           ┌─────────────────┐
          │           │   DynamoDB      │
          │           │   Sessions      │
          ▼           └─────────────────┘
┌─────────────────┐
│ authorization_url│
│   + session_id  │
└─────────┬───────┘
          │
          │ 2. User opens URL in browser
          ▼
┌─────────────────┐        ┌─────────────────┐
│     Google      │        │ auth_callback   │
│ OAuth Server    │───────▶│    Lambda       │
└─────────────────┘        └─────────┬───────┘
                                     │
                                     │ Save tokens
                                     ▼
                               ┌─────────────────┐
                               │   DynamoDB      │
                               │   Sessions      │
                               └─────────────────┘
                                     ▲
          ┌─────────────────┐        │
          │   Client        │        │
          │ Polling Loop    │────────┘ 3. GET /auth/poll/{session_id}
          └─────────┬───────┘
                    │
                    │ 4. Use tokens for API calls
                    ▼
          ┌─────────────────┐
          │    YouTube      │
          │      API        │
          └─────────────────┘
                    │
                    │ When token expires
                    ▼
          ┌─────────────────┐
          │ auth_refresh    │
          │    Lambda       │
          └─────────────────┘
```

## 🔄 Session Lifecycle

1. **Created**: Session entry created with status "pending"
2. **Pending**: Waiting for user to complete OAuth in browser  
3. **Completed**: Tokens available for retrieval via polling
4. **Expired**: Session expires after tokens are retrieved (optional cleanup)

## 🕐 Polling Strategy

**Recommended client polling pattern:**
```
1. Call /auth/initiate
2. Open authorization_url in browser
3. Poll /auth/poll/{session_id} every 2-3 seconds
4. Stop polling when status != "pending"
5. Use tokens for API calls
6. Refresh tokens when they expire using /auth/refresh
```

## � Security Features

- **Session Isolation**: Each authentication flow gets unique session ID
- **Temporary Storage**: Tokens stored only during OAuth flow
- **CORS Support**: Browser-friendly for client applications
- **HTTPS Only**: All endpoints require secure connections
- **Token Expiration**: Access tokens have limited lifetime, refresh tokens for renewal

## 📝 Example Client Implementation

```javascript
async function authenticate() {
  // 1. Start OAuth flow
  const { authorization_url, session_id } = await fetch('/auth/initiate').then(r => r.json());
  
  // 2. Open browser for user authentication
  window.open(authorization_url);
  
  // 3. Poll for completion
  while (true) {
    const response = await fetch(`/auth/poll/${session_id}`);
    
    if (response.status === 200) {
      const tokens = await response.json();
      // Store tokens securely
      localStorage.setItem('access_token', tokens.access_token);
      localStorage.setItem('refresh_token', tokens.refresh_token);
      break;
    } else if (response.status === 202) {
      // Still pending, wait and try again
      await new Promise(resolve => setTimeout(resolve, 2000));
    } else {
      throw new Error('Authentication failed');
    }
  }
}

async function refreshToken() {
  const refresh_token = localStorage.getItem('refresh_token');
  const response = await fetch('/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token })
  });
  
  const { access_token } = await response.json();
  localStorage.setItem('access_token', access_token);
}
```

## 🚨 Error Handling

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Use returned data |
| 202 | Pending | Continue polling |
| 400 | Bad Request | Check request format |
| 404 | Not Found | Invalid session ID |
| 500 | Server Error | Retry or contact support |

## 🎯 Best Practices

1. **Implement exponential backoff** for polling to avoid rate limits
2. **Store refresh tokens securely** (not in localStorage for production)
3. **Handle token expiration gracefully** with automatic refresh
4. **Validate all responses** before using tokens
5. **Implement proper error handling** for all endpoints
