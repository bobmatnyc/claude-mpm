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
import subprocess  # nosec B404
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import httpx

if TYPE_CHECKING:
    from claude_mpm.mcp.rclone_manager import RcloneManager
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from claude_mpm.auth import OAuthManager, TokenStatus, TokenStorage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service name for token storage - matches gworkspace-mcp convention
SERVICE_NAME = "gworkspace-mcp"

# Google API base URLs
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
DOCS_API_BASE = "https://docs.googleapis.com/v1"
TASKS_API_BASE = "https://tasks.googleapis.com/tasks/v1"


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
        self.server = Server("gworkspace-mcp")
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
                    name="create_calendar",
                    description="Create a new calendar",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "Calendar title/name",
                            },
                            "description": {
                                "type": "string",
                                "description": "Calendar description (optional)",
                            },
                            "timezone": {
                                "type": "string",
                                "description": "Calendar timezone (e.g., 'America/New_York', optional)",
                            },
                        },
                        "required": ["summary"],
                    },
                ),
                Tool(
                    name="update_calendar",
                    description="Update an existing calendar's properties",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID to update",
                            },
                            "summary": {
                                "type": "string",
                                "description": "New calendar title/name (optional)",
                            },
                            "description": {
                                "type": "string",
                                "description": "New calendar description (optional)",
                            },
                            "timezone": {
                                "type": "string",
                                "description": "New calendar timezone (optional)",
                            },
                        },
                        "required": ["calendar_id"],
                    },
                ),
                Tool(
                    name="delete_calendar",
                    description="Delete a calendar (cannot delete primary calendar)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID to delete",
                            },
                        },
                        "required": ["calendar_id"],
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
                    description="Search Google Drive files using a query string. Bare search terms like 'MSA' are automatically wrapped in 'fullText contains' syntax. You can also use Drive API query syntax directly (e.g., 'name contains \"report\"', 'mimeType = \"application/pdf\"').",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query - can be simple terms (auto-wrapped) or Drive API syntax (e.g., 'name contains \"report\"')",
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
                Tool(
                    name="add_document_comment",
                    description="Add a new comment to a Google Docs, Sheets, or Slides file. Comments appear in the document's comment sidebar. Write concise, actionable comments.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {
                                "type": "string",
                                "description": "Google Drive file ID (from the document URL)",
                            },
                            "content": {
                                "type": "string",
                                "description": "The comment text. Style guidelines: Be brief and direct (1-2 sentences). Focus on specific, actionable feedback. Avoid filler phrases like 'I think' or 'Maybe consider'. Use imperative mood for suggestions (e.g., 'Add error handling' not 'You might want to add error handling').",
                            },
                            "anchor": {
                                "type": "string",
                                "description": "Optional JSON string specifying the anchor location in the document (for anchored comments)",
                            },
                        },
                        "required": ["file_id", "content"],
                    },
                ),
                Tool(
                    name="reply_to_comment",
                    description="Reply to an existing comment on a Google Docs, Sheets, or Slides file. Write concise replies that directly address the comment.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_id": {
                                "type": "string",
                                "description": "Google Drive file ID (from the document URL)",
                            },
                            "comment_id": {
                                "type": "string",
                                "description": "The ID of the comment to reply to (from list_document_comments)",
                            },
                            "content": {
                                "type": "string",
                                "description": "The reply text. Style guidelines: Be brief (1-2 sentences max). Directly address the original comment. State resolution clearly ('Done', 'Fixed', 'Won't fix because X'). No pleasantries or filler.",
                            },
                        },
                        "required": ["file_id", "comment_id", "content"],
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
                # Gmail Label Management
                Tool(
                    name="list_gmail_labels",
                    description="List all Gmail labels (system and custom)",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                ),
                Tool(
                    name="create_gmail_label",
                    description="Create a custom Gmail label. Use '/' for nesting (e.g., 'Work/Projects')",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Label name (use '/' for nesting, e.g., 'Work/Projects')",
                            },
                            "label_list_visibility": {
                                "type": "string",
                                "enum": ["labelShow", "labelShowIfUnread", "labelHide"],
                                "description": "Visibility in label list (default: labelShow)",
                            },
                            "message_list_visibility": {
                                "type": "string",
                                "enum": ["show", "hide"],
                                "description": "Visibility in message list (default: show)",
                            },
                        },
                        "required": ["name"],
                    },
                ),
                Tool(
                    name="delete_gmail_label",
                    description="Delete a custom Gmail label (cannot delete system labels)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "label_id": {
                                "type": "string",
                                "description": "Label ID to delete",
                            },
                        },
                        "required": ["label_id"],
                    },
                ),
                # Gmail Message Management
                Tool(
                    name="modify_gmail_message",
                    description="Add or remove labels from a Gmail message (core label operation)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message_id": {
                                "type": "string",
                                "description": "Message ID to modify",
                            },
                            "add_label_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Label IDs to add (e.g., ['STARRED', 'IMPORTANT'])",
                            },
                            "remove_label_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Label IDs to remove (e.g., ['UNREAD', 'INBOX'])",
                            },
                        },
                        "required": ["message_id"],
                    },
                ),
                Tool(
                    name="archive_gmail_message",
                    description="Archive a Gmail message (removes from INBOX, keeps in All Mail)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message_id": {
                                "type": "string",
                                "description": "Message ID to archive",
                            },
                        },
                        "required": ["message_id"],
                    },
                ),
                Tool(
                    name="trash_gmail_message",
                    description="Move a Gmail message to trash",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message_id": {
                                "type": "string",
                                "description": "Message ID to trash",
                            },
                        },
                        "required": ["message_id"],
                    },
                ),
                Tool(
                    name="untrash_gmail_message",
                    description="Restore a Gmail message from trash",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message_id": {
                                "type": "string",
                                "description": "Message ID to restore from trash",
                            },
                        },
                        "required": ["message_id"],
                    },
                ),
                Tool(
                    name="mark_gmail_as_read",
                    description="Mark a Gmail message as read",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message_id": {
                                "type": "string",
                                "description": "Message ID to mark as read",
                            },
                        },
                        "required": ["message_id"],
                    },
                ),
                Tool(
                    name="mark_gmail_as_unread",
                    description="Mark a Gmail message as unread",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message_id": {
                                "type": "string",
                                "description": "Message ID to mark as unread",
                            },
                        },
                        "required": ["message_id"],
                    },
                ),
                Tool(
                    name="star_gmail_message",
                    description="Add star to a Gmail message",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message_id": {
                                "type": "string",
                                "description": "Message ID to star",
                            },
                        },
                        "required": ["message_id"],
                    },
                ),
                Tool(
                    name="unstar_gmail_message",
                    description="Remove star from a Gmail message",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message_id": {
                                "type": "string",
                                "description": "Message ID to unstar",
                            },
                        },
                        "required": ["message_id"],
                    },
                ),
                # Gmail Batch Operations
                Tool(
                    name="batch_modify_gmail_messages",
                    description="Add or remove labels from multiple Gmail messages at once. Uses Gmail's efficient batch API.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of message IDs to modify",
                            },
                            "add_label_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Label IDs to add (e.g., ['STARRED', 'IMPORTANT', or custom label IDs])",
                            },
                            "remove_label_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Label IDs to remove (e.g., ['UNREAD', 'INBOX'])",
                            },
                        },
                        "required": ["message_ids"],
                    },
                ),
                Tool(
                    name="batch_archive_gmail_messages",
                    description="Archive multiple Gmail messages at once (removes INBOX label, keeps in All Mail)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of message IDs to archive",
                            },
                        },
                        "required": ["message_ids"],
                    },
                ),
                Tool(
                    name="batch_trash_gmail_messages",
                    description="Move multiple Gmail messages to trash at once",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of message IDs to trash",
                            },
                        },
                        "required": ["message_ids"],
                    },
                ),
                Tool(
                    name="batch_mark_gmail_as_read",
                    description="Mark multiple Gmail messages as read at once",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of message IDs to mark as read",
                            },
                        },
                        "required": ["message_ids"],
                    },
                ),
                Tool(
                    name="batch_delete_gmail_messages",
                    description="Permanently delete multiple Gmail messages at once (CAUTION: cannot be undone)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of message IDs to permanently delete",
                            },
                        },
                        "required": ["message_ids"],
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
                    description="Get the content and structure of a Google Doc. Optionally include tab content for documents with multiple tabs.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "Google Doc ID",
                            },
                            "include_tabs_content": {
                                "type": "boolean",
                                "description": "Whether to include tab content (default: False). Set to True for documents with tabs.",
                                "default": False,
                            },
                        },
                        "required": ["document_id"],
                    },
                ),
                # Google Docs Tab Operations
                Tool(
                    name="list_document_tabs",
                    description="List all tabs in a Google Doc with their metadata (tabId, title, index, nestingLevel, iconEmoji, parentTabId). Use this to discover tabs in a document.",
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
                    name="get_tab_content",
                    description="Get the content from a specific tab in a Google Doc. Returns tab metadata and text content.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "Google Doc ID",
                            },
                            "tab_id": {
                                "type": "string",
                                "description": "Tab ID (from list_document_tabs)",
                            },
                        },
                        "required": ["document_id", "tab_id"],
                    },
                ),
                Tool(
                    name="create_document_tab",
                    description="Create a new tab in a Google Doc. Tabs can be nested by specifying a parent tab ID. Returns the new tab ID.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "Google Doc ID",
                            },
                            "title": {
                                "type": "string",
                                "description": "Tab title",
                            },
                            "icon_emoji": {
                                "type": "string",
                                "description": "Icon emoji for the tab (optional, e.g., '📄', '✨')",
                            },
                            "parent_tab_id": {
                                "type": "string",
                                "description": "Parent tab ID for nested tabs (optional). Creates a child tab under the specified parent.",
                            },
                            "index": {
                                "type": "integer",
                                "description": "Position index for the tab (optional). 0 inserts at the beginning.",
                            },
                        },
                        "required": ["document_id", "title"],
                    },
                ),
                Tool(
                    name="update_tab_properties",
                    description="Update properties of an existing tab (title, iconEmoji). Use this to rename tabs or change their icon.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "Google Doc ID",
                            },
                            "tab_id": {
                                "type": "string",
                                "description": "Tab ID to update (from list_document_tabs)",
                            },
                            "title": {
                                "type": "string",
                                "description": "New tab title (optional)",
                            },
                            "icon_emoji": {
                                "type": "string",
                                "description": "New icon emoji (optional, e.g., '📝', '⭐')",
                            },
                        },
                        "required": ["document_id", "tab_id"],
                    },
                ),
                Tool(
                    name="move_tab",
                    description="Move a tab to a new position or change its parent (nesting level). Use this to reorganize tab hierarchy.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "Google Doc ID",
                            },
                            "tab_id": {
                                "type": "string",
                                "description": "Tab ID to move (from list_document_tabs)",
                            },
                            "new_parent_tab_id": {
                                "type": "string",
                                "description": "New parent tab ID (optional). Use empty string to move to root level.",
                            },
                            "new_index": {
                                "type": "integer",
                                "description": "New position index (optional). 0 moves to the beginning of its level.",
                            },
                        },
                        "required": ["document_id", "tab_id"],
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
                Tool(
                    name="render_mermaid_to_doc",
                    description="Render Mermaid diagram code to an image and insert it into a Google Doc. Uses @mermaid-js/mermaid-cli to render diagrams to SVG or PNG format, uploads to Drive, then inserts into the document.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "Google Doc ID where the image will be inserted",
                            },
                            "mermaid_code": {
                                "type": "string",
                                "description": "Mermaid diagram code (e.g., 'graph TD\\n    A-->B')",
                            },
                            "insert_index": {
                                "type": "integer",
                                "description": "Character index where to insert the image. If not provided, appends to end of document.",
                            },
                            "image_format": {
                                "type": "string",
                                "description": "Output image format: 'svg' (default, best quality) or 'png'",
                                "default": "svg",
                                "enum": ["svg", "png"],
                            },
                            "width_pt": {
                                "type": "integer",
                                "description": "Image width in points (optional, maintains aspect ratio if only one dimension specified)",
                            },
                            "height_pt": {
                                "type": "integer",
                                "description": "Image height in points (optional, maintains aspect ratio if only one dimension specified)",
                            },
                        },
                        "required": ["document_id", "mermaid_code"],
                    },
                ),
                # Google Tasks API - Task Lists Operations
                Tool(
                    name="list_task_lists",
                    description="List all task lists for the authenticated user",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of task lists to return (default: 100)",
                                "default": 100,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="get_task_list",
                    description="Get a specific task list by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tasklist_id": {
                                "type": "string",
                                "description": "Task list ID",
                            },
                        },
                        "required": ["tasklist_id"],
                    },
                ),
                Tool(
                    name="create_task_list",
                    description="Create a new task list",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Title of the new task list",
                            },
                        },
                        "required": ["title"],
                    },
                ),
                Tool(
                    name="update_task_list",
                    description="Update an existing task list",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tasklist_id": {
                                "type": "string",
                                "description": "Task list ID to update",
                            },
                            "title": {
                                "type": "string",
                                "description": "New title for the task list",
                            },
                        },
                        "required": ["tasklist_id", "title"],
                    },
                ),
                Tool(
                    name="delete_task_list",
                    description="Delete a task list",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tasklist_id": {
                                "type": "string",
                                "description": "Task list ID to delete",
                            },
                        },
                        "required": ["tasklist_id"],
                    },
                ),
                # Google Tasks API - Tasks Operations
                Tool(
                    name="list_tasks",
                    description="List all tasks in a task list",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tasklist_id": {
                                "type": "string",
                                "description": "Task list ID (default: '@default' for the default list)",
                                "default": "@default",
                            },
                            "show_completed": {
                                "type": "boolean",
                                "description": "Include completed tasks (default: true)",
                                "default": True,
                            },
                            "show_hidden": {
                                "type": "boolean",
                                "description": "Include hidden tasks (default: false)",
                                "default": False,
                            },
                            "due_min": {
                                "type": "string",
                                "description": "Lower bound for due date (RFC3339 format)",
                            },
                            "due_max": {
                                "type": "string",
                                "description": "Upper bound for due date (RFC3339 format)",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of tasks to return (default: 100)",
                                "default": 100,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="get_task",
                    description="Get a specific task by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tasklist_id": {
                                "type": "string",
                                "description": "Task list ID (default: '@default')",
                                "default": "@default",
                            },
                            "task_id": {
                                "type": "string",
                                "description": "Task ID",
                            },
                        },
                        "required": ["task_id"],
                    },
                ),
                Tool(
                    name="search_tasks",
                    description="Search tasks across all task lists by title or notes content",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query to match against task titles and notes",
                            },
                            "show_completed": {
                                "type": "boolean",
                                "description": "Include completed tasks in search (default: true)",
                                "default": True,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="create_task",
                    description="Create a new task in a task list",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tasklist_id": {
                                "type": "string",
                                "description": "Task list ID (default: '@default')",
                                "default": "@default",
                            },
                            "title": {
                                "type": "string",
                                "description": "Task title",
                            },
                            "notes": {
                                "type": "string",
                                "description": "Task notes/description",
                            },
                            "due": {
                                "type": "string",
                                "description": "Due date in RFC3339 format (e.g., '2024-01-15T00:00:00Z')",
                            },
                            "parent": {
                                "type": "string",
                                "description": "Parent task ID for creating subtasks",
                            },
                        },
                        "required": ["title"],
                    },
                ),
                Tool(
                    name="update_task",
                    description="Update an existing task",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tasklist_id": {
                                "type": "string",
                                "description": "Task list ID (default: '@default')",
                                "default": "@default",
                            },
                            "task_id": {
                                "type": "string",
                                "description": "Task ID to update",
                            },
                            "title": {
                                "type": "string",
                                "description": "New task title",
                            },
                            "notes": {
                                "type": "string",
                                "description": "New task notes/description",
                            },
                            "due": {
                                "type": "string",
                                "description": "New due date in RFC3339 format",
                            },
                            "status": {
                                "type": "string",
                                "description": "Task status: 'needsAction' or 'completed'",
                                "enum": ["needsAction", "completed"],
                            },
                        },
                        "required": ["task_id"],
                    },
                ),
                Tool(
                    name="complete_task",
                    description="Mark a task as completed",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tasklist_id": {
                                "type": "string",
                                "description": "Task list ID (default: '@default')",
                                "default": "@default",
                            },
                            "task_id": {
                                "type": "string",
                                "description": "Task ID to complete",
                            },
                        },
                        "required": ["task_id"],
                    },
                ),
                Tool(
                    name="delete_task",
                    description="Delete a task",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tasklist_id": {
                                "type": "string",
                                "description": "Task list ID (default: '@default')",
                                "default": "@default",
                            },
                            "task_id": {
                                "type": "string",
                                "description": "Task ID to delete",
                            },
                        },
                        "required": ["task_id"],
                    },
                ),
                Tool(
                    name="move_task",
                    description="Move a task to a different position or make it a subtask",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tasklist_id": {
                                "type": "string",
                                "description": "Task list ID (default: '@default')",
                                "default": "@default",
                            },
                            "task_id": {
                                "type": "string",
                                "description": "Task ID to move",
                            },
                            "parent": {
                                "type": "string",
                                "description": "New parent task ID (to make this task a subtask)",
                            },
                            "previous": {
                                "type": "string",
                                "description": "Task ID to position this task after",
                            },
                        },
                        "required": ["task_id"],
                    },
                ),
                # Rclone-based Drive file sync operations
                Tool(
                    name="list_drive_contents",
                    description="List contents of a Google Drive folder using rclone. Returns structured JSON with file metadata including size, modification time, and file IDs. Requires rclone to be installed.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Drive path to list (e.g., 'Documents' or 'Shared drives/TeamDrive/Projects')",
                                "default": "",
                            },
                            "recursive": {
                                "type": "boolean",
                                "description": "Recursively list all subdirectories",
                                "default": False,
                            },
                            "files_only": {
                                "type": "boolean",
                                "description": "Show only files, not directories",
                                "default": False,
                            },
                            "include_hash": {
                                "type": "boolean",
                                "description": "Include MD5 hash for each file",
                                "default": False,
                            },
                            "max_depth": {
                                "type": "integer",
                                "description": "Maximum recursion depth (requires recursive=true, -1 for unlimited)",
                                "default": -1,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="download_drive_folder",
                    description="Download a folder from Google Drive to local filesystem using rclone. Does not delete local files. Requires rclone to be installed.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "drive_path": {
                                "type": "string",
                                "description": "Path in Google Drive to download (e.g., 'Documents/Reports')",
                            },
                            "local_path": {
                                "type": "string",
                                "description": "Local destination directory",
                            },
                            "google_docs_format": {
                                "type": "string",
                                "description": "Export format for Google Docs/Sheets/Slides",
                                "enum": [
                                    "docx",
                                    "pdf",
                                    "odt",
                                    "txt",
                                    "xlsx",
                                    "csv",
                                    "pptx",
                                ],
                                "default": "docx",
                            },
                            "exclude": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Patterns to exclude (e.g., ['*.tmp', '.git/**'])",
                            },
                            "dry_run": {
                                "type": "boolean",
                                "description": "Preview changes without downloading",
                                "default": False,
                            },
                        },
                        "required": ["drive_path", "local_path"],
                    },
                ),
                Tool(
                    name="upload_to_drive",
                    description="Upload a local folder to Google Drive using rclone. Does not delete files in Drive. Requires rclone to be installed.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "local_path": {
                                "type": "string",
                                "description": "Local folder path to upload",
                            },
                            "drive_path": {
                                "type": "string",
                                "description": "Destination path in Google Drive",
                            },
                            "convert_to_google_docs": {
                                "type": "boolean",
                                "description": "Convert Office files to Google Docs format",
                                "default": False,
                            },
                            "exclude": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Patterns to exclude (e.g., ['node_modules/**', '.git/**'])",
                            },
                            "dry_run": {
                                "type": "boolean",
                                "description": "Preview changes without uploading",
                                "default": False,
                            },
                        },
                        "required": ["local_path", "drive_path"],
                    },
                ),
                Tool(
                    name="sync_drive_folder",
                    description="Sync files between local filesystem and Google Drive using rclone. Use dry_run=true to preview changes before syncing. Requires rclone to be installed.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "source": {
                                "type": "string",
                                "description": "Source path. Use 'drive:path' for Drive or '/local/path' for local",
                            },
                            "destination": {
                                "type": "string",
                                "description": "Destination path. Use 'drive:path' for Drive or '/local/path' for local",
                            },
                            "dry_run": {
                                "type": "boolean",
                                "description": "Preview changes without making them (RECOMMENDED: start with true)",
                                "default": True,
                            },
                            "delete_extra": {
                                "type": "boolean",
                                "description": "Delete files in destination that don't exist in source (CAUTION: destructive)",
                                "default": False,
                            },
                            "exclude": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Patterns to exclude (e.g., ['*.tmp', '.git/**'])",
                            },
                            "include": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Patterns to include (if set, only matching files are synced)",
                            },
                        },
                        "required": ["source", "destination"],
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
            "create_calendar": self._create_calendar,
            "update_calendar": self._update_calendar,
            "delete_calendar": self._delete_calendar,
            "get_events": self._get_events,
            "search_gmail_messages": self._search_gmail_messages,
            "get_gmail_message_content": self._get_gmail_message_content,
            "search_drive_files": self._search_drive_files,
            "get_drive_file_content": self._get_drive_file_content,
            "list_document_comments": self._list_document_comments,
            "add_document_comment": self._add_document_comment,
            "reply_to_comment": self._reply_to_comment,
            # Calendar write operations
            "create_event": self._create_event,
            "update_event": self._update_event,
            "delete_event": self._delete_event,
            # Gmail write operations
            "send_email": self._send_email,
            "create_draft": self._create_draft,
            "reply_to_email": self._reply_to_email,
            # Gmail label management
            "list_gmail_labels": self._list_gmail_labels,
            "create_gmail_label": self._create_gmail_label,
            "delete_gmail_label": self._delete_gmail_label,
            # Gmail message management
            "modify_gmail_message": self._modify_gmail_message,
            "archive_gmail_message": self._archive_gmail_message,
            "trash_gmail_message": self._trash_gmail_message,
            "untrash_gmail_message": self._untrash_gmail_message,
            "mark_gmail_as_read": self._mark_gmail_as_read,
            "mark_gmail_as_unread": self._mark_gmail_as_unread,
            "star_gmail_message": self._star_gmail_message,
            "unstar_gmail_message": self._unstar_gmail_message,
            # Gmail batch operations
            "batch_modify_gmail_messages": self._batch_modify_gmail_messages,
            "batch_archive_gmail_messages": self._batch_archive_gmail_messages,
            "batch_trash_gmail_messages": self._batch_trash_gmail_messages,
            "batch_mark_gmail_as_read": self._batch_mark_gmail_as_read,
            "batch_delete_gmail_messages": self._batch_delete_gmail_messages,
            # Drive write operations
            "create_drive_folder": self._create_drive_folder,
            "upload_drive_file": self._upload_drive_file,
            "delete_drive_file": self._delete_drive_file,
            "move_drive_file": self._move_drive_file,
            # Docs write operations
            "create_document": self._create_document,
            "append_to_document": self._append_to_document,
            "get_document": self._get_document,
            # Docs tab operations
            "list_document_tabs": self._list_document_tabs,
            "get_tab_content": self._get_tab_content,
            "create_document_tab": self._create_document_tab,
            "update_tab_properties": self._update_tab_properties,
            "move_tab": self._move_tab,
            # Markdown conversion
            "upload_markdown_as_doc": self._upload_markdown_as_doc,
            # Mermaid diagram rendering
            "render_mermaid_to_doc": self._render_mermaid_to_doc,
            # Tasks - Task Lists operations
            "list_task_lists": self._list_task_lists,
            "get_task_list": self._get_task_list,
            "create_task_list": self._create_task_list,
            "update_task_list": self._update_task_list,
            "delete_task_list": self._delete_task_list,
            # Tasks - Task operations
            "list_tasks": self._list_tasks,
            "get_task": self._get_task,
            "search_tasks": self._search_tasks,
            "create_task": self._create_task,
            "update_task": self._update_task,
            "complete_task": self._complete_task,
            "delete_task": self._delete_task,
            "move_task": self._move_task,
            # Rclone Drive sync operations
            "list_drive_contents": self._list_drive_contents,
            "download_drive_folder": self._download_drive_folder,
            "upload_to_drive": self._upload_to_drive,
            "sync_drive_folder": self._sync_drive_folder,
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

    async def _create_calendar(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Create a new calendar.

        Args:
            arguments: Tool arguments with summary, description, and timezone.

        Returns:
            Created calendar details.
        """
        summary = arguments["summary"]
        description = arguments.get("description")
        timezone = arguments.get("timezone")

        url = f"{CALENDAR_API_BASE}/calendars"

        calendar_body: dict[str, Any] = {
            "summary": summary,
        }

        if description:
            calendar_body["description"] = description
        if timezone:
            calendar_body["timeZone"] = timezone

        response = await self._make_request("POST", url, json_data=calendar_body)

        return {
            "status": "created",
            "id": response.get("id"),
            "summary": response.get("summary"),
            "description": response.get("description"),
            "timezone": response.get("timeZone"),
        }

    async def _update_calendar(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Update an existing calendar's properties.

        Args:
            arguments: Tool arguments with calendar_id and optional summary, description, timezone.

        Returns:
            Updated calendar details.
        """
        calendar_id = arguments["calendar_id"]
        summary = arguments.get("summary")
        description = arguments.get("description")
        timezone = arguments.get("timezone")

        # Build update body with only provided fields
        update_body: dict[str, Any] = {}
        if summary:
            update_body["summary"] = summary
        if description:
            update_body["description"] = description
        if timezone:
            update_body["timeZone"] = timezone

        if not update_body:
            raise ValueError(
                "At least one field (summary, description, or timezone) must be provided for update"
            )

        url = f"{CALENDAR_API_BASE}/calendars/{calendar_id}"
        response = await self._make_request("PATCH", url, json_data=update_body)

        return {
            "status": "updated",
            "id": response.get("id"),
            "summary": response.get("summary"),
            "description": response.get("description"),
            "timezone": response.get("timeZone"),
        }

    async def _delete_calendar(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Delete a calendar.

        Args:
            arguments: Tool arguments with calendar_id.

        Returns:
            Deletion confirmation.
        """
        calendar_id = arguments["calendar_id"]

        # Prevent deletion of primary calendar
        if calendar_id == "primary":
            raise ValueError("Cannot delete the primary calendar")

        url = f"{CALENDAR_API_BASE}/calendars/{calendar_id}"
        await self._make_request("DELETE", url)

        return {
            "status": "deleted",
            "calendar_id": calendar_id,
        }

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

    def _normalize_drive_query(self, query: str) -> str:
        """Normalize a search query for Google Drive API.

        If the query doesn't contain Drive API operators, wrap it in fullText contains.

        Args:
            query: Raw search query from user

        Returns:
            Properly formatted Drive API query
        """
        # List of Drive API query operators
        operators = ["contains", "=", "!=", "<", ">", " in ", " has ", " not "]

        # Check if query already uses API syntax
        query_lower = query.lower()
        if any(op in query_lower for op in operators):
            return query

        # Wrap bare terms in fullText contains
        # Escape single quotes in the query
        escaped_query = query.replace("'", "\\'")
        return f"fullText contains '{escaped_query}'"

    async def _search_drive_files(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Search Google Drive files.

        Args:
            arguments: Tool arguments with query and max_results.

        Returns:
            List of files with id, name, mimeType, modifiedTime.
        """
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 10)

        # Normalize the query to handle bare search terms
        normalized_query = self._normalize_drive_query(query)

        url = f"{DRIVE_API_BASE}/files"
        params = {
            "q": normalized_query,
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

    async def _add_document_comment(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Add a comment to a Google Drive file (Docs, Sheets, Slides).

        Args:
            arguments: Tool arguments with file_id, content, and optional anchor.

        Returns:
            Created comment details with id, author, and timestamps.
        """
        file_id = arguments["file_id"]
        content = arguments["content"]
        anchor = arguments.get("anchor")

        # Build request URL
        url = f"{DRIVE_API_BASE}/files/{file_id}/comments"
        params = {
            "fields": "id,content,author(displayName,emailAddress),createdTime,modifiedTime,resolved",
        }

        # Build request body
        body: dict[str, Any] = {"content": content}
        if anchor:
            # Parse anchor if provided as JSON string
            try:
                body["anchor"] = (
                    json.loads(anchor) if isinstance(anchor, str) else anchor
                )
            except json.JSONDecodeError:
                # If not valid JSON, treat as raw anchor string
                body["anchor"] = anchor

        response = await self._make_request("POST", url, params=params, json_data=body)

        # Format the response
        author = response.get("author", {})
        return {
            "id": response.get("id"),
            "content": response.get("content", ""),
            "author_name": author.get("displayName", "Unknown"),
            "author_email": author.get("emailAddress", ""),
            "created_time": response.get("createdTime", ""),
            "modified_time": response.get("modifiedTime", ""),
            "resolved": response.get("resolved", False),
            "message": "Comment added successfully.",
        }

    async def _reply_to_comment(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Reply to an existing comment on a Google Drive file.

        Args:
            arguments: Tool arguments with file_id, comment_id, and content.

        Returns:
            Created reply details with id, author, and timestamps.
        """
        file_id = arguments["file_id"]
        comment_id = arguments["comment_id"]
        content = arguments["content"]

        # Build request URL
        url = f"{DRIVE_API_BASE}/files/{file_id}/comments/{comment_id}/replies"
        params = {
            "fields": "id,content,author(displayName,emailAddress),createdTime,modifiedTime",
        }

        # Build request body
        body = {"content": content}

        response = await self._make_request("POST", url, params=params, json_data=body)

        # Format the response
        author = response.get("author", {})
        return {
            "id": response.get("id"),
            "content": response.get("content", ""),
            "author_name": author.get("displayName", "Unknown"),
            "author_email": author.get("emailAddress", ""),
            "created_time": response.get("createdTime", ""),
            "modified_time": response.get("modifiedTime", ""),
            "comment_id": comment_id,
            "message": "Reply added successfully.",
        }

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
    # Gmail Label Management
    # =========================================================================

    async def _list_gmail_labels(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List all Gmail labels (system and custom).

        Args:
            arguments: Tool arguments (none required).

        Returns:
            List of all labels with their properties.
        """
        url = f"{GMAIL_API_BASE}/users/me/labels"
        response = await self._make_request("GET", url)

        labels = []
        for label in response.get("labels", []):
            labels.append(
                {
                    "id": label.get("id"),
                    "name": label.get("name"),
                    "type": label.get("type"),  # system or user
                    "message_list_visibility": label.get("messageListVisibility"),
                    "label_list_visibility": label.get("labelListVisibility"),
                }
            )

        # Sort labels: system labels first, then user labels alphabetically
        system_labels = sorted(
            [l for l in labels if l["type"] == "system"], key=lambda x: x["name"]
        )
        user_labels = sorted(
            [l for l in labels if l["type"] == "user"], key=lambda x: x["name"]
        )

        return {
            "total": len(labels),
            "system_labels": system_labels,
            "user_labels": user_labels,
        }

    async def _create_gmail_label(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Create a custom Gmail label.

        Args:
            arguments: Tool arguments with name and optional visibility settings.

        Returns:
            Created label details.
        """
        name = arguments["name"]
        label_list_visibility = arguments.get("label_list_visibility", "labelShow")
        message_list_visibility = arguments.get("message_list_visibility", "show")

        url = f"{GMAIL_API_BASE}/users/me/labels"
        label_body = {
            "name": name,
            "labelListVisibility": label_list_visibility,
            "messageListVisibility": message_list_visibility,
        }

        response = await self._make_request("POST", url, json_data=label_body)

        return {
            "status": "label_created",
            "id": response.get("id"),
            "name": response.get("name"),
            "type": response.get("type"),
            "label_list_visibility": response.get("labelListVisibility"),
            "message_list_visibility": response.get("messageListVisibility"),
        }

    async def _delete_gmail_label(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Delete a custom Gmail label.

        Args:
            arguments: Tool arguments with label_id.

        Returns:
            Deletion confirmation.
        """
        label_id = arguments["label_id"]

        url = f"{GMAIL_API_BASE}/users/me/labels/{label_id}"
        access_token = await self._get_access_token()

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            response.raise_for_status()

        return {
            "status": "label_deleted",
            "label_id": label_id,
        }

    # =========================================================================
    # Gmail Message Management
    # =========================================================================

    async def _modify_gmail_message(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Add or remove labels from a Gmail message.

        This is the core label modification operation. Other convenience methods
        (archive, star, mark_as_read, etc.) use this internally.

        Args:
            arguments: Tool arguments with message_id and optional add_label_ids/remove_label_ids.

        Returns:
            Modified message details.
        """
        message_id = arguments["message_id"]
        add_label_ids = arguments.get("add_label_ids", [])
        remove_label_ids = arguments.get("remove_label_ids", [])

        url = f"{GMAIL_API_BASE}/users/me/messages/{message_id}/modify"
        modify_body: dict[str, Any] = {}

        if add_label_ids:
            modify_body["addLabelIds"] = add_label_ids
        if remove_label_ids:
            modify_body["removeLabelIds"] = remove_label_ids

        response = await self._make_request("POST", url, json_data=modify_body)

        return {
            "status": "message_modified",
            "id": response.get("id"),
            "thread_id": response.get("threadId"),
            "label_ids": response.get("labelIds", []),
        }

    async def _archive_gmail_message(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Archive a Gmail message (removes from INBOX).

        Args:
            arguments: Tool arguments with message_id.

        Returns:
            Archived message details.
        """
        message_id = arguments["message_id"]

        result = await self._modify_gmail_message(
            {
                "message_id": message_id,
                "remove_label_ids": ["INBOX"],
            }
        )

        return {
            "status": "message_archived",
            "id": result.get("id"),
            "thread_id": result.get("thread_id"),
            "label_ids": result.get("label_ids", []),
        }

    async def _trash_gmail_message(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Move a Gmail message to trash.

        Args:
            arguments: Tool arguments with message_id.

        Returns:
            Trashed message details.
        """
        message_id = arguments["message_id"]

        url = f"{GMAIL_API_BASE}/users/me/messages/{message_id}/trash"
        response = await self._make_request("POST", url)

        return {
            "status": "message_trashed",
            "id": response.get("id"),
            "thread_id": response.get("threadId"),
            "label_ids": response.get("labelIds", []),
        }

    async def _untrash_gmail_message(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Restore a Gmail message from trash.

        Args:
            arguments: Tool arguments with message_id.

        Returns:
            Restored message details.
        """
        message_id = arguments["message_id"]

        url = f"{GMAIL_API_BASE}/users/me/messages/{message_id}/untrash"
        response = await self._make_request("POST", url)

        return {
            "status": "message_restored",
            "id": response.get("id"),
            "thread_id": response.get("threadId"),
            "label_ids": response.get("labelIds", []),
        }

    async def _mark_gmail_as_read(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Mark a Gmail message as read.

        Args:
            arguments: Tool arguments with message_id.

        Returns:
            Modified message details.
        """
        message_id = arguments["message_id"]

        result = await self._modify_gmail_message(
            {
                "message_id": message_id,
                "remove_label_ids": ["UNREAD"],
            }
        )

        return {
            "status": "message_marked_as_read",
            "id": result.get("id"),
            "thread_id": result.get("thread_id"),
            "label_ids": result.get("label_ids", []),
        }

    async def _mark_gmail_as_unread(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Mark a Gmail message as unread.

        Args:
            arguments: Tool arguments with message_id.

        Returns:
            Modified message details.
        """
        message_id = arguments["message_id"]

        result = await self._modify_gmail_message(
            {
                "message_id": message_id,
                "add_label_ids": ["UNREAD"],
            }
        )

        return {
            "status": "message_marked_as_unread",
            "id": result.get("id"),
            "thread_id": result.get("thread_id"),
            "label_ids": result.get("label_ids", []),
        }

    async def _star_gmail_message(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Add star to a Gmail message.

        Args:
            arguments: Tool arguments with message_id.

        Returns:
            Modified message details.
        """
        message_id = arguments["message_id"]

        result = await self._modify_gmail_message(
            {
                "message_id": message_id,
                "add_label_ids": ["STARRED"],
            }
        )

        return {
            "status": "message_starred",
            "id": result.get("id"),
            "thread_id": result.get("thread_id"),
            "label_ids": result.get("label_ids", []),
        }

    async def _unstar_gmail_message(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Remove star from a Gmail message.

        Args:
            arguments: Tool arguments with message_id.

        Returns:
            Modified message details.
        """
        message_id = arguments["message_id"]

        result = await self._modify_gmail_message(
            {
                "message_id": message_id,
                "remove_label_ids": ["STARRED"],
            }
        )

        return {
            "status": "message_unstarred",
            "id": result.get("id"),
            "thread_id": result.get("thread_id"),
            "label_ids": result.get("label_ids", []),
        }

    # =========================================================================
    # Gmail Batch Operations
    # =========================================================================

    async def _batch_modify_gmail_messages(
        self, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Add or remove labels from multiple Gmail messages using batch API.

        Args:
            arguments: Tool arguments with message_ids and optional
                add_label_ids/remove_label_ids.

        Returns:
            Batch operation result with success count.
        """
        message_ids = arguments.get("message_ids", [])
        add_label_ids = arguments.get("add_label_ids", [])
        remove_label_ids = arguments.get("remove_label_ids", [])

        if not message_ids:
            return {
                "status": "no_messages",
                "message": "No message IDs provided",
                "modified_count": 0,
            }

        # Use Gmail's batchModify endpoint for efficiency
        url = f"{GMAIL_API_BASE}/users/me/messages/batchModify"
        batch_body: dict[str, Any] = {"ids": message_ids}

        if add_label_ids:
            batch_body["addLabelIds"] = add_label_ids
        if remove_label_ids:
            batch_body["removeLabelIds"] = remove_label_ids

        await self._make_request("POST", url, json_data=batch_body)

        return {
            "status": "messages_modified",
            "modified_count": len(message_ids),
            "add_label_ids": add_label_ids,
            "remove_label_ids": remove_label_ids,
        }

    async def _batch_archive_gmail_messages(
        self, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Archive multiple Gmail messages at once.

        Args:
            arguments: Tool arguments with message_ids.

        Returns:
            Batch operation result with success count.
        """
        message_ids = arguments.get("message_ids", [])

        if not message_ids:
            return {
                "status": "no_messages",
                "message": "No message IDs provided",
                "archived_count": 0,
            }

        result = await self._batch_modify_gmail_messages(
            {
                "message_ids": message_ids,
                "remove_label_ids": ["INBOX"],
            }
        )

        return {
            "status": "messages_archived",
            "archived_count": result.get("modified_count", 0),
        }

    async def _batch_trash_gmail_messages(
        self, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Move multiple Gmail messages to trash at once.

        Note: Gmail doesn't have a batch trash endpoint, so we process
        messages concurrently for efficiency.

        Args:
            arguments: Tool arguments with message_ids.

        Returns:
            Batch operation result with success/failure counts.
        """
        message_ids = arguments.get("message_ids", [])

        if not message_ids:
            return {
                "status": "no_messages",
                "message": "No message IDs provided",
                "trashed_count": 0,
                "failed_count": 0,
            }

        # Process concurrently since there's no batch trash endpoint
        async def trash_single(msg_id: str) -> tuple[str, bool]:
            try:
                url = f"{GMAIL_API_BASE}/users/me/messages/{msg_id}/trash"
                await self._make_request("POST", url)
                return msg_id, True
            except Exception:
                return msg_id, False

        results = await asyncio.gather(
            *[trash_single(msg_id) for msg_id in message_ids], return_exceptions=True
        )

        success_count = sum(1 for r in results if isinstance(r, tuple) and r[1])
        failed_count = len(message_ids) - success_count

        return {
            "status": "messages_trashed",
            "trashed_count": success_count,
            "failed_count": failed_count,
        }

    async def _batch_mark_gmail_as_read(
        self, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Mark multiple Gmail messages as read at once.

        Args:
            arguments: Tool arguments with message_ids.

        Returns:
            Batch operation result with success count.
        """
        message_ids = arguments.get("message_ids", [])

        if not message_ids:
            return {
                "status": "no_messages",
                "message": "No message IDs provided",
                "marked_count": 0,
            }

        result = await self._batch_modify_gmail_messages(
            {
                "message_ids": message_ids,
                "remove_label_ids": ["UNREAD"],
            }
        )

        return {
            "status": "messages_marked_as_read",
            "marked_count": result.get("modified_count", 0),
        }

    async def _batch_delete_gmail_messages(
        self, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Permanently delete multiple Gmail messages at once.

        WARNING: This action cannot be undone. Messages are permanently deleted,
        not moved to trash.

        Args:
            arguments: Tool arguments with message_ids.

        Returns:
            Batch operation result with deleted count.
        """
        message_ids = arguments.get("message_ids", [])

        if not message_ids:
            return {
                "status": "no_messages",
                "message": "No message IDs provided",
                "deleted_count": 0,
            }

        # Use Gmail's batchDelete endpoint
        url = f"{GMAIL_API_BASE}/users/me/messages/batchDelete"
        await self._make_request("POST", url, json_data={"ids": message_ids})

        return {
            "status": "messages_deleted",
            "deleted_count": len(message_ids),
            "warning": "Messages permanently deleted (cannot be undone)",
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
            arguments: Tool arguments with document_id and optional include_tabs_content.

        Returns:
            Document content and metadata, optionally including tab information.
        """
        document_id = arguments["document_id"]
        include_tabs_content = arguments.get("include_tabs_content", False)

        url = f"{DOCS_API_BASE}/documents/{document_id}"
        if include_tabs_content:
            url += "?includeTabsContent=true"

        response = await self._make_request("GET", url)

        # Extract text content from body
        text_content = self._extract_doc_text(response.get("body", {}))

        result = {
            "document_id": response.get("documentId"),
            "title": response.get("title"),
            "revision_id": response.get("revisionId"),
            "text_content": text_content,
        }

        # Include tab information if requested
        if include_tabs_content and "tabs" in response:
            result["tabs"] = self._format_tabs(response["tabs"])

        return result

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
    # =========================================================================
    # Google Docs Tab Operations
    # =========================================================================

    def _format_tabs(self, tabs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format tab information for response.

        Args:
            tabs: Raw tabs array from Google Docs API.

        Returns:
            Formatted list of tab metadata.
        """
        formatted_tabs = []
        for tab in tabs:
            tab_props = tab.get("tabProperties", {})
            formatted_tab = {
                "tab_id": tab_props.get("tabId"),
                "title": tab_props.get("title", ""),
                "index": tab_props.get("index", 0),
                "nesting_level": tab_props.get("nestingLevel", 0),
            }

            # Add optional fields if present
            if "iconEmoji" in tab_props:
                formatted_tab["icon_emoji"] = tab_props["iconEmoji"]
            if "parentTabId" in tab_props:
                formatted_tab["parent_tab_id"] = tab_props["parentTabId"]

            formatted_tabs.append(formatted_tab)

        return formatted_tabs

    async def _list_document_tabs(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List all tabs in a Google Doc with their metadata.

        Args:
            arguments: Tool arguments with document_id.

        Returns:
            List of tabs with metadata (tabId, title, index, nestingLevel, iconEmoji, parentTabId).
        """
        document_id = arguments["document_id"]

        # Request document with tabs included
        url = f"{DOCS_API_BASE}/documents/{document_id}?includeTabsContent=true"
        response = await self._make_request("GET", url)

        tabs = response.get("tabs", [])

        if not tabs:
            return {
                "document_id": document_id,
                "tabs": [],
                "count": 0,
                "message": "Document has no tabs or only a single tab",
            }

        formatted_tabs = self._format_tabs(tabs)

        return {
            "document_id": document_id,
            "tabs": formatted_tabs,
            "count": len(formatted_tabs),
        }

    async def _get_tab_content(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Get content from a specific tab in a Google Doc.

        Args:
            arguments: Tool arguments with document_id and tab_id.

        Returns:
            Tab metadata and text content.
        """
        document_id = arguments["document_id"]
        tab_id = arguments["tab_id"]

        # Request document with tabs included
        url = f"{DOCS_API_BASE}/documents/{document_id}?includeTabsContent=true"
        response = await self._make_request("GET", url)

        tabs = response.get("tabs", [])

        # Find the requested tab
        target_tab = None
        for tab in tabs:
            tab_props = tab.get("tabProperties", {})
            if tab_props.get("tabId") == tab_id:
                target_tab = tab
                break

        if not target_tab:
            return {
                "error": f"Tab '{tab_id}' not found in document",
                "document_id": document_id,
                "available_tabs": [
                    t.get("tabProperties", {}).get("tabId")
                    for t in tabs
                    if "tabProperties" in t
                ],
            }

        # Extract tab properties
        tab_props = target_tab.get("tabProperties", {})

        # Extract text content from tab body
        tab_body = target_tab.get("documentTab", {}).get("body", {})
        text_content = self._extract_doc_text(tab_body)

        result = {
            "document_id": document_id,
            "tab_id": tab_id,
            "title": tab_props.get("title", ""),
            "index": tab_props.get("index", 0),
            "nesting_level": tab_props.get("nestingLevel", 0),
            "text_content": text_content,
        }

        # Add optional fields
        if "iconEmoji" in tab_props:
            result["icon_emoji"] = tab_props["iconEmoji"]
        if "parentTabId" in tab_props:
            result["parent_tab_id"] = tab_props["parentTabId"]

        return result

    async def _create_document_tab(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Create a new tab in a Google Doc.

        Args:
            arguments: Tool arguments with document_id, title, and optional icon_emoji, parent_tab_id, index.

        Returns:
            Created tab information including the new tab_id.
        """
        document_id = arguments["document_id"]
        title = arguments["title"]
        icon_emoji = arguments.get("icon_emoji")
        parent_tab_id = arguments.get("parent_tab_id")
        index = arguments.get("index")

        # Build the createTab request
        create_tab_request: dict[str, Any] = {
            "createTab": {
                "tabProperties": {
                    "title": title,
                }
            }
        }

        # Add optional properties
        if icon_emoji:
            create_tab_request["createTab"]["tabProperties"]["iconEmoji"] = icon_emoji
        if parent_tab_id:
            create_tab_request["createTab"]["tabProperties"]["parentTabId"] = (
                parent_tab_id
            )
        if index is not None:
            create_tab_request["createTab"]["tabProperties"]["index"] = index

        # Execute the batchUpdate
        url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
        body = {"requests": [create_tab_request]}

        response = await self._make_request("POST", url, json_data=body)

        # Extract the created tab ID from the response
        replies = response.get("replies", [])
        if replies and "createTab" in replies[0]:
            created_tab = replies[0]["createTab"]
            return {
                "status": "created",
                "document_id": document_id,
                "tab_id": created_tab.get("tabId"),
                "title": title,
            }

        return {
            "status": "created",
            "document_id": document_id,
            "title": title,
        }

    async def _update_tab_properties(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Update properties of an existing tab.

        Args:
            arguments: Tool arguments with document_id, tab_id, and optional title, icon_emoji.

        Returns:
            Updated tab information.
        """
        document_id = arguments["document_id"]
        tab_id = arguments["tab_id"]
        title = arguments.get("title")
        icon_emoji = arguments.get("icon_emoji")

        if not title and not icon_emoji:
            return {
                "error": "At least one of 'title' or 'icon_emoji' must be provided",
                "document_id": document_id,
                "tab_id": tab_id,
            }

        # Build the updateTabProperties request
        update_request: dict[str, Any] = {
            "updateTabProperties": {
                "tabId": tab_id,
                "tabProperties": {},
                "fields": [],
            }
        }

        # Add properties to update
        if title:
            update_request["updateTabProperties"]["tabProperties"]["title"] = title
            update_request["updateTabProperties"]["fields"].append("title")

        if icon_emoji:
            update_request["updateTabProperties"]["tabProperties"]["iconEmoji"] = (
                icon_emoji
            )
            update_request["updateTabProperties"]["fields"].append("iconEmoji")

        # Convert fields list to comma-separated string
        update_request["updateTabProperties"]["fields"] = ",".join(
            update_request["updateTabProperties"]["fields"]
        )

        # Execute the batchUpdate
        url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
        body = {"requests": [update_request]}

        await self._make_request("POST", url, json_data=body)

        return {
            "status": "updated",
            "document_id": document_id,
            "tab_id": tab_id,
            "updated_fields": update_request["updateTabProperties"]["fields"].split(
                ","
            ),
        }

    async def _move_tab(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Move a tab to a new position or change its parent.

        Args:
            arguments: Tool arguments with document_id, tab_id, and optional new_parent_tab_id, new_index.

        Returns:
            Moved tab information.
        """
        document_id = arguments["document_id"]
        tab_id = arguments["tab_id"]
        new_parent_tab_id = arguments.get("new_parent_tab_id")
        new_index = arguments.get("new_index")

        if new_parent_tab_id is None and new_index is None:
            return {
                "error": "At least one of 'new_parent_tab_id' or 'new_index' must be provided",
                "document_id": document_id,
                "tab_id": tab_id,
            }

        # Build the updateTabProperties request for moving
        update_request: dict[str, Any] = {
            "updateTabProperties": {
                "tabId": tab_id,
                "tabProperties": {},
                "fields": [],
            }
        }

        # Add properties to update
        if new_parent_tab_id is not None:
            # Empty string means move to root level
            if new_parent_tab_id == "":
                # To move to root, we need to remove the parentTabId
                # This requires a different approach - we'll set it to null
                update_request["updateTabProperties"]["tabProperties"][
                    "parentTabId"
                ] = None
            else:
                update_request["updateTabProperties"]["tabProperties"][
                    "parentTabId"
                ] = new_parent_tab_id
            update_request["updateTabProperties"]["fields"].append("parentTabId")

        if new_index is not None:
            update_request["updateTabProperties"]["tabProperties"]["index"] = new_index
            update_request["updateTabProperties"]["fields"].append("index")

        # Convert fields list to comma-separated string
        update_request["updateTabProperties"]["fields"] = ",".join(
            update_request["updateTabProperties"]["fields"]
        )

        # Execute the batchUpdate
        url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"
        body = {"requests": [update_request]}

        await self._make_request("POST", url, json_data=body)

        return {
            "status": "moved",
            "document_id": document_id,
            "tab_id": tab_id,
            "updated_fields": update_request["updateTabProperties"]["fields"].split(
                ","
            ),
        }

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

    async def _render_mermaid_to_doc(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Render Mermaid diagram to image and insert into Google Doc.

        Uses @mermaid-js/mermaid-cli (npx) to render Mermaid code to SVG or PNG,
        uploads the image to Google Drive with public sharing, then inserts
        it into the specified Google Doc using InsertInlineImageRequest.

        Args:
            arguments: Tool arguments with document_id, mermaid_code, insert_index,
                      image_format, width_pt, height_pt.

        Returns:
            Dictionary with status, image URL, insert index, and document ID.

        Raises:
            RuntimeError: If mermaid-cli rendering fails or npx is not available.
            ValueError: If invalid mermaid syntax provided.
        """
        document_id = arguments["document_id"]
        mermaid_code = arguments["mermaid_code"]
        insert_index = arguments.get("insert_index")
        image_format = arguments.get("image_format", "svg")
        width_pt = arguments.get("width_pt")
        height_pt = arguments.get("height_pt")

        # Check if npx is available
        try:
            subprocess.run(  # nosec B603 B607 - npx is trusted
                ["npx", "--version"],
                capture_output=True,
                check=True,
            )
        except FileNotFoundError as err:
            raise RuntimeError(
                "npx is not installed. Install Node.js and npm from:\n"
                "  https://nodejs.org/"
            ) from err

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "diagram.mmd"
            output_path = Path(tmpdir) / f"diagram.{image_format}"

            # Write Mermaid code to temp file
            input_path.write_text(mermaid_code, encoding="utf-8")

            # Render Mermaid diagram using mermaid-cli
            try:
                result = subprocess.run(  # nosec B603 B607 - controlled paths
                    [
                        "npx",
                        "-y",
                        "@mermaid-js/mermaid-cli@11.12.0",
                        "-i",
                        str(input_path),
                        "-o",
                        str(output_path),
                    ],
                    capture_output=True,
                    check=True,
                    text=True,
                    timeout=30,
                )
                logger.info("Mermaid rendering output: %s", result.stdout)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    f"Mermaid rendering failed: {e.stderr}\n"
                    f"Check syntax at https://mermaid.js.org/intro/"
                ) from e
            except subprocess.TimeoutExpired as e:
                raise RuntimeError(
                    "Mermaid rendering timed out (>30s). "
                    "Simplify the diagram or try again."
                ) from e

            # Verify output file was created
            if not output_path.exists():
                raise RuntimeError(
                    f"Mermaid-cli failed to create output file: {output_path}"
                )

            # Read the rendered image
            image_content = output_path.read_bytes()
            logger.info(
                "Rendered Mermaid diagram: %d bytes (%s)",
                len(image_content),
                image_format,
            )

        # Upload image to Google Drive
        access_token = await self._get_access_token()

        # Create a temp folder in Drive for Mermaid diagrams
        metadata: dict[str, Any] = {
            "name": f"mermaid-diagram-{document_id[:8]}.{image_format}",
            "mimeType": f"image/{image_format}+xml"
            if image_format == "svg"
            else f"image/{image_format}",
        }

        # Use multipart upload for the image
        upload_url = (
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
        )

        boundary = "mermaid_diagram_boundary"

        # Build multipart body
        body_start = (
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(metadata)}\r\n"
            f"--{boundary}\r\n"
            f"Content-Type: {metadata['mimeType']}\r\n\r\n"
        ).encode()
        body_end = f"\r\n--{boundary}--".encode()

        full_body = body_start + image_content + body_end

        async with httpx.AsyncClient() as client:
            response = await client.post(
                upload_url,
                content=full_body,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
                timeout=60.0,
            )
            response.raise_for_status()
            upload_result = response.json()

        file_id = upload_result.get("id")
        logger.info("Uploaded Mermaid image to Drive: %s", file_id)

        # Make the file publicly accessible
        permission_url = f"{DRIVE_API_BASE}/files/{file_id}/permissions"
        permission_body = {"role": "reader", "type": "anyone"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                permission_url,
                json=permission_body,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            response.raise_for_status()

        # Get public URL for the image
        public_url = f"https://drive.google.com/uc?export=view&id={file_id}"

        # Determine insert index
        if insert_index is None:
            # Get document to find end index
            get_url = f"{DOCS_API_BASE}/documents/{document_id}"
            doc = await self._make_request("GET", get_url)
            content = doc.get("body", {}).get("content", [])
            if content:
                last_element = content[-1]
                end_index = last_element.get("endIndex", 1)
                insert_index = max(1, end_index - 1)
            else:
                insert_index = 1

        # Insert image into Google Doc using batchUpdate
        update_url = f"{DOCS_API_BASE}/documents/{document_id}:batchUpdate"

        # Build InsertInlineImageRequest
        image_request: dict[str, Any] = {
            "insertInlineImage": {
                "uri": public_url,
                "location": {"index": insert_index},
            }
        }

        # Add optional sizing
        if width_pt or height_pt:
            object_size: dict[str, Any] = {}
            if width_pt:
                object_size["width"] = {"magnitude": width_pt, "unit": "PT"}
            if height_pt:
                object_size["height"] = {"magnitude": height_pt, "unit": "PT"}
            image_request["insertInlineImage"]["objectSize"] = object_size

        body = {"requests": [image_request]}

        await self._make_request("POST", update_url, json_data=body)

        return {
            "status": "success",
            "imageUrl": public_url,
            "fileId": file_id,
            "insertIndex": insert_index,
            "documentId": document_id,
            "format": image_format,
        }

    # =========================================================================
    # Google Tasks API - Task Lists Operations
    # =========================================================================

    async def _list_task_lists(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List all task lists for the user.

        Args:
            arguments: Tool arguments with optional max_results.

        Returns:
            List of task lists with id, title, and updated timestamp.
        """
        max_results = arguments.get("max_results", 100)

        url = f"{TASKS_API_BASE}/users/@me/lists"
        params = {"maxResults": max_results}

        response = await self._make_request("GET", url, params=params)

        task_lists = []
        for item in response.get("items", []):
            task_lists.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "updated": item.get("updated"),
                    "self_link": item.get("selfLink"),
                }
            )

        return {"task_lists": task_lists, "count": len(task_lists)}

    async def _get_task_list(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Get a specific task list by ID.

        Args:
            arguments: Tool arguments with tasklist_id.

        Returns:
            Task list details.
        """
        tasklist_id = arguments["tasklist_id"]

        url = f"{TASKS_API_BASE}/users/@me/lists/{tasklist_id}"
        response = await self._make_request("GET", url)

        return {
            "id": response.get("id"),
            "title": response.get("title"),
            "updated": response.get("updated"),
            "self_link": response.get("selfLink"),
        }

    async def _create_task_list(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Create a new task list.

        Args:
            arguments: Tool arguments with title.

        Returns:
            Created task list details.
        """
        title = arguments["title"]

        url = f"{TASKS_API_BASE}/users/@me/lists"
        response = await self._make_request("POST", url, json_data={"title": title})

        return {
            "status": "created",
            "id": response.get("id"),
            "title": response.get("title"),
            "updated": response.get("updated"),
        }

    async def _update_task_list(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Update an existing task list.

        Args:
            arguments: Tool arguments with tasklist_id and title.

        Returns:
            Updated task list details.
        """
        tasklist_id = arguments["tasklist_id"]
        title = arguments["title"]

        url = f"{TASKS_API_BASE}/users/@me/lists/{tasklist_id}"
        response = await self._make_request("PATCH", url, json_data={"title": title})

        return {
            "status": "updated",
            "id": response.get("id"),
            "title": response.get("title"),
            "updated": response.get("updated"),
        }

    async def _delete_task_list(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Delete a task list.

        Args:
            arguments: Tool arguments with tasklist_id.

        Returns:
            Deletion confirmation.
        """
        tasklist_id = arguments["tasklist_id"]

        url = f"{TASKS_API_BASE}/users/@me/lists/{tasklist_id}"

        access_token = await self._get_access_token()
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            response.raise_for_status()

        return {"status": "deleted", "tasklist_id": tasklist_id}

    # =========================================================================
    # Google Tasks API - Tasks Operations
    # =========================================================================

    async def _list_tasks(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List all tasks in a task list.

        Args:
            arguments: Tool arguments with tasklist_id and filter options.

        Returns:
            List of tasks with details.
        """
        tasklist_id = arguments.get("tasklist_id", "@default")
        show_completed = arguments.get("show_completed", True)
        show_hidden = arguments.get("show_hidden", False)
        due_min = arguments.get("due_min")
        due_max = arguments.get("due_max")
        max_results = arguments.get("max_results", 100)

        url = f"{TASKS_API_BASE}/lists/{tasklist_id}/tasks"
        params: dict[str, Any] = {
            "maxResults": max_results,
            "showCompleted": str(show_completed).lower(),
            "showHidden": str(show_hidden).lower(),
        }

        if due_min:
            params["dueMin"] = due_min
        if due_max:
            params["dueMax"] = due_max

        response = await self._make_request("GET", url, params=params)

        tasks = []
        for item in response.get("items", []):
            tasks.append(self._format_task(item))

        return {"tasks": tasks, "count": len(tasks)}

    def _format_task(self, item: dict[str, Any]) -> dict[str, Any]:
        """Format a task item for consistent output.

        Args:
            item: Raw task data from API.

        Returns:
            Formatted task dictionary.
        """
        return {
            "id": item.get("id"),
            "title": item.get("title"),
            "notes": item.get("notes"),
            "status": item.get("status"),
            "due": item.get("due"),
            "completed": item.get("completed"),
            "parent": item.get("parent"),
            "position": item.get("position"),
            "updated": item.get("updated"),
            "deleted": item.get("deleted", False),
            "hidden": item.get("hidden", False),
        }

    async def _get_task(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Get a specific task by ID.

        Args:
            arguments: Tool arguments with tasklist_id and task_id.

        Returns:
            Task details.
        """
        tasklist_id = arguments.get("tasklist_id", "@default")
        task_id = arguments["task_id"]

        url = f"{TASKS_API_BASE}/lists/{tasklist_id}/tasks/{task_id}"
        response = await self._make_request("GET", url)

        return self._format_task(response)

    async def _search_tasks(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Search tasks across all task lists by title or notes.

        Note: Google Tasks API doesn't have native search, so we fetch all
        tasks and filter locally.

        Args:
            arguments: Tool arguments with query and show_completed.

        Returns:
            List of matching tasks with their task list info.
        """
        query = arguments["query"].lower()
        show_completed = arguments.get("show_completed", True)

        # First get all task lists
        lists_url = f"{TASKS_API_BASE}/users/@me/lists"
        lists_response = await self._make_request("GET", lists_url)

        matching_tasks = []

        # Search in each task list
        for task_list in lists_response.get("items", []):
            tasklist_id = task_list.get("id")
            tasklist_title = task_list.get("title")

            tasks_url = f"{TASKS_API_BASE}/lists/{tasklist_id}/tasks"
            params = {
                "showCompleted": str(show_completed).lower(),
                "maxResults": 100,
            }

            tasks_response = await self._make_request("GET", tasks_url, params=params)

            for task in tasks_response.get("items", []):
                title = task.get("title", "").lower()
                notes = task.get("notes", "").lower()

                if query in title or query in notes:
                    formatted = self._format_task(task)
                    formatted["tasklist_id"] = tasklist_id
                    formatted["tasklist_title"] = tasklist_title
                    matching_tasks.append(formatted)

        return {"tasks": matching_tasks, "count": len(matching_tasks), "query": query}

    async def _create_task(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Create a new task in a task list.

        Args:
            arguments: Tool arguments with tasklist_id, title, notes, due, parent.

        Returns:
            Created task details.
        """
        tasklist_id = arguments.get("tasklist_id", "@default")
        title = arguments["title"]
        notes = arguments.get("notes")
        due = arguments.get("due")
        parent = arguments.get("parent")

        url = f"{TASKS_API_BASE}/lists/{tasklist_id}/tasks"

        task_body: dict[str, Any] = {"title": title}

        if notes:
            task_body["notes"] = notes
        if due:
            task_body["due"] = due

        # If parent is specified, add it as a query parameter
        params = {}
        if parent:
            params["parent"] = parent

        response = await self._make_request(
            "POST", url, params=params if params else None, json_data=task_body
        )

        result = self._format_task(response)
        result["status"] = "created"
        return result

    async def _update_task(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Update an existing task.

        Args:
            arguments: Tool arguments with tasklist_id, task_id, and fields to update.

        Returns:
            Updated task details.
        """
        tasklist_id = arguments.get("tasklist_id", "@default")
        task_id = arguments["task_id"]

        url = f"{TASKS_API_BASE}/lists/{tasklist_id}/tasks/{task_id}"

        # Build update body with only provided fields
        update_body: dict[str, Any] = {}

        if "title" in arguments:
            update_body["title"] = arguments["title"]
        if "notes" in arguments:
            update_body["notes"] = arguments["notes"]
        if "due" in arguments:
            update_body["due"] = arguments["due"]
        if "status" in arguments:
            update_body["status"] = arguments["status"]

        response = await self._make_request("PATCH", url, json_data=update_body)

        result = self._format_task(response)
        result["update_status"] = "updated"
        return result

    async def _complete_task(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Mark a task as completed.

        Args:
            arguments: Tool arguments with tasklist_id and task_id.

        Returns:
            Completed task details.
        """
        tasklist_id = arguments.get("tasklist_id", "@default")
        task_id = arguments["task_id"]

        url = f"{TASKS_API_BASE}/lists/{tasklist_id}/tasks/{task_id}"

        response = await self._make_request(
            "PATCH", url, json_data={"status": "completed"}
        )

        result = self._format_task(response)
        result["update_status"] = "completed"
        return result

    async def _delete_task(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Delete a task.

        Args:
            arguments: Tool arguments with tasklist_id and task_id.

        Returns:
            Deletion confirmation.
        """
        tasklist_id = arguments.get("tasklist_id", "@default")
        task_id = arguments["task_id"]

        url = f"{TASKS_API_BASE}/lists/{tasklist_id}/tasks/{task_id}"

        access_token = await self._get_access_token()
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            response.raise_for_status()

        return {"status": "deleted", "task_id": task_id, "tasklist_id": tasklist_id}

    async def _move_task(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Move a task to a different position or make it a subtask.

        Args:
            arguments: Tool arguments with tasklist_id, task_id, parent, previous.

        Returns:
            Moved task details.
        """
        tasklist_id = arguments.get("tasklist_id", "@default")
        task_id = arguments["task_id"]
        parent = arguments.get("parent")
        previous = arguments.get("previous")

        url = f"{TASKS_API_BASE}/lists/{tasklist_id}/tasks/{task_id}/move"

        params: dict[str, Any] = {}
        if parent:
            params["parent"] = parent
        if previous:
            params["previous"] = previous

        response = await self._make_request(
            "POST", url, params=params if params else None
        )

        result = self._format_task(response)
        result["move_status"] = "moved"
        return result

    # -------------------- Rclone Drive Sync Operations --------------------

    def _get_rclone_manager(self) -> "RcloneManager":
        """Get or create an RcloneManager instance.

        Lazily creates an RcloneManager using the current OAuth tokens
        from TokenStorage.

        Returns:
            Configured RcloneManager instance.

        Raises:
            RuntimeError: If rclone is not installed or tokens unavailable.
        """
        # Import here to avoid circular imports and make rclone optional
        from claude_mpm.mcp.rclone_manager import RcloneManager, RcloneNotInstalledError

        try:
            return RcloneManager(
                storage=self.storage,
                service_name=SERVICE_NAME,
            )
        except RcloneNotInstalledError as e:
            raise RuntimeError(
                "rclone is not installed. Install it from https://rclone.org/downloads/ "
                "to use Drive sync features."
            ) from e

    async def _list_drive_contents(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List Drive folder contents using rclone lsjson.

        Args:
            arguments: Tool arguments with path, recursive, files_only,
                include_hash, max_depth.

        Returns:
            Dictionary with items list, count, and path.
        """
        path = arguments.get("path", "")
        recursive = arguments.get("recursive", False)
        files_only = arguments.get("files_only", False)
        include_hash = arguments.get("include_hash", False)
        max_depth = arguments.get("max_depth", -1)

        manager = self._get_rclone_manager()
        try:
            items = manager.list_json(
                path=path,
                recursive=recursive,
                files_only=files_only,
                include_hash=include_hash,
                max_depth=max_depth,
            )
            return {
                "items": items,
                "count": len(items),
                "path": path or "(root)",
            }
        finally:
            manager.cleanup()

    async def _download_drive_folder(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Download Drive folder to local filesystem.

        Args:
            arguments: Tool arguments with drive_path, local_path,
                google_docs_format, exclude, dry_run.

        Returns:
            Operation result with status and details.
        """
        drive_path = arguments["drive_path"]
        local_path = arguments["local_path"]
        google_docs_format = arguments.get("google_docs_format", "docx")
        exclude = arguments.get("exclude")
        dry_run = arguments.get("dry_run", False)

        manager = self._get_rclone_manager()
        try:
            return manager.download(
                drive_path=drive_path,
                local_path=local_path,
                google_docs_format=google_docs_format,
                exclude=exclude,
                dry_run=dry_run,
            )
        finally:
            manager.cleanup()

    async def _upload_to_drive(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Upload local folder to Google Drive.

        Args:
            arguments: Tool arguments with local_path, drive_path,
                convert_to_google_docs, exclude, dry_run.

        Returns:
            Operation result with status and details.
        """
        local_path = arguments["local_path"]
        drive_path = arguments["drive_path"]
        convert_to_google_docs = arguments.get("convert_to_google_docs", False)
        exclude = arguments.get("exclude")
        dry_run = arguments.get("dry_run", False)

        manager = self._get_rclone_manager()
        try:
            return manager.upload(
                local_path=local_path,
                drive_path=drive_path,
                convert_to_google_docs=convert_to_google_docs,
                exclude=exclude,
                dry_run=dry_run,
            )
        finally:
            manager.cleanup()

    async def _sync_drive_folder(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Sync files between local and Drive.

        Args:
            arguments: Tool arguments with source, destination,
                dry_run, delete_extra, exclude, include.

        Returns:
            Operation result with status and details.
        """
        source = arguments["source"]
        destination = arguments["destination"]
        dry_run = arguments.get("dry_run", True)  # Safe default
        delete_extra = arguments.get("delete_extra", False)
        exclude = arguments.get("exclude")
        include = arguments.get("include")

        manager = self._get_rclone_manager()
        try:
            return manager.sync(
                source=source,
                destination=destination,
                delete_extra=delete_extra,
                exclude=exclude,
                include=include,
                dry_run=dry_run,
            )
        finally:
            manager.cleanup()

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
