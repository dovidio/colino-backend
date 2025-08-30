"""
OAuth callback Lambda function for handling Google OAuth authorization code
exchange.
"""

import logging
import datetime
import uuid
from typing import Dict, Any
from google_auth_oauthlib.flow import Flow  # type: ignore
from shared.config import get_oauth_config, SCOPES
from shared.response_utils import create_error_response
from shared.token_storage import save_oauth_tokens

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
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

        # Construct the callback URL
        redirect_uri = f"https://{host}/Prod/callback"
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

        # Save tokens to DynamoDB
        success = save_oauth_tokens(session_id, token_data, expires_in)

        if not success:
            logger.error(f"Failed to save tokens for session {session_id}")
            return create_error_response(500, "Failed to save authentication data")

        logger.info(f"Successfully processed OAuth callback for session {session_id}")

        # Return HTML page with instructions to keep CLI running
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Complete</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
                                 Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    text-align: center;
                    margin: 0;
                    padding: 50px 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                }}
                .container {{
                    background: rgba(255, 255, 255, 0.95);
                    color: #333;
                    padding: 40px;
                    border-radius: 16px;
                    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                    max-width: 600px;
                    width: 100%;
                }}
                .success-icon {{
                    font-size: 64px;
                    margin-bottom: 20px;
                    color: #28a745;
                }}
                h1 {{
                    color: #28a745;
                    margin-bottom: 20px;
                    font-size: 28px;
                }}
                p {{
                    font-size: 18px;
                    line-height: 1.6;
                    margin-bottom: 20px;
                    color: #666;
                }}
                .important-instruction {{
                    background: #fff3cd;
                    padding: 20px;
                    border-radius: 8px;
                    border-left: 4px solid #ffc107;
                    margin: 20px 0;
                    color: #856404;
                }}
                .close-instruction {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    border-left: 4px solid #28a745;
                    margin-top: 20px;
                }}
                .session-info {{
                    background: #e9ecef;
                    padding: 15px;
                    border-radius: 8px;
                    font-family: monospace;
                    margin: 15px 0;
                    word-break: break-all;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✅</div>
                <h1>Authentication Successful!</h1>
                <p>
                    Your OAuth authentication has been completed successfully
                    and your tokens have been securely stored.
                </p>

                <div class="important-instruction">
                    <strong>⚠️ Important:</strong> Please make sure your CLI
                    command is still running in the terminal before closing
                    this browser window. The CLI needs a few seconds to
                    retrieve your authentication tokens.
                </div>

                <div class="session-info">Session ID: {session_id}</div>

                <div class="close-instruction">
                    <strong>
                        After your CLI confirms successful authentication,
                        you can safely close this browser window.
                    </strong>
                </div>
            </div>
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
