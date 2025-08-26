"""
Unit tests for MemoryManager service.

Tests cover:
- Memory loading from user and project directories
- Memory aggregation and deduplication
- Legacy format migration
- Caching behavior
- Memory search and statistics
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.core.memory_manager import MemoryManager
from claude_mpm.services.core.service_interfaces import ICacheManager, IPathResolver


class TestMemoryManager:
    """Test suite for MemoryManager service."""

    @pytest.fixture
    def mock_cache_manager(self):
        """Create a mock cache manager."""
        cache = MagicMock(spec=ICacheManager)
        cache.get_memories.return_value = None  # Default to cache miss
        cache.get_deployed_agents.return_value = None  # Default to cache miss
        return cache

    @pytest.fixture
    def mock_path_resolver(self):
        """Create a mock path resolver."""
        resolver = MagicMock(spec=IPathResolver)
        resolver.ensure_directory.side_effect = lambda p: p
        return resolver

    @pytest.fixture
    def memory_manager(self, mock_cache_manager, mock_path_resolver):
        """Create a MemoryManager instance with mocked dependencies."""
        return MemoryManager(
            cache_manager=mock_cache_manager, path_resolver=mock_path_resolver
        )

    def test_load_memories_cache_hit(self, memory_manager, mock_cache_manager):
        """Test loading memories with cache hit."""
        # Setup cache hit
        cached_data = {
            "actual_memories": "# PM Memory\n- Test memory",
            "agent_memories": {"test_agent": "# Agent Memory\n- Agent test"},
        }
        mock_cache_manager.get_memories.return_value = cached_data

        # Load memories
        result = memory_manager.load_memories()

        # Verify cache was used
        assert result == cached_data
        assert memory_manager._stats["cache_hits"] == 1
        assert memory_manager._stats["cache_misses"] == 0
        mock_cache_manager.get_memories.assert_called_once()

    def test_load_memories_cache_miss(self, memory_manager, mock_cache_manager):
        """Test loading memories with cache miss."""
        # Setup cache miss
        mock_cache_manager.get_memories.return_value = None
        mock_cache_manager.get_deployed_agents.return_value = {"test_agent"}

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test memory files
            memories_dir = Path(tmpdir) / ".claude-mpm" / "memories"
            memories_dir.mkdir(parents=True)

            pm_file = memories_dir / "PM_memories.md"
            pm_file.write_text("# PM Memory\n- Test PM memory")

            agent_file = memories_dir / "test_agent_memories.md"
            agent_file.write_text("# Agent Memory: test_agent\n- Test agent memory")

            # Mock Path.cwd() to return our temp directory
            with patch(
                "claude_mpm.services.core.memory_manager.Path.cwd",
                return_value=Path(tmpdir),
            ):
                # Load memories
                result = memory_manager.load_memories()

            # Verify memories were loaded
            assert "actual_memories" in result
            assert (
                "Test PM memory" in result["actual_memories"]
            )  # Check content, not header
            assert "agent_memories" in result
            assert "test_agent" in result["agent_memories"]

            # Verify cache was updated
            mock_cache_manager.set_memories.assert_called_once()
            assert memory_manager._stats["cache_misses"] == 1

    def test_load_memories_for_specific_agent(self, memory_manager, mock_cache_manager):
        """Test loading memories for a specific agent."""
        # Setup cached data
        cached_data = {
            "actual_memories": "# PM Memory\n- Test memory",
            "agent_memories": {
                "test_agent": "# Agent Memory\n- Agent test",
                "other_agent": "# Agent Memory\n- Other test",
            },
        }
        mock_cache_manager.get_memories.return_value = cached_data

        # Load memories for specific agent
        result = memory_manager.load_memories("test_agent")

        # Verify only requested agent memories are returned
        assert "actual_memories" in result
        assert len(result["agent_memories"]) == 1
        assert "test_agent" in result["agent_memories"]
        assert "other_agent" not in result["agent_memories"]

    def test_save_memory_pm(
        self, memory_manager, mock_cache_manager, mock_path_resolver
    ):
        """Test saving a PM memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / ".claude-mpm" / "memories"

            # Configure mock to actually create the directory
            mock_path_resolver.ensure_directory.side_effect = (
                lambda p: p.mkdir(parents=True, exist_ok=True) or p
            )

            with patch(
                "claude_mpm.services.core.memory_manager.Path.cwd",
                return_value=Path(tmpdir),
            ):
                # Save PM memory
                memory_manager.save_memory("test_key", "test_value")

            # Verify file was created
            pm_file = memories_dir / "PM_memories.md"
            assert pm_file.exists()
            content = pm_file.read_text()
            assert "test_key: test_value" in content

            # Verify cache was cleared
            mock_cache_manager.clear_memory_caches.assert_called_once()

    def test_save_memory_agent(
        self, memory_manager, mock_cache_manager, mock_path_resolver
    ):
        """Test saving an agent-specific memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / ".claude-mpm" / "memories"

            # Configure mock to actually create the directory
            mock_path_resolver.ensure_directory.side_effect = (
                lambda p: p.mkdir(parents=True, exist_ok=True) or p
            )

            with patch(
                "claude_mpm.services.core.memory_manager.Path.cwd",
                return_value=Path(tmpdir),
            ):
                # Save agent memory
                memory_manager.save_memory("test_key", "test_value", "test_agent")

            # Verify file was created
            agent_file = memories_dir / "test_agent_memories.md"
            assert agent_file.exists()
            content = agent_file.read_text()
            assert "Agent Memory: test_agent" in content
            assert "test_key: test_value" in content

    def test_search_memories(self, memory_manager, mock_cache_manager):
        """Test searching memories."""
        # Setup cached data
        cached_data = {
            "actual_memories": "# PM Memory\n- Important task\n- Regular task",
            "agent_memories": {
                "test_agent": "# Agent Memory\n- Important agent task\n- Other task"
            },
        }
        mock_cache_manager.get_memories.return_value = cached_data

        # Search for "Important"
        results = memory_manager.search_memories("Important")

        # Verify results
        assert len(results) == 2
        assert any(
            r["type"] == "PM" and "Important task" in r["content"] for r in results
        )
        assert any(
            r["type"] == "Agent" and "Important agent task" in r["content"]
            for r in results
        )

    def test_clear_memories_all(self, memory_manager, mock_cache_manager):
        """Test clearing all memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / ".claude-mpm" / "memories"
            memories_dir.mkdir(parents=True)

            # Create test files
            pm_file = memories_dir / "PM_memories.md"
            pm_file.write_text("# PM Memory")

            agent_file = memories_dir / "test_agent_memories.md"
            agent_file.write_text("# Agent Memory")

            with patch(
                "claude_mpm.services.core.memory_manager.Path.cwd",
                return_value=Path(tmpdir),
            ):
                # Clear all memories
                memory_manager.clear_memories()

            # Verify files were deleted
            assert not pm_file.exists()
            assert not agent_file.exists()

            # Verify cache was cleared
            mock_cache_manager.clear_memory_caches.assert_called_once()

    def test_clear_memories_specific_agent(self, memory_manager, mock_cache_manager):
        """Test clearing memories for a specific agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / ".claude-mpm" / "memories"
            memories_dir.mkdir(parents=True)

            # Create test files
            pm_file = memories_dir / "PM_memories.md"
            pm_file.write_text("# PM Memory")

            agent_file = memories_dir / "test_agent_memories.md"
            agent_file.write_text("# Agent Memory")

            other_file = memories_dir / "other_agent_memories.md"
            other_file.write_text("# Agent Memory")

            with patch(
                "claude_mpm.services.core.memory_manager.Path.cwd",
                return_value=Path(tmpdir),
            ):
                # Clear specific agent memories
                memory_manager.clear_memories("test_agent")

            # Verify only specific file was deleted
            assert pm_file.exists()
            assert not agent_file.exists()
            assert other_file.exists()

    def test_get_memory_stats(self, memory_manager, mock_cache_manager):
        """Test getting memory statistics."""
        # Setup cached data
        cached_data = {
            "actual_memories": "# PM Memory\n- Test memory",
            "agent_memories": {
                "agent1": "# Agent Memory\n- Agent 1 memory",
                "agent2": "# Agent Memory\n- Agent 2 memory",
            },
        }
        mock_cache_manager.get_memories.return_value = cached_data

        # Get stats
        stats = memory_manager.get_memory_stats()

        # Verify stats
        assert stats["pm_memory_size"] > 0
        assert stats["agent_count"] == 2
        assert stats["total_agent_memory_size"] > 0
        assert "cache_hits" in stats
        assert "cache_misses" in stats

    def test_aggregate_memories_deduplication(self, memory_manager):
        """Test memory aggregation with deduplication."""
        memory_entries = [
            {
                "source": "user",
                "content": "# Agent Memory\n- Task 1\n- Task 2\n- Common task",
                "path": Path("user_memory.md"),
            },
            {
                "source": "project",
                "content": "# Agent Memory\n- Task 3\n- Common task\n- Task 2",
                "path": Path("project_memory.md"),
            },
        ]

        # Aggregate memories
        result = memory_manager._aggregate_memories(memory_entries)

        # Verify deduplication
        lines = result.split("\n")
        task_lines = [l for l in lines if l.strip().startswith("-")]

        # Should have 4 unique tasks (Task 1, Task 2, Task 3, Common task)
        assert len(task_lines) == 4

        # Verify no exact duplicates
        assert len(task_lines) == len(set(task_lines))

    def test_migrate_legacy_file(self, memory_manager):
        """Test legacy file migration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create old format file
            old_file = Path(tmpdir) / "test_agent.md"
            old_file.write_text("# Old format memory")

            new_file = Path(tmpdir) / "test_agent_memories.md"

            # Migrate file
            memory_manager._migrate_legacy_file(old_file, new_file)

            # Verify migration
            assert not old_file.exists()
            assert new_file.exists()
            assert new_file.read_text() == "# Old format memory"

    def test_migrate_pm_legacy_file(self, memory_manager, mock_cache_manager):
        """Test PM.md to PM_memories.md migration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / ".claude-mpm" / "memories"
            memories_dir.mkdir(parents=True)

            # Create old PM.md file
            old_pm = memories_dir / "PM.md"
            old_pm.write_text("# Old PM format")

            mock_cache_manager.get_deployed_agents.return_value = set()

            with patch(
                "claude_mpm.services.core.memory_manager.Path.cwd",
                return_value=Path(tmpdir),
            ):
                # Load memories (should trigger migration)
                memory_manager.load_memories()

            # Verify migration
            new_pm = memories_dir / "PM_memories.md"
            assert new_pm.exists()
            assert new_pm.read_text() == "# Old PM format"
            assert not old_pm.exists()

    def test_load_memories_with_priority(self, memory_manager, mock_cache_manager):
        """Test memory loading with user/project priority."""
        mock_cache_manager.get_deployed_agents.return_value = {"test_agent"}

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create user and project directories
            user_dir = Path(tmpdir) / "user" / ".claude-mpm" / "memories"
            user_dir.mkdir(parents=True)

            project_dir = Path(tmpdir) / "project" / ".claude-mpm" / "memories"
            project_dir.mkdir(parents=True)

            # Create conflicting memories
            user_pm = user_dir / "PM_memories.md"
            user_pm.write_text("# PM Memory\n- User task 1\n- Common task")

            project_pm = project_dir / "PM_memories.md"
            project_pm.write_text("# PM Memory\n- Project task 1\n- Common task")

            # Mock paths
            with patch(
                "claude_mpm.services.core.memory_manager.Path.home",
                return_value=Path(tmpdir) / "user",
            ), patch(
                "claude_mpm.services.core.memory_manager.Path.cwd",
                return_value=Path(tmpdir) / "project",
            ):
                # Load memories
                result = memory_manager.load_memories()

            # Verify project overrides user for common items
            assert "actual_memories" in result
            content = result["actual_memories"]

            # Should have both unique tasks and the common task
            assert "user task 1" in content.lower()
            assert "project task 1" in content.lower()
            assert "common task" in content.lower()

    def test_naming_mismatch_warning(self, memory_manager, mock_cache_manager, caplog):
        """Test warning for agent naming mismatches."""
        mock_cache_manager.get_deployed_agents.return_value = {
            "test-agent"
        }  # With dash

        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / ".claude-mpm" / "memories"
            memories_dir.mkdir(parents=True)

            # Create memory file with underscore
            agent_file = memories_dir / "test_agent_memories.md"  # With underscore
            agent_file.write_text("# Agent Memory")

            with patch(
                "claude_mpm.services.core.memory_manager.Path.cwd",
                return_value=Path(tmpdir),
            ):
                # Load memories
                memory_manager.load_memories()

            # Verify warning was logged
            assert "Naming mismatch detected" in caplog.text
            assert "test_agent" in caplog.text
            assert "test-agent" in caplog.text
