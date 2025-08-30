"""
OAuth polling Lambda function for retrieving stored tokens.
"""

import logging
from typing import Dict, Any
from shared.response_utils import create_response, create_error_response
from shared.token_storage import get_oauth_tokens

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle polling requests for OAuth tokens.

    Args:
        event: API Gateway event containing path parameters
        context: Lambda context object

    Returns:
        API Gateway response with token data or error
    """
    try:
        # Get session ID from path parameters
        path_params = event.get("pathParameters", {})
        session_id = path_params.get("session_id")

        if not session_id:
            return create_error_response(400, "Missing session_id parameter")

        # Retrieve tokens from DynamoDB
        token_data = get_oauth_tokens(session_id)

        if not token_data:
            return create_error_response(404, "Session not found or expired")

        # Check if tokens are still pending
        if token_data.get("status") == "pending":
            return create_response(
                202,
                {
                    "status": "pending",
                    "message": (
                        "Authentication in progress. Please complete the "
                        "OAuth flow in your browser."
                    ),
                },
            )

        # Remove DynamoDB metadata and internal fields
        response_data = {
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_in": token_data.get("expires_in"),
            "expires_at": token_data.get("expires_at"),
            "scope": token_data.get("scope"),
        }

        # Remove None values
        response_data = {k: v for k, v in response_data.items() if v is not None}

        # If we don't have an access_token, it's still pending
        if not response_data.get("access_token"):
            return create_response(
                202,
                {
                    "status": "pending",
                    "message": (
                        "Authentication in progress. Please complete the "
                        "OAuth flow in your browser."
                    ),
                },
            )

        logger.info(f"Successfully retrieved tokens for session {session_id}")
        return create_response(200, response_data)

    except Exception as e:
        logger.error(f"OAuth poll error: {str(e)}")
        return create_error_response(500, f"Internal server error: {str(e)}")
