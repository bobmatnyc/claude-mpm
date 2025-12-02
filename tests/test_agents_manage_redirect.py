"""Test redirect from 'claude-mpm agents manage' to 'claude-mpm config'."""

from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.cli.commands.agents import AgentsCommand
from claude_mpm.cli.shared import CommandResult


class TestAgentsManageRedirect:
    """Test suite for the agents manage redirect functionality."""

    def test_manage_shows_deprecation_message(self):
        """Test that 'agents manage' shows deprecation notice."""
        # Setup
        cmd = AgentsCommand()
        args = MagicMock()
        args.agents_command = "manage"

        # Mock rich.prompt.Confirm to simulate user declining
        # Need to patch where it's imported, not where it's defined
        with patch("rich.prompt.Confirm") as mock_confirm:
            mock_confirm.ask.return_value = False  # User declines

            # Execute
            result = cmd._manage_local_agents(args)

            # Verify
            assert result.success is True
            assert "Redirected to config interface" in result.message
            mock_confirm.ask.assert_called_once()

    def test_manage_launches_config_when_confirmed(self):
        """Test that 'agents manage' launches config when user confirms."""
        # Setup
        cmd = AgentsCommand()
        args = MagicMock()
        args.agents_command = "manage"

        # Mock ConfigureCommand to simulate successful launch
        with patch("rich.prompt.Confirm") as mock_confirm, patch(
            "claude_mpm.cli.commands.configure.ConfigureCommand"
        ) as mock_config_cmd:
            mock_confirm.ask.return_value = True  # User confirms
            mock_config_instance = MagicMock()
            mock_config_instance.execute.return_value = CommandResult.success_result(
                "Configuration completed"
            )
            mock_config_cmd.return_value = mock_config_instance

            # Execute
            result = cmd._manage_local_agents(args)

            # Verify
            assert result.success is True
            assert "Configuration completed" in result.message
            mock_confirm.ask.assert_called_once()
            mock_config_instance.execute.assert_called_once_with(args)

    def test_manage_help_shows_deprecation(self, capsys):
        """Test that help text shows deprecation notice."""
        import argparse

        from claude_mpm.cli.parsers.agents_parser import add_agents_subparser

        # Setup parser
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        agents_parser = add_agents_subparser(subparsers)

        # Capture help output
        # Need to get subparser for 'manage' specifically
        try:
            parser.parse_args(["agents", "manage", "--help"])
        except SystemExit:
            pass  # Expected when --help is used

        captured = capsys.readouterr()
        # Check for deprecation in output (could be in 'out' or 'err')
        output = captured.out + captured.err
        assert "(Deprecated)" in output or "deprecated" in output.lower()
