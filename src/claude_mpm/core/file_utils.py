"""Centralized file operation utilities for Claude MPM.

This module consolidates 150+ repeated file I/O patterns across the codebase,
providing safe, consistent, and error-handled file operations.
"""

import errno
import fcntl
import hashlib
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, List, Optional, Union

import yaml

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


# ==============================================================================
# PATH UTILITIES
# ==============================================================================


def ensure_directory(path: Union[str, Path], mode: int = 0o755) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Replaces the common pattern:
        os.makedirs(path, exist_ok=True)

    Args:
        path: Directory path
        mode: Directory permissions

    Returns:
        Path object for the directory
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True, mode=mode)
    return path


def ensure_parent_directory(filepath: Union[str, Path]) -> Path:
    """Ensure the parent directory of a file exists.

    Args:
        filepath: File path

    Returns:
        Path object for the parent directory
    """
    filepath = Path(filepath)
    return ensure_directory(filepath.parent)


def safe_path_join(*parts: Union[str, Path]) -> Path:
    """Safely join path components, preventing path traversal.

    Args:
        *parts: Path components to join

    Returns:
        Joined path

    Raises:
        ValueError: If path traversal is attempted
    """
    # Join the parts
    path = Path(*parts)

    # Resolve to absolute path and check for traversal
    resolved = path.resolve()
    base = Path(parts[0]).resolve()

    # Ensure the resolved path is under the base path
    try:
        resolved.relative_to(base)
    except ValueError:
        raise ValueError(f"Path traversal detected: {path}")

    return resolved


def is_safe_path(path: Union[str, Path], base_dir: Union[str, Path]) -> bool:
    """Check if a path is safe (no traversal outside base directory).

    Args:
        path: Path to check
        base_dir: Base directory that path should be under

    Returns:
        True if path is safe, False otherwise
    """
    try:
        path = Path(path).resolve()
        base = Path(base_dir).resolve()
        path.relative_to(base)
        return True
    except ValueError:
        return False


def get_relative_path(
    path: Union[str, Path], base: Optional[Union[str, Path]] = None
) -> Path:
    """Get relative path from base directory.

    Args:
        path: Path to make relative
        base: Base directory (defaults to current working directory)

    Returns:
        Relative path
    """
    path = Path(path)
    base = Path(base) if base else Path.cwd()

    try:
        return path.relative_to(base)
    except ValueError:
        # Path is not relative to base, return absolute path
        return path.absolute()


# ==============================================================================
# FILE READING OPERATIONS
# ==============================================================================


def safe_read(
    filepath: Union[str, Path],
    mode: str = "r",
    encoding: str = "utf-8",
    default: Any = None,
    max_size: Optional[int] = None,
) -> Union[str, bytes, Any]:
    """Safely read a file with error handling.

    Replaces the common pattern:
        with open(file, 'r') as f:
            content = f.read()

    Args:
        filepath: Path to file
        mode: Read mode ('r' for text, 'rb' for binary)
        encoding: Text encoding (ignored for binary mode)
        default: Default value if file doesn't exist or error occurs
        max_size: Maximum file size to read (bytes)

    Returns:
        File contents or default value
    """
    filepath = Path(filepath)

    # Check file exists
    if not filepath.exists():
        logger.debug(f"File not found: {filepath}")
        return default

    # Check file size if limit specified
    if max_size is not None:
        file_size = filepath.stat().st_size
        if file_size > max_size:
            logger.warning(
                f"File {filepath} exceeds size limit ({file_size} > {max_size})"
            )
            return default

    try:
        if "b" in mode:
            with open(filepath, mode) as f:
                return f.read()
        else:
            with open(filepath, mode, encoding=encoding) as f:
                return f.read()
    except (OSError, UnicodeDecodeError) as e:
        logger.error(f"Error reading file {filepath}: {e}")
        return default


