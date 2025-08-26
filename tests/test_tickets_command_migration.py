"""
Test for the migrated TicketsCommand class.

WHY: Verify that the migration to BaseCommand pattern works correctly
and maintains backward compatibility with ai-trackdown integration.
"""

from argparse import Namespace
from unittest.mock import patch

import pytest

from claude_mpm.cli.commands.tickets import TicketsCommand
from claude_mpm.cli.shared.base_command import CommandResult
from claude_mpm.constants import TicketCommands


class TestTicketsCommandMigration:
    """Test the migrated TicketsCommand class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.command = TicketsCommand()

    def test_command_initialization():
        """Test that TicketsCommand initializes correctly."""
        assert self.command.command_name == "tickets"
        assert self.command.logger is not None

    def test_validate_args_no_subcommand():
        """Test argument validation with no subcommand."""
        args = Namespace()
        result = self.command.validate_args(args)
        assert result == "No tickets subcommand specified"

    def test_validate_args_invalid_subcommand():
        """Test argument validation with invalid subcommand."""
        args = Namespace(tickets_command="invalid")
        result = self.command.validate_args(args)
        assert "Unknown tickets command" in result

    def test_validate_args_valid_subcommand():
        """Test argument validation with valid subcommand."""
        args = Namespace(tickets_command=TicketCommands.LIST.value)
        result = self.command.validate_args(args)
        assert result is None

    @patch("claude_mpm.cli.commands.tickets.list_tickets_legacy")
    def test_list_tickets_success(self):
        """Test successful list tickets execution."""
        self.return_value = 0
        args = Namespace(tickets_command=TicketCommands.LIST.value)

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.exit_code == 0
        assert "successfully" in result.message

    @patch("claude_mpm.cli.commands.tickets.list_tickets_legacy")
    def test_list_tickets_failure(self):
        """Test failed list tickets execution."""
        self.return_value = 1
        args = Namespace(tickets_command=TicketCommands.LIST.value)

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert result.exit_code == 1
        assert "Failed" in result.message

    @patch("claude_mpm.cli.commands.tickets.create_ticket_legacy")
    def test_create_ticket_success(self):
        """Test successful create ticket execution."""
        self.return_value = 0
        args = Namespace(tickets_command=TicketCommands.CREATE.value)

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert result.exit_code == 0
        assert "created successfully" in result.message

    @patch("claude_mpm.cli.commands.tickets.view_ticket_legacy")
    def test_view_ticket_success(self):
        """Test successful view ticket execution."""
        self.return_value = 0
        args = Namespace(tickets_command=TicketCommands.VIEW.value)

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "viewed successfully" in result.message

    @patch("claude_mpm.cli.commands.tickets.update_ticket_legacy")
    def test_update_ticket_success(self):
        """Test successful update ticket execution."""
        self.return_value = 0
        args = Namespace(tickets_command=TicketCommands.UPDATE.value)

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "updated successfully" in result.message

    @patch("claude_mpm.cli.commands.tickets.close_ticket_legacy")
    def test_close_ticket_success(self):
        """Test successful close ticket execution."""
        self.return_value = 0
        args = Namespace(tickets_command=TicketCommands.CLOSE.value)

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is True
        assert "closed successfully" in result.message

    def test_unknown_command():
        """Test handling of unknown command."""
        args = Namespace(tickets_command="unknown")

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "Unknown tickets command" in result.message

    def test_backward_compatibility_function():
        """Test that the manage_tickets function maintains backward compatibility."""
        from claude_mpm.cli.commands.tickets import manage_tickets

        with patch.object(TicketsCommand, "execute") as mock_execute:
            mock_result = CommandResult.success_result("Test success")
            mock_execute.return_value = mock_result

            args = Namespace(tickets_command=TicketCommands.LIST.value)
            exit_code = manage_tickets(args)

            assert exit_code == 0
            mock_execute.assert_called_once_with(args)

    def test_list_tickets_compatibility_function():
        """Test that the list_tickets compatibility function works."""
        from claude_mpm.cli.commands.tickets import list_tickets

        with patch("claude_mpm.cli.commands.tickets.manage_tickets") as mock_manage:
            mock_manage.return_value = 0

            args = Namespace()
            result = list_tickets(args)

            assert result == 0
            mock_manage.assert_called_once_with(args)
            assert args.tickets_command == TicketCommands.LIST.value


class TestTicketsCommandErrorHandling:
    """Test error handling in TicketsCommand."""

    def setup_method(self):
        """Setup test fixtures."""
        self.command = TicketsCommand()

    @patch("claude_mpm.cli.commands.tickets.list_tickets_legacy")
    def test_exception_handling(self):
        """Test that exceptions are properly handled."""
        self.side_effect = Exception("Test error")
        args = Namespace(tickets_command=TicketCommands.LIST.value)

        result = self.command.run(args)

        assert isinstance(result, CommandResult)
        assert result.success is False
        assert "Error executing tickets command" in result.message


if __name__ == "__main__":
    pytest.main([__file__])
