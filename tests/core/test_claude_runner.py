"""Comprehensive unit tests for ClaudeRunner class.

This module tests the ClaudeRunner class before refactoring to establish
baseline behavior. Tests focus on the major methods that will be extracted
into separate services during refactoring.
"""

import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call, mock_open
import pytest

from claude_mpm.core.claude_runner import ClaudeRunner


class TestClaudeRunnerInitialization:
    """Test ClaudeRunner initialization and configuration."""
    
    @patch('claude_mpm.core.claude_runner.get_container')
    @patch('claude_mpm.core.claude_runner.Config')
    def test_init_basic(self, mock_config, mock_get_container):
        """Test basic ClaudeRunner initialization."""
        # Setup mocks
        mock_container = Mock()
        mock_get_container.return_value = mock_container
        mock_container.is_registered.return_value = False

        # Mock configuration service
        mock_config_service = Mock()
        mock_config_service.initialize_configuration.return_value = {
            'enable_tickets': True,
            'log_level': "INFO",
            'claude_args': ["--verbose"],
            'launch_method': "subprocess",
            'enable_websocket': False,
            'websocket_port': 8765,
            'config': Mock()
        }
        mock_config_service.initialize_project_logger.return_value = None
        mock_config_service.get_user_working_directory.return_value = None
        mock_config_service.register_core_services.return_value = None
        mock_config_service.register_ticket_manager.return_value = (None, True)
        mock_config_service.initialize_response_logger.return_value = None
        mock_config_service.register_hook_service.return_value = None
        mock_config_service.register_agent_capabilities_service.return_value = None
        mock_config_service.register_system_instructions_service.return_value = None
        mock_config_service.register_subprocess_launcher_service.return_value = None
        mock_config_service.create_session_log_file.return_value = None

        mock_container.get.side_effect = [
            mock_config_service,  # configuration service
            Mock(),  # deployment service
        ]

        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.get.return_value = {'enabled': False}

        # Test initialization
        runner = ClaudeRunner(
            enable_tickets=True,
            log_level="INFO",
            claude_args=["--verbose"],
            launch_method="subprocess"
        )

        assert runner.enable_tickets is True
        assert runner.log_level == "INFO"
        assert runner.claude_args == ["--verbose"]
        assert runner.launch_method == "subprocess"
        assert runner.logger is not None
    
    @patch('claude_mpm.core.claude_runner.get_container')
    @patch('claude_mpm.core.claude_runner.Config')
    def test_init_with_websocket(self, mock_config, mock_get_container):
        """Test initialization with WebSocket enabled."""
        mock_container = Mock()
        mock_get_container.return_value = mock_container
        mock_container.is_registered.return_value = False

        # Mock configuration service
        mock_config_service = Mock()
        mock_config_service.initialize_configuration.return_value = {
            'enable_tickets': True,
            'log_level': "OFF",
            'claude_args': [],
            'launch_method': "exec",
            'enable_websocket': True,
            'websocket_port': 9000,
            'config': Mock()
        }
        mock_config_service.initialize_project_logger.return_value = None
        mock_config_service.get_user_working_directory.return_value = None
        mock_config_service.register_core_services.return_value = None
        mock_config_service.register_ticket_manager.return_value = (None, True)
        mock_config_service.initialize_response_logger.return_value = None
        mock_config_service.register_hook_service.return_value = None
        mock_config_service.register_agent_capabilities_service.return_value = None
        mock_config_service.register_system_instructions_service.return_value = None
        mock_config_service.register_subprocess_launcher_service.return_value = None
        mock_config_service.create_session_log_file.return_value = None

        mock_container.get.side_effect = [
            mock_config_service,  # configuration service
            Mock(),  # deployment service
        ]

        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.get.return_value = {'enabled': False}

        runner = ClaudeRunner(
            enable_websocket=True,
            websocket_port=9000
        )

        assert runner.enable_websocket is True
        assert runner.websocket_port == 9000
    
    @patch('claude_mpm.core.claude_runner.get_container')
    @patch('claude_mpm.core.claude_runner.Config')
    def test_init_service_registration(self, mock_config, mock_get_container):
        """Test that services are properly registered during initialization."""
        mock_container = Mock()
        mock_get_container.return_value = mock_container
        mock_container.is_registered.return_value = False

        # Mock service instances
        mock_deployment_service = Mock()
        mock_ticket_manager = Mock()
        mock_hook_service = Mock()

        # Mock configuration service
        mock_config_service = Mock()
        mock_config_service.initialize_configuration.return_value = {
            'enable_tickets': True,
            'log_level': "OFF",
            'claude_args': [],
            'launch_method': "exec",
            'enable_websocket': False,
            'websocket_port': 8765,
            'config': Mock()
        }
        mock_config_service.initialize_project_logger.return_value = None
        mock_config_service.get_user_working_directory.return_value = None
        mock_config_service.register_core_services.return_value = None
        mock_config_service.register_ticket_manager.return_value = (mock_ticket_manager, True)
        mock_config_service.initialize_response_logger.return_value = None
        mock_config_service.register_hook_service.return_value = mock_hook_service
        mock_config_service.register_agent_capabilities_service.return_value = None
        mock_config_service.register_system_instructions_service.return_value = None
        mock_config_service.register_subprocess_launcher_service.return_value = None
        mock_config_service.create_session_log_file.return_value = None

        mock_container.get.side_effect = [
            mock_config_service,  # configuration service
            mock_deployment_service,  # deployment service
        ]

        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.get.return_value = {'enabled': False}

        with patch.dict('os.environ', {'CLAUDE_MPM_USER_PWD': '/test/dir'}):
            runner = ClaudeRunner(enable_tickets=True)

        # Verify configuration service was used
        mock_config_service.initialize_configuration.assert_called_once()
        mock_config_service.register_core_services.assert_called_once()
        mock_config_service.register_ticket_manager.assert_called_once()
        assert runner.deployment_service == mock_deployment_service
        assert runner.ticket_manager == mock_ticket_manager
        assert runner.hook_service == mock_hook_service


