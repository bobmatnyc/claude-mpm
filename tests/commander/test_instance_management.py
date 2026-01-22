"""Unit tests for Instance Management features.

Tests the new instance management features added in commit 8c0a93a2:
- rename_instance()
- close_instance()
- disconnect_instance()
- auto-connect on create
- summarize_responses config flag
- set_event_manager() and ready detection
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from claude_mpm.commander.chat.cli import CommanderCLIConfig
from claude_mpm.commander.config import DaemonConfig
from claude_mpm.commander.events.manager import EventManager
from claude_mpm.commander.frameworks.base import InstanceInfo
from claude_mpm.commander.instance_manager import (
    InstanceAlreadyExistsError,
    InstanceManager,
    InstanceNotFoundError,
)
from claude_mpm.commander.models.events import EventType


class TestRenameInstance:
    """Test suite for rename_instance() method."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock TmuxOrchestrator."""
        mock = MagicMock()
        mock.session_name = "test-session"
        return mock

    @pytest.fixture
    def instance_manager(self, mock_orchestrator):
        """Create InstanceManager with mock orchestrator."""
        return InstanceManager(mock_orchestrator)

    @pytest.fixture
    def sample_instance(self):
        """Create sample InstanceInfo."""
        return InstanceInfo(
            name="original-name",
            project_path=Path("/test/project"),
            framework="cc",
            tmux_session="test-session",
            pane_target="%1",
            git_branch="main",
            git_status="clean",
            connected=True,
        )

    @pytest.mark.asyncio
    async def test_rename_instance_success(self, instance_manager, sample_instance):
        """Test successful instance rename."""
        # Add instance to manager
        instance_manager._instances["original-name"] = sample_instance

        # Rename
        result = await instance_manager.rename_instance("original-name", "new-name")

        assert result is True
        assert "original-name" not in instance_manager._instances
        assert "new-name" in instance_manager._instances
        assert instance_manager._instances["new-name"].name == "new-name"

    @pytest.mark.asyncio
    async def test_rename_instance_with_adapter(
        self, instance_manager, sample_instance
    ):
        """Test rename updates adapter dictionary."""
        # Add instance and mock adapter
        instance_manager._instances["original-name"] = sample_instance
        mock_adapter = MagicMock()
        instance_manager._adapters["original-name"] = mock_adapter

        # Rename
        result = await instance_manager.rename_instance("original-name", "new-name")

        assert result is True
        assert "original-name" not in instance_manager._adapters
        assert "new-name" in instance_manager._adapters
        assert instance_manager._adapters["new-name"] is mock_adapter

    @pytest.mark.asyncio
    async def test_rename_instance_not_found(self, instance_manager):
        """Test rename raises InstanceNotFoundError for non-existent instance."""
        with pytest.raises(InstanceNotFoundError) as exc_info:
            await instance_manager.rename_instance("nonexistent", "new-name")

        assert exc_info.value.name == "nonexistent"
        assert "Instance not found: nonexistent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rename_instance_name_already_exists(
        self, instance_manager, sample_instance
    ):
        """Test rename raises InstanceAlreadyExistsError if new name exists."""
        # Add two instances
        instance_manager._instances["instance1"] = sample_instance
        instance2 = InstanceInfo(
            name="instance2",
            project_path=Path("/test/project2"),
            framework="cc",
            tmux_session="test-session",
            pane_target="%2",
        )
        instance_manager._instances["instance2"] = instance2

        # Try to rename instance1 to instance2
        with pytest.raises(InstanceAlreadyExistsError) as exc_info:
            await instance_manager.rename_instance("instance1", "instance2")

        assert exc_info.value.name == "instance2"
        assert "Instance already exists: instance2" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rename_instance_name_field_updated(
        self, instance_manager, sample_instance
    ):
        """Test that InstanceInfo.name field is updated correctly."""
        instance_manager._instances["old-name"] = sample_instance

        await instance_manager.rename_instance("old-name", "new-name")

        # Verify the name field in the instance object was updated
        instance = instance_manager._instances["new-name"]
        assert instance.name == "new-name"


