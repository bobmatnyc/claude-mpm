"""
Package initialization with module-level code.

This __init__.py demonstrates that these files can contain
important code that isn't classes or functions.
"""

# Import statements
import os
import sys
from pathlib import Path

# Module-level constants
VERSION = "2.1.0"
PACKAGE_NAME = "test_package"
DEFAULT_CONFIG = {
    "debug": False,
    "log_level": "INFO",
    "max_retries": 3
}

# Module-level variables
_initialized = False
_config_cache = {}

# Package root detection
PACKAGE_ROOT = Path(__file__).parent

# Environment setup
if "TEST_MODE" in os.environ:
    DEFAULT_CONFIG["debug"] = True
    DEFAULT_CONFIG["log_level"] = "DEBUG"

# Auto-configuration
def _setup_logging():
    """Internal setup function."""
    import logging
    level = getattr(logging, DEFAULT_CONFIG["log_level"])
    logging.basicConfig(level=level)

# Execute setup
_setup_logging()
_initialized = True

# Public API exports
__version__ = VERSION
__all__ = ["VERSION", "PACKAGE_NAME", "DEFAULT_CONFIG"]

# Package-level initialization message
print(f"{PACKAGE_NAME} v{VERSION} initialized")
