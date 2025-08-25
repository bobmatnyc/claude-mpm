"""Tests for RunnerConfigurationService.

Tests the extracted runner configuration service to ensure it maintains
the same behavior as the original ClaudeRunner initialization methods.
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.services.runner_configuration_service import RunnerConfigurationService


class TestRunnerConfigurationService:
    """Test the RunnerConfigurationService class."""

    @pytest.fixture
    def service(self):
        """Create a RunnerConfigurationService instance for testing."""
        return RunnerConfigurationService()

    @pytest.fixture
    def mock_container(self):
        """Create a mock DI container."""
        container = Mock()
        container.is_registered.return_value = False
        container.register_factory = Mock()
        container.register_singleton = Mock()
        container.get = Mock()
        return container

    def test_initialize_configuration_basic(service):
        """Test basic configuration initialization."""
        with patch(
            "claude_mpm.services.runner_configuration_service.Config"
        ) as mock_config:
            mock_config.return_value = Mock()

            result = service.initialize_configuration(
                enable_tickets=True,
                log_level="INFO",
                claude_args=["--verbose"],
                launch_method="subprocess",
            )

            assert result["enable_tickets"] is True
            assert result["log_level"] == "INFO"
            assert result["claude_args"] == ["--verbose"]
            assert result["launch_method"] == "subprocess"
            assert result["enable_websocket"] is False  # default
            assert result["websocket_port"] == 8765  # default
            assert "config" in result

    def test_initialize_configuration_with_defaults(service):
        """Test configuration initialization with default values."""
        with patch(
            "claude_mpm.services.runner_configuration_service.Config"
        ) as mock_config:
            mock_config.return_value = Mock()

            result = service.initialize_configuration()

            assert result["enable_tickets"] is True
            assert result["log_level"] == "OFF"
            assert result["claude_args"] == []
            assert result["launch_method"] == "exec"
            assert result["enable_websocket"] is False
            assert result["websocket_port"] == 8765

    def test_initialize_configuration_config_not_found(service):
        """Test configuration initialization when config file not found."""
        with patch(
            "claude_mpm.services.runner_configuration_service.Config"
        ) as mock_config:
            mock_config.side_effect = [FileNotFoundError("Config not found"), Mock()]

            result = service.initialize_configuration()

            # Should handle FileNotFoundError and create default config
            assert "config" in result
            assert mock_config.call_count == 2  # First call fails, second succeeds

    def test_initialize_configuration_config_error(service):
        """Test configuration initialization with config error."""
        with patch(
            "claude_mpm.services.runner_configuration_service.Config"
        ) as mock_config:
            mock_config.side_effect = Exception("Config error")

            with pytest.raises(
                RuntimeError, match="Configuration initialization failed"
            ):
                service.initialize_configuration()

    def test_initialize_project_logger_off(service):
        """Test project logger initialization when disabled."""
        result = service.initialize_project_logger("OFF")

        assert result is None

    def test_initialize_project_logger_success(service):
        """Test successful project logger initialization."""
        mock_logger = Mock()

        with patch(
            "claude_mpm.services.runner_configuration_service.get_project_logger"
        ) as mock_get_logger:
            mock_get_logger.return_value = mock_logger

            result = service.initialize_project_logger("INFO")

            assert result == mock_logger
            mock_get_logger.assert_called_once_with("INFO")
            mock_logger.log_system.assert_called_once()

    def test_initialize_project_logger_import_error(service):
        """Test project logger initialization with import error."""
        with patch(
            "claude_mpm.services.runner_configuration_service.get_project_logger"
        ) as mock_get_logger:
            mock_get_logger.side_effect = ImportError("Module not found")

            result = service.initialize_project_logger("INFO")

            assert result is None

    def test_initialize_project_logger_general_error(service):
        """Test project logger initialization with general error."""
        with patch(
            "claude_mpm.services.runner_configuration_service.get_project_logger"
        ) as mock_get_logger:
            mock_get_logger.side_effect = Exception("General error")

            result = service.initialize_project_logger("INFO")

            assert result is None

    def test_initialize_response_logger_disabled(service):
        """Test response logger initialization when disabled."""
        mock_config = Mock()
        mock_config.get.return_value = {"enabled": False}

        result = service.initialize_response_logger(mock_config)

        assert result is None

    def test_initialize_response_logger_success(service):
        """Test successful response logger initialization."""
        mock_config = Mock()
        mock_config.get.return_value = {"enabled": True}
        mock_logger = Mock()
        mock_project_logger = Mock()

        with patch(
            "claude_mpm.services.claude_session_logger.get_session_logger"
        ) as mock_get_logger:
            mock_get_logger.return_value = mock_logger

            result = service.initialize_response_logger(
                mock_config, mock_project_logger
            )

            assert result == mock_logger
            mock_get_logger.assert_called_once_with(mock_config)
            mock_project_logger.log_system.assert_called_once()

    def test_initialize_response_logger_error(service):
        """Test response logger initialization with error."""
        mock_config = Mock()
        mock_config.get.return_value = {"enabled": True}

        with patch(
            "claude_mpm.services.claude_session_logger.get_session_logger"
        ) as mock_get_logger:
            mock_get_logger.side_effect = Exception("Logger error")

            result = service.initialize_response_logger(mock_config)

            assert result is None

    def test_get_user_working_directory_set(service):
        """Test getting user working directory when environment variable is set."""
        test_path = "/test/path"

        with patch.dict(os.environ, {"CLAUDE_MPM_USER_PWD": test_path}):
            result = service.get_user_working_directory()

            assert result == Path(test_path)

    def test_get_user_working_directory_not_set(service):
        """Test getting user working directory when environment variable is not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = service.get_user_working_directory()

            assert result is None

    def test_register_core_services(service, mock_container):
        """Test core services registration."""
        user_working_dir = Path("/test/dir")

        service.register_core_services(mock_container, user_working_dir)

        # Should register deployment service
        mock_container.register_factory.assert_called_once()

    def test_register_ticket_manager_disabled(service, mock_container):
        """Test ticket manager registration when disabled."""
        ticket_manager, enable_tickets = service.register_ticket_manager(
            mock_container, False
        )

        assert ticket_manager is None
        assert enable_tickets is False
        mock_container.register_singleton.assert_not_called()

    def test_register_ticket_manager_success(service, mock_container):
        """Test successful ticket manager registration."""
        mock_ticket_manager = Mock()
        mock_container.get.return_value = mock_ticket_manager

        ticket_manager, enable_tickets = service.register_ticket_manager(
            mock_container, True
        )

        assert ticket_manager == mock_ticket_manager
        assert enable_tickets is True
        mock_container.register_singleton.assert_called_once()
        mock_container.get.assert_called_once()

    def test_register_ticket_manager_error(service, mock_container):
        """Test ticket manager registration with error."""
        mock_container.get.side_effect = Exception("Registration error")

        ticket_manager, enable_tickets = service.register_ticket_manager(
            mock_container, True
        )

        assert ticket_manager is None
        assert enable_tickets is False

    def test_register_hook_service_success(service, mock_container):
        """Test successful hook service registration."""
        mock_config = Mock()
        mock_hook_service = Mock()
        mock_container.get.return_value = mock_hook_service

        result = service.register_hook_service(mock_container, mock_config)

        assert result == mock_hook_service
        mock_container.register_factory.assert_called_once()
        mock_container.get.assert_called_once()

    def test_register_hook_service_error(service, mock_container):
        """Test hook service registration with error."""
        mock_config = Mock()
        mock_container.get.side_effect = Exception("Registration error")

        result = service.register_hook_service(mock_container, mock_config)

        assert result is None

    def test_register_agent_capabilities_service_success(service, mock_container):
        """Test successful agent capabilities service registration."""
        mock_service = Mock()
        mock_container.get.return_value = mock_service

        result = service.register_agent_capabilities_service(mock_container)

        assert result == mock_service
        mock_container.register_singleton.assert_called_once()
        mock_container.get.assert_called_once()

    def test_register_system_instructions_service_success(
        self, service, mock_container
    ):
        """Test successful system instructions service registration."""
        mock_agent_service = Mock()
        mock_system_service = Mock()
        mock_container.get.return_value = mock_system_service

        result = service.register_system_instructions_service(
            mock_container, mock_agent_service
        )

        assert result == mock_system_service
        mock_container.register_factory.assert_called_once()
        mock_container.get.assert_called_once()

    def test_register_subprocess_launcher_service_success(
        self, service, mock_container
    ):
        """Test successful subprocess launcher service registration."""
        mock_project_logger = Mock()
        mock_websocket_server = Mock()
        mock_launcher_service = Mock()
        mock_container.get.return_value = mock_launcher_service

        result = service.register_subprocess_launcher_service(
            mock_container, mock_project_logger, mock_websocket_server
        )

        assert result == mock_launcher_service
        mock_container.register_factory.assert_called_once()
        mock_container.get.assert_called_once()

    def test_create_session_log_file_disabled(service):
        """Test session log file creation when disabled."""
        result = service.create_session_log_file(None, "OFF", {})

        assert result is None

    def test_create_session_log_file_success(service, tmp_path):
        """Test successful session log file creation."""
        mock_project_logger = Mock()
        mock_project_logger.session_dir = tmp_path

        config_data = {"enable_tickets": True, "launch_method": "exec"}

        result = service.create_session_log_file(
            mock_project_logger, "INFO", config_data
        )

        assert result == tmp_path / "system.jsonl"

    def test_create_session_log_file_permission_error(service):
        """Test session log file creation with permission error."""
        mock_project_logger = Mock()
        mock_project_logger.session_dir = Path("/nonexistent/path")

        config_data = {}

        # The current implementation doesn't actually check for permission errors
        # It just returns the path. This test verifies the current behavior.
        result = service.create_session_log_file(
            mock_project_logger, "INFO", config_data
        )

        # Current implementation returns the path regardless of permissions
        assert result == Path("/nonexistent/path/system.jsonl")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
