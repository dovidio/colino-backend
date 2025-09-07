"""
DynamoDB utilities for storing and retrieving OAuth tokens.
"""

import logging
import os
import time
from typing import Any, Optional

import boto3  # type: ignore

logger = logging.getLogger()

# DynamoDB client will be initialized lazily
_dynamodb = None


def get_dynamodb_resource():
    """Get DynamoDB resource with lazy initialization."""
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb")
    return _dynamodb


def get_oauth_sessions_table():
    """Get the OAuth sessions DynamoDB table."""
    table_name = os.environ.get("OAUTH_SESSIONS_TABLE")
    if not table_name:
        raise ValueError("OAUTH_SESSIONS_TABLE environment variable not set")
    return get_dynamodb_resource().Table(table_name)


def save_oauth_tokens(
    session_id: str, tokens: dict[str, Any], expires_in: int = 600
) -> bool:
    """
    Save OAuth tokens to DynamoDB.

    Args:
        session_id: Unique session identifier
        tokens: Dictionary containing token information
        expires_in: Session expiration time in seconds (default 10 minutes)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        table = get_oauth_sessions_table()

        # Calculate TTL based on the provided expires_in parameter
        # This allows different TTL values for different use cases:
        # - Pending sessions: short TTL (15-30 minutes)
        # - Completed sessions: longer TTL (1-2 hours) or immediate cleanup
        ttl = int(time.time() + expires_in)

        # Prepare item for DynamoDB
        item = {
            "session_id": session_id,
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "token_type": tokens.get("token_type", "Bearer"),
            "expires_in": expires_in,
            "expires_at": tokens.get("expires_at"),
            "scope": tokens.get("scope"),
            "status": tokens.get("status", "completed"),
            "created_at": int(time.time()),
            "ttl": ttl,
        }

        # Remove None values
        item = {k: v for k, v in item.items() if v is not None}

        table.put_item(Item=item)
        logger.info(f"Successfully saved tokens for session {session_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to save tokens for session {session_id}: {str(e)}")
        return False


def get_oauth_tokens(session_id: str) -> Optional[dict[str, Any]]:
    """
    Retrieve OAuth tokens from DynamoDB.

    Args:
        session_id: Unique session identifier

    Returns:
        Dictionary containing token information or None if not found
    """
    try:
        table = get_oauth_sessions_table()

        response = table.get_item(Key={"session_id": session_id})

        if "Item" in response:
            logger.info(f"Successfully retrieved tokens for session {session_id}")
            return response["Item"]
        else:
            logger.warning(f"No tokens found for session {session_id}")
            return None

    except Exception as e:
        logger.error(f"Failed to retrieve tokens for session {session_id}: {str(e)}")
        return None


def delete_oauth_tokens(session_id: str) -> bool:
    """
    Delete OAuth tokens from DynamoDB.

    Args:
        session_id: Unique session identifier

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        table = get_oauth_sessions_table()

        table.delete_item(Key={"session_id": session_id})
        logger.info(f"Successfully deleted tokens for session {session_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete tokens for session {session_id}: {str(e)}")
        return False
