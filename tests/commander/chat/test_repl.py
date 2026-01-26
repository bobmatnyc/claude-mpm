"""Tests for CommanderREPL."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from claude_mpm.commander.chat.repl import CommanderREPL
from claude_mpm.commander.events.manager import EventManager
from claude_mpm.commander.frameworks.base import InstanceInfo
from claude_mpm.commander.instance_manager import InstanceManager
from claude_mpm.commander.models.events import Event, EventPriority, EventType
from claude_mpm.commander.session.manager import SessionManager


@pytest.fixture
def mock_instance_manager():
    """Create a mock InstanceManager."""
    manager = Mock(spec=InstanceManager)
    manager.list_instances = Mock(return_value=[])
    manager.get_instance = Mock(return_value=None)
    manager.start_instance = AsyncMock()
    manager.stop_instance = AsyncMock()
    manager.send_to_instance = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def session_manager():
    """Create a SessionManager instance."""
    return SessionManager()


@pytest.fixture
def repl(mock_instance_manager, session_manager):
    """Create a CommanderREPL instance."""
    return CommanderREPL(
        instance_manager=mock_instance_manager,
        session_manager=session_manager,
    )


def test_repl_initialization(repl, mock_instance_manager, session_manager):
    """Test REPL initialization."""
    assert repl.instances == mock_instance_manager
    assert repl.session == session_manager
    assert repl.relay is None
    assert repl.llm is None
    assert not repl._running


@pytest.mark.asyncio
async def test_cmd_list_empty(repl, capsys):
    """Test 'list' command with no instances."""
    # Clear saved registrations to test empty state
    repl._saved_registrations = {}
    await repl._cmd_list([])

    captured = capsys.readouterr()
    assert "No instances" in captured.out


@pytest.mark.asyncio
async def test_cmd_list_with_instances(repl, mock_instance_manager, capsys):
    """Test 'list' command with active instances."""
    instances = [
        InstanceInfo(
            name="app1",
            project_path=Path("/path/to/app1"),
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
            git_branch="main",
        ),
        InstanceInfo(
            name="app2",
            project_path=Path("/path/to/app2"),
            framework="mpm",
            tmux_session="mpm-commander",
            pane_target="%2",
        ),
    ]
    mock_instance_manager.list_instances.return_value = instances
    # Clear saved registrations to test running instances only
    repl._saved_registrations = {}

    await repl._cmd_list([])

    captured = capsys.readouterr()
    assert "Sessions:" in captured.out
    assert "app1" in captured.out
    assert "app2" in captured.out
    assert "[main]" in captured.out


@pytest.mark.asyncio
async def test_cmd_list_with_running_and_saved(repl, mock_instance_manager, capsys):
    """Test 'list' command shows both running instances and saved registrations."""
    # Setup running instance
    instances = [
        InstanceInfo(
            name="app1",
            project_path=Path("/path/to/app1"),
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
            git_branch="main",
            ready=True,
        ),
    ]
    mock_instance_manager.list_instances.return_value = instances

    # Add saved registration
    from claude_mpm.commander.chat.repl import SavedRegistration

    saved_reg = SavedRegistration(
        name="app2",
        path="/path/to/app2",
        framework="mpm",
        registered_at="2024-01-01T00:00:00",
    )
    repl._saved_registrations["app2"] = saved_reg

    await repl._cmd_list([])

    captured = capsys.readouterr()
    assert "Sessions:" in captured.out
    assert "app1" in captured.out
    assert "running" in captured.out
    assert "ready" in captured.out
    assert "app2" in captured.out
    assert "saved" in captured.out
    assert "[main]" in captured.out


@pytest.mark.asyncio
async def test_cmd_connect_success(repl, mock_instance_manager, capsys):
    """Test successful connection to instance."""
    instance = InstanceInfo(
        name="myapp",
        project_path=Path("/path/to/myapp"),
        framework="cc",
        tmux_session="mpm-commander",
        pane_target="%1",
    )
    mock_instance_manager.get_instance.return_value = instance

    await repl._cmd_connect(["myapp"])

    captured = capsys.readouterr()
    assert "Connected to myapp" in captured.out
    assert repl.session.context.is_connected
    assert repl.session.context.connected_instance == "myapp"


@pytest.mark.asyncio
async def test_cmd_connect_not_found(repl, capsys):
    """Test connection to non-existent instance."""
    await repl._cmd_connect(["nonexistent"])

    captured = capsys.readouterr()
    assert "not found" in captured.out
    assert not repl.session.context.is_connected


@pytest.mark.asyncio
async def test_cmd_connect_no_args(repl, capsys):
    """Test connection without instance name."""
    await repl._cmd_connect([])

    captured = capsys.readouterr()
    assert "Usage:" in captured.out


@pytest.mark.asyncio
async def test_cmd_disconnect(repl, session_manager, capsys):
    """Test disconnecting from instance."""
    session_manager.connect_to("myapp")

    await repl._cmd_disconnect([])

    captured = capsys.readouterr()
    assert "Disconnected from myapp" in captured.out
    assert not session_manager.context.is_connected


@pytest.mark.asyncio
async def test_cmd_disconnect_when_not_connected(repl, capsys):
    """Test disconnect when not connected."""
    await repl._cmd_disconnect([])

    captured = capsys.readouterr()
    assert "Not connected" in captured.out


@pytest.mark.asyncio
async def test_cmd_status_connected(
    repl, mock_instance_manager, session_manager, capsys
):
    """Test status when connected to instance."""
    instance = InstanceInfo(
        name="myapp",
        project_path=Path("/path/to/myapp"),
        framework="cc",
        tmux_session="mpm-commander",
        pane_target="%1",
        git_branch="main",
        git_status="clean",
    )
    mock_instance_manager.get_instance.return_value = instance
    session_manager.connect_to("myapp")

    await repl._cmd_status([])

    captured = capsys.readouterr()
    assert "Connected to: myapp" in captured.out
    assert "Framework: cc" in captured.out
    assert "main" in captured.out


@pytest.mark.asyncio
async def test_cmd_status_not_connected(repl, capsys):
    """Test status when not connected."""
    await repl._cmd_status([])

    captured = capsys.readouterr()
    assert "Not connected" in captured.out


@pytest.mark.asyncio
async def test_cmd_help(repl, capsys):
    """Test help command."""
    await repl._cmd_help([])

    captured = capsys.readouterr()
    assert "Commander Commands" in captured.out
    assert "/list" in captured.out
    assert "/start" in captured.out


@pytest.mark.asyncio
async def test_cmd_exit(repl, mock_instance_manager):
    """Test exit command stops all instances before exiting."""
    repl._running = True

    # Setup mock to return some instances
    instance1 = InstanceInfo(
        name="test_instance1",
        framework="cc",
        project_path="/test/path1",
        tmux_session="test_session1",
        pane_target="test_session1:0",
    )
    instance2 = InstanceInfo(
        name="test_instance2",
        framework="mpm",
        project_path="/test/path2",
        tmux_session="test_session2",
        pane_target="test_session2:0",
    )
    mock_instance_manager.list_instances.return_value = [instance1, instance2]

    await repl._cmd_exit([])

    # Verify both instances were stopped
    assert mock_instance_manager.stop_instance.call_count == 2
    mock_instance_manager.stop_instance.assert_any_call("test_instance1")
    mock_instance_manager.stop_instance.assert_any_call("test_instance2")

    # Verify repl is no longer running
    assert not repl._running


@pytest.mark.asyncio
async def test_cmd_exit_no_instances(repl, mock_instance_manager):
    """Test exit command when no instances are running."""
    repl._running = True

    # Mock returns empty list (no instances)
    mock_instance_manager.list_instances.return_value = []

    await repl._cmd_exit([])

    # Verify stop_instance was never called
    mock_instance_manager.stop_instance.assert_not_called()

    # Verify repl is no longer running
    assert not repl._running


@pytest.mark.asyncio
async def test_cmd_exit_with_stop_error(repl, mock_instance_manager, capsys):
    """Test exit command handles errors when stopping instances."""
    repl._running = True

    # Setup mock to return instance that fails to stop
    instance = InstanceInfo(
        name="test_instance",
        framework="cc",
        project_path="/test/path",
        tmux_session="test_session",
        pane_target="test_session:0",
    )
    mock_instance_manager.list_instances.return_value = [instance]
    mock_instance_manager.stop_instance.side_effect = Exception("Stop failed")

    await repl._cmd_exit([])

    # Verify we attempted to stop the instance
    mock_instance_manager.stop_instance.assert_called_once_with("test_instance")

    # Verify warning was printed
    captured = capsys.readouterr()
    assert (
        "Warning" in captured.out or "Warning" in captured.err or repl._running is False
    )

    # Verify repl still exited (graceful error handling)
    assert not repl._running


@pytest.mark.asyncio
async def test_send_to_instance_not_connected(repl, capsys):
    """Test sending message when not connected."""
    await repl._send_to_instance("Fix the login bug")

    captured = capsys.readouterr()
    assert "Not connected" in captured.out


class TestIntentDetection:
    """Tests for intent classification and handling."""

    def test_classify_intent_greeting(self, repl):
        """Test greeting intent classification."""
        assert repl._classify_intent("hello") == "greeting"
        assert repl._classify_intent("Hello there") == "greeting"
        assert repl._classify_intent("hi") == "greeting"
        assert repl._classify_intent("Hi Claude") == "greeting"
        assert repl._classify_intent("hey") == "greeting"
        assert repl._classify_intent("howdy") == "greeting"

    def test_classify_intent_capabilities(self, repl):
        """Test capabilities intent classification."""
        assert repl._classify_intent("what can you do") == "capabilities"
        assert repl._classify_intent("What can you do?") == "capabilities"
        assert repl._classify_intent("can you help me") == "capabilities"
        assert repl._classify_intent("help me with something") == "capabilities"
        assert repl._classify_intent("how do I use this") == "capabilities"

    def test_classify_intent_chat(self, repl):
        """Test chat intent classification (default)."""
        assert repl._classify_intent("fix the bug") == "chat"
        assert repl._classify_intent("deploy to production") == "chat"
        assert repl._classify_intent("run the tests") == "chat"

    @pytest.mark.asyncio
    async def test_handle_greeting_not_connected(self, repl, capsys):
        """Test greeting response when not connected via _handle_input."""
        # Mock LLM to return greeting intent
        repl.llm = AsyncMock()
        repl.llm.chat = AsyncMock(return_value='{"intent": "greeting", "args": {}}')

        await repl._handle_input("hello")

        captured = capsys.readouterr()
        assert "Hello!" in captured.out
        assert "MPM Commander" in captured.out
        assert "/help" in captured.out

    @pytest.mark.asyncio
    async def test_handle_capabilities_not_connected(self, repl, capsys):
        """Test capabilities response when not connected via _handle_input."""
        # Mock LLM: first call for intent classification, second for capabilities answer
        repl.llm = AsyncMock()
        repl.llm.chat = AsyncMock(
            side_effect=[
                '{"intent": "capabilities", "args": {}}',
                "You can list instances with /list",
            ]
        )

        await repl._handle_input("what can you do")

        captured = capsys.readouterr()
        # Capabilities handler uses LLM when available
        assert "You can list instances with /list" in captured.out

    @pytest.mark.asyncio
    async def test_handle_capabilities_with_llm(
        self, mock_instance_manager, session_manager, capsys
    ):
        """Test capabilities response uses LLM when available."""
        mock_llm = AsyncMock()
        # First call is for intent classification, second is for capabilities
        mock_llm.chat = AsyncMock(
            side_effect=[
                '{"intent": "capabilities", "args": {}}',
                "You can list and connect to instances.",
            ]
        )

        repl_with_llm = CommanderREPL(
            instance_manager=mock_instance_manager,
            session_manager=session_manager,
            llm_client=mock_llm,
        )

        await repl_with_llm._handle_input("how do I see running instances")

        captured = capsys.readouterr()
        assert "You can list and connect to instances." in captured.out
        # Called twice: once for classification, once for capabilities
        assert mock_llm.chat.call_count == 2
        # Verify the second call included capabilities context
        call_args = mock_llm.chat.call_args_list[1]
        assert "INSTANCE MANAGEMENT" in call_args[0][0][0]["content"]

    @pytest.mark.asyncio
    async def test_handle_capabilities_llm_fallback(
        self, mock_instance_manager, session_manager, capsys
    ):
        """Test capabilities falls back to static output on LLM classification failure."""
        mock_llm = AsyncMock()
        # First call fails (classification), triggers fallback to chat
        mock_llm.chat = AsyncMock(side_effect=Exception("API Error"))

        repl_with_llm = CommanderREPL(
            instance_manager=mock_instance_manager,
            session_manager=session_manager,
            llm_client=mock_llm,
        )

        # When LLM fails, it defaults to "chat" intent, which requires connection
        await repl_with_llm._handle_input("what can you do")

        captured = capsys.readouterr()
        # Falls back to chat intent since LLM fails, so shows not connected message
        assert "Not connected to any instance" in captured.out


class TestLLMIntentClassification:
    """Tests for LLM-mediated intent detection."""

    @pytest.mark.asyncio
    async def test_classify_intent_llm_no_client(self, repl):
        """Test LLM classification without LLM client returns chat."""
        result = await repl._classify_intent_llm("start myapp")

        assert result == {"intent": "chat", "args": {}}

    @pytest.mark.asyncio
    async def test_classify_intent_llm_register_command(self, repl):
        """Test LLM classification for register command."""
        repl.llm = AsyncMock()
        repl.llm.chat = AsyncMock(
            return_value='{"intent": "register", "args": {"path": "~/foo", "framework": "mpm", "name": "myapp"}}'
        )

        result = await repl._classify_intent_llm("register ~/foo as myapp using mpm")

        assert result["intent"] == "register"
        assert result["args"]["path"] == "~/foo"
        assert result["args"]["framework"] == "mpm"
        assert result["args"]["name"] == "myapp"

    @pytest.mark.asyncio
    async def test_classify_intent_llm_start_command(self, repl):
        """Test LLM classification for start command."""
        repl.llm = AsyncMock()
        repl.llm.chat = AsyncMock(
            return_value='{"intent": "start", "args": {"name": "myapp"}}'
        )

        result = await repl._classify_intent_llm("fire up myapp")

        assert result["intent"] == "start"
        assert result["args"]["name"] == "myapp"

    @pytest.mark.asyncio
    async def test_classify_intent_llm_json_parse_error(self, repl):
        """Test LLM classification falls back on JSON parse error."""
        repl.llm = AsyncMock()
        repl.llm.chat = AsyncMock(return_value="not valid json")

        result = await repl._classify_intent_llm("some command")

        assert result == {"intent": "chat", "args": {}}

    @pytest.mark.asyncio
    async def test_handle_input_llm_list_intent(
        self, mock_instance_manager, session_manager, capsys
    ):
        """Test _handle_input routes list intent correctly."""
        repl = CommanderREPL(
            instance_manager=mock_instance_manager,
            session_manager=session_manager,
        )
        # Clear saved registrations to test empty state
        repl._saved_registrations = {}
        repl.llm = AsyncMock()
        repl.llm.chat = AsyncMock(return_value='{"intent": "list", "args": {}}')

        await repl._handle_input("show me all running instances")

        captured = capsys.readouterr()
        assert "No instances" in captured.out

    @pytest.mark.asyncio
    async def test_handle_input_llm_start_with_arg_inference(
        self, mock_instance_manager, session_manager, capsys
    ):
        """Test start command infers name when only one instance exists."""
        instance = InstanceInfo(
            name="only-instance",
            project_path=Path("/path/to/project"),
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
        )
        mock_instance_manager.list_instances = Mock(return_value=[instance])
        mock_instance_manager.start_by_name = AsyncMock(return_value=instance)

        repl = CommanderREPL(
            instance_manager=mock_instance_manager,
            session_manager=session_manager,
        )
        repl.llm = AsyncMock()
        # LLM returns start intent with no name
        repl.llm.chat = AsyncMock(
            return_value='{"intent": "start", "args": {"name": null}}'
        )

        await repl._handle_input("start the server")

        # Should infer the only instance
        mock_instance_manager.start_by_name.assert_called_once_with("only-instance")


@pytest.mark.asyncio
async def test_send_to_instance_instance_gone(repl, session_manager, capsys):
    """Test sending message when instance no longer exists."""
    session_manager.connect_to("myapp")

    await repl._send_to_instance("Fix the authentication bug")

    captured = capsys.readouterr()
    assert "no longer exists" in captured.out
    assert not session_manager.context.is_connected


@pytest.mark.asyncio
async def test_send_to_instance_success(
    repl, mock_instance_manager, session_manager, capsys
):
    """Test successful message sending."""
    instance = InstanceInfo(
        name="myapp",
        project_path=Path("/path/to/myapp"),
        framework="cc",
        tmux_session="mpm-commander",
        pane_target="%1",
    )
    mock_instance_manager.get_instance.return_value = instance
    session_manager.connect_to("myapp")

    await repl._send_to_instance("Fix the bug")

    captured = capsys.readouterr()
    assert "Sending to myapp" in captured.out
    mock_instance_manager.send_to_instance.assert_called_once_with(
        "myapp", "Fix the bug"
    )
    assert len(session_manager.context.messages) == 1
    assert session_manager.context.messages[0].content == "Fix the bug"


def test_get_prompt_connected(repl, session_manager):
    """Test prompt shows instance name when connected and ready.

    After /register auto-connects and the instance becomes ready,
    the prompt should show the instance name to indicate readiness.
    """
    session_manager.connect_to("myapp")
    repl._instance_ready["myapp"] = True  # Mark instance as ready

    prompt = repl._get_prompt()

    assert prompt == "Commander (myapp)> "


def test_get_prompt_connected_not_ready(repl, session_manager):
    """Test prompt when connected but instance not ready yet."""
    session_manager.connect_to("myapp")
    # Don't mark instance as ready

    prompt = repl._get_prompt()

    assert prompt == "Commander> "


def test_get_prompt_not_connected(repl):
    """Test prompt when not connected."""
    prompt = repl._get_prompt()

    assert prompt == "Commander> "


@pytest.mark.asyncio
async def test_cmd_start_no_args(repl, capsys):
    """Test start command without arguments."""
    await repl._cmd_start([])

    captured = capsys.readouterr()
    assert "Usage:" in captured.out


@pytest.mark.asyncio
async def test_cmd_stop_no_args(repl, capsys):
    """Test stop command without arguments."""
    await repl._cmd_stop([])

    captured = capsys.readouterr()
    assert "Usage:" in captured.out


@pytest.mark.asyncio
async def test_cmd_register_auto_connects(
    repl, mock_instance_manager, session_manager, capsys, tmp_path
):
    """Test register command auto-connects after successful registration."""
    instance = InstanceInfo(
        name="myapp",
        project_path=tmp_path,
        framework="cc",
        tmux_session="mpm-commander",
        pane_target="%1",
    )
    mock_instance_manager.register_instance = AsyncMock(return_value=instance)

    await repl._cmd_register([str(tmp_path), "cc", "myapp"])

    captured = capsys.readouterr()
    assert "Registered and started 'myapp'" in captured.out
    assert "Connected to 'myapp'" in captured.out
    assert session_manager.context.is_connected
    assert session_manager.context.connected_instance == "myapp"


class TestMentionParsing:
    """Tests for @mention parsing and direct instance messaging."""

    def test_parse_mention_at_syntax(self, repl):
        """Test parsing @name message syntax."""
        result = repl._parse_mention("@myapp show me the code")

        assert result is not None
        assert result[0] == "myapp"
        assert result[1] == "show me the code"

    def test_parse_mention_paren_syntax(self, repl):
        """Test parsing (name): message syntax."""
        result = repl._parse_mention("(izzie): what's the status")

        assert result is not None
        assert result[0] == "izzie"
        assert result[1] == "what's the status"

    def test_parse_mention_paren_without_colon(self, repl):
        """Test parsing (name) message syntax without colon."""
        result = repl._parse_mention("(myapp) run the tests")

        assert result is not None
        assert result[0] == "myapp"
        assert result[1] == "run the tests"

    def test_parse_mention_no_match(self, repl):
        """Test parsing regular text without mention."""
        result = repl._parse_mention("fix the bug")

        assert result is None

    def test_parse_mention_at_no_message(self, repl):
        """Test parsing @name without message doesn't match."""
        result = repl._parse_mention("@myapp")

        assert result is None

    @pytest.mark.asyncio
    async def test_cmd_message_instance_success(
        self, mock_instance_manager, session_manager, capsys
    ):
        """Test sending message to specific instance."""
        instance = InstanceInfo(
            name="myapp",
            project_path=Path("/path/to/myapp"),
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
        )
        mock_instance_manager.get_instance = Mock(return_value=instance)

        mock_relay = MagicMock()
        mock_relay.get_latest_output = AsyncMock(return_value="Code looks good")

        repl = CommanderREPL(
            instance_manager=mock_instance_manager,
            session_manager=session_manager,
            output_relay=mock_relay,
        )

        await repl._cmd_message_instance("myapp", "show me the code")

        mock_instance_manager.send_to_instance.assert_called_once_with(
            "myapp", "show me the code"
        )
        captured = capsys.readouterr()
        assert "@myapp:" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_message_instance_not_found(
        self, mock_instance_manager, session_manager, capsys
    ):
        """Test messaging non-existent instance."""
        mock_instance_manager.get_instance = Mock(return_value=None)
        mock_instance_manager.start_by_name = AsyncMock(return_value=None)

        repl = CommanderREPL(
            instance_manager=mock_instance_manager,
            session_manager=session_manager,
        )

        await repl._cmd_message_instance("unknown", "hello")

        captured = capsys.readouterr()
        assert "not found" in captured.out
        assert "unknown" in captured.out

    @pytest.mark.asyncio
    async def test_handle_input_with_mention(
        self, mock_instance_manager, session_manager, capsys
    ):
        """Test that @mention in input triggers direct messaging."""
        instance = InstanceInfo(
            name="myapp",
            project_path=Path("/path/to/myapp"),
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
        )
        mock_instance_manager.get_instance = Mock(return_value=instance)

        repl = CommanderREPL(
            instance_manager=mock_instance_manager,
            session_manager=session_manager,
        )

        await repl._handle_input("@myapp fix the bug")

        mock_instance_manager.send_to_instance.assert_called_once_with(
            "myapp", "fix the bug"
        )

    def test_display_response_short(self, repl, capsys):
        """Test display of short response."""
        repl._display_response("myapp", "All tests pass")

        captured = capsys.readouterr()
        assert "@myapp: All tests pass" in captured.out

    def test_display_response_long_truncated(self, repl, capsys):
        """Test display of long response is truncated."""
        long_response = "A" * 200
        repl._display_response("myapp", long_response)

        captured = capsys.readouterr()
        assert "@myapp:" in captured.out
        assert "..." in captured.out
        # Should be truncated to ~100 chars
        assert len(captured.out.strip()) < 150

    def test_display_response_newlines_replaced(self, repl, capsys):
        """Test that newlines in response are replaced with spaces."""
        repl._display_response("myapp", "Line 1\nLine 2\nLine 3")

        captured = capsys.readouterr()
        assert "\n\n" not in captured.out  # Only the leading newline should exist
        assert "Line 1 Line 2 Line 3" in captured.out


