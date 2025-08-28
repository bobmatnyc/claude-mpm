#!/usr/bin/env python3
"""Memory Format Service - Handles memory content formatting and parsing."""

import logging
import re
from datetime import datetime
from typing import Dict, List


class MemoryFormatService:
    """Service for memory content formatting and parsing."""

    def __init__(self):
        """Initialize the memory format service."""
        self.logger = logging.getLogger(__name__)

    def build_simple_memory_content(self, agent_id: str, items: List[str]) -> str:
        """Build memory content as a simple list with header and timestamp.

        Args:
            agent_id: Agent identifier for the header
            items: List of memory items

        Returns:
            Formatted memory content string
        """
        # Build header
        header = f"# {agent_id.title()} Agent Memory\n\n"
        header += f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        header += "## Learnings\n\n"

        # Build item list
        item_lines = []
        for item in items:
            # Clean and format each item
            item = item.strip()
            if item and not item.startswith("- "):
                item = f"- {item}"
            if item:
                item_lines.append(item)

        # Combine
        content = header + "\n".join(item_lines)
        if item_lines:
            content += "\n"

        return content

    def parse_memory_list(self, memory_content: str) -> List[str]:
        """Parse memory content into a simple list.

        Args:
            memory_content: Raw memory content

        Returns:
            List of memory items (without "- " prefix)
        """
        items = []
        lines = memory_content.split("\n")

        for line in lines:
            line = line.strip()
            # Skip headers, empty lines, and metadata
            if (
                not line
                or line.startswith(("#", "Last Updated:", "**"))
                or line == "---"
            ):
                continue

            # Extract list items
            if line.startswith("- "):
                item = line[2:].strip()
                if item:
                    items.append(item)
            elif line and not any(
                line.startswith(p) for p in ["#", "**", "Last Updated:", "---"]
            ):
                # Include non-list items that aren't headers
                items.append(line)

        return items

    def parse_memory_sections(self, memory_content: str) -> Dict[str, List[str]]:
        """Parse memory content into sections and items.

        Args:
            memory_content: Raw memory file content

        Returns:
            Dict mapping section names to lists of items
        """
        sections = {}
        current_section = None
        current_items = []

        for line in memory_content.split("\n"):
            # Check for section header (## Section Name)
            if line.startswith("## "):
                # Save previous section if exists
                if current_section and current_items:
                    sections[current_section] = current_items
                # Start new section
                current_section = line[3:].strip()
                current_items = []
            # Check for list item
            elif line.startswith("- ") and current_section:
                item = line[2:].strip()
                if item:
                    current_items.append(item)

        # Save last section
        if current_section and current_items:
            sections[current_section] = current_items

        return sections

    def clean_template_placeholders(
        self,
        content: str,
        preserve_structure: bool = False,
        agent_id: str = "agent",
    ) -> str:
        """Clean template placeholders from memory content.

        WHY: Default templates contain placeholder text that should be removed
        when adding real memories. This method cleans those placeholders while
        preserving any actual content.

        Args:
            content: Memory content to clean
            preserve_structure: If True, preserve empty sections
            agent_id: Agent ID for context

        Returns:
            Cleaned content string
        """
        if not content:
            return content

        # Patterns to remove
        placeholder_patterns = [
            r"\[Agent will add.*?\]",
            r"\[No .* yet\]",
            r"<!-- .* -->",
            r"No items yet.*",
            r"Memory items will be added.*",
            r"\*\*Note:.*?\*\*",
        ]

        cleaned = content
        for pattern in placeholder_patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.MULTILINE)

        if not preserve_structure:
            # Remove empty sections
            lines = []
            skip_empty = False
            for line in cleaned.split("\n"):
                if line.startswith("## "):
                    skip_empty = True
                    lines.append(line)
                elif line.strip() and skip_empty:
                    skip_empty = False
                    lines.append(line)
                elif not skip_empty:
                    lines.append(line)

            cleaned = "\n".join(lines)

        # Clean up multiple blank lines
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        return cleaned.strip()

    def clean_template_placeholders_list(self, items: List[str]) -> List[str]:
        """Clean template placeholders from a list of items.

        Args:
            items: List of items to clean

        Returns:
            Cleaned list of items
        """
        cleaned = []
        for item in items:
            # Skip placeholder items
            if any(
                pattern in item.lower()
                for pattern in [
                    "[agent will add",
                    "[no ",
                    "no items yet",
                    "memory items will be added",
                ]
            ):
                continue
            cleaned.append(item)
        return cleaned
