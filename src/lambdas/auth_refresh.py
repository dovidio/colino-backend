"""
OAuth token refresh Lambda function for refreshing Google OAuth access tokens.
"""

import os
import logging
import json
import datetime
import requests
from shared.config import get_oauth_config
from shared.response_utils import create_response, create_error_response

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Refresh OAuth access token using refresh token.

    Args:
        event: API Gateway event containing refresh token in body
        context: Lambda context object

    Returns:
        API Gateway response with new access token
    """
    try:
        # Parse request body
        body = event.get("body", "")
        if not body:
            return create_error_response(400, "Missing request body")

        try:
            request_data = json.loads(body)
        except json.JSONDecodeError:
            return create_error_response(400, "Invalid JSON in request body")

        # Get refresh token from request
        refresh_token = request_data.get("refresh_token")
        if not refresh_token:
            return create_error_response(400, "Missing refresh_token in request body")

        logger.info("Processing token refresh request")

        # Get OAuth configuration
        oauth_config = get_oauth_config()
        client_id = oauth_config["web"]["client_id"]
        client_secret = oauth_config["web"]["client_secret"]

        # Prepare refresh request to Google
        token_url = "https://oauth2.googleapis.com/token"
        refresh_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }

        # Make refresh request to Google
        response = requests.post(
            token_url,
            data=refresh_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if response.status_code != 200:
            logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
            
            # Parse error response if possible
            try:
                error_data = response.json()
                error_msg = error_data.get("error_description", error_data.get("error", "Token refresh failed"))
            except:
                error_msg = f"Token refresh failed with status {response.status_code}"
            
            return create_error_response(400, error_msg)

        # Parse successful response
        token_data = response.json()
        
        # Calculate expiry information
        expires_in = token_data.get("expires_in", 3600)  # Default 1 hour
        expires_at = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)
        expires_timestamp = int(expires_at.timestamp())

        # Prepare response with new token info
        response_data = {
            "message": "Token refreshed successfully",
            "access_token": token_data["access_token"],
            "expires_in": expires_in,
            "expires_at": expires_timestamp,
            "token_type": token_data.get("token_type", "Bearer"),
            "scope": token_data.get("scope", "")
        }

        # Include new refresh token if provided (Google sometimes rotates them)
        if "refresh_token" in token_data:
            response_data["refresh_token"] = token_data["refresh_token"]
            logger.info("New refresh token provided by Google")

        logger.info("Token refresh successful")
        return create_response(200, response_data)

    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return create_error_response(500, f"Internal server error: {str(e)}")
