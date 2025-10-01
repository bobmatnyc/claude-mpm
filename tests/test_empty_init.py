# This is an __init__.py file that is NOT empty
# It contains module-level documentation and imports

"""
Test package initialization module.

This module demonstrates that __init__.py files can contain
meaningful content beyond just imports.
"""

import os
import sys
from typing import Dict, List, Optional

# Module-level constants
VERSION = "1.0.0"
AUTHOR = "Test Author"

# Module-level variables
_private_cache = {}
public_config = {"debug": False, "log_level": "INFO"}


# Module-level function
def get_version() -> str:
    """Get the package version."""
    return VERSION


def initialize_package(config: Optional[Dict] = None) -> None:
    """Initialize the package with optional configuration."""
    global public_config
    if config:
        public_config.update(config)

    print(f"Package initialized with config: {public_config}")


# Module-level class
class PackageManager:
    """Manages package-level operations."""

    def __init__(self):
        self.initialized = False

    def setup(self) -> bool:
        """Setup the package manager."""
        self.initialized = True
        return True

    def get_status(self) -> Dict:
        """Get package status."""
        return {
            "initialized": self.initialized,
            "version": VERSION,
            "config": public_config,
        }


# Auto-initialization
_manager = PackageManager()
_manager.setup()

# Export public interface
__all__ = [
    "AUTHOR",
    "VERSION",
    "PackageManager",
    "get_version",
    "initialize_package",
    "public_config",
]
