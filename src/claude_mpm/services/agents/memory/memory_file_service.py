"""Memory File Service - Handles file operations for agent memories."""

from pathlib import Path

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)

# Maps current (new) agent IDs to their previous (old) agent IDs.
# Used by get_memory_file_with_migration() to find memory files that were
# created under the old name before an agent was renamed.
_AGENT_RENAME_MAP: dict[str, list[str]] = {
    "tmux": ["tmux-agent", "tmux_agent"],
    "content": ["content-agent", "content_agent"],
    "memory-manager": ["memory-manager-agent", "memory_manager_agent"],
    "web-ui-engineer": ["web-ui", "web_ui"],
}


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

        Normalizes agent_id to canonical kebab-case and lazily migrates
        legacy files (underscore-format, singular _memory.md) on access.

        Args:
            directory: Directory to check for memory file
            agent_id: Agent identifier (any format accepted)

        Returns:
            Path to the memory file (canonical kebab-case naming)
        """
        from claude_mpm.utils.agent_filters import normalize_agent_id

        # Normalize to canonical kebab-case (lowercase)
        normalized_id = normalize_agent_id(agent_id)
        if not normalized_id:
            # Edge case guard (empty string, "-agent" input)
            normalized_id = (
                agent_id.replace("-", "_").lower() if agent_id else "unknown"
            )

        # Canonical file path
        canonical_file = directory / f"{normalized_id}_memories.md"

        # If canonical already exists, return immediately
        if canonical_file.exists():
            return canonical_file

        # Rename-aware fallback: check previous agent IDs for renamed agents.
        # This handles cases where an agent was renamed (e.g., "tmux-agent" -> "tmux")
        # and the memory file still uses the old name.
        previous_ids = _AGENT_RENAME_MAP.get(normalized_id, [])
        for prev_id in previous_ids:
            for suffix in ["_memories.md", "_memory.md"]:
                legacy_file = directory / f"{prev_id}{suffix}"
                if legacy_file.exists():
                    self.logger.info(
                        f"Migrating renamed agent memory: "
                        f"{legacy_file.name} -> {canonical_file.name}"
                    )
                    try:
                        legacy_file.rename(canonical_file)
                        return canonical_file
                    except Exception as e:
                        self.logger.warning(
                            f"Could not migrate renamed agent memory file: {e}"
                        )
                        return legacy_file

        # Legacy fallback 1: hyphenated raw agent_id (e.g. research-agent_memories.md)
        # This covers cases like "research-agent" that normalize to "research" but were
        # stored using the raw hyphenated form before normalization was introduced.
        raw_hyphenated_id = agent_id.lower()
        if raw_hyphenated_id != normalized_id:
            legacy_hyphenated = directory / f"{raw_hyphenated_id}_memories.md"
            if legacy_hyphenated.exists():
                try:
                    legacy_hyphenated.rename(canonical_file)
                    self.logger.info(
                        f"Migrated hyphenated memory file: "
                        f"{legacy_hyphenated.name} -> {canonical_file.name}"
                    )
                    return canonical_file
                except Exception as e:
                    self.logger.warning(
                        f"Could not migrate hyphenated memory file: {e}"
                    )
                    return legacy_hyphenated

        # Legacy fallback 2: underscore-format file
        underscore_id = agent_id.replace("-", "_").lower()
        if underscore_id != normalized_id:
            legacy_underscore = directory / f"{underscore_id}_memories.md"
            if legacy_underscore.exists():
                try:
                    legacy_underscore.rename(canonical_file)
                    self.logger.info(
                        f"Migrated underscore memory file: "
                        f"{legacy_underscore.name} -> {canonical_file.name}"
                    )
                    return canonical_file
                except Exception as e:
                    self.logger.warning(
                        f"Could not migrate underscore memory file: {e}"
                    )
                    return legacy_underscore

        # Legacy fallback 3: raw agent_id format (no normalization applied)
        if agent_id != normalized_id and agent_id.lower() != underscore_id:
            raw_file = directory / f"{agent_id}_memories.md"
            if raw_file.exists() and not canonical_file.exists():
                try:
                    raw_file.rename(canonical_file)
                    self.logger.info(
                        f"Migrated raw memory file: "
                        f"{raw_file.name} -> {canonical_file.name}"
                    )
                    return canonical_file
                except Exception as e:
                    self.logger.warning(f"Could not migrate raw memory file: {e}")
                    return raw_file

        # Legacy fallback 3: singular _memory.md format (oldest convention)
        for stem in [normalized_id, underscore_id]:
            old_singular = directory / f"{stem}_memory.md"
            if old_singular.exists() and not canonical_file.exists():
                try:
                    old_singular.rename(canonical_file)
                    self.logger.info(
                        f"Migrated singular memory file: "
                        f"{old_singular.name} -> {canonical_file.name}"
                    )
                    return canonical_file
                except Exception as e:
                    self.logger.warning(f"Could not migrate singular memory file: {e}")
                    return old_singular

        return canonical_file

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
