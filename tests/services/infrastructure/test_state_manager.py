"""Tests for State Manager service."""

import asyncio
import json
import gzip
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from claude_mpm.services.infrastructure.state_manager import StateManager
from claude_mpm.models.state_models import (
    ProcessState,
    ConversationState,
    ConversationContext,
    ProjectState,
    RestartState,
    CompleteState
)


class TestStateManager:
    """Test suite for State Manager service."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    async def state_manager(self, temp_dir):
        """Create State Manager instance for testing."""
        manager = StateManager(state_dir=temp_dir)
        await manager.initialize()
        yield manager
        await manager.shutdown()
    
    @pytest.fixture
    def sample_process_state(self):
        """Create sample process state."""
        return ProcessState(
            pid=12345,
            parent_pid=1000,
            process_name="claude-mpm",
            command=["python", "-m", "claude_mpm"],
            args=["run"],
            working_directory="/test/project",
            environment={"PATH": "/usr/bin", "API_KEY": "secret"},
            memory_mb=512.5,
            cpu_percent=25.3,
            open_files=["/test/file1.txt", "/test/file2.py"],
            start_time=time.time() - 3600,
            capture_time=time.time()
        )
    
    @pytest.fixture
    def sample_conversation_state(self):
        """Create sample conversation state."""
        active_conv = ConversationContext(
            conversation_id="conv_123",
            title="Test Conversation",
            created_at=time.time() - 7200,
            updated_at=time.time() - 1800,
            message_count=50,
            total_tokens=5000,
            max_tokens=100000,
            referenced_files=["/test/main.py"],
            open_tabs=["tab1", "tab2"],
            tags=["test", "demo"],
            is_active=True
        )
        
        return ConversationState(
            active_conversation_id="conv_123",
            active_conversation=active_conv,
            recent_conversations=[],
            total_conversations=10,
            total_storage_mb=150.5,
            preferences={"theme": "dark"},
            open_files=["/test/file1.py", "/test/file2.py"],
            recent_files=["/test/recent.py"],
            pinned_files=["/test/pinned.py"]
        )
    
    @pytest.fixture
    def sample_project_state(self):
        """Create sample project state."""
        return ProjectState(
            project_path="/test/project",
            project_name="test_project",
            git_branch="main",
            git_commit="abc123",
            git_status={
                "staged": ["file1.py"],
                "modified": ["file2.py"],
                "untracked": ["temp.txt"]
            },
            git_remotes={"origin": "https://github.com/test/repo.git"},
            modified_files=["file2.py"],
            open_editors=["editor1.py"],
            breakpoints={"debug.py": [10, 20, 30]},
            project_type="python",
            dependencies={"pytest": "7.0.0"},
            environment_vars={"PROJECT_ENV": "test"},
            last_build_status="success",
            last_test_results={"passed": 10, "failed": 0}
        )
    
    @pytest.fixture
    def sample_restart_state(self):
        """Create sample restart state."""
        return RestartState(
            restart_id="restart_123",
            restart_count=3,
            timestamp=time.time(),
            previous_uptime=7200.0,
            reason="Memory threshold exceeded",
            trigger="memory",
            memory_mb=2048.0,
            memory_limit_mb=2048.0,
            cpu_percent=50.0,
            error_type=None,
            error_message=None,
            error_traceback=None,
            recovery_attempted=True,
            recovery_successful=True,
            data_preserved=["process", "conversation", "project"]
        )
    
    @pytest.fixture
    def sample_complete_state(self, sample_process_state, sample_conversation_state,
                            sample_project_state, sample_restart_state):
        """Create sample complete state."""
        return CompleteState(
            process_state=sample_process_state,
            conversation_state=sample_conversation_state,
            project_state=sample_project_state,
            restart_state=sample_restart_state
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, temp_dir):
        """Test State Manager initialization."""
        manager = StateManager(state_dir=temp_dir)
        assert not manager._initialized
        
        result = await manager.initialize()
        assert result is True
        assert manager._initialized
        assert manager.state_dir.exists()
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_capture_state(self, state_manager, monkeypatch):
        """Test state capture."""
        # Mock subprocess calls for Git
        mock_run = MagicMock()
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "main"
        monkeypatch.setattr("subprocess.run", mock_run)
        
        # Mock platform memory
        mock_memory = MagicMock()
        mock_memory.return_value = MagicMock(rss_mb=512.0)
        monkeypatch.setattr("claude_mpm.services.infrastructure.state_manager.get_process_memory", mock_memory)
        
        # Capture state
        state = await state_manager.capture_state(restart_reason="Test capture")
        
        assert state is not None
        assert isinstance(state, CompleteState)
        assert state.restart_state.reason == "Test capture"
        assert state.process_state.pid == os.getpid()
        assert state_manager.capture_count == 1
    
    @pytest.mark.asyncio
    async def test_persist_and_load_state(self, state_manager, sample_complete_state, temp_dir):
        """Test state persistence and loading."""
        # Persist state
        result = await state_manager.persist_state(sample_complete_state, compress=False)
        assert result is True
        
        # Check file exists
        state_file = temp_dir / "current_state.json"
        assert state_file.exists()
        
        # Load state
        loaded_state = await state_manager.load_state()
        assert loaded_state is not None
        assert loaded_state.state_id == sample_complete_state.state_id
        assert loaded_state.restart_state.reason == sample_complete_state.restart_state.reason
    
    @pytest.mark.asyncio
    async def test_persist_state_compressed(self, state_manager, sample_complete_state, temp_dir):
        """Test compressed state persistence."""
        # Persist compressed state
        result = await state_manager.persist_state(sample_complete_state, compress=True)
        assert result is True
        
        # Check compressed file exists
        compressed_file = temp_dir / "current_state.json.gz"
        assert compressed_file.exists()
        
        # Load compressed state
        loaded_state = await state_manager.load_state()
        assert loaded_state is not None
        assert loaded_state.state_id == sample_complete_state.state_id
    
    @pytest.mark.asyncio
    async def test_restore_state(self, state_manager, sample_complete_state, monkeypatch):
        """Test state restoration."""
        # Mock os.chdir
        mock_chdir = MagicMock()
        monkeypatch.setattr("os.chdir", mock_chdir)
        
        # Restore state
        result = await state_manager.restore_state(sample_complete_state)
        assert result is True
        
        # Check working directory was restored
        mock_chdir.assert_called_once_with(sample_complete_state.process_state.working_directory)
        
        # Check environment variables were set (non-sensitive only)
        assert os.environ.get("PATH") == "/usr/bin"
        assert "API_KEY" not in os.environ or os.environ["API_KEY"] != "secret"
        
        assert state_manager.restore_count == 1
    
    @pytest.mark.asyncio
    async def test_cleanup_old_states(self, state_manager, temp_dir):
        """Test cleanup of old state files."""
        # Create old state files
        old_time = datetime.now() - timedelta(days=10)
        
        for i in range(5):
            state_file = temp_dir / f"state_{i}.json"
            state_file.write_text("{}")
            # Set old modification time
            os.utime(state_file, (old_time.timestamp(), old_time.timestamp()))
        
        # Create recent state files
        for i in range(5, 8):
            state_file = temp_dir / f"state_{i}.json"
            state_file.write_text("{}")
        
        # Run cleanup
        removed = await state_manager.cleanup_old_states()
        assert removed == 5
        
        # Check that old files were removed
        remaining_files = list(temp_dir.glob("state_*.json"))
        assert len(remaining_files) == 3
    
    @pytest.mark.asyncio
    async def test_cleanup_max_files(self, state_manager, temp_dir):
        """Test cleanup enforces max file limit."""
        state_manager.max_state_files = 5
        
        # Create many state files
        for i in range(10):
            state_file = temp_dir / f"state_{i:03d}.json"
            state_file.write_text("{}")
            time.sleep(0.01)  # Ensure different timestamps
        
        # Run cleanup
        removed = await state_manager.cleanup_old_states()
        
        # Check that excess files were removed
        remaining_files = list(temp_dir.glob("state_*.json"))
        assert len(remaining_files) <= state_manager.max_state_files
    
    @pytest.mark.asyncio
    async def test_get_conversation_context(self, state_manager, temp_dir, monkeypatch):
        """Test conversation context extraction."""
        # Create mock Claude config
        claude_dir = temp_dir / ".claude"
        claude_dir.mkdir()
        claude_json = claude_dir / ".claude.json"
        
        claude_data = {
            "activeConversationId": "conv_123",
            "conversations": [
                {
                    "id": "conv_123",
                    "title": "Active Conv",
                    "createdAt": 1000000,
                    "updatedAt": 2000000,
                    "messages": [{"content": "test"}],
                    "totalTokens": 1000,
                    "maxTokens": 100000,
                    "openTabs": ["tab1"],
                    "tags": ["test"]
                }
            ],
            "preferences": {"theme": "dark"},
            "openFiles": ["/test/file.py"],
            "recentFiles": ["/test/recent.py"],
            "pinnedFiles": ["/test/pinned.py"]
        }
        
        claude_json.write_text(json.dumps(claude_data))
        
        # Mock Claude config path
        monkeypatch.setattr(state_manager, "claude_json_path", claude_json)
        
        # Get conversation context
        context = await state_manager.get_conversation_context()
        
        assert context is not None
        assert context.active_conversation_id == "conv_123"
        assert context.active_conversation.title == "Active Conv"
        assert context.preferences["theme"] == "dark"
        assert "/test/file.py" in context.open_files
    
    @pytest.mark.asyncio
    async def test_get_conversation_context_large_file(self, state_manager, temp_dir, monkeypatch):
        """Test conversation context extraction for large files."""
        # Create mock large Claude config
        claude_dir = temp_dir / ".claude"
        claude_dir.mkdir()
        claude_json = claude_dir / ".claude.json"
        
        # Create a file that appears large
        claude_json.write_text("{}")
        
        # Mock file size to appear large
        mock_stat = MagicMock()
        mock_stat.return_value.st_size = 200 * 1024 * 1024  # 200MB
        monkeypatch.setattr(Path, "stat", mock_stat)
        
        # Mock Claude config path
        monkeypatch.setattr(state_manager, "claude_json_path", claude_json)
        
        # Get conversation context (should use minimal extraction)
        context = await state_manager.get_conversation_context()
        
        assert context is not None
        # Should have minimal data due to large file handling
    
    @pytest.mark.asyncio
    async def test_capture_conversation_state(self, state_manager, monkeypatch):
        """Test conversation state capture."""
        # Mock get_conversation_context
        mock_context = ConversationState(
            active_conversation_id="test_conv",
            active_conversation=None,
            recent_conversations=[],
            total_conversations=5,
            total_storage_mb=10.0,
            preferences={},
            open_files=[],
            recent_files=[],
            pinned_files=[]
        )
        
        async def mock_get_context():
            return mock_context
        
        monkeypatch.setattr(state_manager, "get_conversation_context", mock_get_context)
        
        # Capture conversation state
        state = await state_manager._capture_conversation_state()
        
        assert state is not None
        assert state.active_conversation_id == "test_conv"
        assert state.total_conversations == 5
    
    @pytest.mark.asyncio
    async def test_capture_project_state(self, state_manager, monkeypatch):
        """Test project state capture."""
        # Mock subprocess for Git commands
        def mock_run(cmd, *args, **kwargs):
            result = MagicMock()
            if "rev-parse" in cmd and "--abbrev-ref" in cmd:
                result.returncode = 0
                result.stdout = "main\n"
            elif "rev-parse" in cmd and "HEAD" in cmd:
                result.returncode = 0
                result.stdout = "abc123def456\n"
            elif "status" in cmd:
                result.returncode = 0
                result.stdout = "M  modified.py\n?? untracked.txt\n"
            else:
                result.returncode = 1
            return result
        
        monkeypatch.setattr("subprocess.run", mock_run)
        
        # Capture project state
        state = await state_manager._capture_project_state()
        
        assert state is not None
        assert state.git_branch == "main"
        assert state.git_commit == "abc123de"
        assert "modified.py" in state.git_status.get("staged", [])
        assert "untracked.txt" in state.git_status.get("untracked", [])
    
    @pytest.mark.asyncio
    async def test_detect_project_type(self, state_manager, temp_dir):
        """Test project type detection."""
        # Test Python project
        (temp_dir / "pyproject.toml").touch()
        assert state_manager._detect_project_type(str(temp_dir)) == "python"
        
        # Test Node project
        (temp_dir / "pyproject.toml").unlink()
        (temp_dir / "package.json").touch()
        assert state_manager._detect_project_type(str(temp_dir)) == "node"
        
        # Test Go project
        (temp_dir / "package.json").unlink()
        (temp_dir / "go.mod").touch()
        assert state_manager._detect_project_type(str(temp_dir)) == "go"
        
        # Test unknown project
        (temp_dir / "go.mod").unlink()
        assert state_manager._detect_project_type(str(temp_dir)) == "unknown"
    
    @pytest.mark.asyncio
    async def test_state_validation(self, sample_complete_state):
        """Test state validation."""
        # Valid state should have no issues
        issues = sample_complete_state.validate()
        assert len(issues) == 0
        
        # Invalid state with missing fields
        invalid_state = CompleteState(
            process_state=ProcessState(
                pid=0,  # Invalid PID
                parent_pid=0,
                process_name="",
                command=[],
                args=[],
                working_directory="",
                environment={},
                memory_mb=0,
                cpu_percent=0,
                open_files=[],
                start_time=0,
                capture_time=0
            ),
            conversation_state=sample_complete_state.conversation_state,
            project_state=ProjectState(
                project_path="",  # Invalid path
                project_name="",
                git_branch=None,
                git_commit=None,
                git_status={},
                git_remotes={},
                modified_files=[],
                open_editors=[],
                breakpoints={},
                project_type="unknown",
                dependencies={},
                environment_vars={},
                last_build_status=None,
                last_test_results=None
            ),
            restart_state=sample_complete_state.restart_state
        )
        
        issues = invalid_state.validate()
        assert len(issues) > 0
        assert any("PID" in issue for issue in issues)
        assert any("path" in issue for issue in issues)
    
    @pytest.mark.asyncio
    async def test_cooldown_between_captures(self, state_manager, monkeypatch):
        """Test cooldown period between state captures."""
        # Mock subprocess and memory
        monkeypatch.setattr("subprocess.run", MagicMock(return_value=MagicMock(returncode=1)))
        monkeypatch.setattr("claude_mpm.services.infrastructure.state_manager.get_process_memory",
                          MagicMock(return_value=MagicMock(rss_mb=512.0)))
        
        # First capture should succeed
        state1 = await state_manager.capture_state("Test 1")
        assert state1 is not None
        
        # Immediate second capture should be skipped due to cooldown
        state2 = await state_manager.capture_state("Test 2")
        assert state2 == state1  # Should return cached state
        assert state_manager.capture_count == 1  # Count shouldn't increase
        
        # Wait for cooldown
        state_manager.last_capture_time = time.time() - state_manager.capture_cooldown - 1
        
        # Now capture should work
        state3 = await state_manager.capture_state("Test 3")
        assert state3 is not None
        assert state3 != state1
        assert state_manager.capture_count == 2
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, state_manager, temp_dir):
        """Test statistics retrieval."""
        # Create some state files
        for i in range(3):
            state_file = temp_dir / f"state_{i}.json"
            state_file.write_text('{"test": "data"}')
        
        # Get statistics
        stats = state_manager.get_statistics()
        
        assert stats["capture_count"] == 0
        assert stats["restore_count"] == 0
        assert stats["cleanup_count"] == 0
        assert stats["state_files"] == 3
        assert stats["state_directory"] == str(temp_dir)
        assert stats["retention_days"] == 7
        assert stats["max_state_files"] == 50
    
    @pytest.mark.asyncio
    async def test_error_handling(self, state_manager, monkeypatch):
        """Test error handling in various scenarios."""
        # Test capture with subprocess error
        def mock_run_error(*args, **kwargs):
            raise Exception("Subprocess error")
        
        monkeypatch.setattr("subprocess.run", mock_run_error)
        
        # Should handle error gracefully
        state = await state_manager.capture_state("Test with error")
        assert state is not None  # Should still return partial state
        
        # Test load with corrupted file
        state_manager.current_state_file.write_text("invalid json {")
        loaded = await state_manager.load_state()
        assert loaded is None  # Should return None on error
        
        # Test persist with permission error
        def mock_mkstemp(*args, **kwargs):
            raise PermissionError("No permission")
        
        monkeypatch.setattr("tempfile.mkstemp", mock_mkstemp)
        
        sample_state = CompleteState(
            process_state=MagicMock(),
            conversation_state=MagicMock(),
            project_state=MagicMock(),
            restart_state=MagicMock()
        )
        sample_state.to_dict = MagicMock(return_value={})
        
        result = await state_manager.persist_state(sample_state)
        assert result is False  # Should return False on error