"""
Shared CLI utilities for claude-mpm.

This module provides common utilities to reduce code duplication across CLI commands.
"""

from .argument_patterns import (
    CommonArguments,
    add_agent_arguments,
    add_common_arguments,
    add_config_arguments,
    add_logging_arguments,
    add_memory_arguments,
    add_output_arguments,
)
from .command_base import AgentCommand, BaseCommand, CommandResult, MemoryCommand
from .error_handling import CLIErrorHandler, handle_cli_errors
from .output_formatters import OutputFormatter, format_output

__all__ = [
    # Argument patterns
    "CommonArguments",
    "add_agent_arguments",
    "add_common_arguments",
    "add_config_arguments",
    "add_logging_arguments",
    "add_memory_arguments",
    "add_output_arguments",
    # Command base
    "AgentCommand",
    "BaseCommand",
    "CommandResult",
    "MemoryCommand",
    # Error handling
    "CLIErrorHandler",
    "handle_cli_errors",
    # Output formatting
    "OutputFormatter",
    "format_output",
]
