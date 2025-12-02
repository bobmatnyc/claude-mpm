#!/usr/bin/env python3
"""
Integration Tests for Dashboard Code Analysis Workflow
======================================================

Tests the end-to-end flow of the dashboard-triggered code analysis:
1. SocketIO server setup with handlers
2. Analysis runner initialization
3. Event emission and handling
4. Code analysis subprocess execution
5. Result streaming and completion

WHY: Ensures the complete dashboard analysis workflow functions correctly
from UI interaction through server processing to result display.
"""

import tempfile
import time
from pathlib import Path
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from claude_mpm.core.logging_config import get_logger
from claude_mpm.dashboard.analysis_runner import (AnalysisRequest,
                                                  CodeAnalysisRunner)
from claude_mpm.services.socketio.handlers.code_analysis import \
    CodeAnalysisEventHandler


class MockSocketIOServer:
    """Mock SocketIO server for testing."""

    def __init__(self, port=8765):
        self.port = port
        self.events_emitted = []
        self.connected_clients = set()
        self.core = MagicMock()
        self.core.sio = MagicMock()
        self.sio = MagicMock()  # Add sio attribute for handlers
        self.clients = {}  # Add clients dict for handlers
        self.event_history = []  # Add event_history for handlers
        self.logger = get_logger("MockSocketIOServer")

    def broadcast_event(self, event_type: str, data: Dict):
        """Mock broadcast event - just record the event."""
        event = {"type": event_type, "data": data, "timestamp": time.time()}
        self.events_emitted.append(event)
        self.logger.info(f"Mock broadcast: {event_type} with data: {data}")

    def get_events_by_type(self, event_type: str) -> List[Dict]:
        """Get all events of a specific type."""
        return [e for e in self.events_emitted if e["type"] == event_type]

    def clear_events(self):
        """Clear all recorded events."""
        self.events_emitted.clear()


class TestDashboardCodeAnalysisIntegration:
    """Integration tests for dashboard code analysis workflow."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory with test files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_path = Path(tmp_dir)

            # Create a sample Python file
            (temp_path / "test_module.py").write_text(
                '''
def hello_world():
    """A simple test function."""
    return "Hello, World!"

class TestClass:
    """A simple test class."""

    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hello, {self.name}!"
'''
            )

            # Create a sample JavaScript file
            (temp_path / "test_script.js").write_text(
                """
function greetUser(name) {
    return `Hello, ${name}!`;
}

class Calculator {
    add(a, b) {
        return a + b;
    }

