#!/usr/bin/env python3
"""Comprehensive unit tests for hook_handler.py.

These tests ensure complete coverage before refactoring with rope.
"""

import json
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import UTC, datetime, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestConnectionManagement:
    """Test SocketIO and EventBus connection management."""

    @pytest.mark.skip(
        reason="Connection pool and EVENTBUS_AVAILABLE removed - hook handler uses HTTP connection manager"
    )
    def test_connection_pool_initialization(self):
        """Test SocketIO connection pool initialization."""

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.get_connection_pool")
    def test_connection_pool_initialization_failure(self, mock_get_pool):
        """Test handling of connection pool initialization failure."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        mock_get_pool.side_effect = Exception("Connection failed")

        handler = ClaudeHookHandler()

        assert handler.connection_pool is None

    @pytest.mark.skip(
        reason="EventBus and EVENTBUS_AVAILABLE removed - hook handler uses HTTP connection manager"
    )
    def test_eventbus_initialization_failure(self):
        """Test handling of EventBus initialization failure."""

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler._global_handler", None)
    @patch(
        "src.claude_mpm.hooks.claude_hooks.hook_handler._handler_lock", threading.Lock()
    )
    def test_singleton_pattern(self):
        """Test global handler singleton pattern."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import main

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with patch("sys.exit"):
                    main()

        # Check that continue was printed
        output = mock_stdout.getvalue()
        assert '{"continue": true}' in output

    def test_cleanup_on_destruction(self):
        """Test cleanup when handler is destroyed."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()
        mock_manager = MagicMock()
        handler.connection_manager = mock_manager

        # Trigger __del__
        handler.__del__()

        mock_manager.cleanup.assert_called_once()


class TestStateManagement:
    """Test state tracking and management."""

    def test_track_delegation(self):
        """Test tracking of agent delegations."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        session_id = "test-session-123"
        agent_type = "research"
        request_data = {"prompt": "Research something"}

        handler._track_delegation(session_id, agent_type, request_data)

        assert handler.active_delegations[session_id] == agent_type
        assert session_id in handler.delegation_requests
        assert handler.delegation_requests[session_id]["agent_type"] == agent_type
        assert handler.delegation_requests[session_id]["request"] == request_data

    def test_track_delegation_cleanup_old(self):
        """Test cleanup of old delegations."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        # Add an old delegation
        old_session = "old-session"
        old_timestamp = datetime.now(UTC).timestamp() - 400  # More than 5 minutes old
        handler.active_delegations[old_session] = "engineer"
        handler.delegation_history.append(
            (f"{old_session}:{old_timestamp}", "engineer")
        )

        # Add a new delegation
        new_session = "new-session"
        handler._track_delegation(new_session, "research")

        # Old delegation should be cleaned up
        assert old_session not in handler.active_delegations
        assert new_session in handler.active_delegations

    def test_get_delegation_agent_type_exact_match(self):
        """Test getting agent type with exact session match."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        session_id = "test-session-123"
        handler.active_delegations[session_id] = "qa"

        result = handler._get_delegation_agent_type(session_id)
        assert result == "qa"

    def test_get_delegation_agent_type_from_history(self):
        """Test getting agent type from delegation history."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        session_id = "test-session-456"
        timestamp = datetime.now(UTC).timestamp()
        handler.delegation_history.append((f"{session_id}:{timestamp}", "engineer"))

        result = handler._get_delegation_agent_type(session_id)
        assert result == "engineer"

    def test_get_delegation_agent_type_unknown(self):
        """Test getting agent type when session not found."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        result = handler._get_delegation_agent_type("unknown-session")
        assert result == "unknown"

    @patch("subprocess.run")
    @patch("os.chdir")
    @patch("os.getcwd")
    def test_git_branch_caching(self, mock_getcwd, mock_chdir, mock_run):
        """Test git branch caching with TTL."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        # Mock current directory
        mock_getcwd.return_value = "/original/path"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "main\n"
        mock_run.return_value = mock_result

        # First call should execute git command
        branch1 = handler._get_git_branch("/test/path")
        assert branch1 == "main"
        assert mock_run.call_count == 1

        # Second call within TTL should use cache
        branch2 = handler._get_git_branch("/test/path")
        assert branch2 == "main"
        assert mock_run.call_count == 1  # Still 1, not called again

        # Expire the cache - it lives in state_manager now
        handler.state_manager._git_branch_cache_time["/test/path"] = (
            datetime.now(UTC).timestamp() - 400
        )

        # Third call should execute git command again
        branch3 = handler._get_git_branch("/test/path")
        assert branch3 == "main"
        assert mock_run.call_count == 2

    @pytest.mark.skip(
        reason="_cleanup_old_entries removed - cleanup now handled by state_manager"
    )
    def test_cleanup_old_entries(self):
        """Test cleanup of old entries from various stores."""
