"""Test single-path event emission architecture.

This test ensures the connection manager follows the single-path emission
principle and does not create duplicate events.

These tests serve as architecture compliance checks to prevent regression
to duplicate emission patterns.
"""

import re
from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

from claude_mpm.hooks.claude_hooks.services.connection_manager import (
    ConnectionManagerService,
)


class TestSinglePathEmission:
    """Test the single-path event emission architecture."""

    def setup_method(self):
        """Set up test fixtures."""
        self.connection_manager = ConnectionManagerService()

    @patch(
        "claude_mpm.hooks.claude_hooks.services.connection_manager.get_connection_pool"
    )
    def test_single_emission_path_success(self, mock_get_pool):
        """Test that successful direct emission does not trigger fallback."""
        # Mock successful connection pool
        mock_pool = Mock()
        mock_get_pool.return_value = mock_pool

        # Reinitialize to pick up mocked pool
        self.connection_manager._initialize_socketio_pool()

        # Emit event
        self.connection_manager.emit_event("test", "test_event", {"key": "value"})

        # Verify direct emission was called
        mock_pool.emit.assert_called_once()

        # Verify event data structure
        call_args = mock_pool.emit.call_args
        assert call_args[0][0] == "claude_event"  # Event name
        assert "event" in call_args[0][1]  # Event data contains 'event' key
        assert "type" in call_args[0][1]  # Event data contains 'type' key

    @patch("requests.post")
    @patch(
        "claude_mpm.hooks.claude_hooks.services.connection_manager.get_connection_pool"
    )
    def test_fallback_on_direct_failure(self, mock_get_pool, mock_requests_post):
        """Test that HTTP fallback is used when direct emission fails."""
        # Mock failing connection pool
        mock_pool = Mock()
        mock_pool.emit.side_effect = Exception("Connection failed")
        mock_get_pool.return_value = mock_pool

        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests_post.return_value = mock_response

        # Reinitialize to pick up mocked pool
        self.connection_manager._initialize_socketio_pool()

        # Emit event
        self.connection_manager.emit_event("test", "test_event", {"key": "value"})

        # Verify direct emission was attempted
        mock_pool.emit.assert_called_once()

        # Verify HTTP fallback was called
        mock_requests_post.assert_called_once()

        # Verify HTTP fallback endpoint
        call_args = mock_requests_post.call_args
        assert call_args[0][0] == "http://localhost:8765/api/events"
        assert call_args[1]["timeout"] == 2.0

    @patch(
        "claude_mpm.hooks.claude_hooks.services.connection_manager.get_connection_pool"
    )
    def test_no_eventbus_emission(self, mock_get_pool):
        """Test that EventBus emission is not used (prevents duplicates)."""
        # Mock connection pool
        mock_pool = Mock()
        mock_get_pool.return_value = mock_pool

        # Reinitialize to pick up mocked pool
        self.connection_manager._initialize_socketio_pool()

        # Verify no EventBus is initialized
        assert (
            not hasattr(self.connection_manager, "event_bus")
            or self.connection_manager.event_bus is None
        )

        # Emit event
        self.connection_manager.emit_event("test", "test_event", {"key": "value"})

        # Verify only one emission method was called
        mock_pool.emit.assert_called_once()

    def test_event_normalization(self):
        """Test that events are properly normalized."""
        # Create test event data
        test_data = {"session_id": "test-123", "tool_name": "TestTool"}

        # Mock the normalizer to capture the raw event
        captured_events = []
        original_normalize = self.connection_manager.event_normalizer.normalize

        def capture_normalize(raw_event, source="hook"):
            captured_events.append(raw_event)
            return original_normalize(raw_event, source)

        self.connection_manager.event_normalizer.normalize = capture_normalize

        # Emit event (will fail due to no connection, but normalization will happen)
        self.connection_manager.emit_event("test", "test_event", test_data)

        # Verify event was normalized
        assert len(captured_events) == 1
        raw_event = captured_events[0]

        # Verify event structure
        assert raw_event["type"] == "hook"
        assert raw_event["subtype"] == "test_event"
        assert raw_event["data"] == test_data
        assert raw_event["source"] == "claude_hooks"
        assert "timestamp" in raw_event

    @patch("requests.post")
    @patch(
        "claude_mpm.hooks.claude_hooks.services.connection_manager.get_connection_pool"
    )
    def test_no_duplicate_emissions(self, mock_get_pool, mock_requests_post):
        """Test that events are emitted exactly once (no duplicates)."""
        # Mock connection pool that fails
        mock_pool = Mock()
        mock_pool.emit.side_effect = Exception("Connection failed")
        mock_get_pool.return_value = mock_pool

        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests_post.return_value = mock_response

        # Reinitialize to pick up mocked pool
        self.connection_manager._initialize_socketio_pool()

        # Emit event
        self.connection_manager.emit_event("test", "test_event", {"key": "value"})

        # Verify exactly one attempt at each emission method
        assert mock_pool.emit.call_count == 1  # Direct emission attempted once
        assert mock_requests_post.call_count == 1  # HTTP fallback called once

        # Verify no other emission methods exist
        assert (
            not hasattr(self.connection_manager, "event_bus")
            or self.connection_manager.event_bus is None
        )

    def test_architecture_compliance(self):
        """Test that the connection manager follows architecture guidelines."""
        # Verify no EventBus references
        assert (
            not hasattr(self.connection_manager, "event_bus")
            or self.connection_manager.event_bus is None
        )

        # Verify required methods exist
        assert hasattr(self.connection_manager, "emit_event")
        assert hasattr(self.connection_manager, "_try_http_fallback")
        assert hasattr(self.connection_manager, "connection_pool")

        # Verify event normalizer exists
        assert hasattr(self.connection_manager, "event_normalizer")
        assert self.connection_manager.event_normalizer is not None


