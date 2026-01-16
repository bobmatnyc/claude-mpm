"""Phase 3 integration tests for Commander chat interface.

Tests the complete chat workflow including:
- Instance management
- Chat interface interaction
- Framework selection
- Output summarization
- Session persistence
- Command parsing
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from claude_mpm.commander.chat.repl import CommanderREPL
from claude_mpm.commander.frameworks.base import InstanceInfo
from claude_mpm.commander.instance_manager import InstanceManager
from claude_mpm.commander.session.manager import SessionManager


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    (project_dir / ".git").mkdir()
    return project_dir


@pytest.fixture
def mock_instance_manager():
    """Create a mock InstanceManager for testing."""
    manager = Mock(spec=InstanceManager)
    manager.list_instances = Mock(return_value=[])
    manager.get_instance = Mock(return_value=None)
    manager.start_instance = AsyncMock()
    manager.stop_instance = AsyncMock()
    manager.send_to_instance = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def session_manager():
    """Create a real SessionManager instance."""
    return SessionManager()


@pytest.fixture
def repl(mock_instance_manager, session_manager):
    """Create a CommanderREPL instance with mocked dependencies."""
    return CommanderREPL(
        instance_manager=mock_instance_manager,
        session_manager=session_manager,
    )


@pytest.mark.integration
class TestChatIntegration:
    """End-to-end tests for chat interface."""

    @pytest.mark.asyncio
    async def test_full_chat_workflow(
        self, repl, mock_instance_manager, session_manager, temp_project_dir
    ):
        """Test complete workflow: start → connect → chat → disconnect → stop.

        This tests the full lifecycle of working with an instance:
        1. Start a new instance
        2. Connect to it
        3. Send messages
        4. Disconnect
        5. Stop the instance
        """
        # Setup instance info
        instance = InstanceInfo(
            name="test-app",
            project_path=temp_project_dir,
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
            git_branch="main",
            git_status="clean",
        )

        # Step 1: Start instance
        mock_instance_manager.start_instance.return_value = instance
        await repl._cmd_start(
            [str(temp_project_dir), "--framework", "cc", "--name", "test-app"]
        )

        mock_instance_manager.start_instance.assert_called_once()
        # start_instance(name, project_path, framework)
        call_args = mock_instance_manager.start_instance.call_args[0]
        assert call_args[0] == "test-app"  # name
        assert call_args[1] == temp_project_dir  # project_path
        assert call_args[2] == "cc"  # framework

        # Step 2: Connect to instance
        mock_instance_manager.get_instance.return_value = instance
        await repl._cmd_connect(["test-app"])

        assert session_manager.context.is_connected
        assert session_manager.context.connected_instance == "test-app"

        # Step 3: Send messages
        await repl._send_to_instance("Show me the project structure")

        assert len(session_manager.context.messages) == 1
        assert (
            session_manager.context.messages[0].content
            == "Show me the project structure"
        )
        mock_instance_manager.send_to_instance.assert_called_with(
            "test-app", "Show me the project structure"
        )

        # Send another message
        await repl._send_to_instance("Create a new file called test.py")

        assert len(session_manager.context.messages) == 2
        assert mock_instance_manager.send_to_instance.call_count == 2

        # Step 4: Disconnect
        await repl._cmd_disconnect([])

        assert not session_manager.context.is_connected
        assert session_manager.context.connected_instance is None

        # Step 5: Stop instance
        await repl._cmd_stop(["test-app"])

        mock_instance_manager.stop_instance.assert_called_once_with("test-app")

    @pytest.mark.asyncio
    async def test_multiple_instances(
        self, repl, mock_instance_manager, session_manager, temp_project_dir
    ):
        """Test managing multiple instances simultaneously.

        Tests that Commander can:
        1. Start multiple instances
        2. Switch between them
        3. Maintain separate session state
        4. Stop them independently
        """
        # Create two project directories
        project1 = temp_project_dir / "app1"
        project2 = temp_project_dir / "app2"
        project1.mkdir()
        project2.mkdir()

        # Create instance info for both
        instance1 = InstanceInfo(
            name="app1",
            project_path=project1,
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
        )
        instance2 = InstanceInfo(
            name="app2",
            project_path=project2,
            framework="mpm",
            tmux_session="mpm-commander",
            pane_target="%2",
        )

        # Start both instances
        mock_instance_manager.start_instance.side_effect = [instance1, instance2]
        await repl._cmd_start([str(project1), "--name", "app1", "--framework", "cc"])
        await repl._cmd_start([str(project2), "--name", "app2", "--framework", "mpm"])

        # List should show both
        mock_instance_manager.list_instances.return_value = [instance1, instance2]
        await repl._cmd_list([])

        # Connect to first instance
        mock_instance_manager.get_instance.side_effect = lambda name: (
            instance1 if name == "app1" else instance2
        )
        await repl._cmd_connect(["app1"])

        assert session_manager.context.connected_instance == "app1"

        # Send message to first
        await repl._send_to_instance("Message to app1")
        assert len(session_manager.context.messages) == 1

        # Switch to second instance
        await repl._cmd_connect(["app2"])

        assert session_manager.context.connected_instance == "app2"
        # Messages should be preserved across connections
        assert len(session_manager.context.messages) > 0

        # Send message to second
        await repl._send_to_instance("Message to app2")

        # Verify correct instance received message
        last_call = mock_instance_manager.send_to_instance.call_args_list[-1]
        assert last_call[0][0] == "app2"
        assert last_call[0][1] == "Message to app2"

        # Stop first instance
        await repl._cmd_stop(["app1"])

        # Second should still be running
        assert session_manager.context.connected_instance == "app2"

    @pytest.mark.asyncio
    async def test_framework_selection(
        self, repl, mock_instance_manager, temp_project_dir
    ):
        """Test starting with different frameworks (cc, mpm).

        Ensures that framework selection is properly passed through
        and instances are started with the correct framework adapter.
        """
        # Test Claude Code framework
        instance_cc = InstanceInfo(
            name="cc-app",
            project_path=temp_project_dir,
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
        )
        mock_instance_manager.start_instance.return_value = instance_cc

        await repl._cmd_start(
            [str(temp_project_dir), "--framework", "cc", "--name", "cc-app"]
        )

        # start_instance(name, project_path, framework)
        call_args = mock_instance_manager.start_instance.call_args[0]
        assert call_args[2] == "cc"  # framework

        # Reset mock
        mock_instance_manager.start_instance.reset_mock()

        # Test MPM framework
        instance_mpm = InstanceInfo(
            name="mpm-app",
            project_path=temp_project_dir,
            framework="mpm",
            tmux_session="mpm-commander",
            pane_target="%2",
        )
        mock_instance_manager.start_instance.return_value = instance_mpm

        await repl._cmd_start(
            [str(temp_project_dir), "--framework", "mpm", "--name", "mpm-app"]
        )

        # start_instance(name, project_path, framework)
        call_args = mock_instance_manager.start_instance.call_args[0]
        assert call_args[2] == "mpm"  # framework

    @pytest.mark.asyncio
    async def test_output_summarization(
        self, repl, mock_instance_manager, session_manager
    ):
        """Test that long output gets summarized.

        When instances produce verbose output, the output proxy should
        detect and summarize it before displaying to the user.
        """
        # This test validates the integration with OutputRelay
        # In practice, the relay would intercept long output and summarize it

        instance = InstanceInfo(
            name="test-app",
            project_path=Path("/test"),
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
        )
        mock_instance_manager.get_instance.return_value = instance

        # Connect and enable relay (if initialized)
        await repl._cmd_connect(["test-app"])

        # Send a command that would generate long output
        await repl._send_to_instance("Run all tests with verbose output")

        # Verify message was sent
        assert mock_instance_manager.send_to_instance.called

        # In a real scenario, the relay would capture output and summarize
        # This integration test verifies the plumbing is in place
        assert session_manager.context.is_connected

    @pytest.mark.asyncio
    async def test_session_persistence(
        self, repl, mock_instance_manager, session_manager, temp_project_dir
    ):
        """Test session state persists across operations.

        Session context should maintain:
        - Connection state
        - Message history
        - Current instance info
        """
        instance = InstanceInfo(
            name="persistent-app",
            project_path=temp_project_dir,
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
        )
        mock_instance_manager.get_instance.return_value = instance

        # Connect to instance
        await repl._cmd_connect(["persistent-app"])
        initial_connection = session_manager.context.connected_instance

        # Send multiple messages
        messages = [
            "First message",
            "Second message",
            "Third message",
        ]
        for msg in messages:
            await repl._send_to_instance(msg)

        # Verify state persisted
        assert session_manager.context.connected_instance == initial_connection
        assert len(session_manager.context.messages) == len(messages)

        # Verify message order preserved
        for i, msg in enumerate(messages):
            assert session_manager.context.messages[i].content == msg

        # Disconnect and verify state cleared appropriately
        await repl._cmd_disconnect([])

        assert not session_manager.context.is_connected
        # Messages may be cleared or preserved depending on implementation

    @pytest.mark.asyncio
    async def test_command_parsing(self, repl, mock_instance_manager, session_manager):
        """Test all built-in commands work correctly.

        Tests command parsing and execution for:
        - list/ls
        - start
        - stop
        - connect
        - disconnect
        - status
        - help
        - exit
        """
        # Test list command (alias: ls)
        await repl._cmd_list([])
        mock_instance_manager.list_instances.assert_called()

        # Test help command
        await repl._cmd_help([])
        # Should not raise error

        # Test status when not connected
        await repl._cmd_status([])
        assert not session_manager.context.is_connected

        # Test exit command
        repl._running = True
        await repl._cmd_exit([])
        assert not repl._running

        # Test status when connected
        instance = InstanceInfo(
            name="status-app",
            project_path=Path("/test"),
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
            git_branch="feature/test",
            git_status="modified",
        )
        mock_instance_manager.get_instance.return_value = instance

        await repl._cmd_connect(["status-app"])
        await repl._cmd_status([])

        assert session_manager.context.is_connected
        assert session_manager.context.connected_instance == "status-app"

    @pytest.mark.asyncio
    async def test_error_handling(self, repl, mock_instance_manager, session_manager):
        """Test error handling in various scenarios.

        Tests:
        - Connecting to non-existent instance
        - Stopping non-existent instance
        - Sending message when not connected
        - Invalid command arguments
        """
        # Connect to non-existent instance
        mock_instance_manager.get_instance.return_value = None
        await repl._cmd_connect(["nonexistent"])

        assert not session_manager.context.is_connected

        # Send message when not connected
        await repl._send_to_instance("This should fail")

        assert not mock_instance_manager.send_to_instance.called

        # Disconnect when not connected
        await repl._cmd_disconnect([])
        # Should handle gracefully

        # Commands without required arguments
        await repl._cmd_start([])  # Missing path
        await repl._cmd_stop([])  # Missing name
        await repl._cmd_connect([])  # Missing name

    @pytest.mark.asyncio
    async def test_git_integration(
        self, repl, mock_instance_manager, session_manager, temp_project_dir
    ):
        """Test git branch and status display in instance info.

        When starting or connecting to instances, git information
        should be captured and displayed.
        """
        # Create git repo
        (temp_project_dir / ".git").mkdir(exist_ok=True)

        instance = InstanceInfo(
            name="git-app",
            project_path=temp_project_dir,
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
            git_branch="feature/new-feature",
            git_status="modified: 2 files",
        )

        mock_instance_manager.get_instance.return_value = instance
        mock_instance_manager.list_instances.return_value = [instance]

        # Connect and check status
        await repl._cmd_connect(["git-app"])
        await repl._cmd_status([])

        # List should show git info
        await repl._cmd_list([])

        assert session_manager.context.is_connected


@pytest.mark.integration
class TestChatEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_rapid_connection_switching(
        self, repl, mock_instance_manager, session_manager
    ):
        """Test rapidly switching between instances."""
        instances = [
            InstanceInfo(
                name=f"app{i}",
                project_path=Path(f"/test/app{i}"),
                framework="cc",
                tmux_session="mpm-commander",
                pane_target=f"%{i}",
            )
            for i in range(5)
        ]

        mock_instance_manager.get_instance.side_effect = lambda name: next(
            (inst for inst in instances if inst.name == name), None
        )

        # Rapidly switch between instances
        for instance in instances:
            await repl._cmd_connect([instance.name])
            assert session_manager.context.connected_instance == instance.name

    @pytest.mark.asyncio
    async def test_concurrent_message_sending(
        self, repl, mock_instance_manager, session_manager
    ):
        """Test sending multiple messages concurrently."""
        instance = InstanceInfo(
            name="concurrent-app",
            project_path=Path("/test"),
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
        )
        mock_instance_manager.get_instance.return_value = instance

        await repl._cmd_connect(["concurrent-app"])

        # Send multiple messages in quick succession
        messages = [f"Message {i}" for i in range(10)]
        tasks = [repl._send_to_instance(msg) for msg in messages]
        await asyncio.gather(*tasks)

        # All messages should be tracked
        assert len(session_manager.context.messages) == len(messages)

    @pytest.mark.asyncio
    async def test_empty_and_whitespace_messages(
        self, repl, mock_instance_manager, session_manager
    ):
        """Test handling of empty and whitespace-only messages."""
        instance = InstanceInfo(
            name="test-app",
            project_path=Path("/test"),
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
        )
        mock_instance_manager.get_instance.return_value = instance

        await repl._cmd_connect(["test-app"])

        # These should be handled gracefully
        await repl._send_to_instance("")
        await repl._send_to_instance("   ")
        await repl._send_to_instance("\n\n")

    @pytest.mark.asyncio
    async def test_long_message_handling(
        self, repl, mock_instance_manager, session_manager
    ):
        """Test handling of very long messages."""
        instance = InstanceInfo(
            name="test-app",
            project_path=Path("/test"),
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
        )
        mock_instance_manager.get_instance.return_value = instance

        await repl._cmd_connect(["test-app"])

        # Send a very long message
        long_message = "A" * 10000
        await repl._send_to_instance(long_message)

        assert len(session_manager.context.messages) == 1
        assert session_manager.context.messages[0].content == long_message