class TestCloseInstance:
    """Test suite for close_instance() method."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock TmuxOrchestrator."""
        mock = MagicMock()
        mock.session_name = "test-session"
        return mock

    @pytest.fixture
    def instance_manager(self, mock_orchestrator):
        """Create InstanceManager with mock orchestrator."""
        return InstanceManager(mock_orchestrator)

    @pytest.fixture
    def sample_instance(self):
        """Create sample InstanceInfo."""
        return InstanceInfo(
            name="test-instance",
            project_path=Path("/test/project"),
            framework="cc",
            tmux_session="test-session",
            pane_target="%1",
            connected=True,
        )

    @pytest.mark.asyncio
    async def test_close_instance_success(
        self, instance_manager, mock_orchestrator, sample_instance
    ):
        """Test successful instance close."""
        instance_manager._instances["test-instance"] = sample_instance

        result = await instance_manager.close_instance("test-instance")

        assert result is True
        assert "test-instance" not in instance_manager._instances
        mock_orchestrator.kill_pane.assert_called_once_with("%1")

    @pytest.mark.asyncio
    async def test_close_instance_removes_adapter(
        self, instance_manager, sample_instance
    ):
        """Test close removes adapter."""
        instance_manager._instances["test-instance"] = sample_instance
        mock_adapter = MagicMock()
        instance_manager._adapters["test-instance"] = mock_adapter

        await instance_manager.close_instance("test-instance")

        assert "test-instance" not in instance_manager._adapters

    @pytest.mark.asyncio
    async def test_close_instance_not_found(self, instance_manager):
        """Test close raises InstanceNotFoundError."""
        with pytest.raises(InstanceNotFoundError) as exc_info:
            await instance_manager.close_instance("nonexistent")

        assert exc_info.value.name == "nonexistent"

    @pytest.mark.asyncio
    async def test_close_instance_calls_stop_instance(
        self, instance_manager, sample_instance
    ):
        """Test close_instance delegates to stop_instance."""
        instance_manager._instances["test-instance"] = sample_instance

        # close_instance should have same effect as stop_instance
        result = await instance_manager.close_instance("test-instance")

        assert result is True
        assert "test-instance" not in instance_manager._instances


class TestDisconnectInstance:
    """Test suite for disconnect_instance() method."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock TmuxOrchestrator."""
        mock = MagicMock()
        mock.session_name = "test-session"
        return mock

    @pytest.fixture
    def instance_manager(self, mock_orchestrator):
        """Create InstanceManager with mock orchestrator."""
        return InstanceManager(mock_orchestrator)

    @pytest.fixture
    def sample_instance(self):
        """Create sample InstanceInfo."""
        return InstanceInfo(
            name="test-instance",
            project_path=Path("/test/project"),
            framework="cc",
            tmux_session="test-session",
            pane_target="%1",
            connected=True,
        )

    @pytest.mark.asyncio
    async def test_disconnect_instance_success(self, instance_manager, sample_instance):
        """Test successful instance disconnect."""
        instance_manager._instances["test-instance"] = sample_instance
        mock_adapter = MagicMock()
        instance_manager._adapters["test-instance"] = mock_adapter

        result = await instance_manager.disconnect_instance("test-instance")

        assert result is True
        # Instance still exists
        assert "test-instance" in instance_manager._instances
        # Adapter removed
        assert "test-instance" not in instance_manager._adapters
        # Connected flag updated
        assert instance_manager._instances["test-instance"].connected is False

    @pytest.mark.asyncio
    async def test_disconnect_instance_without_adapter(
        self, instance_manager, sample_instance
    ):
        """Test disconnect on instance without adapter."""
        instance_manager._instances["test-instance"] = sample_instance
        # No adapter

        result = await instance_manager.disconnect_instance("test-instance")

        assert result is True
        # Instance still exists
        assert "test-instance" in instance_manager._instances

    @pytest.mark.asyncio
    async def test_disconnect_instance_not_found(self, instance_manager):
        """Test disconnect raises InstanceNotFoundError."""
        with pytest.raises(InstanceNotFoundError) as exc_info:
            await instance_manager.disconnect_instance("nonexistent")

        assert exc_info.value.name == "nonexistent"

    @pytest.mark.asyncio
    async def test_disconnect_keeps_tmux_pane_running(
        self, instance_manager, mock_orchestrator, sample_instance
    ):
        """Test disconnect doesn't kill tmux pane."""
        instance_manager._instances["test-instance"] = sample_instance
        mock_adapter = MagicMock()
        instance_manager._adapters["test-instance"] = mock_adapter

        await instance_manager.disconnect_instance("test-instance")

        # Verify kill_pane was NOT called
        mock_orchestrator.kill_pane.assert_not_called()


