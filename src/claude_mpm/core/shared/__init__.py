"""
Shared core utilities to reduce code duplication.

This module provides common utilities that can be used across
different parts of the application.
"""

from .config_loader import ConfigLoader, ConfigPattern
from .path_resolver import PathResolver
from .singleton_manager import SingletonManager

__all__ = [
    "ConfigLoader",
    "ConfigPattern",
    "PathResolver",
    "SingletonManager",
]