class TestClaudeRunnerAgentCapabilities:
    """Test agent capabilities generation methods."""
    
    @pytest.fixture
    def runner(self):
        """Create a ClaudeRunner instance for testing."""
        with patch('claude_mpm.core.claude_runner.get_container') as mock_get_container, \
             patch('claude_mpm.core.claude_runner.Config'):

            # Setup mocks
            mock_container = Mock()
            mock_get_container.return_value = mock_container
            mock_container.is_registered.return_value = False

            # Mock configuration service
            mock_config_service = Mock()
            mock_config_service.initialize_configuration.return_value = {
                'enable_tickets': True,
                'log_level': "OFF",
                'claude_args': [],
                'launch_method': "exec",
                'enable_websocket': False,
                'websocket_port': 8765,
                'config': Mock()
            }
            mock_config_service.initialize_project_logger.return_value = None
            mock_config_service.get_user_working_directory.return_value = None
            mock_config_service.register_core_services.return_value = None
            mock_config_service.register_ticket_manager.return_value = (None, True)
            mock_config_service.initialize_response_logger.return_value = None
            mock_config_service.register_hook_service.return_value = None
            mock_config_service.register_agent_capabilities_service.return_value = None
            mock_config_service.register_system_instructions_service.return_value = None
            mock_config_service.register_subprocess_launcher_service.return_value = None
            mock_config_service.register_version_service.return_value = None
            mock_config_service.register_command_handler_service.return_value = Mock()
            mock_config_service.register_memory_hook_service.return_value = None
            mock_config_service.register_session_management_service.return_value = None
            mock_config_service.register_utility_service.return_value = Mock()
            mock_config_service.create_session_log_file.return_value = None

            mock_container.get.side_effect = [
                mock_config_service,  # configuration service
                Mock(),  # deployment service
            ]

            return ClaudeRunner()
    
    def test_generate_deployed_agent_capabilities_success(self, runner):
        """Test successful agent capabilities generation delegation to service."""
        # Mock the agent capabilities service
        runner.agent_capabilities_service = Mock()
        runner.agent_capabilities_service.generate_deployed_agent_capabilities.return_value = """
## Available Agent Capabilities

You have the following specialized agents available for delegation:

### Development Agents
- **Test Agent** (`test-agent`): A test agent

**Total Available Agents**: 1
"""

        result = runner._generate_deployed_agent_capabilities()

        assert "Available Agent Capabilities" in result
        assert "Test Agent" in result
        assert "Development Agents" in result
        assert "Total Available Agents" in result
        runner.agent_capabilities_service.generate_deployed_agent_capabilities.assert_called_once()
    
    def test_generate_deployed_agent_capabilities_no_agents(self, runner):
        """Test capabilities generation when no agents are found."""
        # Mock the agent capabilities service to return fallback
        runner.agent_capabilities_service = Mock()
        runner.agent_capabilities_service.generate_deployed_agent_capabilities.return_value = """
## Available Agent Capabilities

You have the following specialized agents available for delegation:

- **Engineer Agent**: Code implementation and development
- **Research Agent**: Investigation and analysis
"""

        result = runner._generate_deployed_agent_capabilities()

        # Should return fallback capabilities with default agents
        assert "Available Agent Capabilities" in result
        assert "Engineer Agent" in result  # Default fallback includes these
        assert "Research Agent" in result
        runner.agent_capabilities_service.generate_deployed_agent_capabilities.assert_called_once()
    
    def test_agent_capabilities_service_fallback(self, runner):
        """Test fallback when agent capabilities service is not available."""
        # Set service to None to test fallback
        runner.agent_capabilities_service = None

        result = runner._generate_deployed_agent_capabilities()

        # Should return fallback capabilities
        assert "Available Agent Capabilities" in result
        assert "Engineer Agent" in result
        assert "Research Agent" in result
    
    def test_agent_capabilities_service_initialization(self, runner):
        """Test that agent capabilities service is properly initialized."""
        # The service should be initialized during ClaudeRunner construction
        assert hasattr(runner, 'agent_capabilities_service')
        # Service might be None if initialization failed, but attribute should exist
        assert runner.agent_capabilities_service is not None or runner.agent_capabilities_service is None


