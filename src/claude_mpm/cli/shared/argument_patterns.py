"""
Common CLI argument patterns to reduce duplication.

This module provides reusable argument definitions that are commonly used
across multiple CLI commands.
"""

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional


class CommonArguments:
    """Registry of common argument patterns used across CLI commands."""

    # Logging arguments
    VERBOSE = {
        "flags": ["-v", "--verbose"],
        "action": "store_true",
        "help": "Enable verbose output",
    }

    QUIET = {
        "flags": ["-q", "--quiet"],
        "action": "store_true",
        "help": "Suppress non-error output",
    }

    DEBUG = {
        "flags": ["--debug"],
        "action": "store_true",
        "help": "Enable debug logging",
    }

    # Configuration arguments
    CONFIG_FILE = {
        "flags": ["-c", "--config"],
        "type": Path,
        "help": "Path to configuration file",
    }

    CONFIG_DIR = {
        "flags": ["--config-dir"],
        "type": Path,
        "help": "Configuration directory path",
    }

    # Output arguments
    OUTPUT_FORMAT = {
        "flags": ["-f", "--format"],
        "choices": ["json", "yaml", "table", "text"],
        "default": "text",
        "help": "Output format",
    }

    OUTPUT_FILE = {
        "flags": ["-o", "--output"],
        "type": Path,
        "help": "Output file path",
    }

    # Common flags
    FORCE = {
        "flags": ["--force"],
        "action": "store_true",
        "help": "Force operation without confirmation",
    }

    DRY_RUN = {
        "flags": ["--dry-run"],
        "action": "store_true",
        "help": "Show what would be done without executing",
    }

    # Agent-related arguments
    AGENT_NAME = {"flags": ["--agent"], "help": "Agent name or pattern"}

    AGENT_DIR = {"flags": ["--agent-dir"], "type": Path, "help": "Agent directory path"}

    # Memory-related arguments
    MEMORY_DIR = {
        "flags": ["--memory-dir"],
        "type": Path,
        "help": "Memory directory path",
    }


def add_argument_from_pattern(
    parser: argparse.ArgumentParser, pattern: Dict[str, Any]
) -> None:
    """Add an argument to parser from a pattern definition."""
    flags = pattern.pop("flags")
    parser.add_argument(*flags, **pattern)


def add_common_arguments(
    parser: argparse.ArgumentParser,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
) -> None:
    """
    Add common arguments to a parser.

    Args:
        parser: ArgumentParser to add arguments to
        include: List of argument names to include (if None, includes all)
        exclude: List of argument names to exclude
    """
    # Default common arguments
    common_args = ["verbose", "quiet", "debug", "config_file", "output_format"]

    if include is not None:
        common_args = [arg for arg in common_args if arg in include]

    if exclude is not None:
        common_args = [arg for arg in common_args if arg not in exclude]

    # Map argument names to patterns
    arg_patterns = {
        "verbose": CommonArguments.VERBOSE.copy(),
        "quiet": CommonArguments.QUIET.copy(),
        "debug": CommonArguments.DEBUG.copy(),
        "config_file": CommonArguments.CONFIG_FILE.copy(),
        "output_format": CommonArguments.OUTPUT_FORMAT.copy(),
        "force": CommonArguments.FORCE.copy(),
        "dry_run": CommonArguments.DRY_RUN.copy(),
    }

    for arg_name in common_args:
        if arg_name in arg_patterns:
            add_argument_from_pattern(parser, arg_patterns[arg_name])


def add_logging_arguments(parser: argparse.ArgumentParser) -> None:
    """Add logging-related arguments."""
    group = parser.add_argument_group("logging options")

    patterns = [
        CommonArguments.VERBOSE.copy(),
        CommonArguments.QUIET.copy(),
        CommonArguments.DEBUG.copy(),
    ]

    for pattern in patterns:
        add_argument_from_pattern(group, pattern)


def add_config_arguments(parser: argparse.ArgumentParser) -> None:
    """Add configuration-related arguments."""
    group = parser.add_argument_group("configuration options")

    patterns = [CommonArguments.CONFIG_FILE.copy(), CommonArguments.CONFIG_DIR.copy()]

    for pattern in patterns:
        add_argument_from_pattern(group, pattern)


def add_output_arguments(parser: argparse.ArgumentParser) -> None:
    """Add output-related arguments."""
    group = parser.add_argument_group("output options")

    patterns = [
        CommonArguments.OUTPUT_FORMAT.copy(),
        CommonArguments.OUTPUT_FILE.copy(),
    ]

    for pattern in patterns:
        add_argument_from_pattern(group, pattern)


def add_agent_arguments(parser: argparse.ArgumentParser) -> None:
    """Add agent-related arguments."""
    group = parser.add_argument_group("agent options")

    patterns = [CommonArguments.AGENT_NAME.copy(), CommonArguments.AGENT_DIR.copy()]

    for pattern in patterns:
        add_argument_from_pattern(group, pattern)


def add_memory_arguments(parser: argparse.ArgumentParser) -> None:
    """Add memory-related arguments."""
    group = parser.add_argument_group("memory options")

    patterns = [CommonArguments.MEMORY_DIR.copy()]

    for pattern in patterns:
        add_argument_from_pattern(group, pattern)


def add_operation_arguments(parser: argparse.ArgumentParser) -> None:
    """Add operation control arguments."""
    group = parser.add_argument_group("operation options")

    patterns = [CommonArguments.FORCE.copy(), CommonArguments.DRY_RUN.copy()]

    for pattern in patterns:
        add_argument_from_pattern(group, pattern)
