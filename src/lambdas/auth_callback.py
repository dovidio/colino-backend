"""
OAuth callback Lambda function for handling Google OAuth authorization code exchange.
"""

import os
import logging
import json
import datetime
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

        # Get actual expiry information from Google's response
        expires_in = None
        expires_at = None
        expires_timestamp = None
        
        if credentials.expiry:
            expires_at = credentials.expiry
            expires_timestamp = int(expires_at.timestamp())
            # Calculate seconds until expiry
            expires_in = int((expires_at - datetime.datetime.now(expires_at.tzinfo)).total_seconds())
        else:
            # Fallback to Google's default if expiry not provided
            expires_in = 3600  # 1 hour in seconds
            expires_at = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)
            expires_timestamp = int(expires_at.timestamp())

        # Prepare response data with essential token information only
        # Privacy-first: only return what the client actually needs
        response_data = {
            "message": "Authentication successful",
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
        }

        # Prepare CLI-friendly token data (without sensitive client info)
        cli_token_data = {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_in": expires_in,
            "expires_at": expires_timestamp,
            "token_type": "Bearer",
            "scope": " ".join(SCOPES)
        }

        # Check if request accepts JSON
        headers = event.get("headers", {})
        accept_header = headers.get("Accept", headers.get("accept", ""))

        if "application/json" in accept_header:
            return create_response(200, response_data)
        else:
            # Create warning message outside f-string to avoid backslash issues
            refresh_token_warning = ""
            if not credentials.refresh_token:
                refresh_token_warning = '<div style="background: #fff3cd; padding: 15px; margin: 15px 0; border-radius: 6px; color: #856404;"><strong>WARNING:</strong> No refresh token was provided. This usually means you have authorized this app before. The access token will expire in 1 hour. To get a refresh token, <a href="https://myaccount.google.com/permissions" target="_blank">revoke previous access</a> and try again.</div>'
            # Return HTML page for browser
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Successful</title>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center;
                           margin: 50px; }}
                    .success {{ color: green; }}
                    .token-container {{ background: #f8f9fa; padding: 30px; margin: 20px auto;
                                       border-radius: 12px; max-width: 500px; 
                                       box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .copy-btn {{ background: #28a745; color: white; border: none;
                                padding: 15px 30px; margin: 20px; border-radius: 8px;
                                cursor: pointer; font-size: 16px; font-weight: bold;
                                transition: all 0.3s ease; }}
                    .copy-btn:hover {{ background: #218838; transform: translateY(-2px); }}
                    .copy-btn:active {{ background: #1e7e34; }}
                    .instructions {{ background: #d4edda; padding: 20px; margin: 20px auto;
                                    border-radius: 8px; max-width: 500px; color: #155724;
                                    border-left: 4px solid #28a745; }}
                    .token-info {{ background: #e9ecef; padding: 15px; margin: 15px 0;
                                  border-radius: 6px; font-family: monospace; }}
                    .hidden-content {{ color: #6c757d; font-style: italic; }}
                    .success-icon {{ font-size: 48px; margin-bottom: 10px; color: #28a745; }}
                </style>
            </head>
            <body>
                <div class="success-icon">[OK]</div>
                <h1 class="success">Authentication Successful!</h1>
                <div class="token-container">
                    <p>One last step: click the button below to copy your access information and paste it in the terminal where you are running Colino</p>                 
                    <button class="copy-btn" onclick="copyTokenData()">
                        Copy Access Information for Colino
                    </button>
                    
                    {refresh_token_warning}
                </div>
                
                <p style="color: #6c757d; font-size: 14px;">
                    Your access information is hidden for security and ready to be copied when you click the button above.<br>
                    Return to your terminal and paste this information when prompted by Colino.
                </p>
                
                <script>
                const tokenData = {json.dumps(cli_token_data, indent=2)};
                
                function copyTokenData() {{
                    const jsonString = JSON.stringify(tokenData, null, 2);
                    
                    navigator.clipboard.writeText(jsonString).then(function() {{
                        const button = document.querySelector('.copy-btn');
                        const originalText = button.textContent;
                        const originalBg = button.style.backgroundColor;
                        
                        button.textContent = 'Copied to Clipboard!';
                        button.style.backgroundColor = '#007bff';
                        
                        setTimeout(function() {{
                            button.textContent = originalText;
                            button.style.backgroundColor = originalBg;
                        }}, 3000);
                    }}).catch(function(err) {{
                        // Fallback for older browsers
                        const textarea = document.createElement('textarea');
                        textarea.value = jsonString;
                        document.body.appendChild(textarea);
                        textarea.select();
                        document.execCommand('copy');
                        document.body.removeChild(textarea);
                        
                        const button = document.querySelector('.copy-btn');
                        const originalText = button.textContent;
                        button.textContent = 'Copied!';
                        setTimeout(function() {{
                            button.textContent = originalText;
                        }}, 3000);
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
