"""
Common utility functions to replace duplicate implementations across the codebase.

This module consolidates frequently duplicated utility functions found across
50+ files in the claude-mpm codebase.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

# Import our centralized logger
from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


# ==============================================================================
# JSON/YAML UTILITIES
# ==============================================================================


def load_json_safe(
    file_path: Union[str, Path],
    default: Optional[Any] = None,
    encoding: str = "utf-8",
) -> Any:
    """
    Safely load JSON from a file with error handling.

    Replaces 20+ duplicate implementations across the codebase.

    Args:
        file_path: Path to JSON file
        default: Default value if file doesn't exist or is invalid
        encoding: File encoding

    Returns:
        Parsed JSON data or default value
    """
    file_path = Path(file_path)

    try:
        with Path(file_path).open(
            encoding=encoding,
        ) as f:
            return json.load(f)
    except FileNotFoundError:
        logger.debug(f"JSON file not found: {file_path}")
        return default if default is not None else {}
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in {file_path}: {e}")
        return default if default is not None else {}
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {e}")
        return default if default is not None else {}


def save_json_safe(
    file_path: Union[str, Path],
    data: Any,
    indent: int = 2,
    encoding: str = "utf-8",
    create_parents: bool = True,
) -> bool:
    """
    Safely save data to JSON file with error handling.

    Args:
        file_path: Path to save JSON file
        data: Data to serialize
        indent: JSON indentation level
        encoding: File encoding
        create_parents: Create parent directories if they don't exist

    Returns:
        True if successful, False otherwise
    """
    file_path = Path(file_path)

    try:
        if create_parents:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        with file_path.open("w", encoding=encoding) as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving JSON to {file_path}: {e}")
        return False


def load_yaml_safe(
    file_path: Union[str, Path],
    default: Optional[Any] = None,
    encoding: str = "utf-8",
) -> Any:
    """
    Safely load YAML from a file with error handling.

    Args:
        file_path: Path to YAML file
        default: Default value if file doesn't exist or is invalid
        encoding: File encoding

    Returns:
        Parsed YAML data or default value
    """
    file_path = Path(file_path)

    try:
        with Path(file_path).open(
            encoding=encoding,
        ) as f:
            return yaml.safe_load(f) or default or {}
    except FileNotFoundError:
        logger.debug(f"YAML file not found: {file_path}")
        return default if default is not None else {}
    except yaml.YAMLError as e:
        logger.warning(f"Invalid YAML in {file_path}: {e}")
        return default if default is not None else {}
    except Exception as e:
        logger.error(f"Error loading YAML from {file_path}: {e}")
        return default if default is not None else {}


def save_yaml_safe(
    file_path: Union[str, Path],
    data: Any,
    encoding: str = "utf-8",
    create_parents: bool = True,
) -> bool:
    """
    Safely save data to YAML file with error handling.

    Args:
        file_path: Path to save YAML file
        data: Data to serialize
        encoding: File encoding
        create_parents: Create parent directories if they don't exist

    Returns:
        True if successful, False otherwise
    """
    file_path = Path(file_path)

    try:
        if create_parents:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        with file_path.open("w", encoding=encoding) as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
        return True
    except Exception as e:
        logger.error(f"Error saving YAML to {file_path}: {e}")
        return False


# ==============================================================================
# PATH/FILE UTILITIES
# ==============================================================================


def ensure_path_exists(
    path: Union[str, Path],
    create_parents: bool = True,
    is_file: bool = False,
) -> bool:
    """
    Ensure a path exists, optionally creating parent directories.

    Replaces 50+ duplicate path existence checks.

    Args:
        path: Path to check/create
        create_parents: Create parent directories if needed
        is_file: If True, path is a file (create parent dir only)

    Returns:
        True if path exists or was created, False otherwise
    """
    path = Path(path)

    try:
        if path.exists():
            return True

        if is_file:
            if create_parents:
                path.parent.mkdir(parents=True, exist_ok=True)
            # Don't create the file itself, just ensure parent exists
            return path.parent.exists()
        if create_parents:
            path.mkdir(parents=True, exist_ok=True)
            return True
        return False
    except Exception as e:
        logger.error(f"Error ensuring path exists {path}: {e}")
        return False


def read_file_if_exists(
    file_path: Union[str, Path],
    encoding: str = "utf-8",
    default: str = "",
) -> Optional[str]:
    """
    Read file contents if it exists, otherwise return default.

    Args:
        file_path: Path to file
        encoding: File encoding
        default: Default value if file doesn't exist

    Returns:
        File contents or default value
    """
    file_path = Path(file_path)

    try:
        if file_path.exists() and file_path.is_file():
            return file_path.read_text(encoding=encoding)
        return default
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return default


def write_file_safe(
    file_path: Union[str, Path],
    content: str,
    encoding: str = "utf-8",
    create_parents: bool = True,
) -> bool:
    """
    Safely write content to file with error handling.

    Args:
        file_path: Path to file
        content: Content to write
        encoding: File encoding
        create_parents: Create parent directories if needed

    Returns:
        True if successful, False otherwise
    """
    file_path = Path(file_path)

    try:
        if create_parents:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_text(content, encoding=encoding)
        return True
    except Exception as e:
        logger.error(f"Error writing file {file_path}: {e}")
        return False


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    Get file size in bytes, returning 0 if file doesn't exist.

    Args:
        file_path: Path to file

    Returns:
        File size in bytes or 0
    """
    file_path = Path(file_path)

    try:
        if file_path.exists() and file_path.is_file():
            return file_path.stat().st_size
        return 0
    except Exception as e:
        logger.error(f"Error getting file size {file_path}: {e}")
        return 0


