from pathlib import Path

"""
Framework INSTRUCTIONS.md Generator Service

This service provides structured generation of the framework INSTRUCTIONS.md template
(legacy: CLAUDE.md) with auto-versioning, section management, and deployment capabilities.
"""

from typing import Any, Dict, List, Optional, Tuple

from .content_assembler import ContentAssembler
from .content_validator import ContentValidator
from .deployment_manager import DeploymentManager
from .section_generators import section_registry
from .section_manager import SectionManager
from .version_manager import VersionManager


class FrameworkClaudeMdGenerator:
    """
    Generates and manages the framework INSTRUCTIONS.md template (legacy: CLAUDE.md)
    with structured sections, auto-versioning, and deployment capabilities.

    This is the main facade class that coordinates all the submodules.
    """

    def __init__(self, target_filename: str = "INSTRUCTIONS.md"):
        """
        Initialize the generator with current framework version.

        Args:
            target_filename: Target filename for deployment (default: "INSTRUCTIONS.md")
                           Can be set to "CLAUDE.md" for legacy compatibility
        """
        # Initialize managers
        self.version_manager = VersionManager()
        self.validator = ContentValidator()
        self.assembler = ContentAssembler()
        self.section_manager = SectionManager()

        # Initialize deployment manager with dependencies
        self.deployment_manager = DeploymentManager(
            self.version_manager, self.validator, target_filename=target_filename
        )

        # Get framework version
        self.framework_version = self.version_manager.framework_version

        # Initialize sections
        self._initialize_sections()

    def _initialize_sections(self):
        """Initialize all sections in the required order."""
        # Register all default sections with their generators
        section_order = [
            "header",
            "role_designation",
            "agents",
            "todo_task_tools",
            "claude_pm_init",
            "orchestration_principles",
            "subprocess_validation",
            "delegation_constraints",
            "environment_config",
            "troubleshooting",
            "core_responsibilities",
            "footer",
        ]

        for section_name in section_order:
            generator_class = section_registry.get(section_name)
            if generator_class:
                generator_instance = generator_class(self.framework_version)
                self.section_manager.register_section(
                    section_name, generator_instance.generate
                )

    def generate(
        self,
        current_content: Optional[str] = None,
        template_variables: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Generate the complete INSTRUCTIONS.md/CLAUDE.md content.

        Args:
            current_content: Current INSTRUCTIONS.md/CLAUDE.md content for version parsing
            template_variables: Variables to substitute in the template

        Returns:
            str: Complete INSTRUCTIONS.md/CLAUDE.md content
        """
        # Auto-increment version if current content provided
        version = self.version_manager.auto_increment_version(current_content)

        # Create metadata for header
        metadata = self.assembler.create_metadata_dict(
            version=version, framework_version=self.framework_version
        )

        # Update header section with metadata
        sections = self.section_manager.get_sections()
        if "header" in sections:
            generator_func, _ = sections["header"]
            sections["header"] = (generator_func, metadata)

        # Assemble content
        return self.assembler.assemble_content(sections, template_variables)

    def validate_content(self, content: str) -> Tuple[bool, List[str]]:
        """
        Validate that generated content has all required sections.

        Args:
            content: Content to validate

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        return self.validator.validate_content(content)

    def deploy_to_parent(
        self, parent_path: Path, force: bool = False
    ) -> Tuple[bool, str]:
        """
        Deploy generated content to a parent directory.

        Args:
            parent_path: Path to parent directory
            force: Force deployment even if versions match

        Returns:
            Tuple of (success, message)
        """
        # Check if we need to read existing content
        # Try INSTRUCTIONS.md first, fallback to CLAUDE.md for compatibility
        target_file = parent_path / "INSTRUCTIONS.md"
        if not target_file.exists() and (parent_path / "CLAUDE.md").exists():
            target_file = parent_path / "CLAUDE.md"
        current_content = None

        if target_file.exists():
            with target_file.open() as f:
                current_content = f.read()

        # Generate new content
        new_content = self.generate(current_content=current_content)

        # Deploy using deployment manager
        return self.deployment_manager.deploy_to_parent(new_content, parent_path, force)

    def get_section_list(self) -> List[str]:
        """
        Get list of all section names in order.

        Returns:
            List of section names
        """
        return self.section_manager.get_section_list()

    def update_section(self, section_name: str, content: str) -> bool:
        """
        Update a specific section's generator to return custom content.

        Args:
            section_name: Name of section to update
            content: New content for the section

        Returns:
            bool: Success status
        """
        return self.section_manager.update_section(section_name, content)

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
        self.section_manager.add_custom_section(section_name, content, after)

    # Compatibility methods to match original API
    def _get_framework_version(self) -> str:
        """Get framework version (compatibility method)."""
        return self.version_manager._get_framework_version()

    def _parse_current_version(self, content: str) -> Tuple[str, int]:
        """Parse current version (compatibility method)."""
        return self.version_manager.parse_current_version(content)

    def _auto_increment_version(self, current_content: Optional[str] = None) -> str:
        """Auto-increment version (compatibility method)."""
        return self.version_manager.auto_increment_version(current_content)

    def _generate_content_hash(self) -> str:
        """Generate content hash (compatibility method)."""
        return self.assembler.generate_content_hash()


# Export the main class
__all__ = ["FrameworkClaudeMdGenerator"]
