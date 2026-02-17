"""MCP Session Server for claude-mpm headless sessions.

This MCP server provides tools for managing claude-mpm headless sessions,
enabling AI assistants to orchestrate multiple concurrent development sessions
programmatically.

The server exposes 5 tools:
- mpm_session_start: Start a new claude-mpm session
- mpm_session_continue: Continue an existing session
- mpm_session_status: Get session status
- mpm_session_list: List all sessions
- mpm_session_stop: Stop a session
"""

import asyncio
import json
import logging
from dataclasses import asdict
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from claude_mpm.mcp.errors import SessionError
from claude_mpm.mcp.models import SessionInfo, SessionResult, SessionStatus
from claude_mpm.mcp.session_manager import SessionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _session_info_to_dict(info: SessionInfo) -> dict[str, Any]:
    """Convert SessionInfo to JSON-serializable dict.

    Args:
        info: SessionInfo dataclass instance.

    Returns:
        Dictionary with session info, status as string value.
    """
    data = asdict(info)
    # Convert enum to string value
    data["status"] = info.status.value
    return data


def _session_result_to_dict(result: SessionResult) -> dict[str, Any]:
    """Convert SessionResult to JSON-serializable dict.

    Args:
        result: SessionResult dataclass instance.

    Returns:
        Dictionary with session result data.
    """
    return asdict(result)


