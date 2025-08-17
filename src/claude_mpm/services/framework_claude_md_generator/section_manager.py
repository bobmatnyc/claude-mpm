"""
Section management for framework CLAUDE.md templates.

Manages section registration, ordering, and updates.
"""

from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional


class SectionManager:
    """Manages sections for framework CLAUDE.md generation."""

    def __init__(self):
        """Initialize section manager."""
        self.sections = OrderedDict()

    def register_section(
        self,
        name: str,
        generator: Callable[[Dict[str, Any]], str],
        data: Optional[Dict[str, Any]] = None,
    ):
        """
        Register a section generator.

        Args:
            name: Section name
            generator: Function that generates section content
            data: Optional data to pass to generator
        """
        self.sections[name] = (generator, data or {})

    def update_section(self, section_name: str, content: str) -> bool:
        """
        Update a specific section's generator to return custom content.

        Args:
            section_name: Name of section to update
            content: New content for the section

        Returns:
            bool: Success status
        """
        if section_name not in self.sections:
            return False

        # Create a lambda that returns the custom content
        self.sections[section_name] = (lambda data: content, {})
        return True

    def add_custom_section(
        self, section_name: str, content: str, after: Optional[str] = None
    ):
        """
        Add a custom section to the generator.

        Args:
            section_name: Name for the new section
            content: Content for the section
            after: Section name to insert after (None = append at end)
        """
        new_section = (lambda data: content, {})

        if after is None or after not in self.sections:
            self.sections[section_name] = new_section
        else:
            # Insert after specified section
            new_sections = OrderedDict()
            for key, value in self.sections.items():
                new_sections[key] = value
                if key == after:
                    new_sections[section_name] = new_section
            self.sections = new_sections

    def get_section_list(self) -> List[str]:
        """
        Get list of all section names in order.

        Returns:
            List of section names
        """
        return list(self.sections.keys())

    def get_sections(self) -> OrderedDict:
        """
        Get all sections.

        Returns:
            OrderedDict of section definitions
        """
        return self.sections

    def remove_section(self, section_name: str) -> bool:
        """
        Remove a section.

        Args:
            section_name: Name of section to remove

        Returns:
            bool: Success status
        """
        if section_name in self.sections:
            del self.sections[section_name]
            return True
        return False
