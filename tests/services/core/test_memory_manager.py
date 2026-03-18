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
        """Test loading memories with cache miss.

        normalize_agent_id("test") = "test", so deployed set uses "test".
        The memory file test_memories.md has raw_agent_name "test" which
        normalizes to "test" — matching the deployed agent.
        """
        # Setup cache miss
        mock_cache_manager.get_memories.return_value = None
        # Use "test" as deployed agent (normalize_agent_id("test_agent") = "test")
        mock_cache_manager.get_deployed_agents.return_value = {"test"}

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test memory files
            memories_dir = Path(tmpdir) / ".claude-mpm" / "memories"
            memories_dir.mkdir(parents=True)

            pm_file = memories_dir / "PM_memories.md"
            pm_file.write_text("# PM Memory\n- Test PM memory")

            # Use canonical filename: normalize_agent_id produces "test"
            agent_file = memories_dir / "test_memories.md"
            agent_file.write_text("# Agent Memory: test\n- Test agent memory")

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
            assert "test" in result["agent_memories"]

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
            mock_path_resolver.ensure_directory.side_effect = lambda p: (
                p.mkdir(parents=True, exist_ok=True) or p
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
        """Test saving an agent-specific memory.

        normalize_agent_id("test_agent") = "test", so file is test_memories.md.
        The header uses the raw agent_name "test_agent" for display.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / ".claude-mpm" / "memories"

            # Configure mock to actually create the directory
            mock_path_resolver.ensure_directory.side_effect = lambda p: (
                p.mkdir(parents=True, exist_ok=True) or p
            )

            with patch(
                "claude_mpm.services.core.memory_manager.Path.cwd",
                return_value=Path(tmpdir),
            ):
                # Save agent memory
                memory_manager.save_memory("test_key", "test_value", "test_agent")

            # normalize_agent_id("test_agent") = "test" -> test_memories.md
            agent_file = memories_dir / "test_memories.md"
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
        """Test clearing memories for a specific agent.

        normalize_agent_id("test_agent") = "test", so clear targets test_memories.md.
        other_agent normalizes to "other" -> other_memories.md is NOT the same file
        as other_agent_memories.md, but we test that only the target is deleted.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / ".claude-mpm" / "memories"
            memories_dir.mkdir(parents=True)

            # Create test files with canonical names
            pm_file = memories_dir / "PM_memories.md"
            pm_file.write_text("# PM Memory")

            # normalize_agent_id("test_agent") = "test" -> test_memories.md
            agent_file = memories_dir / "test_memories.md"
            agent_file.write_text("# Agent Memory")

            # normalize_agent_id("other_agent") = "other" -> other_memories.md
            other_file = memories_dir / "other_memories.md"
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
        """Test memory loading with project-only scope (v4.7.10+).

        As of v4.7.10+, only project-level memories are loaded to prevent
        cross-project contamination. User-level memories are no longer loaded.
        """
        mock_cache_manager.get_deployed_agents.return_value = {"test_agent"}

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create user and project directories
            user_dir = Path(tmpdir) / "user" / ".claude-mpm" / "memories"
            user_dir.mkdir(parents=True)

            project_dir = Path(tmpdir) / "project" / ".claude-mpm" / "memories"
            project_dir.mkdir(parents=True)

            # Create memories in both locations
            # User-level should NOT be loaded (v4.7.10+)
            user_pm = user_dir / "PM_memories.md"
            user_pm.write_text("# PM Memory\n- User task 1\n- Common task")

            # Project-level should be loaded
            project_pm = project_dir / "PM_memories.md"
            project_pm.write_text("# PM Memory\n- Project task 1\n- Common task")

            # Mock paths
            with (
                patch(
                    "claude_mpm.services.core.memory_manager.Path.home",
                    return_value=Path(tmpdir) / "user",
                ),
                patch(
                    "claude_mpm.services.core.memory_manager.Path.cwd",
                    return_value=Path(tmpdir) / "project",
                ),
            ):
                # Load memories
                result = memory_manager.load_memories()

            # Verify only project-level memories are loaded (v4.7.10+)
            assert "actual_memories" in result
            content = result["actual_memories"]

            # Should ONLY have project tasks (user tasks NOT loaded)
            assert "user task 1" not in content.lower(), (
                "User-level memories should NOT be loaded"
            )
            assert "project task 1" in content.lower(), (
                "Project-level memories should be loaded"
            )
            assert "common task" in content.lower(), (
                "Project-level common task should be present"
            )

    def test_naming_mismatch_warning(self, memory_manager, mock_cache_manager):
        """Test warning for agent naming mismatches.

        Mismatch detection triggers when normalize_agent_id produces a name
        (e.g. "python-engineer") not in the deployed set, but the alt_name
        (swapping hyphens/underscores) IS in the deployed set.

        File: python_engineer_memories.md -> raw "python_engineer"
              -> normalize_agent_id = "python-engineer"
        Deployed: {"python_engineer"} (un-normalized, dash/underscore mismatch)
        alt_name: "python_engineer" (swap - to _) -> found in deployed -> WARNING
        """
        mock_cache_manager.get_deployed_agents.return_value = {
            "python_engineer"
        }  # With underscore (un-normalized)

        with tempfile.TemporaryDirectory() as tmpdir:
            memories_dir = Path(tmpdir) / ".claude-mpm" / "memories"
            memories_dir.mkdir(parents=True)

            # Create memory file with underscore naming
            agent_file = memories_dir / "python_engineer_memories.md"
            agent_file.write_text("# Agent Memory\n- some learning")

            with patch(
                "claude_mpm.services.core.memory_manager.Path.cwd",
                return_value=Path(tmpdir),
            ):
                # Patch the logger on the instance to capture warnings regardless
                # of logging propagation state (hook tests may suppress propagation)
                with patch.object(memory_manager, "logger") as mock_logger:
                    memory_manager.load_memories()

                    # Verify warning was logged
                    warning_messages = " ".join(
                        str(call) for call in mock_logger.warning.call_args_list
                    )
                    assert "Naming mismatch detected" in warning_messages
                    assert "python-engineer" in warning_messages
                    assert "python_engineer" in warning_messages


class TestGetDeployedAgentsNormalization:
    """Tests for Phase H6: _get_deployed_agents() normalization.

    Verifies that _get_deployed_agents() returns normalized agent IDs
    (lowercase, kebab-case, no -agent suffix) regardless of the on-disk
    filename convention.
    """

    @pytest.fixture
    def mock_cache_manager(self):
        """Create a mock cache manager."""
        cache = MagicMock(spec=ICacheManager)
        cache.get_memories.return_value = None
        cache.get_deployed_agents.return_value = None  # Cache miss
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

    def test_get_deployed_agents_normalizes_underscore_stems(
        self, memory_manager, mock_cache_manager
    ):
        """Deploy file named dart_engineer.md, verify returns {'dart-engineer'}."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / ".claude" / "agents"
            agents_dir.mkdir(parents=True)

            (agents_dir / "dart_engineer.md").write_text("# Dart Engineer")

            with patch(
                "claude_mpm.utils.agent_filters.Path.cwd",
                return_value=Path(tmpdir),
            ):
                deployed = memory_manager._get_deployed_agents()

            assert "dart-engineer" in deployed
            assert "dart_engineer" not in deployed

    def test_get_deployed_agents_normalizes_uppercase_stems(
        self, memory_manager, mock_cache_manager
    ):
        """Deploy file named ENGINEER.md, verify returns {'engineer'}."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / ".claude" / "agents"
            agents_dir.mkdir(parents=True)

            (agents_dir / "ENGINEER.md").write_text("# Engineer")

            with patch(
                "claude_mpm.utils.agent_filters.Path.cwd",
                return_value=Path(tmpdir),
            ):
                deployed = memory_manager._get_deployed_agents()

            assert "engineer" in deployed
            assert "ENGINEER" not in deployed

    def test_get_deployed_agents_strips_agent_suffix(
        self, memory_manager, mock_cache_manager
    ):
        """Deploy file named research-agent.md, verify returns {'research'}."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / ".claude" / "agents"
            agents_dir.mkdir(parents=True)

            (agents_dir / "research-agent.md").write_text("# Research Agent")

            with patch(
                "claude_mpm.utils.agent_filters.Path.cwd",
                return_value=Path(tmpdir),
            ):
                deployed = memory_manager._get_deployed_agents()

            assert "research" in deployed
            assert "research-agent" not in deployed

    def test_get_deployed_agents_uses_cache_when_available(
        self, memory_manager, mock_cache_manager
    ):
        """Verify cache is used when available, bypassing filesystem scan."""
        mock_cache_manager.get_deployed_agents.return_value = {"cached-agent"}

        deployed = memory_manager._get_deployed_agents()

        assert deployed == {"cached-agent"}
        mock_cache_manager.set_deployed_agents.assert_not_called()

    def test_get_deployed_agents_caches_result_on_miss(
        self, memory_manager, mock_cache_manager
    ):
        """Verify scan result is cached on cache miss."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / ".claude" / "agents"
            agents_dir.mkdir(parents=True)

            (agents_dir / "qa.md").write_text("# QA")

            with patch(
                "claude_mpm.utils.agent_filters.Path.cwd",
                return_value=Path(tmpdir),
            ):
                deployed = memory_manager._get_deployed_agents()

            assert "qa" in deployed
            mock_cache_manager.set_deployed_agents.assert_called_once()

    def test_deployed_agent_memories_loaded_with_underscore_filenames(
        self, memory_manager, mock_cache_manager
    ):
        """Deploy dart_engineer.md agent, create dart-engineer_memories.md, verify loaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir) / ".claude" / "agents"
            agents_dir.mkdir(parents=True)
            (agents_dir / "dart_engineer.md").write_text("# Dart Engineer")

            memories_dir = Path(tmpdir) / ".claude-mpm" / "memories"
            memories_dir.mkdir(parents=True)
            (memories_dir / "dart-engineer_memories.md").write_text(
                "# Agent Memory: dart-engineer\n- Dart test memory"
            )

            with (
                patch(
                    "claude_mpm.services.core.memory_manager.Path.cwd",
                    return_value=Path(tmpdir),
                ),
                patch(
                    "claude_mpm.utils.agent_filters.Path.cwd",
                    return_value=Path(tmpdir),
                ),
            ):
                result = memory_manager.load_memories()

            assert "agent_memories" in result
            assert "dart-engineer" in result["agent_memories"]
            assert "Dart test memory" in result["agent_memories"]["dart-engineer"]
