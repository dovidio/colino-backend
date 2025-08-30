"""
Test cases for the OAuth token refresh Lambda function.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from src.lambdas.auth_refresh import lambda_handler


class TestAuthRefresh:
    """Test cases for the auth refresh Lambda function."""

    def test_missing_body(self):
        """Test handling of missing request body."""
        event = {}
        context = {}
        
        response = lambda_handler(event, context)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Missing request body" in body["error"]

    def test_invalid_json(self):
        """Test handling of invalid JSON in request body."""
        event = {"body": "invalid json"}
        context = {}
        
        response = lambda_handler(event, context)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Invalid JSON" in body["error"]

    def test_missing_refresh_token(self):
        """Test handling of missing refresh_token in request."""
        event = {"body": json.dumps({"other_field": "value"})}
        context = {}
        
        response = lambda_handler(event, context)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Missing refresh_token" in body["error"]

    @patch('src.lambdas.auth_refresh.get_oauth_config')
    @patch('src.lambdas.auth_refresh.requests.post')
    def test_successful_refresh(self, mock_post, mock_config):
        """Test successful token refresh."""
        # Mock OAuth config
        mock_config.return_value = {
            "web": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret"
            }
        }
        
        # Mock successful Google response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "test_scope"
        }
        mock_post.return_value = mock_response
        
        event = {
            "body": json.dumps({"refresh_token": "test_refresh_token"})
        }
        context = {}
        
        response = lambda_handler(event, context)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["access_token"] == "new_access_token"
        assert body["expires_in"] == 3600
        assert body["token_type"] == "Bearer"
        assert "expires_at" in body

    @patch('src.lambdas.auth_refresh.get_oauth_config')
    @patch('src.lambdas.auth_refresh.requests.post')
    def test_google_error_response(self, mock_post, mock_config):
        """Test handling of error response from Google."""
        # Mock OAuth config
        mock_config.return_value = {
            "web": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret"
            }
        }
        
        # Mock error response from Google
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Token has been expired or revoked."
        }
        mock_post.return_value = mock_response
        
        event = {
            "body": json.dumps({"refresh_token": "invalid_refresh_token"})
        }
        context = {}
        
        response = lambda_handler(event, context)
        
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "Token has been expired or revoked" in body["error"]

    @patch('src.lambdas.auth_refresh.get_oauth_config')
    @patch('src.lambdas.auth_refresh.requests.post')
    def test_refresh_with_new_refresh_token(self, mock_post, mock_config):
        """Test refresh response that includes a new refresh token."""
        # Mock OAuth config
        mock_config.return_value = {
            "web": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret"
            }
        }
        
        # Mock Google response with new refresh token
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "test_scope"
        }
        mock_post.return_value = mock_response
        
        event = {
            "body": json.dumps({"refresh_token": "test_refresh_token"})
        }
        context = {}
        
        response = lambda_handler(event, context)
        
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["access_token"] == "new_access_token"
        assert body["refresh_token"] == "new_refresh_token"
