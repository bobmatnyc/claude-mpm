"""Metadata extraction and processing for framework files."""

import re
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from claude_mpm.core.logging_utils import get_logger


class MetadataProcessor:
    """Processes and extracts metadata from framework files and agents."""

    def __init__(self):
        """Initialize the metadata processor."""
        self.logger = get_logger("metadata_processor")

    def extract_metadata_from_content(self, content: str) -> Dict[str, Optional[str]]:
        """Extract metadata from content string.

        Args:
            content: Content to extract metadata from

        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            "version": None,
            "last_modified": None,
        }

        # Extract version
        version_match = re.search(r"<!-- FRAMEWORK_VERSION: (\d+) -->", content)
        if version_match:
            metadata["version"] = version_match.group(1)
            self.logger.debug(f"Extracted version: {metadata['version']}")

        # Extract timestamp
        timestamp_match = re.search(r"<!-- LAST_MODIFIED: ([^>]+) -->", content)
        if timestamp_match:
            metadata["last_modified"] = timestamp_match.group(1).strip()
            self.logger.debug(f"Extracted last_modified: {metadata['last_modified']}")

        return metadata

    def parse_agent_metadata(self, agent_file: Path) -> Optional[Dict[str, Any]]:
        """Parse agent metadata from deployed agent file.

        Args:
            agent_file: Path to deployed agent file

        Returns:
            Dictionary with agent metadata or None
        """
        try:
            with agent_file.open() as f:
                content = f.read()

            # Default values
            agent_data = {
                "id": agent_file.stem,
                "display_name": agent_file.stem.replace("_", " ")
                .replace("-", " ")
                .title(),
                "description": "Specialized agent",
                "file_path": str(agent_file),
                "file_mtime": agent_file.stat().st_mtime,
            }

            # Extract YAML frontmatter if present
            if content.startswith("---"):
                end_marker = content.find("---", 3)
                if end_marker > 0:
                    frontmatter = content[3:end_marker]
                    metadata = yaml.safe_load(frontmatter)
                    if metadata:
                        # Use name as ID for Task tool
                        agent_data["id"] = metadata.get("name", agent_data["id"])
                        agent_data["display_name"] = (
                            metadata.get("name", agent_data["display_name"])
                            .replace("-", " ")
                            .title()
                        )

                        # Copy all metadata fields directly
                        for key, value in metadata.items():
                            if key not in ["name"]:  # Skip already processed fields
                                agent_data[key] = value

                        # IMPORTANT: Do NOT add spaces to tools field - it breaks deployment!
                        # Tools must remain as comma-separated without spaces: "Read,Write,Edit"

            return agent_data

        except Exception as e:
            self.logger.debug(f"Could not parse metadata from {agent_file}: {e}")
            return None

    def extract_cache_metadata(self, data: Any, cache_key: str) -> Tuple[Any, float]:
        """Extract cache metadata for storage.

        Args:
            data: Data to cache
            cache_key: Cache key for identification

        Returns:
            Tuple of (data, timestamp) for cache storage
        """
        return data, time.time()

    def validate_cache_metadata(
        self,
        cached_data: Tuple[Any, float],
        file_path: Optional[Path] = None,
        ttl: float = 60.0,
    ) -> bool:
        """Validate cache metadata for freshness.

        Args:
            cached_data: Tuple of (data, timestamp) from cache
            file_path: Optional file path to check modification time
            ttl: Time-to-live in seconds

        Returns:
            True if cache is valid, False otherwise
        """
        try:
            _data, cache_time = cached_data
            current_time = time.time()

            # Check TTL
            if current_time - cache_time > ttl:
                return False

            # Check file modification time if provided
            if file_path and file_path.exists():
                file_mtime = file_path.stat().st_mtime
                if file_mtime > cache_time:
                    return False

            return True
        except Exception as e:
            self.logger.debug(f"Cache validation failed: {e}")
            return False
