"""Unit tests for DeployedAgentDiscovery service."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import logging

from claude_mpm.services.deployed_agent_discovery import DeployedAgentDiscovery


class TestDeployedAgentDiscovery:
    """Test cases for DeployedAgentDiscovery service."""
    
    @pytest.fixture
    def mock_agent_registry(self):
        """Create a mock agent registry."""
        with patch('claude_mpm.services.deployed_agent_discovery.AgentRegistryAdapter') as mock:
            yield mock
    
    @pytest.fixture
    def mock_path_resolver(self):
        """Create a mock path resolver."""
        with patch('claude_mpm.services.deployed_agent_discovery.PathResolver') as mock:
            mock.get_project_root.return_value = Path('/test/project')
            yield mock
    
    @pytest.fixture
    def discovery_service(self, mock_agent_registry, mock_path_resolver):
        """Create a DeployedAgentDiscovery instance with mocks."""
        return DeployedAgentDiscovery()
    
    def test_init_with_default_project_root(self, mock_path_resolver):
        """Test initialization with default project root."""
        service = DeployedAgentDiscovery()
        assert service.project_root == Path('/test/project')
        mock_path_resolver.get_project_root.assert_called_once()
    
    def test_init_with_custom_project_root(self, mock_agent_registry, mock_path_resolver):
        """Test initialization with custom project root."""
        custom_root = Path('/custom/root')
        service = DeployedAgentDiscovery(project_root=custom_root)
        assert service.project_root == custom_root
        mock_path_resolver.get_project_root.assert_not_called()
    
    def test_discover_deployed_agents_success(self, discovery_service):
        """Test successful agent discovery."""
        # Create mock agents with new schema
        mock_agent1 = Mock()
        mock_agent1.agent_id = 'research'
        mock_agent1.metadata.name = 'Research Agent'
        mock_agent1.metadata.description = 'Analyzes codebases'
        mock_agent1.metadata.specializations = ['analysis', 'patterns']
        mock_agent1.capabilities = {'when_to_use': ['codebase analysis', 'pattern detection']}
        mock_agent1.configuration.tools = ['grep', 'find']
        
        # Create mock agent with legacy format
        mock_agent2 = Mock(spec=['type', 'name', 'description', 'specializations', 'tools'])
        mock_agent2.type = 'engineer'
        mock_agent2.name = 'Engineer Agent'
        mock_agent2.description = 'Implements solutions'
        mock_agent2.specializations = ['coding', 'refactoring']
        mock_agent2.tools = ['edit', 'write']
        
        discovery_service.agent_registry.list_agents.return_value = [mock_agent1, mock_agent2]
        
        agents = discovery_service.discover_deployed_agents()
        
        assert len(agents) == 2
        
        # Verify first agent (new schema)
        assert agents[0]['id'] == 'research'
        assert agents[0]['name'] == 'Research Agent'
        assert agents[0]['description'] == 'Analyzes codebases'
        assert agents[0]['specializations'] == ['analysis', 'patterns']
        assert agents[0]['capabilities'] == {'when_to_use': ['codebase analysis', 'pattern detection']}
        assert agents[0]['tools'] == ['grep', 'find']
        
        # Verify second agent (legacy format)
        assert agents[1]['id'] == 'engineer'
        assert agents[1]['name'] == 'Engineer Agent'
        assert agents[1]['description'] == 'Implements solutions'
        assert agents[1]['specializations'] == ['coding', 'refactoring']
        assert agents[1]['tools'] == ['edit', 'write']
    
    def test_discover_deployed_agents_empty_list(self, discovery_service):
        """Test discovery with no agents."""
        discovery_service.agent_registry.list_agents.return_value = []
        
        agents = discovery_service.discover_deployed_agents()
        
        assert agents == []
    
    def test_discover_deployed_agents_with_error(self, discovery_service):
        """Test discovery handles registry errors gracefully."""
        discovery_service.agent_registry.list_agents.side_effect = Exception("Registry error")
        
        agents = discovery_service.discover_deployed_agents()
        
        # Should return empty list on failure
        assert agents == []
    
    def test_extract_agent_info_with_error(self, discovery_service):
        """Test extraction handles errors gracefully."""
        # Create an agent that will cause extraction to fail
        mock_agent = Mock()
        # Make metadata access raise an exception
        type(mock_agent).metadata = property(lambda self: (_ for _ in ()).throw(Exception("Extraction error")))
        
        result = discovery_service._extract_agent_info(mock_agent)
        
        assert result is None
    
    def test_determine_source_tier_with_explicit_tier(self, discovery_service):
        """Test source tier determination with explicit attribute."""
        mock_agent = Mock()
        mock_agent.source_tier = 'project'
        
        tier = discovery_service._determine_source_tier(mock_agent)
        
        assert tier == 'project'
    
    def test_determine_source_tier_from_path(self, discovery_service):
        """Test source tier determination from file path."""
        mock_agent = Mock()
        del mock_agent.source_tier  # No explicit tier
        
        # Test project tier detection
        mock_agent.source_path = '/test/project/.claude/agents/custom.json'
        assert discovery_service._determine_source_tier(mock_agent) == 'project'
        
        # Test user tier detection
        mock_agent.source_path = f'{Path.home()}/agents/custom.json'
        assert discovery_service._determine_source_tier(mock_agent) == 'user'
    
    def test_determine_source_tier_default(self, discovery_service):
        """Test source tier defaults to system."""
        mock_agent = Mock()
        del mock_agent.source_tier  # No explicit tier
        del mock_agent.source_path  # No path
        
        tier = discovery_service._determine_source_tier(mock_agent)
        
        assert tier == 'system'
    
    def test_extract_agent_info_handles_missing_attributes(self, discovery_service):
        """Test extraction handles missing attributes gracefully."""
        # Minimal legacy agent with only type attribute
        mock_agent = Mock(spec=['type'])
        mock_agent.type = 'minimal'
        
        info = discovery_service._extract_agent_info(mock_agent)
        
        assert info['id'] == 'minimal'
        assert info['name'] == 'Minimal'  # Title case from type
        assert info['description'] == 'No description available'
        assert info['specializations'] == []
        assert info['tools'] == []
    
    def test_logging_on_extraction_error(self, discovery_service, caplog):
        """Test that extraction errors are logged properly."""
        # Create agent that will cause extraction to fail
        mock_agent = Mock()
        mock_agent.agent_id = 'bad-agent'
        
        # Force an error by making metadata access fail
        type(mock_agent).metadata = property(lambda self: 1/0)  # Division by zero
        
        with caplog.at_level(logging.ERROR):
            discovery_service._extract_agent_info(mock_agent)
        
        assert "Error extracting agent info" in caplog.text