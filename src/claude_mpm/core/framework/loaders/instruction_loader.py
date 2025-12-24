"""Loader for framework instructions and configuration files."""

from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.core.logging_utils import get_logger

from .file_loader import FileLoader
from .packaged_loader import PackagedLoader


class InstructionLoader:
    """Handles loading of INSTRUCTIONS, WORKFLOW, and MEMORY files."""

    def __init__(self, framework_path: Optional[Path] = None):
        """Initialize the instruction loader.

        Args:
            framework_path: Path to framework installation
        """
        self.logger = get_logger("instruction_loader")
        self.framework_path = framework_path
        self.file_loader = FileLoader()
        self.packaged_loader = PackagedLoader()
        self.current_dir = Path.cwd()

    def load_all_instructions(self, content: Dict[str, Any]) -> None:
        """Load all instruction files into the content dictionary.

        Args:
            content: Dictionary to update with loaded instructions
        """
        # Load custom INSTRUCTIONS.md
        self.load_custom_instructions(content)

        # Load framework instructions
        self.load_framework_instructions(content)

        # Load WORKFLOW.md
        self.load_workflow_instructions(content)

        # Load MEMORY.md
        self.load_memory_instructions(content)

    def load_custom_instructions(self, content: Dict[str, Any]) -> None:
        """Load custom INSTRUCTIONS.md from .claude-mpm directories.

        Args:
            content: Dictionary to update with loaded instructions
        """
        instructions, level = self.file_loader.load_instructions_file(self.current_dir)
        if instructions:
            content["custom_instructions"] = instructions
            content["custom_instructions_level"] = level

    def load_framework_instructions(self, content: Dict[str, Any]) -> None:
        """Load framework INSTRUCTIONS.md or PM_INSTRUCTIONS.md.

        Args:
            content: Dictionary to update with framework instructions
        """
        if not self.framework_path:
            return

        # Check if this is a packaged installation
        if self.framework_path == Path("__PACKAGED__"):
            # Use packaged loader
            self.packaged_loader.load_framework_content(content)
        else:
            # Load from filesystem for development mode
            self._load_filesystem_framework_instructions(content)

        # Update framework metadata
        if self.file_loader.framework_version:
            content["instructions_version"] = self.file_loader.framework_version
            content["version"] = self.file_loader.framework_version
        if self.file_loader.framework_last_modified:
            content["instructions_last_modified"] = (
                self.file_loader.framework_last_modified
            )

        # Transfer metadata from packaged loader if available
        if self.packaged_loader.framework_version:
            content["instructions_version"] = self.packaged_loader.framework_version
            content["version"] = self.packaged_loader.framework_version
        if self.packaged_loader.framework_last_modified:
            content["instructions_last_modified"] = (
                self.packaged_loader.framework_last_modified
            )

    def _extract_version(self, file_content: str) -> int:
        """Extract version number from PM_INSTRUCTIONS_VERSION comment.

        Args:
            file_content: Content of the file to extract version from

        Returns:
            Version number as integer, or 0 if not found
        """
        import re

        match = re.search(r"PM_INSTRUCTIONS_VERSION:\s*(\d+)", file_content)
        if match:
            return int(match.group(1))
        return 0  # No version = oldest

    def _load_filesystem_framework_instructions(self, content: Dict[str, Any]) -> None:
        """Load framework instructions from filesystem.

        Priority order:
        1. Deployed compiled file: .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md (if version >= source)
        2. Source file (development): src/claude_mpm/agents/PM_INSTRUCTIONS.md
        3. Legacy file (backward compat): src/claude_mpm/agents/INSTRUCTIONS.md

        Version validation ensures deployed file is never stale compared to source.

        Args:
            content: Dictionary to update with framework instructions
        """
        # Define source path for version checking
        pm_instructions_path = (
            self.framework_path / "src" / "claude_mpm" / "agents" / "PM_INSTRUCTIONS.md"
        )

        # PRIORITY 1: Check for compiled/deployed version in .claude-mpm/
        # This is the merged PM_INSTRUCTIONS.md + WORKFLOW.md + MEMORY.md
        deployed_path = self.current_dir / ".claude-mpm" / "PM_INSTRUCTIONS_DEPLOYED.md"
        if deployed_path.exists():
            # Validate version before using deployed file
            deployed_content = deployed_path.read_text()
            deployed_version = self._extract_version(deployed_content)

            # Check source version for comparison
            if pm_instructions_path.exists():
                source_content = pm_instructions_path.read_text()
                source_version = self._extract_version(source_content)

                if deployed_version < source_version:
                    self.logger.warning(
                        f"Deployed PM instructions v{deployed_version:04d} is stale, "
                        f"source is v{source_version:04d}. Using source instead."
                    )
                    # Fall through to source loading - don't return early
                else:
                    # Version OK, use deployed
                    content["framework_instructions"] = deployed_content
                    content["loaded"] = True
                    self.logger.info(
                        f"Loaded PM_INSTRUCTIONS_DEPLOYED.md v{deployed_version:04d} from .claude-mpm/"
                    )
                    return  # Stop here - deployed version is current
            else:
                # Source doesn't exist, use deployed even without version check
                content["framework_instructions"] = deployed_content
                content["loaded"] = True
                self.logger.info("Loaded PM_INSTRUCTIONS_DEPLOYED.md from .claude-mpm/")
                return

        # PRIORITY 2: Development mode - load from source PM_INSTRUCTIONS.md
        framework_instructions_path = (
            self.framework_path / "src" / "claude_mpm" / "agents" / "INSTRUCTIONS.md"
        )

        # Try loading new consolidated file (pm_instructions_path already defined above)
        if pm_instructions_path.exists():
            loaded_content = self.file_loader.try_load_file(
                pm_instructions_path, "source PM_INSTRUCTIONS.md (development mode)"
            )
            if loaded_content:
                content["framework_instructions"] = loaded_content
                content["loaded"] = True
                self.logger.warning(
                    "Using source PM_INSTRUCTIONS.md - deployed version not found"
                )
        # PRIORITY 3: Fall back to legacy file for backward compatibility
        elif framework_instructions_path.exists():
            loaded_content = self.file_loader.try_load_file(
                framework_instructions_path, "framework INSTRUCTIONS.md (legacy)"
            )
            if loaded_content:
                content["framework_instructions"] = loaded_content
                content["loaded"] = True
                self.logger.warning(
                    "Using legacy INSTRUCTIONS.md - consider migrating to PM_INSTRUCTIONS.md"
                )

        # Load BASE_PM.md for core framework requirements
        base_pm_path = (
            self.framework_path / "src" / "claude_mpm" / "agents" / "BASE_PM.md"
        )
        if base_pm_path.exists():
            base_pm_content = self.file_loader.try_load_file(
                base_pm_path, "BASE_PM framework requirements"
            )
            if base_pm_content:
                content["base_pm_instructions"] = base_pm_content

    def load_workflow_instructions(self, content: Dict[str, Any]) -> None:
        """Load WORKFLOW.md from appropriate location.

        Args:
            content: Dictionary to update with workflow instructions
        """
        workflow, level = self.file_loader.load_workflow_file(
            self.current_dir, self.framework_path
        )
        if workflow:
            content["workflow_instructions"] = workflow
            content["workflow_instructions_level"] = level

    def load_memory_instructions(self, content: Dict[str, Any]) -> None:
        """Load MEMORY.md from appropriate location.

        Args:
            content: Dictionary to update with memory instructions
        """
        memory, level = self.file_loader.load_memory_file(
            self.current_dir, self.framework_path
        )
        if memory:
            content["memory_instructions"] = memory
            content["memory_instructions_level"] = level