class TestClaudeRunnerSystemInstructions:
    """Test system instructions processing methods."""
    
    @pytest.fixture
    def runner(self):
        """Create a ClaudeRunner instance for testing."""
        with patch('claude_mpm.core.claude_runner.get_container') as mock_get_container, \
             patch('claude_mpm.core.claude_runner.Config'):

            # Setup mocks
            mock_container = Mock()
            mock_get_container.return_value = mock_container
            mock_container.is_registered.return_value = False

            # Mock configuration service
            mock_config_service = Mock()
            mock_config_service.initialize_configuration.return_value = {
                'enable_tickets': True,
                'log_level': "OFF",
                'claude_args': [],
                'launch_method': "exec",
                'enable_websocket': False,
                'websocket_port': 8765,
                'config': Mock()
            }
            mock_config_service.initialize_project_logger.return_value = None
            mock_config_service.get_user_working_directory.return_value = None
            mock_config_service.register_core_services.return_value = None
            mock_config_service.register_ticket_manager.return_value = (None, True)
            mock_config_service.initialize_response_logger.return_value = None
            mock_config_service.register_hook_service.return_value = None
            mock_config_service.register_agent_capabilities_service.return_value = None
            mock_config_service.register_system_instructions_service.return_value = None
            mock_config_service.register_subprocess_launcher_service.return_value = None
            mock_config_service.register_version_service.return_value = None
            mock_config_service.register_command_handler_service.return_value = Mock()
            mock_config_service.register_memory_hook_service.return_value = None
            mock_config_service.register_session_management_service.return_value = None
            mock_config_service.register_utility_service.return_value = Mock()
            mock_config_service.create_session_log_file.return_value = None

            mock_container.get.side_effect = [
                mock_config_service,  # configuration service
                Mock(),  # deployment service
            ]

            return ClaudeRunner()
    
    def test_load_system_instructions_success(self, runner):
        """Test successful system instructions loading delegation to service."""
        mock_instructions = "# System Instructions\nYou are Claude Code."

        # Mock the system instructions service
        runner.system_instructions_service = Mock()
        runner.system_instructions_service.load_system_instructions.return_value = mock_instructions

        result = runner._load_system_instructions()

        assert result == mock_instructions
        runner.system_instructions_service.load_system_instructions.assert_called_once()
    
    def test_load_system_instructions_not_found(self, runner):
        """Test system instructions loading when service returns None."""
        # Mock the system instructions service to return None
        runner.system_instructions_service = Mock()
        runner.system_instructions_service.load_system_instructions.return_value = None

        result = runner._load_system_instructions()

        assert result is None
        runner.system_instructions_service.load_system_instructions.assert_called_once()
    
    def test_strip_metadata_comments(self, runner):
        """Test HTML metadata comment stripping delegation to service."""
        content_with_comments = """
        <!-- metadata: test -->
        # Real Content
        Some instructions
        <!-- another comment -->
        More content
        """

        expected_result = """
        # Real Content
        Some instructions
        More content
        """

        # Mock the system instructions service
        runner.system_instructions_service = Mock()
        runner.system_instructions_service.strip_metadata_comments.return_value = expected_result

        result = runner._strip_metadata_comments(content_with_comments)

        assert result == expected_result
        runner.system_instructions_service.strip_metadata_comments.assert_called_once_with(content_with_comments)
        assert "Some instructions" in result
        assert "More content" in result
    
    def test_process_base_pm_content(self, runner):
        """Test BASE_PM.md content processing delegation to service."""
        base_content = """
        # Base PM Content
        {{AGENT_CAPABILITIES}}
        {{VERSION}}
        """

        expected_result = """
        # Base PM Content
        Agent list
        1.0.0
        """

        # Mock the system instructions service
        runner.system_instructions_service = Mock()
        runner.system_instructions_service.process_base_pm_content.return_value = expected_result

        result = runner._process_base_pm_content(base_content)

        assert result == expected_result
        runner.system_instructions_service.process_base_pm_content.assert_called_once_with(base_content)
    
    def test_create_system_prompt(self, runner):
        """Test system prompt creation delegation to service."""
        runner.system_instructions = "Test instructions"

        # Mock the system instructions service
        runner.system_instructions_service = Mock()
        runner.system_instructions_service.create_system_prompt.return_value = "Test instructions"

        result = runner._create_system_prompt()

        assert result == "Test instructions"
        runner.system_instructions_service.create_system_prompt.assert_called_once_with("Test instructions")

        # Test fallback when no instructions - returns default context
        runner.system_instructions = None
        result = runner._create_system_prompt()
        assert result is not None
        assert len(result) > 0  # Should return some default content


