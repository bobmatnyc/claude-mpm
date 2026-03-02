"""
Global pytest configuration and fixtures for all tests.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import yaml

# ===== Configuration Fixtures =====


@pytest.fixture
def mock_config():
    """Common configuration fixture with sensible defaults."""
    config = Mock()
    config.get.return_value = {
        "version": "1.0.0",
        "services": {
            "socketio": {"port": 8765},
            "hook": {"port": 8080},
        },
        "paths": {
            "agents": ".claude/agents",
            "memory": ".claude/memory",
            "logs": ".claude/logs",
        },
        "features": {
            "auto_restart": True,
            "memory_enabled": True,
        },
    }
    config.return_value.get = config.get
    return config


@pytest.fixture
def config_file(tmp_path):
    """Create a temporary config file."""
    config_path = tmp_path / "config.yml"
    config_data = {
        "version": "1.0.0",
        "services": {
            "socketio": {"port": 8765},
        },
    }
    config_path.write_text(yaml.dump(config_data))
    return config_path


# ===== Service Registry Fixtures =====


@pytest.fixture
def mock_service_registry():
    """Common service registry fixture."""
    registry = Mock()

    # Create mock services
    mock_memory_service = Mock()
    mock_memory_service.get_agent_memory.return_value = {}
    mock_memory_service.update_agent_memory.return_value = True

    mock_agent_service = Mock()
    mock_agent_service.list_agents.return_value = []
    mock_agent_service.deploy_agent.return_value = True

    # Setup service registry returns
    def get_service(name):
        services = {
            "memory": mock_memory_service,
            "agent": mock_agent_service,
            "socketio": Mock(),
            "hook": Mock(),
        }
        return services.get(name, Mock())

    registry.get_service = get_service
    return registry


# ===== Path and Directory Fixtures =====


@pytest.fixture
def temp_agent_dir(tmp_path):
    """Create a temporary agent directory structure."""
    agent_dir = tmp_path / ".claude" / "agents"
    agent_dir.mkdir(parents=True, exist_ok=True)

    # Create some default agent files
    (agent_dir / "researcher.yml").write_text(
        yaml.dump(
            {
                "name": "researcher",
                "description": "Research agent",
                "capabilities": ["research", "analysis"],
            }
        )
    )

    return agent_dir


@pytest.fixture
def temp_memory_dir(tmp_path):
    """Create a temporary memory directory structure."""
    memory_dir = tmp_path / ".claude" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    # Create default memory structure
    (memory_dir / "index.json").write_text(
        json.dumps({"agents": {}, "global": {}, "version": "1.0.0"})
    )

    return memory_dir


@pytest.fixture
def project_root(tmp_path):
    """Create a temporary project root with standard structure."""
    # Create standard directories
    (tmp_path / "src" / "claude_mpm").mkdir(parents=True)
    (tmp_path / "tests").mkdir(parents=True)
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / ".claude" / "agents").mkdir(parents=True)

    # Create basic files
    (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "claude-mpm"')
    (tmp_path / "VERSION").write_text("1.0.0")

    return tmp_path


# ===== Agent Safety Fixtures =====


@pytest.fixture(autouse=True)
def verify_agents_untouched():
    """Detect any test that modifies the real .claude/agents/ directory.

    Guards against regressions where production code resolves paths via
    Path.cwd() instead of an explicit project_path argument, causing tests
    to operate on live deployed agent files.

    Checks both agents/ (for removals) and agents/unused/ (for archives),
    since the damage path is shutil.move() from agents/ to agents/unused/.
    """
    agents_dir = Path.cwd() / ".claude" / "agents"
    unused_dir = agents_dir / "unused"

    def _snapshot(directory: Path) -> set:
        if not directory.exists():
            return set()
        return {f.name for f in directory.glob("*.md")}

    before_agents = _snapshot(agents_dir)
    before_unused = _snapshot(unused_dir)

    yield

    after_agents = _snapshot(agents_dir)
    after_unused = _snapshot(unused_dir)

    removed = before_agents - after_agents
    added_to_unused = after_unused - before_unused

    problems = []
    if removed:
        problems.append(f"agents removed from .claude/agents/: {sorted(removed)}")
    if added_to_unused:
        problems.append(
            f"agents archived to .claude/agents/unused/: {sorted(added_to_unused)}"
        )

    assert not problems, (
        "TEST BUG: Real deployed agents were modified during test.\n"
        + "\n".join(f"  - {p}" for p in problems)
    )


@pytest.fixture(autouse=True)
def verify_source_agents_untouched():
    """Detect any test that modifies source agent files in the package.

    Guards against tests that write back to src/claude_mpm/agents/ source
    files (e.g. via save_output_style()). Under parallel execution
    (pytest -n auto), concurrent write_text() calls can truncate these
    files to 0 bytes due to the open(mode='w') truncation window.

    Checks both file existence AND content checksums to catch truncation.
    """
    import hashlib

    source_agents_dir = Path.cwd() / "src" / "claude_mpm" / "agents"

    def _content_snapshot(directory: Path) -> dict:
        if not directory.exists():
            return {}
        result = {}
        for f in directory.glob("*.md"):
            content = f.read_bytes()
            result[f.name] = {
                "size": len(content),
                "hash": hashlib.md5(content).hexdigest(),
            }
        return result

    before = _content_snapshot(source_agents_dir)

    yield

    after = _content_snapshot(source_agents_dir)

    problems = []
    for name, before_info in before.items():
        after_info = after.get(name)
        if after_info is None:
            problems.append(f"source file DELETED: {name}")
        elif after_info["size"] == 0 and before_info["size"] > 0:
            problems.append(
                f"source file EMPTIED: {name} "
                f"(was {before_info['size']} bytes, now 0 bytes)"
            )
        elif after_info["hash"] != before_info["hash"]:
            problems.append(
                f"source file MODIFIED: {name} "
                f"(size {before_info['size']} -> {after_info['size']})"
            )

    assert not problems, (
        "TEST BUG: Source agent files in src/claude_mpm/agents/ were modified.\n"
        + "\n".join(f"  - {p}" for p in problems)
    )


# ===== Mock Objects Fixtures =====


@pytest.fixture
def mock_agent():
    """Create a mock agent with standard properties."""
    agent = Mock()
    agent.name = "test_agent"
    agent.description = "Test agent for testing"
    agent.capabilities = ["test", "mock"]
    agent.is_deployed = True
    agent.path = Path(".claude/agents/test_agent.yml")
    return agent


@pytest.fixture
def mock_memory_manager():
    """Create a mock memory manager."""
    manager = Mock()
    manager.get_agent_memory.return_value = {
        "learnings": [],
        "context": {},
        "patterns": [],
    }
    manager.update_agent_memory.return_value = True
    manager.add_learning.return_value = True
    manager.search_memories.return_value = []
    return manager


@pytest.fixture
def mock_session():
    """Create a mock session object."""
    session = Mock()
    session.id = "test-session-123"
    session.pid = 12345
    session.status = "running"
    session.start_time = "2024-01-01T00:00:00"
    session.config = {}
    return session


# ===== Async Fixtures =====


@pytest.fixture
def mock_async_client():
    """Create a mock async client."""
    client = AsyncMock()
    client.connect = AsyncMock(return_value=True)
    client.disconnect = AsyncMock(return_value=True)
    client.send = AsyncMock(return_value=True)
    client.receive = AsyncMock(return_value={"type": "message", "data": {}})
    return client


@pytest.fixture
async def async_service():
    """Create a mock async service."""
    service = AsyncMock()
    service.start = AsyncMock(return_value=True)
    service.stop = AsyncMock(return_value=True)
    service.is_running = AsyncMock(return_value=True)
    yield service
    # Cleanup if needed
    if hasattr(service, "cleanup"):
        await service.cleanup()


# ===== CLI Command Fixtures =====


@pytest.fixture
def mock_argparse_namespace():
    """Create a mock argparse namespace with common attributes."""
    args = Mock()
    args.verbose = False
    args.quiet = False
    args.config = None
    args.output = "text"
    args.force = False
    return args


@pytest.fixture
def cli_runner():
    """Create a CLI test runner."""
    from click.testing import CliRunner

    return CliRunner()


# ===== File Content Fixtures =====


@pytest.fixture
def sample_yaml_content():
    """Sample YAML content for testing."""
    return """
