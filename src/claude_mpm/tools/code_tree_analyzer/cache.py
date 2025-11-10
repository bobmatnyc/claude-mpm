#!/usr/bin/env python3
"""
Cache Module
============

Handles caching of analyzed code tree results.

WHY: Caching prevents re-parsing files that haven't changed,
significantly improving performance for large codebases.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List

from ...core.logging_config import get_logger
from .models import CodeNode


class CacheManager:
    """Manages caching of code analysis results."""

    def __init__(self, cache_dir: Path):
        """Initialize cache manager.

        Args:
            cache_dir: Directory to store cache files
        """
        self.logger = get_logger(__name__)
        self.cache_dir = cache_dir
        self.cache: Dict[str, List[CodeNode]] = {}

    def get_file_hash(self, file_path: Path) -> str:
        """Get hash of file contents for caching.

        Args:
            file_path: Path to file

        Returns:
            MD5 hash of file contents
        """
        hasher = hashlib.md5()
        with file_path.open("rb") as f:
            hasher.update(f.read())
        return hasher.hexdigest()

    def get_cache_key(self, file_path: Path) -> str:
        """Generate cache key for a file.

        Args:
            file_path: Path to file

        Returns:
            Cache key string
        """
        file_hash = self.get_file_hash(file_path)
        return f"{file_path}:{file_hash}"

    def get(self, cache_key: str) -> List[CodeNode]:
        """Get cached nodes for a file.

        Args:
            cache_key: Cache key

        Returns:
            List of cached nodes or None if not cached
        """
        return self.cache.get(cache_key)

    def set(self, cache_key: str, nodes: List[CodeNode]) -> None:
        """Cache nodes for a file.

        Args:
            cache_key: Cache key
            nodes: List of nodes to cache
        """
        self.cache[cache_key] = nodes

    def load(self) -> None:
        """Load cache from disk."""
        cache_file = self.cache_dir / "code_tree_cache.json"
        if cache_file.exists():
            try:
                with cache_file.open() as f:
                    cache_data = json.load(f)
                    # Reconstruct CodeNode objects
                    for key, nodes_data in cache_data.items():
                        self.cache[key] = [
                            CodeNode(**node_data) for node_data in nodes_data
                        ]
                self.logger.info(f"Loaded cache with {len(self.cache)} entries")
            except Exception as e:
                self.logger.warning(f"Failed to load cache: {e}")

    def save(self) -> None:
        """Save cache to disk."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / "code_tree_cache.json"

        try:
            # Convert CodeNode objects to dictionaries
            cache_data = {}
            for key, nodes in self.cache.items():
                cache_data[key] = [
                    {
                        "file_path": n.file_path,
                        "node_type": n.node_type,
                        "name": n.name,
                        "line_start": n.line_start,
                        "line_end": n.line_end,
                        "complexity": n.complexity,
                        "has_docstring": n.has_docstring,
                        "decorators": n.decorators,
                        "parent": n.parent,
                        "language": n.language,
                        "signature": n.signature,
                    }
                    for n in nodes
                ]

            with cache_file.open("w") as f:
                json.dump(cache_data, f, indent=2)

            self.logger.info(f"Saved cache with {len(self.cache)} entries")
        except Exception as e:
            self.logger.warning(f"Failed to save cache: {e}")

    def clear(self) -> None:
        """Clear all cached data."""
        self.cache.clear()
