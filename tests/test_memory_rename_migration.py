"""Tests for memory file migration of renamed agents.

Verifies that get_memory_file_with_migration() correctly finds and migrates
memory files for agents that have been renamed (e.g., tmux-agent -> tmux).
"""

import logging
from pathlib import Path

import pytest

from claude_mpm.services.agents.memory.memory_file_service import (
    _AGENT_RENAME_MAP,
    MemoryFileService,
)


@pytest.fixture
def memory_service(tmp_path: Path) -> MemoryFileService:
    """Create a MemoryFileService with a temporary directory."""
    return MemoryFileService(memories_dir=tmp_path)


class TestMemoryRenameMigration:
    """Memory files for renamed agents must be found and migrated."""

    @pytest.mark.parametrize(
        "new_id,old_file,expected_new",
        [
            ("tmux", "tmux-agent_memories.md", "tmux_memories.md"),
            ("content", "content-agent_memories.md", "content_memories.md"),
            (
                "memory-manager",
                "memory-manager-agent_memories.md",
                "memory-manager_memories.md",
            ),
            (
                "web-ui-engineer",
                "web-ui_memories.md",
                "web-ui-engineer_memories.md",
            ),
        ],
    )
    def test_renamed_agent_memory_found(
        self,
        tmp_path: Path,
        memory_service: MemoryFileService,
        new_id: str,
        old_file: str,
        expected_new: str,
    ) -> None:
        """Old memory file found and renamed to canonical."""
        old_path = tmp_path / old_file
        old_path.write_text("# Memories\n- important fact")

        result = memory_service.get_memory_file_with_migration(tmp_path, new_id)

        assert result.name == expected_new
        assert result.exists()
        assert not old_path.exists(), f"Old file {old_file} should have been renamed"
        assert "important fact" in result.read_text()

    def test_web_ui_to_web_ui_engineer_migration(
        self,
        tmp_path: Path,
        memory_service: MemoryFileService,
    ) -> None:
        """Special case: completely different name, must still find memories."""
        (tmp_path / "web-ui_memories.md").write_text("# Web UI memories")

        result = memory_service.get_memory_file_with_migration(
            tmp_path, "web-ui-engineer"
        )

        assert result.name == "web-ui-engineer_memories.md"
        assert result.exists()
        assert "Web UI memories" in result.read_text()
        assert not (tmp_path / "web-ui_memories.md").exists()

    def test_underscore_variant_also_migrated(
        self,
        tmp_path: Path,
        memory_service: MemoryFileService,
    ) -> None:
        """Underscore variant of old name (tmux_agent) is also found."""
        (tmp_path / "tmux_agent_memories.md").write_text("# Tmux underscore memories")

        result = memory_service.get_memory_file_with_migration(tmp_path, "tmux")

        assert result.name == "tmux_memories.md"
        assert result.exists()
        assert "Tmux underscore memories" in result.read_text()

    def test_singular_memory_suffix_also_migrated(
        self,
        tmp_path: Path,
        memory_service: MemoryFileService,
    ) -> None:
        """Old singular _memory.md suffix for a renamed agent is also found."""
        (tmp_path / "content-agent_memory.md").write_text("# Content old singular")

        result = memory_service.get_memory_file_with_migration(tmp_path, "content")

        assert result.name == "content_memories.md"
        assert result.exists()
        assert "Content old singular" in result.read_text()

    def test_idempotent_migration(
        self,
        tmp_path: Path,
        memory_service: MemoryFileService,
    ) -> None:
        """Running migration twice does not fail."""
        (tmp_path / "tmux-agent_memories.md").write_text("# Tmux memories")

        # First call: migrates tmux-agent -> tmux
        result1 = memory_service.get_memory_file_with_migration(tmp_path, "tmux")
        assert result1.name == "tmux_memories.md"
        assert result1.exists()

        # Second call: finds canonical file directly, no error
        result2 = memory_service.get_memory_file_with_migration(tmp_path, "tmux")
        assert result2.name == "tmux_memories.md"
        assert result2.exists()
        assert "Tmux memories" in result2.read_text()

    def test_canonical_file_takes_priority(
        self,
        tmp_path: Path,
        memory_service: MemoryFileService,
    ) -> None:
        """If both old and new files exist, canonical (new) wins."""
        (tmp_path / "tmux_memories.md").write_text("# New canonical")
        (tmp_path / "tmux-agent_memories.md").write_text("# Old legacy")

        result = memory_service.get_memory_file_with_migration(tmp_path, "tmux")

        assert result.name == "tmux_memories.md"
        assert "New canonical" in result.read_text()
        # Old file should be untouched (not deleted, not overwritten)
        assert (tmp_path / "tmux-agent_memories.md").exists()
        assert "Old legacy" in (tmp_path / "tmux-agent_memories.md").read_text()

    def test_migration_logs_paths(
        self,
        tmp_path: Path,
        memory_service: MemoryFileService,
    ) -> None:
        """Migration logs both old and new paths."""
        from unittest.mock import patch

        (tmp_path / "content-agent_memories.md").write_text("# Content")

        with patch.object(memory_service, "logger") as mock_logger:
            memory_service.get_memory_file_with_migration(tmp_path, "content")

        # Verify the info log was called with both old and new filenames
        mock_logger.info.assert_called_once()
        log_msg = mock_logger.info.call_args[0][0]
        assert "content-agent_memories.md" in log_msg
        assert "content_memories.md" in log_msg

    def test_no_file_returns_canonical_path(
        self,
        tmp_path: Path,
        memory_service: MemoryFileService,
    ) -> None:
        """When no memory file exists at all, return the canonical path."""
        result = memory_service.get_memory_file_with_migration(tmp_path, "tmux")

        assert result.name == "tmux_memories.md"
        assert not result.exists()

    def test_rename_map_covers_all_renamed_agents(self) -> None:
        """Ensure all 4 renamed agents are in the rename map."""
        assert "tmux" in _AGENT_RENAME_MAP
        assert "content" in _AGENT_RENAME_MAP
        assert "memory-manager" in _AGENT_RENAME_MAP
        assert "web-ui-engineer" in _AGENT_RENAME_MAP
        assert len(_AGENT_RENAME_MAP) == 4

    def test_non_renamed_agent_unaffected(
        self,
        tmp_path: Path,
        memory_service: MemoryFileService,
    ) -> None:
        """Agents NOT in the rename map are unaffected by this change."""
        (tmp_path / "python-engineer_memories.md").write_text("# Python memories")

        result = memory_service.get_memory_file_with_migration(
            tmp_path, "python-engineer"
        )

        assert result.name == "python-engineer_memories.md"
        assert result.exists()
        assert "Python memories" in result.read_text()
