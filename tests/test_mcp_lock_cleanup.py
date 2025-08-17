#!/usr/bin/env python3
"""
Tests for MCP Gateway Lock Management
======================================

Tests the improved lock handling and automatic cleanup of stale locks.

WHY: Ensure that the MCP gateway can recover from stale locks and properly
manage concurrent access attempts.
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.mcp_gateway.manager import MCPGatewayManager


class TestMCPLockManagement:
    """Test suite for MCP lock management."""

    @pytest.fixture
    def temp_state_dir(self, tmp_path):
        """Create a temporary state directory for testing."""
        state_dir = tmp_path / ".claude-mpm" / "mcp"
        state_dir.mkdir(parents=True)
        return state_dir

    @pytest.fixture
    def manager(self, temp_state_dir, monkeypatch):
        """Create a test manager with temporary directories."""
        # Patch the home directory to use temp path
        monkeypatch.setattr(Path, "home", lambda: temp_state_dir.parent.parent)

        # Create manager
        manager = MCPGatewayManager()
        manager._initialized = False  # Reset for clean test
        manager.__init__()

        return manager

    def test_stale_lock_detection(self, manager):
        """Test that stale locks are properly detected."""
        # Create a lock file with a non-existent PID
        dead_pid = 99999
        manager.lock_file.write_text(str(dead_pid))

        # Should detect and clean stale lock
        assert manager._check_and_clean_stale_lock() == True
        assert not manager.lock_file.exists()

    def test_valid_lock_preserved(self, manager):
        """Test that valid locks are not removed."""
        # Create a lock file with current process PID
        current_pid = os.getpid()
        manager.lock_file.write_text(str(current_pid))

        # Should not clean valid lock
        assert manager._check_and_clean_stale_lock() == False
        assert manager.lock_file.exists()
        assert manager.lock_file.read_text() == str(current_pid)

    def test_empty_lock_cleanup(self, manager):
        """Test that empty lock files are cleaned up."""
        # Create an empty lock file
        manager.lock_file.touch()

        # Should clean empty lock
        assert manager._check_and_clean_stale_lock() == True
        assert not manager.lock_file.exists()

    def test_invalid_pid_cleanup(self, manager):
        """Test that lock files with invalid PIDs are cleaned up."""
        # Create a lock file with invalid PID
        manager.lock_file.write_text("not_a_pid")

        # Should clean invalid lock
        assert manager._check_and_clean_stale_lock() == True
        assert not manager.lock_file.exists()

    def test_instance_file_cleanup_with_lock(self, manager):
        """Test that instance files are cleaned when lock is stale."""
        # Create matching lock and instance files with dead PID
        dead_pid = 99999
        manager.lock_file.write_text(str(dead_pid))

        instance_data = {"pid": dead_pid, "gateway_name": "test", "version": "1.0.0"}
        manager.instance_file.write_text(json.dumps(instance_data))

        # Should clean both files
        assert manager._check_and_clean_stale_lock() == True
        assert not manager.lock_file.exists()
        assert not manager.instance_file.exists()

    def test_acquire_lock_with_stale(self, manager):
        """Test acquiring lock when stale lock exists."""
        # Create a stale lock
        dead_pid = 99999
        manager.lock_file.write_text(str(dead_pid))

        # Should acquire lock after cleaning stale
        assert manager.acquire_lock() == True
        assert manager.lock_file.exists()

        # Lock should contain our PID
        lock_pid = int(manager.lock_file.read_text())
        assert lock_pid == os.getpid()

    def test_concurrent_lock_attempt(self, manager):
        """Test that concurrent lock attempts are properly handled."""
        # First manager acquires lock
        assert manager.acquire_lock() == True

        # Second manager should fail to acquire
        manager2 = MCPGatewayManager()
        manager2.state_dir = manager.state_dir
        manager2.lock_file = manager.lock_file
        manager2.instance_file = manager.instance_file

        assert manager2.acquire_lock() == False

        # Release first lock
        manager.release_lock()

        # Now second manager should succeed
        assert manager2.acquire_lock() == True

    def test_get_running_instance_info(self, manager):
        """Test getting info about running instances."""
        # No instance file
        assert manager.get_running_instance_info() is None

        # Create instance file with current PID
        instance_data = {"pid": os.getpid(), "gateway_name": "test", "version": "1.0.0"}
        manager.instance_file.write_text(json.dumps(instance_data))

        # Should return instance info
        info = manager.get_running_instance_info()
        assert info is not None
        assert info["pid"] == os.getpid()
        assert info["gateway_name"] == "test"

        # Create instance file with dead PID
        instance_data["pid"] = 99999
        manager.instance_file.write_text(json.dumps(instance_data))

        # Should return None and clean up file
        info = manager.get_running_instance_info()
        assert info is None
        assert not manager.instance_file.exists()

    @pytest.mark.asyncio
    async def test_start_gateway_with_stale_lock(self, manager):
        """Test starting gateway when stale lock exists."""
        # Create a stale lock
        dead_pid = 99999
        manager.lock_file.write_text(str(dead_pid))

        # Mock the gateway components
        with patch.object(manager, "_load_default_tools", return_value=None):
            with patch(
                "claude_mpm.services.mcp_gateway.manager.MCPConfiguration"
            ) as mock_config:
                with patch(
                    "claude_mpm.services.mcp_gateway.manager.ToolRegistry"
                ) as mock_registry:
                    with patch(
                        "claude_mpm.services.mcp_gateway.manager.MCPGateway"
                    ) as mock_gateway:
                        # Setup mocks
                        async def mock_async_func():
                            return None

                        mock_config_instance = MagicMock()
                        mock_config_instance.initialize = mock_async_func
                        mock_config.return_value = mock_config_instance

                        mock_registry_instance = MagicMock()
                        mock_registry_instance.initialize = mock_async_func
                        mock_registry_instance.list_tools.return_value = []
                        mock_registry.return_value = mock_registry_instance

                        mock_gateway_instance = MagicMock()
                        mock_gateway_instance.initialize = mock_async_func
                        mock_gateway_instance.gateway_name = "test"
                        mock_gateway_instance.version = "1.0.0"
                        mock_gateway.return_value = mock_gateway_instance

                        # Start should succeed after cleaning stale lock
                        result = await manager.start_gateway("test", "1.0.0")
                        assert result == True

                        # Lock should be acquired with our PID
                        assert manager.lock_file.exists()
                        lock_pid = int(manager.lock_file.read_text())
                        assert lock_pid == os.getpid()

    def test_cleanup_on_signal(self, manager):
        """Test cleanup on termination signal."""
        # Acquire lock and create instance file
        manager.acquire_lock()
        manager.save_instance_info()

        assert manager.lock_file.exists()
        assert manager.instance_file.exists()

        # Simulate cleanup
        manager.cleanup()

        # Files should be removed
        assert not manager.lock_file.exists()
        assert not manager.instance_file.exists()


class TestMCPLockCleaner:
    """Test the standalone lock cleaner utility."""

    def test_cleaner_script_exists(self):
        """Test that the cleanup script exists."""
        script_path = Path(__file__).parent.parent / "scripts" / "cleanup_mcp_locks.py"
        assert script_path.exists()
        assert script_path.is_file()

    def test_cleaner_import(self):
        """Test that the cleaner can be imported."""
        # Add scripts to path
        scripts_path = Path(__file__).parent.parent / "scripts"
        sys.path.insert(0, str(scripts_path))

        # Import should work
        from cleanup_mcp_locks import MCPLockCleaner

        # Should be able to create instance
        cleaner = MCPLockCleaner()
        assert cleaner is not None

    def test_process_detection(self):
        """Test process existence detection."""
        from scripts.cleanup_mcp_locks import MCPLockCleaner

        cleaner = MCPLockCleaner()

        # Current process should exist
        exists, message = cleaner.check_process_exists(os.getpid())
        assert exists == True

        # Non-existent process
        exists, message = cleaner.check_process_exists(99999)
        assert exists == False
        assert "does not exist" in message.lower()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
