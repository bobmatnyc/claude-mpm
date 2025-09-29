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

    def _load_filesystem_framework_instructions(self, content: Dict[str, Any]) -> None:
        """Load framework instructions from filesystem.

        Args:
            content: Dictionary to update with framework instructions
        """
        # Try new consolidated PM_INSTRUCTIONS.md first, fall back to INSTRUCTIONS.md
        pm_instructions_path = (
            self.framework_path / "src" / "claude_mpm" / "agents" / "PM_INSTRUCTIONS.md"
        )
        framework_instructions_path = (
            self.framework_path / "src" / "claude_mpm" / "agents" / "INSTRUCTIONS.md"
        )

        # Try loading new consolidated file first
        if pm_instructions_path.exists():
            loaded_content = self.file_loader.try_load_file(
                pm_instructions_path, "consolidated PM_INSTRUCTIONS.md"
            )
            if loaded_content:
                content["framework_instructions"] = loaded_content
                content["loaded"] = True
                self.logger.info("Loaded consolidated PM_INSTRUCTIONS.md")
        # Fall back to legacy file for backward compatibility
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
