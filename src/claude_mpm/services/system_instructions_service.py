"""System instructions service for loading and processing system instructions.

This service handles:
1. Loading system instructions from multiple sources (project, framework)
2. Processing template variables in instructions
3. Stripping metadata comments
4. Creating system prompts with fallbacks

Extracted from ClaudeRunner to follow Single Responsibility Principle.
"""

import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from claude_mpm.config.paths import paths
from claude_mpm.core.base_service import BaseService
from claude_mpm.services.core.interfaces import SystemInstructionsInterface


class SystemInstructionsService(BaseService, SystemInstructionsInterface):
    """Service for loading and processing system instructions."""

    def __init__(self, agent_capabilities_service=None):
        """Initialize the system instructions service.

        Args:
            agent_capabilities_service: Optional service for generating agent capabilities
        """
        super().__init__(name="system_instructions_service")
        self.agent_capabilities_service = agent_capabilities_service
        self._framework_loader = None  # Cache the framework loader instance
        self._loaded_instructions = None  # Cache loaded instructions

    async def _initialize(self) -> None:
        """Initialize the service. No special initialization needed."""

    async def _cleanup(self) -> None:
        """Cleanup service resources. No cleanup needed."""

    def load_system_instructions(self, instruction_type: str = "default") -> str:
        """Load and process system instructions from agents/INSTRUCTIONS.md.

        Args:
            instruction_type: Type of instructions to load (currently only "default" supported)

        Now uses the FrameworkLoader for comprehensive instruction loading including:
        - INSTRUCTIONS.md
        - WORKFLOW.md
        - MEMORY.md
        - Actual PM memories from .claude-mpm/memories/PM.md
        - Agent capabilities
        - BASE_PM.md

        Returns:
            Processed system instructions string
        """
        try:
            # Return cached instructions if already loaded
            if self._loaded_instructions is not None:
                self.logger.debug("Returning cached system instructions")
                return self._loaded_instructions

            # Create FrameworkLoader only once
            if self._framework_loader is None:
                from claude_mpm.core.framework_loader import FrameworkLoader

                self._framework_loader = FrameworkLoader()
                self.logger.debug("Created new FrameworkLoader instance")

            # Load instructions and cache them
            instructions = self._framework_loader.get_framework_instructions()

            if instructions:
                self._loaded_instructions = instructions
                self.logger.info(
                    "Loaded and cached framework instructions via FrameworkLoader"
                )
                return instructions

            # Fallback if FrameworkLoader returns empty
            self.logger.warning(
                "FrameworkLoader returned empty instructions, using fallback"
            )
            fallback = "# System Instructions\n\nNo specific system instructions found. Using default behavior."
            self._loaded_instructions = fallback
            return fallback

        except Exception as e:
            self.logger.error(f"Failed to load system instructions: {e}")
            fallback = "# System Instructions\n\nError loading system instructions. Using default behavior."
            self._loaded_instructions = fallback
            return fallback

    def process_base_pm_content(self, base_pm_content: str) -> str:
        """Process BASE_PM.md content with dynamic injections.

        This method replaces template variables in BASE_PM.md with:
        - {{AGENT_CAPABILITIES}}: List of deployed agents from .claude/agents/
        - {{VERSION}}: Current framework version
        - {{CURRENT_DATE}}: Today's date for temporal context

        Args:
            base_pm_content: Raw BASE_PM.md content

        Returns:
            Processed content with variables replaced
        """
        try:
            # Replace agent capabilities if service is available
            if (
                self.agent_capabilities_service
                and "{{AGENT_CAPABILITIES}}" in base_pm_content
            ):
                capabilities = self.agent_capabilities_service.generate_deployed_agent_capabilities()
                base_pm_content = base_pm_content.replace(
                    "{{AGENT_CAPABILITIES}}", capabilities
                )

            # Replace version
            if "{{VERSION}}" in base_pm_content:
                version = self._get_version()
                base_pm_content = base_pm_content.replace("{{VERSION}}", version)

            # Replace current date
            if "{{CURRENT_DATE}}" in base_pm_content:
                current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                base_pm_content = base_pm_content.replace(
                    "{{CURRENT_DATE}}", current_date
                )

        except Exception as e:
            self.logger.warning(f"Error processing BASE_PM content: {e}")

        return base_pm_content

    def strip_metadata_comments(self, content: str) -> str:
        """Strip HTML metadata comments from content.

        Removes comments like:
        <!-- FRAMEWORK_VERSION: 0010 -->
        <!-- LAST_MODIFIED: 2025-08-10T00:00:00Z -->
        <!-- metadata: {...} -->

        Args:
            content: Content with potential metadata comments

        Returns:
            Content with metadata comments removed
        """
        try:
            # Remove HTML comments that contain metadata keywords
            metadata_patterns = [
                r"<!--\s*FRAMEWORK_VERSION:.*?-->",
                r"<!--\s*LAST_MODIFIED:.*?-->",
                r"<!--\s*metadata:.*?-->",
                r"<!--\s*META:.*?-->",
                r"<!--\s*VERSION:.*?-->",
            ]

            cleaned = content
            for pattern in metadata_patterns:
                cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.IGNORECASE)

            # Remove any remaining empty lines that might result from comment removal
            lines = cleaned.split("\n")
            cleaned_lines = []
            prev_empty = False

            for line in lines:
                is_empty = not line.strip()
                if not (is_empty and prev_empty):  # Avoid consecutive empty lines
                    cleaned_lines.append(line)
                prev_empty = is_empty

            cleaned = "\n".join(cleaned_lines)

            # Also remove any leading blank lines that might result
            return cleaned.lstrip("\n")

        except Exception as e:
            self.logger.warning(f"Error stripping metadata comments: {e}")
            return content

    def create_system_prompt(self, system_instructions: Optional[str] = None) -> str:
        """Create the complete system prompt including instructions.

        Args:
            system_instructions: Optional pre-loaded instructions, will load if None

        Returns:
            Complete system prompt
        """
        if system_instructions is None:
            system_instructions = self.load_system_instructions()

        return system_instructions

    def _process_base_pm_content(self, base_pm_content: str) -> str:
        """Internal method for processing BASE_PM content."""
        return self.process_base_pm_content(base_pm_content)

    def _strip_metadata_comments(self, content: str) -> str:
        """Internal method for stripping metadata comments."""
        return self.strip_metadata_comments(content)

    def _get_version(self) -> str:
        """Get the current framework version.

        Returns:
            Version string or 'unknown' if not found
        """
        try:
            version_file = paths.project_root / "VERSION"
            if version_file.exists():
                return version_file.read_text().strip()

            # Try to get version from package info
            try:
                import claude_mpm

                if hasattr(claude_mpm, "__version__"):
                    return claude_mpm.__version__
            except ImportError:
                pass

            return "unknown"

        except Exception as e:
            self.logger.debug(f"Could not determine version: {e}")
            return "unknown"

    def get_available_instruction_types(self) -> List[str]:
        """Get list of available instruction types.

        Returns:
            List of available instruction type names
        """
        # Currently only "default" type is supported
        return ["default"]

    def validate_instructions(self, instructions: str) -> Tuple[bool, List[str]]:
        """Validate system instructions format and content.

        Args:
            instructions: Instructions content to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if not instructions or not instructions.strip():
            errors.append("Instructions cannot be empty")
            return False, errors

        # Check for basic structure
        if len(instructions.strip()) < 10:
            errors.append("Instructions appear to be too short")

        # Check for potentially problematic content
        if "{{" in instructions and "}}" in instructions:
            # Check if template variables are properly processed
            unprocessed_vars = re.findall(r"\{\{([^}]+)\}\}", instructions)
            if unprocessed_vars:
                errors.append(
                    f"Unprocessed template variables found: {', '.join(unprocessed_vars)}"
                )

        return len(errors) == 0, errors
