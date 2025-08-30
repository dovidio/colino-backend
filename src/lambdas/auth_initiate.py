"""
AWS Lambda function to initiate Google OAuth flow for YouTube API access.
This function generates the authorization URL that users need to visit.
"""

import os
import sys
from typing import Dict, Any

from google_auth_oauthlib.flow import Flow

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from shared.config import GOOGLE_CLIENT_CONFIG, SCOPES  # noqa: E402
from shared.response_utils import create_response  # noqa: E402


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler to initiate Google OAuth flow.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        Dict containing authorization URL and state
    """
    try:
        # Construct redirect URI dynamically from the event
        headers = event.get("headers", {})
        host = headers.get("Host") or headers.get("host")
        
        if not host:
            raise ValueError("Unable to determine API Gateway host")
        
        # Construct the callback URL
        redirect_uri = f"https://{host}/Prod/callback"

        # Create OAuth flow
        flow = Flow.from_client_config(GOOGLE_CLIENT_CONFIG, scopes=SCOPES)
        flow.redirect_uri = redirect_uri

        # Generate authorization URL
        authorization_url, state = flow.authorization_url(
            access_type="offline", 
            include_granted_scopes="true",
            prompt="consent"  # Force consent screen to get refresh token
        )

        response_data = {
            "authorization_url": authorization_url,
            "state": state,
            "redirect_uri": redirect_uri,
        }

        return create_response(200, response_data)

    except Exception as e:
        error_response = {
            "error": "Failed to generate authorization URL",
            "message": str(e),
        }
        return create_response(500, error_response)