def safe_read_lines(
    filepath: Union[str, Path],
    encoding: str = "utf-8",
    max_lines: Optional[int] = None,
    skip_empty: bool = False,
) -> List[str]:
    """Safely read lines from a file.

    Args:
        filepath: Path to file
        encoding: Text encoding
        max_lines: Maximum number of lines to read
        skip_empty: Skip empty lines

    Returns:
        List of lines (empty list on error)
    """
    filepath = Path(filepath)

    if not filepath.exists():
        return []

    try:
        with open(filepath, encoding=encoding) as f:
            lines = []
            for i, line in enumerate(f):
                if max_lines is not None and i >= max_lines:
                    break

                line = line.rstrip("\n")
                if skip_empty and not line.strip():
                    continue

                lines.append(line)

            return lines
    except (OSError, UnicodeDecodeError) as e:
        logger.error(f"Error reading lines from {filepath}: {e}")
        return []


def safe_read_json(
    filepath: Union[str, Path],
    default: Any = None,
    encoding: str = "utf-8",
) -> Any:
    """Safely read and parse a JSON file.

    Args:
        filepath: Path to JSON file
        default: Default value if file doesn't exist or is invalid
        encoding: Text encoding

    Returns:
        Parsed JSON data or default value
    """
    content = safe_read(filepath, encoding=encoding, default=None)

    if content is None:
        return default

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        return default


def safe_read_yaml(
    filepath: Union[str, Path],
    default: Any = None,
    encoding: str = "utf-8",
) -> Any:
    """Safely read and parse a YAML file.

    Args:
        filepath: Path to YAML file
        default: Default value if file doesn't exist or is invalid
        encoding: Text encoding

    Returns:
        Parsed YAML data or default value
    """
    content = safe_read(filepath, encoding=encoding, default=None)

    if content is None:
        return default

    try:
        return yaml.safe_load(content)
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in {filepath}: {e}")
        return default


# ==============================================================================
# FILE WRITING OPERATIONS
# ==============================================================================


def safe_write(
    filepath: Union[str, Path],
    content: Union[str, bytes],
    mode: str = "w",
    encoding: str = "utf-8",
    create_dirs: bool = True,
    backup: bool = False,
) -> bool:
    """Safely write content to a file with error handling.

    Args:
        filepath: Path to file
        content: Content to write
        mode: Write mode ('w' for text, 'wb' for binary)
        encoding: Text encoding (ignored for binary mode)
        create_dirs: Create parent directories if they don't exist
        backup: Create backup of existing file

    Returns:
        True if successful, False otherwise
    """
    filepath = Path(filepath)

    # Create parent directories if requested
    if create_dirs:
        ensure_parent_directory(filepath)

    # Create backup if requested and file exists
    if backup and filepath.exists():
        backup_path = filepath.with_suffix(filepath.suffix + ".backup")
        try:
            shutil.copy2(filepath, backup_path)
        except OSError as e:
            logger.warning(f"Failed to create backup of {filepath}: {e}")

    try:
        if "b" in mode:
            with open(filepath, mode) as f:
                f.write(content)
        else:
            with open(filepath, mode, encoding=encoding) as f:
                f.write(content)
        return True
    except OSError as e:
        logger.error(f"Error writing file {filepath}: {e}")
        return False


def atomic_write(
    filepath: Union[str, Path],
    content: Union[str, bytes],
    mode: str = "w",
    encoding: str = "utf-8",
) -> bool:
    """Atomically write content to a file.

    Writes to a temporary file and then moves it to the target path,
    ensuring the write is atomic (all-or-nothing).

    Args:
        filepath: Path to file
        content: Content to write
        mode: Write mode ('w' for text, 'wb' for binary)
        encoding: Text encoding (ignored for binary mode)

    Returns:
        True if successful, False otherwise
    """
    filepath = Path(filepath)
    ensure_parent_directory(filepath)

    # Create temporary file in same directory (for atomic rename)
    temp_fd, temp_path = tempfile.mkstemp(
        dir=filepath.parent, prefix=f".{filepath.name}.", suffix=".tmp"
    )

    try:
        # Write to temporary file
        with os.fdopen(temp_fd, mode) as f:
            if "b" in mode:
                f.write(content)
            else:
                f.write(content)

        # Atomic rename
        os.replace(temp_path, filepath)
        return True

    except OSError as e:
        logger.error(f"Error in atomic write to {filepath}: {e}")
        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except:
            pass
        return False