name: test_agent
description: A test agent
version: 1.0.0
capabilities:
  - research
  - analysis
  - documentation
"""


@pytest.fixture
def sample_json_content():
    """Sample JSON content for testing."""
    return json.dumps(
        {
            "name": "test",
            "version": "1.0.0",
            "data": {"key1": "value1", "key2": ["item1", "item2"]},
        },
        indent=2,
    )


# ===== Socket.IO Fixtures =====


@pytest.fixture
def mock_socketio_server():
    """Create a mock Socket.IO server."""
    server = Mock()
    server.emit = Mock(return_value=True)
    server.send = Mock(return_value=True)
    server.on = Mock()
    server.disconnect = Mock()
    server.clients = []
    return server


@pytest.fixture
def mock_socketio_client():
    """Create a mock Socket.IO client."""
    client = Mock()
    client.sid = "test-client-123"
    client.connected = True
    client.emit = Mock()
    client.disconnect = Mock()
    return client


# ===== Environment Fixtures =====


@pytest.fixture
def clean_env(monkeypatch):
    """Provide a clean environment without Claude MPM variables."""
    env_vars_to_remove = [
        "CLAUDE_MPM_CONFIG",
        "CLAUDE_MPM_DEBUG",
        "CLAUDE_MPM_LOG_LEVEL",
        "CLAUDE_MPM_AGENT_DIR",
    ]
    for var in env_vars_to_remove:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


@pytest.fixture
def test_env(monkeypatch, tmp_path):
    """Setup test environment variables."""
    monkeypatch.setenv("CLAUDE_MPM_CONFIG", str(tmp_path / "config.yml"))
    monkeypatch.setenv("CLAUDE_MPM_AGENT_DIR", str(tmp_path / ".claude" / "agents"))
    monkeypatch.setenv("CLAUDE_MPM_DEBUG", "true")
    return monkeypatch


# ===== Process and System Fixtures =====


@pytest.fixture
def mock_process():
    """Create a mock process object."""
    process = Mock()
    process.pid = 12345
    process.name.return_value = "claude-mpm"
    process.status.return_value = "running"
    process.create_time.return_value = 1234567890.0
    process.terminate = Mock()
    process.kill = Mock()
    return process


@pytest.fixture
def mock_subprocess():
    """Mock subprocess module."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")
        yield mock_run


