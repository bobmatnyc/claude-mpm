"""CLI module for claude-mpm.

This module provides registry-based argument and command management
to reduce complexity in the main CLI function.
"""

from .args import ArgumentRegistry
from .commands import CommandRegistry, CommandDefinition, register_standard_commands

__all__ = [
    'ArgumentRegistry',
    'CommandRegistry',
    'CommandDefinition',
    'register_standard_commands'
]