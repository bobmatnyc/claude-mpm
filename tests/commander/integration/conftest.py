"""Pytest fixtures for Commander integration tests."""

import asyncio
import shutil
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_mpm.commander.config import DaemonConfig
from claude_mpm.commander.daemon import CommanderDaemon
from claude_mpm.commander.models import Project


@pytest.fixture
def integration_tmp_path(tmp_path: Path) -> Generator[Path, None, None]:
    """Create isolated temporary directory for integration tests.

    Args:
        tmp_path: Pytest temporary directory

    Yields:
        Temporary path for test state

    Cleanup:
        Removes all test artifacts after test completion
    """
    test_dir = tmp_path / "integration_test"
    test_dir.mkdir(parents=True, exist_ok=True)

    yield test_dir

    # Cleanup
    if test_dir.exists():
        shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def integration_config(integration_tmp_path: Path) -> DaemonConfig:
    """Create daemon configuration for integration tests.

    Args:
        integration_tmp_path: Isolated test directory

    Returns:
        DaemonConfig with test-friendly settings
    """
    return DaemonConfig(
        host="127.0.0.1",
        port=18765,  # Test port to avoid conflicts
        log_level="DEBUG",
        state_dir=integration_tmp_path / "state",
        max_projects=5,
        healthcheck_interval=60,
        save_interval=5,  # Frequent saves for testing recovery
        poll_interval=0.1,  # Fast polling for responsive tests
    )


@pytest.fixture
def mock_tmux_orchestrator() -> MagicMock:
    """Create mock TmuxOrchestrator for integration tests.

    Mocks tmux interactions to avoid requiring actual tmux session.

    Returns:
        Mocked TmuxOrchestrator with basic behaviors
    """
    mock = MagicMock()
    mock.session_exists.return_value = False
    mock.create_session.return_value = None
    mock.kill_session.return_value = None
    mock.send_keys = MagicMock()
    mock.capture_pane.return_value = ""

    return mock


@pytest.fixture
def mock_runtime_executor() -> MagicMock:
    """Create mock RuntimeExecutor for integration tests.

    Returns:
        Mocked RuntimeExecutor
    """
    mock = MagicMock()
    mock.spawn = AsyncMock(return_value="test:pane.0")
    mock.stop = AsyncMock()

    return mock


@pytest.fixture
async def daemon_lifecycle(
    integration_config: DaemonConfig,
) -> AsyncGenerator[CommanderDaemon, None]:
    """Create and manage daemon lifecycle for integration tests.

    Provides a daemon instance with mocked external dependencies,
    handles startup and cleanup automatically.

    Args:
        integration_config: Test daemon configuration

    Yields:
        Running CommanderDaemon instance

    Cleanup:
        Ensures daemon is stopped after test completion
    """
    with patch("claude_mpm.commander.daemon.TmuxOrchestrator") as mock_tmux_cls, patch(
        "claude_mpm.commander.daemon.uvicorn.Server"
    ) as mock_server_cls:
        # Configure mock tmux
        mock_tmux = MagicMock()
        mock_tmux.session_exists.return_value = False
        mock_tmux.create_session.return_value = None
        mock_tmux_cls.return_value = mock_tmux

        # Configure mock server
        mock_server = MagicMock()
        mock_server.serve = AsyncMock()
        mock_server_cls.return_value = mock_server

        # Create daemon
        daemon = CommanderDaemon(integration_config)

        # Start daemon
        await daemon.start()

        # Let daemon initialize
        await asyncio.sleep(0.1)

        try:
            yield daemon
        finally:
            # Cleanup: stop daemon
            if daemon.is_running:
                await daemon.stop()

            # Give time for cleanup to complete
            await asyncio.sleep(0.1)


@pytest.fixture
def sample_project(integration_tmp_path: Path) -> Project:
    """Create a sample project for integration tests.

    Args:
        integration_tmp_path: Test directory

    Returns:
        Sample Project instance
    """
    project_path = integration_tmp_path / "sample_project"
    project_path.mkdir(parents=True, exist_ok=True)

    from claude_mpm.commander.registry import ProjectRegistry

    registry = ProjectRegistry()

    return registry.register(str(project_path), "Sample Test Project")


@pytest.fixture
def multiple_projects(integration_tmp_path: Path) -> list[Project]:
    """Create multiple sample projects for integration tests.

    Args:
        integration_tmp_path: Test directory

    Returns:
        List of 3 sample Project instances
    """
    from claude_mpm.commander.registry import ProjectRegistry

    registry = ProjectRegistry()

    projects = []
    for i in range(3):
        project_path = integration_tmp_path / f"project_{i}"
        project_path.mkdir(parents=True, exist_ok=True)

        project = registry.register(str(project_path), f"Test Project {i}")
        projects.append(project)

    return projects
