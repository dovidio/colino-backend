"""
AWS Lambda function to initiate Google OAuth flow for YouTube API access.
This function generates the authorization URL that users need to visit.
"""

import os
import sys
import uuid
from typing import Dict, Any

from google_auth_oauthlib.flow import Flow

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from shared.config import GOOGLE_CLIENT_CONFIG, SCOPES  # noqa: E402
from shared.response_utils import create_response  # noqa: E402
from shared.token_storage import save_oauth_tokens  # noqa: E402


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

        # Generate a unique session ID
        session_id = str(uuid.uuid4())

        # Create OAuth flow with the session ID as state
        flow = Flow.from_client_config(GOOGLE_CLIENT_CONFIG, scopes=SCOPES)
        flow.redirect_uri = redirect_uri

        # Generate authorization URL using session_id as state
        authorization_url, _ = flow.authorization_url(
            access_type="offline", 
            include_granted_scopes="true",
            prompt="consent",  # Force consent screen to get refresh token
            state=session_id  # Use our session_id as the state parameter
        )

        # Save a placeholder record in DynamoDB so polling can start immediately
        placeholder_data = {
            "status": "pending",
            "created_at": None,  # Will be set by save_oauth_tokens
        }
        
        # Save placeholder with a longer TTL (1 hour for the OAuth flow to complete)
        save_oauth_tokens(session_id, placeholder_data, expires_in=3600)

        response_data = {
            "authorization_url": authorization_url,
            "session_id": session_id,
            "redirect_uri": redirect_uri,
        }

        return create_response(200, response_data)

    except Exception as e:
        error_response = {
            "error": "Failed to generate authorization URL",
            "message": str(e),
        }
        return create_response(500, error_response)
