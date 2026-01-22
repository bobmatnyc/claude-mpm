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
    await repl._cmd_list([])

    captured = capsys.readouterr()
    assert "No active instances" in captured.out


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

    await repl._cmd_list([])

    captured = capsys.readouterr()
    assert "Active instances" in captured.out
    assert "app1" in captured.out
    assert "app2" in captured.out
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
async def test_cmd_exit(repl):
    """Test exit command."""
    repl._running = True

    await repl._cmd_exit([])

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
        repl.llm = AsyncMock()
        repl.llm.chat = AsyncMock(return_value='{"intent": "list", "args": {}}')

        await repl._handle_input("show me all running instances")

        captured = capsys.readouterr()
        assert "No active instances" in captured.out

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
    """Test prompt when connected to ready instance."""
    session_manager.connect_to("myapp")
    repl._instance_ready["myapp"] = True  # Mark instance as ready

    prompt = repl._get_prompt()

    assert "myapp" in prompt
    assert "Commander" in prompt


def test_get_prompt_connected_not_ready(repl, session_manager):
    """Test prompt when connected but instance not ready yet."""
    session_manager.connect_to("myapp")
    # Don't mark instance as ready

    prompt = repl._get_prompt()

    # Should not show instance name until ready
    assert "myapp" not in prompt
    assert "Commander>" in prompt


def test_get_prompt_not_connected(repl):
    """Test prompt when not connected."""
    prompt = repl._get_prompt()

    assert "Commander>" in prompt
    assert "(" not in prompt  # No instance name


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