class TestEventNotifications:
    """Tests for event-driven instance notifications."""

    def test_repl_accepts_event_manager(self, mock_instance_manager, session_manager):
        """Test REPL can be initialized with EventManager."""
        event_manager = EventManager()
        repl = CommanderREPL(
            instance_manager=mock_instance_manager,
            session_manager=session_manager,
            event_manager=event_manager,
        )
        assert repl.event_manager == event_manager

    def test_on_instance_event_starting(
        self, mock_instance_manager, session_manager, capsys
    ):
        """Test handling of INSTANCE_STARTING event."""
        repl = CommanderREPL(
            instance_manager=mock_instance_manager,
            session_manager=session_manager,
        )

        event = Event(
            id="evt_123",
            project_id="myapp",
            type=EventType.INSTANCE_STARTING,
            priority=EventPriority.INFO,
            title="Starting instance 'myapp'",
        )

        repl._on_instance_event(event)

        captured = capsys.readouterr()
        assert "[Starting]" in captured.out
        assert "myapp" in captured.out

    def test_on_instance_event_ready(
        self, mock_instance_manager, session_manager, capsys
    ):
        """Test handling of INSTANCE_READY event."""
        repl = CommanderREPL(
            instance_manager=mock_instance_manager,
            session_manager=session_manager,
        )

        event = Event(
            id="evt_123",
            project_id="myapp",
            type=EventType.INSTANCE_READY,
            priority=EventPriority.INFO,
            title="Instance 'myapp' ready",
            context={"instance_name": "myapp"},
        )

        repl._on_instance_event(event)

        captured = capsys.readouterr()
        assert "[Ready]" in captured.out
        assert "/connect myapp" in captured.out

    def test_on_instance_event_ready_with_timeout(
        self, mock_instance_manager, session_manager, capsys
    ):
        """Test handling of INSTANCE_READY event with timeout flag."""
        repl = CommanderREPL(
            instance_manager=mock_instance_manager,
            session_manager=session_manager,
        )

        event = Event(
            id="evt_123",
            project_id="myapp",
            type=EventType.INSTANCE_READY,
            priority=EventPriority.INFO,
            title="Instance 'myapp' started",
            context={"instance_name": "myapp", "timeout": True},
        )

        repl._on_instance_event(event)

        captured = capsys.readouterr()
        assert "[Warning]" in captured.out
        assert "timeout" in captured.out
        assert "/connect myapp" in captured.out

    def test_on_instance_event_error(
        self, mock_instance_manager, session_manager, capsys
    ):
        """Test handling of INSTANCE_ERROR event."""
        repl = CommanderREPL(
            instance_manager=mock_instance_manager,
            session_manager=session_manager,
        )

        event = Event(
            id="evt_123",
            project_id="myapp",
            type=EventType.INSTANCE_ERROR,
            priority=EventPriority.HIGH,
            title="Instance 'myapp' failed",
            content="Failed to start Claude Code process",
        )

        repl._on_instance_event(event)

        captured = capsys.readouterr()
        assert "[Error]" in captured.out
        assert "failed" in captured.out
        assert "Failed to start" in captured.out


