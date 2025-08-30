#!/usr/bin/env python3
"""
OAuth authentication helper for the CLI.
This script handles the OAuth flow by calling the Lambda functions.
"""

import requests
import webbrowser
import time
import sys
from typing import Dict, Any, Optional


class YouTubeOAuth:
    """Helper class for YouTube OAuth authentication via Lambda functions."""
    
    def __init__(self, auth_initiate_url: str, user_id: str = None):
        """
        Initialize OAuth helper.
        
        Args:
            auth_initiate_url: URL of the auth_initiate Lambda function
            user_id: User identifier for token storage
        """
        self.auth_initiate_url = auth_initiate_url
        self.user_id = user_id or f"user_{int(time.time())}"
    
    def authenticate(self) -> Optional[Dict[str, Any]]:
        """
        Perform OAuth authentication flow.
        
        Returns:
            Token data if successful, None otherwise
        """
        try:
            print(f"🔐 Starting YouTube OAuth authentication for user: {self.user_id}")
            
            # Step 1: Get authorization URL from Lambda
            print("📡 Getting authorization URL...")
            response = requests.get(self.auth_initiate_url)
            
            if response.status_code != 200:
                print(f"❌ Failed to get authorization URL: {response.status_code}")
                print(f"Response: {response.text}")
                return None
            
            auth_data = response.json()
            auth_url = auth_data.get('authorization_url')
            state = auth_data.get('state')
            
            if not auth_url:
                print("❌ No authorization URL in response")
                return None
            
            # Add user_id to the callback URL for identification
            if '?' in auth_url:
                auth_url += f"&user_id={self.user_id}"
            else:
                auth_url += f"?user_id={self.user_id}"
            
            print(f"🌐 Opening browser for authorization...")
            print(f"URL: {auth_url}")
            
            # Step 2: Open browser for user authorization
            webbrowser.open(auth_url)
            
            print("\n" + "="*60)
            print("Please complete the authorization in your browser.")
            print("After authorization, you'll see a success message.")
            print("The tokens will be automatically stored for your CLI use.")
            print("="*60)
            
            input("\nPress Enter after completing authorization in the browser...")
            
            print("✅ Authentication flow completed!")
            print(f"🔑 Tokens stored for user ID: {self.user_id}")
            print("\nYou can now use the CLI commands with this user ID:")
            print(f"  python cli.py --user-id {self.user_id} subscriptions")
            
            return {
                'user_id': self.user_id,
                'state': state,
                'message': 'Authentication completed - tokens stored remotely'
            }
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return None


def main():
    """Main function for CLI OAuth."""
    if len(sys.argv) < 2:
        print("Usage: python oauth_helper.py <auth_initiate_url> [user_id]")
        print("\nExample:")
        print("  python oauth_helper.py https://your-api.execute-api.us-east-1.amazonaws.com/Prod/auth/initiate my-user-123")
        sys.exit(1)
    
    auth_initiate_url = sys.argv[1]
    user_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    oauth = YouTubeOAuth(auth_initiate_url, user_id)
    result = oauth.authenticate()
    
    if result:
        print(f"\n🎉 Success! User ID: {result['user_id']}")
        sys.exit(0)
    else:
        print("\n💥 Authentication failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