class TestArchitectureCompliance:
    """Test architecture compliance to prevent regression to duplicate emission patterns."""

    def get_project_root(self) -> Path:
        """Get the project root directory."""
        # Start from this test file and go up to find project root
        current = Path(__file__).resolve()
        while current.parent != current:
            if (current / "src" / "claude_mpm").exists():
                return current
            current = current.parent
        raise RuntimeError("Could not find project root")

    def test_no_eventbus_in_active_hook_files(self):
        """Test that active hook handler files contain no EventBus references."""
        project_root = self.get_project_root()

        # Only check the ACTIVE hook handler files (not legacy/backup files)
        active_files = [
            "src/claude_mpm/hooks/claude_hooks/hook_handler.py",
            "src/claude_mpm/hooks/claude_hooks/services/connection_manager.py",
            "src/claude_mpm/hooks/claude_hooks/services/connection_manager_http.py",
        ]

        violations = []

        for file_path in active_files:
            full_path = project_root / file_path
            if not full_path.exists():
                pytest.skip(f"File not found: {file_path}")
                continue

            with open(full_path, encoding="utf-8") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                # Skip comments and documentation references
                if (
                    line.strip().startswith("#")
                    or '"""' in line
                    or "'''" in line
                    or "docs/developer/EVENT_EMISSION_ARCHITECTURE.md" in line
                    or "DO NOT add additional emission paths (EventBus" in line
                    or "EventBus removed" in line
                ):
                    continue

                # Check for ACTUAL EventBus usage (not documentation)
                if (
                    re.search(r"\bevent_bus\s*=", line, re.IGNORECASE)
                    or re.search(r"EventBus\(", line)
                    or re.search(r"EVENTBUS_AVAILABLE", line)
                    or re.search(r"\.event_bus\.", line)
                    or re.search(r"from.*EventBus", line)
                ):
                    violations.append(f"{file_path}:{line_num} - {line.strip()}")

        assert not violations, (
            "Found EventBus references in active files:\n" + "\n".join(violations)
        )

    def test_connection_manager_single_emission_path(self):
        """Test that connection manager implements single emission path."""
        project_root = self.get_project_root()
        connection_manager_path = (
            project_root
            / "src/claude_mpm/hooks/claude_hooks/services/connection_manager.py"
        )

        if not connection_manager_path.exists():
            pytest.skip("Connection manager file not found")

        with open(connection_manager_path, encoding="utf-8") as f:
            content = f.read()

        # Verify required methods exist
        assert "def emit_event(" in content, "emit_event method not found"
        assert "def _try_http_fallback(" in content, (
            "_try_http_fallback method not found"
        )

        # Verify single-path pattern in emit_event method
        lines = content.split("\n")
        in_emit_method = False
        found_return_after_success = False

        for line in lines:
            if "def emit_event(" in line:
                in_emit_method = True
            elif in_emit_method and (
                line.strip().startswith("def ") or line.strip().startswith("class ")
            ):
                break
            elif in_emit_method and "return  # Success" in line:
                found_return_after_success = True

        assert found_return_after_success, (
            "Single-path pattern not found: missing 'return # Success' after primary emission"
        )

    def test_required_architecture_files_exist(self):
        """Test that required architecture documentation files exist."""
        project_root = self.get_project_root()

        required_files = [
            "docs/developer/EVENT_EMISSION_ARCHITECTURE.md",
            "src/claude_mpm/hooks/claude_hooks/services/connection_manager.py",
        ]

        for file_path in required_files:
            full_path = project_root / file_path
            assert full_path.exists(), (
                f"Required architecture file missing: {file_path}"
            )

    def test_architecture_documentation_references(self):
        """Test that connection manager references architecture documentation."""
        project_root = self.get_project_root()
        connection_manager_path = (
            project_root
            / "src/claude_mpm/hooks/claude_hooks/services/connection_manager.py"
        )

        if not connection_manager_path.exists():
            pytest.skip("Connection manager file not found")

        with open(connection_manager_path, encoding="utf-8") as f:
            content = f.read()

        # Verify documentation references exist
        assert "EVENT_EMISSION_ARCHITECTURE.md" in content, (
            "Missing reference to architecture documentation"
        )
        assert "SINGLE-PATH EVENT EMISSION ARCHITECTURE" in content, (
            "Missing architecture pattern description"
        )

    def test_no_multiple_parallel_emissions(self):
        """Test that emit_event method doesn't have multiple parallel emission calls."""
        project_root = self.get_project_root()
        connection_manager_path = (
            project_root
            / "src/claude_mpm/hooks/claude_hooks/services/connection_manager.py"
        )

        if not connection_manager_path.exists():
            pytest.skip("Connection manager file not found")

        with open(connection_manager_path, encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        in_emit_method = False
        emission_calls = []

        for line_num, line in enumerate(lines, 1):
            if "def emit_event(" in line:
                in_emit_method = True
                emission_calls = []
            elif in_emit_method and (
                line.strip().startswith("def ") or line.strip().startswith("class ")
            ):
                in_emit_method = False

                # Should have at most 2 emission calls: primary + fallback
                assert len(emission_calls) <= 2, (
                    f"Too many emission calls in emit_event: {emission_calls}"
                )

            elif in_emit_method and re.search(r"\.(emit|publish|post)\s*\(", line):
                emission_calls.append((line_num, line.strip()))


if __name__ == "__main__":
    pytest.main([__file__])
