"""CLI module for claude-mpm.

This module provides registry-based argument and command management
to reduce complexity in the main CLI function.
"""

from .args import ArgumentRegistry
from .commands import CommandDefinition, CommandRegistry, register_standard_commands

__all__ = [
    "ArgumentRegistry",
    "CommandDefinition",
    "CommandRegistry",
    "register_standard_commands",
]
