"""Integration tests: memory lookup works with both old and new format files."""

from pathlib import Path

import pytest

from claude_mpm.services.agents.memory.memory_file_service import MemoryFileService


@pytest.fixture
def temp_memories_dir(tmp_path):
    memories_dir = tmp_path / "memories"
    memories_dir.mkdir()
    return memories_dir


class TestMemoryFileServiceMigration:
    def test_finds_kebab_case_file(self, temp_memories_dir):
        """Kebab-case file is found directly."""
        (temp_memories_dir / "python-engineer_memories.md").write_text("test")
        svc = MemoryFileService(temp_memories_dir)
        result = svc.get_memory_file_with_migration(
            temp_memories_dir, "python_engineer"
        )
        assert result.exists()
        assert result.name == "python-engineer_memories.md"

    def test_migrates_underscore_to_kebab(self, temp_memories_dir):
        """Underscore-format file is lazily migrated to kebab on access."""
        (temp_memories_dir / "python_engineer_memories.md").write_text("content")
        svc = MemoryFileService(temp_memories_dir)
        result = svc.get_memory_file_with_migration(
            temp_memories_dir, "python-engineer"
        )
        assert result.name == "python-engineer_memories.md"
        assert result.exists()
        assert not (temp_memories_dir / "python_engineer_memories.md").exists()

    def test_migrates_singular_memory(self, temp_memories_dir):
        """Legacy singular _memory.md is migrated to _memories.md."""
        (temp_memories_dir / "research_memory.md").write_text("old")
        svc = MemoryFileService(temp_memories_dir)
        result = svc.get_memory_file_with_migration(temp_memories_dir, "research")
        assert result.name == "research_memories.md"

    def test_strips_agent_suffix(self, temp_memories_dir):
        """Agent IDs with -agent suffix produce correct filenames."""
        svc = MemoryFileService(temp_memories_dir)
        result = svc.get_memory_file_with_migration(temp_memories_dir, "research-agent")
        assert result.name == "research_memories.md"

    def test_pm_normalizes_to_lowercase(self, temp_memories_dir):
        """PM normalizes to 'pm' (no special case)."""
        (temp_memories_dir / "PM_memories.md").write_text("PM memories")
        svc = MemoryFileService(temp_memories_dir)
        result = svc.get_memory_file_with_migration(temp_memories_dir, "PM")
        # PM_memories.md should be migrated to pm_memories.md
        assert result.name == "pm_memories.md"

    def test_no_migration_when_canonical_exists(self, temp_memories_dir):
        """If canonical file exists, legacy file is not touched."""
        (temp_memories_dir / "python-engineer_memories.md").write_text("new")
        (temp_memories_dir / "python_engineer_memories.md").write_text("old")
        svc = MemoryFileService(temp_memories_dir)
        result = svc.get_memory_file_with_migration(
            temp_memories_dir, "python_engineer"
        )
        assert result.name == "python-engineer_memories.md"
        # Legacy file untouched (no conflict resolution in lazy migration)
        assert (temp_memories_dir / "python_engineer_memories.md").exists()

    def test_empty_agent_id_handled(self, temp_memories_dir):
        """Empty agent ID does not crash."""
        svc = MemoryFileService(temp_memories_dir)
        result = svc.get_memory_file_with_migration(temp_memories_dir, "")
        assert result is not None

    def test_idempotent_migration(self, temp_memories_dir):
        """Calling migration twice produces the same result."""
        (temp_memories_dir / "golang_engineer_memories.md").write_text("content")
        svc = MemoryFileService(temp_memories_dir)
        result1 = svc.get_memory_file_with_migration(
            temp_memories_dir, "golang_engineer"
        )
        result2 = svc.get_memory_file_with_migration(
            temp_memories_dir, "golang_engineer"
        )
        assert result1 == result2
        assert result2.name == "golang-engineer_memories.md"
