"""
Tests for the authentication Lambda functions.
"""

import json
import sys
import os
from unittest.mock import Mock, patch

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Mock boto3 before importing modules that use it
with patch("boto3.resource"):
    from lambdas.auth_initiate import (  # noqa: E402
        lambda_handler as auth_initiate_handler,
    )
    from lambdas.auth_callback import (  # noqa: E402
        lambda_handler as auth_callback_handler,
    )


class TestAuthInitiate:
    """Test cases for OAuth initiation Lambda."""

    @patch.dict(os.environ, {"OAUTH_SESSIONS_TABLE": "test-table"})
    @patch("shared.token_storage.get_dynamodb_resource")
    @patch("lambdas.auth_initiate.Flow")
    def test_auth_initiate_success(self, mock_flow, mock_dynamodb):
        """Test successful OAuth initiation."""
        # Mock DynamoDB table response
        mock_table = Mock()
        mock_table.put_item.return_value = {}
        mock_dynamodb.return_value.Table.return_value = mock_table

        # Mock the Flow
        mock_flow_instance = Mock()
        mock_flow_instance.authorization_url.return_value = (
            "https://accounts.google.com/oauth2/auth?test=true",
            "state123",
        )
        mock_flow.from_client_config.return_value = mock_flow_instance

        # Test event
        event = {"headers": {"Host": "api.example.com"}}
        context = Mock()

        # Call handler
        result = auth_initiate_handler(event, context)

        # Assertions
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "authorization_url" in body
        assert "session_id" in body  # Now returns session_id instead of state
        # Remove the old test assertion that checks for 'state'
        # The API now returns 'session_id' instead

    @patch("lambdas.auth_initiate.Flow")
    def test_auth_initiate_error(self, mock_flow):
        """Test OAuth initiation error handling."""
        # Mock Flow to raise exception
        mock_flow.from_client_config.side_effect = Exception("Config error")

        # Test event
        event = {}
        context = Mock()

        # Call handler
        result = auth_initiate_handler(event, context)

        # Assertions
        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "error" in body


class TestAuthCallback:
    """Test cases for OAuth callback Lambda."""

    @patch.dict(os.environ, {"OAUTH_SESSIONS_TABLE": "test-table"})
    @patch("shared.token_storage.get_dynamodb_resource")
    @patch("lambdas.auth_callback.Flow")
    def test_auth_callback_success(self, mock_flow, mock_dynamodb):
        """Test successful OAuth callback."""
        # Mock DynamoDB table response
        mock_table = Mock()
        mock_table.put_item.return_value = {}
        mock_dynamodb.return_value.Table.return_value = mock_table

        # Mock credentials
        mock_credentials = Mock()
        mock_credentials.token = "access_token_123"
        mock_credentials.refresh_token = "refresh_token_123"
        mock_credentials.token_uri = "https://oauth2.googleapis.com/token"
        mock_credentials.client_id = "client_id_123"
        mock_credentials.client_secret = "client_secret_123"
        mock_credentials.scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        mock_credentials.expiry = None

        # Mock the Flow
        mock_flow_instance = Mock()
        mock_flow_instance.credentials = mock_credentials
        mock_flow.from_client_config.return_value = mock_flow_instance

        # Test event with environment variable mock
        event = {
            "headers": {"Host": "api.example.com"},
            "queryStringParameters": {"code": "auth_code_123", "state": "state123"},
        }
        context = Mock()

        # Call handler
        result = auth_callback_handler(event, context)

        # Assertions
        assert result["statusCode"] == 200
        assert result["headers"]["Content-Type"] == "text/html"
        assert "Authentication Successful!" in result["body"]
        assert "state123" in result["body"]  # Session ID should be in HTML

        # Verify DynamoDB put was called
        mock_table.put_item.assert_called_once()

    def test_auth_callback_missing_code(self):
        """Test callback with missing authorization code."""
        # Test event without code
        event = {"queryStringParameters": {"state": "state123"}}
        context = Mock()

        # Call handler
        result = auth_callback_handler(event, context)

        # Assertions
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body

    def test_auth_callback_oauth_error(self):
        """Test callback with OAuth error."""
        # Test event with OAuth error
        event = {
            "queryStringParameters": {"error": "access_denied", "state": "state123"}
        }
        context = Mock()

        # Call handler
        result = auth_callback_handler(event, context)

        # Assertions
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "OAuth error" in body["error"]