# ===== Logging Fixtures =====


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    return logger


# ===== Event Loop Configuration =====


@pytest.fixture(scope="function")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ===== Pytest Configuration =====


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line(
        "markers", "requires_network: mark test as requiring network access"
    )
    config.addinivalue_line(
        "markers", "regression: mark test as a regression/characterization test"
    )


# ===== Helper Functions =====


def create_mock_file(path: Path, content: str = "") -> Path:
    """Helper to create a mock file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def create_mock_agent_file(agent_dir: Path, name: str, **kwargs) -> Path:
    """Helper to create a mock agent file."""
    agent_data = {
        "name": name,
        "description": kwargs.get("description", f"{name} agent"),
        "version": kwargs.get("version", "1.0.0"),
        "capabilities": kwargs.get("capabilities", []),
    }
    agent_path = agent_dir / f"{name}.yml"
    agent_path.write_text(yaml.dump(agent_data))
    return agent_path


# ===== Scope-Aware Deployment Fixtures =====


@pytest.fixture
def project_scope_dirs(tmp_path):
    """Standard PROJECT scope directory structure.

    Mimics: {project}/.claude/agents/, {project}/.claude/skills/,
            {project}/.claude-mpm/
    """
    project = tmp_path / "my_project"
    dirs = {
        "root": project,
        "agents": project / ".claude" / "agents",
        "skills": project / ".claude" / "skills",
        "archive": project / ".claude" / "agents" / "unused",
        "config": project / ".claude-mpm",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


@pytest.fixture
def user_scope_dirs(tmp_path):
    """Standard USER scope directory structure (mocked home).

    Patches Path.home() to tmp_path/home so tests don't touch the real
    ~/.claude directory.

    Returns: (dirs_dict, fake_home_path)
    """
    fake_home = tmp_path / "home"
    dirs = {
        "home": fake_home,
        "agents": fake_home / ".claude" / "agents",
        "skills": fake_home / ".claude" / "skills",
        "archive": fake_home / ".claude" / "agents" / "unused",
        "config": fake_home / ".claude-mpm",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs, fake_home


@pytest.fixture
def both_scopes(project_scope_dirs, user_scope_dirs):
    """Provides both scope directory structures for cross-scope isolation tests."""
    user_dirs, fake_home = user_scope_dirs
    return {
        "project": project_scope_dirs,
        "user": user_dirs,
        "fake_home": fake_home,
    }
