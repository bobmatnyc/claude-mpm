"""System instructions service for loading and processing system instructions.

This service handles:
1. Loading system instructions from multiple sources (project, framework)
2. Processing template variables in instructions
3. Stripping metadata comments
4. Creating system prompts with fallbacks

Extracted from ClaudeRunner to follow Single Responsibility Principle.
"""

import re
from datetime import UTC, datetime

from claude_mpm.config.paths import paths
from claude_mpm.core.base_service import BaseService
from claude_mpm.core.unified_paths import get_path_manager
from claude_mpm.services.core.interfaces import SystemInstructionsInterface


class SystemInstructionsService(BaseService, SystemInstructionsInterface):
    """Service for loading and processing system instructions."""

    # Marker injected into the prompt when the user-level override is applied.
    # Used as a defensive check against double-append in addition to the
    # _system_prompt_cache field.
    USER_OVERRIDE_MARKER = "# User-Level PM Override"

    def __init__(self, agent_capabilities_service=None):
        """Initialize the system instructions service.

        Args:
            agent_capabilities_service: Optional service for generating agent capabilities
        """
        super().__init__(name="system_instructions_service")
        self.agent_capabilities_service = agent_capabilities_service
        self._framework_loader = None  # Cache the framework loader instance
        self._loaded_instructions = None  # Cache loaded instructions
        # Cache the augmented system prompt so the user-level override is
        # appended at most once per service instance.  Previously the
        # idempotency guard checked the cached *base* content (which never
        # contains the marker), causing the override to be re-appended on
        # every create_system_prompt() call.
        self._system_prompt_cache: str | None = None

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
                current_date = datetime.now(UTC).strftime("%Y-%m-%d")
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

    def create_system_prompt(self, system_instructions: str | None = None) -> str:
        """Create the complete system prompt including instructions.

        Appends a user-level PM_INSTRUCTIONS override from
        ~/.claude-mpm/PM_INSTRUCTIONS.md when present, so users can
        customize PM behavior without modifying package source files.

        The augmented prompt is cached on the service instance via
        ``self._system_prompt_cache`` so the override is appended at most
        once per service lifetime — subsequent calls return the cached
        result. The cache is keyed on the service instance, not on the
        argument, so explicit ``system_instructions`` arguments bypass
        the cache (used for callers that need to compose their own base).

        Args:
            system_instructions: Optional pre-loaded instructions, will load if None

        Returns:
            Complete system prompt, optionally augmented with user-level override
        """
        # Track whether the caller supplied explicit instructions so we
        # only cache results built from our own canonical base. Explicit
        # callers get their own augmented result back but don't pollute
        # the shared cache.
        caller_supplied = system_instructions is not None

        # Fast path: caller did not supply explicit instructions and the
        # augmented prompt has already been built. Return it directly so
        # the override is appended at most once per service instance.
        if not caller_supplied and self._system_prompt_cache is not None:
            return self._system_prompt_cache

        if system_instructions is None:
            system_instructions = self.load_system_instructions()

        # Apply user-level PM_INSTRUCTIONS override if present.
        # Use the unified path manager so the directory name stays in sync
        # with UnifiedPathManager.CONFIG_DIR_NAME (currently ".claude-mpm").
        # Failure to read the file is non-fatal: log at DEBUG and continue
        # with the base (un-augmented) instructions.
        user_override_path = (
            get_path_manager().get_user_config_dir() / "PM_INSTRUCTIONS.md"
        )
        if user_override_path.is_file():
            try:
                override_content = user_override_path.read_text(encoding="utf-8")
                # Defensive: don't double-append if the marker is somehow
                # already present in the base instructions (e.g. caller
                # passed an already-augmented prompt).
                if self.USER_OVERRIDE_MARKER not in system_instructions:
                    system_instructions = (
                        system_instructions
                        + f"\n\n---\n{self.USER_OVERRIDE_MARKER}\n\n"
                        + override_content
                    )
                    self.logger.info(
                        f"Applied user-level PM_INSTRUCTIONS override ({len(override_content)} chars)"
                    )
            except OSError as e:
                self.logger.debug(f"User-level override exists but couldn't read: {e}")

        # Cache the augmented result so subsequent no-arg calls return
        # immediately without re-reading the override file or risking
        # double-append. Only populate the cache when we built the prompt
        # from our own canonical base (system_instructions arg was None).
        if not caller_supplied:
            self._system_prompt_cache = system_instructions
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

    def get_available_instruction_types(self) -> list[str]:
        """Get list of available instruction types.

        Returns:
            List of available instruction type names
        """
        # Currently only "default" type is supported
        return ["default"]

    def validate_instructions(self, instructions: str) -> tuple[bool, list[str]]:
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