def safe_write_json(
    filepath: Union[str, Path],
    data: Any,
    indent: int = 2,
    encoding: str = "utf-8",
    atomic: bool = False,
) -> bool:
    """Safely write data to a JSON file.

    Args:
        filepath: Path to JSON file
        data: Data to serialize
        indent: JSON indentation
        encoding: Text encoding
        atomic: Use atomic write

    Returns:
        True if successful, False otherwise
    """
    try:
        content = json.dumps(data, indent=indent, ensure_ascii=False)
        if atomic:
            return atomic_write(filepath, content, encoding=encoding)
        return safe_write(filepath, content, encoding=encoding)
    except (TypeError, ValueError) as e:
        logger.error(f"Error serializing JSON for {filepath}: {e}")
        return False


def safe_write_yaml(
    filepath: Union[str, Path],
    data: Any,
    encoding: str = "utf-8",
    atomic: bool = False,
) -> bool:
    """Safely write data to a YAML file.

    Args:
        filepath: Path to YAML file
        data: Data to serialize
        encoding: Text encoding
        atomic: Use atomic write

    Returns:
        True if successful, False otherwise
    """
    try:
        content = yaml.safe_dump(data, default_flow_style=False, allow_unicode=True)
        if atomic:
            return atomic_write(filepath, content, encoding=encoding)
        return safe_write(filepath, content, encoding=encoding)
    except yaml.YAMLError as e:
        logger.error(f"Error serializing YAML for {filepath}: {e}")
        return False


def append_to_file(
    filepath: Union[str, Path],
    content: str,
    encoding: str = "utf-8",
    create: bool = True,
) -> bool:
    """Safely append content to a file.

    Args:
        filepath: Path to file
        content: Content to append
        encoding: Text encoding
        create: Create file if it doesn't exist

    Returns:
        True if successful, False otherwise
    """
    filepath = Path(filepath)

    if not filepath.exists() and not create:
        return False

    return safe_write(filepath, content, mode="a", encoding=encoding)


# ==============================================================================
# FILE OPERATIONS
# ==============================================================================


def safe_copy(
    source: Union[str, Path],
    destination: Union[str, Path],
    overwrite: bool = False,
    preserve_metadata: bool = True,
) -> bool:
    """Safely copy a file.

    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Overwrite if destination exists
        preserve_metadata: Preserve file metadata

    Returns:
        True if successful, False otherwise
    """
    source = Path(source)
    destination = Path(destination)

    if not source.exists():
        logger.error(f"Source file not found: {source}")
        return False

    if destination.exists() and not overwrite:
        logger.warning(f"Destination already exists: {destination}")
        return False

    try:
        ensure_parent_directory(destination)

        if preserve_metadata:
            shutil.copy2(source, destination)
        else:
            shutil.copy(source, destination)

        return True
    except OSError as e:
        logger.error(f"Error copying {source} to {destination}: {e}")
        return False


def safe_move(
    source: Union[str, Path],
    destination: Union[str, Path],
    overwrite: bool = False,
) -> bool:
    """Safely move a file.

    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Overwrite if destination exists

    Returns:
        True if successful, False otherwise
    """
    source = Path(source)
    destination = Path(destination)

    if not source.exists():
        logger.error(f"Source file not found: {source}")
        return False

    if destination.exists() and not overwrite:
        logger.warning(f"Destination already exists: {destination}")
        return False

    try:
        ensure_parent_directory(destination)
        shutil.move(str(source), str(destination))
        return True
    except OSError as e:
        logger.error(f"Error moving {source} to {destination}: {e}")
        return False


def safe_delete(
    filepath: Union[str, Path],
    missing_ok: bool = True,
) -> bool:
    """Safely delete a file.

    Args:
        filepath: File path to delete
        missing_ok: Don't error if file doesn't exist

    Returns:
        True if successful or file didn't exist, False on error
    """
    filepath = Path(filepath)

    if not filepath.exists():
        return missing_ok

    try:
        if filepath.is_dir():
            shutil.rmtree(filepath)
        else:
            filepath.unlink()
        return True
    except OSError as e:
        logger.error(f"Error deleting {filepath}: {e}")
        return False


