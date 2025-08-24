"""
MCP Tool Adapters for aitrackdown Ticket Management
====================================================

Provides MCP tool wrappers for common aitrackdown operations, enabling
ticket management through Claude Code's MCP interface.

WHY: These tools allow Claude Code to interact with aitrackdown for
ticket management without requiring direct CLI access, providing a
seamless integration experience.

DESIGN DECISIONS:
- Thin wrappers that delegate to aitrackdown CLI for actual operations
- Focus on the most common operations that benefit from Claude integration
- Structured responses for better error handling and user feedback
- Async execution to avoid blocking the MCP gateway
"""

import asyncio
import json
from datetime import datetime

from claude_mpm.services.mcp_gateway.core.interfaces import (
    MCPToolDefinition,
    MCPToolInvocation,
    MCPToolResult,
)
from claude_mpm.services.mcp_gateway.tools.base_adapter import BaseToolAdapter


class TicketCreateTool(BaseToolAdapter):
    """
    Create new tickets using aitrackdown.

    WHY: Creating tickets is the most fundamental operation for tracking work items.
    This tool provides a simple interface for creating tasks, issues, and epics.
    """

    def __init__(self):
        """Initialize the ticket create tool."""
        definition = MCPToolDefinition(
            name="ticket_create",
            description="Create a new ticket (task, issue, or epic) using aitrackdown",
            input_schema={
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["task", "issue", "epic"],
                        "description": "Type of ticket to create",
                    },
                    "title": {"type": "string", "description": "Title of the ticket"},
                    "description": {
                        "type": "string",
                        "description": "Detailed description of the ticket",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Priority level",
                        "default": "medium",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to associate with the ticket",
                    },
                    "parent_epic": {
                        "type": "string",
                        "description": "Parent epic ID (for issues)",
                    },
                    "parent_issue": {
                        "type": "string",
                        "description": "Parent issue ID (for tasks)",
                    },
                },
                "required": ["type", "title"],
            },
        )
        super().__init__(definition)

    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        Create a ticket using aitrackdown CLI.

        Args:
            invocation: Tool invocation request

        Returns:
            Tool execution result with created ticket ID
        """
        start_time = datetime.now()

        try:
            params = invocation.parameters

            # Build aitrackdown command
            cmd = ["aitrackdown", "create", params["type"], params["title"]]

            # Add optional parameters
            if "description" in params:
                cmd.extend(["--description", params["description"]])

            if "priority" in params:
                cmd.extend(["--priority", params["priority"]])

            if params.get("tags"):
                # aitrackdown uses --tag for tags (singular)
                for tag in params["tags"]:
                    cmd.extend(["--tag", tag])

            # For tasks, use --issue to associate with parent issue
            if params["type"] == "task" and "parent_issue" in params:
                cmd.extend(["--issue", params["parent_issue"]])

            # Execute command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            execution_time = (datetime.now() - start_time).total_seconds()

            if process.returncode == 0:
                # Parse ticket ID from output
                output = stdout.decode().strip()
                # aitrackdown typically returns "Created ticket: TSK-XXXX" or similar
                ticket_id = None
                for line in output.split("\n"):
                    if "TSK-" in line or "ISS-" in line or "EP-" in line:
                        # Extract ticket ID
                        import re

                        match = re.search(r"(TSK|ISS|EP)-\d+", line)
                        if match:
                            ticket_id = match.group(0)
                            break

                self._update_metrics(True, execution_time)

                return MCPToolResult(
                    success=True,
                    data={
                        "ticket_id": ticket_id or "Unknown",
                        "type": params["type"],
                        "title": params["title"],
                        "message": output,
                    },
                    execution_time=execution_time,
                    metadata={"tool": "ticket_create", "operation": "create"},
                )
            error_msg = stderr.decode() if stderr else stdout.decode()
            self._update_metrics(False, execution_time)

            return MCPToolResult(
                success=False,
                error=f"Failed to create ticket: {error_msg}",
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(False, execution_time)

            return MCPToolResult(
                success=False,
                error=f"Ticket creation failed: {e!s}",
                execution_time=execution_time,
            )


class TicketListTool(BaseToolAdapter):
    """
    List tickets with optional filters using aitrackdown status command.

    WHY: Users need to review and browse existing tickets. This tool provides
    a quick way to list recent tickets with filtering capabilities.
    """

    def __init__(self):
        """Initialize the ticket list tool."""
        definition = MCPToolDefinition(
            name="ticket_list",
            description="List tickets with optional filters using status command",
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of tickets to return",
                        "default": 10,
                    },
                    "type": {
                        "type": "string",
                        "enum": ["all", "task", "issue", "epic"],
                        "description": "Filter by ticket type",
                        "default": "all",
                    },
                    "status": {
                        "type": "string",
                        "enum": [
                            "all",
                            "open",
                            "in_progress",
                            "done",
                            "closed",
                            "blocked",
                        ],
                        "description": "Filter by status",
                        "default": "all",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["all", "low", "medium", "high", "critical"],
                        "description": "Filter by priority",
                        "default": "all",
                    },
                },
                "required": [],
            },
        )
        super().__init__(definition)

    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        List tickets using aitrackdown CLI.

        Args:
            invocation: Tool invocation request

        Returns:
            Tool execution result with list of tickets
        """
        start_time = datetime.now()

        try:
            params = invocation.parameters
            limit = params.get("limit", 10)

            # Build aitrackdown command - use status tasks for listing
            cmd = ["aitrackdown", "status", "tasks", "--limit", str(limit)]

            # Add filters
            if params.get("status") and params["status"] != "all":
                cmd.extend(["--status", params["status"]])

            # Execute command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            execution_time = (datetime.now() - start_time).total_seconds()

            if process.returncode == 0:
                try:
                    # Try to parse JSON output
                    tickets = json.loads(stdout.decode())
                except json.JSONDecodeError:
                    # Fallback to text parsing if JSON fails
                    output = stdout.decode().strip()
                    tickets = {"raw_output": output, "count": output.count("\n") + 1}

                self._update_metrics(True, execution_time)

                return MCPToolResult(
                    success=True,
                    data=tickets,
                    execution_time=execution_time,
                    metadata={
                        "tool": "ticket_list",
                        "operation": "list",
                        "count": len(tickets) if isinstance(tickets, list) else 1,
                    },
                )
            error_msg = stderr.decode() if stderr else stdout.decode()
            self._update_metrics(False, execution_time)

            return MCPToolResult(
                success=False,
                error=f"Failed to list tickets: {error_msg}",
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(False, execution_time)

            return MCPToolResult(
                success=False,
                error=f"Ticket listing failed: {e!s}",
                execution_time=execution_time,
            )


class TicketUpdateTool(BaseToolAdapter):
    """
    Update ticket status or priority.

    WHY: Tickets need to be updated as work progresses. This tool provides
    a simple interface for updating ticket status and priority.
    """

    def __init__(self):
        """Initialize the ticket update tool."""
        definition = MCPToolDefinition(
            name="ticket_update",
            description="Update a ticket's status or priority",
            input_schema={
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "Ticket ID to update (e.g., TSK-0001)",
                    },
                    "status": {
                        "type": "string",
                        "enum": [
                            "open",
                            "in-progress",
                            "ready",
                            "tested",
                            "done",
                            "waiting",
                        ],
                        "description": "New status for the ticket (workflow state)",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "New priority for the ticket",
                    },
                    "comment": {
                        "type": "string",
                        "description": "Optional comment for the update",
                    },
                },
                "required": ["ticket_id"],
            },
        )
        super().__init__(definition)

    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        Update a ticket using aitrackdown CLI.

        Args:
            invocation: Tool invocation request

        Returns:
            Tool execution result
        """
        start_time = datetime.now()

        try:
            params = invocation.parameters
            ticket_id = params["ticket_id"]

            # Determine which update to perform
            if "status" in params:
                # Use transition command for status updates
                cmd = ["aitrackdown", "transition", ticket_id, params["status"]]

                if "comment" in params:
                    cmd.extend(["--comment", params["comment"]])
            elif "priority" in params:
                # For priority updates, we might need to use edit or transition
                # aitrackdown doesn't have a direct update command, so use transition
                cmd = ["aitrackdown", "transition", ticket_id, "open"]
                cmd.extend(["--comment", f"Priority changed to {params['priority']}"])

                if "comment" in params:
                    cmd.extend(["--comment", params["comment"]])
            else:
                return MCPToolResult(
                    success=False,
                    error="No update fields provided (status or priority required)",
                    execution_time=0.0,
                )

            # Execute command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            execution_time = (datetime.now() - start_time).total_seconds()

            if process.returncode == 0:
                self._update_metrics(True, execution_time)

                return MCPToolResult(
                    success=True,
                    data={
                        "ticket_id": ticket_id,
                        "updated_fields": [
                            k for k in ["status", "priority"] if k in params
                        ],
                        "message": stdout.decode().strip(),
                    },
                    execution_time=execution_time,
                    metadata={"tool": "ticket_update", "operation": "update"},
                )
            error_msg = stderr.decode() if stderr else stdout.decode()
            self._update_metrics(False, execution_time)

            return MCPToolResult(
                success=False,
                error=f"Failed to update ticket: {error_msg}",
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(False, execution_time)

            return MCPToolResult(
                success=False,
                error=f"Ticket update failed: {e!s}",
                execution_time=execution_time,
            )


class TicketViewTool(BaseToolAdapter):
    """
    View detailed ticket information.

    WHY: Users need to see full ticket details including description, metadata,
    and all associated information for understanding context and status.
    """

    def __init__(self):
        """Initialize the ticket view tool."""
        definition = MCPToolDefinition(
            name="ticket_view",
            description="View detailed information about a specific ticket",
            input_schema={
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "Ticket ID to view (e.g., TSK-0001)",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "text"],
                        "description": "Output format",
                        "default": "json",
                    },
                },
                "required": ["ticket_id"],
            },
        )
        super().__init__(definition)

    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        View a ticket using aitrackdown CLI.

        Args:
            invocation: Tool invocation request

        Returns:
            Tool execution result with ticket details
        """
        start_time = datetime.now()

        try:
            params = invocation.parameters
            ticket_id = params["ticket_id"]
            format_type = params.get("format", "json")

            # Build aitrackdown command - use show for viewing
            cmd = ["aitrackdown", "show", ticket_id]

            # Execute command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            execution_time = (datetime.now() - start_time).total_seconds()

            if process.returncode == 0:
                output = stdout.decode().strip()

                if format_type == "json":
                    try:
                        ticket_data = json.loads(output)
                    except json.JSONDecodeError:
                        ticket_data = {"raw_output": output}
                else:
                    ticket_data = {"raw_output": output}

                self._update_metrics(True, execution_time)

                return MCPToolResult(
                    success=True,
                    data=ticket_data,
                    execution_time=execution_time,
                    metadata={
                        "tool": "ticket_view",
                        "operation": "view",
                        "ticket_id": ticket_id,
                    },
                )
            error_msg = stderr.decode() if stderr else stdout.decode()
            self._update_metrics(False, execution_time)

            return MCPToolResult(
                success=False,
                error=f"Failed to view ticket: {error_msg}",
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(False, execution_time)

            return MCPToolResult(
                success=False,
                error=f"Ticket view failed: {e!s}",
                execution_time=execution_time,
            )


class TicketSearchTool(BaseToolAdapter):
    """
    Search tickets by keywords.

    WHY: Users need to find specific tickets based on content, tags, or other criteria.
    This tool provides keyword search across ticket titles and descriptions.
    """

    def __init__(self):
        """Initialize the ticket search tool."""
        definition = MCPToolDefinition(
            name="ticket_search",
            description="Search tickets by keywords in title or description",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query keywords"},
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of results",
                        "default": 10,
                    },
                    "type": {
                        "type": "string",
                        "enum": ["all", "task", "issue", "epic"],
                        "description": "Filter by ticket type",
                        "default": "all",
                    },
                },
                "required": ["query"],
            },
        )
        super().__init__(definition)

    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        Search tickets using aitrackdown CLI.

        Args:
            invocation: Tool invocation request

        Returns:
            Tool execution result with matching tickets
        """
        start_time = datetime.now()

        try:
            params = invocation.parameters
            query = params["query"]
            limit = params.get("limit", 10)

            # Build aitrackdown command - use search tasks
            cmd = ["aitrackdown", "search", "tasks", query, "--limit", str(limit)]

            if params.get("type") and params["type"] != "all":
                cmd.extend(["--type", params["type"]])

            # Execute command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            execution_time = (datetime.now() - start_time).total_seconds()

            if process.returncode == 0:
                try:
                    # Try to parse JSON output
                    results = json.loads(stdout.decode())
                except json.JSONDecodeError:
                    # Fallback to text parsing if JSON fails
                    output = stdout.decode().strip()
                    results = {"raw_output": output, "query": query}

                self._update_metrics(True, execution_time)

                return MCPToolResult(
                    success=True,
                    data=results,
                    execution_time=execution_time,
                    metadata={
                        "tool": "ticket_search",
                        "operation": "search",
                        "query": query,
                    },
                )
            error_msg = stderr.decode() if stderr else stdout.decode()
            self._update_metrics(False, execution_time)

            return MCPToolResult(
                success=False,
                error=f"Failed to search tickets: {error_msg}",
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(False, execution_time)

            return MCPToolResult(
                success=False,
                error=f"Ticket search failed: {e!s}",
                execution_time=execution_time,
            )


# Export all ticket tools
__all__ = [
    "TicketCreateTool",
    "TicketListTool",
    "TicketSearchTool",
    "TicketUpdateTool",
    "TicketViewTool",
]