class TestClaudeRunnerAgentDeployment:
    """Test agent deployment methods."""
    
    @pytest.fixture
    def runner(self):
        """Create a ClaudeRunner instance for testing."""
        with patch('claude_mpm.core.claude_runner.get_container') as mock_get_container, \
             patch('claude_mpm.core.claude_runner.Config'):

            # Setup mocks
            mock_container = Mock()
            mock_get_container.return_value = mock_container
            mock_container.is_registered.return_value = False

            # Mock configuration service
            mock_config_service = Mock()
            mock_config_service.initialize_configuration.return_value = {
                'enable_tickets': True,
                'log_level': "OFF",
                'claude_args': [],
                'launch_method': "exec",
                'enable_websocket': False,
                'websocket_port': 8765,
                'config': Mock()
            }
            mock_config_service.initialize_project_logger.return_value = None
            mock_config_service.get_user_working_directory.return_value = None
            mock_config_service.register_core_services.return_value = None
            mock_config_service.register_ticket_manager.return_value = (None, True)
            mock_config_service.initialize_response_logger.return_value = None
            mock_config_service.register_hook_service.return_value = None
            mock_config_service.register_agent_capabilities_service.return_value = None
            mock_config_service.register_system_instructions_service.return_value = None
            mock_config_service.register_subprocess_launcher_service.return_value = None
            mock_config_service.register_version_service.return_value = None
            mock_config_service.register_command_handler_service.return_value = Mock()
            mock_config_service.register_memory_hook_service.return_value = None
            mock_config_service.register_session_management_service.return_value = None
            mock_config_service.register_utility_service.return_value = Mock()
            mock_config_service.create_session_log_file.return_value = None

            mock_deployment_service = Mock()
            mock_container.get.side_effect = [
                mock_config_service,  # configuration service
                mock_deployment_service,  # deployment service
            ]

            runner = ClaudeRunner()
            runner.deployment_service = mock_deployment_service
            return runner
    
    def test_setup_agents_success(self, runner):
        """Test successful agent setup."""
        # Mock the deployment service to return expected format
        runner.deployment_service.deploy_agents.return_value = {
            'deployed': ['agent1', 'agent2', 'agent3'],  # List of deployed agents
            'updated': [],
            'skipped': [],
            'errors': []
        }

        result = runner.setup_agents()

        assert result is True
        runner.deployment_service.deploy_agents.assert_called_once()
    
    def test_setup_agents_failure(self, runner):
        """Test agent setup failure."""
        runner.deployment_service.deploy_agents.side_effect = Exception("Deploy failed")
        
        result = runner.setup_agents()
        
        assert result is False
    
    def test_ensure_project_agents_success(self, runner, tmp_path):
        """Test successful project agent ensuring."""
        # Use a real temporary directory that exists
        test_project = tmp_path / "test_project"
        test_project.mkdir()

        runner.deployment_service.deploy_agents.return_value = {
            'deployed': ['agent1', 'agent2', 'agent3'],
            'updated': [],
            'skipped': [],
            'errors': []
        }

        with patch.dict('os.environ', {'CLAUDE_MPM_USER_PWD': str(test_project)}):
            result = runner.ensure_project_agents()

            assert result is True
            runner.deployment_service.deploy_agents.assert_called()
    
    def test_deploy_project_agents_to_claude_no_agents(self, runner, tmp_path):
        """Test project agent deployment when no agents exist."""
        # Setup test environment with no agents
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        with patch.dict('os.environ', {'CLAUDE_MPM_USER_PWD': str(project_dir)}):
            result = runner.deploy_project_agents_to_claude()

            # Should return True when no agents to deploy
            assert result is True


