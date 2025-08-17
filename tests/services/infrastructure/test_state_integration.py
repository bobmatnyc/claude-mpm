"""Integration tests for State Management System with Memory Guardian."""

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from claude_mpm.config.memory_guardian_config import MemoryGuardianConfig
from claude_mpm.services.infrastructure.context_preservation import (
    ContextPreservationService,
)
from claude_mpm.services.infrastructure.memory_guardian import MemoryGuardian
from claude_mpm.services.infrastructure.state_manager import StateManager
from claude_mpm.storage.state_storage import StateCache, StateStorage


class TestStateIntegration:
    """Integration tests for the complete state management system."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    async def memory_guardian(self, temp_dir):
        """Create Memory Guardian with state management."""
        config = MemoryGuardianConfig(
            enabled=True,
            auto_start=False,
            persist_state=True,
            state_file=str(temp_dir / "memory_guardian_state.json"),
            thresholds={"warning": 1024, "critical": 1536, "emergency": 2048},
        )

        guardian = MemoryGuardian(config)

        # Initialize state manager
        state_manager = StateManager(state_dir=temp_dir / "state")
        await state_manager.initialize()

        # Set state manager in guardian
        guardian.set_state_manager(state_manager)

        await guardian.initialize()

        yield guardian

        await guardian.shutdown()

    @pytest.fixture
    async def context_service(self, temp_dir):
        """Create Context Preservation service."""
        service = ContextPreservationService(claude_dir=temp_dir / ".claude")
        await service.initialize()
        yield service

    @pytest.fixture
    def state_storage(self, temp_dir):
        """Create State Storage instance."""
        return StateStorage(storage_dir=temp_dir / "storage")

    @pytest.mark.asyncio
    async def test_memory_guardian_with_state_manager(
        self, memory_guardian, monkeypatch
    ):
        """Test Memory Guardian integration with State Manager."""
        # Mock subprocess for process management
        mock_popen = MagicMock()
        mock_popen.pid = 12345
        mock_popen.poll.return_value = None  # Process is running
        mock_popen.returncode = None

        monkeypatch.setattr("subprocess.Popen", MagicMock(return_value=mock_popen))

        # Mock memory info
        mock_memory = MagicMock(rss_mb=512.0)
        monkeypatch.setattr(
            "claude_mpm.utils.platform_memory.get_process_memory",
            MagicMock(return_value=mock_memory),
        )

        # Start process
        success = await memory_guardian.start_process()
        assert success is True
        assert memory_guardian.process_pid == 12345

        # Verify state manager is set
        assert memory_guardian.state_manager is not None

        # Trigger restart with state preservation
        await memory_guardian.restart_process("Test restart")

        # Check that state was captured and persisted
        state_manager = memory_guardian.state_manager
        assert state_manager.capture_count > 0

        # Verify state files were created
        state_files = list(state_manager.state_dir.glob("state_*.json*"))
        assert len(state_files) > 0

    @pytest.mark.asyncio
    async def test_state_persistence_and_recovery(self, temp_dir):
        """Test complete state persistence and recovery cycle."""
        # Create state manager
        state_manager = StateManager(state_dir=temp_dir / "state")
        await state_manager.initialize()

        # Capture initial state
        state1 = await state_manager.capture_state("Initial capture")
        assert state1 is not None

        # Persist state
        success = await state_manager.persist_state(state1)
        assert success is True

        # Create new state manager (simulating restart)
        state_manager2 = StateManager(state_dir=temp_dir / "state")
        await state_manager2.initialize()

        # Load persisted state
        loaded_state = await state_manager2.load_state()
        assert loaded_state is not None
        assert loaded_state.state_id == state1.state_id

        # Restore state
        success = await state_manager2.restore_state(loaded_state)
        assert success is True
        assert state_manager2.restore_count == 1

        await state_manager.shutdown()
        await state_manager2.shutdown()

    @pytest.mark.asyncio
    async def test_context_preservation(self, context_service, temp_dir):
        """Test conversation context preservation."""
        # Create mock Claude configuration
        claude_dir = temp_dir / ".claude"
        claude_dir.mkdir()
        claude_json = claude_dir / ".claude.json"

        # Create sample conversation data
        conversation_data = {
            "activeConversationId": "conv_test",
            "conversations": [
                {
                    "id": "conv_test",
                    "title": "Test Conversation",
                    "createdAt": 1000000000,
                    "updatedAt": 2000000000,
                    "messages": [
                        {"content": "Test message 1"},
                        {"content": "Test message 2"},
                    ],
                    "totalTokens": 1500,
                    "maxTokens": 100000,
                }
            ],
            "preferences": {"theme": "dark", "fontSize": 14},
            "openFiles": ["/test/file1.py", "/test/file2.py"],
        }

        import json

        claude_json.write_text(json.dumps(conversation_data))

        # Parse conversation data
        state = await context_service.parse_claude_json(extract_full=True)

        assert state is not None
        assert state.active_conversation_id == "conv_test"
        assert state.active_conversation.title == "Test Conversation"
        assert state.preferences["theme"] == "dark"
        assert len(state.open_files) == 2

    @pytest.mark.asyncio
    async def test_state_storage_atomic_operations(self, state_storage, temp_dir):
        """Test atomic file operations in state storage."""
        # Test data
        test_data = {"test": "data", "nested": {"key": "value", "number": 42}}

        # Test atomic JSON write
        file_path = temp_dir / "test_state.json"
        success = state_storage.write_json(test_data, file_path, atomic=True)
        assert success is True
        assert file_path.exists()

        # Test JSON read
        loaded_data = state_storage.read_json(file_path)
        assert loaded_data == test_data

        # Test compressed write
        compressed_path = temp_dir / "test_state_compressed.json.gz"
        success = state_storage.write_json(test_data, compressed_path, compress=True)
        assert success is True
        assert compressed_path.exists()

        # Test compressed read
        loaded_compressed = state_storage.read_json(compressed_path)
        assert loaded_compressed == test_data

        # Verify statistics
        info = state_storage.get_storage_info()
        assert info["write_count"] == 2
        assert info["read_count"] == 2

    @pytest.mark.asyncio
    async def test_state_cache(self):
        """Test state caching functionality."""
        cache = StateCache(max_size=3, ttl_seconds=2)

        # Test cache set and get
        cache.set("key1", {"data": "value1"})
        cache.set("key2", {"data": "value2"})

        assert cache.get("key1") == {"data": "value1"}
        assert cache.get("key2") == {"data": "value2"}
        assert cache.get("key3") is None  # Miss

        # Check statistics
        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["size"] == 2

        # Test TTL expiration
        await asyncio.sleep(2.1)
        assert cache.get("key1") is None  # Expired

        # Test LRU eviction
        cache.clear()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        # Access 'a' and 'b' to make them more recently used
        cache.get("a")
        cache.get("b")

        # Add new item, should evict 'c' (least recently used)
        cache.set("d", 4)
        assert cache.get("c") is None
        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("d") == 4

    @pytest.mark.asyncio
    async def test_state_cleanup(self, temp_dir):
        """Test cleanup of old state files."""
        state_manager = StateManager(state_dir=temp_dir / "state")
        await state_manager.initialize()

        # Create multiple state captures
        for i in range(5):
            state = await state_manager.capture_state(f"Capture {i}")
            await state_manager.persist_state(state)
            await asyncio.sleep(0.1)

        # Verify files were created
        state_files = list(state_manager.state_dir.glob("state_*.json*"))
        assert len(state_files) >= 5

        # Manually age some files
        import datetime

        old_time = datetime.datetime.now() - datetime.timedelta(days=10)
        for file in state_files[:3]:
            os.utime(file, (old_time.timestamp(), old_time.timestamp()))

        # Run cleanup
        removed = await state_manager.cleanup_old_states()
        assert removed >= 3

        # Verify old files were removed
        remaining_files = list(state_manager.state_dir.glob("state_*.json*"))
        assert len(remaining_files) < len(state_files)

        await state_manager.shutdown()

    @pytest.mark.asyncio
    async def test_complete_restart_scenario(self, temp_dir, monkeypatch):
        """Test complete restart scenario with state preservation."""
        # Phase 1: Initial process with state capture
        guardian1 = MemoryGuardian(
            MemoryGuardianConfig(
                enabled=True,
                auto_start=False,
                persist_state=True,
                state_file=str(temp_dir / "guardian_state.json"),
            )
        )

        state_manager1 = StateManager(state_dir=temp_dir / "state")
        await state_manager1.initialize()
        guardian1.set_state_manager(state_manager1)
        await guardian1.initialize()

        # Mock process
        mock_popen = MagicMock()
        mock_popen.pid = 99999
        mock_popen.poll.return_value = None
        monkeypatch.setattr("subprocess.Popen", MagicMock(return_value=mock_popen))

        # Start and capture state
        await guardian1.start_process()
        state = await state_manager1.capture_state("Pre-restart state")
        await state_manager1.persist_state(state)

        # Shutdown first instance
        await guardian1.shutdown()

        # Phase 2: New process loads and restores state
        guardian2 = MemoryGuardian(
            MemoryGuardianConfig(
                enabled=True,
                auto_start=False,
                persist_state=True,
                state_file=str(temp_dir / "guardian_state.json"),
            )
        )

        state_manager2 = StateManager(state_dir=temp_dir / "state")
        await state_manager2.initialize()
        guardian2.set_state_manager(state_manager2)
        await guardian2.initialize()

        # Load and restore state
        loaded_state = await state_manager2.load_state()
        assert loaded_state is not None
        assert loaded_state.process_state.pid == 99999

        success = await state_manager2.restore_state(loaded_state)
        assert success is True

        # Verify restoration
        assert state_manager2.restore_count == 1
        assert state_manager2.current_state is not None

        await guardian2.shutdown()

    @pytest.mark.asyncio
    async def test_error_recovery(self, temp_dir):
        """Test error recovery in state management."""
        state_manager = StateManager(state_dir=temp_dir / "state")
        await state_manager.initialize()

        # Test with corrupted state file
        corrupted_file = temp_dir / "state" / "current_state.json"
        corrupted_file.write_text("{ invalid json }")

        # Should handle corrupted file gracefully
        loaded = await state_manager.load_state()
        assert loaded is None

        # Test with missing Claude configuration
        context_service = ContextPreservationService(claude_dir=temp_dir / "missing")
        await context_service.initialize()

        state = await context_service.parse_claude_json()
        assert state is not None  # Should return empty state
        assert state.total_conversations == 0

        await state_manager.shutdown()
