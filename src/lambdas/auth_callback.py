"""
OAuth callback Lambda function for handling Google OAuth authorization code exchange.
"""

import os
import logging
from google_auth_oauthlib.flow import Flow
from shared.config import get_oauth_config, SCOPES
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
            oauth_config, scopes=SCOPES
        )

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

        # Prepare response data with essential token information only
        # Privacy-first: only return what the client actually needs
        response_data = {
            "message": "Authentication successful",
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
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
                    .token-container {{ background: #f8f9fa; padding: 20px; margin: 20px auto;
                                       border-radius: 8px; max-width: 600px; }}
                    .token {{ background: #e9ecef; padding: 15px; margin: 10px 0;
                             word-break: break-all; font-family: monospace;
                             border-radius: 4px; }}
                    .copy-btn {{ background: #007bff; color: white; border: none;
                                padding: 10px 20px; margin: 5px; border-radius: 4px;
                                cursor: pointer; font-size: 14px; }}
                    .copy-btn:hover {{ background: #0056b3; }}
                    .copy-btn:active {{ background: #004085; }}
                    .instructions {{ background: #d4edda; padding: 15px; margin: 20px auto;
                                    border-radius: 8px; max-width: 600px; color: #155724; }}
                </style>
            </head>
            <body>
                <h1 class="success">Authentication Successful!</h1>
                <p>You have successfully authorized the application to access your YouTube data.</p>
                
                <div class="instructions">
                    <strong>For CLI users:</strong><br>
                    1. Click the "Copy Access Token" button below<br>
                    2. Go back to your terminal<br>
                    3. Paste the token when prompted
                </div>
                
                <div class="token-container">
                    <h3>Access Token:</h3>
                    <div class="token" id="accessToken">{credentials.token}</div>
                    <button class="copy-btn" onclick="copyToClipboard('accessToken', this)">
                        Copy Access Token
                    </button>
                    
                    <h3>Refresh Token:</h3>
                    <div class="token" id="refreshToken">{credentials.refresh_token or 'None'}</div>
                    <button class="copy-btn" onclick="copyToClipboard('refreshToken', this)">
                        Copy Refresh Token
                    </button>
                    
                    <br><br>
                    <button class="copy-btn" onclick="copyBothTokens()" style="background: #28a745;">
                        Copy Both Tokens (JSON)
                    </button>
                </div>
                
                <p>You can now close this window.</p>
                
                <script>
                function copyToClipboard(elementId, button) {{
                    const element = document.getElementById(elementId);
                    const text = element.textContent;
                    
                    navigator.clipboard.writeText(text).then(function() {{
                        const originalText = button.textContent;
                        button.textContent = 'Copied!';
                        button.style.background = '#28a745';
                        setTimeout(function() {{
                            button.textContent = originalText;
                            button.style.background = '#007bff';
                        }}, 2000);
                    }}).catch(function(err) {{
                        // Fallback for older browsers
                        const textarea = document.createElement('textarea');
                        textarea.value = text;
                        document.body.appendChild(textarea);
                        textarea.select();
                        document.execCommand('copy');
                        document.body.removeChild(textarea);
                        
                        const originalText = button.textContent;
                        button.textContent = 'Copied!';
                        button.style.background = '#28a745';
                        setTimeout(function() {{
                            button.textContent = originalText;
                            button.style.background = '#007bff';
                        }}, 2000);
                    }});
                }}
                
                function copyBothTokens() {{
                    const accessToken = document.getElementById('accessToken').textContent;
                    const refreshToken = document.getElementById('refreshToken').textContent;
                    const json = JSON.stringify({{
                        access_token: accessToken,
                        refresh_token: refreshToken === 'None' ? null : refreshToken
                    }}, null, 2);
                    
                    navigator.clipboard.writeText(json).then(function() {{
                        const button = event.target;
                        const originalText = button.textContent;
                        button.textContent = 'Copied JSON!';
                        setTimeout(function() {{
                            button.textContent = originalText;
                        }}, 2000);
                    }});
                }}
                </script>
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
