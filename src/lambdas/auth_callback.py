"""
OAuth callback Lambda function for handling Google OAuth authorization code
exchange.
"""

import datetime
import logging
import uuid
from typing import Any

from google_auth_oauthlib.flow import Flow  # type: ignore

from shared.config import SCOPES, get_oauth_config
from shared.response_utils import create_error_response
from shared.token_storage import save_oauth_tokens

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Handle OAuth callback from Google.

    Args:
        event: API Gateway event containing query parameters
        context: Lambda context object

    Returns:
        API Gateway response
    """
    try:
        # Get query parameters
        query_params = event.get("queryStringParameters", {})

        if not query_params:
            return create_error_response(400, "Missing query parameters")

        # Check for OAuth error
        if "error" in query_params:
            error_msg = f"OAuth error: {query_params['error']}"
            if "error_description" in query_params:
                error_msg += f" - {query_params['error_description']}"
            return create_error_response(400, error_msg)

        # Get authorization code
        auth_code = query_params.get("code")
        if not auth_code:
            return create_error_response(400, "Missing authorization code")

        # Get state parameter (optional but recommended for security)
        state = query_params.get("state")
        logger.info(f"Processing OAuth callback with state: {state}")

        # Get OAuth configuration
        oauth_config = get_oauth_config()

        # Create flow instance
        flow = Flow.from_client_config(oauth_config, scopes=SCOPES)

        # Construct redirect URI dynamically from the event
        headers = event.get("headers", {})
        host = headers.get("Host") or headers.get("host")

        if not host:
            return create_error_response(500, "Unable to determine API Gateway host")

        # Construct the callback URL - check if using custom domain
        if host.endswith('.amazonaws.com'):
            # Using API Gateway URL, include stage
            redirect_uri = f"https://{host}/Prod/callback"
        else:
            # Using custom domain, no stage prefix needed
            redirect_uri = f"https://{host}/callback"
        flow.redirect_uri = redirect_uri

        # Exchange authorization code for tokens
        flow.fetch_token(code=auth_code)

        # Get credentials
        credentials = flow.credentials

        # Get actual expiry information from Google's response
        expires_in = None
        expires_at = None
        expires_timestamp = None

        if credentials.expiry:
            expires_at = credentials.expiry
            expires_timestamp = int(expires_at.timestamp())
            # Calculate seconds until expiry
            expires_in = int(
                (expires_at - datetime.datetime.now(expires_at.tzinfo)).total_seconds()
            )
        else:
            # Fallback to Google's default if expiry not provided
            expires_in = 3600  # 1 hour in seconds
            expires_at = datetime.datetime.now() + datetime.timedelta(
                seconds=expires_in
            )
            expires_timestamp = int(expires_at.timestamp())

        # Prepare token data for storage
        token_data = {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "expires_at": expires_timestamp,
            "scope": " ".join(SCOPES),
        }

        # Generate a unique session ID if state is not provided
        session_id = state if state else str(uuid.uuid4())

        success = save_oauth_tokens(session_id, token_data)

        if not success:
            logger.error(f"Failed to save tokens for session {session_id}")
            return create_error_response(500, "Failed to save authentication data")

        logger.info(f"Successfully processed OAuth callback for session {session_id}")

        # Return HTML page with instructions to keep CLI running
        html_content = """
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Authentication Successful • Colino</title>
      <style>
        html, body { height: 100%; }
        body {
          margin: 0;
          font-family: Roboto, Helvetica;
          background: #313131;
          display: grid;
          place-items: center;
        }
        .card {
          text-align: center;
        }
        .logos {
          display: grid;
          place-items: center;
          margin-bottom: 24px;
          gap: 16px;
        }
        .logos .colino {
          display: inline-grid;
          place-items: center;
          width: 256px; height: 256px;
        }

        h1 {
          font-size: 2rem;
          margin: 12px 0;
          line-height: 1.2;
          color: #ffffff;
        }
        p.subtitle {
          font-size: 1.125rem;
          color: #d6d6d6;
        }
        .success {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          background: rgba(34, 197, 94, 0.1);
          border: 2px solid rgba(34, 197, 94, 0.1);
          color: #22c55e;
          padding: 12px 14px;
          border-radius: 999px;
          font-weight: 600;
          margin: 16px 0 8px;
        }
      </style>
    </head>
    <body>
      <main class="card" role="main" aria-labelledby="title">
        <div class="logos" aria-label="Colino logo">
            <img class="colino" src="https://colinoassets.s3.us-east-1.amazonaws.com/filtering.png" alt="Colino" />
        </div>

        <div class="success" aria-live="polite">
         <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10Z" stroke="currentColor" stroke-width="2"/>
            <path d="M8 12.5l2.5 2.5L16 9.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          Authentication successful
        </div>

        <h1 id="title">You're all set.</h1>
        <p class="subtitle">You can now close this tab and use <strong>Colino</strong> in your terminal.</p>
      </main>
    </body>
    </html>
       """

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/html",
                "Access-Control-Allow-Origin": "*",
            },
            "body": html_content,
        }

    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        return create_error_response(500, f"Internal server error: {str(e)}")
