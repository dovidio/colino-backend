"""
YouTube API utilities for fetching user subscriptions and other data.
This module can be used by the command line application.
"""

from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from shared.token_storage import get_tokens


class YouTubeClient:
    """YouTube API client for fetching user data."""

    def __init__(self, user_id: str):
        """
        Initialize YouTube client with user credentials.

        Args:
            user_id: User identifier for token retrieval
        """
        self.user_id = user_id
        self.service = None
        self._initialize_service()

    def _initialize_service(self) -> None:
        """Initialize YouTube API service with stored credentials."""
        token_data = get_tokens(self.user_id)
        if not token_data:
            raise ValueError(f"No tokens found for user: {self.user_id}")

        credentials = Credentials(
            token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes", []),
        )

        self.service = build("youtube", "v3", credentials=credentials)

    def get_subscriptions(self, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch user's YouTube subscriptions.

        Args:
            max_results: Maximum number of subscriptions to fetch

        Returns:
            List of subscription data
        """
        if not self.service:
            raise RuntimeError("YouTube service not initialized")

        subscriptions = []
        next_page_token = None

        while len(subscriptions) < max_results:
            request = self.service.subscriptions().list(
                part="snippet,contentDetails",
                mine=True,
                maxResults=min(50, max_results - len(subscriptions)),
                pageToken=next_page_token,
            )

            response = request.execute()

            for item in response.get("items", []):
                subscription_data = {
                    "id": item["id"],
                    "channel_id": item["snippet"]["resourceId"]["channelId"],
                    "channel_title": item["snippet"]["title"],
                    "description": item["snippet"]["description"],
                    "published_at": item["snippet"]["publishedAt"],
                    "thumbnail_url": item["snippet"]["thumbnails"]["default"]["url"],
                }
                subscriptions.append(subscription_data)

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        return subscriptions

    def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific channel.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Channel information or None
        """
        if not self.service:
            raise RuntimeError("YouTube service not initialized")

        request = self.service.channels().list(part="snippet,statistics", id=channel_id)

        response = request.execute()
        items = response.get("items", [])

        if not items:
            return None

        item = items[0]
        return {
            "id": item["id"],
            "title": item["snippet"]["title"],
            "description": item["snippet"]["description"],
            "published_at": item["snippet"]["publishedAt"],
            "subscriber_count": item["statistics"].get("subscriberCount"),
            "video_count": item["statistics"].get("videoCount"),
            "view_count": item["statistics"].get("viewCount"),
            "thumbnail_url": item["snippet"]["thumbnails"]["default"]["url"],
        }

    def search_channels(
        self, query: str, max_results: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Search for channels by query.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of channel search results
        """
        if not self.service:
            raise RuntimeError("YouTube service not initialized")

        request = self.service.search().list(
            part="snippet", q=query, type="channel", maxResults=max_results
        )

        response = request.execute()

        results = []
        for item in response.get("items", []):
            channel_data = {
                "id": item["id"]["channelId"],
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"],
                "published_at": item["snippet"]["publishedAt"],
                "thumbnail_url": item["snippet"]["thumbnails"]["default"]["url"],
            }
            results.append(channel_data)

        return results
