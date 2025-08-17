from pathlib import Path

"""System instructions service for loading and processing system instructions.

This service handles:
1. Loading system instructions from multiple sources (project, framework)
2. Processing template variables in instructions
3. Stripping metadata comments
4. Creating system prompts with fallbacks

Extracted from ClaudeRunner to follow Single Responsibility Principle.
"""

import re
from datetime import datetime

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

    async def _initialize(self) -> None:
        """Initialize the service. No special initialization needed."""
        pass

    async def _cleanup(self) -> None:
        """Cleanup service resources. No cleanup needed."""
        pass

    def load_system_instructions(self) -> Optional[str]:
        """Load and process system instructions from agents/INSTRUCTIONS.md.

        Implements project > framework precedence:
        1. First check for project-specific instructions in .claude-mpm/agents/INSTRUCTIONS.md
        2. If not found, fall back to framework instructions in src/claude_mpm/agents/INSTRUCTIONS.md

        Returns:
            Processed system instructions or None if not found
        """
        try:
            # Check for project-specific instructions first
            project_instructions_path = Path.cwd() / ".claude-mpm" / "agents" / "INSTRUCTIONS.md"
            if project_instructions_path.exists():
                self.logger.info(
                    f"Loading project system instructions from {project_instructions_path}"
                )
                content = project_instructions_path.read_text(encoding="utf-8")
                return self._strip_metadata_comments(content)

            # Fall back to framework instructions
            framework_instructions_path = (
                paths.project_root / "src" / "claude_mpm" / "agents" / "INSTRUCTIONS.md"
            )
            if framework_instructions_path.exists():
                self.logger.info(
                    f"Loading framework system instructions from {framework_instructions_path}"
                )
                content = framework_instructions_path.read_text(encoding="utf-8")
                return self._strip_metadata_comments(content)

            # Check for BASE_PM.md as additional fallback
            base_pm_path = paths.project_root / "src" / "claude_mpm" / "agents" / "BASE_PM.md"
            if base_pm_path.exists():
                self.logger.info(f"Loading BASE_PM instructions from {base_pm_path}")
                content = base_pm_path.read_text(encoding="utf-8")
                processed_content = self._process_base_pm_content(content)
                return self._strip_metadata_comments(processed_content)

            self.logger.warning("No system instructions found in project or framework")
            return None

        except Exception as e:
            self.logger.error(f"Failed to load system instructions: {e}")
            return None

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
            if self.agent_capabilities_service and "{{AGENT_CAPABILITIES}}" in base_pm_content:
                capabilities = (
                    self.agent_capabilities_service.generate_deployed_agent_capabilities()
                )
                base_pm_content = base_pm_content.replace("{{AGENT_CAPABILITIES}}", capabilities)

            # Replace version
            if "{{VERSION}}" in base_pm_content:
                version = self._get_version()
                base_pm_content = base_pm_content.replace("{{VERSION}}", version)

            # Replace current date
            if "{{CURRENT_DATE}}" in base_pm_content:
                current_date = datetime.now().strftime("%Y-%m-%d")
                base_pm_content = base_pm_content.replace("{{CURRENT_DATE}}", current_date)

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
            cleaned = cleaned.lstrip("\n")

            return cleaned

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

        if system_instructions:
            return system_instructions
        else:
            # Fallback to basic context
            self.logger.info("Using fallback system context")
            # Import locally to avoid circular dependency
            from claude_mpm.core.claude_runner import create_simple_context

            return create_simple_context()

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
