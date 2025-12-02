"""
Test MCP Ticket Tools
=====================

Tests for the MCP ticket tool adapters that wrap aitrackdown functionality.

WHY: Ensure that the ticket tools correctly interface with aitrackdown CLI
and handle various scenarios including success, errors, and edge cases.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from claude_mpm.services.mcp_gateway.core.interfaces import MCPToolInvocation
from claude_mpm.services.mcp_gateway.tools.ticket_tools import (
    TicketCreateTool,
    TicketListTool,
    TicketSearchTool,
    TicketUpdateTool,
    TicketViewTool,
)


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for testing CLI interactions."""
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        yield mock_exec


class TestTicketCreateTool:
    """Test the ticket creation tool."""

    @pytest.mark.asyncio
    async def test_create_task_success(self):
        """Test successful task creation."""
        # Setup mock process
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            b"Created ticket: TSK-0001\nTask 'Test task' created successfully",
            b"",
        )
        self.return_value = mock_process

        # Create tool and invocation
        tool = TicketCreateTool()
        invocation = MCPToolInvocation(
            tool_name="ticket_create",
            parameters={
                "type": "task",
                "title": "Test task",
                "description": "Test description",
                "priority": "medium",
            },
        )

        # Invoke tool
        result = await tool.invoke(invocation)

        # Verify result
        assert result.success is True
        assert result.data["ticket_id"] == "TSK-0001"
        assert result.data["type"] == "task"
        assert result.data["title"] == "Test task"
        assert "Created ticket" in result.data["message"]

        # Verify CLI command
        self.assert_called_once()
        cmd_args = self.call_args[0]
        assert cmd_args[0] == "aitrackdown"
        assert cmd_args[1] == "create"
        assert cmd_args[2] == "task"
        assert cmd_args[3] == "Test task"
        assert "--description" in cmd_args
        assert "--priority" in cmd_args

    @pytest.mark.asyncio
    async def test_create_with_tags(self):
        """Test creating a ticket with tags."""
        # Setup mock process
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Created ticket: ISS-0001", b"")
        self.return_value = mock_process

        # Create tool and invocation
        tool = TicketCreateTool()
        invocation = MCPToolInvocation(
            tool_name="ticket_create",
            parameters={
                "type": "issue",
                "title": "Bug report",
                "tags": ["bug", "ui", "critical"],
            },
        )

        # Invoke tool
        result = await tool.invoke(invocation)

        # Verify result
        assert result.success is True
        assert result.data["ticket_id"] == "ISS-0001"

        # Verify tags were passed correctly
        cmd_args = self.call_args[0]
        assert "--tags" in cmd_args
        tags_idx = cmd_args.index("--tags")
        assert cmd_args[tags_idx + 1] == "bug,ui,critical"

    @pytest.mark.asyncio
    async def test_create_failure(self):
        """Test handling of creation failure."""
        # Setup mock process with error
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"Error: Invalid ticket type")
        self.return_value = mock_process

        # Create tool and invocation
        tool = TicketCreateTool()
        invocation = MCPToolInvocation(
            tool_name="ticket_create", parameters={"type": "invalid", "title": "Test"}
        )

        # Invoke tool
        result = await tool.invoke(invocation)

        # Verify error result
        assert result.success is False
        assert "Failed to create ticket" in result.error
        assert "Invalid ticket type" in result.error


class TestTicketListTool:
    """Test the ticket listing tool."""

    @pytest.mark.asyncio
    async def test_list_json_output(self):
        """Test listing tickets with JSON output."""
        # Setup mock process
        mock_tickets = [
            {"id": "TSK-0001", "title": "Task 1", "status": "open"},
            {"id": "TSK-0002", "title": "Task 2", "status": "done"},
        ]
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (json.dumps(mock_tickets).encode(), b"")
        self.return_value = mock_process

        # Create tool and invocation
        tool = TicketListTool()
        invocation = MCPToolInvocation(
            tool_name="ticket_list",
            parameters={"limit": 10, "type": "task", "status": "all"},
        )

        # Invoke tool
        result = await tool.invoke(invocation)

        # Verify result
        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0]["id"] == "TSK-0001"
        assert result.metadata["count"] == 2

        # Verify CLI command
        cmd_args = self.call_args[0]
        assert "--limit" in cmd_args
        assert "--format" in cmd_args
        assert "json" in cmd_args
        assert "--type" in cmd_args
        assert "task" in cmd_args

    @pytest.mark.asyncio
    async def test_list_text_fallback(self):
        """Test fallback to text parsing when JSON fails."""
        # Setup mock process with non-JSON output
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            b"TSK-0001: Task 1\nTSK-0002: Task 2",
            b"",
        )
        self.return_value = mock_process

        # Create tool and invocation
        tool = TicketListTool()
        invocation = MCPToolInvocation(tool_name="ticket_list", parameters={})

        # Invoke tool
        result = await tool.invoke(invocation)

        # Verify result
        assert result.success is True
        assert "raw_output" in result.data
        assert "TSK-0001" in result.data["raw_output"]


