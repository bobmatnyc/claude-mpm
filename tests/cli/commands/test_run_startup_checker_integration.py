"""Integration test for StartupCheckerService in run command.

Tests that the new StartupCheckerService properly integrates with the run command.
"""

import tempfile
from unittest.mock import MagicMock, patch

from claude_mpm.cli.commands.run import RunCommand


class TestRunStartupCheckerIntegration:
    """Test StartupCheckerService integration with run command."""

    def test_check_configuration_health_uses_new_service(self):
        """Test that _check_configuration_health uses StartupCheckerService."""
        command = RunCommand()

        with patch(
            "claude_mpm.cli.commands.run.StartupCheckerService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.check_configuration.return_value = []

            # Call the method
            command._check_configuration_health()

            # Verify StartupCheckerService was created and used
            mock_service_class.assert_called_once()
            mock_service.check_configuration.assert_called_once()
            mock_service.display_warnings.assert_called_once_with([])

    def test_check_claude_json_memory_uses_new_service(self):
        """Test that _check_claude_json_memory uses StartupCheckerService."""
        command = RunCommand()

        # Create mock args
        args = MagicMock()
        args.mpm_resume = True

        with patch(
            "claude_mpm.cli.commands.run.StartupCheckerService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.check_memory.return_value = None

            # Call the method
            command._check_claude_json_memory(args)

            # Verify StartupCheckerService was created and used
            mock_service_class.assert_called_once()
            mock_service.check_memory.assert_called_once_with(True)

    def test_check_claude_json_memory_displays_warning(self):
        """Test that memory warning is displayed when detected."""
        command = RunCommand()

        # Create mock args
        args = MagicMock()
        args.mpm_resume = True

        with patch(
            "claude_mpm.cli.commands.run.StartupCheckerService"
        ) as mock_service_class:
            from claude_mpm.services.cli.startup_checker import StartupWarning

            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            # Create a mock warning
            warning = StartupWarning(
                category="memory",
                message="Large file detected",
                suggestion="Run cleanup",
            )
            mock_service.check_memory.return_value = warning

            # Call the method
            command._check_claude_json_memory(args)

            # Verify warning was displayed
            mock_service.display_warnings.assert_called_once_with([warning])

    def test_legacy_check_functions_use_new_service(self):
        """Test that legacy check functions use StartupCheckerService."""
        from claude_mpm.cli.commands.run import (_check_claude_json_memory,
                                                 _check_configuration_health)

        # Test _check_configuration_health
        logger = MagicMock()
        with patch(
            "claude_mpm.cli.commands.run.StartupCheckerService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.check_configuration.return_value = []

            _check_configuration_health(logger)

            mock_service_class.assert_called_once()
            mock_service.check_configuration.assert_called_once()

        # Test _check_claude_json_memory
        args = MagicMock()
        args.mpm_resume = True
        logger = MagicMock()

        with patch(
            "claude_mpm.cli.commands.run.StartupCheckerService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.check_memory.return_value = None

            _check_claude_json_memory(args, logger)

            mock_service_class.assert_called_once()
            mock_service.check_memory.assert_called_once_with(True)

    def test_end_to_end_warning_display(self, capsys):
        """Test end-to-end warning display from run command."""
        command = RunCommand()

        with tempfile.TemporaryDirectory():
            # Create a config with issues
            with patch("claude_mpm.core.config.Config") as mock_config_class:
                mock_config = MagicMock()
                mock_config_class.return_value = mock_config

                # Configure mock to return config with issues
                mock_config.get.side_effect = lambda key, default=None: {
                    "response_logging": {
                        "enabled": True,
                        "directory": "/nonexistent/dir",
                    },
                    "memory_management": {
                        "auto_cleanup": True,
                        "cleanup_threshold_mb": 10,  # Very low
                    },
                }.get(key, default)

                # Run the configuration check
                command._check_configuration_health()

                # Check output
                captured = capsys.readouterr()
                assert (
                    "does not exist" in captured.out
                    or "threshold very low" in captured.out
                )
