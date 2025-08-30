"""
Token storage utilities for managing OAuth tokens.
Supports both DynamoDB and local file storage for development.
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
import boto3
from shared.config import AWS_REGION, DYNAMODB_TABLE_NAME


class TokenStorage:
    """Handle token storage operations."""

    def __init__(self):
        self.use_dynamodb = os.environ.get("USE_DYNAMODB", "true").lower() == "true"
        if self.use_dynamodb:
            self.dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
            self.table = self.dynamodb.Table(DYNAMODB_TABLE_NAME)

    def store_tokens(self, user_id: str, token_data: Dict[str, Any]) -> bool:
        """
        Store tokens for a user.

        Args:
            user_id: Unique user identifier
            token_data: Token information

        Returns:
            Success status
        """
        try:
            token_data["user_id"] = user_id
            token_data["updated_at"] = datetime.utcnow().isoformat()

            if self.use_dynamodb:
                self.table.put_item(Item=token_data)
            else:
                # Local file storage for development
                self._store_local(user_id, token_data)

            return True
        except Exception as e:
            print(f"Error storing tokens: {str(e)}")
            return False

    def get_tokens(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve tokens for a user.

        Args:
            user_id: Unique user identifier

        Returns:
            Token data or None
        """
        try:
            if self.use_dynamodb:
                response = self.table.get_item(Key={"user_id": user_id})
                return response.get("Item")
            else:
                return self._get_local(user_id)
        except Exception as e:
            print(f"Error retrieving tokens: {str(e)}")
            return None

    def _store_local(self, user_id: str, token_data: Dict[str, Any]) -> None:
        """Store tokens locally for development."""
        os.makedirs("/tmp/tokens", exist_ok=True)
        with open(f"/tmp/tokens/{user_id}.json", "w") as f:
            json.dump(token_data, f, indent=2)

    def _get_local(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve tokens from local storage."""
        try:
            with open(f"/tmp/tokens/{user_id}.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return None


# Global instance
_token_storage = TokenStorage()


def store_tokens(user_id: str, token_data: Dict[str, Any]) -> bool:
    """Store tokens for a user."""
    return _token_storage.store_tokens(user_id, token_data)


def get_tokens(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve tokens for a user."""
    return _token_storage.get_tokens(user_id)
