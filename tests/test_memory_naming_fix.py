"""Test that memory file naming handles both hyphen and underscore conventions."""

import tempfile
from pathlib import Path

import pytest

from claude_mpm.services.agents.memory.memory_file_service import MemoryFileService


class TestMemoryFileNaming:
    """Test memory file naming normalization."""

    def test_normalizes_hyphenated_agent_id(self):
        """Test that hyphenated agent IDs produce canonical kebab-case filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / "memories"
            memories_dir.mkdir()

            service = MemoryFileService(memories_dir)

            # Request memory file with hyphenated ID
            memory_file = service.get_memory_file_with_migration(
                memories_dir, "data-engineer"
            )

            # normalize_agent_id("data-engineer") = "data-engineer"
            assert memory_file.name == "data-engineer_memories.md"

    def test_migrates_underscore_file_to_kebab(self):
        """Test that existing underscore files are migrated to kebab-case."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / "memories"
            memories_dir.mkdir()

            # Create existing file with underscores (legacy format)
            legacy_file = memories_dir / "data_engineer_memories.md"
            legacy_file.write_text("# Existing memory")

            service = MemoryFileService(memories_dir)

            # Request with hyphenated ID
            memory_file = service.get_memory_file_with_migration(
                memories_dir, "data-engineer"
            )

            # normalize_agent_id("data-engineer") = "data-engineer"
            # Legacy underscore file should be migrated to kebab-case
            assert memory_file.name == "data-engineer_memories.md"
            assert memory_file.exists()
            assert memory_file.read_text() == "# Existing memory"
            assert not legacy_file.exists()  # Old file should be renamed

    def test_finds_existing_kebab_case_file(self):
        """Test that existing kebab-case file is found directly (no migration needed)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / "memories"
            memories_dir.mkdir()

            # Create canonical kebab-case file
            canonical_file = memories_dir / "data-engineer_memories.md"
            canonical_file.write_text("# Kebab memory")

            service = MemoryFileService(memories_dir)

            # Request memory file
            memory_file = service.get_memory_file_with_migration(
                memories_dir, "data-engineer"
            )

            # Should find existing canonical file directly
            assert memory_file.name == "data-engineer_memories.md"
            assert memory_file.exists()
            assert memory_file.read_text() == "# Kebab memory"

    def test_handles_underscore_ids(self):
        """Test that underscore IDs produce canonical kebab-case filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / "memories"
            memories_dir.mkdir()

            service = MemoryFileService(memories_dir)

            # Request with underscore ID
            memory_file = service.get_memory_file_with_migration(
                memories_dir, "data_engineer"
            )

            # normalize_agent_id("data_engineer") = "data-engineer"
            assert memory_file.name == "data-engineer_memories.md"

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
        """Test version-control agent name handling with canonical kebab-case."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / "memories"
            memories_dir.mkdir()

            service = MemoryFileService(memories_dir)

            # Test version-control with hyphen
            # normalize_agent_id("version-control") = "version-control"
            memory_file = service.get_memory_file_with_migration(
                memories_dir, "version-control"
            )
            assert memory_file.name == "version-control_memories.md"

            # Test version_control with underscore
            # normalize_agent_id("version_control") = "version-control"
            memory_file2 = service.get_memory_file_with_migration(
                memories_dir, "version_control"
            )
            assert memory_file2.name == "version-control_memories.md"

            # Both should point to the same file
            assert memory_file == memory_file2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