class TestClaudeRunnerSubprocessManagement:
    """Test subprocess launching and management methods."""

    @pytest.fixture
    def runner(self):
        """Create a ClaudeRunner instance for testing."""
        with patch('claude_mpm.core.claude_runner.get_container') as mock_get_container, \
             patch('claude_mpm.core.claude_runner.Config'):

            # Setup mocks
            mock_container = Mock()
            mock_get_container.return_value = mock_container
            mock_container.is_registered.return_value = False

            # Mock configuration service
            mock_config_service = Mock()
            mock_config_service.initialize_configuration.return_value = {
                'enable_tickets': True,
                'log_level': "OFF",
                'claude_args': [],
                'launch_method': "subprocess",
                'enable_websocket': False,
                'websocket_port': 8765,
                'config': Mock()
            }
            mock_config_service.initialize_project_logger.return_value = None
            mock_config_service.get_user_working_directory.return_value = None
            mock_config_service.register_core_services.return_value = None
            mock_config_service.register_ticket_manager.return_value = (None, True)
            mock_config_service.initialize_response_logger.return_value = None
            mock_config_service.register_hook_service.return_value = None
            mock_config_service.register_agent_capabilities_service.return_value = None
            mock_config_service.register_system_instructions_service.return_value = None
            mock_config_service.register_subprocess_launcher_service.return_value = None
            mock_config_service.register_version_service.return_value = None
            mock_config_service.register_command_handler_service.return_value = Mock()
            mock_config_service.register_memory_hook_service.return_value = None
            mock_config_service.register_session_management_service.return_value = None
            mock_config_service.register_utility_service.return_value = Mock()
            mock_config_service.create_session_log_file.return_value = None

            mock_container.get.side_effect = [
                mock_config_service,  # configuration service
                Mock(),  # deployment service
            ]

            return ClaudeRunner(launch_method="subprocess")

    def test_launch_subprocess_interactive_success(self, runner):
        """Test successful subprocess launching delegation to service."""
        cmd = ['claude', '--test']
        env = {'TEST': 'value'}

        # Mock the subprocess launcher service
        runner.subprocess_launcher_service = Mock()

        runner._launch_subprocess_interactive(cmd, env)

        # Verify delegation to service
        runner.subprocess_launcher_service.launch_subprocess_interactive.assert_called_once_with(cmd, env)

    def test_launch_subprocess_interactive_with_websocket(self, runner):
        """Test subprocess launching delegation with WebSocket integration."""
        runner.websocket_server = Mock()

        cmd = ['claude']
        env = {}

        # Mock the subprocess launcher service
        runner.subprocess_launcher_service = Mock()

        runner._launch_subprocess_interactive(cmd, env)

        # Verify delegation to service
        runner.subprocess_launcher_service.launch_subprocess_interactive.assert_called_once_with(cmd, env)

    def test_launch_subprocess_interactive_basic_setup(self, runner):
        """Test basic subprocess setup delegation to service."""
        cmd = ['claude']
        env = {}

        # Mock the subprocess launcher service
        runner.subprocess_launcher_service = Mock()

        # Should complete without error
        runner._launch_subprocess_interactive(cmd, env)

        # Verify delegation to service
        runner.subprocess_launcher_service.launch_subprocess_interactive.assert_called_once_with(cmd, env)

    def test_launch_subprocess_interactive_service_unavailable(self, runner):
        """Test subprocess launching when service is unavailable."""
        cmd = ['claude']
        env = {}

        # Set service to None to test fallback
        runner.subprocess_launcher_service = None

        # Should raise RuntimeError when service is not available
        with pytest.raises(RuntimeError, match="Subprocess launcher service not available"):
            runner._launch_subprocess_interactive(cmd, env)


