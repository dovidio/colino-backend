"""
Tests for the authentication Lambda functions.
"""

import json
import sys
import os
from unittest.mock import Mock, patch

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lambdas.auth_initiate import lambda_handler as auth_initiate_handler  # noqa: E402
from lambdas.auth_callback import lambda_handler as auth_callback_handler  # noqa: E402


class TestAuthInitiate:
    """Test cases for OAuth initiation Lambda."""

    @patch.dict(os.environ, {"REDIRECT_URI": "https://example.com/callback"})
    @patch("lambdas.auth_initiate.Flow")
    def test_auth_initiate_success(self, mock_flow):
        """Test successful OAuth initiation."""
        # Mock the Flow
        mock_flow_instance = Mock()
        mock_flow_instance.authorization_url.return_value = (
            "https://accounts.google.com/oauth2/auth?test=true",
            "state123",
        )
        mock_flow.from_client_config.return_value = mock_flow_instance

        # Test event
        event = {}
        context = Mock()

        # Call handler
        result = auth_initiate_handler(event, context)

        # Assertions
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "authorization_url" in body
        assert "state" in body
        assert body["state"] == "state123"

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

    @patch("lambdas.auth_callback.Flow")
    def test_auth_callback_success(self, mock_flow):
        """Test successful OAuth callback."""
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
        with patch.dict(os.environ, {"REDIRECT_URI": "https://example.com/callback"}):
            event = {
                "headers": {"Accept": "application/json"},
                "queryStringParameters": {"code": "auth_code_123", "state": "state123"},
            }
            context = Mock()

            # Call handler
            result = auth_callback_handler(event, context)

            # Assertions
            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["message"] == "Authentication successful"
            assert body["access_token"] == "access_token_123"
            assert body["refresh_token"] == "refresh_token_123"
            assert body["client_id"] == "client_id_123"
            # No more token storage assertions since we're privacy-first

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
