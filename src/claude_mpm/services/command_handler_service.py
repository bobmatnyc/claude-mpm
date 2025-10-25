"""Command handler service for processing MPM commands.

This service handles:
1. MPM command parsing and validation
2. Command execution and routing
3. Command logging and error handling
4. Integration with CLI modules

Extracted from ClaudeRunner to follow Single Responsibility Principle.
"""

from typing import Any, Dict, List

from claude_mpm.core.base_service import BaseService
from claude_mpm.core.enums import OperationResult
from claude_mpm.services.core.interfaces import CommandHandlerInterface


class CommandHandlerService(BaseService, CommandHandlerInterface):
    """Service for handling MPM commands."""

    def __init__(self, project_logger=None):
        """Initialize the command handler service.

        Args:
            project_logger: Optional project logger for command logging
        """
        super().__init__(name="command_handler_service")
        self.project_logger = project_logger

    async def _initialize(self) -> None:
        """Initialize the service. No special initialization needed."""

    async def _cleanup(self) -> None:
        """Cleanup service resources. No cleanup needed."""

    def handle_mpm_command(self, prompt: str) -> bool:
        """Handle /mpm: commands directly without going to Claude.

        Args:
            prompt: The full prompt starting with "/mpm:"

        Returns:
            bool: True if command was handled successfully, False otherwise
        """
        try:
            # Extract command and arguments
            command_line = prompt[5:].strip()  # Remove "/mpm:"
            parts = command_line.split()

            if not parts:
                print("No command specified. Available commands: test, agents")
                return True

            command = parts[0]
            args = parts[1:]

            # Route to appropriate handler
            if command == "test":
                return self._handle_test_command(args)
            if command == "agents":
                return self._handle_agents_command(args)
            print(f"Unknown command: {command}")
            print("Available commands: test, agents")
            return True

        except KeyboardInterrupt:
            print("\nCommand interrupted")
            return False
        except Exception as e:
            print(f"Error executing command: {e}")
            self._log_command_error(f"Failed to execute /mpm: command: {e}")
            return False

    def _handle_test_command(self, args: list) -> bool:
        """Handle the test command.

        Args:
            args: Command arguments

        Returns:
            bool: True if successful
        """
        print("Hello World")
        self._log_command_success("Executed /mpm:test command")
        return True

    def _handle_agents_command(self, args: list) -> bool:
        """Handle the agents command - display deployed agent versions.

        WHY: This provides users with a quick way to check deployed agent versions
        directly from within Claude Code, maintaining consistency with CLI behavior.

        Args:
            args: Command arguments

        Returns:
            bool: True if successful, False if error occurred
        """
        try:
            from claude_mpm.cli import _get_agent_versions_display

            agent_versions = _get_agent_versions_display()
            if agent_versions:
                print(agent_versions)
            else:
                print("No deployed agents found")
                print("\nTo deploy agents, run: claude-mpm --mpm:agents deploy")

            self._log_command_success("Executed /mpm:agents command")
            return True

        except ImportError as e:
            print(f"Error: CLI module not available: {e}")
            return False
        except Exception as e:
            print(f"Error getting agent versions: {e}")
            return False

    def _log_command_success(self, message: str):
        """Log successful command execution.

        Args:
            message: Success message to log
        """
        if self.project_logger:
            self.project_logger.log_system(message, level="INFO", component="command")

    def _log_command_error(self, message: str):
        """Log command execution error.

        Args:
            message: Error message to log
        """
        if self.project_logger:
            self.project_logger.log_system(message, level="ERROR", component="command")

    def is_mpm_command(self, prompt: str) -> bool:
        """Check if a prompt is an MPM command.

        Args:
            prompt: The prompt to check

        Returns:
            bool: True if the prompt is an MPM command
        """
        return prompt.strip().startswith("/mpm:")

    def get_available_commands(self) -> List[str]:
        """Get list of available MPM commands.

        Returns:
            List: List of available command names
        """
        return ["test", "agents"]

    # Implementation of abstract methods from CommandHandlerInterface

    def handle_command(self, command: str, args: List[str]) -> Dict[str, Any]:
        """Handle an MPM command.

        Args:
            command: Command name to execute
            args: Command arguments

        Returns:
            Dictionary with command execution results
        """
        try:
            if command == "test":
                success = self._handle_test_command(args)
                return {
                    OperationResult.SUCCESS.value: success,
                    "command": command,
                    "args": args,
                    "message": (
                        "Test command executed" if success else "Test command failed"
                    ),
                }
            if command == "agents":
                success = self._handle_agents_command(args)
                return {
                    OperationResult.SUCCESS.value: success,
                    "command": command,
                    "args": args,
                    "message": (
                        "Agents command executed"
                        if success
                        else "Agents command failed"
                    ),
                }
            return {
                OperationResult.SUCCESS.value: False,
                "command": command,
                "args": args,
                OperationResult.ERROR.value: f"Unknown command: {command}",
                "available_commands": self.get_available_commands(),
            }
        except Exception as e:
            return {
                OperationResult.SUCCESS.value: False,
                "command": command,
                "args": args,
                OperationResult.ERROR.value: str(e),
            }

    def get_command_help(self, command: str) -> str:
        """Get help text for a specific command.

        Args:
            command: Command name

        Returns:
            Help text for the command
        """
        help_text = {
            "test": "Test command - prints 'Hello World' to verify MPM command functionality",
            "agents": "Agents command - displays information about deployed agents and their versions",
        }

        return help_text.get(command, f"No help available for command: {command}")
