"""Slack tools module.

WHY: Provides CLI-accessible bulk operations for Slack APIs.
Bypasses MCP protocol overhead for batch processing.

USAGE:
    claude-mpm tools slack <action> [options]

ACTIONS:
    channels-list       - List all channels (public and private)
    messages-export     - Export messages from a channel
"""

from typing import Any, Optional

import requests

from claude_mpm.tools import register_service
from claude_mpm.tools.base import BaseToolModule, ToolResult


class SlackTools(BaseToolModule):
    """Slack bulk operations tool module."""

    def get_service_name(self) -> str:
        """Return service name."""
        return "slack"

    def get_actions(self) -> list[str]:
        """Return list of available actions."""
        return [
            "channels-list",
            "messages-export",
        ]

    def get_action_help(self, action: str) -> str:
        """Return help text for specific action."""
        help_texts = {
            "channels-list": "List all channels (public and private) in the workspace",
            "messages-export": "Export messages from a channel to JSON",
        }
        return help_texts.get(action, "No help available")

    def _get_valid_token(self, service: str = "slack-user-proxy") -> str:
        """Get valid access token.

        Args:
            service: Service name for token lookup

        Returns:
            Valid access token

        Raises:
            ValueError: If no token found or token is expired
        """
        stored = self.storage.retrieve(service)
        if not stored:
            raise ValueError(
                f"No token found for {service}. Run 'claude-mpm setup oauth slack' first."
            )

        # Slack user tokens are typically long-lived
        # Check expiration if present
        if stored.token.is_expired():
            raise ValueError(
                f"Token for {service} is expired. Run 'claude-mpm setup oauth slack' to re-authenticate."
            )

        return stored.token.access_token

    def _make_request(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
        service: str = "slack-user-proxy",
    ) -> dict[str, Any]:
        """Make authenticated Slack API request.

        Args:
            endpoint: Slack API endpoint (e.g., 'conversations.list')
            params: Query parameters
            json_data: JSON body for POST
            service: Service name for token

        Returns:
            Response JSON

        Raises:
            ValueError: If request fails
        """
        token = self._get_valid_token(service)
        url = f"https://slack.com/api/{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

        try:
            if json_data:
                response = requests.post(
                    url, headers=headers, json=json_data, timeout=30
                )
            else:
                response = requests.get(url, headers=headers, params=params, timeout=30)

            response.raise_for_status()
            result = response.json()

            # Slack returns ok: false on error, not HTTP status codes
            if not result.get("ok", False):
                error_msg = result.get("error", "Unknown error")
                raise ValueError(f"Slack API error: {error_msg}")

            return result

        except requests.exceptions.HTTPError as e:
            raise ValueError(
                f"API request failed: {e.response.status_code} {e.response.text}"
            ) from e
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Request error: {e}") from e

    def execute(self, action: str, **kwargs) -> ToolResult:
        """Execute Slack action.

        Args:
            action: Action name
            **kwargs: Action-specific arguments

        Returns:
            ToolResult with operation results
        """
        # Validate action
        self.validate_action(action)

        # Route to action handler
        if action == "channels-list":
            return self._channels_list(**kwargs)
        if action == "messages-export":
            return self._messages_export(**kwargs)

        return ToolResult(
            success=False,
            action=action,
            error=f"Action {action} not implemented yet",
        )

    def _channels_list(self, **kwargs) -> ToolResult:
        """List all channels in the workspace.

        Args:
            include_private: Include private channels (default: True)
            limit: Maximum number of channels per type (default: 1000)

        Returns:
            ToolResult with channel list
        """
        include_private = kwargs.get("include_private", True)
        limit = int(kwargs.get("limit", 1000))

        try:
            channels = []

            # Get public channels
            cursor = None
            while True:
                params: dict[str, Any] = {
                    "types": "public_channel",
                    "limit": min(limit - len(channels), 1000),
                    "exclude_archived": False,
                }
                if cursor:
                    params["cursor"] = cursor

                result = self._make_request("conversations.list", params=params)
                channels.extend(result.get("channels", []))

                cursor = result.get("response_metadata", {}).get("next_cursor")
                if not cursor or len(channels) >= limit:
                    break

            # Get private channels if requested
            if include_private:
                cursor = None
                while len(channels) < limit:
                    params = {
                        "types": "private_channel",
                        "limit": min(limit - len(channels), 1000),
                        "exclude_archived": False,
                    }
                    if cursor:
                        params["cursor"] = cursor

                    result = self._make_request("conversations.list", params=params)
                    channels.extend(result.get("channels", []))

                    cursor = result.get("response_metadata", {}).get("next_cursor")
                    if not cursor:
                        break

            # Format channel data
            formatted_channels = []
            for channel in channels:
                formatted_channels.append(
                    {
                        "id": channel.get("id"),
                        "name": channel.get("name"),
                        "is_private": channel.get("is_private", False),
                        "is_archived": channel.get("is_archived", False),
                        "num_members": channel.get("num_members", 0),
                        "topic": channel.get("topic", {}).get("value", ""),
                        "purpose": channel.get("purpose", {}).get("value", ""),
                    }
                )

            return ToolResult(
                success=True,
                action="channels-list",
                data={"channels": formatted_channels},
                metadata={"count": len(formatted_channels)},
            )

        except ValueError as e:
            return ToolResult(
                success=False,
                action="channels-list",
                error=str(e),
            )
        except Exception as e:
            return ToolResult(
                success=False,
                action="channels-list",
                error=f"Unexpected error: {e}",
            )

    def _messages_export(self, **kwargs) -> ToolResult:
        """Export messages from a channel.

        Args:
            channel: Channel ID (required)
            limit: Maximum number of messages to export (default: 1000)
            oldest: Oldest message timestamp (optional, UNIX timestamp)
            latest: Latest message timestamp (optional, UNIX timestamp)

        Returns:
            ToolResult with exported messages
        """
        channel = kwargs.get("channel")
        limit = int(kwargs.get("limit", 1000))
        oldest = kwargs.get("oldest")
        latest = kwargs.get("latest")

        if not channel:
            return ToolResult(
                success=False,
                action="messages-export",
                error="Required parameter 'channel' not provided",
            )

        try:
            messages = []
            cursor = None

            while len(messages) < limit:
                params: dict[str, Any] = {
                    "channel": channel,
                    "limit": min(limit - len(messages), 1000),
                }
                if oldest:
                    params["oldest"] = oldest
                if latest:
                    params["latest"] = latest
                if cursor:
                    params["cursor"] = cursor

                result = self._make_request("conversations.history", params=params)
                batch_messages = result.get("messages", [])

                if not batch_messages:
                    break

                messages.extend(batch_messages)

                # Check for more messages
                cursor = result.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break

            # Format messages
            formatted_messages = []
            for msg in messages:
                formatted_messages.append(
                    {
                        "type": msg.get("type"),
                        "user": msg.get("user"),
                        "text": msg.get("text"),
                        "ts": msg.get("ts"),
                        "thread_ts": msg.get("thread_ts"),
                        "reply_count": msg.get("reply_count", 0),
                        "reactions": msg.get("reactions", []),
                    }
                )

            return ToolResult(
                success=True,
                action="messages-export",
                data={
                    "messages": formatted_messages,
                    "channel": channel,
                },
                metadata={
                    "count": len(formatted_messages),
                    "limit": limit,
                },
            )

        except ValueError as e:
            return ToolResult(
                success=False,
                action="messages-export",
                error=str(e),
            )
        except Exception as e:
            return ToolResult(
                success=False,
                action="messages-export",
                error=f"Unexpected error: {e}",
            )


# Register this service
register_service("slack", SlackTools)
