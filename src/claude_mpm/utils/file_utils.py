#!/usr/bin/env python3
"""
File utilities for Claude MPM.

This module provides safe file operations with atomic writes,
error handling, and directory management.
"""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..core.exceptions import FileOperationError


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists

    Returns:
        Path object for the directory

    Raises:
        FileOperationError: If directory cannot be created
    """
    path = Path(path)
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except (OSError, PermissionError) as e:
        raise FileOperationError(
            f"Failed to create directory: {e}",
            context={
                "path": str(path),
                "operation": "mkdir",
                "error_type": type(e).__name__,
            },
        ) from e


def safe_read_file(path: Union[str, Path], encoding: str = "utf-8") -> str:
    """
    Safely read a file with error handling.

    Args:
        path: File path to read
        encoding: Text encoding to use

    Returns:
        File contents as string

    Raises:
        FileOperationError: If file cannot be read
    """
    path = Path(path)
    try:
        return path.read_text(encoding=encoding)
    except FileNotFoundError as e:
        raise FileOperationError(
            f"File not found: {path}",
            context={
                "path": str(path),
                "operation": "read",
                "encoding": encoding,
                "error_type": "FileNotFoundError",
            },
        ) from e
    except (OSError, PermissionError, UnicodeDecodeError) as e:
        raise FileOperationError(
            f"Failed to read file: {e}",
            context={
                "path": str(path),
                "operation": "read",
                "encoding": encoding,
                "error_type": type(e).__name__,
            },
        ) from e


def safe_write_file(
    path: Union[str, Path],
    content: str,
    encoding: str = "utf-8",
    create_dirs: bool = True,
) -> None:
    """
    Safely write content to a file with directory creation.

    Args:
        path: File path to write
        content: Content to write
        encoding: Text encoding to use
        create_dirs: Whether to create parent directories

    Raises:
        FileOperationError: If file cannot be written
    """
    path = Path(path)
    try:
        if create_dirs:
            ensure_directory(path.parent)
        path.write_text(content, encoding=encoding)
    except Exception as e:
        raise FileOperationError(f"Failed to write file {path}: {e}") from e


def atomic_write(
    path: Union[str, Path],
    content: str,
    encoding: str = "utf-8",
    create_dirs: bool = True,
) -> None:
    """
    Atomically write content to a file using a temporary file.

    This prevents corruption if the write operation is interrupted.

    Args:
        path: File path to write
        content: Content to write
        encoding: Text encoding to use
        create_dirs: Whether to create parent directories

    Raises:
        FileOperationError: If file cannot be written atomically
    """
    path = Path(path)
    try:
        if create_dirs:
            ensure_directory(path.parent)

        # Write to temporary file first
        with tempfile.NamedTemporaryFile(
            mode="w", encoding=encoding, dir=path.parent, delete=False, suffix=".tmp"
        ) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        # Atomically move temporary file to target
        shutil.move(temp_path, path)

    except Exception as e:
        # Clean up temporary file if it exists
        try:
            if "temp_path" in locals():
                Path(temp_path).unlink()
        except Exception:
            pass
        raise FileOperationError(f"Failed to atomically write file {path}: {e}") from e


def get_file_info(path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    Get file metadata safely.

    Args:
        path: File path to examine

    Returns:
        Dictionary with file information or None if file doesn't exist
    """
    path = Path(path)
    try:
        if not path.exists():
            return None

        stat = path.stat()
        return {
            "path": str(path),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "permissions": oct(stat.st_mode)[-3:],
        }
    except Exception:
        return None


def safe_copy_file(
    src: Union[str, Path], dst: Union[str, Path], create_dirs: bool = True
) -> None:
    """
    Safely copy a file with error handling.

    Args:
        src: Source file path
        dst: Destination file path
        create_dirs: Whether to create destination directories

    Raises:
        FileOperationError: If file cannot be copied
    """
    src = Path(src)
    dst = Path(dst)

    try:
        if not src.exists():
            raise FileOperationError(f"Source file does not exist: {src}")

        if create_dirs:
            ensure_directory(dst.parent)

        shutil.copy2(src, dst)

    except Exception as e:
        raise FileOperationError(f"Failed to copy {src} to {dst}: {e}") from e


def safe_remove_file(path: Union[str, Path]) -> bool:
    """
    Safely remove a file.

    Args:
        path: File path to remove

    Returns:
        True if file was removed, False if it didn't exist

    Raises:
        FileOperationError: If file cannot be removed
    """
    path = Path(path)
    try:
        if not path.exists():
            return False
        path.unlink()
        return True
    except Exception as e:
        raise FileOperationError(f"Failed to remove file {path}: {e}") from e


def read_json_file(path: Union[str, Path]) -> Any:
    """
    Read and parse a JSON file safely.

    Args:
        path: JSON file path

    Returns:
        Parsed JSON data

    Raises:
        FileOperationError: If file cannot be read or parsed
    """
    try:
        content = safe_read_file(path)
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise FileOperationError(f"Invalid JSON in file {path}: {e}") from e


def write_json_file(
    path: Union[str, Path], data: Any, indent: int = 2, atomic: bool = True
) -> None:
    """
    Write data to a JSON file safely.

    Args:
        path: JSON file path
        data: Data to serialize to JSON
        indent: JSON indentation level
        atomic: Whether to use atomic write

    Raises:
        FileOperationError: If file cannot be written
    """
    try:
        content = json.dumps(data, indent=indent, ensure_ascii=False)
        if atomic:
            atomic_write(path, content)
        else:
            safe_write_file(path, content)
    except Exception as e:
        raise FileOperationError(f"Failed to write JSON file {path}: {e}") from e


def backup_file(path: Union[str, Path], backup_suffix: str = ".backup") -> Path:
    """
    Create a backup copy of a file.

    Args:
        path: File path to backup
        backup_suffix: Suffix to add to backup filename

    Returns:
        Path to the backup file

    Raises:
        FileOperationError: If backup cannot be created
    """
    path = Path(path)
    backup_path = path.with_suffix(path.suffix + backup_suffix)

    try:
        safe_copy_file(path, backup_path)
        return backup_path
    except Exception as e:
        raise FileOperationError(f"Failed to create backup of {path}: {e}") from e
