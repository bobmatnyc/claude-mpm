#!/usr/bin/env python3
"""Memory File Service - Handles file operations for agent memories."""

from pathlib import Path

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class MemoryFileService:
    """Service for handling memory file operations."""

    def __init__(self, memories_dir: Path):
        """Initialize the memory file service.

        Args:
            memories_dir: Directory where memory files are stored
        """
        self.memories_dir = memories_dir
        self.logger = logger  # Use the module-level logger

    def get_memory_file_with_migration(self, directory: Path, agent_id: str) -> Path:
        """Get memory file path with migration support.

        Migrates from old naming convention if needed.
        Also handles hyphen to underscore conversion for agent IDs.

        Args:
            directory: Directory to check for memory file
            agent_id: Agent identifier (may contain hyphens or underscores)

        Returns:
            Path to the memory file
        """
        # Normalize agent_id to use underscores (matching deployed agent names)
        normalized_id = agent_id.replace("-", "_")

        # Define possible file paths
        new_file = directory / f"{normalized_id}_memories.md"
        old_file = directory / f"{normalized_id}_memory.md"

        # Also check for legacy hyphenated versions
        hyphenated_file = (
            directory / f"{agent_id}_memories.md" if "-" in agent_id else None
        )

        # Migration priority:
        # 1. If hyphenated version exists and normalized doesn't, migrate it
        if hyphenated_file and hyphenated_file.exists() and not new_file.exists():
            try:
                hyphenated_file.rename(new_file)
                self.logger.info(
                    f"Migrated hyphenated memory file: {hyphenated_file} -> {new_file}"
                )
            except Exception as e:
                self.logger.warning(f"Could not migrate hyphenated memory file: {e}")
                # Fall back to using the hyphenated version
                return hyphenated_file

        # 2. Migrate from old naming convention (_memory.md to _memories.md)
        if old_file.exists() and not new_file.exists():
            try:
                old_file.rename(new_file)
                self.logger.info(f"Migrated memory file: {old_file} -> {new_file}")
            except Exception as e:
                self.logger.warning(f"Could not migrate memory file: {e}")
                return old_file

        return new_file

    def save_memory_file(self, file_path: Path, content: str) -> bool:
        """Save content to a memory file.

        Args:
            file_path: Path to the memory file
            content: Content to save

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            file_path.write_text(content)

            self.logger.debug(f"Saved memory file: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save memory file {file_path}: {e}")
            return False

    def ensure_memories_directory(self) -> None:
        """Ensure the memories directory exists with README."""
        try:
            # Create directory if it doesn't exist
            self.memories_dir.mkdir(parents=True, exist_ok=True)

            # Create README if it doesn't exist
            readme_path = self.memories_dir / "README.md"
            if not readme_path.exists():
                readme_content = """# Agent Memories Directory

This directory contains memory files for various agents used in the project.

## File Format

Memory files follow the naming convention: `{agent_id}_memories.md`

Each file contains:
- Agent metadata (name, type, version)
- Project-specific learnings organized by category
- Timestamps for tracking updates

## Auto-generated

These files are managed automatically by the agent memory system.
Manual edits should be done carefully to preserve the format.
"""
                readme_path.write_text(readme_content)
                self.logger.debug(
                    f"Created README in memories directory: {readme_path}"
                )

        except Exception as e:
            self.logger.error(f"Failed to ensure memories directory: {e}")