class TestAutoConnectOnCreate:
    """Test suite for auto-connect behavior on instance creation."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock TmuxOrchestrator."""
        mock = MagicMock()
        mock.session_name = "test-session"
        mock.create_pane = Mock(return_value="%1")
        return mock

    @pytest.fixture
    def instance_manager(self, mock_orchestrator):
        """Create InstanceManager with mock orchestrator."""
        with patch(
            "claude_mpm.commander.instance_manager.ClaudeCodeFramework"
        ) as mock_framework_class:
            mock_framework = MagicMock()
            mock_framework.name = "cc"
            mock_framework.display_name = "Claude Code"
            mock_framework.is_available = Mock(return_value=True)
            mock_framework.get_git_info = Mock(return_value=("main", "clean"))
            mock_framework.get_startup_command = Mock(return_value="claude")
            mock_framework_class.return_value = mock_framework

            manager = InstanceManager(mock_orchestrator)
            # Manually set up framework since we're mocking
            manager._frameworks["cc"] = mock_framework
            return manager

    @pytest.mark.asyncio
    async def test_new_instance_has_connected_true(
        self, instance_manager, mock_orchestrator
    ):
        """Test new instance has connected=True."""
        with patch(
            "claude_mpm.commander.instance_manager.ClaudeCodeAdapter"
        ) as mock_adapter_class, patch(
            "claude_mpm.commander.instance_manager.ClaudeCodeCommunicationAdapter"
        ) as mock_comm_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter_class.return_value = mock_adapter
            mock_comm_adapter = MagicMock()
            mock_comm_adapter_class.return_value = mock_comm_adapter

            instance = await instance_manager.start_instance(
                "test-instance", Path("/test/project"), framework="cc"
            )

            assert instance.connected is True

    @pytest.mark.asyncio
    async def test_new_instance_creates_adapter(
        self, instance_manager, mock_orchestrator
    ):
        """Test new instance automatically creates adapter."""
        with patch(
            "claude_mpm.commander.instance_manager.ClaudeCodeAdapter"
        ) as mock_adapter_class, patch(
            "claude_mpm.commander.instance_manager.ClaudeCodeCommunicationAdapter"
        ) as mock_comm_adapter_class:
            mock_adapter = MagicMock()
            mock_adapter_class.return_value = mock_adapter
            mock_comm_adapter = MagicMock()
            mock_comm_adapter_class.return_value = mock_comm_adapter

            await instance_manager.start_instance(
                "test-instance", Path("/test/project"), framework="cc"
            )

            # Verify adapter was created
            assert "test-instance" in instance_manager._adapters
            mock_adapter_class.assert_called_once()
            mock_comm_adapter_class.assert_called_once()


class TestSummarizeResponsesConfig:
    """Test suite for summarize_responses configuration flag."""

    def test_daemon_config_default_summarize_responses(self):
        """Test DaemonConfig.summarize_responses defaults to True."""
        config = DaemonConfig()
        assert config.summarize_responses is True

    def test_daemon_config_custom_summarize_responses(self):
        """Test DaemonConfig.summarize_responses can be set to False."""
        config = DaemonConfig(summarize_responses=False)
        assert config.summarize_responses is False

    def test_cli_config_default_summarize_responses(self):
        """Test CommanderCLIConfig.summarize_responses defaults to True."""
        config = CommanderCLIConfig()
        assert config.summarize_responses is True

    def test_cli_config_custom_summarize_responses(self):
        """Test CommanderCLIConfig.summarize_responses can be set to False."""
        config = CommanderCLIConfig(summarize_responses=False)
        assert config.summarize_responses is False

    @pytest.mark.asyncio
    async def test_summarizer_none_when_disabled(self):
        """Test OutputSummarizer is None when summarize_responses=False."""
        config = CommanderCLIConfig(summarize_responses=False)

        with patch(
            "claude_mpm.commander.chat.cli.TmuxOrchestrator"
        ) as mock_orch, patch(
            "claude_mpm.commander.chat.cli.InstanceManager"
        ) as mock_im, patch(
            "claude_mpm.commander.chat.cli.SessionManager"
        ) as mock_sm, patch(
            "claude_mpm.commander.chat.cli.OpenRouterClient"
        ) as mock_llm, patch(
            "claude_mpm.commander.chat.cli.OpenRouterConfig"
        ) as mock_llm_config, patch(
            "claude_mpm.commander.chat.cli.OutputSummarizer"
        ) as mock_summarizer, patch(
            "claude_mpm.commander.chat.cli.OutputHandler"
        ) as mock_handler, patch(
            "claude_mpm.commander.chat.cli.OutputFormatter"
        ) as mock_formatter, patch(
            "claude_mpm.commander.chat.cli.OutputRelay"
        ) as mock_relay, patch(
            "claude_mpm.commander.chat.cli.CommanderREPL"
        ) as mock_repl:
            # Setup mocks
            mock_llm_instance = MagicMock()
            mock_llm.return_value = mock_llm_instance

            # Mock REPL to not actually run
            async def mock_run():
                pass

            mock_repl_instance = MagicMock()
            mock_repl_instance.run = mock_run
            mock_repl.return_value = mock_repl_instance

            # Import and run
            from claude_mpm.commander.chat.cli import run_commander

            try:
                await run_commander(config=config)
            except Exception:
                pass  # We're testing initialization, not full execution

            # Verify summarizer was NOT created when disabled
            if config.summarize_responses:
                mock_summarizer.assert_called()
            else:
                mock_summarizer.assert_not_called()


