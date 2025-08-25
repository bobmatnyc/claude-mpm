"""
Comprehensive unit tests for tickets command refactoring.

WHY: These tests ensure the tickets command functionality is preserved
during refactoring from a god class to service-oriented architecture.

DESIGN DECISIONS:
- Test all CRUD operations and command routing
- Mock external dependencies (subprocess, aitrackdown)
- Test error handling and edge cases
- Verify output formatting in different modes
- Test pagination and filtering logic
- Ensure backward compatibility
"""

import json
import subprocess
from argparse import Namespace
from unittest.mock import Mock, patch

from claude_mpm.cli.commands.tickets import TicketsCommand, manage_tickets
from claude_mpm.cli.shared.base_command import CommandResult
from claude_mpm.constants import TicketCommands


class TestTicketsCommand:
    """Test TicketsCommand functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.command = TicketsCommand()

    def test_initialization(self):
        """Test TicketsCommand initialization."""
        assert self.command.command_name == "tickets"
        assert self.command.logger is not None

    def test_validate_args_no_subcommand(self):
        """Test validation when no subcommand is provided."""
        args = Namespace()
        error = self.command.validate_args(args)
        assert error == "No tickets subcommand specified"

    def test_validate_args_invalid_subcommand(self):
        """Test validation with invalid subcommand."""
        args = Namespace(tickets_command="invalid")
        error = self.command.validate_args(args)
        assert "Unknown tickets command: invalid" in error

    def test_validate_args_valid_subcommands(self):
        """Test validation with all valid subcommands."""
        valid_commands = [cmd.value for cmd in TicketCommands]

        for cmd in valid_commands:
            args = Namespace(tickets_command=cmd)
            error = self.command.validate_args(args)
            assert error is None, f"Command {cmd} should be valid"

    @patch("claude_mpm.cli.commands.tickets.create_ticket_legacy")
    def test_create_ticket_success(self, mock_create):
        """Test successful ticket creation."""
        mock_create.return_value = 0

        args = Namespace(
            tickets_command=TicketCommands.CREATE.value,
            title="Test ticket",
            type="task",
            priority="medium",
            description=["Test", "description"],
            tags="bug,urgent",
            parent_epic=None,
            parent_issue=None,
            verbose=False,
        )

        result = self.command.run(args)

        assert result.success is True
        assert result.exit_code == 0
        assert "Ticket created successfully" in result.message
        mock_create.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.tickets.create_ticket_legacy")
    def test_create_ticket_failure(self, mock_create):
        """Test failed ticket creation."""
        mock_create.return_value = 1

        args = Namespace(
            tickets_command=TicketCommands.CREATE.value,
            title="Test ticket",
            type="task",
            priority="medium",
            description=[],
            tags="",
            verbose=False,
        )

        result = self.command.run(args)

        assert result.success is False
        assert result.exit_code == 1
        assert "Failed to create ticket" in result.message

    @patch("claude_mpm.cli.commands.tickets.list_tickets_legacy")
    def test_list_tickets_success(self, mock_list):
        """Test successful ticket listing."""
        mock_list.return_value = 0

        args = Namespace(
            tickets_command=TicketCommands.LIST.value,
            limit=10,
            page=1,
            page_size=20,
            type="all",
            status="all",
            verbose=False,
        )

        result = self.command.run(args)

        assert result.success is True
        assert "Tickets listed successfully" in result.message
        mock_list.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.tickets.view_ticket_legacy")
    def test_view_ticket_success(self, mock_view):
        """Test successful ticket viewing."""
        mock_view.return_value = 0

        args = Namespace(
            tickets_command=TicketCommands.VIEW.value, ticket_id="TSK-001", verbose=True
        )

        result = self.command.run(args)

        assert result.success is True
        assert "Ticket viewed successfully" in result.message
        mock_view.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.tickets.update_ticket_legacy")
    def test_update_ticket_success(self, mock_update):
        """Test successful ticket update."""
        mock_update.return_value = 0

        args = Namespace(
            tickets_command=TicketCommands.UPDATE.value,
            ticket_id="TSK-001",
            status="in_progress",
            priority="high",
            description=["Updated", "description"],
            tags="updated,tags",
            assign="user@example.com",
        )

        result = self.command.run(args)

        assert result.success is True
        assert "Ticket updated successfully" in result.message
        mock_update.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.tickets.close_ticket_legacy")
    def test_close_ticket_success(self, mock_close):
        """Test successful ticket closure."""
        mock_close.return_value = 0

        args = Namespace(
            tickets_command=TicketCommands.CLOSE.value,
            ticket_id="TSK-001",
            resolution="Fixed the issue",
        )

        result = self.command.run(args)

        assert result.success is True
        assert "Ticket closed successfully" in result.message
        mock_close.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.tickets.delete_ticket_legacy")
    def test_delete_ticket_success(self, mock_delete):
        """Test successful ticket deletion."""
        mock_delete.return_value = 0

        args = Namespace(
            tickets_command=TicketCommands.DELETE.value, ticket_id="TSK-001", force=True
        )

        result = self.command.run(args)

        assert result.success is True
        assert "Ticket deleted successfully" in result.message
        mock_delete.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.tickets.search_tickets_legacy")
    def test_search_tickets_success(self, mock_search):
        """Test successful ticket search."""
        mock_search.return_value = 0

        args = Namespace(
            tickets_command=TicketCommands.SEARCH.value,
            query="bug",
            type="all",
            status="all",
            limit=10,
        )

        result = self.command.run(args)

        assert result.success is True
        assert "Tickets searched successfully" in result.message
        mock_search.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.tickets.add_comment_legacy")
    def test_add_comment_success(self, mock_comment):
        """Test successful comment addition."""
        mock_comment.return_value = 0

        args = Namespace(
            tickets_command=TicketCommands.COMMENT.value,
            ticket_id="TSK-001",
            comment=["This", "is", "a", "comment"],
        )

        result = self.command.run(args)

        assert result.success is True
        assert "Comment added successfully" in result.message
        mock_comment.assert_called_once_with(args)

    @patch("claude_mpm.cli.commands.tickets.update_workflow_legacy")
    def test_update_workflow_success(self, mock_workflow):
        """Test successful workflow update."""
        mock_workflow.return_value = 0

        args = Namespace(
            tickets_command=TicketCommands.WORKFLOW.value,
            ticket_id="TSK-001",
            state="ready",
            comment="Ready for review",
        )

        result = self.command.run(args)

        assert result.success is True
        assert "Workflow updated successfully" in result.message
        mock_workflow.assert_called_once_with(args)

    def test_run_exception_handling(self):
        """Test exception handling in run method."""
        args = Namespace(tickets_command="invalid_command")

        result = self.command.run(args)

        assert result.success is False
        assert "Unknown tickets command" in result.message


class TestTicketLegacyFunctions:
    """Test legacy ticket functions that will be refactored into services."""

    @patch("claude_mpm.services.ticket_manager.TicketManager")
    def test_create_ticket_legacy_basic(self, mock_manager_class):
        """Test basic ticket creation."""
        from claude_mpm.cli.commands.tickets import create_ticket_legacy

        mock_manager = Mock()
        mock_manager.create_ticket.return_value = "TSK-001"
        mock_manager_class.return_value = mock_manager

        args = Namespace(
            title="Test ticket",
            type="task",
            priority="medium",
            description=["Test", "description"],
            tags="bug,urgent",
            parent_epic=None,
            parent_issue=None,
            verbose=False,
        )

        with patch("builtins.print") as mock_print:
            result = create_ticket_legacy(args)

        assert result == 0
        mock_manager.create_ticket.assert_called_once_with(
            title="Test ticket",
            ticket_type="task",
            description="Test description",
            priority="medium",
            tags=["bug", "urgent"],
            source="claude-mpm-cli",
            parent_epic=None,
            parent_issue=None,
        )
        mock_print.assert_called_with("✅ Created ticket: TSK-001")

    @patch("subprocess.run")
    @patch("claude_mpm.services.ticket_manager.TicketManager")
    def test_list_tickets_legacy_with_aitrackdown(
        self, mock_manager_class, mock_subprocess
    ):
        """Test ticket listing using aitrackdown CLI."""
        from claude_mpm.cli.commands.tickets import list_tickets_legacy

        # Mock aitrackdown output
        tickets_data = [
            {
                "id": "TSK-001",
                "title": "Test ticket 1",
                "status": "open",
                "priority": "high",
                "tags": ["bug"],
                "created_at": "2024-01-01T00:00:00Z",
                "metadata": {"ticket_type": "task"},
            },
            {
                "id": "TSK-002",
                "title": "Test ticket 2",
                "status": "in_progress",
                "priority": "medium",
                "tags": ["feature"],
                "created_at": "2024-01-02T00:00:00Z",
                "metadata": {"ticket_type": "issue"},
            },
        ]

        mock_result = Mock()
        mock_result.stdout = json.dumps(tickets_data)
        mock_subprocess.return_value = mock_result

        args = Namespace(
            page=1, page_size=20, limit=20, type="all", status="all", verbose=False
        )

        with patch("builtins.print") as mock_print:
            result = list_tickets_legacy(args)

        assert result == 0
        mock_subprocess.assert_called_once()
        # Check that tickets are displayed
        calls = mock_print.call_args_list
        assert any("TSK-001" in str(call) for call in calls)
        assert any("TSK-002" in str(call) for call in calls)

    @patch("claude_mpm.services.ticket_manager.TicketManager")
    def test_list_tickets_legacy_fallback(self, mock_manager_class):
        """Test ticket listing fallback when aitrackdown is not available."""
        from claude_mpm.cli.commands.tickets import list_tickets_legacy

        mock_manager = Mock()
        mock_manager.list_recent_tickets.return_value = [
            {
                "id": "TSK-001",
                "title": "Test ticket",
                "status": "open",
                "priority": "high",
                "tags": ["bug"],
                "created_at": "2024-01-01T00:00:00Z",
                "metadata": {"ticket_type": "task"},
            }
        ]
        mock_manager_class.return_value = mock_manager

        args = Namespace(
            page=1, page_size=20, limit=10, type="all", status="all", verbose=False
        )

        with patch("subprocess.run", side_effect=FileNotFoundError):
            with patch("builtins.print") as mock_print:
                result = list_tickets_legacy(args)

        assert result == 0
        mock_manager.list_recent_tickets.assert_called_once()

    @patch("claude_mpm.services.ticket_manager.TicketManager")
    def test_view_ticket_legacy_success(self, mock_manager_class):
        """Test viewing a specific ticket."""
        from claude_mpm.cli.commands.tickets import view_ticket_legacy

        mock_manager = Mock()
        mock_manager.get_ticket.return_value = {
            "id": "TSK-001",
            "title": "Test ticket",
            "status": "open",
            "priority": "high",
            "tags": ["bug", "urgent"],
            "description": "Test description",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "metadata": {"ticket_type": "task", "parent_epic": "EP-001"},
        }
        mock_manager_class.return_value = mock_manager

        args = Namespace(ticket_id="TSK-001", verbose=True)

        with patch("builtins.print") as mock_print:
            result = view_ticket_legacy(args)

        assert result == 0
        mock_manager.get_ticket.assert_called_once_with("TSK-001")
        # Check that ticket details are displayed
        calls = mock_print.call_args_list
        assert any("TSK-001" in str(call) for call in calls)
        assert any("Test ticket" in str(call) for call in calls)

    @patch("claude_mpm.services.ticket_manager.TicketManager")
    def test_view_ticket_legacy_not_found(self, mock_manager_class):
        """Test viewing a non-existent ticket."""
        from claude_mpm.cli.commands.tickets import view_ticket_legacy

        mock_manager = Mock()
        mock_manager.get_ticket.return_value = None
        mock_manager_class.return_value = mock_manager

        args = Namespace(ticket_id="TSK-999", verbose=False)

        with patch("builtins.print") as mock_print:
            result = view_ticket_legacy(args)

        assert result == 1
        mock_print.assert_called_with("❌ Ticket TSK-999 not found")

    @patch("subprocess.run")
    @patch("claude_mpm.services.ticket_manager.TicketManager")
    def test_update_ticket_legacy_with_aitrackdown(
        self, mock_manager_class, mock_subprocess
    ):
        """Test updating ticket with aitrackdown fallback."""
        from claude_mpm.cli.commands.tickets import update_ticket_legacy

        mock_manager = Mock()
        mock_manager.update_task.return_value = False  # Force fallback
        mock_manager_class.return_value = mock_manager

        mock_subprocess.return_value = Mock()

        args = Namespace(
            ticket_id="TSK-001",
            status="in_progress",
            priority="high",
            description=["Updated", "description"],
            tags="updated,tags",
            assign="user@example.com",
        )

        with patch("builtins.print") as mock_print:
            result = update_ticket_legacy(args)

        assert result == 0
        mock_subprocess.assert_called_once()
        mock_print.assert_called_with("✅ Updated ticket: TSK-001")

    @patch("subprocess.run")
    def test_delete_ticket_legacy_with_confirmation(self, mock_subprocess):
        """Test ticket deletion with user confirmation."""
        from claude_mpm.cli.commands.tickets import delete_ticket_legacy

        mock_subprocess.return_value = Mock()

        args = Namespace(ticket_id="TSK-001", force=False)

        with patch("builtins.input", return_value="y"):
            with patch("builtins.print") as mock_print:
                result = delete_ticket_legacy(args)

        assert result == 0
        mock_subprocess.assert_called_once_with(
            ["aitrackdown", "delete", "TSK-001"],
            check=True,
            capture_output=True,
            text=True,
        )
        mock_print.assert_called_with("✅ Deleted ticket: TSK-001")

    @patch("subprocess.run")
    def test_delete_ticket_legacy_cancelled(self, mock_subprocess):
        """Test ticket deletion cancelled by user."""
        from claude_mpm.cli.commands.tickets import delete_ticket_legacy

        args = Namespace(ticket_id="TSK-001", force=False)

        with patch("builtins.input", return_value="n"):
            with patch("builtins.print") as mock_print:
                result = delete_ticket_legacy(args)

        assert result == 0
        mock_subprocess.assert_not_called()
        mock_print.assert_called_with("Deletion cancelled")

    @patch("claude_mpm.services.ticket_manager.TicketManager")
    def test_search_tickets_legacy_success(self, mock_manager_class):
        """Test ticket search functionality."""
        from claude_mpm.cli.commands.tickets import search_tickets_legacy

        mock_manager = Mock()
        mock_manager.list_recent_tickets.return_value = [
            {
                "id": "TSK-001",
                "title": "Fix bug in login",
                "status": "open",
                "description": "There's a bug in the login process",
                "tags": ["bug", "auth"],
                "metadata": {"ticket_type": "task"},
            },
            {
                "id": "TSK-002",
                "title": "Add feature",
                "status": "closed",
                "description": "Add new feature to dashboard",
                "tags": ["feature"],
                "metadata": {"ticket_type": "issue"},
            },
        ]
        mock_manager_class.return_value = mock_manager

        args = Namespace(query="bug", type="all", status="all", limit=10)

        with patch("builtins.print") as mock_print:
            result = search_tickets_legacy(args)

        assert result == 0
        # Should only show TSK-001 which contains "bug"
        calls = mock_print.call_args_list
        assert any("TSK-001" in str(call) for call in calls)
        assert not any("TSK-002" in str(call) for call in calls)

    @patch("subprocess.run")
    def test_add_comment_legacy_success(self, mock_subprocess):
        """Test adding comment to ticket."""
        from claude_mpm.cli.commands.tickets import add_comment_legacy

        mock_subprocess.return_value = Mock()

        args = Namespace(ticket_id="TSK-001", comment=["This", "is", "a", "comment"])

        with patch("builtins.print") as mock_print:
            result = add_comment_legacy(args)

        assert result == 0
        mock_subprocess.assert_called_once_with(
            ["aitrackdown", "comment", "TSK-001", "This is a comment"],
            check=True,
            capture_output=True,
            text=True,
        )
        mock_print.assert_called_with("✅ Added comment to ticket: TSK-001")

    @patch("subprocess.run")
    def test_update_workflow_legacy_success(self, mock_subprocess):
        """Test updating workflow state."""
        from claude_mpm.cli.commands.tickets import update_workflow_legacy

        mock_subprocess.return_value = Mock()

        args = Namespace(ticket_id="TSK-001", state="ready", comment="Ready for review")

        with patch("builtins.print") as mock_print:
            result = update_workflow_legacy(args)

        assert result == 0
        mock_subprocess.assert_called_once_with(
            [
                "aitrackdown",
                "transition",
                "TSK-001",
                "ready",
                "--comment",
                "Ready for review",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        mock_print.assert_called_with("✅ Updated workflow state for TSK-001 to: ready")


class TestManageTicketsBackwardCompatibility:
    """Test backward compatibility functions."""

    @patch("claude_mpm.cli.commands.tickets.TicketsCommand")
    def test_manage_tickets_function(self, mock_command_class):
        """Test manage_tickets backward compatibility wrapper."""
        mock_command = Mock()
        mock_result = CommandResult.success_result("Success", data={"test": "data"})
        mock_command.execute.return_value = mock_result
        mock_command_class.return_value = mock_command

        args = Namespace(tickets_command=TicketCommands.LIST.value, format="json")

        with patch.object(mock_command, "print_result") as mock_print:
            result = manage_tickets(args)

        assert result == 0
        mock_command.execute.assert_called_once_with(args)
        mock_print.assert_called_once_with(mock_result, args)

    def test_list_tickets_wrapper(self):
        """Test list_tickets backward compatibility wrapper."""
        from claude_mpm.cli.commands.tickets import list_tickets

        args = Namespace(limit=10, verbose=False)

        with patch("claude_mpm.cli.commands.tickets.manage_tickets") as mock_manage:
            mock_manage.return_value = 0

            result = list_tickets(args)

            assert result == 0
            assert args.tickets_command == TicketCommands.LIST.value
            mock_manage.assert_called_once_with(args)


class TestTicketsPagination:
    """Test pagination functionality in ticket listing."""

    @patch("subprocess.run")
    def test_pagination_calculation(self, mock_subprocess):
        """Test pagination offset calculation."""
        from claude_mpm.cli.commands.tickets import list_tickets_legacy

        # Create enough tickets for multiple pages
        tickets = [
            {
                "id": f"TSK-{i:03d}",
                "title": f"Ticket {i}",
                "status": "open",
                "priority": "medium",
                "tags": [],
                "created_at": f"2024-01-{i:02d}T00:00:00Z",
                "metadata": {"ticket_type": "task"},
            }
            for i in range(1, 51)
        ]

        mock_result = Mock()
        mock_result.stdout = json.dumps(tickets)
        mock_subprocess.return_value = mock_result

        # Test page 2 with page_size=10
        args = Namespace(
            page=2, page_size=10, limit=10, type="all", status="all", verbose=False
        )

        with patch("builtins.print") as mock_print:
            result = list_tickets_legacy(args)

        assert result == 0
        # Should show tickets 11-20
        calls = str(mock_print.call_args_list)
        assert "TSK-011" in calls
        assert "TSK-020" in calls
        assert "TSK-010" not in calls  # Previous page
        assert "TSK-021" not in calls  # Next page

    def test_pagination_invalid_page(self):
        """Test handling of invalid page numbers."""
        from claude_mpm.cli.commands.tickets import list_tickets_legacy

        args = Namespace(
            page=0,  # Invalid page number
            page_size=10,
            limit=10,
            type="all",
            status="all",
            verbose=False,
        )

        with patch("builtins.print") as mock_print:
            result = list_tickets_legacy(args)

        assert result == 1
        mock_print.assert_called_with("❌ Page number must be 1 or greater")


class TestTicketsErrorHandling:
    """Test error handling in tickets command."""

    @patch("claude_mpm.cli.commands.tickets.create_ticket_legacy")
    def test_create_ticket_exception(self, mock_create):
        """Test exception handling during ticket creation."""
        mock_create.side_effect = Exception("Database error")

        command = TicketsCommand()
        args = Namespace(
            tickets_command=TicketCommands.CREATE.value, title="Test ticket"
        )

        result = command.run(args)

        assert result.success is False
        assert "Error creating ticket" in result.message

    @patch("subprocess.run")
    def test_aitrackdown_command_failure(self, mock_subprocess):
        """Test handling of aitrackdown command failures."""
        from claude_mpm.cli.commands.tickets import delete_ticket_legacy

        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "aitrackdown")

        args = Namespace(ticket_id="TSK-001", force=True)

        with patch("builtins.print") as mock_print:
            result = delete_ticket_legacy(args)

        assert result == 1
        mock_print.assert_called_with("❌ Failed to delete ticket: TSK-001")

    def test_no_ticket_id_provided(self):
        """Test handling when no ticket ID is provided."""
        from claude_mpm.cli.commands.tickets import view_ticket_legacy

        args = Namespace()  # No ticket_id attribute

        with patch("builtins.print") as mock_print:
            result = view_ticket_legacy(args)

        assert result == 1
        mock_print.assert_called_with("❌ No ticket ID provided")
