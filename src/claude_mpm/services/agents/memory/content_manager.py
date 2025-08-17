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

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


class MemoryContentManager:
    """Manages memory content manipulation and validation.

    WHY: Memory content requires careful manipulation to maintain structure,
    enforce limits, and ensure consistency. This class centralizes all content
    manipulation logic.
    """

    REQUIRED_SECTIONS = [
        "Project Architecture",
        "Implementation Guidelines",
        "Common Mistakes to Avoid",
        "Current Technical Context",
    ]

    def __init__(self, memory_limits: Dict[str, Any]):
        """Initialize the content manager.

        Args:
            memory_limits: Dictionary containing memory limits configuration
        """
        self.memory_limits = memory_limits
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def add_item_to_section(self, content: str, section: str, new_item: str) -> str:
        """Add item to specified section, respecting limits.

        WHY: Each section has a maximum item limit to prevent information overload
        and maintain readability. When limits are reached, oldest items are removed
        to make room for new learnings (FIFO strategy).

        Args:
            content: Current memory file content
            section: Section name to add item to
            new_item: Item to add

        Returns:
            str: Updated content with new item added
        """
        lines = content.split("\n")
        section_start = None
        section_end = None

        # Find section boundaries
        for i, line in enumerate(lines):
            if line.startswith(f"## {section}"):
                section_start = i
            elif section_start is not None and line.startswith("## "):
                section_end = i
                break

        if section_start is None:
            # Section doesn't exist, add it
            return self._add_new_section(content, section, new_item)

        if section_end is None:
            section_end = len(lines)

        # Count existing items in section and find first item index
        item_count = 0
        first_item_index = None
        for i in range(section_start + 1, section_end):
            if lines[i].strip().startswith("- "):
                if first_item_index is None:
                    first_item_index = i
                item_count += 1

        # Check if we can add more items
        if item_count >= self.memory_limits["max_items_per_section"]:
            # Remove oldest item (first one) to make room
            if first_item_index is not None:
                lines.pop(first_item_index)
                section_end -= 1  # Adjust section end after removal

        # Add new item (find insertion point after any comments)
        insert_point = section_start + 1
        while insert_point < section_end and (
            not lines[insert_point].strip() or lines[insert_point].strip().startswith("<!--")
        ):
            insert_point += 1

        # Ensure line length limit (account for "- " prefix)
        max_item_length = self.memory_limits["max_line_length"] - 2  # Subtract 2 for "- " prefix
        if len(new_item) > max_item_length:
            new_item = new_item[: max_item_length - 3] + "..."

        lines.insert(insert_point, f"- {new_item}")

        # Update timestamp
        updated_content = "\n".join(lines)
        return self.update_timestamp(updated_content)

    def _add_new_section(self, content: str, section: str, new_item: str) -> str:
        """Add a new section with the given item.

        WHY: When agents discover learnings that don't fit existing sections,
        we need to create new sections dynamically while respecting the maximum
        section limit.

        Args:
            content: Current memory content
            section: New section name
            new_item: First item for the section

        Returns:
            str: Updated content with new section
        """
        lines = content.split("\n")

        # Count existing sections
        section_count = sum(1 for line in lines if line.startswith("## "))

        if section_count >= self.memory_limits["max_sections"]:
            self.logger.warning(f"Maximum sections reached, cannot add '{section}'")
            # Try to add to Recent Learnings instead
            return self.add_item_to_section(content, "Recent Learnings", new_item)

        # Find insertion point (before Recent Learnings or at end)
        insert_point = len(lines)
        for i, line in enumerate(lines):
            if line.startswith("## Recent Learnings"):
                insert_point = i
                break

        # Insert new section
        new_section = ["", f"## {section}", f"- {new_item}", ""]

        for j, line in enumerate(new_section):
            lines.insert(insert_point + j, line)

        return "\n".join(lines)

    def exceeds_limits(self, content: str, agent_limits: Optional[Dict[str, Any]] = None) -> bool:
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

    def truncate_to_limits(
        self, content: str, agent_limits: Optional[Dict[str, Any]] = None
    ) -> str:
        """Truncate content to fit within limits.

        WHY: When memory files exceed size limits, we need a strategy to reduce
        size while preserving the most important information. This implementation
        removes items from "Recent Learnings" first as they're typically less
        consolidated than other sections.

        Args:
            content: Content to truncate
            agent_limits: Optional agent-specific limits

        Returns:
            str: Truncated content within size limits
        """
        lines = content.split("\n")
        limits = agent_limits or self.memory_limits

        # Strategy: Remove items from Recent Learnings first
        while self.exceeds_limits("\n".join(lines), agent_limits):
            removed = False

            # First try Recent Learnings
            for i, line in enumerate(lines):
                if line.startswith("## Recent Learnings"):
                    # Find and remove first item in this section
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip().startswith("- "):
                            lines.pop(j)
                            removed = True
                            break
                        elif lines[j].startswith("## "):
                            break
                    break

            # If no Recent Learnings items, remove from other sections
            if not removed:
                # Remove from sections in reverse order (bottom up)
                for i in range(len(lines) - 1, -1, -1):
                    if lines[i].strip().startswith("- "):
                        lines.pop(i)
                        removed = True
                        break

            # Safety: If nothing removed, truncate from end
            if not removed:
                lines = lines[:-10]

        return "\n".join(lines)

    def update_timestamp(self, content: str) -> str:
        """Update the timestamp in the file header.

        Args:
            content: Content to update

        Returns:
            str: Content with updated timestamp
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return re.sub(
            r"<!-- Last Updated: .+ \| Auto-updated by: .+ -->",
            f"<!-- Last Updated: {timestamp} | Auto-updated by: system -->",
            content,
        )

    def validate_and_repair(self, content: str, agent_id: str) -> str:
        """Validate memory file and repair if needed.

        WHY: Memory files might be manually edited by developers or corrupted.
        This method ensures the file maintains required structure and sections.

        Args:
            content: Content to validate
            agent_id: Agent identifier

        Returns:
            str: Validated and repaired content
        """
        lines = content.split("\n")
        existing_sections = set()

        # Find existing sections
        for line in lines:
            if line.startswith("## "):
                section_name = line[3:].split("(")[0].strip()
                existing_sections.add(section_name)

        # Check for required sections
        missing_sections = []
        for required in self.REQUIRED_SECTIONS:
            if required not in existing_sections:
                missing_sections.append(required)

        if missing_sections:
            self.logger.info(f"Adding missing sections to {agent_id} memory: {missing_sections}")

            # Add missing sections before Recent Learnings
            insert_point = len(lines)
            for i, line in enumerate(lines):
                if line.startswith("## Recent Learnings"):
                    insert_point = i
                    break

            for section in missing_sections:
                section_content = ["", f"## {section}", "<!-- Section added by repair -->", ""]
                for j, line in enumerate(section_content):
                    lines.insert(insert_point + j, line)
                insert_point += len(section_content)

        return "\n".join(lines)

    def parse_memory_content_to_dict(self, content: str) -> Dict[str, List[str]]:
        """Parse memory content into structured dictionary format.

        WHY: Provides consistent parsing of memory content into sections and items
        for both display and programmatic access. This ensures the same parsing
        logic is used across the system.

        Args:
            content: Raw memory file content

        Returns:
            Dict mapping section names to lists of items
        """
        sections = {}
        current_section = None
        current_items = []

        for line in content.split("\n"):
            line = line.strip()

            # Skip empty lines and header information
            if not line or line.startswith("#") and "Memory Usage" in line:
                continue

            if line.startswith("## ") and not line.startswith("## Memory Usage"):
                # New section found
                if current_section and current_items:
                    sections[current_section] = current_items.copy()

                current_section = line[3:].strip()
                current_items = []

            elif line.startswith("- ") and current_section:
                # Item in current section
                item = line[2:].strip()
                if item and len(item) > 3:  # Filter out very short items
                    current_items.append(item)

        # Add final section
        if current_section and current_items:
            sections[current_section] = current_items

        return sections

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
            max_size_kb = self.memory_limits.get("max_file_size_kb", 8)

            if size_kb > max_size_kb:
                return False, f"Memory size {size_kb:.1f}KB exceeds limit of {max_size_kb}KB"

            # Check section count
            sections = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)
            max_sections = self.memory_limits.get("max_sections", 10)

            if len(sections) > max_sections:
                return False, f"Too many sections: {len(sections)} (max {max_sections})"

            # Check for required sections
            required = set(self.REQUIRED_SECTIONS)
            found = set(sections)
            missing = required - found

            if missing:
                return False, f"Missing required sections: {', '.join(missing)}"

            return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"
