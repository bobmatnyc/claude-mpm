#!/usr/bin/env python3
"""
Memory Content Manager
=====================

Manages memory content manipulation, validation, and size enforcement.

This module provides:
- Content parsing and validation
- Section and item management
- Size limit enforcement and truncation
- Content repair and structure validation
"""

import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class MemoryContentManager:
    """Manages memory content manipulation and validation.

    WHY: Memory content requires careful manipulation to maintain structure,
    enforce limits, and ensure consistency. This class centralizes all content
    manipulation logic for simple list-based memories.
    """

    def __init__(self, memory_limits: Dict[str, Any]):
        """Initialize the content manager.

        Args:
            memory_limits: Dictionary containing memory limits configuration
        """
        self.memory_limits = memory_limits
        self.logger = logger  # Use the module-level logger

    def add_item_to_list(self, content: str, new_item: str) -> str:
        """Add item to memory list with deduplication.

        WHY: Simplified memory system uses a simple list format. We still use
        NLP-based similarity detection to prevent duplicate or highly similar
        items from cluttering the memory.

        Args:
            content: Current memory file content
            new_item: Item to add

        Returns:
            str: Updated content with new item added and duplicates removed
        """
        lines = content.split("\n")

        # Ensure line length limit (account for "- " prefix)
        max_item_length = (
            self.memory_limits["max_line_length"] - 2
        )  # Subtract 2 for "- " prefix
        if len(new_item) > max_item_length:
            new_item = new_item[: max_item_length - 3] + "..."

        # Find existing items and check for duplicates
        items_to_remove = []
        item_indices = []
        for i, line in enumerate(lines):
            if line.strip().startswith("- "):
                item_indices.append(i)
                existing_item = line.strip()[2:]  # Remove "- " prefix
                similarity = self._calculate_similarity(existing_item, new_item)

                # If highly similar (>80%), mark for removal
                if similarity > 0.8:
                    items_to_remove.append(i)
                    self.logger.debug(
                        f"Found similar item (similarity={similarity:.2f}): "
                        f"replacing '{existing_item[:50]}...' with '{new_item[:50]}...'"
                    )

        # Remove similar items (in reverse order to maintain indices)
        for idx in reversed(items_to_remove):
            lines.pop(idx)

        # Count remaining items
        item_count = sum(1 for line in lines if line.strip().startswith("- "))

        # Check if we need to remove oldest item due to limits
        max_items = self.memory_limits.get("max_items", 100)
        if item_count >= max_items:
            # Find and remove the first item (oldest)
            for i, line in enumerate(lines):
                if line.strip().startswith("- "):
                    lines.pop(i)
                    break

        # Add new item at the end of the list
        # Find the insertion point (after header and metadata, before any trailing empty lines)
        insert_point = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip():
                insert_point = i + 1
                break

        lines.insert(insert_point, f"- {new_item}")

        # Update timestamp
        updated_content = "\n".join(lines)
        return self.update_timestamp(updated_content)

    def add_item_to_section(self, content: str, section: str, new_item: str) -> str:
        """Legacy method for backward compatibility - delegates to add_item_to_list.

        Args:
            content: Current memory file content
            section: Section name (ignored in simple list format)
            new_item: Item to add

        Returns:
            str: Updated content with new item added
        """
        return self.add_item_to_list(content, new_item)

    def exceeds_limits(
        self, content: str, agent_limits: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if content exceeds size limits.

        Args:
            content: Content to check
            agent_limits: Optional agent-specific limits

        Returns:
            bool: True if content exceeds limits
        """
        # Use agent-specific limits if provided, otherwise use default
        limits = agent_limits or self.memory_limits
        size_kb = len(content.encode("utf-8")) / 1024
        return size_kb > limits["max_file_size_kb"]

    def truncate_simple_list(
        self, content: str, agent_limits: Optional[Dict[str, Any]] = None
    ) -> str:
        """Truncate simple list content to fit within limits.

        WHY: When memory files exceed size limits, we remove oldest items
        (from the beginning of the list) to maintain the most recent learnings.

        Args:
            content: Content to truncate
            agent_limits: Optional agent-specific limits

        Returns:
            str: Truncated content within size limits
        """
        lines = content.split("\n")
        limits = agent_limits or self.memory_limits

        # Strategy: Remove oldest items (from beginning) to keep recent ones
        while self.exceeds_limits("\n".join(lines), agent_limits):
            removed = False

            # Find and remove the first item (oldest)
            for i, line in enumerate(lines):
                if line.strip().startswith("- "):
                    lines.pop(i)
                    removed = True
                    break

            # Safety: If nothing removed, truncate from end
            if not removed:
                lines = lines[:-10]

        # Also check max_items limit
        max_items = limits.get("max_items", 100)
        item_count = sum(1 for line in lines if line.strip().startswith("- "))

        if item_count > max_items:
            # Remove oldest items to fit within max_items
            items_removed = 0
            target_removals = item_count - max_items

            i = 0
            while i < len(lines) and items_removed < target_removals:
                if lines[i].strip().startswith("- "):
                    lines.pop(i)
                    items_removed += 1
                else:
                    i += 1

        return "\n".join(lines)

    def truncate_to_limits(
        self, content: str, agent_limits: Optional[Dict[str, Any]] = None
    ) -> str:
        """Legacy method for backward compatibility - delegates to truncate_simple_list."""
        return self.truncate_simple_list(content, agent_limits)

    def update_timestamp(self, content: str) -> str:
        """Update the timestamp in the file header.

        Args:
            content: Content to update

        Returns:
            str: Content with updated timestamp
        """
        timestamp = datetime.now(timezone.utc).isoformat() + "Z"
        # Handle both old and new timestamp formats
        content = re.sub(
            r"<!-- Last Updated: .+? -->",
            f"<!-- Last Updated: {timestamp} -->",
            content,
        )
        # Also handle legacy format
        return re.sub(
            r"<!-- Last Updated: .+ \| Auto-updated by: .+ -->",
            f"<!-- Last Updated: {timestamp} -->",
            content,
        )

    def validate_and_repair(self, content: str, agent_id: str) -> str:
        """Validate memory file and repair if needed.

        WHY: Memory files might be manually edited by developers or corrupted.
        This method ensures the file maintains proper simple list structure.

        Args:
            content: Content to validate
            agent_id: Agent identifier

        Returns:
            str: Validated and repaired content
        """
        lines = content.split("\n")

        # Ensure proper header format
        has_header = False
        has_timestamp = False

        for _i, line in enumerate(lines[:5]):  # Check first 5 lines
            if line.startswith("# Agent Memory:"):
                has_header = True
            elif line.startswith("<!-- Last Updated:"):
                has_timestamp = True

        # Add missing header or timestamp
        if not has_header or not has_timestamp:
            from datetime import datetime

            new_lines = []

            if not has_header:
                new_lines.append(f"# Agent Memory: {agent_id}")
            else:
                # Keep existing header
                for line in lines:
                    if line.startswith("# "):
                        new_lines.append(line)
                        lines.remove(line)
                        break

            if not has_timestamp:
                new_lines.append(
                    f"<!-- Last Updated: {datetime.now(timezone.utc).isoformat()}Z -->"
                )
                new_lines.append("")
            else:
                # Keep existing timestamp
                for line in lines:
                    if line.startswith("<!-- Last Updated:"):
                        new_lines.append(line)
                        lines.remove(line)
                        break

            # Add remaining content
            for line in lines:
                if not line.startswith("# ") and not line.startswith(
                    "<!-- Last Updated:"
                ):
                    new_lines.append(line)

            return "\n".join(new_lines)

        return "\n".join(lines)

    def parse_memory_content_to_list(self, content: str) -> List[str]:
        """Parse memory content into a simple list format.

        WHY: Provides consistent parsing of memory content as a simple list
        for both display and programmatic access.

        Args:
            content: Raw memory file content

        Returns:
            List of memory items
        """
        items = []

        for line in content.split("\n"):
            line = line.strip()

            # Skip empty lines, headers, and metadata
            if not line or line.startswith(("#", "<!--")):
                continue

            if line.startswith("- "):
                # Item in list
                item = line[2:].strip()
                if item and len(item) > 3:  # Filter out very short items
                    items.append(item)

        return items

    def parse_memory_content_to_dict(self, content: str) -> Dict[str, List[str]]:
        """Legacy method for backward compatibility.

        Returns a dict with single key 'memories' containing all items.

        Args:
            content: Raw memory file content

        Returns:
            Dict with 'memories' key mapping to list of items
        """
        items = self.parse_memory_content_to_list(content)
        return {"memories": items}

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings using fuzzy matching.

        WHY: We use difflib's SequenceMatcher for lightweight NLP-based similarity
        detection. This avoids heavy ML dependencies while still providing effective
        duplicate detection. The algorithm finds the longest contiguous matching
        subsequences and calculates a ratio between 0 and 1.

        DESIGN DECISION: We normalize strings before comparison by:
        - Converting to lowercase for case-insensitive matching
        - Stripping whitespace to ignore formatting differences
        - This balances accuracy with performance for real-time deduplication

        Args:
            str1: First string to compare
            str2: Second string to compare

        Returns:
            float: Similarity score between 0 (completely different) and 1 (identical)
        """
        # Normalize strings for comparison
        str1_normalized = str1.lower().strip()
        str2_normalized = str2.lower().strip()

        # Handle exact matches quickly
        if str1_normalized == str2_normalized:
            return 1.0

        # Use SequenceMatcher for fuzzy matching
        # None as first param tells it to use automatic junk heuristic
        matcher = SequenceMatcher(None, str1_normalized, str2_normalized)
        similarity = matcher.ratio()

        # Additional check: if one string contains the other (substring match)
        # This catches cases where one item is a more detailed version of another
        if (
            len(str1_normalized) > 20
            and len(str2_normalized) > 20
            and (
                str1_normalized in str2_normalized or str2_normalized in str1_normalized
            )
        ):
            # Boost similarity for substring matches
            similarity = max(similarity, 0.85)

        return similarity

    def deduplicate_list(self, content: str) -> Tuple[str, int]:
        """Deduplicate items in the memory list using NLP similarity.

        WHY: Over time, memory lists can accumulate similar or duplicate items from
        different sessions. This method cleans up by removing similar items while
        preserving the most recent ones.

        Args:
            content: Current memory file content

        Returns:
            Tuple of (updated content, number of items removed)
        """
        lines = content.split("\n")

        # Collect all items in the list
        items = []
        item_indices = []
        for i, line in enumerate(lines):
            if line.strip().startswith("- "):
                items.append(line.strip()[2:])  # Remove "- " prefix
                item_indices.append(i)

        # Find duplicates using pairwise comparison
        duplicates_to_remove = set()
        for i in range(len(items)):
            if i in duplicates_to_remove:
                continue
            for j in range(i + 1, len(items)):
                if j in duplicates_to_remove:
                    continue
                similarity = self._calculate_similarity(items[i], items[j])
                if similarity > 0.8:
                    # Remove the older item (lower index)
                    duplicates_to_remove.add(i)
                    self.logger.debug(
                        f"Deduplicating: '{items[i][:50]}...' "
                        f"(keeping newer: '{items[j][:50]}...')"
                    )
                    break  # Move to next item

        # Remove duplicates (in reverse order to maintain indices)
        removed_count = len(duplicates_to_remove)
        for idx in sorted(duplicates_to_remove, reverse=True):
            lines.pop(item_indices[idx])

        return "\n".join(lines), removed_count

    def deduplicate_section(self, content: str, section: str) -> Tuple[str, int]:
        """Legacy method for backward compatibility - delegates to deduplicate_list.

        Args:
            content: Current memory file content
            section: Section name (ignored in simple list format)

        Returns:
            Tuple of (updated content, number of items removed)
        """
        return self.deduplicate_list(content)

    def validate_memory_size(self, content: str) -> tuple[bool, Optional[str]]:
        """Validate memory content size and structure.

        Args:
            content: Memory content to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check file size
            size_kb = len(content.encode("utf-8")) / 1024
            max_size_kb = self.memory_limits.get("max_file_size_kb", 80)

            if size_kb > max_size_kb:
                return (
                    False,
                    f"Memory size {size_kb:.1f}KB exceeds limit of {max_size_kb}KB",
                )

            # Check item count
            items = sum(
                1 for line in content.split("\n") if line.strip().startswith("- ")
            )
            max_items = self.memory_limits.get("max_items", 100)

            if items > max_items:
                return False, f"Too many items: {items} (max {max_items})"

            return True, None

        except Exception as e:
            return False, f"Validation error: {e!s}"
