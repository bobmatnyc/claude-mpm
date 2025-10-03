"""
Base command class to reduce duplication in CLI command implementations.
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from ...core.config import Config
from ...core.logger import get_logger
from ...core.shared.config_loader import ConfigLoader


@dataclass
class CommandResult:
    """Standard result structure for CLI commands."""

    success: bool
    exit_code: int = 0
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    @classmethod
    def success_result(
        cls, message: Optional[str] = None, data: Optional[Dict[str, Any]] = None
    ) -> "CommandResult":
        """Create a success result."""
        return cls(success=True, exit_code=0, message=message, data=data)

    @classmethod
    def error_result(
        cls, message: str, exit_code: int = 1, data: Optional[Dict[str, Any]] = None
    ) -> "CommandResult":
        """Create an error result."""
        return cls(success=False, exit_code=exit_code, message=message, data=data)


class BaseCommand(ABC):
    """
    Base class for CLI commands to reduce duplication.

    Provides common functionality:
    - Logger initialization
    - Configuration loading
    - Working directory handling
    - Standard error handling patterns
    """

    def __init__(self, command_name: str):
        """
        Initialize base command.

        Args:
            command_name: Name of the command for logging
        """
        self.command_name = command_name
        self.logger = get_logger(f"cli.{command_name}")
        self._config: Optional[Config] = None
        self._working_dir: Optional[Path] = None

    @property
    def config(self) -> Config:
        """Get configuration instance (lazy loaded)."""
        if self._config is None:
            config_loader = ConfigLoader()
            self._config = config_loader.load_main_config()
        return self._config

    @property
    def working_dir(self) -> Path:
        """Get working directory (respects CLAUDE_MPM_USER_PWD)."""
        if self._working_dir is None:
            # Use CLAUDE_MPM_USER_PWD if available (when called via shell script)
            user_pwd = os.environ.get("CLAUDE_MPM_USER_PWD", Path.cwd())
            self._working_dir = Path(user_pwd)
        return self._working_dir

    def setup_logging(self, args) -> None:
        """Setup logging based on command arguments."""
        import logging

        # Set log level based on arguments
        if hasattr(args, "debug") and args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
        elif hasattr(args, "verbose") and args.verbose:
            logging.getLogger().setLevel(logging.INFO)
        elif hasattr(args, "quiet") and args.quiet:
            logging.getLogger().setLevel(logging.WARNING)

    def load_config(self, args) -> None:
        """Load configuration from arguments."""
        config_loader = ConfigLoader()
        if hasattr(args, "config") and args.config:
            # Use specific config file with ConfigLoader
            from ...core.shared.config_loader import ConfigPattern

            pattern = ConfigPattern(
                filenames=[Path(args.config).name],
                search_paths=[str(Path(args.config).parent)],
                env_prefix="CLAUDE_MPM_",
            )
            self._config = config_loader.load_config(
                pattern, cache_key=f"cli_{args.config}"
            )
        else:
            self._config = config_loader.load_main_config()

    def validate_args(self, args) -> Optional[str]:
        """
        Validate command arguments.

        Args:
            args: Parsed command arguments

        Returns:
            Error message if validation fails, None if valid
        """
        # Base validation - subclasses can override
        return None

    def execute(self, args) -> CommandResult:
        """
        Execute the command with standard error handling.

        Args:
            args: Parsed command arguments

        Returns:
            CommandResult with execution status
        """
        try:
            # Setup
            self.setup_logging(args)
            self.load_config(args)

            # Validate arguments
            validation_error = self.validate_args(args)
            if validation_error:
                return CommandResult.error_result(validation_error)

            # Execute command-specific logic
            return self.run(args)

        except KeyboardInterrupt:
            self.logger.info("Command interrupted by user")
            return CommandResult.error_result(
                "Operation cancelled by user", exit_code=130
            )

        except Exception as e:
            self.logger.error(f"Command failed: {e}", exc_info=True)
            return CommandResult.error_result(f"Command failed: {e}")

    @abstractmethod
    def run(self, args) -> CommandResult:
        """
        Run the command-specific logic.

        Args:
            args: Parsed command arguments

        Returns:
            CommandResult with execution status
        """

    def print_result(self, result: CommandResult, args) -> None:
        """
        Print command result based on output format.

        Args:
            result: Command result to print
            args: Command arguments (for format options)
        """
        from .output_formatters import format_output

        # Determine output format
        output_format = getattr(args, "format", "text")

        # Format and print result
        formatted_output = format_output(result, output_format)

        if hasattr(args, "output") and args.output:
            # Write to file
            with args.output.open("w") as f:
                f.write(formatted_output)
            self.logger.info(f"Output written to {args.output}")
        else:
            # Print to stdout
            print(formatted_output)


class ServiceCommand(BaseCommand):
    """Base class for commands that work with services."""

    def __init__(self, command_name: str, service_class: type):
        """
        Initialize service command.

        Args:
            command_name: Name of the command
            service_class: Service class to instantiate
        """
        super().__init__(command_name)
        self.service_class = service_class
        self._service = None

    @property
    def service(self):
        """Get service instance (lazy loaded)."""
        if self._service is None:
            self._service = self.service_class()
        return self._service


class AgentCommand(BaseCommand):
    """Base class for agent-related commands."""

    def get_agent_dir(self, args) -> Path:
        """Get agent directory from arguments or default."""
        if hasattr(args, "agent_dir") and args.agent_dir:
            return args.agent_dir

        # Default to working directory
        return self.working_dir

    def get_agent_pattern(self, args) -> Optional[str]:
        """Get agent name pattern from arguments."""
        return getattr(args, "agent", None)


class MemoryCommand(BaseCommand):
    """Base class for memory-related commands."""

    def get_memory_dir(self, args) -> Path:
        """Get memory directory from arguments or default."""
        if hasattr(args, "memory_dir") and args.memory_dir:
            return args.memory_dir

        # Default to .claude-mpm/memories in working directory
        return self.working_dir / ".claude-mpm" / "memories"
