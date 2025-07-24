"""Tests for agent registry integration."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from claude_mpm.core.agent_registry import AgentRegistryAdapter


class TestAgentRegistryAdapter:
    """Test the AgentRegistryAdapter class."""
    
    def test_init_without_framework(self, tmp_path):
        """Test initialization when framework not found."""
        with patch.object(AgentRegistryAdapter, '_find_framework', return_value=None):
            adapter = AgentRegistryAdapter()
            assert adapter.framework_path is None
            assert adapter.registry is None
    
    def test_find_framework(self, tmp_path, monkeypatch):
        """Test framework detection."""
        # Create mock framework
        framework_dir = tmp_path / "claude-multiagent-pm"
        framework_dir.mkdir()
        (framework_dir / "claude_pm").mkdir()
        (framework_dir / "claude_pm" / "__init__.py").touch()
        
        # Mock home to tmp_path
        mock_home = tmp_path
        monkeypatch.setattr(Path, "home", lambda: mock_home)
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        
        adapter = AgentRegistryAdapter()
        assert adapter.framework_path == framework_dir
    
    @patch('sys.path', new_list=[])
    def test_initialize_registry_success(self, tmp_path):
        """Test successful registry initialization."""
        # Create mock framework
        framework_dir = tmp_path / "framework"
        framework_dir.mkdir()
        (framework_dir / "claude_pm").mkdir()
        (framework_dir / "claude_pm" / "__init__.py").touch()
        
        # Mock the import
        mock_registry_class = Mock()
        mock_registry_instance = Mock()
        mock_registry_class.return_value = mock_registry_instance
        
        with patch.dict('sys.modules', {'claude_pm.core.agent_registry': Mock(AgentRegistry=mock_registry_class)}):
            adapter = AgentRegistryAdapter(framework_path=framework_dir)
            assert adapter.registry is not None
            mock_registry_class.assert_called_once()
    
    def test_list_agents_no_registry(self):
        """Test list_agents when no registry available."""
        adapter = AgentRegistryAdapter()
        adapter.registry = None
        
        result = adapter.list_agents()
        assert result == {}
    
    def test_list_agents_with_registry(self):
        """Test list_agents with registry."""
        adapter = AgentRegistryAdapter()
        
        # Mock registry
        mock_registry = Mock()
        mock_agents = {
            'engineer': {'type': 'engineer', 'path': '/path/to/engineer.md'},
            'qa': {'type': 'qa', 'path': '/path/to/qa.md'}
        }
        mock_registry.listAgents.return_value = mock_agents
        adapter.registry = mock_registry
        
        result = adapter.list_agents()
        assert result == mock_agents
        mock_registry.listAgents.assert_called_once()
    
    def test_get_agent_definition(self, tmp_path):
        """Test getting agent definition."""
        adapter = AgentRegistryAdapter()
        
        # Create mock agent file
        agent_file = tmp_path / "engineer.md"
        agent_file.write_text("# Engineer Agent\nImplements code")
        
        # Mock registry
        mock_registry = Mock()
        mock_registry.listAgents.return_value = {
            'engineer': {'type': 'engineer', 'path': str(agent_file)}
        }
        adapter.registry = mock_registry
        
        result = adapter.get_agent_definition('engineer')
        assert result is not None
        assert "Engineer Agent" in result
        assert "Implements code" in result
    
    def test_select_agent_for_task(self):
        """Test selecting agent for task."""
        adapter = AgentRegistryAdapter()
        
        # Mock registry
        mock_registry = Mock()
        mock_registry.listAgents.return_value = {
            'engineer': {'type': 'engineer', 'specializations': ['coding']},
            'qa': {'type': 'qa', 'specializations': ['testing']}
        }
        adapter.registry = mock_registry
        
        result = adapter.select_agent_for_task("implement new feature", ['coding'])
        assert result is not None
        assert result['id'] == 'engineer'
    
    def test_get_agent_hierarchy(self):
        """Test getting agent hierarchy."""
        adapter = AgentRegistryAdapter()
        
        # Mock registry
        mock_registry = Mock()
        mock_registry.listAgents.return_value = {
            'project-engineer': {'path': '/project/.claude-pm/agents/project-specific/engineer.md'},
            'user-qa': {'path': '/home/user/.claude-pm/agents/user-agents/qa.md'},
            'system-researcher': {'path': '/framework/claude_pm/agents/researcher.md'}
        }
        adapter.registry = mock_registry
        
        hierarchy = adapter.get_agent_hierarchy()
        assert 'project-engineer' in hierarchy['project']
        assert 'user-qa' in hierarchy['user']
        assert 'system-researcher' in hierarchy['system']
    
    def test_get_core_agents(self):
        """Test getting core agents list."""
        adapter = AgentRegistryAdapter()
        core_agents = adapter.get_core_agents()
        
        assert 'documentation' in core_agents
        assert 'engineer' in core_agents
        assert 'qa' in core_agents
        assert 'research' in core_agents
        assert len(core_agents) == 8
    
    def test_format_agent_for_task_tool(self):
        """Test formatting agent delegation."""
        adapter = AgentRegistryAdapter()
        
        result = adapter.format_agent_for_task_tool(
            'engineer',
            'Implement user authentication',
            'Use JWT tokens'
        )
        
        assert '**Engineer**:' in result
        assert 'Implement user authentication' in result
        assert 'Use JWT tokens' in result
        assert 'TEMPORAL CONTEXT' in result
        assert 'Authority' in result