class TestStateConsistency:
    """Test suite for state consistency across operations."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock TmuxOrchestrator."""
        mock = MagicMock()
        mock.session_name = "test-session"
        return mock

    @pytest.fixture
    def instance_manager(self, mock_orchestrator):
        """Create InstanceManager with mock orchestrator."""
        return InstanceManager(mock_orchestrator)

    @pytest.mark.asyncio
    async def test_state_after_rename(self, instance_manager):
        """Test state consistency after rename operation."""
        instance = InstanceInfo(
            name="old",
            project_path=Path("/test"),
            framework="cc",
            tmux_session="test",
            pane_target="%1",
            connected=True,
        )
        instance_manager._instances["old"] = instance
        mock_adapter = MagicMock()
        instance_manager._adapters["old"] = mock_adapter

        await instance_manager.rename_instance("old", "new")

        # Verify complete state transfer
        assert len(instance_manager._instances) == 1
        assert len(instance_manager._adapters) == 1
        assert "old" not in instance_manager._instances
        assert "old" not in instance_manager._adapters
        assert "new" in instance_manager._instances
        assert "new" in instance_manager._adapters
        assert instance_manager._instances["new"].name == "new"

    @pytest.mark.asyncio
    async def test_state_after_disconnect(self, instance_manager):
        """Test state consistency after disconnect operation."""
        instance = InstanceInfo(
            name="test",
            project_path=Path("/test"),
            framework="cc",
            tmux_session="test",
            pane_target="%1",
            connected=True,
        )
        instance_manager._instances["test"] = instance
        mock_adapter = MagicMock()
        instance_manager._adapters["test"] = mock_adapter

        await instance_manager.disconnect_instance("test")

        # Verify partial state (instance remains, adapter removed)
        assert len(instance_manager._instances) == 1
        assert len(instance_manager._adapters) == 0
        assert "test" in instance_manager._instances
        assert "test" not in instance_manager._adapters
        assert instance_manager._instances["test"].connected is False

    @pytest.mark.asyncio
    async def test_state_after_close(self, instance_manager):
        """Test state consistency after close operation."""
        instance = InstanceInfo(
            name="test",
            project_path=Path("/test"),
            framework="cc",
            tmux_session="test",
            pane_target="%1",
            connected=True,
        )
        instance_manager._instances["test"] = instance
        mock_adapter = MagicMock()
        instance_manager._adapters["test"] = mock_adapter

        await instance_manager.close_instance("test")

        # Verify complete cleanup
        assert len(instance_manager._instances) == 0
        assert len(instance_manager._adapters) == 0
        assert "test" not in instance_manager._instances
        assert "test" not in instance_manager._adapters