def safe_rename(
    old_path: Union[str, Path],
    new_path: Union[str, Path],
    overwrite: bool = False,
) -> bool:
    """Safely rename a file or directory.

    Args:
        old_path: Current path
        new_path: New path
        overwrite: Overwrite if new path exists

    Returns:
        True if successful, False otherwise
    """
    old_path = Path(old_path)
    new_path = Path(new_path)

    if not old_path.exists():
        logger.error(f"Source path not found: {old_path}")
        return False

    if new_path.exists() and not overwrite:
        logger.warning(f"Destination already exists: {new_path}")
        return False

    try:
        old_path.rename(new_path)
        return True
    except OSError as e:
        logger.error(f"Error renaming {old_path} to {new_path}: {e}")
        return False


# ==============================================================================
# FILE LOCKING
# ==============================================================================


@contextmanager
def file_lock(filepath: Union[str, Path], timeout: float = 5.0):
    """Context manager for file locking.

    Args:
        filepath: Path to lock file
        timeout: Maximum time to wait for lock

    Yields:
        File handle with exclusive lock
    """
    filepath = Path(filepath)
    ensure_parent_directory(filepath)

    lock_file = filepath.with_suffix(filepath.suffix + ".lock")
    lock_handle = None

    try:
        import time

        start_time = time.time()

        while True:
            try:
                lock_handle = open(lock_file, "w")
                fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as e:
                if e.errno != errno.EAGAIN:
                    raise
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Could not acquire lock for {filepath}")
                time.sleep(0.1)

        yield lock_handle

    finally:
        if lock_handle:
            try:
                fcntl.flock(lock_handle, fcntl.LOCK_UN)
                lock_handle.close()
                lock_file.unlink(missing_ok=True)
            except:
                pass


# ==============================================================================
# FILE VALIDATION
# ==============================================================================


def validate_file(
    filepath: Union[str, Path],
    must_exist: bool = True,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    extensions: Optional[List[str]] = None,
) -> bool:
    """Validate a file meets specified criteria.

    Args:
        filepath: Path to file
        must_exist: File must exist
        min_size: Minimum file size in bytes
        max_size: Maximum file size in bytes
        extensions: Allowed file extensions

    Returns:
        True if file is valid, False otherwise
    """
    filepath = Path(filepath)

    # Check existence
    if must_exist and not filepath.exists():
        return False

    if not filepath.exists():
        return not must_exist

    # Check it's a file
    if not filepath.is_file():
        return False

    # Check size
    size = filepath.stat().st_size
    if min_size is not None and size < min_size:
        return False
    if max_size is not None and size > max_size:
        return False

    # Check extension
    if extensions and filepath.suffix not in extensions:
        return False

    return True


def get_file_hash(
    filepath: Union[str, Path],
    algorithm: str = "sha256",
) -> Optional[str]:
    """Calculate hash of a file.

    Args:
        filepath: Path to file
        algorithm: Hash algorithm (sha256, md5, etc.)

    Returns:
        Hex digest of file hash or None on error
    """
    filepath = Path(filepath)

    if not filepath.exists():
        return None

    try:
        hasher = hashlib.new(algorithm)
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except OSError as e:
        logger.error(f"Error hashing {filepath}: {e}")
        return None


def find_files(
    directory: Union[str, Path],
    pattern: str = "*",
    recursive: bool = True,
    file_only: bool = True,
) -> List[Path]:
    """Find files matching a pattern.

    Args:
        directory: Directory to search
        pattern: Glob pattern
        recursive: Search recursively
        file_only: Return only files (not directories)

    Returns:
        List of matching paths
    """
    directory = Path(directory)

    if not directory.exists():
        return []

    if recursive:
        paths = directory.rglob(pattern)
    else:
        paths = directory.glob(pattern)

    if file_only:
        return [p for p in paths if p.is_file()]
    return list(paths)
