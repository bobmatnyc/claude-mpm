#!/usr/bin/env python3
"""Test that memory file naming handles both hyphen and underscore conventions."""

import tempfile
from pathlib import Path

import pytest

from claude_mpm.services.agents.memory.memory_file_service import MemoryFileService


class TestMemoryFileNaming:
    """Test memory file naming normalization."""

    def test_normalizes_hyphenated_agent_id(self):
        """Test that hyphenated agent IDs are normalized to underscores."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / "memories"
            memories_dir.mkdir()

            service = MemoryFileService(memories_dir)

            # Request memory file with hyphenated ID
            memory_file = service.get_memory_file_with_migration(
                memories_dir, "data-engineer"
            )

            # Should return underscore version
            assert memory_file.name == "data_engineer_memories.md"

    def test_uses_existing_underscore_file(self):
        """Test that existing underscore files are used directly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / "memories"
            memories_dir.mkdir()

            # Create existing file with underscores
            existing_file = memories_dir / "data_engineer_memories.md"
            existing_file.write_text("# Existing memory")

            service = MemoryFileService(memories_dir)

            # Request with hyphenated ID
            memory_file = service.get_memory_file_with_migration(
                memories_dir, "data-engineer"
            )

            # Should return the existing underscore version
            assert memory_file == existing_file
            assert memory_file.exists()
            assert memory_file.read_text() == "# Existing memory"

    def test_migrates_hyphenated_to_underscore(self):
        """Test migration from hyphenated to underscore naming."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / "memories"
            memories_dir.mkdir()

            # Create hyphenated file
            hyphenated_file = memories_dir / "data-engineer_memories.md"
            hyphenated_file.write_text("# Hyphenated memory")

            service = MemoryFileService(memories_dir)

            # Request memory file
            memory_file = service.get_memory_file_with_migration(
                memories_dir, "data-engineer"
            )

            # Should have migrated to underscore version
            assert memory_file.name == "data_engineer_memories.md"
            assert memory_file.exists()
            assert memory_file.read_text() == "# Hyphenated memory"
            assert not hyphenated_file.exists()  # Old file should be renamed

    def test_handles_already_normalized_ids(self):
        """Test that already normalized IDs work correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / "memories"
            memories_dir.mkdir()

            service = MemoryFileService(memories_dir)

            # Request with already normalized ID
            memory_file = service.get_memory_file_with_migration(
                memories_dir, "data_engineer"
            )

            # Should work without issues
            assert memory_file.name == "data_engineer_memories.md"

    def test_handles_simple_agent_names(self):
        """Test that simple agent names without special characters work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / "memories"
            memories_dir.mkdir()

            service = MemoryFileService(memories_dir)

            # Test simple agent names
            for agent_id in ["engineer", "qa", "research", "ops"]:
                memory_file = service.get_memory_file_with_migration(
                    memories_dir, agent_id
                )
                assert memory_file.name == f"{agent_id}_memories.md"

    def test_version_control_agent_naming(self):
        """Test version-control agent name handling."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / "memories"
            memories_dir.mkdir()

            service = MemoryFileService(memories_dir)

            # Test version-control with hyphen
            memory_file = service.get_memory_file_with_migration(
                memories_dir, "version-control"
            )
            assert memory_file.name == "version_control_memories.md"

            # Test version_control with underscore
            memory_file2 = service.get_memory_file_with_migration(
                memories_dir, "version_control"
            )
            assert memory_file2.name == "version_control_memories.md"

            # Both should point to the same file
            assert memory_file == memory_file2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
