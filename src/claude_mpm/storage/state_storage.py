from pathlib import Path

"""State Storage module for reliable state persistence.

This module provides atomic file operations and various serialization
formats for state data storage.

Design Principles:
- Atomic file operations (write-to-temp-then-rename)
- Multiple serialization formats (JSON, pickle, compressed)
- File locking for concurrent access safety
- Corruption detection and recovery
"""

import fcntl
import gzip
import hashlib
import json
import os
import pickle
import platform
import tempfile
import time
from contextlib import contextmanager, suppress
from typing import Any, Dict, Optional, Tuple, Union

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class StateStorage:
    """Reliable state storage with atomic operations."""

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize State Storage.

        Args:
            storage_dir: Directory for state storage (default: ~/.claude-mpm/storage)
        """
        self.storage_dir = storage_dir or Path.home() / ".claude-mpm" / "storage"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # File locking support (Unix-like systems)
        self.supports_locking = platform.system() != "Windows"

        # Statistics
        self.write_count = 0
        self.read_count = 0
        self.error_count = 0

    def write_json(
        self,
        data: Dict[str, Any],
        file_path: Union[str, Path],
        compress: bool = False,
        atomic: bool = True,
    ) -> bool:
        """Write data to JSON file atomically.

        Args:
            data: Data to serialize
            file_path: Target file path
            compress: Whether to compress with gzip
            atomic: Whether to use atomic write

        Returns:
            True if write successful
        """
        try:
            file_path = Path(file_path)

            if atomic:
                return self._atomic_write(
                    file_path, data, serializer="json", compress=compress
                )
            # Direct write (not atomic)
            if compress:
                with gzip.open(file_path, "wt", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)
            else:
                with file_path.open("w") as f:
                    json.dump(data, f, indent=2, default=str)

            self.write_count += 1
            return True

        except Exception as e:
            logger.error(f"Failed to write JSON to {file_path}: {e}")
            self.error_count += 1
            return False

    def read_json(
        self, file_path: Union[str, Path], compressed: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """Read data from JSON file.

        Args:
            file_path: Source file path
            compressed: Whether file is compressed (auto-detect if None)

        Returns:
            Deserialized data or None if read failed
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                logger.debug(f"File not found: {file_path}")
                return None

            # Auto-detect compression
            if compressed is None:
                compressed = file_path.suffix == ".gz"

            with self._file_lock(file_path, "r"):
                if compressed:
                    with gzip.open(file_path, "rt", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    with file_path.open() as f:
                        data = json.load(f)

            self.read_count += 1
            return data

        except Exception as e:
            logger.error(f"Failed to read JSON from {file_path}: {e}")
            self.error_count += 1
            return None

    def write_pickle(
        self,
        data: Any,
        file_path: Union[str, Path],
        compress: bool = False,
        atomic: bool = True,
    ) -> bool:
        """Write data to pickle file atomically.

        Args:
            data: Data to serialize
            file_path: Target file path
            compress: Whether to compress with gzip
            atomic: Whether to use atomic write

        Returns:
            True if write successful
        """
        try:
            file_path = Path(file_path)

            if atomic:
                return self._atomic_write(
                    file_path, data, serializer="pickle", compress=compress
                )
            # Direct write (not atomic)
            if compress:
                with gzip.open(file_path, "wb") as f:
                    pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            else:
                with file_path.open("wb") as f:
                    pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

            self.write_count += 1
            return True

        except Exception as e:
            logger.error(f"Failed to write pickle to {file_path}: {e}")
            self.error_count += 1
            return False

    def read_pickle(
        self, file_path: Union[str, Path], compressed: Optional[bool] = None
    ) -> Optional[Any]:
        """Read data from pickle file.

        Args:
            file_path: Source file path
            compressed: Whether file is compressed (auto-detect if None)

        Returns:
            Deserialized data or None if read failed
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                logger.debug(f"File not found: {file_path}")
                return None

            # Auto-detect compression
            if compressed is None:
                compressed = file_path.suffix == ".gz"

            with self._file_lock(file_path, "rb"):
                if compressed:
                    with gzip.open(file_path, "rb") as f:
                        data = pickle.load(f)
                else:
                    with file_path.open("rb") as f:
                        data = pickle.load(f)

            self.read_count += 1
            return data

        except Exception as e:
            logger.error(f"Failed to read pickle from {file_path}: {e}")
            self.error_count += 1
            return None

    def _atomic_write(
        self,
        file_path: Path,
        data: Any,
        serializer: str = "json",
        compress: bool = False,
    ) -> bool:
        """Perform atomic write operation.

        Args:
            file_path: Target file path
            data: Data to write
            serializer: Serialization format ('json' or 'pickle')
            compress: Whether to compress

        Returns:
            True if write successful
        """
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(
                dir=file_path.parent, prefix=f".{file_path.stem}_", suffix=".tmp"
            )

            try:
                # Write to temporary file
                if serializer == "json":
                    if compress:
                        with gzip.open(temp_path, "wt", encoding="utf-8") as f:
                            json.dump(data, f, indent=2, default=str)
                    else:
                        with os.fdopen(temp_fd, "w") as f:
                            json.dump(data, f, indent=2, default=str)
                elif serializer == "pickle":
                    if compress:
                        with gzip.open(temp_path, "wb") as f:
                            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
                    else:
                        with os.fdopen(temp_fd, "wb") as f:
                            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
                else:
                    raise ValueError(f"Unknown serializer: {serializer}")

                # Add checksum for integrity verification
                self._add_checksum(temp_path)

                # Atomic rename
                Path(temp_path).replace(file_path)

                self.write_count += 1
                logger.debug(f"Atomic write successful: {file_path}")
                return True

            finally:
                # Clean up temp file if it still exists
                if Path(temp_path).exists():
                    Path(temp_path).unlink()

        except Exception as e:
            logger.error(f"Atomic write failed for {file_path}: {e}")
            self.error_count += 1
            return False

    @contextmanager
    def _file_lock(self, file_path: Path, mode: str):
        """Context manager for file locking.

        Args:
            file_path: File to lock
            mode: File open mode

        Yields:
            Locked file handle
        """
        if not self.supports_locking:
            # No locking on Windows
            with Path(file_path).open(mode) as f:
                yield f
            return

        # Unix-like systems with fcntl
        f = None
        try:
            f = Path(file_path).open(mode)

            # Try to acquire lock (non-blocking)
            max_attempts = 50
            for attempt in range(max_attempts):
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(0.1)

            yield f

        finally:
            if f:
                with suppress(Exception):
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                f.close()

    def _add_checksum(self, file_path: Union[str, Path]) -> None:
        """Add checksum to file for integrity verification.

        Args:
            file_path: File to add checksum to
        """
        try:
            file_path = Path(file_path)

            # Calculate checksum
            hasher = hashlib.sha256()
            with file_path.open("rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)

            checksum = hasher.hexdigest()

            # Write checksum file
            checksum_path = file_path.with_suffix(file_path.suffix + ".sha256")
            with checksum_path.open("w") as f:
                f.write(checksum)

        except Exception as e:
            logger.warning(f"Could not add checksum: {e}")

    def verify_checksum(self, file_path: Union[str, Path]) -> bool:
        """Verify file checksum for integrity.

        Args:
            file_path: File to verify

        Returns:
            True if checksum valid or not present
        """
        try:
            file_path = Path(file_path)
            checksum_path = file_path.with_suffix(file_path.suffix + ".sha256")

            if not checksum_path.exists():
                return True  # No checksum to verify

            # Read expected checksum
            with checksum_path.open() as f:
                expected = f.read().strip()

            # Calculate actual checksum
            hasher = hashlib.sha256()
            with file_path.open("rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)

            actual = hasher.hexdigest()

            if actual != expected:
                logger.error(f"Checksum mismatch for {file_path}")
                return False

            return True

        except Exception as e:
            logger.warning(f"Could not verify checksum: {e}")
            return True  # Assume valid if can't verify

    def cleanup_temp_files(self) -> int:
        """Clean up temporary files in storage directory.

        Returns:
            Number of files cleaned up
        """
        try:
            cleaned = 0

            # Find temp files
            for temp_file in self.storage_dir.glob(".*_*.tmp"):
                try:
                    # Check if file is old (> 1 hour)
                    age = time.time() - temp_file.stat().st_mtime
                    if age > 3600:
                        temp_file.unlink()
                        cleaned += 1
                        logger.debug(f"Cleaned up temp file: {temp_file}")
                except Exception:
                    pass

            # Clean up orphaned checksum files
            for checksum_file in self.storage_dir.glob("*.sha256"):
                data_file = checksum_file.with_suffix("")
                if not data_file.exists():
                    checksum_file.unlink()
                    cleaned += 1

            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} temporary files")

            return cleaned

        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")
            return 0

    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage statistics and information.

        Returns:
            Dictionary containing storage info
        """
        try:
            # Calculate storage size
            total_size = 0
            file_count = 0

            for file_path in self.storage_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1

            # Find temp files
            temp_files = list(self.storage_dir.glob(".*_*.tmp"))

            return {
                "storage_directory": str(self.storage_dir),
                "total_files": file_count,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "temp_files": len(temp_files),
                "write_count": self.write_count,
                "read_count": self.read_count,
                "error_count": self.error_count,
                "supports_locking": self.supports_locking,
            }

        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {"storage_directory": str(self.storage_dir), "error": str(e)}


class StateCache:
    """In-memory cache for frequently accessed state data."""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        """Initialize State Cache.

        Args:
            max_size: Maximum number of cached items
            ttl_seconds: Time-to-live for cached items
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.access_count: Dict[str, int] = {}

        # Statistics
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.cache:
            self.misses += 1
            return None

        value, timestamp = self.cache[key]

        # Check TTL
        if time.time() - timestamp > self.ttl_seconds:
            del self.cache[key]
            del self.access_count[key]
            self.misses += 1
            return None

        self.hits += 1
        self.access_count[key] = self.access_count.get(key, 0) + 1
        return value

    def set(self, key: str, value: Any) -> None:
        """Set item in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        # Evict if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict_lru()

        self.cache[key] = (value, time.time())
        self.access_count[key] = 0

    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if not self.cache:
            return

        # Find LRU item
        lru_key = min(self.access_count.keys(), key=lambda k: self.access_count[k])

        del self.cache[lru_key]
        del self.access_count[lru_key]

    def clear(self) -> None:
        """Clear all cached items."""
        self.cache.clear()
        self.access_count.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary containing cache stats
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests,
        }