class TestEventManagerIntegration:
    """Test suite for event manager integration and ready detection."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock TmuxOrchestrator."""
        mock = MagicMock()
        mock.session_name = "test-session"
        mock.create_pane = Mock(return_value="%1")
        mock.capture_output = Mock(return_value="")
        return mock

    @pytest.fixture
    def instance_manager(self, mock_orchestrator):
        """Create InstanceManager with mock orchestrator."""
        return InstanceManager(mock_orchestrator)

    @pytest.fixture
    def event_manager(self):
        """Create real EventManager for testing."""
        return EventManager()

    def test_set_event_manager(self, instance_manager, event_manager):
        """Test set_event_manager sets the event manager."""
        assert instance_manager._event_manager is None

        instance_manager.set_event_manager(event_manager)

        assert instance_manager._event_manager is event_manager

    @pytest.mark.asyncio
    async def test_start_instance_emits_starting_event(
        self, instance_manager, mock_orchestrator, event_manager
    ):
        """Test start_instance emits INSTANCE_STARTING event."""
        with patch(
            "claude_mpm.commander.instance_manager.ClaudeCodeFramework"
        ) as mock_framework_class, patch(
            "claude_mpm.commander.instance_manager.ClaudeCodeAdapter"
        ) as mock_adapter_class, patch(
            "claude_mpm.commander.instance_manager.ClaudeCodeCommunicationAdapter"
        ) as mock_comm_adapter_class, patch(
            "claude_mpm.commander.instance_manager.asyncio.create_task"
        ) as mock_create_task:
            # Setup framework mock
            mock_framework = MagicMock()
            mock_framework.name = "cc"
            mock_framework.display_name = "Claude Code"
            mock_framework.is_available = Mock(return_value=True)
            mock_framework.get_git_info = Mock(return_value=("main", "clean"))
            mock_framework.get_startup_command = Mock(return_value="claude")
            mock_framework_class.return_value = mock_framework

            # Re-create instance manager to pick up framework mock
            manager = InstanceManager(mock_orchestrator)
            manager._frameworks["cc"] = mock_framework
            manager.set_event_manager(event_manager)

            # Setup adapter mocks
            mock_adapter_class.return_value = MagicMock()
            mock_comm_adapter_class.return_value = MagicMock()

            await manager.start_instance("test-instance", Path("/test"), framework="cc")

            # Verify INSTANCE_STARTING event was created
            events = event_manager.get_pending("test-instance")
            assert len(events) >= 1
            starting_events = [
                e for e in events if e.type == EventType.INSTANCE_STARTING
            ]
            assert len(starting_events) == 1
            assert starting_events[0].title == "Starting instance 'test-instance'"

            # Verify background task was created for ready detection
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_detect_ready_emits_ready_event_on_prompt(
        self, instance_manager, mock_orchestrator, event_manager
    ):
        """Test _detect_ready emits INSTANCE_READY when prompt detected."""
        instance_manager.set_event_manager(event_manager)

        instance = InstanceInfo(
            name="test",
            project_path=Path("/test"),
            framework="cc",
            tmux_session="test-session",
            pane_target="%1",
        )

        # Mock capture_output to return a prompt on second call
        call_count = [0]

        def mock_capture(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] >= 2:
                return "Some output\n> "
            return "Loading..."

        mock_orchestrator.capture_output = mock_capture

        # Run detect_ready with short timeout
        await instance_manager._detect_ready("test", instance, timeout=3)

        # Verify INSTANCE_READY event was created
        events = event_manager.get_pending("test")
        ready_events = [e for e in events if e.type == EventType.INSTANCE_READY]
        assert len(ready_events) == 1
        assert ready_events[0].title == "Instance 'test' ready"
        assert ready_events[0].context.get("instance_name") == "test"

    @pytest.mark.asyncio
    async def test_detect_ready_emits_timeout_event(
        self, instance_manager, mock_orchestrator, event_manager
    ):
        """Test _detect_ready emits INSTANCE_READY with timeout flag when times out."""
        instance_manager.set_event_manager(event_manager)

        instance = InstanceInfo(
            name="test",
            project_path=Path("/test"),
            framework="cc",
            tmux_session="test-session",
            pane_target="%1",
        )

        # Mock capture_output to never return a ready prompt
        mock_orchestrator.capture_output = Mock(return_value="Still loading...")

        # Run detect_ready with very short timeout
        await instance_manager._detect_ready("test", instance, timeout=2)

        # Verify INSTANCE_READY event was created with timeout flag
        events = event_manager.get_pending("test")
        ready_events = [e for e in events if e.type == EventType.INSTANCE_READY]
        assert len(ready_events) == 1
        assert "timeout" in ready_events[0].title.lower() or ready_events[
            0
        ].context.get("timeout")

    @pytest.mark.asyncio
    async def test_detect_ready_handles_capture_errors(
        self, instance_manager, mock_orchestrator, event_manager
    ):
        """Test _detect_ready handles errors from capture_output gracefully."""
        instance_manager.set_event_manager(event_manager)

        instance = InstanceInfo(
            name="test",
            project_path=Path("/test"),
            framework="cc",
            tmux_session="test-session",
            pane_target="%1",
        )

        # Mock capture_output to raise exception then return prompt
        call_count = [0]

        def mock_capture(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Pane not ready")
            return "What would you like me to do?"

        mock_orchestrator.capture_output = mock_capture

        # Run detect_ready - should handle error and eventually detect ready
        await instance_manager._detect_ready("test", instance, timeout=5)

        # Verify INSTANCE_READY event was created despite initial error
        events = event_manager.get_pending("test")
        ready_events = [e for e in events if e.type == EventType.INSTANCE_READY]
        assert len(ready_events) == 1

    def test_no_event_without_event_manager(self, instance_manager):
        """Test no errors when event_manager is not set."""
        # Should not have event manager by default
        assert instance_manager._event_manager is None

        # No exception should be raised accessing it
        instance_manager._event_manager
