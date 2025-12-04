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

    def _load_tier_file(
        self,
        filename: str,
        current_dir: Path,
        framework_path: Optional[Path] = None,
        include_system: bool = False,
    ) -> tuple[Optional[str], Optional[str]]:
        """Load file with tier precedence: project → user → system.

        Args:
            filename: Name of file to load (e.g., "INSTRUCTIONS.md")
            current_dir: Current working directory for project-level
            framework_path: Path to framework installation for system-level
            include_system: Whether to check system-level path

        Returns:
            Tuple of (content, level) where level is 'project', 'user', 'system', or None
        """
        # Check project-level (highest priority)
        project_path = current_dir / ".claude-mpm" / filename
        if project_path.exists():
            loaded_content = self.try_load_file(
                project_path, f"project-specific {filename}"
            )
            if loaded_content:
                self.logger.info(f"Using project-specific {filename} from .claude-mpm/")
                return loaded_content, "project"

        # Check user-level (medium priority)
        user_path = Path.home() / ".claude-mpm" / filename
        if user_path.exists():
            loaded_content = self.try_load_file(user_path, f"user-specific {filename}")
            if loaded_content:
                self.logger.info(f"Using user-specific {filename} from ~/.claude-mpm/")
                return loaded_content, "user"

        # Check system-level (lowest priority)
        if include_system and framework_path and framework_path != Path("__PACKAGED__"):
            system_path = framework_path / "src" / "claude_mpm" / "agents" / filename
            if system_path.exists():
                loaded_content = self.try_load_file(system_path, f"system {filename}")
                if loaded_content:
                    self.logger.info(f"Using system {filename}")
                    return loaded_content, "system"

        return None, None

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
        return self._load_tier_file("INSTRUCTIONS.md", current_dir)

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
        return self._load_tier_file(
            "WORKFLOW.md", current_dir, framework_path, include_system=True
        )

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
        return self._load_tier_file(
            "MEMORY.md", current_dir, framework_path, include_system=True
        )
