"""Integration test: hook normalization -> memory file service pipeline.

Verifies that the agent_id produced by hook-layer normalization
matches what MemoryFileService.get_memory_file_with_migration() expects,
ensuring no memory file splits or duplicates.
"""

from pathlib import Path

import pytest

from claude_mpm.services.agents.memory.memory_file_service import MemoryFileService
from claude_mpm.utils.agent_filters import normalize_agent_id


class TestHookToMemoryPipeline:
    """End-to-end: hook normalization -> memory file lookup."""

    @pytest.mark.parametrize(
        "agent_display_name,expected_file_stem",
        [
            ("Engineer Agent", "engineer"),
            ("Python Engineer", "python-engineer"),
            ("Research Agent", "research"),
            ("Agent Manager", "agent-manager"),
            ("QA", "qa"),
            ("PM", "pm"),
            ("NestJS Engineer", "nestjs-engineer"),
            ("Data Engineer Agent", "data-engineer"),
        ],
    )
    def test_hook_normalization_matches_memory_service(
        self, tmp_path, agent_display_name, expected_file_stem
    ):
        """Hook's normalized agent_id resolves to the correct memory file."""
        memories_dir = tmp_path / "memories"
        memories_dir.mkdir()

        # Step 1: Simulate what the hook does (after CRIT-1 fix)
        agent_id = normalize_agent_id(agent_display_name)
        assert agent_id == expected_file_stem

        # Step 2: Pass through memory file service
        svc = MemoryFileService(memories_dir)
        result = svc.get_memory_file_with_migration(memories_dir, agent_id)

        # Step 3: Verify canonical file path
        assert result.name == f"{expected_file_stem}_memories.md"

    @pytest.mark.parametrize(
        "agent_display_name",
        [
            "Python Engineer",
            "Research Agent",
            "QA",
            "PM",
        ],
    )
    def test_no_duplicate_creation_on_repeated_access(
        self, tmp_path, agent_display_name
    ):
        """Two accesses with the same agent name produce the same file."""
        memories_dir = tmp_path / "memories"
        memories_dir.mkdir()

        agent_id = normalize_agent_id(agent_display_name)
        svc = MemoryFileService(memories_dir)

        # First access
        result1 = svc.get_memory_file_with_migration(memories_dir, agent_id)
        # Write something so the file exists
        result1.write_text("# Test memory")

        # Second access
        result2 = svc.get_memory_file_with_migration(memories_dir, agent_id)

        assert result1 == result2
        # Verify only one memory file exists
        memory_files = list(memories_dir.glob("*_memories.md"))
        assert len(memory_files) == 1

    def test_legacy_underscore_file_migrated_on_hook_access(self, tmp_path):
        """Pre-existing underscore-format file is found and migrated."""
        memories_dir = tmp_path / "memories"
        memories_dir.mkdir()

        # Simulate a legacy file created by the OLD hook normalization
        legacy_file = memories_dir / "python_engineer_memories.md"
        legacy_file.write_text("# Legacy memories")

        # Now simulate the NEW hook normalization
        agent_id = normalize_agent_id("Python Engineer")
        assert agent_id == "python-engineer"

        svc = MemoryFileService(memories_dir)
        result = svc.get_memory_file_with_migration(memories_dir, agent_id)

        # Should migrate to canonical name
        assert result.name == "python-engineer_memories.md"
        assert result.exists()
        assert result.read_text() == "# Legacy memories"
        # Legacy file should be gone
        assert not legacy_file.exists()