class TestTicketUpdateTool:
    """Test the ticket update tool."""

    @pytest.mark.asyncio
    async def test_update_status(self):
        """Test updating ticket status."""
        # Setup mock process
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            b"Ticket TSK-0001 transitioned to in_progress",
            b"",
        )
        self.return_value = mock_process

        # Create tool and invocation
        tool = TicketUpdateTool()
        invocation = MCPToolInvocation(
            tool_name="ticket_update",
            parameters={
                "ticket_id": "TSK-0001",
                "status": "in_progress",
                "comment": "Starting work",
            },
        )

        # Invoke tool
        result = await tool.invoke(invocation)

        # Verify result
        assert result.success is True
        assert result.data["ticket_id"] == "TSK-0001"
        assert "status" in result.data["updated_fields"]

        # Verify CLI command
        cmd_args = self.call_args[0]
        assert cmd_args[0] == "aitrackdown"
        assert cmd_args[1] == "transition"
        assert cmd_args[2] == "TSK-0001"
        assert cmd_args[3] == "in_progress"
        assert "--comment" in cmd_args

    @pytest.mark.asyncio
    async def test_update_priority(self):
        """Test updating ticket priority."""
        # Setup mock process
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            b"Ticket TSK-0001 priority updated to high",
            b"",
        )
        self.return_value = mock_process

        # Create tool and invocation
        tool = TicketUpdateTool()
        invocation = MCPToolInvocation(
            tool_name="ticket_update",
            parameters={"ticket_id": "TSK-0001", "priority": "high"},
        )

        # Invoke tool
        result = await tool.invoke(invocation)

        # Verify result
        assert result.success is True
        assert "priority" in result.data["updated_fields"]

        # Verify CLI command uses update for priority
        cmd_args = self.call_args[0]
        assert cmd_args[0] == "aitrackdown"
        assert cmd_args[1] == "update"
        assert cmd_args[2] == "TSK-0001"
        assert "--priority" in cmd_args
        assert "high" in cmd_args

    @pytest.mark.asyncio
    async def test_update_no_fields(self):
        """Test error when no update fields provided."""
        # Create tool and invocation
        tool = TicketUpdateTool()
        invocation = MCPToolInvocation(
            tool_name="ticket_update", parameters={"ticket_id": "TSK-0001"}
        )

        # Invoke tool
        result = await tool.invoke(invocation)

        # Verify error result
        assert result.success is False
        assert "No update fields provided" in result.error


class TestTicketViewTool:
    """Test the ticket view tool."""

    @pytest.mark.asyncio
    async def test_view_json_format(self):
        """Test viewing ticket with JSON format."""
        # Setup mock process
        mock_ticket = {
            "id": "TSK-0001",
            "title": "Test task",
            "status": "open",
            "description": "Test description",
        }
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (json.dumps(mock_ticket).encode(), b"")
        self.return_value = mock_process

        # Create tool and invocation
        tool = TicketViewTool()
        invocation = MCPToolInvocation(
            tool_name="ticket_view",
            parameters={"ticket_id": "TSK-0001", "format": "json"},
        )

        # Invoke tool
        result = await tool.invoke(invocation)

        # Verify result
        assert result.success is True
        assert result.data["id"] == "TSK-0001"
        assert result.data["title"] == "Test task"
        assert result.metadata["ticket_id"] == "TSK-0001"

        # Verify CLI command
        cmd_args = self.call_args[0]
        assert cmd_args[0] == "aitrackdown"
        assert cmd_args[1] == "view"
        assert cmd_args[2] == "TSK-0001"
        assert "--format" in cmd_args
        assert "json" in cmd_args


class TestTicketSearchTool:
    """Test the ticket search tool."""

    @pytest.mark.asyncio
    async def test_search_with_filters(self):
        """Test searching tickets with filters."""
        # Setup mock process
        mock_results = [
            {"id": "TSK-0001", "title": "Fix bug in login"},
            {"id": "ISS-0002", "title": "Bug in authentication"},
        ]
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (json.dumps(mock_results).encode(), b"")
        self.return_value = mock_process

        # Create tool and invocation
        tool = TicketSearchTool()
        invocation = MCPToolInvocation(
            tool_name="ticket_search",
            parameters={"query": "bug", "limit": 5, "type": "task"},
        )

        # Invoke tool
        result = await tool.invoke(invocation)

        # Verify result
        assert result.success is True
        assert len(result.data) == 2
        assert result.metadata["query"] == "bug"

        # Verify CLI command
        cmd_args = self.call_args[0]
        assert cmd_args[0] == "aitrackdown"
        assert cmd_args[1] == "search"
        assert cmd_args[2] == "bug"
        assert "--limit" in cmd_args
        assert "--type" in cmd_args
        assert "task" in cmd_args


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
