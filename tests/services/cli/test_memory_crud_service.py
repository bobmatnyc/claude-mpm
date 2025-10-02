"""
Tests for Memory CRUD Service
==============================

WHY: Comprehensive test coverage for all memory CRUD operations ensures reliable
memory management across the system. These tests validate both successful operations
and error handling scenarios.

DESIGN DECISIONS:
- Mock AgentMemoryManager to isolate service logic
- Test each CRUD operation independently
- Verify error handling and edge cases
- Test integration with memory manager
- Validate structured data returns
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.cli.memory_crud_service import (
    IMemoryCRUDService,
    MemoryCRUDService,
)


class TestMemoryCRUDServiceInterface:
    """Test that MemoryCRUDService implements IMemoryCRUDService interface."""

    def test_implements_interface(self):
        """Verify service implements all required interface methods."""
        service = MemoryCRUDService()
        assert isinstance(service, IMemoryCRUDService)

        # Check all interface methods are implemented
        assert hasattr(service, "create_memory")
        assert hasattr(service, "read_memory")
        assert hasattr(service, "update_memory")
        assert hasattr(service, "delete_memory")
        assert hasattr(service, "list_memories")
        assert hasattr(service, "clean_memory")
        assert hasattr(service, "init_project_memories")


class TestMemoryCRUDService:
    """Test memory CRUD service operations."""

    @pytest.fixture
    def mock_memory_manager(self):
        """Create mock memory manager."""
        mock = MagicMock()
        mock.memories_dir = Path("/test/memories")
        mock.template_generator = MagicMock()
        return mock

    @pytest.fixture
    def service(self, mock_memory_manager):
        """Create service with mocked memory manager."""
        return MemoryCRUDService(memory_manager=mock_memory_manager)

    def test_create_memory_success(self, service, mock_memory_manager):
        """Test successful memory creation."""
        # Setup mocks
        mock_memory_manager.load_agent_memory.return_value = None  # No existing memory
        mock_memory_manager.template_generator.generate_template.return_value = (
            "# Test Template"
        )

        with patch("pathlib.Path.mkdir"), patch(
            "pathlib.Path.write_text"
        ) as mock_write:

            result = service.create_memory("test_agent", "default")

            assert result["success"] is True
            assert result["agent_id"] == "test_agent"
            assert "file_path" in result
            assert result["template_type"] == "default"
            mock_write.assert_called_once_with("# Test Template")

    def test_create_memory_already_exists(self, service, mock_memory_manager):
        """Test creation when memory already exists."""
        # Setup mocks
        mock_memory_manager.load_agent_memory.return_value = "Existing content"

        result = service.create_memory("test_agent", "default")

        assert result["success"] is False
        assert "already exists" in result["error"]
        assert result["agent_id"] == "test_agent"

    def test_read_memory_single_agent_success(self, service, mock_memory_manager):
        """Test reading memory for single agent."""
        # Setup mocks
        test_content = "# Test Memory Content"
        mock_memory_manager.load_agent_memory.return_value = test_content

        memory_file = MagicMock()
        memory_file.exists.return_value = True
        memory_file.stat.return_value = MagicMock(
            st_size=1024, st_mtime=datetime.now(timezone.utc).timestamp()
        )

        with patch.object(Path, "__truediv__", return_value=memory_file):
            result = service.read_memory("test_agent")

            assert result["success"] is True
            assert result["agent_id"] == "test_agent"
            assert result["content"] == test_content
            assert "file_stats" in result

    def test_read_memory_single_agent_not_found(self, service, mock_memory_manager):
        """Test reading memory when agent not found."""
        # Setup mocks
        mock_memory_manager.load_agent_memory.return_value = None

        result = service.read_memory("test_agent")

        assert result["success"] is False
        assert "No memory found" in result["error"]
        assert result["agent_id"] == "test_agent"

    def test_read_memory_all_agents(self, service, mock_memory_manager):
        """Test reading all agent memories."""
        # Setup mocks
        memory_dir = MagicMock()
        memory_dir.exists.return_value = True

        # Create mock memory files
        file1 = MagicMock()
        file1.name = "agent1_memories.md"
        file1.stem = "agent1_memories"
        file1.stat.return_value = MagicMock(
            st_size=1024,
            st_mtime=datetime.now(timezone.utc).timestamp(),
            st_ctime=datetime.now(timezone.utc).timestamp(),
        )

        file2 = MagicMock()
        file2.name = "agent2_memories.md"
        file2.stem = "agent2_memories"
        file2.stat.return_value = MagicMock(
            st_size=2048,
            st_mtime=datetime.now(timezone.utc).timestamp(),
            st_ctime=datetime.now(timezone.utc).timestamp(),
        )

        mock_memory_manager.memories_dir = memory_dir
        mock_memory_manager.load_agent_memory.side_effect = ["Content 1", "Content 2"]

        with patch.object(service, "_get_memory_files", return_value=[file1, file2]):
            result = service.read_memory(None)

            assert result["success"] is True
            assert "agents" in result
            assert len(result["agents"]) == 2
            assert "agent1" in result["agents"]
            assert "agent2" in result["agents"]

    def test_update_memory_success(self, service, mock_memory_manager):
        """Test successful memory update."""
        # Setup mocks
        mock_memory_manager.update_agent_memory.return_value = True

        result = service.update_memory(
            "test_agent", "pattern", "Use dependency injection"
        )

        assert result["success"] is True
        assert result["agent_id"] == "test_agent"
        assert result["section"] == "Project Architecture"
        assert "content_preview" in result
        mock_memory_manager.update_agent_memory.assert_called_once_with(
            "test_agent", "Project Architecture", "Use dependency injection"
        )

    def test_update_memory_failure(self, service, mock_memory_manager):
        """Test memory update failure."""
        # Setup mocks
        mock_memory_manager.update_agent_memory.return_value = False

        result = service.update_memory(
            "test_agent", "pattern", "Use dependency injection"
        )

        assert result["success"] is False
        assert "size limit" in result["error"]

    def test_delete_memory_without_confirmation(self, service):
        """Test deletion without confirmation flag."""
        result = service.delete_memory("test_agent", confirm=False)

        assert result["success"] is False
        assert "confirmation flag" in result["error"]
        assert "--confirm" in result["hint"]

    def test_delete_memory_success(self, service, mock_memory_manager):
        """Test successful memory deletion."""
        # Setup mocks
        memory_file = MagicMock()
        memory_file.exists.return_value = True
        memory_file.stat.return_value = MagicMock(st_size=2048)

        with patch.object(Path, "__truediv__", return_value=memory_file):
            result = service.delete_memory("test_agent", confirm=True)

            assert result["success"] is True
            assert result["agent_id"] == "test_agent"
            assert "deleted_file" in result
            assert result["file_size_kb"] == 2.0
            memory_file.unlink.assert_called_once()

    def test_delete_memory_not_found(self, service, mock_memory_manager):
        """Test deletion when memory not found."""
        # Setup mocks
        memory_file = MagicMock()
        memory_file.exists.return_value = False

        with patch.object(Path, "__truediv__", return_value=memory_file):
            result = service.delete_memory("test_agent", confirm=True)

            assert result["success"] is False
            assert "No memory file found" in result["error"]

    def test_list_memories_empty(self, service, mock_memory_manager):
        """Test listing when no memories exist."""
        # Setup mocks
        memory_dir = MagicMock()
        memory_dir.exists.return_value = False
        mock_memory_manager.memories_dir = memory_dir

        result = service.list_memories()

        assert result["success"] is True
        assert result["exists"] is False
        assert result["total_files"] == 0
        assert len(result["memories"]) == 0

    def test_list_memories_with_stats(self, service, mock_memory_manager):
        """Test listing memories with statistics."""
        # Setup mocks
        memory_dir = MagicMock()
        memory_dir.exists.return_value = True
        mock_memory_manager.memories_dir = memory_dir

        # Create mock memory files
        file1 = MagicMock()
        file1.name = "agent1_memories.md"
        file1.stem = "agent1_memories"
        file1.stat.return_value = MagicMock(
            st_size=1024,
            st_mtime=datetime.now(timezone.utc).timestamp(),
            st_ctime=datetime.now(timezone.utc).timestamp(),
        )

        with patch.object(service, "_get_memory_files", return_value=[file1]):
            result = service.list_memories(include_stats=True)

            assert result["success"] is True
            assert result["exists"] is True
            assert result["total_files"] == 1
            assert len(result["memories"]) == 1
            assert "size_kb" in result["memories"][0]
            assert "modified" in result["memories"][0]

    def test_clean_memory_dry_run(self, service, mock_memory_manager):
        """Test memory cleanup in dry run mode."""
        # Setup mocks
        memory_dir = MagicMock()
        memory_dir.exists.return_value = True
        mock_memory_manager.memories_dir = memory_dir

        # Create old memory file
        old_file = MagicMock()
        old_file.name = "old_agent_memories.md"
        old_file.stem = "old_agent_memories"

        # Mock old modification time (35 days ago)
        old_timestamp = datetime.now(timezone.utc).timestamp() - (35 * 24 * 60 * 60)
        old_file.stat.return_value = MagicMock(st_size=1024, st_mtime=old_timestamp)

        with patch.object(service, "_get_memory_files", return_value=[old_file]):
            result = service.clean_memory(dry_run=True)

            assert result["success"] is True
            assert result["dry_run"] is True
            assert len(result["cleanup_candidates"]) == 1
            assert result["cleanup_candidates"][0]["age_days"] >= 35

    def test_clean_memory_specific_agent(self, service, mock_memory_manager):
        """Test cleanup for specific agent."""
        # Setup mocks
        memory_dir = MagicMock()
        memory_dir.exists.return_value = True
        mock_memory_manager.memories_dir = memory_dir

        # Create multiple memory files
        file1 = MagicMock()
        file1.name = "agent1_memories.md"
        file1.stem = "agent1_memories"
        file1.stat.return_value = MagicMock(
            st_size=1024,
            st_mtime=(datetime.now(timezone.utc).timestamp() - (35 * 24 * 60 * 60)),
        )

        file2 = MagicMock()
        file2.name = "agent2_memories.md"
        file2.stem = "agent2_memories"
        file2.stat.return_value = MagicMock(
            st_size=2048,
            st_mtime=(datetime.now(timezone.utc).timestamp() - (35 * 24 * 60 * 60)),
        )

        with patch.object(service, "_get_memory_files", return_value=[file1, file2]):
            result = service.clean_memory(agent_id="agent1", dry_run=True)

            assert result["success"] is True
            assert len(result["cleanup_candidates"]) == 1
            assert result["cleanup_candidates"][0]["agent_id"] == "agent1"

    def test_init_project_memories(self, service):
        """Test project memory initialization task creation."""
        result = service.init_project_memories()

        assert result["success"] is True
        assert "task_data" in result

        task = result["task_data"]
        assert task["task"] == "Initialize Project-Specific Memories"
        assert len(task["instructions"]) > 0
        assert len(task["focus_areas"]) > 0
        assert len(task["example_commands"]) > 0
        assert "claude-mpm memory add" in task["example_commands"][0]

    def test_extract_agent_id_various_formats(self, service):
        """Test agent ID extraction from various file formats."""
        # Test new format
        assert service._extract_agent_id(Path("agent1_memories.md")) == "agent1"

        # Test old format
        assert service._extract_agent_id(Path("agent2_agent.md")) == "agent2"

        # Test simple format
        assert service._extract_agent_id(Path("agent3.md")) == "agent3"

    def test_get_memory_files(self, service):
        """Test memory file discovery."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_dir = Path(tmpdir)

            # Create various format files
            (memory_dir / "agent1_memories.md").touch()
            (memory_dir / "agent2_agent.md").touch()
            (memory_dir / "agent3.md").touch()
            (memory_dir / "README.md").touch()  # Should be excluded

            files = service._get_memory_files(memory_dir)

            assert len(files) == 3
            file_names = {f.name for f in files}
            assert "agent1_memories.md" in file_names
            assert "agent2_agent.md" in file_names
            assert "agent3.md" in file_names
            assert "README.md" not in file_names