    multiply(a, b) {
        return a * b;
    }
}
"""
            )

            yield str(temp_path)

    @pytest.fixture
    def mock_server(self):
        """Create a mock SocketIO server."""
        return MockSocketIOServer()

    @pytest.fixture
    def analysis_runner(self, mock_server):
        """Create an analysis runner with mock server."""
        runner = CodeAnalysisRunner(mock_server)
        yield runner
        # Cleanup
        runner.stop()

    @pytest.fixture
    def event_handler(self, mock_server):
        """Create a code analysis event handler."""
        handler = CodeAnalysisEventHandler(mock_server)
        handler.initialize()
        yield handler
        # Cleanup
        handler.cleanup()

    def test_analysis_runner_initialization(self, analysis_runner):
        """Test that the analysis runner initializes correctly."""
        assert analysis_runner is not None
        assert not analysis_runner.running
        assert analysis_runner.current_process is None
        assert analysis_runner.current_request is None

        # Test starting the runner
        analysis_runner.start()
        assert analysis_runner.running
        assert analysis_runner.worker_thread is not None

        # Test stopping the runner
        analysis_runner.stop()
        assert not analysis_runner.running

    def test_event_handler_initialization(self, event_handler):
        """Test that the event handler initializes correctly."""
        assert event_handler is not None
        assert event_handler.analysis_runner is not None
        assert event_handler.analysis_runner.running

        # Test that events are registered
        events = event_handler.get_events()
        expected_events = {
            "code:analyze:request",
            "code:analyze:cancel",
            "code:analyze:status",
        }
        assert set(events.keys()) == expected_events

    def test_analysis_request_validation(self, analysis_runner, temp_project_dir):
        """Test analysis request validation."""
        analysis_runner.start()

        # Valid request should succeed
        success = analysis_runner.request_analysis(
            request_id="test-001", path=temp_project_dir, languages=["python"]
        )
        assert success

        # Invalid path should fail
        success = analysis_runner.request_analysis(
            request_id="test-002", path="/nonexistent/path"
        )
        assert not success

    def test_analysis_runner_event_emission(
        self, analysis_runner, mock_server, temp_project_dir
    ):
        """Test that the analysis runner emits correct events."""
        analysis_runner.start()

        # Clear any initial events
        mock_server.clear_events()

        # Request analysis
        request_id = "test-event-emission"
        success = analysis_runner.request_analysis(
            request_id=request_id, path=temp_project_dir, languages=["python"]
        )
        assert success

        # Should immediately emit a queued event
        queued_events = mock_server.get_events_by_type("code:analysis:queued")
        assert len(queued_events) >= 1

        # Give the worker thread time to process
        time.sleep(2)

        # Should emit start event
        start_events = mock_server.get_events_by_type("code:analysis:start")
        assert len(start_events) >= 1
        assert start_events[0]["data"]["request_id"] == request_id

    def test_analysis_cancellation(
        self, analysis_runner, mock_server, temp_project_dir
    ):
        """Test analysis cancellation."""
        analysis_runner.start()
        mock_server.clear_events()

        # Start analysis
        request_id = "test-cancellation"
        analysis_runner.request_analysis(request_id=request_id, path=temp_project_dir)

        # Wait a moment for analysis to start
        time.sleep(0.5)

        # Cancel analysis
        analysis_runner.cancel_current()

        # Give time for cancellation to process
        time.sleep(1)

        # Should emit cancellation event
        cancelled_events = mock_server.get_events_by_type("code:analysis:cancelled")
        assert len(cancelled_events) >= 1

    def test_status_retrieval(self, analysis_runner):
        """Test getting analysis runner status."""
        status = analysis_runner.get_status()

        assert "running" in status
        assert "current_request" in status
        assert "queue_size" in status
        assert "stats" in status

        # Test stats structure
        stats = status["stats"]
        expected_stats = {
            "analyses_started",
            "analyses_completed",
            "analyses_cancelled",
            "analyses_failed",
            "total_files",
            "total_nodes",
        }
        assert set(stats.keys()) == expected_stats

    @pytest.mark.asyncio
    async def test_event_handler_request_processing(
        self, event_handler, temp_project_dir
    ):
        """Test event handler processes analysis requests correctly."""
        mock_emit = AsyncMock()
        event_handler.server.sio = MagicMock()
        event_handler.server.sio.emit = mock_emit

        # Valid request
        request_data = {
            "request_id": "test-handler-001",
            "path": temp_project_dir,
            "languages": ["python"],
        }

        await event_handler.handle_analyze_request("test-sid", request_data)

        # Should emit acceptance event
        mock_emit.assert_called()
        call_args = mock_emit.call_args
        assert call_args[0][0] == "code:analysis:accepted"

    @pytest.mark.asyncio
    async def test_event_handler_invalid_request(self, event_handler):
        """Test event handler handles invalid requests correctly."""
        mock_emit = AsyncMock()
        event_handler.server.sio = MagicMock()
        event_handler.server.sio.emit = mock_emit

        # Request without path
        request_data = {
            "request_id": "test-invalid-001"
            # Missing path
        }

        await event_handler.handle_analyze_request("test-sid", request_data)

        # Should emit error event
        mock_emit.assert_called()
        call_args = mock_emit.call_args
        assert call_args[0][0] == "code:analysis:error"
        assert "Path is required" in call_args[0][1]["message"]

    @pytest.mark.asyncio
    async def test_event_handler_cancellation(self, event_handler):
        """Test event handler processes cancellation requests."""
        mock_emit = AsyncMock()
        event_handler.server.sio = MagicMock()
        event_handler.server.sio.emit = mock_emit

        # Cancel request
        cancel_data = {"request_id": "test-cancel-001"}

        await event_handler.handle_cancel_request("test-sid", cancel_data)

        # Should emit cancelled event
        mock_emit.assert_called()
        call_args = mock_emit.call_args
        assert call_args[0][0] == "code:analysis:cancelled"

    @pytest.mark.asyncio
    async def test_event_handler_status_request(self, event_handler):
        """Test event handler provides status information."""
        mock_emit = AsyncMock()
        event_handler.server.sio = MagicMock()
        event_handler.server.sio.emit = mock_emit

        await event_handler.handle_status_request("test-sid", {})

        # Should emit status
        mock_emit.assert_called()
        call_args = mock_emit.call_args
        assert call_args[0][0] == "code:analysis:status"

        # Check status structure
        status = call_args[0][1]
        assert "running" in status
        assert "stats" in status

    def test_analysis_request_dataclass(self):
        """Test AnalysisRequest dataclass functionality."""
        request = AnalysisRequest(request_id="test-dataclass", path="/test/path")

        assert request.request_id == "test-dataclass"
        assert request.path == "/test/path"
        assert request.languages is None
        assert request.timestamp is not None

    def test_command_building(self, analysis_runner):
        """Test that subprocess commands are built correctly."""
        request = AnalysisRequest(
            request_id="test-cmd",
            path="/test/path",
            languages=["python", "javascript"],
            max_depth=3,
            ignore_patterns=["*.test.js", "test_*"],
        )

        cmd = analysis_runner._build_command(request)

        # Check basic structure
        assert len(cmd) >= 6  # python, -m, module, --path, path, --emit-events
        assert cmd[1] == "-m"
        assert cmd[2] == "claude_mpm.tools"
        assert "--path" in cmd
        assert "/test/path" in cmd
        assert "--emit-events" in cmd

        # Check optional parameters
        assert "--languages" in cmd
        assert "python,javascript" in cmd
        assert "--max-depth" in cmd
        assert "3" in cmd
        assert "--ignore" in cmd

    def test_subprocess_environment(self, analysis_runner, mock_server):
        """Test subprocess environment variables."""
        env = analysis_runner._get_subprocess_env()

        assert "SOCKETIO_URL" in env
        assert f"localhost:{mock_server.port}" in env["SOCKETIO_URL"]
        assert "PYTHONPATH" in env


class TestCodeAnalysisWorkflowIntegration:
    """Higher-level integration tests for the complete workflow."""

    @pytest.fixture
    def full_setup(self, temp_project_dir):
        """Set up a complete test environment."""
        mock_server = MockSocketIOServer()
        analysis_runner = CodeAnalysisRunner(mock_server)
        event_handler = CodeAnalysisEventHandler(mock_server)

        # Initialize components
        analysis_runner.start()
        event_handler.initialize()

        yield {
            "server": mock_server,
            "runner": analysis_runner,
            "handler": event_handler,
            "project_dir": temp_project_dir,
        }

        # Cleanup
        event_handler.cleanup()
        analysis_runner.stop()

    @pytest.mark.asyncio
    async def test_complete_analysis_workflow(self, full_setup):
        """Test the complete analysis workflow from request to completion."""
        server = full_setup["server"]
        handler = full_setup["handler"]
        project_dir = full_setup["project_dir"]

        # Mock the Socket.IO emit method
        mock_emit = AsyncMock()
        server.sio = MagicMock()
        server.sio.emit = mock_emit

        server.clear_events()

        # Simulate client request
        request_data = {
            "request_id": "workflow-test",
            "path": project_dir,
            "languages": ["python"],
        }

        # Process the request
        await handler.handle_analyze_request("client-001", request_data)

        # Give time for processing
        time.sleep(2)

        # Verify events were emitted
        assert len(server.events_emitted) > 0

        # Should have queued and start events
        event_types = [e["type"] for e in server.events_emitted]
        assert "code:analysis:queued" in event_types
        assert "code:analysis:start" in event_types

        # Verify the acceptance was sent to client
        mock_emit.assert_called()

    def test_multiple_concurrent_requests(self, full_setup):
        """Test handling multiple analysis requests."""
        runner = full_setup["runner"]
        server = full_setup["server"]
        project_dir = full_setup["project_dir"]

        server.clear_events()

        # Submit multiple requests
        request_ids = ["multi-001", "multi-002", "multi-003"]
        for request_id in request_ids:
            success = runner.request_analysis(request_id=request_id, path=project_dir)
            assert success

        # Give time for processing
        time.sleep(3)

        # Should have events for all requests
        queued_events = server.get_events_by_type("code:analysis:queued")
        assert len(queued_events) == 3

        # Should process them sequentially
        start_events = server.get_events_by_type("code:analysis:start")
        assert len(start_events) >= 1  # At least one should start

    def test_error_handling_workflow(self, full_setup):
        """Test error handling in the analysis workflow."""
        runner = full_setup["runner"]
        server = full_setup["server"]

        server.clear_events()

        # Request analysis of non-existent path
        success = runner.request_analysis(
            request_id="error-test", path="/definitely/does/not/exist"
        )
        assert not success

        # Should emit error event
        error_events = server.get_events_by_type("code:analysis:error")
        assert len(error_events) >= 1
        assert "does not exist" in error_events[0]["data"]["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
