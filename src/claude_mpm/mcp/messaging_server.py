"""Internal MCP server for the claude-mpm messaging system.

WHY: Exposes MessageService and ShortcutsService as MCP tools so that
Claude Desktop and other MCP clients can send, read, and manage
cross-project messages without needing direct Python imports.

All MessageService calls are synchronous SQLite operations wrapped in
asyncio.to_thread() to avoid blocking the event loop.
"""

import asyncio
import json
import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from claude_mpm.core.unified_paths import UnifiedPathManager
from claude_mpm.services.communication.message_service import MessageService
from claude_mpm.services.communication.shortcuts_service import ShortcutsService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _resolve_default_project_root() -> Path:
    """Resolve the project root the MCP server should default to.

    WHY: An MCP server is launched by the host (Claude Desktop, claude-code,
    etc.) from whatever cwd that host happens to be running in — typically the
    home directory or some host-internal scratch dir. ``Path.cwd()`` therefore
    does NOT reliably point at the user's project. To give callers a useful
    default we honor, in order:

      1. ``CLAUDE_MPM_PROJECT_ROOT`` (explicit override),
      2. ``PWD`` (the user-facing working dir, set by most shells/launchers),
      3. ``UnifiedPathManager().project_root`` (best-effort discovery),
      4. ``Path.cwd()`` (last resort).
    """
    for env_var in ("CLAUDE_MPM_PROJECT_ROOT", "PWD"):
        value = os.environ.get(env_var)
        if value:
            candidate = Path(value).expanduser()
            if candidate.is_dir():
                return candidate.resolve()

    try:
        return Path(UnifiedPathManager().project_root).resolve()
    except Exception:
        return Path.cwd().resolve()


def _message_to_dict(msg: Any) -> dict[str, Any]:
    """Convert a Message dataclass to a JSON-serialisable dict."""
    try:
        d = asdict(msg)
    except TypeError:
        d = msg.__dict__.copy()
    # Convert any non-serialisable values to strings
    for key, val in d.items():
        if hasattr(val, "isoformat"):
            d[key] = val.isoformat()
    return d


