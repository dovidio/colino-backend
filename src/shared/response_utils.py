"""
Utility functions for creating API Gateway responses.
"""

import json
from typing import Any, Optional

from shared.config import ALLOWED_ORIGINS


def create_response(
    status_code: int, body: dict[str, Any], headers: Optional[dict[str, str]] = None
) -> dict[str, Any]:
    """
    Create a standardized API Gateway response.

    Args:
        status_code: HTTP status code
        body: Response body data
        headers: Additional headers

    Returns:
        Formatted API Gateway response
    """
    default_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",  # Configure based on your needs
        "Access-Control-Allow-Headers": (
            "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
        ),
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    }

    if headers:
        default_headers.update(headers)

    return {
        "statusCode": status_code,
        "headers": default_headers,
        "body": json.dumps(body, default=str),
    }


def create_cors_headers(origin: Optional[str] = None) -> dict[str, str]:
    """
    Create CORS headers based on allowed origins.

    Args:
        origin: Request origin

    Returns:
        CORS headers
    """
    if origin and origin in ALLOWED_ORIGINS:
        return {"Access-Control-Allow-Origin": origin}
    return {
        "Access-Control-Allow-Origin": ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "*"
    }


def create_error_response(status_code: int, message: str) -> dict[str, Any]:
    """
    Create a standardized error response.

    Args:
        status_code: HTTP status code
        message: Error message

    Returns:
        Formatted API Gateway error response
    """
    return create_response(status_code, {"error": message})