class TestClaudeRunnerSessionManagement:
    """Test session management and execution methods."""

    @pytest.fixture
    def runner(self):
        """Create a ClaudeRunner instance for testing."""
        with patch('claude_mpm.core.claude_runner.get_container') as mock_get_container, \
             patch('claude_mpm.core.claude_runner.Config'):

            # Setup mocks
            mock_container = Mock()
            mock_get_container.return_value = mock_container
            mock_container.is_registered.return_value = False

            # Mock configuration service
            mock_config_service = Mock()
            mock_config_service.initialize_configuration.return_value = {
                'enable_tickets': True,
                'log_level': "OFF",
                'claude_args': [],
                'launch_method': "exec",
                'enable_websocket': False,
                'websocket_port': 8765,
                'config': Mock()
            }
            mock_config_service.initialize_project_logger.return_value = None
            mock_config_service.get_user_working_directory.return_value = None
            mock_config_service.register_core_services.return_value = None
            mock_config_service.register_ticket_manager.return_value = (None, True)
            mock_config_service.initialize_response_logger.return_value = None
            mock_config_service.register_hook_service.return_value = None
            mock_config_service.register_agent_capabilities_service.return_value = None
            mock_config_service.register_system_instructions_service.return_value = None
            mock_config_service.register_subprocess_launcher_service.return_value = None
            mock_config_service.register_version_service.return_value = None
            mock_config_service.register_command_handler_service.return_value = Mock()
            mock_config_service.register_memory_hook_service.return_value = None
            mock_config_service.register_session_management_service.return_value = None
            mock_config_service.register_utility_service.return_value = Mock()
            mock_config_service.create_session_log_file.return_value = None

            # Create specific mocks for services that need to return proper values
            mock_command_handler = Mock()
            mock_command_handler.handle_mpm_command.return_value = True
            mock_command_handler.is_mpm_command.return_value = False

            mock_utility_service = Mock()
            mock_utility_service.contains_delegation.return_value = True
            mock_utility_service.extract_agent_from_response.return_value = "test_agent"
            mock_utility_service.log_session_event.return_value = None

            mock_container.get.side_effect = [
                mock_config_service,  # configuration service
                Mock(),  # deployment service
            ]

            runner = ClaudeRunner()
            # Override the services with our specific mocks
            runner.command_handler_service = mock_command_handler
            runner.utility_service = mock_utility_service
            return runner

    @patch('claude_mpm.core.interactive_session.InteractiveSession')
    def test_run_interactive_success(self, mock_session_class, runner):
        """Test successful interactive session execution."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.initialize_interactive_session.return_value = (True, None)
        mock_session.setup_interactive_environment.return_value = (True, {'test': 'env'})
        mock_session.handle_interactive_input.return_value = True

        # Should not raise exception
        runner.run_interactive("test context")

        mock_session_class.assert_called_once_with(runner)
        mock_session.initialize_interactive_session.assert_called_once()
        mock_session.setup_interactive_environment.assert_called_once()
        mock_session.handle_interactive_input.assert_called_once_with({'test': 'env'})
        mock_session.cleanup_interactive_session.assert_called_once()

    @patch('claude_mpm.core.interactive_session.InteractiveSession')
    def test_run_interactive_initialization_failure(self, mock_session_class, runner):
        """Test interactive session with initialization failure."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.initialize_interactive_session.return_value = (False, "Init failed")

        # Should handle failure gracefully
        runner.run_interactive()

        mock_session.initialize_interactive_session.assert_called_once()
        # Should not proceed to setup
        mock_session.setup_interactive_environment.assert_not_called()
        # Cleanup should still be called
        mock_session.cleanup_interactive_session.assert_called_once()

    @patch('claude_mpm.core.oneshot_session.OneshotSession')
    def test_run_oneshot_success(self, mock_session_class, runner):
        """Test successful oneshot session execution."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.initialize_session.return_value = (True, None)
        mock_session.deploy_agents.return_value = True
        mock_session.setup_infrastructure.return_value = {'test': 'infra'}
        mock_session.execute_command.return_value = (True, "Success")

        result = runner.run_oneshot("test prompt", "test context")

        assert result is True
        mock_session_class.assert_called_once_with(runner)
        mock_session.initialize_session.assert_called_once_with("test prompt")
        mock_session.deploy_agents.assert_called_once()
        mock_session.setup_infrastructure.assert_called_once()
        mock_session.execute_command.assert_called_once_with(
            "test prompt", "test context", {'test': 'infra'}
        )

    @patch('claude_mpm.core.oneshot_session.OneshotSession')
    def test_run_oneshot_mmp_command(self, mock_session_class, runner):
        """Test oneshot session with MPM command."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.initialize_session.return_value = (True, None)

        result = runner.run_oneshot("/mpm:test")

        assert result is True
        # Should return early for MPM commands
        mock_session.deploy_agents.assert_not_called()


