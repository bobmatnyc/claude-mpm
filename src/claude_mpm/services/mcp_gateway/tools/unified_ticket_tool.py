"""
Unified Ticket Tool for MCP Gateway
====================================

Provides a single, unified interface for all ticket management operations
through the MCP Gateway, consolidating create, list, update, view, and search
functionality into one tool with an operation parameter.

WHY: Having 5 separate ticket tools creates unnecessary complexity. A single
tool with an operation parameter provides a cleaner, more intuitive API that
matches the mental model of "ticket operations" better.

DESIGN DECISIONS:
- Single tool with operation parameter for cleaner API
- Conditional parameter validation based on operation type
- Reuses existing logic from separate tools for consistency
- Maintains same error handling and metrics tracking patterns
- Uses JSON Schema oneOf for operation-specific parameter validation
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Any, Dict, Optional

from claude_mpm.services.mcp_gateway.core.interfaces import (
    MCPToolDefinition,
    MCPToolInvocation,
    MCPToolResult,
)
from claude_mpm.services.mcp_gateway.tools.base_adapter import BaseToolAdapter


class UnifiedTicketTool(BaseToolAdapter):
    """
    Unified ticket management tool for aitrackdown operations.

    WHY: Consolidates all ticket operations (create, list, update, view, search)
    into a single tool with an operation parameter, providing a cleaner and more
    intuitive interface for ticket management.

    DESIGN DECISIONS:
    - Use operation parameter to route to appropriate handler
    - Implement conditional parameter validation per operation
    - Maintain backward compatibility with existing aitrackdown CLI
    - Preserve all error handling and metrics from original tools
    """

    def __init__(self):
        """Initialize the unified ticket tool with comprehensive schema."""
        definition = MCPToolDefinition(
            name="ticket",
            description="Unified ticket management tool for all aitrackdown operations",
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["create", "list", "update", "view", "search"],
                        "description": "The ticket operation to perform",
                    },
                    # Create operation parameters
                    "type": {
                        "type": "string",
                        "enum": ["task", "issue", "epic"],
                        "description": "Type of ticket (for create operation)",
                    },
                    "title": {
                        "type": "string",
                        "description": "Title of the ticket (for create operation)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description (for create operation)",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Priority level",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to associate with the ticket (for create)",
                    },
                    "parent_epic": {
                        "type": "string",
                        "description": "Parent epic ID for issues (create operation)",
                    },
                    "parent_issue": {
                        "type": "string",
                        "description": "Parent issue ID for tasks (create operation)",
                    },
                    # List operation parameters
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                    # Update operation parameters
                    "ticket_id": {
                        "type": "string",
                        "description": "Ticket ID (for update/view operations)",
                    },
                    "status": {
                        "type": "string",
                        "enum": [
                            "all",
                            "open",
                            "in-progress",
                            "ready",
                            "tested",
                            "done",
                            "waiting",
                            "closed",
                            "blocked",
                        ],
                        "description": "Status filter or new status",
                    },
                    "comment": {
                        "type": "string",
                        "description": "Comment for update operation",
                    },
                    # View operation parameters
                    "format": {
                        "type": "string",
                        "enum": ["json", "text"],
                        "description": "Output format (for view operation)",
                        "default": "json",
                    },
                    # Search operation parameters
                    "query": {
                        "type": "string",
                        "description": "Search query keywords (for search operation)",
                    },
                },
                "required": ["operation"],
                # Note: Additional validation is handled in the invoke method
                # to avoid using allOf/oneOf/anyOf at the top level which is not
                # supported by the Claude API
            },
        )
        super().__init__(definition)

    async def invoke(self, invocation: MCPToolInvocation) -> MCPToolResult:
        """
        Route the invocation to the appropriate operation handler.

        Args:
            invocation: Tool invocation request

        Returns:
            Tool execution result from the specific operation
        """
        operation = invocation.parameters.get("operation")

        if not operation:
            return MCPToolResult(
                success=False,
                error="Operation parameter is required",
                execution_time=0.0,
            )

        # Validate required parameters based on operation type
        validation_error = self._validate_parameters(operation, invocation.parameters)
        if validation_error:
            return MCPToolResult(
                success=False,
                error=validation_error,
                execution_time=0.0,
            )

        # Route to appropriate handler based on operation
        handlers = {
            "create": self._handle_create,
            "list": self._handle_list,
            "update": self._handle_update,
            "view": self._handle_view,
            "search": self._handle_search,
        }

        handler = handlers.get(operation)
        if not handler:
            return MCPToolResult(
                success=False,
                error=f"Unknown operation: {operation}",
                execution_time=0.0,
            )

        return await handler(invocation.parameters)

    def _validate_parameters(
        self, operation: str, params: Dict[str, Any]
    ) -> Optional[str]:
        """
        Validate parameters based on the operation type.

        Args:
            operation: The operation being performed
            params: Parameters provided for the operation

        Returns:
            Error message if validation fails, None if valid
        """
        if operation == "create":
            if "type" not in params:
                return "'type' parameter is required for create operation"
            if "title" not in params:
                return "'title' parameter is required for create operation"
            if params["type"] not in ["task", "issue", "epic"]:
                return f"Invalid type '{params['type']}'. Must be 'task', 'issue', or 'epic'"

        elif operation == "update":
            if "ticket_id" not in params:
                return "'ticket_id' parameter is required for update operation"

        elif operation == "view":
            if "ticket_id" not in params:
                return "'ticket_id' parameter is required for view operation"

        elif operation == "search":
            if "query" not in params:
                return "'query' parameter is required for search operation"

        elif operation == "list":
            # List operation has no required parameters beyond operation itself
            pass

        else:
            return f"Unknown operation: {operation}"

        return None

    async def _handle_create(self, params: Dict[str, Any]) -> MCPToolResult:
        """
        Handle ticket creation operation.

        Args:
            params: Parameters for ticket creation

        Returns:
            Tool execution result with created ticket ID
        """
        start_time = datetime.now()

        try:
            # Build aitrackdown command
            cmd = ["aitrackdown", "create", params["type"], params["title"]]

            # Add optional parameters
            if "description" in params:
                cmd.extend(["--description", params["description"]])

            if "priority" in params:
                cmd.extend(["--priority", params["priority"]])

            if params.get("tags"):
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
                ticket_id = None
                for line in output.split("\n"):
                    if "TSK-" in line or "ISS-" in line or "EP-" in line:
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
                    metadata={"tool": "ticket", "operation": "create"},
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

    async def _handle_list(self, params: Dict[str, Any]) -> MCPToolResult:
        """
        Handle ticket listing operation.

        Args:
            params: Parameters for ticket listing

        Returns:
            Tool execution result with list of tickets
        """
        start_time = datetime.now()

        try:
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
                        "tool": "ticket",
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

    async def _handle_update(self, params: Dict[str, Any]) -> MCPToolResult:
        """
        Handle ticket update operation.

        Args:
            params: Parameters for ticket update

        Returns:
            Tool execution result
        """
        start_time = datetime.now()

        try:
            ticket_id = params["ticket_id"]

            # Determine which update to perform
            if "status" in params and params["status"] != "all":
                # Use transition command for status updates
                cmd = ["aitrackdown", "transition", ticket_id, params["status"]]

                if "comment" in params:
                    cmd.extend(["--comment", params["comment"]])
            elif "priority" in params:
                # For priority updates, use transition with comment
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
                    metadata={"tool": "ticket", "operation": "update"},
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

    async def _handle_view(self, params: Dict[str, Any]) -> MCPToolResult:
        """
        Handle ticket viewing operation.

        Args:
            params: Parameters for ticket viewing

        Returns:
            Tool execution result with ticket details
        """
        start_time = datetime.now()

        try:
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
                        "tool": "ticket",
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

    async def _handle_search(self, params: Dict[str, Any]) -> MCPToolResult:
        """
        Handle ticket search operation.

        Args:
            params: Parameters for ticket search

        Returns:
            Tool execution result with matching tickets
        """
        start_time = datetime.now()

        try:
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
                    metadata={"tool": "ticket", "operation": "search", "query": query},
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


# Export the unified ticket tool
__all__ = ["UnifiedTicketTool"]
