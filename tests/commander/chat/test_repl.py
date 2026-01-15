"""Tests for CommanderREPL."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from claude_mpm.commander.chat.repl import CommanderREPL
from claude_mpm.commander.frameworks.base import InstanceInfo
from claude_mpm.commander.instance_manager import InstanceManager
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
    assert "Commander Commands:" in captured.out
    assert "list" in captured.out
    assert "start" in captured.out


@pytest.mark.asyncio
async def test_cmd_exit(repl):
    """Test exit command."""
    repl._running = True

    await repl._cmd_exit([])

    assert not repl._running


@pytest.mark.asyncio
async def test_send_to_instance_not_connected(repl, capsys):
    """Test sending message when not connected."""
    await repl._send_to_instance("Hello")

    captured = capsys.readouterr()
    assert "Not connected" in captured.out


@pytest.mark.asyncio
async def test_send_to_instance_instance_gone(repl, session_manager, capsys):
    """Test sending message when instance no longer exists."""
    session_manager.connect_to("myapp")

    await repl._send_to_instance("Hello")

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
    """Test prompt when connected to instance."""
    session_manager.connect_to("myapp")

    prompt = repl._get_prompt()

    assert "myapp" in prompt
    assert "Commander" in prompt


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
