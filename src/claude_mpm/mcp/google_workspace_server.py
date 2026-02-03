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

# Service name for token storage - matches google-workspace-mcp convention
SERVICE_NAME = "google-workspace-mcp"

# Google API base URLs
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
DOCS_API_BASE = "https://docs.googleapis.com/v1"


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
        self.server = Server("google-workspace-mcp")
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
                Tool(
                    name="list_document_comments",
                    description="List all comments on a Google Docs, Sheets, or Slides file. Returns comment content, author, timestamps, resolved status, and replies.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {
                                "type": "string",
                                "description": "Google Drive file ID (from the document URL)",
                            },
                            "include_deleted": {
                                "type": "boolean",
                                "default": False,
                                "description": "Include deleted comments",
                            },
                            "max_results": {
                                "type": "integer",
                                "default": 100,
                                "description": "Maximum number of comments to return",
                            },
                        },
                        "required": ["file_id"],
                    },
                ),
                # Calendar Write Operations
                Tool(
                    name="create_event",
                    description="Create a new calendar event",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID (default: 'primary')",
                                "default": "primary",
                            },
                            "summary": {
                                "type": "string",
                                "description": "Event title",
                            },
                            "description": {
                                "type": "string",
                                "description": "Event description",
                            },
                            "start_time": {
                                "type": "string",
                                "description": "Start time in RFC3339 format (e.g., '2024-01-15T10:00:00Z')",
                            },
                            "end_time": {
                                "type": "string",
                                "description": "End time in RFC3339 format (e.g., '2024-01-15T11:00:00Z')",
                            },
                            "attendees": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of attendee email addresses",
                            },
                            "location": {
                                "type": "string",
                                "description": "Event location",
                            },
                            "timezone": {
                                "type": "string",
                                "description": "Timezone for the event (e.g., 'America/New_York')",
                            },
                        },
                        "required": ["summary", "start_time", "end_time"],
                    },
                ),
                Tool(
                    name="update_event",
                    description="Update an existing calendar event",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID (default: 'primary')",
                                "default": "primary",
                            },
                            "event_id": {
                                "type": "string",
                                "description": "Event ID to update",
                            },
                            "summary": {
                                "type": "string",
                                "description": "New event title",
                            },
                            "description": {
                                "type": "string",
                                "description": "New event description",
                            },
                            "start_time": {
                                "type": "string",
                                "description": "New start time in RFC3339 format",
                            },
                            "end_time": {
                                "type": "string",
                                "description": "New end time in RFC3339 format",
                            },
                            "attendees": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "New list of attendee email addresses",
                            },
                            "location": {
                                "type": "string",
                                "description": "New event location",
                            },
                        },
                        "required": ["event_id"],
                    },
                ),
                Tool(
                    name="delete_event",
                    description="Delete a calendar event",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID (default: 'primary')",
                                "default": "primary",
                            },
                            "event_id": {
                                "type": "string",
                                "description": "Event ID to delete",
                            },
                        },
                        "required": ["event_id"],
                    },
                ),
                # Gmail Write Operations
                Tool(
                    name="send_email",
                    description="Send an email message",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "to": {
                                "type": "string",
                                "description": "Recipient email address(es), comma-separated for multiple",
                            },
                            "subject": {
                                "type": "string",
                                "description": "Email subject",
                            },
                            "body": {
                                "type": "string",
                                "description": "Email body (plain text)",
                            },
                            "cc": {
                                "type": "string",
                                "description": "CC recipients, comma-separated",
                            },
                            "bcc": {
                                "type": "string",
                                "description": "BCC recipients, comma-separated",
                            },
                        },
                        "required": ["to", "subject", "body"],
                    },
                ),
                Tool(
                    name="create_draft",
                    description="Create an email draft",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "to": {
                                "type": "string",
                                "description": "Recipient email address(es), comma-separated for multiple",
                            },
                            "subject": {
                                "type": "string",
                                "description": "Email subject",
                            },
                            "body": {
                                "type": "string",
                                "description": "Email body (plain text)",
                            },
                            "cc": {
                                "type": "string",
                                "description": "CC recipients, comma-separated",
                            },
                            "bcc": {
                                "type": "string",
                                "description": "BCC recipients, comma-separated",
                            },
                        },
                        "required": ["to", "subject", "body"],
                    },
                ),
                Tool(
                    name="reply_to_email",
                    description="Reply to an existing email thread",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message_id": {
                                "type": "string",
                                "description": "Original message ID to reply to",
                            },
                            "body": {
                                "type": "string",
                                "description": "Reply body (plain text)",
                            },
                        },
                        "required": ["message_id", "body"],
                    },
                ),
                # Drive Write Operations
                Tool(
                    name="create_drive_folder",
                    description="Create a new folder in Google Drive",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Folder name",
                            },
                            "parent_id": {
                                "type": "string",
                                "description": "Parent folder ID (optional, defaults to root)",
                            },
                        },
                        "required": ["name"],
                    },
                ),
                Tool(
                    name="upload_drive_file",
                    description="Upload a text file to Google Drive",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "File name",
                            },
                            "content": {
                                "type": "string",
                                "description": "File content (text)",
                            },
                            "mime_type": {
                                "type": "string",
                                "description": "MIME type (default: 'text/plain')",
                                "default": "text/plain",
                            },
                            "parent_id": {
                                "type": "string",
                                "description": "Parent folder ID (optional)",
                            },
                        },
                        "required": ["name", "content"],
                    },
                ),
                Tool(
                    name="delete_drive_file",
                    description="Delete a file or folder from Google Drive",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {
                                "type": "string",
                                "description": "File or folder ID to delete",
                            },
                        },
                        "required": ["file_id"],
                    },
                ),
                Tool(
                    name="move_drive_file",
                    description="Move a file to a different folder in Google Drive",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {
                                "type": "string",
                                "description": "File ID to move",
                            },
                            "new_parent_id": {
                                "type": "string",
                                "description": "Destination folder ID",
                            },
                        },
                        "required": ["file_id", "new_parent_id"],
                    },
                ),
                # Google Docs Write Operations
                Tool(
                    name="create_document",
                    description="Create a new Google Doc",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Document title",
                            },
                        },
                        "required": ["title"],
                    },
                ),
                Tool(
                    name="append_to_document",
                    description="Append text to an existing Google Doc",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "Google Doc ID",
                            },
                            "text": {
                                "type": "string",
                                "description": "Text to append",
                            },
                        },
                        "required": ["document_id", "text"],
                    },
                ),
                Tool(
                    name="get_document",
                    description="Get the content and structure of a Google Doc",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "Google Doc ID",
                            },
                        },
                        "required": ["document_id"],
                    },
                ),
                Tool(
                    name="upload_markdown_as_doc",
                    description="Convert Markdown content to Google Docs format and upload to Drive. Uses pandoc for conversion.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Document name (without extension)",
                            },
                            "markdown_content": {
                                "type": "string",
                                "description": "Markdown content to convert",
                            },
                            "parent_id": {
                                "type": "string",
                                "description": "Parent folder ID (optional)",
                            },
                            "output_format": {
                                "type": "string",
                                "description": "Output format: 'gdoc' (Google Docs) or 'docx' (Microsoft Word)",
                                "default": "gdoc",
                                "enum": ["gdoc", "docx"],
                            },
                        },
                        "required": ["name", "markdown_content"],
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
            # Read operations
            "list_calendars": self._list_calendars,
            "get_events": self._get_events,
            "search_gmail_messages": self._search_gmail_messages,
            "get_gmail_message_content": self._get_gmail_message_content,
            "search_drive_files": self._search_drive_files,
            "get_drive_file_content": self._get_drive_file_content,
            "list_document_comments": self._list_document_comments,
            # Calendar write operations
            "create_event": self._create_event,
            "update_event": self._update_event,
            "delete_event": self._delete_event,
            # Gmail write operations
            "send_email": self._send_email,
            "create_draft": self._create_draft,
            "reply_to_email": self._reply_to_email,
            # Drive write operations
            "create_drive_folder": self._create_drive_folder,
            "upload_drive_file": self._upload_drive_file,
            "delete_drive_file": self._delete_drive_file,
            "move_drive_file": self._move_drive_file,
            # Docs write operations
            "create_document": self._create_document,
            "append_to_document": self._append_to_document,
            "get_document": self._get_document,
            # Markdown conversion
            "upload_markdown_as_doc": self._upload_markdown_as_doc,
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

    async def _list_document_comments(
        self, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """List comments on a Google Drive file (Docs, Sheets, Slides).

        Args:
            arguments: Tool arguments with file_id, include_deleted, max_results.

        Returns:
            List of comments with content, author, timestamps, resolved status, and replies.
        """
        file_id = arguments["file_id"]
        include_deleted = arguments.get("include_deleted", False)
        max_results = arguments.get("max_results", 100)

        # Build request URL with required fields parameter
        url = f"{DRIVE_API_BASE}/files/{file_id}/comments"
        params = {
            "fields": "comments(id,content,author(displayName,emailAddress),createdTime,modifiedTime,resolved,deleted,quotedFileContent,replies(id,content,author(displayName,emailAddress),createdTime,modifiedTime,deleted))",
            "pageSize": min(max_results, 100),
            "includeDeleted": str(include_deleted).lower(),
        }

        response = await self._make_request("GET", url, params=params)

        comments = response.get("comments", [])
        if not comments:
            return {
                "comments": [],
                "count": 0,
                "message": "No comments found on this document.",
            }

        # Format comments for readable output
        formatted_comments = []
        for comment in comments:
            author = comment.get("author", {})
            quoted = comment.get("quotedFileContent", {})

            formatted_comment: dict[str, Any] = {
                "id": comment.get("id"),
                "author_name": author.get("displayName", "Unknown"),
                "author_email": author.get("emailAddress", ""),
                "created_time": comment.get("createdTime", ""),
                "modified_time": comment.get("modifiedTime", ""),
                "resolved": comment.get("resolved", False),
                "deleted": comment.get("deleted", False),
                "content": comment.get("content", ""),
            }

            # Add quoted text if present
            if quoted.get("value"):
                quoted_text = quoted.get("value", "")
                # Truncate long quoted text
                if len(quoted_text) > 200:
                    quoted_text = quoted_text[:200] + "..."
                formatted_comment["quoted_text"] = quoted_text

            # Include replies if present
            replies = comment.get("replies", [])
            if replies:
                formatted_replies = []
                for reply in replies:
                    reply_author = reply.get("author", {})
                    formatted_replies.append(
                        {
                            "id": reply.get("id"),
                            "author_name": reply_author.get("displayName", "Unknown"),
                            "author_email": reply_author.get("emailAddress", ""),
                            "created_time": reply.get("createdTime", ""),
                            "modified_time": reply.get("modifiedTime", ""),
                            "deleted": reply.get("deleted", False),
                            "content": reply.get("content", ""),
                        }
                    )
                formatted_comment["replies"] = formatted_replies
                formatted_comment["reply_count"] = len(formatted_replies)

            formatted_comments.append(formatted_comment)

        return {"comments": formatted_comments, "count": len(formatted_comments)}

    # =========================================================================
    # Calendar Write Operations
    # =========================================================================

    async def _create_event(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Create a new calendar event.

        Args:
            arguments: Tool arguments with summary, start_time, end_time, etc.

        Returns:
            Created event details with id and link.
        """
        calendar_id = arguments.get("calendar_id", "primary")
        summary = arguments["summary"]
        start_time = arguments["start_time"]
        end_time = arguments["end_time"]
        description = arguments.get("description")
        attendees = arguments.get("attendees", [])
        location = arguments.get("location")
        timezone = arguments.get("timezone")

        url = f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events"

        event_body: dict[str, Any] = {
            "summary": summary,
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time},
        }

        if timezone:
            event_body["start"]["timeZone"] = timezone
            event_body["end"]["timeZone"] = timezone

        if description:
            event_body["description"] = description

        if attendees:
            event_body["attendees"] = [{"email": email} for email in attendees]

        if location:
            event_body["location"] = location

        response = await self._make_request("POST", url, json_data=event_body)

        return {
            "status": "created",
            "id": response.get("id"),
            "summary": response.get("summary"),
            "start": response.get("start", {}).get("dateTime"),
            "end": response.get("end", {}).get("dateTime"),
            "html_link": response.get("htmlLink"),
        }

    async def _update_event(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Update an existing calendar event.

        Args:
            arguments: Tool arguments with event_id and fields to update.

        Returns:
            Updated event details.
        """
        calendar_id = arguments.get("calendar_id", "primary")
        event_id = arguments["event_id"]

        # First get the existing event
        get_url = f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}"
        existing = await self._make_request("GET", get_url)

        # Build update body with only provided fields
        update_body: dict[str, Any] = {}

        if "summary" in arguments:
            update_body["summary"] = arguments["summary"]
        if "description" in arguments:
            update_body["description"] = arguments["description"]
        if "start_time" in arguments:
            update_body["start"] = {"dateTime": arguments["start_time"]}
            if existing.get("start", {}).get("timeZone"):
                update_body["start"]["timeZone"] = existing["start"]["timeZone"]
        if "end_time" in arguments:
            update_body["end"] = {"dateTime": arguments["end_time"]}
            if existing.get("end", {}).get("timeZone"):
                update_body["end"]["timeZone"] = existing["end"]["timeZone"]
        if "attendees" in arguments:
            update_body["attendees"] = [
                {"email": email} for email in arguments["attendees"]
            ]
        if "location" in arguments:
            update_body["location"] = arguments["location"]

        response = await self._make_request("PATCH", get_url, json_data=update_body)

        return {
            "status": "updated",
            "id": response.get("id"),
            "summary": response.get("summary"),
            "start": response.get("start", {}).get("dateTime"),
            "end": response.get("end", {}).get("dateTime"),
            "html_link": response.get("htmlLink"),
        }

    async def _delete_event(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Delete a calendar event.

        Args:
            arguments: Tool arguments with event_id.

        Returns:
            Deletion confirmation.
        """
        calendar_id = arguments.get("calendar_id", "primary")
        event_id = arguments["event_id"]

        url = f"{CALENDAR_API_BASE}/calendars/{calendar_id}/events/{event_id}"

        access_token = await self._get_access_token()
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            response.raise_for_status()

        return {"status": "deleted", "event_id": event_id}

    # =========================================================================
    # Gmail Write Operations
    # =========================================================================

    def _build_email_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
    ) -> str:
        """Build RFC 2822 email message and return base64url encoded.

        Args:
            to: Recipient email(s).
            subject: Email subject.
            body: Email body text.
            cc: Optional CC recipients.
            bcc: Optional BCC recipients.
            thread_id: Optional thread ID for replies.
            in_reply_to: Optional Message-ID for reply threading.
            references: Optional References header for reply threading.

        Returns:
            Base64url encoded email message.
        """
        import base64
        from email.mime.text import MIMEText

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        if cc:
            message["cc"] = cc
        if bcc:
            message["bcc"] = bcc
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
        if references:
            message["References"] = references

        return base64.urlsafe_b64encode(message.as_bytes()).decode()

    async def _send_email(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Send an email message.

        Args:
            arguments: Tool arguments with to, subject, body, cc, bcc.

        Returns:
            Sent message details.
        """
        to = arguments["to"]
        subject = arguments["subject"]
        body = arguments["body"]
        cc = arguments.get("cc")
        bcc = arguments.get("bcc")

        raw_message = self._build_email_message(to, subject, body, cc, bcc)

        url = f"{GMAIL_API_BASE}/users/me/messages/send"
        response = await self._make_request("POST", url, json_data={"raw": raw_message})

        return {
            "status": "sent",
            "id": response.get("id"),
            "thread_id": response.get("threadId"),
            "label_ids": response.get("labelIds", []),
        }

    async def _create_draft(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Create an email draft.

        Args:
            arguments: Tool arguments with to, subject, body, cc, bcc.

        Returns:
            Created draft details.
        """
        to = arguments["to"]
        subject = arguments["subject"]
        body = arguments["body"]
        cc = arguments.get("cc")
        bcc = arguments.get("bcc")

        raw_message = self._build_email_message(to, subject, body, cc, bcc)

        url = f"{GMAIL_API_BASE}/users/me/drafts"
        response = await self._make_request(
            "POST", url, json_data={"message": {"raw": raw_message}}
        )

        return {
            "status": "draft_created",
            "id": response.get("id"),
            "message_id": response.get("message", {}).get("id"),
            "thread_id": response.get("message", {}).get("threadId"),
        }

    async def _reply_to_email(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Reply to an existing email thread.

        Args:
            arguments: Tool arguments with message_id and body.

        Returns:
            Sent reply details.
        """
        message_id = arguments["message_id"]
        body = arguments["body"]

        # Get original message to extract thread info and headers
        orig_url = f"{GMAIL_API_BASE}/users/me/messages/{message_id}"
        original = await self._make_request(
            "GET", orig_url, params={"format": "metadata"}
        )

        thread_id = original.get("threadId")
        headers = {
            h["name"]: h["value"]
            for h in original.get("payload", {}).get("headers", [])
        }

        # Get reply-to address or sender
        reply_to = headers.get("Reply-To") or headers.get("From", "")
        original_subject = headers.get("Subject", "")
        message_id_header = headers.get("Message-ID")

        # Build reply subject
        if not original_subject.lower().startswith("re:"):
            reply_subject = f"Re: {original_subject}"
        else:
            reply_subject = original_subject

        raw_message = self._build_email_message(
            to=reply_to,
            subject=reply_subject,
            body=body,
            in_reply_to=message_id_header,
            references=message_id_header,
        )

        url = f"{GMAIL_API_BASE}/users/me/messages/send"
        response = await self._make_request(
            "POST", url, json_data={"raw": raw_message, "threadId": thread_id}
        )

        return {
            "status": "reply_sent",
            "id": response.get("id"),
            "thread_id": response.get("threadId"),
            "in_reply_to": message_id,
        }

    # =========================================================================
    # Drive Write Operations
    # =========================================================================

    async def _create_drive_folder(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Create a new folder in Google Drive.

        Args:
            arguments: Tool arguments with name and optional parent_id.

        Returns:
            Created folder details.
        """
        name = arguments["name"]
        parent_id = arguments.get("parent_id")

        url = f"{DRIVE_API_BASE}/files"

        metadata: dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }

        if parent_id:
            metadata["parents"] = [parent_id]

        response = await self._make_request("POST", url, json_data=metadata)

        return {
            "status": "folder_created",
            "id": response.get("id"),
            "name": response.get("name"),
            "mimeType": response.get("mimeType"),
        }

    async def _upload_drive_file(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Upload a text file to Google Drive.

        Args:
            arguments: Tool arguments with name, content, mime_type, parent_id.

        Returns:
            Uploaded file details.
        """
        name = arguments["name"]
        content = arguments["content"]
        mime_type = arguments.get("mime_type", "text/plain")
        parent_id = arguments.get("parent_id")

        access_token = await self._get_access_token()

        # Build metadata
        metadata: dict[str, Any] = {"name": name, "mimeType": mime_type}
        if parent_id:
            metadata["parents"] = [parent_id]

        # Use multipart upload
        upload_url = (
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
        )

        # Build multipart body
        boundary = "foo_bar_baz"
        body_parts = [
            f"--{boundary}",
            "Content-Type: application/json; charset=UTF-8",
            "",
            json.dumps(metadata),
            f"--{boundary}",
            f"Content-Type: {mime_type}",
            "",
            content,
            f"--{boundary}--",
        ]
        body = "\r\n".join(body_parts)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                upload_url,
                content=body.encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
                timeout=60.0,
            )
            response.raise_for_status()
            result = response.json()

        return {
            "status": "uploaded",
            "id": result.get("id"),
            "name": result.get("name"),
            "mimeType": result.get("mimeType"),
        }

    async def _delete_drive_file(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Delete a file or folder from Google Drive.

        Args:
            arguments: Tool arguments with file_id.

        Returns:
            Deletion confirmation.
        """
        file_id = arguments["file_id"]

        url = f"{DRIVE_API_BASE}/files/{file_id}"

        access_token = await self._get_access_token()
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            response.raise_for_status()

        return {"status": "deleted", "file_id": file_id}

    async def _move_drive_file(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Move a file to a different folder in Google Drive.

        Args:
            arguments: Tool arguments with file_id and new_parent_id.

        Returns:
            Moved file details.
        """
        file_id = arguments["file_id"]
        new_parent_id = arguments["new_parent_id"]

        # First get current parents
        get_url = f"{DRIVE_API_BASE}/files/{file_id}?fields=parents"
        file_info = await self._make_request("GET", get_url)
        current_parents = file_info.get("parents", [])

        # Update with new parent, removing old ones
        update_url = f"{DRIVE_API_BASE}/files/{file_id}"
        params = {
            "addParents": new_parent_id,
            "removeParents": ",".join(current_parents),
            "fields": "id,name,parents",
        }

        access_token = await self._get_access_token()
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                update_url,
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()

        return {
            "status": "moved",
            "id": result.get("id"),
            "name": result.get("name"),
            "new_parents": result.get("parents", []),
        }

    # =========================================================================
    # Google Docs Write Operations
    # =========================================================================

    async def _create_document(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Create a new Google Doc.

        Args:
            arguments: Tool arguments with title.

        Returns:
            Created document details.
        """
        title = arguments["title"]

        url = f"{DOCS_API_BASE}/documents"
        response = await self._make_request("POST", url, json_data={"title": title})

        return {
            "status": "created",
            "document_id": response.get("documentId"),
            "title": response.get("title"),
            "revision_id": response.get("revisionId"),
        }

    async def _append_to_document(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Append text to an existing Google Doc.

        Args:
            arguments: Tool arguments with document_id and text.

        Returns:
            Update confirmation.
        """
        document_id = arguments["document_id"]
        text = arguments["text"]

        # First get document to find end index
        get_url = f"{DOCS_API_BASE}/documents/{document_id}"
        doc = await self._make_request("GET", get_url)

        # Get the end of the document body
        content = doc.get("body", {}).get("content", [])
        if content:
            # Find the last element's endIndex
            last_element = content[-1]
            end_index = last_element.get("endIndex", 1)
            # Insert before the final newline
            insert_index = max(1, end_index - 1)
        else:
            insert_index = 1

        # Use batchUpdate to insert text
        update_url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
        body = {
            "requests": [
                {
                    "insertText": {
                        "location": {"index": insert_index},
                        "text": text,
                    }
                }
            ]
        }

        await self._make_request("POST", update_url, json_data=body)

        return {
            "status": "appended",
            "document_id": document_id,
            "text_length": len(text),
        }

    async def _get_document(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Get the content and structure of a Google Doc.

        Args:
            arguments: Tool arguments with document_id.

        Returns:
            Document content and metadata.
        """
        document_id = arguments["document_id"]

        url = f"{DOCS_API_BASE}/documents/{document_id}"
        response = await self._make_request("GET", url)

        # Extract text content from body
        text_content = self._extract_doc_text(response.get("body", {}))

        return {
            "document_id": response.get("documentId"),
            "title": response.get("title"),
            "revision_id": response.get("revisionId"),
            "text_content": text_content,
        }

    def _extract_doc_text(self, body: dict[str, Any]) -> str:
        """Extract plain text from a Google Docs body structure.

        Args:
            body: The body section of a Google Docs response.

        Returns:
            Plain text content of the document.
        """
        text_parts = []
        for element in body.get("content", []):
            if "paragraph" in element:
                for para_element in element["paragraph"].get("elements", []):
                    if "textRun" in para_element:
                        text_parts.append(para_element["textRun"].get("content", ""))
            elif "table" in element:
                # Handle tables
                for row in element["table"].get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        cell_text = self._extract_doc_text(cell)
                        if cell_text:
                            text_parts.append(cell_text)
                            text_parts.append("\t")
                    text_parts.append("\n")

        return "".join(text_parts)

    # =========================================================================
    # Markdown Conversion Operations
    # =========================================================================

    async def _upload_markdown_as_doc(
        self, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Convert Markdown to Google Docs or DOCX and upload to Drive.

        Uses pandoc for conversion. Supports two output formats:
        - gdoc: Converts to Google Docs native format
        - docx: Uploads as Microsoft Word document

        Args:
            arguments: Tool arguments with name, markdown_content, parent_id, output_format.

        Returns:
            Uploaded document details.

        Raises:
            RuntimeError: If pandoc is not installed or conversion fails.
        """
        import subprocess  # nosec B404 - pandoc is trusted executable
        import tempfile
        from pathlib import Path

        name = arguments["name"]
        markdown_content = arguments["markdown_content"]
        parent_id = arguments.get("parent_id")
        output_format = arguments.get("output_format", "gdoc")

        # Check if pandoc is available
        try:
            subprocess.run(  # nosec B603 B607 - pandoc is trusted with fixed args
                ["pandoc", "--version"],
                capture_output=True,
                check=True,
            )
        except FileNotFoundError as err:
            raise RuntimeError(
                "pandoc is not installed. Install it with:\n"
                "  macOS: brew install pandoc\n"
                "  Ubuntu: sudo apt-get install pandoc\n"
                "  Windows: choco install pandoc"
            ) from err

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.md"
            output_path = Path(tmpdir) / "output.docx"

            # Write markdown to temp file
            input_path.write_text(markdown_content, encoding="utf-8")

            # Convert markdown to docx using pandoc
            try:
                subprocess.run(  # nosec B603 B607 - pandoc with controlled paths
                    [
                        "pandoc",
                        str(input_path),
                        "-o",
                        str(output_path),
                        "--from=markdown",
                        "--to=docx",
                    ],
                    capture_output=True,
                    check=True,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"pandoc conversion failed: {e.stderr}") from e

            # Read the converted docx
            docx_content = output_path.read_bytes()

        access_token = await self._get_access_token()

        if output_format == "gdoc":
            # Upload and convert to Google Docs
            metadata: dict[str, Any] = {
                "name": name,
                "mimeType": "application/vnd.google-apps.document",
            }
            if parent_id:
                metadata["parents"] = [parent_id]

            # Use multipart upload with conversion
            upload_url = (
                "https://www.googleapis.com/upload/drive/v3/files"
                "?uploadType=multipart&convert=true"
            )

            boundary = "foo_bar_baz_docx"
            import base64

            docx_base64 = base64.b64encode(docx_content).decode("ascii")

            # Build multipart body for binary content
            body = (
                f"--{boundary}\r\n"
                f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
                f"{json.dumps(metadata)}\r\n"
                f"--{boundary}\r\n"
                f"Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n"
                f"Content-Transfer-Encoding: base64\r\n\r\n"
                f"{docx_base64}\r\n"
                f"--{boundary}--"
            )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    upload_url,
                    content=body.encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": f"multipart/related; boundary={boundary}",
                    },
                    timeout=120.0,
                )
                response.raise_for_status()
                result = response.json()

            return {
                "status": "created",
                "format": "google_docs",
                "id": result.get("id"),
                "name": result.get("name"),
                "mimeType": result.get("mimeType"),
            }

        # Upload as DOCX file
        metadata = {"name": f"{name}.docx"}
        if parent_id:
            metadata["parents"] = [parent_id]

        upload_url = (
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
        )

        boundary = "foo_bar_baz_docx"

        # Build multipart body
        body_start = (
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(metadata)}\r\n"
            f"--{boundary}\r\n"
            f"Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n"
        ).encode()
        body_end = f"\r\n--{boundary}--".encode()

        full_body = body_start + docx_content + body_end

        async with httpx.AsyncClient() as client:
            response = await client.post(
                upload_url,
                content=full_body,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
                timeout=120.0,
            )
            response.raise_for_status()
            result = response.json()

        return {
            "status": "uploaded",
            "format": "docx",
            "id": result.get("id"),
            "name": result.get("name"),
            "mimeType": result.get("mimeType"),
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
