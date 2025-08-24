"""Path operations and validation utilities.

This module provides a centralized PathOperations class for common path validation
and file operations, reducing code duplication across the codebase.
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Callable, List, Optional, Union

logger = logging.getLogger(__name__)


class PathOperations:
    """Utility class for path validation and safe file operations."""

    def __init__(self, default_encoding: str = "utf-8"):
        """Initialize PathOperations with default encoding.

        Args:
            default_encoding: Default encoding for file operations
        """
        self.default_encoding = default_encoding

    # Path Validation Methods

    def validate_exists(self, path: Union[str, Path]) -> bool:
        """Check if path exists.

        Args:
            path: Path to validate

        Returns:
            True if path exists, False otherwise
        """
        try:
            return Path(path).exists()
        except Exception as e:
            logger.error(f"Error checking path existence: {e}")
            return False

    def validate_is_file(self, path: Union[str, Path]) -> bool:
        """Check if path is a file.

        Args:
            path: Path to validate

        Returns:
            True if path is a file, False otherwise
        """
        try:
            return Path(path).is_file()
        except Exception as e:
            logger.error(f"Error checking if path is file: {e}")
            return False

    def validate_is_dir(self, path: Union[str, Path]) -> bool:
        """Check if path is a directory.

        Args:
            path: Path to validate

        Returns:
            True if path is a directory, False otherwise
        """
        try:
            return Path(path).is_dir()
        except Exception as e:
            logger.error(f"Error checking if path is directory: {e}")
            return False

    def validate_readable(self, path: Union[str, Path]) -> bool:
        """Check if path has read permissions.

        Args:
            path: Path to validate

        Returns:
            True if path is readable, False otherwise
        """
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                return False
            return os.access(str(path_obj), os.R_OK)
        except Exception as e:
            logger.error(f"Error checking read permissions: {e}")
            return False

    def validate_writable(self, path: Union[str, Path]) -> bool:
        """Check if path has write permissions.

        Args:
            path: Path to validate

        Returns:
            True if path is writable, False otherwise
        """
        try:
            path_obj = Path(path)
            if path_obj.exists():
                return os.access(str(path_obj), os.W_OK)
            # Check parent directory for new files
            parent = path_obj.parent
            return parent.exists() and os.access(str(parent), os.W_OK)
        except Exception as e:
            logger.error(f"Error checking write permissions: {e}")
            return False

    # Safe File Operations

    def safe_read(
        self,
        path: Union[str, Path],
        encoding: Optional[str] = None,
        default: Optional[str] = None,
    ) -> Optional[str]:
        """Read file with error handling.

        Args:
            path: Path to read
            encoding: File encoding (uses default if None)
            default: Default value if read fails

        Returns:
            File contents or default value
        """
        encoding = encoding or self.default_encoding
        try:
            path_obj = Path(path)
            if not self.validate_readable(path_obj):
                logger.warning(f"File not readable: {path}")
                return default

            with open(path_obj, encoding=encoding) as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            return default

    def safe_write(
        self,
        path: Union[str, Path],
        content: str,
        encoding: Optional[str] = None,
        backup: bool = False,
        atomic: bool = False,
    ) -> bool:
        """Write file with error handling and optional backup.

        Args:
            path: Path to write
            content: Content to write
            encoding: File encoding (uses default if None)
            backup: Create backup before writing
            atomic: Use atomic write (write to temp file and move)

        Returns:
            True if write successful, False otherwise
        """
        encoding = encoding or self.default_encoding
        path_obj = Path(path)

        try:
            # Create backup if requested
            if backup and path_obj.exists():
                backup_path = path_obj.with_suffix(path_obj.suffix + ".bak")
                shutil.copy2(str(path_obj), str(backup_path))
                logger.info(f"Created backup: {backup_path}")

            # Ensure parent directory exists
            path_obj.parent.mkdir(parents=True, exist_ok=True)

            if atomic:
                # Atomic write: write to temp file then move
                with tempfile.NamedTemporaryFile(
                    mode="w", encoding=encoding, dir=path_obj.parent, delete=False
                ) as tmp_file:
                    tmp_file.write(content)
                    tmp_path = tmp_file.name

                # Move temp file to target
                shutil.move(tmp_path, str(path_obj))
            else:
                # Direct write
                with open(path_obj, "w", encoding=encoding) as f:
                    f.write(content)

            logger.info(f"Successfully wrote to {path}")
            return True

        except Exception as e:
            logger.error(f"Error writing file {path}: {e}")
            return False

    def safe_delete(
        self, path: Union[str, Path], confirm: Optional[Callable[[], bool]] = None
    ) -> bool:
        """Delete file/directory with optional confirmation.

        Args:
            path: Path to delete
            confirm: Optional confirmation callback

        Returns:
            True if delete successful, False otherwise
        """
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                logger.warning(f"Path does not exist: {path}")
                return True

            # Confirm if callback provided
            if confirm and not confirm():
                logger.info(f"Delete cancelled by user: {path}")
                return False

            if path_obj.is_file():
                path_obj.unlink()
            else:
                shutil.rmtree(str(path_obj))

            logger.info(f"Successfully deleted: {path}")
            return True

        except Exception as e:
            logger.error(f"Error deleting {path}: {e}")
            return False

    def safe_copy(
        self, src: Union[str, Path], dst: Union[str, Path], overwrite: bool = False
    ) -> bool:
        """Copy file/directory with overwrite protection.

        Args:
            src: Source path
            dst: Destination path
            overwrite: Allow overwriting existing files

        Returns:
            True if copy successful, False otherwise
        """
        try:
            src_path = Path(src)
            dst_path = Path(dst)

            if not src_path.exists():
                logger.error(f"Source does not exist: {src}")
                return False

            if dst_path.exists() and not overwrite:
                logger.error(f"Destination exists and overwrite=False: {dst}")
                return False

            # Ensure parent directory exists
            dst_path.parent.mkdir(parents=True, exist_ok=True)

            if src_path.is_file():
                shutil.copy2(str(src_path), str(dst_path))
            else:
                if dst_path.exists():
                    shutil.rmtree(str(dst_path))
                shutil.copytree(str(src_path), str(dst_path))

            logger.info(f"Successfully copied {src} to {dst}")
            return True

        except Exception as e:
            logger.error(f"Error copying {src} to {dst}: {e}")
            return False

    # Common Patterns

    def ensure_dir(self, path: Union[str, Path]) -> bool:
        """Create directory if it doesn't exist.

        Args:
            path: Directory path to ensure

        Returns:
            True if directory exists or was created, False otherwise
        """
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Error creating directory {path}: {e}")
            return False

    def get_size(self, path: Union[str, Path]) -> int:
        """Get size of file or directory in bytes.

        Args:
            path: Path to measure

        Returns:
            Size in bytes, or -1 on error
        """
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                return -1

            if path_obj.is_file():
                return path_obj.stat().st_size
            # Calculate total size for directory
            total = 0
            for item in path_obj.rglob("*"):
                if item.is_file():
                    total += item.stat().st_size
            return total

        except Exception as e:
            logger.error(f"Error getting size of {path}: {e}")
            return -1

    def list_files(
        self,
        path: Union[str, Path],
        pattern: str = "*",
        recursive: bool = False,
        include_dirs: bool = False,
    ) -> List[Path]:
        """List files in directory with filtering.

        Args:
            path: Directory path
            pattern: Glob pattern for filtering
            recursive: Search recursively
            include_dirs: Include directories in results

        Returns:
            List of matching paths
        """
        try:
            path_obj = Path(path)
            if not path_obj.is_dir():
                logger.error(f"Not a directory: {path}")
                return []

            items = path_obj.rglob(pattern) if recursive else path_obj.glob(pattern)

            results = []
            for item in items:
                if item.is_file() or (include_dirs and item.is_dir()):
                    results.append(item)

            return sorted(results)

        except Exception as e:
            logger.error(f"Error listing files in {path}: {e}")
            return []


# Convenience instance for direct imports
path_ops = PathOperations()
