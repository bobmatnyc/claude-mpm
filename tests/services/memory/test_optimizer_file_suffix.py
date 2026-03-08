"""
Tests for Phase H5: Memory optimizer file suffix fix (_agent.md -> _memories.md).

Verifies that the MemoryOptimizer correctly uses *_memories.md file suffix
instead of the legacy *_agent.md suffix.
"""

import tempfile
from pathlib import Path

import pytest

from claude_mpm.services.memory.optimizer import MemoryOptimizer


class TestOptimizerFileSuffix:
    """Tests verifying the optimizer uses *_memories.md file suffix."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for memory files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def optimizer(self, temp_dir):
        """Create a MemoryOptimizer with temp directory."""
        optimizer = MemoryOptimizer(working_directory=temp_dir)
        return optimizer

    @pytest.fixture
    def memories_dir(self, temp_dir):
        """Create and return the memories directory."""
        d = temp_dir / ".claude-mpm" / "memories"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _create_memory_file(
        self, memories_dir: Path, agent_id: str, suffix: str
    ) -> Path:
        """Helper to create a memory file with given suffix and minimal content."""
        filename = f"{agent_id}{suffix}"
        filepath = memories_dir / filename
        content = (
            f"# {agent_id} Agent Memory\n"
            f"<!-- Last Updated: 2025-01-01 00:00:00 | Auto-updated by: test -->\n"
            "\n"
            "## Recent Learnings\n"
            "- Learning item one\n"
            "- Learning item two\n"
        )
        filepath.write_text(content, encoding="utf-8")
        return filepath

    def test_optimize_agent_memory_finds_memories_file(self, optimizer, memories_dir):
        """Optimizer should find *_memories.md files, not *_agent.md files."""
        # Create a _memories.md file
        self._create_memory_file(memories_dir, "python-engineer", "_memories.md")

        result = optimizer.optimize_agent_memory("python-engineer")

        assert result["success"] is True
        assert result["agent_id"] == "python-engineer"

    def test_optimize_agent_memory_does_not_find_agent_suffix(
        self, optimizer, memories_dir
    ):
        """Optimizer should NOT find *_agent.md files (legacy suffix)."""
        # Create only a _agent.md file (legacy)
        self._create_memory_file(memories_dir, "python-engineer", "_agent.md")

        result = optimizer.optimize_agent_memory("python-engineer")

        # Should report file not found since we only look for _memories.md now
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_optimize_all_globs_memories_files(self, optimizer, memories_dir):
        """optimize_all_memories should glob for *_memories.md and find all of them."""
        # Create two _memories.md files
        self._create_memory_file(memories_dir, "python-engineer", "_memories.md")
        self._create_memory_file(memories_dir, "qa", "_memories.md")

        result = optimizer.optimize_all_memories()

        assert result["success"] is True
        summary = result["summary"]
        assert summary["agents_processed"] == 2
        # Both agents should be found
        assert "python-engineer" in result["agents"]
        assert "qa" in result["agents"]

    def test_optimizer_ignores_agent_suffix_files(self, optimizer, memories_dir):
        """optimize_all_memories should NOT pick up *_agent.md files."""
        # Create only _agent.md files (legacy)
        self._create_memory_file(memories_dir, "python-engineer", "_agent.md")
        self._create_memory_file(memories_dir, "qa", "_agent.md")

        result = optimizer.optimize_all_memories()

        assert result["success"] is True
        summary = result["summary"]
        # No agents should be processed because we only glob *_memories.md
        assert summary["agents_processed"] == 0

    def test_analyze_single_agent_uses_memories_suffix(self, optimizer, memories_dir):
        """_analyze_single_agent should look for *_memories.md files."""
        self._create_memory_file(memories_dir, "data-engineer", "_memories.md")

        result = optimizer.analyze_optimization_opportunities(agent_id="data-engineer")

        assert result["success"] is True
        assert result["agent_id"] == "data-engineer"

    def test_analyze_single_agent_not_found_with_agent_suffix(
        self, optimizer, memories_dir
    ):
        """_analyze_single_agent should NOT find *_agent.md files."""
        self._create_memory_file(memories_dir, "data-engineer", "_agent.md")

        result = optimizer.analyze_optimization_opportunities(agent_id="data-engineer")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_analyze_all_agents_globs_memories_files(self, optimizer, memories_dir):
        """_analyze_all_agents should glob for *_memories.md files."""
        self._create_memory_file(memories_dir, "python-engineer", "_memories.md")
        self._create_memory_file(memories_dir, "qa", "_memories.md")

        result = optimizer.analyze_optimization_opportunities()

        assert result["success"] is True
        assert result["agents_analyzed"] == 2
        assert "python-engineer" in result["agents"]
        assert "qa" in result["agents"]

    def test_analyze_all_agents_ignores_agent_suffix(self, optimizer, memories_dir):
        """_analyze_all_agents should NOT pick up *_agent.md files."""
        self._create_memory_file(memories_dir, "python-engineer", "_agent.md")

        result = optimizer.analyze_optimization_opportunities()

        assert result["success"] is True
        assert result["agents_analyzed"] == 0

    def test_optimize_all_extracts_agent_id_from_memories_stem(
        self, optimizer, memories_dir
    ):
        """Agent IDs extracted from filenames should strip _memories, not _agent."""
        # Create file: dart-engineer_memories.md -> agent_id should be "dart-engineer"
        self._create_memory_file(memories_dir, "dart-engineer", "_memories.md")

        result = optimizer.optimize_all_memories()

        assert result["success"] is True
        # The key should be "dart-engineer", not "dart-engineer_memories" or something else
        assert "dart-engineer" in result["agents"]
        assert result["agents"]["dart-engineer"]["success"] is True
