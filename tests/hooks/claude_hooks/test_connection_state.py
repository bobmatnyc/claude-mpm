#!/usr/bin/env python3
"""Unit tests for Connection and State Management.

Tests connection management and state tracking functionality.
"""

import json
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestConnectionManagement:
    """Test SocketIO and EventBus connection management."""

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.get_connection_pool")
    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EventBus")
    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EVENTBUS_AVAILABLE", True)
    def test_connection_pool_initialization(self, mock_eventbus, mock_get_pool):
        """Test SocketIO connection pool initialization."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        mock_pool = MagicMock()
        mock_get_pool.return_value = mock_pool
        mock_bus = MagicMock()
        mock_eventbus.get_instance.return_value = mock_bus

        handler = ClaudeHookHandler()

        assert handler.connection_pool == mock_pool
        assert handler.event_bus == mock_bus
        mock_get_pool.assert_called_once()
        mock_eventbus.get_instance.assert_called_once()

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.get_connection_pool")
    def test_connection_pool_initialization_failure(self, mock_get_pool):
        """Test handling of connection pool initialization failure."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        mock_get_pool.side_effect = Exception("Connection failed")

        handler = ClaudeHookHandler()

        assert handler.connection_pool is None

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EventBus")
    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler.EVENTBUS_AVAILABLE", True)
    def test_eventbus_initialization_failure(self, mock_eventbus):
        """Test handling of EventBus initialization failure."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        mock_eventbus.get_instance.side_effect = Exception("EventBus failed")

        handler = ClaudeHookHandler()

        assert handler.event_bus is None

    @patch("src.claude_mpm.hooks.claude_hooks.hook_handler._global_handler", None)
    @patch(
        "src.claude_mpm.hooks.claude_hooks.hook_handler._handler_lock", threading.Lock()
    )
    def test_singleton_pattern(self):
        """Test global handler singleton pattern."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import (
            main,
        )

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                with patch("sys.exit"):
                    main()

        # Check that continue was printed
        output = mock_stdout.getvalue()
        assert '{"action": "continue"}' in output

    def test_cleanup_on_destruction(self):
        """Test cleanup when handler is destroyed."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        mock_pool = MagicMock()
        handler = ClaudeHookHandler()
        handler.connection_pool = mock_pool

        # Trigger __del__
        handler.__del__()

        mock_pool.cleanup.assert_called_once()


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
        old_timestamp = (
            datetime.now(timezone.utc).timestamp() - 400
        )  # More than 5 minutes old
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
        timestamp = datetime.now(timezone.utc).timestamp()
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

        # Expire the cache
        handler._git_branch_cache_time["/test/path"] = (
            datetime.now(timezone.utc).timestamp() - 40
        )

        # Third call should execute git command again
        branch3 = handler._get_git_branch("/test/path")
        assert branch3 == "main"
        assert mock_run.call_count == 2

    def test_cleanup_old_entries(self):
        """Test cleanup of old entries from various stores."""
        from src.claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

        handler = ClaudeHookHandler()

        # Add entries exceeding max limits
        for i in range(250):
            handler.active_delegations[f"session-{i}"] = f"agent-{i}"
            handler.delegation_requests[f"session-{i}"] = {"data": i}

        for i in range(150):
            handler.pending_prompts[f"prompt-{i}"] = {"prompt": f"test-{i}"}

        # Add old git branch cache entries
        old_time = datetime.now(timezone.utc).timestamp() - 400
        handler._git_branch_cache["old-path"] = "old-branch"
        handler._git_branch_cache_time["old-path"] = old_time

        handler._cleanup_old_entries()

        # Check that storage was trimmed to max sizes
        assert len(handler.active_delegations) <= handler.MAX_DELEGATION_TRACKING
        assert len(handler.delegation_requests) <= handler.MAX_DELEGATION_TRACKING
        assert len(handler.pending_prompts) <= handler.MAX_PROMPT_TRACKING

        # Check that old git cache was removed
        assert "old-path" not in handler._git_branch_cache
        assert "old-path" not in handler._git_branch_cache_time