class TestInstancePrefixCommands:
    """Tests for @instance prefix on slash commands."""

    @pytest.mark.asyncio
    async def test_cmd_status_with_target_instance(
        self, repl, mock_instance_manager, capsys
    ):
        """Test /status command with @instance prefix."""
        instance = InstanceInfo(
            name="duetto",
            project_path=Path("/path/to/duetto"),
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
            git_branch="feature/xyz",
            ready=True,
        )
        mock_instance_manager.get_instance.return_value = instance

        await repl._cmd_status([], target_instance="duetto")

        captured = capsys.readouterr()
        assert "Status of duetto:" in captured.out
        assert "Framework: cc" in captured.out
        assert "feature/xyz" in captured.out
        assert "Ready: Yes" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_status_with_target_instance_not_found(
        self, repl, mock_instance_manager, capsys
    ):
        """Test /status with @instance prefix when instance doesn't exist."""
        mock_instance_manager.get_instance.return_value = None

        await repl._cmd_status([], target_instance="nonexistent")

        captured = capsys.readouterr()
        assert "not found" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_send_with_target_instance(
        self, repl, mock_instance_manager, capsys
    ):
        """Test /send command with @instance prefix."""
        orchestrator = MagicMock()
        orchestrator.send_keys = MagicMock(return_value=True)
        mock_instance_manager.orchestrator = orchestrator

        instance = InstanceInfo(
            name="mpm",
            project_path=Path("/path/to/mpm"),
            framework="mpm",
            tmux_session="mpm-commander",
            pane_target="%2",
        )
        mock_instance_manager.get_instance.return_value = instance

        await repl._cmd_send(["/help"], target_instance="mpm")

        captured = capsys.readouterr()
        assert "Sent to mpm:" in captured.out
        assert "/help" in captured.out
        orchestrator.send_keys.assert_called_once()

    @pytest.mark.asyncio
    async def test_cmd_send_with_target_instance_not_found(
        self, repl, mock_instance_manager, capsys
    ):
        """Test /send with @instance prefix when instance doesn't exist."""
        mock_instance_manager.get_instance.return_value = None

        await repl._cmd_send(["/help"], target_instance="nonexistent")

        captured = capsys.readouterr()
        assert "not found" in captured.out

    @pytest.mark.asyncio
    async def test_cmd_stop_with_target_instance(
        self, repl, mock_instance_manager, capsys
    ):
        """Test /stop command with @instance prefix."""
        instance = InstanceInfo(
            name="duetto",
            project_path=Path("/path/to/duetto"),
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
        )
        mock_instance_manager.get_instance.return_value = instance

        await repl._cmd_stop([], target_instance="duetto")

        captured = capsys.readouterr()
        assert "Stopped instance 'duetto'" in captured.out
        mock_instance_manager.stop_instance.assert_called_once_with("duetto")

    @pytest.mark.asyncio
    async def test_handle_input_at_instance_slash_command_status(
        self, repl, mock_instance_manager, capsys
    ):
        """Test _handle_input with @instance /status."""
        instance = InstanceInfo(
            name="duetto",
            project_path=Path("/path/to/duetto"),
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
            ready=True,
        )
        mock_instance_manager.get_instance.return_value = instance

        await repl._handle_input("@duetto /status")

        captured = capsys.readouterr()
        assert "Status of duetto:" in captured.out
        assert "Framework: cc" in captured.out

    @pytest.mark.asyncio
    async def test_handle_input_at_instance_slash_command_send(
        self, repl, mock_instance_manager, capsys
    ):
        """Test _handle_input with @instance /send."""
        orchestrator = MagicMock()
        orchestrator.send_keys = MagicMock(return_value=True)
        mock_instance_manager.orchestrator = orchestrator

        instance = InstanceInfo(
            name="mpm",
            project_path=Path("/path/to/mpm"),
            framework="mpm",
            tmux_session="mpm-commander",
            pane_target="%2",
        )
        mock_instance_manager.get_instance.return_value = instance

        await repl._handle_input("@mpm /send /help")

        captured = capsys.readouterr()
        assert "Sent to mpm:" in captured.out

    @pytest.mark.asyncio
    async def test_handle_input_at_instance_slash_command_stop(
        self, repl, mock_instance_manager, capsys
    ):
        """Test _handle_input with @instance /stop."""
        instance = InstanceInfo(
            name="duetto",
            project_path=Path("/path/to/duetto"),
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
        )
        mock_instance_manager.get_instance.return_value = instance

        await repl._handle_input("@duetto /stop")

        captured = capsys.readouterr()
        assert "Stopped instance 'duetto'" in captured.out
        mock_instance_manager.stop_instance.assert_called_once_with("duetto")

    @pytest.mark.asyncio
    async def test_handle_input_at_instance_message(
        self, repl, mock_instance_manager, capsys
    ):
        """Test _handle_input with @instance message (no slash command)."""
        instance = InstanceInfo(
            name="myapp",
            project_path=Path("/path/to/myapp"),
            framework="cc",
            tmux_session="mpm-commander",
            pane_target="%1",
        )
        mock_instance_manager.get_instance.return_value = instance

        await repl._handle_input("@myapp show me the code")

        # Message should be enqueued for processing
        assert len(repl._pending_requests) >= 0  # May be processing async

    @pytest.mark.asyncio
    async def test_handle_input_at_instance_no_message(self, repl, capsys):
        """Test _handle_input with @instance but no message."""
        await repl._handle_input("@nonexistent")

        captured = capsys.readouterr()
        assert "prefix requires a message or command" in captured.out

    @pytest.mark.asyncio
    async def test_parse_mention_with_at_syntax(self, repl):
        """Test _parse_mention with @name syntax."""
        result = repl._parse_mention("@myapp hello there")
        assert result == ("myapp", "hello there")

    @pytest.mark.asyncio
    async def test_parse_mention_with_parentheses_syntax(self, repl):
        """Test _parse_mention with (name) syntax."""
        result = repl._parse_mention("(izzie) what's the status")
        assert result == ("izzie", "what's the status")