class MessagingMCPServer:
    """MCP server wrapping MessageService and ShortcutsService.

    Exposes 10 tools:
      message_send, message_list, message_read, message_archive,
      message_reply, message_check, shortcut_add, shortcut_list,
      shortcut_remove, shortcut_resolve
    """

    def __init__(self) -> None:
        """Initialise the Messaging MCP server."""
        self.server = Server("mpm-messaging")
        self.default_project_root = _resolve_default_project_root()
        logger.info(
            "MessagingMCPServer default project root: %s", self.default_project_root
        )
        self.messages = MessageService(self.default_project_root)
        self._service_cache: dict[str, MessageService] = {
            str(self.default_project_root): self.messages,
        }
        self.shortcuts = ShortcutsService()
        self._setup_handlers()

    def _get_message_service(
        self, project_path: str | None
    ) -> tuple[MessageService, str]:
        """Return a MessageService scoped to ``project_path``.

        Falls back to the server's default project root when no path is given.
        Caches one MessageService per resolved path so repeated calls do not
        keep reopening the SQLite database.
        """
        if not project_path:
            return self.messages, str(self.default_project_root)

        resolved = str(Path(project_path).expanduser().resolve())
        cached = self._service_cache.get(resolved)
        if cached is not None:
            return cached, resolved

        service = MessageService(Path(resolved))
        self._service_cache[resolved] = service
        return service, resolved

    def _setup_handlers(self) -> None:
        """Register MCP tool handlers.

        WHY: We register bound class methods directly with the MCP server's
        decorator factories rather than defining inner functions. The MCP
        ``@server.list_tools()`` / ``@server.call_tool()`` decorators are used
        purely for their registration side-effect — they don't need a local
        name. Defining inner ``async def`` handlers caused Pyright to flag the
        local names as unused (reportUnusedVariable), and ``# pyright: ignore``
        suppressions are brittle. Promoting the handlers to real methods makes
        them first-class, individually testable, and eliminates the unused-name
        problem entirely.
        """
        self.server.list_tools()(self._handle_list_tools)
        self.server.call_tool()(self._handle_call_tool)

    async def _handle_list_tools(self) -> list[Tool]:
        """Return list of available tools."""
        return [
            Tool(
                name="message_send",
                description="Send a message to another claude-mpm project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to_project": {
                            "type": "string",
                            "description": "Destination project path or shortcut name",
                        },
                        "to_agent": {
                            "type": "string",
                            "description": "Target agent in the destination project",
                        },
                        "message_type": {
                            "type": "string",
                            "description": "Message type (e.g. task, notification, query)",
                        },
                        "subject": {
                            "type": "string",
                            "description": "Message subject",
                        },
                        "body": {
                            "type": "string",
                            "description": "Message body",
                        },
                        "priority": {
                            "type": "string",
                            "description": "Priority: low, normal, high (default: normal)",
                            "default": "normal",
                        },
                        "from_agent": {
                            "type": "string",
                            "description": "Sending agent name (default: pm)",
                            "default": "pm",
                        },
                    },
                    "required": [
                        "to_project",
                        "to_agent",
                        "message_type",
                        "subject",
                        "body",
                    ],
                },
            ),
            Tool(
                name="message_list",
                description=(
                    "List messages addressed to a specific project, optionally "
                    "filtered by status or agent. If project_path is omitted, "
                    "the server uses CLAUDE_MPM_PROJECT_ROOT or PWD; relying on "
                    "that fallback is discouraged because the MCP server's cwd "
                    "is not the user's project."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Filter by status: unread, read, archived",
                        },
                        "agent": {
                            "type": "string",
                            "description": "Filter by recipient agent name",
                        },
                        "project_path": {
                            "type": "string",
                            "description": (
                                "Absolute path to the project whose inbox should "
                                "be queried. Strongly recommended; defaults to "
                                "CLAUDE_MPM_PROJECT_ROOT/PWD when omitted."
                            ),
                        },
                    },
                    "required": [],
                },
            ),
            Tool(
                name="message_read",
                description="Read a specific message by ID (auto-marks as read)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "Unique message ID",
                        },
                    },
                    "required": ["message_id"],
                },
            ),
            Tool(
                name="message_archive",
                description="Archive a message by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "Unique message ID to archive",
                        },
                    },
                    "required": ["message_id"],
                },
            ),
            Tool(
                name="message_reply",
                description="Reply to an existing message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "original_message_id": {
                            "type": "string",
                            "description": "ID of the message to reply to",
                        },
                        "subject": {
                            "type": "string",
                            "description": "Reply subject",
                        },
                        "body": {
                            "type": "string",
                            "description": "Reply body",
                        },
                        "from_agent": {
                            "type": "string",
                            "description": "Sending agent name (default: pm)",
                            "default": "pm",
                        },
                    },
                    "required": ["original_message_id", "subject", "body"],
                },
            ),
            Tool(
                name="message_check",
                description="Check unread message count and high-priority messages for a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent": {
                            "type": "string",
                            "description": "Filter unread count by agent name",
                        },
                        "project_path": {
                            "type": "string",
                            "description": (
                                "Absolute path to the project to check. Defaults "
                                "to CLAUDE_MPM_PROJECT_ROOT/PWD when omitted."
                            ),
                        },
                    },
                    "required": [],
                },
            ),
            Tool(
                name="shortcut_add",
                description="Add or update a project path shortcut",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Shortcut name (alphanumeric, underscores, hyphens)",
                        },
                        "path": {
                            "type": "string",
                            "description": "Absolute directory path to shortcut to",
                        },
                    },
                    "required": ["name", "path"],
                },
            ),
            Tool(
                name="shortcut_list",
                description="List all configured project path shortcuts",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="shortcut_remove",
                description="Remove a project path shortcut by name",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Shortcut name to remove",
                        },
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="shortcut_resolve",
                description="Resolve a shortcut name or path to an absolute path",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name_or_path": {
                            "type": "string",
                            "description": "Shortcut name or directory path to resolve",
                        },
                    },
                    "required": ["name_or_path"],
                },
            ),
        ]

    async def _handle_call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        """Handle tool calls by dispatching to the appropriate handler."""
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
            ValueError: If tool name is not recognised.
        """
        handlers = {
            "message_send": self._message_send,
            "message_list": self._message_list,
            "message_read": self._message_read,
            "message_archive": self._message_archive,
            "message_reply": self._message_reply,
            "message_check": self._message_check,
            "shortcut_add": self._shortcut_add,
            "shortcut_list": self._shortcut_list,
            "shortcut_remove": self._shortcut_remove,
            "shortcut_resolve": self._shortcut_resolve,
        }

        handler = handlers.get(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name}")

        return await handler(arguments)

    # ------------------------------------------------------------------
    # Message handlers
    # ------------------------------------------------------------------

    async def _message_send(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Send a message to another project.

        Resolves shortcut names for to_project before sending.
        """
        to_project: str = arguments["to_project"]

        # Resolve shortcut if the value is not an absolute path
        if not to_project.startswith("/"):
            to_project = await asyncio.to_thread(
                self.shortcuts.resolve_shortcut, to_project
            )

        msg = await asyncio.to_thread(
            self.messages.send_message,
            to_project,
            arguments["to_agent"],
            arguments["message_type"],
            arguments["subject"],
            arguments["body"],
            arguments.get("priority", "normal"),
            arguments.get("from_agent", "pm"),
        )

        return {"ok": True, "message": _message_to_dict(msg)}

    async def _message_list(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List messages with optional filters, scoped to a project."""
        service, resolved_project = self._get_message_service(
            arguments.get("project_path")
        )
        msgs = await asyncio.to_thread(
            service.list_messages,
            arguments.get("status"),
            arguments.get("agent"),
        )

        return {
            "messages": [_message_to_dict(m) for m in msgs],
            "count": len(msgs),
            "project_path": resolved_project,
        }

    async def _message_read(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Read a specific message (auto-marks as read)."""
        msg = await asyncio.to_thread(
            self.messages.read_message, arguments["message_id"]
        )

        if msg is None:
            return {"error": f"Message not found: {arguments['message_id']}"}

        return {"message": _message_to_dict(msg)}

    async def _message_archive(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Archive a message."""
        success = await asyncio.to_thread(
            self.messages.archive_message, arguments["message_id"]
        )

        return {"ok": success, "message_id": arguments["message_id"]}

    async def _message_reply(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Reply to an existing message."""
        msg = await asyncio.to_thread(
            self.messages.reply_to_message,
            arguments["original_message_id"],
            arguments["subject"],
            arguments["body"],
            arguments.get("from_agent", "pm"),
        )

        if msg is None:
            return {
                "error": f"Original message not found: {arguments['original_message_id']}"
            }

        return {"ok": True, "message": _message_to_dict(msg)}

    async def _message_check(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Check unread count and high-priority messages, scoped to a project."""
        service, resolved_project = self._get_message_service(
            arguments.get("project_path")
        )
        unread_count = await asyncio.to_thread(
            service.get_unread_count, arguments.get("agent")
        )
        high_priority = await asyncio.to_thread(service.get_high_priority_messages)

        return {
            "unread_count": unread_count,
            "high_priority_messages": [_message_to_dict(m) for m in high_priority],
            "high_priority_count": len(high_priority),
            "project_path": resolved_project,
        }

    # ------------------------------------------------------------------
    # Shortcut handlers
    # ------------------------------------------------------------------

    async def _shortcut_add(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Add or update a shortcut."""
        success = await asyncio.to_thread(
            self.shortcuts.add_shortcut, arguments["name"], arguments["path"]
        )

        return {"ok": success, "name": arguments["name"], "path": arguments["path"]}

    async def _shortcut_list(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        """List all shortcuts."""
        shortcuts = await asyncio.to_thread(self.shortcuts.list_shortcuts)

        return {"shortcuts": shortcuts, "count": len(shortcuts)}

    async def _shortcut_remove(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Remove a shortcut."""
        success = await asyncio.to_thread(
            self.shortcuts.remove_shortcut, arguments["name"]
        )

        return {"ok": success, "name": arguments["name"]}

    async def _shortcut_resolve(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Resolve a shortcut name or path."""
        resolved = await asyncio.to_thread(
            self.shortcuts.resolve_shortcut, arguments["name_or_path"]
        )

        return {
            "input": arguments["name_or_path"],
            "resolved": resolved,
            "was_shortcut": self.shortcuts.is_shortcut(arguments["name_or_path"]),
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
    """Entry point for the Messaging MCP server."""
    server = MessagingMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
