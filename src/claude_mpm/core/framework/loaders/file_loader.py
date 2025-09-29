"""File loading utilities for the framework."""

import logging
import re
from pathlib import Path
from typing import Optional

from claude_mpm.core.logging_utils import get_logger


class FileLoader:
    """Handles file I/O operations for the framework."""

    def __init__(self):
        """Initialize the file loader."""
        self.logger = get_logger("file_loader")
        self.framework_version: Optional[str] = None
        self.framework_last_modified: Optional[str] = None

    def try_load_file(self, file_path: Path, file_type: str) -> Optional[str]:
        """
        Try to load a file with error handling.

        Args:
            file_path: Path to the file to load
            file_type: Description of file type for logging

        Returns:
            File content if successful, None otherwise
        """
        try:
            content = file_path.read_text()
            if self.logger.isEnabledFor(logging.INFO):
                self.logger.info(f"Loaded {file_type} from: {file_path}")

            # Extract metadata if present
            self._extract_metadata(content, file_path)
            return content
        except Exception as e:
            if self.logger.isEnabledFor(logging.ERROR):
                self.logger.error(f"Failed to load {file_type}: {e}")
            return None

    def _extract_metadata(self, content: str, file_path: Path) -> None:
        """Extract metadata from file content.

        Args:
            content: File content to extract metadata from
            file_path: Path to the file (for context)
        """
        # Extract version
        version_match = re.search(r"<!-- FRAMEWORK_VERSION: (\d+) -->", content)
        if version_match:
            version = version_match.group(1)  # Keep as string to preserve leading zeros
            self.logger.info(f"Framework version: {version}")
            # Store framework version if this is the main INSTRUCTIONS.md
            if "INSTRUCTIONS.md" in str(file_path):
                self.framework_version = version

        # Extract modification timestamp
        timestamp_match = re.search(r"<!-- LAST_MODIFIED: ([^>]+) -->", content)
        if timestamp_match:
            timestamp = timestamp_match.group(1).strip()
            self.logger.info(f"Last modified: {timestamp}")
            # Store timestamp if this is the main INSTRUCTIONS.md
            if "INSTRUCTIONS.md" in str(file_path):
                self.framework_last_modified = timestamp

    def load_instructions_file(
        self, current_dir: Path
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Load custom INSTRUCTIONS.md from .claude-mpm directories.

        Precedence (highest to lowest):
        1. Project-specific: ./.claude-mpm/INSTRUCTIONS.md
        2. User-specific: ~/.claude-mpm/INSTRUCTIONS.md

        Args:
            current_dir: Current working directory

        Returns:
            Tuple of (content, level) where level is 'project', 'user', or None
        """
        # Check for project-specific INSTRUCTIONS.md first
        project_instructions_path = current_dir / ".claude-mpm" / "INSTRUCTIONS.md"
        if project_instructions_path.exists():
            loaded_content = self.try_load_file(
                project_instructions_path, "project-specific INSTRUCTIONS.md"
            )
            if loaded_content:
                self.logger.info(
                    "Using project-specific PM instructions from .claude-mpm/INSTRUCTIONS.md"
                )
                return loaded_content, "project"

        # Check for user-specific INSTRUCTIONS.md
        user_instructions_path = Path.home() / ".claude-mpm" / "INSTRUCTIONS.md"
        if user_instructions_path.exists():
            loaded_content = self.try_load_file(
                user_instructions_path, "user-specific INSTRUCTIONS.md"
            )
            if loaded_content:
                self.logger.info(
                    "Using user-specific PM instructions from ~/.claude-mpm/INSTRUCTIONS.md"
                )
                return loaded_content, "user"

        return None, None

    def load_workflow_file(
        self, current_dir: Path, framework_path: Path
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Load WORKFLOW.md from various locations.

        Precedence (highest to lowest):
        1. Project-specific: ./.claude-mpm/WORKFLOW.md
        2. User-specific: ~/.claude-mpm/WORKFLOW.md
        3. System default: framework/agents/WORKFLOW.md

        Args:
            current_dir: Current working directory
            framework_path: Path to framework installation

        Returns:
            Tuple of (content, level) where level is 'project', 'user', 'system', or None
        """
        # Check for project-specific WORKFLOW.md first (highest priority)
        project_workflow_path = current_dir / ".claude-mpm" / "WORKFLOW.md"
        if project_workflow_path.exists():
            loaded_content = self.try_load_file(
                project_workflow_path, "project-specific WORKFLOW.md"
            )
            if loaded_content:
                self.logger.info(
                    "Using project-specific workflow instructions from .claude-mpm/WORKFLOW.md"
                )
                return loaded_content, "project"

        # Check for user-specific WORKFLOW.md (medium priority)
        user_workflow_path = Path.home() / ".claude-mpm" / "WORKFLOW.md"
        if user_workflow_path.exists():
            loaded_content = self.try_load_file(
                user_workflow_path, "user-specific WORKFLOW.md"
            )
            if loaded_content:
                self.logger.info(
                    "Using user-specific workflow instructions from ~/.claude-mpm/WORKFLOW.md"
                )
                return loaded_content, "user"

        # Fall back to system workflow (lowest priority)
        if framework_path and framework_path != Path("__PACKAGED__"):
            system_workflow_path = (
                framework_path / "src" / "claude_mpm" / "agents" / "WORKFLOW.md"
            )
            if system_workflow_path.exists():
                loaded_content = self.try_load_file(
                    system_workflow_path, "system WORKFLOW.md"
                )
                if loaded_content:
                    self.logger.info("Using system workflow instructions")
                    return loaded_content, "system"

        return None, None

    def load_memory_file(
        self, current_dir: Path, framework_path: Path
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Load MEMORY.md from various locations.

        Precedence (highest to lowest):
        1. Project-specific: ./.claude-mpm/MEMORY.md
        2. User-specific: ~/.claude-mpm/MEMORY.md
        3. System default: framework/agents/MEMORY.md

        Args:
            current_dir: Current working directory
            framework_path: Path to framework installation

        Returns:
            Tuple of (content, level) where level is 'project', 'user', 'system', or None
        """
        # Check for project-specific MEMORY.md first (highest priority)
        project_memory_path = current_dir / ".claude-mpm" / "MEMORY.md"
        if project_memory_path.exists():
            loaded_content = self.try_load_file(
                project_memory_path, "project-specific MEMORY.md"
            )
            if loaded_content:
                self.logger.info(
                    "Using project-specific memory instructions from .claude-mpm/MEMORY.md"
                )
                return loaded_content, "project"

        # Check for user-specific MEMORY.md (medium priority)
        user_memory_path = Path.home() / ".claude-mpm" / "MEMORY.md"
        if user_memory_path.exists():
            loaded_content = self.try_load_file(
                user_memory_path, "user-specific MEMORY.md"
            )
            if loaded_content:
                self.logger.info(
                    "Using user-specific memory instructions from ~/.claude-mpm/MEMORY.md"
                )
                return loaded_content, "user"

        # Fall back to system memory instructions (lowest priority)
        if framework_path and framework_path != Path("__PACKAGED__"):
            system_memory_path = (
                framework_path / "src" / "claude_mpm" / "agents" / "MEMORY.md"
            )
            if system_memory_path.exists():
                loaded_content = self.try_load_file(
                    system_memory_path, "system MEMORY.md"
                )
                if loaded_content:
                    self.logger.info("Using system memory instructions")
                    return loaded_content, "system"

        return None, None
