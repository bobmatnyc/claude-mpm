"""Tests for agent registry integration."""

from pathlib import Path
from unittest.mock import Mock, patch

from claude_mpm.core.agent_registry import AgentRegistryAdapter


class TestAgentRegistryAdapter:
    """Test the AgentRegistryAdapter class."""

    def test_init_without_framework(self):
        """Test initialization when framework not found."""
        with patch.object(AgentRegistryAdapter, "_find_framework", return_value=None):
            adapter = AgentRegistryAdapter()
            assert adapter.framework_path is None
            assert adapter.registry is None

    def test_find_framework(self, monkeypatch):
        """Test framework detection."""
        # Create mock framework with correct structure
        framework_dir = self / "Projects" / "claude-mpm"
        framework_dir.mkdir(parents=True)
        agents_dir = framework_dir / "src" / "claude_mpm" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "test_agent.md").touch()

        # Mock home to tmp_path
        mock_home = self
        monkeypatch.setattr(Path, "home", lambda: mock_home)
        monkeypatch.setattr(Path, "cwd", lambda: self)

        # Mock __file__ to avoid detecting current framework
        monkeypatch.setattr(
            "claude_mpm.core.agent_registry.__file__", str(self / "dummy.py")
        )

        adapter = AgentRegistryAdapter()
        assert adapter.framework_path == framework_dir

    def test_initialize_registry_success(self):
        """Test successful registry initialization."""
        # Create mock framework with correct structure
        framework_dir = self / "framework"
        framework_dir.mkdir()
        agents_dir = framework_dir / "src" / "claude_mpm" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "test_agent.md").touch()

        # Create adapter with framework path
        adapter = AgentRegistryAdapter(framework_path=framework_dir)

        # Registry initialization is now internal to framework loader
        # Just verify the adapter was created successfully
        assert adapter.framework_path == framework_dir

    def test_list_agents_no_registry():
        """Test list_agents when no registry available."""
        adapter = AgentRegistryAdapter()
        adapter.registry = None

        result = adapter.list_agents()
        assert result == {}

    def test_list_agents_with_registry():
        """Test list_agents with registry."""
        adapter = AgentRegistryAdapter()

        # Mock registry
        mock_registry = Mock()
        mock_agents = {
            "engineer": {"type": "engineer", "path": "/path/to/engineer.md"},
            "qa": {"type": "qa", "path": "/path/to/qa.md"},
        }
        mock_registry.list_agents.return_value = mock_agents
        adapter.registry = mock_registry

        result = adapter.list_agents()
        assert result == mock_agents
        mock_registry.list_agents.assert_called_once()

    def test_get_agent_definition(self):
        """Test getting agent definition."""
        adapter = AgentRegistryAdapter()

        # Create mock agent file
        agent_file = self / "engineer.md"
        agent_file.write_text("# Engineer Agent\nImplements code")

        # Mock registry
        mock_registry = Mock()
        mock_registry.list_agents.return_value = {
            "engineer": {"type": "engineer", "path": str(agent_file)}
        }
        adapter.registry = mock_registry

        result = adapter.get_agent_definition("engineer")
        assert result is not None
        assert "Engineer Agent" in result
        assert "Implements code" in result

    def test_select_agent_for_task():
        """Test selecting agent for task."""
        adapter = AgentRegistryAdapter()

        # Mock registry
        mock_registry = Mock()
        mock_registry.list_agents.return_value = {
            "engineer": {"type": "engineer", "specializations": ["coding"]},
            "qa": {"type": "qa", "specializations": ["testing"]},
        }
        adapter.registry = mock_registry

        result = adapter.select_agent_for_task("implement new feature", ["coding"])
        assert result is not None
        assert result["id"] == "engineer"

    def test_get_agent_hierarchy():
        """Test getting agent hierarchy."""
        adapter = AgentRegistryAdapter()

        # The adapter now uses framework_loader internally
        # which returns a different hierarchy structure
        hierarchy = adapter.get_agent_hierarchy()

        # Should return hierarchy with project/user/system keys
        assert isinstance(hierarchy, dict)
        assert "system" in hierarchy
        assert isinstance(hierarchy["system"], list)

    def test_get_core_agents():
        """Test getting core agents list."""
        adapter = AgentRegistryAdapter()
        core_agents = adapter.get_core_agents()

        assert "documentation" in core_agents
        assert "engineer" in core_agents
        assert "qa" in core_agents
        assert "research" in core_agents
        assert len(core_agents) == 8

    def test_format_agent_for_task_tool():
        """Test formatting agent delegation."""
        adapter = AgentRegistryAdapter()

        result = adapter.format_agent_for_task_tool(
            "engineer", "Implement user authentication", "Use JWT tokens"
        )

        assert "**Engineer**:" in result
        assert "Implement user authentication" in result
        assert "Use JWT tokens" in result
        assert "TEMPORAL CONTEXT" in result
        assert "Authority" in result
