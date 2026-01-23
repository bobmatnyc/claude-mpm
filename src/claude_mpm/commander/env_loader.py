"""Environment variable loader for Commander.

This module handles automatic loading of .env and .env.local files
at Commander startup. Environment files are loaded with the following precedence:
1. Existing environment variables (not overridden)
2. .env.local (local overrides)
3. .env (defaults)

Example:
    >>> from claude_mpm.commander.env_loader import load_env
    >>> load_env()
    # Automatically loads .env.local and .env from project root
"""

import logging
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def load_env() -> None:
    """Load environment variables from .env and .env.local files.

    Searches for .env and .env.local in the project root directory
    (parent of src/claude_mpm). Files are loaded with override=False,
    meaning existing environment variables take precedence.

    Precedence (highest to lowest):
    1. Existing environment variables
    2. .env.local
    3. .env

    Example:
        >>> load_env()
        # Loads .env.local and .env if they exist
    """
    # Use current working directory as project root
    # This makes the loader work regardless of where the module is installed
    project_root = Path.cwd()

    # Try loading .env.local first (higher priority)
    env_local = project_root / ".env.local"
    if env_local.exists():
        load_dotenv(env_local, override=False)
        logger.debug(f"Loaded environment from {env_local}")

    # Then load .env (lower priority)
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=False)
        logger.debug(f"Loaded environment from {env_file}")

    # Log if neither file exists
    if not env_local.exists() and not env_file.exists():
        logger.debug("No .env or .env.local files found in project root")