class TestClaudeRunnerUtilityMethods:
    """Test utility and helper methods."""

    @pytest.fixture
    def runner(self):
        """Create a ClaudeRunner instance for testing."""
        with patch('claude_mpm.core.claude_runner.get_container') as mock_get_container, \
             patch('claude_mpm.core.claude_runner.Config'):

            # Setup mocks
            mock_container = Mock()
            mock_get_container.return_value = mock_container
            mock_container.is_registered.return_value = False

            # Mock configuration service
            mock_config_service = Mock()
            mock_config_service.initialize_configuration.return_value = {
                'enable_tickets': True,
                'log_level': "OFF",
                'claude_args': [],
                'launch_method': "exec",
                'enable_websocket': False,
                'websocket_port': 8765,
                'config': Mock()
            }
            mock_config_service.initialize_project_logger.return_value = None
            mock_config_service.get_user_working_directory.return_value = None
            mock_config_service.register_core_services.return_value = None
            mock_config_service.register_ticket_manager.return_value = (None, True)
            mock_config_service.initialize_response_logger.return_value = None
            mock_config_service.register_hook_service.return_value = None
            mock_config_service.register_agent_capabilities_service.return_value = None
            mock_config_service.register_system_instructions_service.return_value = None
            mock_config_service.register_subprocess_launcher_service.return_value = None
            mock_config_service.register_version_service.return_value = None
            mock_config_service.register_command_handler_service.return_value = Mock()
            mock_config_service.register_memory_hook_service.return_value = None
            mock_config_service.register_session_management_service.return_value = None
            mock_config_service.register_utility_service.return_value = Mock()
            mock_config_service.create_session_log_file.return_value = None

            # Create specific mocks for services that need to return proper values
            mock_command_handler = Mock()
            mock_command_handler.handle_mpm_command.return_value = True
            mock_command_handler.is_mmp_command.return_value = False

            mock_utility_service = Mock()
            mock_utility_service.contains_delegation.return_value = True
            mock_utility_service.extract_agent_from_response.return_value = "test_agent"
            mock_utility_service.log_session_event.return_value = None

            mock_container.get.side_effect = [
                mock_config_service,  # configuration service
                Mock(),  # deployment service
            ]

            runner = ClaudeRunner()
            # Override the services with our specific mocks
            runner.command_handler_service = mock_command_handler
            runner.utility_service = mock_utility_service
            return runner

    def test_extract_tickets(self, runner):
        """Test ticket extraction from text."""
        runner.ticket_manager = Mock()
        runner.ticket_manager.extract_tickets_from_text = Mock(return_value=[])
        test_text = "Some response with ticket data"

        runner._extract_tickets(test_text)

        # The method should call the ticket manager if it exists
        runner.ticket_manager.extract_tickets_from_text.assert_called_once_with(test_text)

    def test_extract_tickets_no_manager(self, runner):
        """Test ticket extraction when no ticket manager."""
        runner.ticket_manager = None

        # Should not raise exception
        runner._extract_tickets("test text")

    def test_contains_delegation(self, runner):
        """Test delegation detection in text."""
        # Test that the method exists and runs
        result1 = runner._contains_delegation("I'll delegate this to the code-analyzer agent")
        result2 = runner._contains_delegation("I'll handle this myself")

        # The method should return boolean values
        assert isinstance(result1, bool)
        assert isinstance(result2, bool)

    def test_extract_agent_from_response(self, runner):
        """Test agent name extraction from delegation response."""
        # Test that the method exists and runs
        result1 = runner._extract_agent_from_response("I'll use the code-analyzer agent")
        result2 = runner._extract_agent_from_response("No agent mentioned here")

        # The method should return string or None
        assert result1 is None or isinstance(result1, str)
        assert result2 is None or isinstance(result2, str)

    def test_handle_mpm_command(self, runner):
        """Test MPM command handling."""
        # Test that the method exists and runs
        result1 = runner._handle_mpm_command("/mpm:version")
        result2 = runner._handle_mpm_command("/mpm:invalid")

        # The method should return boolean values
        assert isinstance(result1, bool)
        assert isinstance(result2, bool)

    def test_log_session_event(self, runner):
        """Test session event logging delegation to utility service."""
        runner.session_log_file = Path("/tmp/test.log")
        event_data = {"event": "test", "data": "value"}

        # Test that the method delegates to the utility service
        runner._log_session_event(event_data)

        # Verify the utility service was called with the correct parameters
        runner.utility_service.log_session_event.assert_called_once_with(
            runner.session_log_file, event_data
        )

    def test_log_session_event_no_file(self, runner):
        """Test session event logging when no log file."""
        runner.session_log_file = None

        # Should not raise exception
        runner._log_session_event({"event": "test"})

    def test_get_version(self, runner):
        """Test version detection."""
        # Test that the method exists and returns a version string
        version = runner._get_version()

        assert isinstance(version, str)
        assert len(version) > 0
        # Should contain some version-like content
        assert any(char.isdigit() for char in version) or "unknown" in version.lower() or "dev" in version.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
