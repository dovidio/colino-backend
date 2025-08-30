"""
Tests for the auth_poll Lambda function.
"""

import json
import sys
import os
from unittest.mock import Mock, patch

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Mock boto3 before importing modules that use it
with patch("boto3.resource"):
    from lambdas.auth_poll import lambda_handler  # noqa: E402


class TestAuthPoll:
    """Test cases for OAuth polling Lambda."""

    @patch.dict(os.environ, {"OAUTH_SESSIONS_TABLE": "test-table"})
    @patch("shared.token_storage.get_dynamodb_resource")
    def test_auth_poll_pending(self, mock_dynamodb):
        """Test polling with pending status."""
        # Mock DynamoDB table response
        mock_table = Mock()
        mock_table.get_item.return_value = {"Item": {"status": "pending"}}
        mock_dynamodb.return_value.Table.return_value = mock_table

        # Test event
        event = {"pathParameters": {"session_id": "test-session-123"}}
        context = Mock()

        # Call handler
        result = lambda_handler(event, context)

        # Assertions
        assert result["statusCode"] == 202
        body = json.loads(result["body"])
        assert body["status"] == "pending"

    @patch.dict(os.environ, {"OAUTH_SESSIONS_TABLE": "test-table"})
    @patch("shared.token_storage.get_dynamodb_resource")
    def test_auth_poll_success(self, mock_dynamodb):
        """Test polling with successful token retrieval."""
        # Mock DynamoDB table response
        mock_table = Mock()
        mock_table.get_item.return_value = {
            "Item": {
                "access_token": "access_123",
                "refresh_token": "refresh_123",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "youtube.readonly",
            }
        }
        mock_dynamodb.return_value.Table.return_value = mock_table

        # Test event
        event = {"pathParameters": {"session_id": "test-session-123"}}
        context = Mock()

        # Call handler
        result = lambda_handler(event, context)

        # Assertions
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["access_token"] == "access_123"
        assert body["refresh_token"] == "refresh_123"

    @patch.dict(os.environ, {"OAUTH_SESSIONS_TABLE": "test-table"})
    @patch("shared.token_storage.get_dynamodb_resource")
    def test_auth_poll_not_found(self, mock_dynamodb):
        """Test polling with session not found."""
        # Mock DynamoDB table response - no Item
        mock_table = Mock()
        mock_table.get_item.return_value = {}  # No Item key means not found
        mock_dynamodb.return_value.Table.return_value = mock_table

        # Test event
        event = {"pathParameters": {"session_id": "nonexistent-session"}}
        context = Mock()

        # Call handler
        result = lambda_handler(event, context)

        # Assertions
        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert "not found" in body["error"].lower()

    def test_auth_poll_missing_session_id(self):
        """Test polling without session ID."""
        # Test event without session_id
        event = {"pathParameters": {}}
        context = Mock()

        # Call handler
        result = lambda_handler(event, context)

        # Assertions
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "session_id" in body["error"]