class SessionServer:
    """MCP server for managing claude-mpm headless sessions.

    Provides tools for starting, continuing, monitoring, and stopping
    claude-mpm sessions through the MCP protocol.

    Attributes:
        server: MCP Server instance.
        manager: SessionManager for session lifecycle management.
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        default_timeout: float | None = None,
    ) -> None:
        """Initialize the Session MCP server.

        Args:
            max_concurrent: Maximum number of concurrent sessions (default: 5).
            default_timeout: Default timeout for session operations in seconds.
        """
        self.server = Server("mpm-session-server")
        self.manager = SessionManager(
            max_concurrent=max_concurrent,
            default_timeout=default_timeout,
        )
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """Return list of available tools."""
            return [
                Tool(
                    name="mpm_session_start",
                    description="Start a new claude-mpm headless session with a prompt",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "The prompt to send to claude-mpm",
                            },
                            "working_directory": {
                                "type": "string",
                                "description": "Working directory for the session (optional)",
                            },
                            "no_hooks": {
                                "type": "boolean",
                                "description": "Disable hooks in claude-mpm (default: false)",
                                "default": False,
                            },
                            "no_tickets": {
                                "type": "boolean",
                                "description": "Disable ticket tracking (default: false)",
                                "default": False,
                            },
                            "timeout": {
                                "type": "number",
                                "description": "Timeout in seconds (optional, uses server default if not specified)",
                            },
                        },
                        "required": ["prompt"],
                    },
                ),
                Tool(
                    name="mpm_session_continue",
                    description="Continue an existing claude-mpm session with a new prompt",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "The session ID to continue",
                            },
                            "prompt": {
                                "type": "string",
                                "description": "The prompt to send",
                            },
                            "fork": {
                                "type": "boolean",
                                "description": "Fork the session (creates a new branch, default: false)",
                                "default": False,
                            },
                            "timeout": {
                                "type": "number",
                                "description": "Timeout in seconds (optional)",
                            },
                        },
                        "required": ["session_id", "prompt"],
                    },
                ),
                Tool(
                    name="mpm_session_status",
                    description="Get the status of a specific claude-mpm session",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "The session ID to query",
                            },
                        },
                        "required": ["session_id"],
                    },
                ),
                Tool(
                    name="mpm_session_list",
                    description="List all tracked claude-mpm sessions",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "Filter by status (starting, active, completed, error, stopped)",
                                "enum": [
                                    "starting",
                                    "active",
                                    "completed",
                                    "error",
                                    "stopped",
                                ],
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="mpm_session_stop",
                    description="Stop a running claude-mpm session",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "The session ID to stop",
                            },
                            "force": {
                                "type": "boolean",
                                "description": "Forcefully kill the process (default: false)",
                                "default": False,
                            },
                        },
                        "required": ["session_id"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool calls."""
            try:
                result = await self._dispatch_tool(name, arguments)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            except SessionError as e:
                logger.exception(f"Session error calling tool {name}")
                error_data: dict[str, Any] = {
                    "error": str(e),
                    "error_type": "SessionError",
                }
                if e.session_id:
                    error_data["session_id"] = e.session_id
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(error_data, indent=2),
                    )
                ]
            except Exception as e:
                logger.exception(f"Error calling tool {name}")
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
            "mpm_session_start": self._handle_start,
            "mpm_session_continue": self._handle_continue,
            "mpm_session_status": self._handle_status,
            "mpm_session_list": self._handle_list,
            "mpm_session_stop": self._handle_stop,
        }

        handler = handlers.get(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name}")

        return await handler(arguments)

    async def _handle_start(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle mpm_session_start tool call.

        Args:
            arguments: Tool arguments with prompt, working_directory, etc.

        Returns:
            SessionResult as dictionary.
        """
        prompt = arguments["prompt"]
        working_directory = arguments.get("working_directory")
        no_hooks = arguments.get("no_hooks", False)
        no_tickets = arguments.get("no_tickets", False)
        timeout = arguments.get("timeout")

        result = await self.manager.start_session(
            prompt=prompt,
            working_directory=working_directory,
            no_hooks=no_hooks,
            no_tickets=no_tickets,
            timeout=timeout,
        )

        return _session_result_to_dict(result)

    async def _handle_continue(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle mpm_session_continue tool call.

        Args:
            arguments: Tool arguments with session_id, prompt, fork, timeout.

        Returns:
            SessionResult as dictionary.
        """
        session_id = arguments["session_id"]
        prompt = arguments["prompt"]
        fork = arguments.get("fork", False)
        timeout = arguments.get("timeout")

        result = await self.manager.continue_session(
            session_id=session_id,
            prompt=prompt,
            fork=fork,
            timeout=timeout,
        )

        return _session_result_to_dict(result)

    async def _handle_status(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle mpm_session_status tool call.

        Args:
            arguments: Tool arguments with session_id.

        Returns:
            SessionInfo as dictionary, or error if not found.
        """
        session_id = arguments["session_id"]

        info = await self.manager.get_session_status(session_id)
        if info is None:
            return {
                "error": f"Session not found: {session_id}",
                "session_id": session_id,
                "found": False,
            }

        result = _session_info_to_dict(info)
        result["found"] = True
        return result

    async def _handle_list(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle mpm_session_list tool call.

        Args:
            arguments: Tool arguments with optional status filter.

        Returns:
            Dictionary with sessions list and count.
        """
        status_filter = arguments.get("status")

        # Convert string status to enum if provided
        status_enum = None
        if status_filter:
            try:
                status_enum = SessionStatus(status_filter)
            except ValueError:
                return {
                    "error": f"Invalid status filter: {status_filter}",
                    "valid_statuses": [s.value for s in SessionStatus],
                }

        sessions = await self.manager.list_sessions(status=status_enum)
        active_count = await self.manager.get_active_count()

        return {
            "sessions": [_session_info_to_dict(s) for s in sessions],
            "count": len(sessions),
            "active_count": active_count,
        }

    async def _handle_stop(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle mpm_session_stop tool call.

        Args:
            arguments: Tool arguments with session_id and force flag.

        Returns:
            Dictionary with stop result.
        """
        session_id = arguments["session_id"]
        force = arguments.get("force", False)

        success = await self.manager.stop_session(
            session_id=session_id,
            force=force,
        )

        return {
            "session_id": session_id,
            "stopped": success,
            "force": force,
        }

    async def run(self) -> None:
        """Run the MCP server using stdio transport."""
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options(),
                )
        finally:
            # Ensure all sessions are cleaned up on shutdown
            await self.manager.shutdown()


def main() -> None:
    """Entry point for the MPM Session MCP server."""
    server = SessionServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
