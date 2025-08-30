"""
OAuth callback Lambda function for handling Google OAuth authorization code exchange.
"""

import os
import logging
from google_auth_oauthlib.flow import Flow
from shared.config import get_oauth_config
from shared.response_utils import create_response, create_error_response

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
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
        flow = Flow.from_client_config(
            oauth_config, scopes=["https://www.googleapis.com/auth/youtube.readonly"]
        )

        # Set redirect URI
        redirect_uri = os.environ.get("REDIRECT_URI")
        if not redirect_uri:
            return create_error_response(500, "REDIRECT_URI not configured")

        flow.redirect_uri = redirect_uri

        # Exchange authorization code for tokens
        flow.fetch_token(code=auth_code)

        # Get credentials
        credentials = flow.credentials

        # Prepare response data with all token information
        # No storage - privacy first, return tokens to CLI client
        response_data = {
            "message": "Authentication successful",
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "expires_in": 3600 if credentials.expiry else None,  # Default to 1 hour
            "scope": " ".join(credentials.scopes) if credentials.scopes else None,
        }

        # Check if request accepts JSON
        headers = event.get("headers", {})
        accept_header = headers.get("Accept", headers.get("accept", ""))

        if "application/json" in accept_header:
            return create_response(200, response_data)
        else:
            # Return HTML page for browser
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Successful</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center;
                           margin: 50px; }}
                    .success {{ color: green; }}
                    .token {{ background: #f0f0f0; padding: 10px; margin: 20px;
                             word-break: break-all; }}
                </style>
            </head>
            <body>
                <h1 class="success">Authentication Successful!</h1>
                <p>You have successfully authorized the application to access
                   your YouTube data.</p>
                <div class="token">
                    <strong>Access Token:</strong><br>
                    {credentials.token[:20]}...
                </div>
                <p>You can now close this window.</p>
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
