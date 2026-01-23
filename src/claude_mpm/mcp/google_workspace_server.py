"""Google Workspace MCP server integrated with claude-mpm OAuth storage.

This MCP server provides tools for interacting with Google Workspace APIs
(Calendar, Gmail, Drive) using OAuth tokens managed by claude-mpm's
TokenStorage system.

The server automatically handles token refresh when tokens expire,
using the OAuthManager for seamless re-authentication.
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

# Service name for token storage - matches workspace-mcp convention
SERVICE_NAME = "workspace-mcp"

# Google API base URLs
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"


class GoogleWorkspaceServer:
    """MCP server for Google Workspace APIs.

    Integrates with claude-mpm's TokenStorage for credential management
    and provides tools for Calendar, Gmail, and Drive operations.

    Attributes:
        server: MCP Server instance.
        storage: TokenStorage for retrieving OAuth tokens.
        manager: OAuthManager for token refresh operations.
    """

    def __init__(self) -> None:
        """Initialize the Google Workspace MCP server."""
        self.server = Server("google-workspace-mpm")
        self.storage = TokenStorage()
        self.manager = OAuthManager(storage=self.storage)
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """Return list of available tools."""
            return [
                Tool(
                    name="list_calendars",
                    description="List all calendars accessible by the authenticated user",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="get_events",
                    description="Get events from a calendar within a time range",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID (default: 'primary')",
                                "default": "primary",
                            },
                            "time_min": {
                                "type": "string",
                                "description": "Start time in RFC3339 format (e.g., '2024-01-01T00:00:00Z')",
                            },
                            "time_max": {
                                "type": "string",
                                "description": "End time in RFC3339 format",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of events to return (default: 10)",
                                "default": 10,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="search_gmail_messages",
                    description="Search Gmail messages using a query string",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Gmail search query (e.g., 'from:user@example.com subject:meeting')",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of messages to return (default: 10)",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="get_gmail_message_content",
                    description="Get the full content of a Gmail message by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message_id": {
                                "type": "string",
                                "description": "Gmail message ID",
                            },
                        },
                        "required": ["message_id"],
                    },
                ),
                Tool(
                    name="search_drive_files",
                    description="Search Google Drive files using a query string",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Drive search query (e.g., 'name contains \"report\"')",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of files to return (default: 10)",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="get_drive_file_content",
                    description="Get the content of a Google Drive file by ID (text files only)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {
                                "type": "string",
                                "description": "Google Drive file ID",
                            },
                        },
                        "required": ["file_id"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            try:
                result = await self._dispatch_tool(name, arguments)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except Exception as e:
                logger.exception(f"Error calling tool {name}")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": str(e)}, indent=2),
                    )
                ]

    async def _get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary.

        Returns:
            Valid access token string.

        Raises:
            RuntimeError: If no token is available or refresh fails.
        """
        status = self.storage.get_status(SERVICE_NAME)

        if status == TokenStatus.MISSING:
            raise RuntimeError(
                f"No OAuth token found for service '{SERVICE_NAME}'. "
                "Please authenticate first using: claude-mpm auth login google"
            )

        if status == TokenStatus.INVALID:
            raise RuntimeError(
                f"OAuth token for service '{SERVICE_NAME}' is invalid or corrupted. "
                "Please re-authenticate using: claude-mpm auth login google"
            )

        # Try to refresh if expired
        if status == TokenStatus.EXPIRED:
            logger.info("Token expired, attempting refresh...")
            token = await self.manager.refresh_if_needed(SERVICE_NAME)
            if token is None:
                raise RuntimeError(
                    "Token refresh failed. Please re-authenticate using: "
                    "claude-mpm auth login google"
                )
            return token.access_token

        # Token is valid
        stored = self.storage.retrieve(SERVICE_NAME)
        if stored is None:
            raise RuntimeError("Unexpected error: token retrieval failed")

        return stored.token.access_token

    async def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make an authenticated HTTP request to Google APIs.

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Full URL to request.
            params: Optional query parameters.
            json_data: Optional JSON body data.

        Returns:
            JSON response as a dictionary.

        Raises:
            httpx.HTTPStatusError: If the request fails.
        """
        access_token = await self._get_access_token()

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result

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
            "list_calendars": self._list_calendars,
            "get_events": self._get_events,
            "search_gmail_messages": self._search_gmail_messages,
            "get_gmail_message_content": self._get_gmail_message_content,
            "search_drive_files": self._search_drive_files,
            "get_drive_file_content": self._get_drive_file_content,
        }

        handler = handlers.get(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name}")

        return await handler(arguments)

    async def _list_calendars(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List all calendars accessible by the user.

        Args:
            arguments: Tool arguments (not used).

        Returns:
            List of calendars with id, summary, and access role.
        """
        url = f"{CALENDAR_API_BASE}/users/me/calendarList"
        response = await self._make_request("GET", url)

        calendars = []
        for item in response.get("items", []):
            calendars.append(
                {
                    "id": item.get("id"),
                    "summary": item.get("summary"),
                    "description": item.get("description"),
                    "access_role": item.get("accessRole"),
                    "primary": item.get("primary", False),
                }
            )

        return {"calendars": calendars, "count": len(calendars)}

    async def _get_events(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Get events from a calendar.

        Args:
            arguments: Tool arguments with calendar_id, time_min, time_max, max_results.

        Returns:
            List of events with summary, start, end times.
        """
        calendar_id = arguments.get("calendar_id", "primary")
        time_min = arguments.get("time_min")
        time_max = arguments.get("time_max")
        max_results = arguments.get("max_results", 10)

        url = f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events"
        params: dict[str, Any] = {
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }

        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max

        response = await self._make_request("GET", url, params=params)

        events = []
        for item in response.get("items", []):
            start = item.get("start", {})
            end = item.get("end", {})
            events.append(
                {
                    "id": item.get("id"),
                    "summary": item.get("summary"),
                    "description": item.get("description"),
                    "start": start.get("dateTime") or start.get("date"),
                    "end": end.get("dateTime") or end.get("date"),
                    "location": item.get("location"),
                    "attendees": [a.get("email") for a in item.get("attendees", [])],
                }
            )

        return {"events": events, "count": len(events)}

    async def _search_gmail_messages(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Search Gmail messages.

        Args:
            arguments: Tool arguments with query and max_results.

        Returns:
            List of message snippets with id, thread_id, subject, from, date.
        """
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 10)

        url = f"{GMAIL_API_BASE}/users/me/messages"
        params = {"q": query, "maxResults": max_results}

        response = await self._make_request("GET", url, params=params)

        messages = []
        for msg in response.get("messages", []):
            # Get message metadata
            msg_url = f"{GMAIL_API_BASE}/users/me/messages/{msg['id']}"
            msg_detail = await self._make_request(
                "GET", msg_url, params={"format": "metadata"}
            )

            headers = {
                h["name"]: h["value"]
                for h in msg_detail.get("payload", {}).get("headers", [])
            }

            messages.append(
                {
                    "id": msg["id"],
                    "thread_id": msg.get("threadId"),
                    "subject": headers.get("Subject"),
                    "from": headers.get("From"),
                    "to": headers.get("To"),
                    "date": headers.get("Date"),
                    "snippet": msg_detail.get("snippet"),
                }
            )

        return {"messages": messages, "count": len(messages)}

    async def _get_gmail_message_content(
        self, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Get full content of a Gmail message.

        Args:
            arguments: Tool arguments with message_id.

        Returns:
            Message content including headers and body.
        """
        message_id = arguments["message_id"]

        url = f"{GMAIL_API_BASE}/users/me/messages/{message_id}"
        response = await self._make_request("GET", url, params={"format": "full"})

        headers = {
            h["name"]: h["value"]
            for h in response.get("payload", {}).get("headers", [])
        }

        # Extract body content
        body = self._extract_message_body(response.get("payload", {}))

        return {
            "id": response.get("id"),
            "thread_id": response.get("threadId"),
            "subject": headers.get("Subject"),
            "from": headers.get("From"),
            "to": headers.get("To"),
            "cc": headers.get("Cc"),
            "date": headers.get("Date"),
            "body": body,
            "labels": response.get("labelIds", []),
        }

    def _extract_message_body(self, payload: dict[str, Any]) -> str:
        """Extract message body from Gmail payload.

        Handles both simple and multipart messages.

        Args:
            payload: Gmail message payload.

        Returns:
            Decoded message body text.
        """
        import base64

        # Simple message with body data
        if "body" in payload and payload["body"].get("data"):
            data = payload["body"]["data"]
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        # Multipart message
        parts = payload.get("parts", [])
        for part in parts:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode(
                        "utf-8", errors="replace"
                    )
            elif mime_type.startswith("multipart/"):
                # Recursively extract from nested parts
                result = self._extract_message_body(part)
                if result:
                    return result

        # Fallback to HTML if no plain text
        for part in parts:
            if part.get("mimeType") == "text/html":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode(
                        "utf-8", errors="replace"
                    )

        return ""

    async def _search_drive_files(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Search Google Drive files.

        Args:
            arguments: Tool arguments with query and max_results.

        Returns:
            List of files with id, name, mimeType, modifiedTime.
        """
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 10)

        url = f"{DRIVE_API_BASE}/files"
        params = {
            "q": query,
            "pageSize": max_results,
            "fields": "files(id,name,mimeType,modifiedTime,size,webViewLink,owners)",
        }

        response = await self._make_request("GET", url, params=params)

        files = []
        for item in response.get("files", []):
            files.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "mimeType": item.get("mimeType"),
                    "modifiedTime": item.get("modifiedTime"),
                    "size": item.get("size"),
                    "webViewLink": item.get("webViewLink"),
                    "owners": [o.get("emailAddress") for o in item.get("owners", [])],
                }
            )

        return {"files": files, "count": len(files)}

    async def _get_drive_file_content(
        self, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Get content of a Google Drive file.

        Args:
            arguments: Tool arguments with file_id.

        Returns:
            File metadata and content (for exportable types).
        """
        file_id = arguments["file_id"]

        # First get file metadata
        meta_url = f"{DRIVE_API_BASE}/files/{file_id}"
        metadata = await self._make_request(
            "GET", meta_url, params={"fields": "id,name,mimeType,size"}
        )

        mime_type = metadata.get("mimeType", "")

        # Google Docs types need export
        export_map = {
            "application/vnd.google-apps.document": "text/plain",
            "application/vnd.google-apps.spreadsheet": "text/csv",
            "application/vnd.google-apps.presentation": "text/plain",
        }

        access_token = await self._get_access_token()

        if mime_type in export_map:
            # Export Google Workspace files
            export_url = f"{DRIVE_API_BASE}/files/{file_id}/export"
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    export_url,
                    params={"mimeType": export_map[mime_type]},
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30.0,
                )
                response.raise_for_status()
                content = response.text
        else:
            # Download regular files
            download_url = f"{DRIVE_API_BASE}/files/{file_id}"
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    download_url,
                    params={"alt": "media"},
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30.0,
                )
                response.raise_for_status()

                # Try to decode as text, otherwise indicate binary
                try:
                    content = response.text
                except UnicodeDecodeError:
                    content = f"[Binary file: {metadata.get('size', 'unknown')} bytes]"

        return {
            "id": metadata.get("id"),
            "name": metadata.get("name"),
            "mimeType": mime_type,
            "content": content,
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
    """Entry point for the Google Workspace MCP server."""
    server = GoogleWorkspaceServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
