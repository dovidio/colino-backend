#!/usr/bin/env python3
"""
Command-line interface for accessing YouTube data using stored OAuth tokens.
"""

import argparse
import json
import sys
from typing import List, Dict, Any
from src.shared.youtube_client import YouTubeClient
from src.shared.token_storage import get_tokens


def print_subscriptions(subscriptions: List[Dict[str, Any]]) -> None:
    """Print subscription data in a formatted way."""
    print(f"\nFound {len(subscriptions)} subscriptions:\n")
    print("-" * 80)

    for i, sub in enumerate(subscriptions, 1):
        print(f"{i:3d}. {sub['channel_title']}")
        print(f"     Channel ID: {sub['channel_id']}")
        print(f"     Subscribed: {sub['published_at']}")
        if sub["description"]:
            desc = (
                sub["description"][:100] + "..."
                if len(sub["description"]) > 100
                else sub["description"]
            )
            print(f"     Description: {desc}")
        print()


def print_channels(channels: List[Dict[str, Any]]) -> None:
    """Print channel search results."""
    print(f"\nFound {len(channels)} channels:\n")
    print("-" * 80)

    for i, channel in enumerate(channels, 1):
        print(f"{i:3d}. {channel['title']}")
        print(f"     Channel ID: {channel['id']}")
        print(f"     Created: {channel['published_at']}")
        if channel["description"]:
            desc = (
                channel["description"][:100] + "..."
                if len(channel["description"]) > 100
                else channel["description"]
            )
            print(f"     Description: {desc}")
        print()


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="YouTube CLI - Access YouTube data using stored OAuth tokens"
    )

    parser.add_argument("--user-id", required=True, help="User ID for token retrieval")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Subscriptions command
    subs_parser = subparsers.add_parser("subscriptions", help="Get user subscriptions")
    subs_parser.add_argument(
        "--max-results",
        type=int,
        default=50,
        help="Maximum number of subscriptions to fetch (default: 50)",
    )
    subs_parser.add_argument(
        "--output",
        choices=["json", "table"],
        default="table",
        help="Output format (default: table)",
    )

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for channels")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "--max-results",
        type=int,
        default=25,
        help="Maximum number of results (default: 25)",
    )
    search_parser.add_argument(
        "--output",
        choices=["json", "table"],
        default="table",
        help="Output format (default: table)",
    )

    # Channel info command
    info_parser = subparsers.add_parser(
        "channel-info", help="Get information about a specific channel"
    )
    info_parser.add_argument("channel_id", help="YouTube channel ID")

    # Status command
    status_parser = subparsers.add_parser("status", help="Check authentication status")

    # Auth command
    auth_parser = subparsers.add_parser("auth", help="Authenticate with YouTube API")
    auth_parser.add_argument(
        "--auth-url", required=True, help="URL of the auth_initiate Lambda function"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "auth":
            # Import here to avoid dependency issues if requests not installed
            try:
                import requests
                import webbrowser
            except ImportError:
                print("❌ Missing dependencies. Install with: pip install requests")
                return 1

            # Perform OAuth authentication
            print(f"🔐 Starting YouTube OAuth authentication for user: {args.user_id}")

            # Get authorization URL from Lambda
            print("📡 Getting authorization URL...")
            response = requests.get(args.auth_url)

            if response.status_code != 200:
                print(f"❌ Failed to get authorization URL: {response.status_code}")
                print(f"Response: {response.text}")
                return 1

            auth_data = response.json()
            auth_url = auth_data.get("authorization_url")

            if not auth_url:
                print("❌ No authorization URL in response")
                return 1

            # Add user_id to the callback URL for identification
            separator = "&" if "?" in auth_url else "?"
            auth_url += f"{separator}user_id={args.user_id}"

            print(f"🌐 Opening browser for authorization...")
            print(f"URL: {auth_url}")

            # Open browser for user authorization
            webbrowser.open(auth_url)

            print("\n" + "=" * 60)
            print("Please complete the authorization in your browser.")
            print("After authorization, you'll see a success message.")
            print("The tokens will be automatically stored for your CLI use.")
            print("=" * 60)

            input("\nPress Enter after completing authorization in the browser...")

            print("✅ Authentication flow completed!")
            print(f"🔑 Tokens stored for user ID: {args.user_id}")
            print("\nYou can now use other CLI commands:")
            print(f"  python cli.py --user-id {args.user_id} status")
            print(f"  python cli.py --user-id {args.user_id} subscriptions")
            return 0

        elif args.command == "status":
            # Check if tokens exist
            tokens = get_tokens(args.user_id)
            if tokens:
                print(f"✓ Tokens found for user: {args.user_id}")
                print(f"  Access token: {tokens['access_token'][:20]}...")
                print(f"  Scopes: {', '.join(tokens.get('scopes', []))}")
                if tokens.get("expiry"):
                    print(f"  Expires: {tokens['expiry']}")
            else:
                print(f"✗ No tokens found for user: {args.user_id}")
                print("Run the OAuth flow first to authenticate.")
                return 1
            return 0

        # Initialize YouTube client
        try:
            client = YouTubeClient(args.user_id)
        except ValueError as e:
            print(f"Error: {e}")
            print("Run the OAuth flow first to authenticate.")
            return 1

        if args.command == "subscriptions":
            subscriptions = client.get_subscriptions(args.max_results)

            if args.output == "json":
                print(json.dumps(subscriptions, indent=2))
            else:
                print_subscriptions(subscriptions)

        elif args.command == "search":
            channels = client.search_channels(args.query, args.max_results)

            if args.output == "json":
                print(json.dumps(channels, indent=2))
            else:
                print_channels(channels)

        elif args.command == "channel-info":
            channel_info = client.get_channel_info(args.channel_id)

            if channel_info:
                print(json.dumps(channel_info, indent=2))
            else:
                print(f"Channel not found: {args.channel_id}")
                return 1

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