def find_files(
    directory: Union[str, Path],
    pattern: str = "*",
    recursive: bool = True,
) -> List[Path]:
    """
    Find files matching a pattern in a directory.

    Args:
        directory: Directory to search
        pattern: Glob pattern
        recursive: Search recursively

    Returns:
        List of matching file paths
    """
    directory = Path(directory)

    try:
        if not directory.exists():
            return []

        if recursive:
            return list(directory.rglob(pattern))
        return list(directory.glob(pattern))
    except Exception as e:
        logger.error(f"Error finding files in {directory}: {e}")
        return []


# ==============================================================================
# SUBPROCESS UTILITIES
# ==============================================================================


def run_command_safe(
    command: Union[str, List[str]],
    cwd: Optional[Union[str, Path]] = None,
    capture_output: bool = True,
    check: bool = False,
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """
    Safely run a subprocess command with error handling.

    Replaces 15+ duplicate subprocess patterns.

    Args:
        command: Command to run (string or list)
        cwd: Working directory
        capture_output: Capture stdout/stderr
        check: Raise exception on non-zero return code
        timeout: Command timeout in seconds
        env: Environment variables

    Returns:
        CompletedProcess result
    """
    try:
        shell = bool(isinstance(command, str))

        return subprocess.run(
            command,
            shell=shell,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=check,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out: {command}")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {command}, return code: {e.returncode}")
        raise
    except Exception as e:
        logger.error(f"Error running command {command}: {e}")
        raise


def check_command_exists(command: str) -> bool:
    """
    Check if a command exists in the system PATH.

    Args:
        command: Command name to check

    Returns:
        True if command exists, False otherwise
    """
    try:
        result = run_command_safe(
            ["which", command] if sys.platform != "win32" else ["where", command],
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


# ==============================================================================
# ENVIRONMENT UTILITIES
# ==============================================================================


def get_env_bool(key: str, default: bool = False) -> bool:
    """
    Get boolean value from environment variable.

    Args:
        key: Environment variable key
        default: Default value if not set

    Returns:
        Boolean value
    """
    value = os.environ.get(key, "").lower()

    if not value:
        return default

    return value in ("1", "true", "yes", "on")


def get_env_int(key: str, default: int = 0) -> int:
    """
    Get integer value from environment variable.

    Args:
        key: Environment variable key
        default: Default value if not set or invalid

    Returns:
        Integer value
    """
    value = os.environ.get(key, "")

    if not value:
        return default

    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid integer value for {key}: {value}")
        return default


def get_env_list(
    key: str, separator: str = ",", default: Optional[List[str]] = None
) -> List[str]:
    """
    Get list from environment variable.

    Args:
        key: Environment variable key
        separator: List separator
        default: Default list if not set

    Returns:
        List of values
    """
    value = os.environ.get(key, "")

    if not value:
        return default or []

    return [item.strip() for item in value.split(separator) if item.strip()]


# ==============================================================================
# IMPORT UTILITIES
# ==============================================================================


def safe_import(module_name: str, fallback: Any = None) -> Any:
    """
    Safely import a module with fallback.

    Replaces 40+ duplicate import error handling patterns.

    Args:
        module_name: Module to import
        fallback: Fallback value if import fails

    Returns:
        Imported module or fallback
    """
    try:
        import importlib

        return importlib.import_module(module_name)
    except ImportError as e:
        logger.debug(f"Could not import {module_name}: {e}")
        return fallback
    except Exception as e:
        logger.error(f"Error importing {module_name}: {e}")
        return fallback


def import_from_string(import_path: str, fallback: Any = None) -> Any:
    """
    Import a class or function from a string path.

    Args:
        import_path: Full import path (e.g., "package.module.ClassName")
        fallback: Fallback value if import fails

    Returns:
        Imported object or fallback
    """
    try:
        module_path, attr_name = import_path.rsplit(".", 1)
        module = safe_import(module_path)

        if module is None:
            return fallback

        return getattr(module, attr_name, fallback)
    except (ValueError, AttributeError) as e:
        logger.debug(f"Could not import {import_path}: {e}")
        return fallback


# ==============================================================================
# DEPRECATION WARNINGS
# ==============================================================================


def deprecated(replacement: Optional[str] = None):
    """
    Decorator to mark functions as deprecated.

    Args:
        replacement: Suggested replacement function

    Returns:
        Decorated function
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            import warnings

            message = f"{func.__name__} is deprecated"
            if replacement:
                message += f", use {replacement} instead"

            warnings.warn(message, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator
