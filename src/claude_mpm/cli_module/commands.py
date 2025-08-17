"""Command registry for managing CLI subcommands."""

import argparse
from typing import Any, Callable, Dict, List, Optional

from .args import ArgumentRegistry


class CommandDefinition:
    """Definition for a CLI command."""

    def __init__(
        self,
        name: str,
        help_text: str,
        handler: Callable,
        argument_groups: Optional[List[str]] = None,
        extra_args: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        """Initialize command definition.

        Args:
            name: Command name
            help_text: Help text for the command
            handler: Function to call when command is executed
            argument_groups: List of argument group names to include
            extra_args: Additional command-specific arguments
        """
        self.name = name
        self.help_text = help_text
        self.handler = handler
        self.argument_groups = argument_groups or []
        self.extra_args = extra_args or {}


class CommandRegistry:
    """Registry for managing CLI subcommands.

    This class simplifies subcommand management and reduces
    complexity in the main CLI function.
    """

    def __init__(self, arg_registry: Optional[ArgumentRegistry] = None):
        """Initialize the command registry.

        Args:
            arg_registry: ArgumentRegistry instance for applying arguments
        """
        self._commands: Dict[str, CommandDefinition] = {}
        self._arg_registry = arg_registry or ArgumentRegistry()
        self._default_command: Optional[str] = None

    def register(
        self,
        name: str,
        help_text: str,
        handler: Callable,
        argument_groups: Optional[List[str]] = None,
        extra_args: Optional[Dict[str, Dict[str, Any]]] = None,
        is_default: bool = False,
    ):
        """Register a new command.

        Args:
            name: Command name
            help_text: Help text for the command
            handler: Function to call when command is executed
            argument_groups: List of argument group names from ArgumentRegistry
            extra_args: Additional command-specific arguments
            is_default: Whether this is the default command
        """
        command = CommandDefinition(
            name=name,
            help_text=help_text,
            handler=handler,
            argument_groups=argument_groups,
            extra_args=extra_args,
        )

        self._commands[name] = command

        if is_default:
            self._default_command = name

    def setup_subcommands(
        self, parser: argparse.ArgumentParser
    ) -> argparse._SubParsersAction:
        """Set up all registered subcommands on the parser.

        Args:
            parser: Main argument parser

        Returns:
            The subparsers object
        """
        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        for name, command in self._commands.items():
            # Create subparser
            subparser = subparsers.add_parser(name, help=command.help_text)

            # Apply argument groups
            if command.argument_groups:
                self._arg_registry.apply_arguments(
                    subparser, groups=command.argument_groups
                )

            # Apply extra arguments
            for arg_name, arg_config in command.extra_args.items():
                flags = arg_config.pop("flags", [f'--{arg_name.replace("_", "-")}'])
                subparser.add_argument(*flags, **arg_config)

            # Store handler reference
            subparser.set_defaults(_handler=command.handler)

        return subparsers

    def execute_command(self, args: argparse.Namespace, **kwargs) -> Any:
        """Execute the appropriate command handler.

        Args:
            args: Parsed command line arguments
            **kwargs: Additional keyword arguments to pass to handler

        Returns:
            Result from the command handler
        """
        # Handle default command
        command_name = args.command
        if not command_name and self._default_command:
            command_name = self._default_command
            args.command = command_name

            # Apply default command's argument defaults
            command = self._commands.get(command_name)
            if command:
                # Set defaults for arguments that might not be present
                for group in command.argument_groups:
                    for arg_name in self._arg_registry._groups.get(group, []):
                        if not hasattr(args, arg_name):
                            definition = self._arg_registry.get_argument_definition(
                                arg_name
                            )
                            if definition and "default" in definition:
                                setattr(args, arg_name, definition["default"])
                            elif (
                                definition and definition.get("action") == "store_true"
                            ):
                                setattr(args, arg_name, False)

        # Get command handler
        if hasattr(args, "_handler"):
            handler = args._handler
        else:
            command = self._commands.get(command_name)
            if command:
                handler = command.handler
            else:
                return None

        # Execute handler
        return handler(args, **kwargs)

    def get_command_names(self) -> List[str]:
        """Get list of all registered command names."""
        return list(self._commands.keys())

    def get_default_command(self) -> Optional[str]:
        """Get the default command name."""
        return self._default_command

    def has_command(self, name: str) -> bool:
        """Check if a command is registered."""
        return name in self._commands


def register_standard_commands(registry: CommandRegistry):
    """Register the standard claude-mpm commands.

    This function registers all the standard commands that claude-mpm
    supports, reducing the setup code in main().

    Args:
        registry: CommandRegistry instance to register commands with
    """
    # Import handlers (these would be refactored from cli.py)
    from ..cli import list_tickets, run_session, show_info

    # Register run command (default)
    registry.register(
        name="run",
        help_text="Run orchestrated Claude session (default)",
        handler=run_session,
        argument_groups=["run", "orchestration"],
        is_default=True,
    )

    # Register tickets command
    registry.register(
        name="tickets",
        help_text="List recent tickets",
        handler=list_tickets,
        argument_groups=["tickets"],
    )

    # Register info command
    registry.register(
        name="info",
        help_text="Show framework and configuration info",
        handler=show_info,
        argument_groups=[],  # No specific arguments needed
    )
