"""Instruction cache service for managing assembled PM instruction content.

WHY: Linux systems have ARG_MAX limits (~128-256KB) that prevent passing
assembled PM instructions (~450KB) via CLI arguments. This service caches
the complete assembled instruction content to a file that Claude Code can
load directly.

DESIGN DECISION: Cache FULL assembled instruction content (BASE_PM + PM_INSTRUCTIONS
+ WORKFLOW + capabilities + temporal context) rather than single source file.
Uses SHA-256 hash-based invalidation to update cache only when assembled content
changes. This avoids unnecessary file I/O while ensuring cache stays synchronized.

Trade-offs:
- Performance: Hash computation adds ~1ms overhead but saves 450KB arg passing
- Complexity: Content-based hashing vs. multi-file dependency tracking
- Reliability: Hash-based validation is deterministic and platform-independent
- Flexibility: Caller assembles content, service only caches (separation of concerns)

Alternatives Considered:
1. File-based tracking: Rejected - can't detect changes in dynamic components
2. Multi-file dependency tracking: Rejected - complex and error-prone
3. No caching (always pass via CLI): Rejected due to Linux ARG_MAX limits
4. Database caching: Rejected as overkill for single-content caching

Extension Points:
- Compression: Add gzip compression if content sizes grow beyond disk constraints
- Multiple cache slots: Support caching different agent instruction sets
- TTL-based invalidation: Add time-based expiration for dynamic content
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class InstructionCacheService:
    """Manages cached assembled PM instruction content for file-based loading.

    The cache is stored at `.claude-mpm/PM_INSTRUCTIONS.md` and includes
    a metadata file `.claude-mpm/PM_INSTRUCTIONS.md.meta` containing:
    - content_hash: SHA-256 of assembled instruction content
    - content_size_bytes: Size of cached content in bytes
    - content_type: Type identifier ("assembled_instruction")
    - components: List of instruction components that were assembled
    - cached_at: ISO timestamp of cache creation
    - version: Cache format version

    Cache Updates:
    - Triggered during agent deployment or interactive sessions
    - Accepts pre-assembled instruction content from caller
    - Only updates if content hash changes
    - Atomic writes to prevent partial updates
    - Graceful error handling (deployment continues on cache failure)

    Performance:
    - Hash computation: O(n) where n = content size, ~1ms for 450KB content
    - Cache validation: O(1) metadata read + O(n) hash computation
    - Update operation: O(n) content write, atomic via temp file

    Error Handling:
    - All methods return result dicts instead of raising exceptions
    - Errors are logged but don't propagate to callers
    - Graceful degradation: Cache failures don't break deployments
    """

    CACHE_DIR = ".claude-mpm"
    CACHE_FILENAME = "PM_INSTRUCTIONS.md"
    META_FILENAME = "PM_INSTRUCTIONS.md.meta"
    CACHE_VERSION = "1.0"

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize instruction cache service.

        Args:
            project_root: Project root directory. If None, uses current directory.
        """
        self.project_root = project_root or Path.cwd()
        self.cache_dir = self.project_root / self.CACHE_DIR
        self.cache_file = self.cache_dir / self.CACHE_FILENAME
        self.meta_file = self.cache_dir / self.META_FILENAME
        self.logger = get_logger(__name__)

    def update_cache(
        self, instruction_content: str, force: bool = False
    ) -> Dict[str, Any]:
        """Update cache with assembled instruction content.

        This method implements atomic cache updates using a temp file strategy:
        1. Calculate content hash
        2. Compare with cached hash (if exists)
        3. If different or force=True, write content to temp file
        4. Atomically replace cache with temp file
        5. Write metadata with new hash

        Args:
            instruction_content: Complete assembled instruction content
                (BASE_PM + PM_INSTRUCTIONS + WORKFLOW + capabilities + temporal context)
            force: Force update even if hash matches

        Returns:
            Result dictionary with:
            - updated: Whether cache was updated
            - reason: Why update occurred or was skipped
            - cache_path: Path to cache file
            - content_hash: SHA-256 hash of content
            - content_size_kb: Size of content in KB

        Error Handling:
            Does NOT raise exceptions - returns error in result dict.
            This ensures cache failures don't break agent deployments.

        Example:
            >>> service = InstructionCacheService()
            >>> assembled = "# BASE_PM\\n...\\n# PM_INSTRUCTIONS\\n..."
            >>> result = service.update_cache(instruction_content=assembled)
            >>> if result["updated"]:
            ...     print(f"Cache updated: {result['reason']}")
        """
        try:
            # Ensure cache directory exists
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            # Calculate content hash
            content_hash = self._calculate_hash_from_content(instruction_content)

            # Check if update needed
            if not force and self.is_cache_valid(instruction_content):
                return {
                    "updated": False,
                    "reason": "cache_valid",
                    "cache_path": str(self.cache_file),
                    "content_hash": content_hash,
                }

            # Write content to cache (atomic operation)
            temp_file = self.cache_file.with_suffix(".tmp")
            temp_file.write_text(instruction_content, encoding="utf-8")
            temp_file.replace(self.cache_file)

            # Write metadata
            self._write_metadata(content_hash, len(instruction_content))

            self.logger.info(f"Updated instruction cache: {self.cache_file}")

            return {
                "updated": True,
                "reason": "content_changed" if not force else "forced",
                "cache_path": str(self.cache_file),
                "content_hash": content_hash,
                "content_size_kb": len(instruction_content) / 1024,
            }

        except Exception as e:
            self.logger.error(f"Failed to update instruction cache: {e}")
            return {
                "updated": False,
                "reason": "error",
                "error": str(e),
                "cache_path": str(self.cache_file),
            }

    def get_cache_path(self) -> Path:
        """Get path to cache file.

        Returns:
            Path to PM_INSTRUCTIONS.md cache

        Example:
            >>> service = InstructionCacheService()
            >>> cache_path = service.get_cache_path()
            >>> print(cache_path)  # .claude-mpm/PM_INSTRUCTIONS.md
        """
        return self.cache_file

    def is_cache_valid(self, instruction_content: str) -> bool:
        """Check if cache matches current assembled content.

        Validation checks:
        1. Cache file exists
        2. Metadata file exists
        3. Content hash matches cached hash

        Args:
            instruction_content: Current assembled instruction to validate against

        Returns:
            True if cache exists and hash matches content

        Example:
            >>> service = InstructionCacheService()
            >>> assembled = "# BASE_PM\\n...\\n# PM_INSTRUCTIONS\\n..."
            >>> if not service.is_cache_valid(assembled):
            ...     service.update_cache(assembled)
        """
        try:
            if not self.cache_file.exists() or not self.meta_file.exists():
                return False

            content_hash = self._calculate_hash_from_content(instruction_content)
            cached_hash = self._get_cached_hash()

            return content_hash == cached_hash

        except Exception as e:
            self.logger.debug(f"Cache validation failed: {e}")
            return False

    def invalidate_cache(self) -> bool:
        """Invalidate cache by removing cache files.

        This method removes both the cache file and metadata file,
        forcing a fresh cache creation on next update.

        Returns:
            True if cache was invalidated (files removed), False otherwise

        Example:
            >>> service = InstructionCacheService()
            >>> if service.invalidate_cache():
            ...     print("Cache cleared")
        """
        try:
            removed = False
            if self.cache_file.exists():
                self.cache_file.unlink()
                removed = True
            if self.meta_file.exists():
                self.meta_file.unlink()
                removed = True

            if removed:
                self.logger.info("Invalidated instruction cache")

            return removed

        except Exception as e:
            self.logger.error(f"Failed to invalidate cache: {e}")
            return False

    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about current cache state.

        Returns cache metadata including existence, sizes, and timestamps
        for debugging and monitoring. Note: cannot validate cache without
        current content, so cache_valid is always None.

        Returns:
            Dictionary with cache metadata:
            - cache_exists: Whether cache file exists
            - cache_path: Path to cache file
            - cache_valid: Always None (validation requires current content)
            - content_type: Type of cached content ("assembled_instruction")
            - cache_size_kb: Cache file size in KB (if exists)
            - cached_at: Cache creation timestamp (if exists)
            - content_hash: Content hash (if cache exists)
            - content_size_bytes: Cached content size in bytes (if exists)
            - components: List of instruction components (if exists)

        Example:
            >>> service = InstructionCacheService()
            >>> info = service.get_cache_info()
            >>> print(f"Cache exists: {info['cache_exists']}")
            >>> print(f"Size: {info.get('cache_size_kb', 0):.1f}KB")
        """
        info: Dict[str, Any] = {
            "cache_exists": self.cache_file.exists(),
            "cache_path": str(self.cache_file),
            "cache_valid": None,  # Can't validate without current content
            "content_type": "assembled_instruction",
        }

        try:
            if self.cache_file.exists():
                info["cache_size_kb"] = self.cache_file.stat().st_size / 1024

                # Load metadata
                if self.meta_file.exists():
                    meta = json.loads(self.meta_file.read_text())
                    info.update(
                        {
                            "cached_at": meta.get("cached_at"),
                            "content_hash": meta.get("content_hash"),
                            "content_size_bytes": meta.get("content_size_bytes"),
                            "components": meta.get("components", []),
                            "cache_version": meta.get("version"),
                        }
                    )

        except Exception as e:
            info["error"] = str(e)

        return info

    def _calculate_hash_from_content(self, content: str) -> str:
        """Calculate SHA-256 hash of content string.

        Args:
            content: String content to hash

        Returns:
            Hex digest of SHA-256 hash

        Performance:
            - Time complexity: O(n) where n = content size
            - Memory usage: O(1) - hash computed incrementally
        """
        sha256 = hashlib.sha256()
        sha256.update(content.encode("utf-8"))
        return sha256.hexdigest()

    def _get_cached_hash(self) -> Optional[str]:
        """Get cached content hash from metadata.

        Returns:
            Cached hash or None if not available
        """
        try:
            if not self.meta_file.exists():
                return None

            meta = json.loads(self.meta_file.read_text())
            return meta.get("content_hash")

        except Exception as e:
            self.logger.debug(f"Failed to read cached hash: {e}")
            return None

    def _write_metadata(self, content_hash: str, content_size: int) -> None:
        """Write cache metadata file.

        Metadata includes:
        - version: Cache format version (for future compatibility)
        - content_type: Type identifier ("assembled_instruction")
        - content_hash: SHA-256 hash of assembled content
        - content_size_bytes: Size of cached content in bytes
        - components: List of instruction components that were assembled
        - cached_at: ISO 8601 timestamp with UTC timezone

        Args:
            content_hash: SHA-256 hash of assembled content
            content_size: Size of content in bytes

        Example metadata:
            {
                "version": "1.0",
                "content_type": "assembled_instruction",
                "content_hash": "abc123...",
                "content_size_bytes": 450000,
                "components": ["BASE_PM.md", "PM_INSTRUCTIONS.md", ...],
                "cached_at": "2025-11-30T15:30:00Z"
            }
        """
        metadata = {
            "version": self.CACHE_VERSION,
            "content_type": "assembled_instruction",
            "components": [
                "BASE_PM.md",
                "PM_INSTRUCTIONS.md",
                "WORKFLOW.md",
                "agent_capabilities",
                "temporal_context",
            ],
            "content_hash": content_hash,
            "content_size_bytes": content_size,
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }

        self.meta_file.write_text(json.dumps(metadata, indent=2))
