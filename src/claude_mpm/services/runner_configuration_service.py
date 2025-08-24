from pathlib import Path

"""Runner configuration service for initializing and configuring ClaudeRunner.

This service handles:
1. Service registration and dependency injection setup
2. Configuration loading and validation
3. Logger initialization (project and response loggers)
4. Session management setup
5. Hook service registration

Extracted from ClaudeRunner to follow Single Responsibility Principle.
"""

import os
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.core.base_service import BaseService
from claude_mpm.core.config import Config
from claude_mpm.core.container import ServiceLifetime
from claude_mpm.core.logger import get_project_logger
from claude_mpm.core.shared.config_loader import ConfigLoader
from claude_mpm.services.core.interfaces import RunnerConfigurationInterface


class RunnerConfigurationService(BaseService, RunnerConfigurationInterface):
    """Service for configuring and initializing ClaudeRunner components."""

    def __init__(self):
        """Initialize the runner configuration service."""
        super().__init__(name="runner_configuration_service")

    async def _initialize(self) -> None:
        """Initialize the service. No special initialization needed."""

    async def _cleanup(self) -> None:
        """Cleanup service resources. No cleanup needed."""

    # Implementation of abstract methods from RunnerConfigurationInterface

    def initialize_runner(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize runner with configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Dictionary with initialization results
        """
        # This method can delegate to the existing initialize_configuration method
        return self.initialize_configuration(**config)

    def register_services(self, service_container) -> None:
        """Register services with the dependency injection container.

        Args:
            service_container: Service container for registration
        """
        # This method can delegate to existing service registration methods
        # For now, this is a no-op as service registration is handled elsewhere

    def load_configuration(self, config_path: Optional[Path] = None) -> Dict[str, Any]:
        """Load configuration from file or defaults.

        Args:
            config_path: Optional path to configuration file

        Returns:
            Loaded configuration dictionary
        """
        try:
            # Use singleton Config instance to prevent duplicate loading
            config_loader = ConfigLoader()
            if config_path:
                # Use specific config file with ConfigLoader
                from claude_mpm.core.shared.config_loader import ConfigPattern

                pattern = ConfigPattern(
                    filenames=[Path(config_path).name],
                    search_paths=[str(Path(config_path).parent)],
                    env_prefix="CLAUDE_MPM_",
                )
                config = config_loader.load_config(
                    pattern, cache_key=f"runner_{config_path}"
                )
            else:
                # Use main config
                config = config_loader.load_main_config()

            return {
                "config": config,
                "enable_tickets": True,
                "log_level": "OFF",
                "claude_args": [],
                "launch_method": "exec",
                "enable_websocket": False,
                "websocket_port": 8765,
            }
        except Exception as e:
            self.logger.error("Failed to load configuration", exc_info=True)
            raise RuntimeError(f"Configuration loading failed: {e}") from e

    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate configuration structure and values.

        Args:
            config: Configuration to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Validate required keys
        required_keys = ["enable_tickets", "log_level", "claude_args", "launch_method"]
        for key in required_keys:
            if key not in config:
                errors.append(f"Missing required configuration key: {key}")

        # Validate specific values
        if "launch_method" in config and config["launch_method"] not in [
            "exec",
            "subprocess",
        ]:
            errors.append("launch_method must be 'exec' or 'subprocess'")

        if "websocket_port" in config:
            try:
                port = int(config["websocket_port"])
                if port < 1 or port > 65535:
                    errors.append("websocket_port must be between 1 and 65535")
            except (ValueError, TypeError):
                errors.append("websocket_port must be a valid integer")

        return len(errors) == 0, errors

    def setup_logging(self, config: Dict[str, Any]) -> None:
        """Setup logging configuration.

        Args:
            config: Logging configuration
        """
        log_level = config.get("log_level", "OFF")
        if log_level != "OFF":
            try:
                # Initialize project logger if needed
                project_logger = self.initialize_project_logger(log_level)
                if project_logger:
                    self.logger.info(
                        f"Project logging initialized with level: {log_level}"
                    )
            except Exception as e:
                self.logger.warning(f"Failed to setup logging: {e}")

    def initialize_configuration(self, **kwargs) -> Dict[str, Any]:
        """Initialize configuration and return configuration data.

        Args:
            **kwargs: Configuration parameters from ClaudeRunner constructor

        Returns:
            Dictionary containing initialized configuration data
        """
        config_data = {
            "enable_tickets": kwargs.get("enable_tickets", True),
            "log_level": kwargs.get("log_level", "OFF"),
            "claude_args": kwargs.get("claude_args", []) or [],
            "launch_method": kwargs.get("launch_method", "exec"),
            "enable_websocket": kwargs.get("enable_websocket", False),
            "websocket_port": kwargs.get("websocket_port", 8765),
        }

        # Initialize main configuration using ConfigLoader
        try:
            config_loader = ConfigLoader()
            config = config_loader.load_main_config()
        except Exception as e:
            self.logger.error("Failed to load configuration", exc_info=True)
            raise RuntimeError(f"Configuration initialization failed: {e}") from e

        config_data["config"] = config

        return config_data

    def initialize_project_logger(self, log_level: str):
        """Initialize project logger for session logging.

        Args:
            log_level: Logging level

        Returns:
            Initialized project logger or None if disabled/failed
        """
        if log_level == "OFF":
            return None

        try:
            project_logger = get_project_logger(log_level)
            project_logger.log_system(
                "Initializing ClaudeRunner", level="INFO", component="runner"
            )
            return project_logger
        except ImportError as e:
            self.logger.warning(f"Project logger module not available: {e}")
            return None
        except Exception as e:
            self.logger.warning(f"Failed to initialize project logger: {e}")
            return None

    def initialize_response_logger(self, config: Config, project_logger=None):
        """Initialize response logger if enabled in configuration.

        Args:
            config: Configuration object
            project_logger: Optional project logger for system events

        Returns:
            Initialized response logger or None if disabled/failed
        """
        response_config = config.get("response_logging", {})
        if not response_config.get("enabled", False):
            return None

        try:
            from claude_mpm.services.claude_session_logger import get_session_logger

            response_logger = get_session_logger(config)
            if project_logger:
                project_logger.log_system(
                    "Response logging initialized", level="INFO", component="logging"
                )
            return response_logger
        except Exception:
            self.logger.warning("Failed to initialize response logger", exc_info=True)
            return None

    def get_user_working_directory(self) -> Optional[Path]:
        """Get user working directory from environment.

        Returns:
            Path to user working directory or None if not set
        """
        if "CLAUDE_MPM_USER_PWD" in os.environ:
            user_working_dir = Path(os.environ["CLAUDE_MPM_USER_PWD"])
            self.logger.info(
                "Using user working directory from CLAUDE_MPM_USER_PWD",
                extra={"directory": str(user_working_dir)},
            )
            return user_working_dir
        return None

    def register_core_services(
        self, container, user_working_dir: Optional[Path] = None
    ):
        """Register core services in the DI container.

        Args:
            container: DI container instance
            user_working_dir: Optional user working directory
        """
        # Register deployment service
        from claude_mpm.core.interfaces import AgentDeploymentInterface

        if not container.is_registered(AgentDeploymentInterface):
            from claude_mpm.services.agents.deployment import AgentDeploymentService

            container.register_factory(
                AgentDeploymentInterface,
                lambda c: AgentDeploymentService(working_directory=user_working_dir),
                lifetime=ServiceLifetime.SINGLETON,
            )

    def register_ticket_manager(self, container, enable_tickets: bool):
        """Register ticket manager service if enabled.

        Args:
            container: DI container instance
            enable_tickets: Whether to enable ticket management

        Returns:
            Tuple of (ticket_manager, actual_enable_tickets_flag)
        """
        # Ticket manager is now disabled by default - use claude-mpm tickets CLI instead
        self.logger.info(
            "Ticket manager disabled - use 'claude-mpm tickets' CLI commands for ticket management"
        )
        return None, False

    def register_hook_service(self, container, config: Config):
        """Register hook service in the DI container.

        Args:
            container: DI container instance
            config: Configuration object

        Returns:
            Initialized hook service or None if failed
        """
        from claude_mpm.core.interfaces import HookServiceInterface

        if not container.is_registered(HookServiceInterface):
            from claude_mpm.services.hook_service import HookService

            container.register_factory(
                HookServiceInterface,
                lambda c: HookService(config),
                lifetime=ServiceLifetime.SINGLETON,
            )

        try:
            return container.get(HookServiceInterface)
        except Exception:
            self.logger.warning("Failed to initialize hook service", exc_info=True)
            return None

    def register_agent_capabilities_service(self, container):
        """Register agent capabilities service in the DI container.

        Args:
            container: DI container instance

        Returns:
            Initialized agent capabilities service or None if failed
        """
        from claude_mpm.services.core.interfaces import AgentCapabilitiesInterface

        if not container.is_registered(AgentCapabilitiesInterface):
            from claude_mpm.services.agent_capabilities_service import (
                AgentCapabilitiesService,
            )

            container.register_singleton(
                AgentCapabilitiesInterface, AgentCapabilitiesService
            )

        try:
            return container.get(AgentCapabilitiesInterface)
        except Exception:
            self.logger.warning(
                "Failed to initialize agent capabilities service", exc_info=True
            )
            return None

    def register_system_instructions_service(
        self, container, agent_capabilities_service
    ):
        """Register system instructions service in the DI container.

        Args:
            container: DI container instance
            agent_capabilities_service: Agent capabilities service dependency

        Returns:
            Initialized system instructions service or None if failed
        """
        from claude_mpm.services.core.interfaces import SystemInstructionsInterface

        if not container.is_registered(SystemInstructionsInterface):
            from claude_mpm.services.system_instructions_service import (
                SystemInstructionsService,
            )

            container.register_factory(
                SystemInstructionsInterface,
                lambda c: SystemInstructionsService(
                    agent_capabilities_service=agent_capabilities_service
                ),
                lifetime=ServiceLifetime.SINGLETON,
            )

        try:
            return container.get(SystemInstructionsInterface)
        except Exception:
            self.logger.warning(
                "Failed to initialize system instructions service", exc_info=True
            )
            return None

    def register_subprocess_launcher_service(
        self, container, project_logger, websocket_server
    ):
        """Register subprocess launcher service in the DI container.

        Args:
            container: DI container instance
            project_logger: Project logger dependency
            websocket_server: WebSocket server dependency

        Returns:
            Initialized subprocess launcher service or None if failed
        """
        from claude_mpm.services.core.interfaces import SubprocessLauncherInterface

        if not container.is_registered(SubprocessLauncherInterface):
            from claude_mpm.services.subprocess_launcher_service import (
                SubprocessLauncherService,
            )

            container.register_factory(
                SubprocessLauncherInterface,
                lambda c: SubprocessLauncherService(
                    project_logger=project_logger, websocket_server=websocket_server
                ),
                lifetime=ServiceLifetime.SINGLETON,
            )

        try:
            return container.get(SubprocessLauncherInterface)
        except Exception:
            self.logger.warning(
                "Failed to initialize subprocess launcher service", exc_info=True
            )
            return None

    def register_version_service(self, container):
        """Register version service in the DI container.

        Args:
            container: DI container instance

        Returns:
            Initialized version service or None if failed
        """
        from claude_mpm.services.core.interfaces import VersionServiceInterface

        if not container.is_registered(VersionServiceInterface):
            from claude_mpm.services.version_service import VersionService

            container.register_singleton(VersionServiceInterface, VersionService)

        try:
            return container.get(VersionServiceInterface)
        except Exception:
            self.logger.warning("Failed to initialize version service", exc_info=True)
            return None

    def register_command_handler_service(self, container, project_logger):
        """Register command handler service in the DI container.

        Args:
            container: DI container instance
            project_logger: Project logger dependency

        Returns:
            Initialized command handler service or None if failed
        """
        from claude_mpm.services.core.interfaces import CommandHandlerInterface

        if not container.is_registered(CommandHandlerInterface):
            from claude_mpm.services.command_handler_service import (
                CommandHandlerService,
            )

            container.register_factory(
                CommandHandlerInterface,
                lambda c: CommandHandlerService(project_logger=project_logger),
                lifetime=ServiceLifetime.SINGLETON,
            )

        try:
            return container.get(CommandHandlerInterface)
        except Exception:
            self.logger.warning(
                "Failed to initialize command handler service", exc_info=True
            )
            return None

    def register_memory_hook_service(self, container, hook_service):
        """Register memory hook service in the DI container.

        Args:
            container: DI container instance
            hook_service: Hook service dependency

        Returns:
            Initialized memory hook service or None if failed
        """
        from claude_mpm.services.core.interfaces import MemoryHookInterface

        if not container.is_registered(MemoryHookInterface):
            from claude_mpm.services.memory_hook_service import MemoryHookService

            container.register_factory(
                MemoryHookInterface,
                lambda c: MemoryHookService(hook_service=hook_service),
                lifetime=ServiceLifetime.SINGLETON,
            )

        try:
            return container.get(MemoryHookInterface)
        except Exception:
            self.logger.warning(
                "Failed to initialize memory hook service", exc_info=True
            )
            return None

    def register_session_management_service(self, container, runner):
        """Register session management service in the DI container.

        Args:
            container: DI container instance
            runner: ClaudeRunner instance dependency

        Returns:
            Initialized session management service or None if failed
        """
        from claude_mpm.services.core.interfaces import SessionManagementInterface

        if not container.is_registered(SessionManagementInterface):
            from claude_mpm.services.session_management_service import (
                SessionManagementService,
            )

            container.register_factory(
                SessionManagementInterface,
                lambda c: SessionManagementService(runner=runner),
                lifetime=ServiceLifetime.SINGLETON,
            )

        try:
            return container.get(SessionManagementInterface)
        except Exception:
            self.logger.warning(
                "Failed to initialize session management service", exc_info=True
            )
            return None

    def register_utility_service(self, container):
        """Register utility service in the DI container.

        Args:
            container: DI container instance

        Returns:
            Initialized utility service or None if failed
        """
        from claude_mpm.services.core.interfaces import UtilityServiceInterface

        if not container.is_registered(UtilityServiceInterface):
            from claude_mpm.services.utility_service import UtilityService

            container.register_singleton(UtilityServiceInterface, UtilityService)

        try:
            return container.get(UtilityServiceInterface)
        except Exception:
            self.logger.warning("Failed to initialize utility service", exc_info=True)
            return None

    def create_session_log_file(
        self, project_logger, log_level: str, config_data: Dict[str, Any]
    ) -> Optional[Path]:
        """Create session log file and log session start event.

        Args:
            project_logger: Project logger instance
            log_level: Logging level
            config_data: Configuration data for logging

        Returns:
            Path to session log file or None if failed
        """
        if not project_logger or log_level == "OFF":
            return None

        try:
            # Create a system.jsonl file in the session directory
            session_log_file = project_logger.session_dir / "system.jsonl"

            # Log session start event
            {
                "event": "session_start",
                "runner": "ClaudeRunner",
                "enable_tickets": config_data.get("enable_tickets"),
                "log_level": log_level,
                "launch_method": config_data.get("launch_method"),
            }

            # Write session event (this would be handled by a session logging method)
            # For now, we'll return the file path
            return session_log_file

        except PermissionError as e:
            self.logger.debug(f"Permission denied creating session log file: {e}")
            return None
        except OSError as e:
            self.logger.debug(f"OS error creating session log file: {e}")
            return None
        except Exception as e:
            self.logger.debug(f"Failed to create session log file: {e}")
            return None