class TestMemoryCRUDServiceErrorHandling:
    """Test error handling in memory CRUD service."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return MemoryCRUDService()

    def test_create_memory_exception(self, service):
        """Test exception handling in create_memory."""
        with patch.object(service, "_get_memory_manager") as mock_get:
            mock_get.side_effect = Exception("Test error")

            result = service.create_memory("test_agent")

            assert result["success"] is False
            assert "Test error" in result["error"]

    def test_read_memory_exception(self, service):
        """Test exception handling in read_memory."""
        with patch.object(service, "_get_memory_manager") as mock_get:
            mock_get.side_effect = Exception("Read error")

            result = service.read_memory("test_agent")

            assert result["success"] is False
            assert "Read error" in result["error"]

    def test_update_memory_exception(self, service):
        """Test exception handling in update_memory."""
        with patch.object(service, "_get_memory_manager") as mock_get:
            mock_get.side_effect = Exception("Update error")

            result = service.update_memory("test_agent", "pattern", "content")

            assert result["success"] is False
            assert "Update error" in result["error"]

    def test_delete_memory_exception(self, service):
        """Test exception handling in delete_memory."""
        with patch.object(service, "_get_memory_manager") as mock_get:
            mock_get.side_effect = Exception("Delete error")

            result = service.delete_memory("test_agent", confirm=True)

            assert result["success"] is False
            assert "Delete error" in result["error"]

    def test_list_memories_exception(self, service):
        """Test exception handling in list_memories."""
        with patch.object(service, "_get_memory_manager") as mock_get:
            mock_get.side_effect = Exception("List error")

            result = service.list_memories()

            assert result["success"] is False
            assert "List error" in result["error"]


class TestMemoryCRUDServiceIntegration:
    """Test integration with AgentMemoryManager."""

    @pytest.mark.integration
    def test_lazy_memory_manager_creation(self):
        """Test lazy creation of memory manager."""
        service = MemoryCRUDService()

        # Memory manager should not be created yet
        assert service._memory_manager is None

        with patch(
            "claude_mpm.services.cli.memory_crud_service.AgentMemoryManager"
        ) as mock_class, patch("claude_mpm.core.shared.config_loader.ConfigLoader"):

            mock_instance = MagicMock()
            mock_instance.memories_dir = Path("/test")
            mock_instance.load_agent_memory.return_value = None
            mock_class.return_value = mock_instance

            # Trigger memory manager creation
            service.read_memory("test")

            # Memory manager should now be created
            assert service._memory_manager is not None
            mock_class.assert_called_once()
