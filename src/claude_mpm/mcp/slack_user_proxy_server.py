"""Slack User Proxy MCP server integrated with claude-mpm OAuth storage.

This MCP server provides tools for interacting with Slack APIs using
user tokens managed by claude-mpm's TokenStorage system.

The server acts on behalf of the authenticated user, providing access
to channels, messages, and workspace features.
"""

import asyncio
import json
import logging
from typing import Any, Optional

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from claude_mpm.auth import OAuthManager, TokenStatus, TokenStorage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service name for token storage - matches slack-user-proxy convention
SERVICE_NAME = "slack-user-proxy"

# Slack API base URL
SLACK_API_BASE = "https://slack.com/api"


class SlackUserProxyServer:
    """MCP server for Slack APIs using user tokens.

    Integrates with claude-mpm's TokenStorage for credential management
    and provides tools for channel access, message history, and messaging.

    Attributes:
        server: MCP Server instance.
        storage: TokenStorage for retrieving OAuth tokens.
        manager: OAuthManager for token refresh operations.
    """

    def __init__(self) -> None:
        """Initialize the Slack User Proxy MCP server."""
        self.server = Server("slack-user-proxy")
        self.storage = TokenStorage()
        self.manager = OAuthManager(storage=self.storage)
        self._setup_handlers()

    async def _get_access_token(self) -> str:
        """Get a valid access token.

        Note: Slack user tokens are typically long-lived and don't expire
        unless explicitly revoked. Refresh is attempted if configured.

        Returns:
            Valid access token string.

        Raises:
            RuntimeError: If no token is available or refresh fails.
        """
        status = self.storage.get_status(SERVICE_NAME)

        if status == TokenStatus.MISSING:
            raise RuntimeError(
                f"No OAuth token found for service '{SERVICE_NAME}'. "
                "Please authenticate first using: claude-mpm auth login slack"
            )

        if status == TokenStatus.INVALID:
            raise RuntimeError(
                f"OAuth token for service '{SERVICE_NAME}' is invalid or corrupted. "
                "Please re-authenticate using: claude-mpm auth login slack"
            )

        # Try to refresh if expired (though Slack tokens are typically long-lived)
        if status == TokenStatus.EXPIRED:
            logger.info("Token expired, attempting refresh...")
            token = await self.manager.refresh_if_needed(SERVICE_NAME)
            if token is None:
                raise RuntimeError(
                    "Token refresh failed. Please re-authenticate using: "
                    "claude-mpm auth login slack"
                )
            return token.access_token

        # Token is valid
        stored = self.storage.retrieve(SERVICE_NAME)
        if stored is None:
            raise RuntimeError("Unexpected error: token retrieval failed")

        return stored.token.access_token

    async def _slack_api(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make an authenticated request to Slack API.

        Slack API always returns HTTP 200 with ok: true/false in response.
        This method handles that pattern and raises on errors.

        Args:
            method: HTTP method (GET, POST).
            endpoint: Slack API endpoint (e.g., 'conversations.list').
            params: Optional query parameters.
            json_data: Optional JSON body data (for POST).

        Returns:
            JSON response as a dictionary.

        Raises:
            RuntimeError: If the Slack API returns an error.
        """
        access_token = await self._get_access_token()
        url = f"{SLACK_API_BASE}/{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                timeout=30.0,
            )
            result: dict[str, Any] = response.json()

            # Slack returns ok: false on error, not HTTP status codes
            if not result.get("ok", False):
                error_msg = result.get("error", "Unknown error")
                raise RuntimeError(f"Slack API error: {error_msg}")

            return result

    def _setup_handlers(self) -> None:
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """Return list of available tools."""
            return [
                Tool(
                    name="list_channels",
                    description="List public channels in the workspace",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of channels to return (default: 100, max: 1000)",
                                "default": 100,
                            },
                            "cursor": {
                                "type": "string",
                                "description": "Pagination cursor for next page of results",
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="list_private_channels",
                    description="List private channels the user is a member of",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of channels to return (default: 100, max: 1000)",
                                "default": 100,
                            },
                            "cursor": {
                                "type": "string",
                                "description": "Pagination cursor for next page of results",
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="get_channel_history",
                    description="Get message history from a channel",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "channel": {
                                "type": "string",
                                "description": "Channel ID (e.g., 'C1234567890')",  # pragma: allowlist secret
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of messages to return (default: 100, max: 1000)",
                                "default": 100,
                            },
                            "oldest": {
                                "type": "string",
                                "description": "Only messages after this Unix timestamp",
                            },
                            "latest": {
                                "type": "string",
                                "description": "Only messages before this Unix timestamp",
                            },
                            "cursor": {
                                "type": "string",
                                "description": "Pagination cursor for next page of results",
                            },
                        },
                        "required": ["channel"],
                    },
                ),
                Tool(
                    name="send_message",
                    description="Send a message to a channel as the authenticated user",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "channel": {
                                "type": "string",
                                "description": "Channel ID to send message to (e.g., 'C1234567890')",  # pragma: allowlist secret
                            },
                            "text": {
                                "type": "string",
                                "description": "Message text (supports Slack mrkdwn formatting)",
                            },
                            "thread_ts": {
                                "type": "string",
                                "description": "Thread timestamp to reply to (for threaded messages)",
                            },
                        },
                        "required": ["channel", "text"],
                    },
                ),
                # Direct Messages
                Tool(
                    name="list_direct_messages",
                    description="List direct message conversations (1:1 DMs) the user has",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of DMs to return (default: 100, max: 1000)",
                                "default": 100,
                            },
                            "cursor": {
                                "type": "string",
                                "description": "Pagination cursor for next page of results",
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="list_group_dms",
                    description="List multi-party direct message conversations (group DMs)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of group DMs to return (default: 100, max: 1000)",
                                "default": 100,
                            },
                            "cursor": {
                                "type": "string",
                                "description": "Pagination cursor for next page of results",
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="get_dm_history",
                    description="Get message history from a direct message conversation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "channel": {
                                "type": "string",
                                "description": "DM channel ID (e.g., 'D1234567890')",  # pragma: allowlist secret
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of messages to return (default: 100, max: 1000)",
                                "default": 100,
                            },
                            "oldest": {
                                "type": "string",
                                "description": "Only messages after this Unix timestamp",
                            },
                            "latest": {
                                "type": "string",
                                "description": "Only messages before this Unix timestamp",
                            },
                            "cursor": {
                                "type": "string",
                                "description": "Pagination cursor for next page of results",
                            },
                        },
                        "required": ["channel"],
                    },
                ),
                Tool(
                    name="reply_to_thread",
                    description="Reply to a specific message thread",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "channel": {
                                "type": "string",
                                "description": "Channel ID where the thread exists",
                            },
                            "thread_ts": {
                                "type": "string",
                                "description": "Timestamp of the parent message to reply to",
                            },
                            "text": {
                                "type": "string",
                                "description": "Reply message text (supports Slack mrkdwn formatting)",
                            },
                            "broadcast": {
                                "type": "boolean",
                                "description": "Also post the reply to the channel (default: false)",
                                "default": False,
                            },
                        },
                        "required": ["channel", "thread_ts", "text"],
                    },
                ),
                # User & Workspace
                Tool(
                    name="get_user_info",
                    description="Get detailed information about a user",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "user": {
                                "type": "string",
                                "description": "User ID (e.g., 'U1234567890')",  # pragma: allowlist secret
                            },
                        },
                        "required": ["user"],
                    },
                ),
                Tool(
                    name="list_users",
                    description="List all users in the workspace",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of users to return (default: 100, max: 1000)",
                                "default": 100,
                            },
                            "cursor": {
                                "type": "string",
                                "description": "Pagination cursor for next page of results",
                            },
                            "include_locale": {
                                "type": "boolean",
                                "description": "Include locale information for users (default: false)",
                                "default": False,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="get_workspace_info",
                    description="Get information about the current workspace/team",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                # Search
                Tool(
                    name="search_messages",
                    description="Search for messages in the workspace",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (supports Slack search modifiers like from:, in:, has:)",
                            },
                            "count": {
                                "type": "integer",
                                "description": "Number of results per page (default: 20, max: 100)",
                                "default": 20,
                            },
                            "page": {
                                "type": "integer",
                                "description": "Page number of results to return (default: 1)",
                                "default": 1,
                            },
                            "sort": {
                                "type": "string",
                                "description": "Sort order: 'score' (relevance) or 'timestamp' (default: score)",
                                "default": "score",
                            },
                            "sort_dir": {
                                "type": "string",
                                "description": "Sort direction: 'asc' or 'desc' (default: desc)",
                                "default": "desc",
                            },
                        },
                        "required": ["query"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            try:
                result = await self._dispatch_tool(name, arguments)
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2),
                    )
                ]
            except Exception as e:
                logger.exception(f"Error executing tool {name}: {e}")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": str(e)}, indent=2),
                    )
                ]

    async def _dispatch_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Dispatch tool call to appropriate handler.

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            Tool result as dictionary.

        Raises:
            ValueError: If tool name is not recognized.
        """
        handlers = {
            "list_channels": self._list_channels,
            "list_private_channels": self._list_private_channels,
            "get_channel_history": self._get_channel_history,
            "send_message": self._send_message,
            "list_direct_messages": self._list_direct_messages,
            "list_group_dms": self._list_group_dms,
            "get_dm_history": self._get_dm_history,
            "reply_to_thread": self._reply_to_thread,
            "get_user_info": self._get_user_info,
            "list_users": self._list_users,
            "get_workspace_info": self._get_workspace_info,
            "search_messages": self._search_messages,
        }

        handler = handlers.get(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name}")

        return await handler(arguments)

    async def _list_channels(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List public channels in the workspace.

        Args:
            arguments: Tool arguments with optional limit and cursor.

        Returns:
            List of public channels with pagination info.
        """
        params: dict[str, Any] = {
            "types": "public_channel",
            "limit": arguments.get("limit", 100),
        }
        if cursor := arguments.get("cursor"):
            params["cursor"] = cursor

        result = await self._slack_api("GET", "conversations.list", params=params)

        channels = [
            {
                "id": ch["id"],
                "name": ch["name"],
                "topic": ch.get("topic", {}).get("value", ""),
                "purpose": ch.get("purpose", {}).get("value", ""),
                "num_members": ch.get("num_members", 0),
                "is_member": ch.get("is_member", False),
            }
            for ch in result.get("channels", [])
        ]

        response: dict[str, Any] = {"channels": channels}
        if next_cursor := result.get("response_metadata", {}).get("next_cursor"):
            response["next_cursor"] = next_cursor

        return response

    async def _list_private_channels(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List private channels the user is a member of.

        Args:
            arguments: Tool arguments with optional limit and cursor.

        Returns:
            List of private channels with pagination info.
        """
        params: dict[str, Any] = {
            "types": "private_channel",
            "limit": arguments.get("limit", 100),
        }
        if cursor := arguments.get("cursor"):
            params["cursor"] = cursor

        result = await self._slack_api("GET", "conversations.list", params=params)

        channels = [
            {
                "id": ch["id"],
                "name": ch["name"],
                "topic": ch.get("topic", {}).get("value", ""),
                "purpose": ch.get("purpose", {}).get("value", ""),
                "num_members": ch.get("num_members", 0),
            }
            for ch in result.get("channels", [])
        ]

        response: dict[str, Any] = {"channels": channels}
        if next_cursor := result.get("response_metadata", {}).get("next_cursor"):
            response["next_cursor"] = next_cursor

        return response

    async def _get_channel_history(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Get message history from a channel.

        Args:
            arguments: Tool arguments with channel ID and optional filters.

        Returns:
            List of messages with pagination info.
        """
        params: dict[str, Any] = {
            "channel": arguments["channel"],
            "limit": arguments.get("limit", 100),
        }
        if oldest := arguments.get("oldest"):
            params["oldest"] = oldest
        if latest := arguments.get("latest"):
            params["latest"] = latest
        if cursor := arguments.get("cursor"):
            params["cursor"] = cursor

        result = await self._slack_api("GET", "conversations.history", params=params)

        messages = [
            {
                "ts": msg["ts"],
                "user": msg.get("user", ""),
                "text": msg.get("text", ""),
                "type": msg.get("type", "message"),
                "thread_ts": msg.get("thread_ts"),
                "reply_count": msg.get("reply_count", 0),
            }
            for msg in result.get("messages", [])
        ]

        response: dict[str, Any] = {"messages": messages}
        if result.get("has_more"):
            response["has_more"] = True
            if next_cursor := result.get("response_metadata", {}).get("next_cursor"):
                response["next_cursor"] = next_cursor

        return response

    async def _send_message(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Send a message to a channel.

        Args:
            arguments: Tool arguments with channel, text, and optional thread_ts.

        Returns:
            Sent message details.
        """
        payload: dict[str, Any] = {
            "channel": arguments["channel"],
            "text": arguments["text"],
        }
        if thread_ts := arguments.get("thread_ts"):
            payload["thread_ts"] = thread_ts

        result = await self._slack_api("POST", "chat.postMessage", json_data=payload)

        return {
            "ok": True,
            "channel": result.get("channel"),
            "ts": result.get("ts"),
            "message": {
                "text": result.get("message", {}).get("text", ""),
                "user": result.get("message", {}).get("user", ""),
                "ts": result.get("message", {}).get("ts", ""),
            },
        }

    async def _list_direct_messages(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List direct message conversations (1:1 DMs).

        Args:
            arguments: Tool arguments with optional limit and cursor.

        Returns:
            List of DM conversations with pagination info.
        """
        params: dict[str, Any] = {
            "types": "im",
            "limit": arguments.get("limit", 100),
        }
        if cursor := arguments.get("cursor"):
            params["cursor"] = cursor

        result = await self._slack_api("GET", "conversations.list", params=params)

        dms = [
            {
                "id": ch["id"],
                "user": ch.get("user", ""),
                "is_open": ch.get("is_open", False),
                "priority": ch.get("priority", 0),
            }
            for ch in result.get("channels", [])
        ]

        response: dict[str, Any] = {"direct_messages": dms}
        if next_cursor := result.get("response_metadata", {}).get("next_cursor"):
            response["next_cursor"] = next_cursor

        return response

    async def _list_group_dms(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List multi-party direct message conversations (group DMs).

        Args:
            arguments: Tool arguments with optional limit and cursor.

        Returns:
            List of group DM conversations with pagination info.
        """
        params: dict[str, Any] = {
            "types": "mpim",
            "limit": arguments.get("limit", 100),
        }
        if cursor := arguments.get("cursor"):
            params["cursor"] = cursor

        result = await self._slack_api("GET", "conversations.list", params=params)

        group_dms = [
            {
                "id": ch["id"],
                "name": ch.get("name", ""),
                "purpose": ch.get("purpose", {}).get("value", ""),
                "num_members": ch.get("num_members", 0),
            }
            for ch in result.get("channels", [])
        ]

        response: dict[str, Any] = {"group_dms": group_dms}
        if next_cursor := result.get("response_metadata", {}).get("next_cursor"):
            response["next_cursor"] = next_cursor

        return response

    async def _get_dm_history(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Get message history from a direct message conversation.

        Args:
            arguments: Tool arguments with DM channel ID and optional filters.

        Returns:
            List of messages with pagination info.
        """
        params: dict[str, Any] = {
            "channel": arguments["channel"],
            "limit": arguments.get("limit", 100),
        }
        if oldest := arguments.get("oldest"):
            params["oldest"] = oldest
        if latest := arguments.get("latest"):
            params["latest"] = latest
        if cursor := arguments.get("cursor"):
            params["cursor"] = cursor

        result = await self._slack_api("GET", "conversations.history", params=params)

        messages = [
            {
                "ts": msg["ts"],
                "user": msg.get("user", ""),
                "text": msg.get("text", ""),
                "type": msg.get("type", "message"),
                "thread_ts": msg.get("thread_ts"),
                "reply_count": msg.get("reply_count", 0),
            }
            for msg in result.get("messages", [])
        ]

        response: dict[str, Any] = {"messages": messages}
        if result.get("has_more"):
            response["has_more"] = True
            if next_cursor := result.get("response_metadata", {}).get("next_cursor"):
                response["next_cursor"] = next_cursor

        return response

    async def _reply_to_thread(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Reply to a specific message thread.

        Args:
            arguments: Tool arguments with channel, thread_ts, text, and optional broadcast.

        Returns:
            Sent reply message details.
        """
        payload: dict[str, Any] = {
            "channel": arguments["channel"],
            "text": arguments["text"],
            "thread_ts": arguments["thread_ts"],
        }
        if arguments.get("broadcast"):
            payload["reply_broadcast"] = True

        result = await self._slack_api("POST", "chat.postMessage", json_data=payload)

        return {
            "ok": True,
            "channel": result.get("channel"),
            "ts": result.get("ts"),
            "thread_ts": arguments["thread_ts"],
            "message": {
                "text": result.get("message", {}).get("text", ""),
                "user": result.get("message", {}).get("user", ""),
                "ts": result.get("message", {}).get("ts", ""),
            },
        }

    async def _get_user_info(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Get detailed information about a user.

        Args:
            arguments: Tool arguments with user ID.

        Returns:
            User information.
        """
        params: dict[str, Any] = {"user": arguments["user"]}
        result = await self._slack_api("GET", "users.info", params=params)

        user = result.get("user", {})
        profile = user.get("profile", {})

        return {
            "user": {
                "id": user.get("id", ""),
                "name": user.get("name", ""),
                "real_name": user.get("real_name", ""),
                "display_name": profile.get("display_name", ""),
                "email": profile.get("email", ""),
                "title": profile.get("title", ""),
                "status_text": profile.get("status_text", ""),
                "status_emoji": profile.get("status_emoji", ""),
                "tz": user.get("tz", ""),
                "is_admin": user.get("is_admin", False),
                "is_owner": user.get("is_owner", False),
                "is_bot": user.get("is_bot", False),
                "deleted": user.get("deleted", False),
            }
        }

    async def _list_users(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List all users in the workspace.

        Args:
            arguments: Tool arguments with optional limit, cursor, and include_locale.

        Returns:
            List of users with pagination info.
        """
        params: dict[str, Any] = {"limit": arguments.get("limit", 100)}
        if cursor := arguments.get("cursor"):
            params["cursor"] = cursor
        if arguments.get("include_locale"):
            params["include_locale"] = True

        result = await self._slack_api("GET", "users.list", params=params)

        users = [
            {
                "id": user.get("id", ""),
                "name": user.get("name", ""),
                "real_name": user.get("real_name", ""),
                "display_name": user.get("profile", {}).get("display_name", ""),
                "is_admin": user.get("is_admin", False),
                "is_bot": user.get("is_bot", False),
                "deleted": user.get("deleted", False),
            }
            for user in result.get("members", [])
        ]

        response: dict[str, Any] = {"users": users}
        if next_cursor := result.get("response_metadata", {}).get("next_cursor"):
            response["next_cursor"] = next_cursor

        return response

    async def _get_workspace_info(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Get information about the current workspace/team.

        Args:
            arguments: Tool arguments (none required).

        Returns:
            Workspace/team information.
        """
        result = await self._slack_api("GET", "team.info")

        team = result.get("team", {})

        return {
            "team": {
                "id": team.get("id", ""),
                "name": team.get("name", ""),
                "domain": team.get("domain", ""),
                "email_domain": team.get("email_domain", ""),
                "icon": team.get("icon", {}).get("image_132", ""),
            }
        }

    async def _search_messages(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Search for messages in the workspace.

        Args:
            arguments: Tool arguments with query and optional pagination/sort options.

        Returns:
            Search results with pagination info.
        """
        params: dict[str, Any] = {
            "query": arguments["query"],
            "count": arguments.get("count", 20),
            "page": arguments.get("page", 1),
            "sort": arguments.get("sort", "score"),
            "sort_dir": arguments.get("sort_dir", "desc"),
        }

        result = await self._slack_api("GET", "search.messages", params=params)

        messages_data = result.get("messages", {})
        matches = messages_data.get("matches", [])

        messages = [
            {
                "ts": match.get("ts", ""),
                "text": match.get("text", ""),
                "user": match.get("user", ""),
                "username": match.get("username", ""),
                "channel": {
                    "id": match.get("channel", {}).get("id", ""),
                    "name": match.get("channel", {}).get("name", ""),
                },
                "permalink": match.get("permalink", ""),
            }
            for match in matches
        ]

        paging = messages_data.get("paging", {})
        return {
            "messages": messages,
            "total": messages_data.get("total", 0),
            "page": paging.get("page", 1),
            "pages": paging.get("pages", 1),
            "count": paging.get("count", 0),
        }

    async def run(self) -> None:
        """Run the MCP server using stdio transport."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


def main() -> None:
    """Entry point for the Slack User Proxy MCP server."""
    server = SlackUserProxyServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
