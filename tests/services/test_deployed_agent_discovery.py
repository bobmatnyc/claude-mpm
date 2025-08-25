"""Unit tests for DeployedAgentDiscovery service.

This module tests the DeployedAgentDiscovery service which is responsible for
discovering and listing deployed agents in the system.

TEST SCENARIOS COVERED:
1. Service initialization with default and custom project roots
2. Agent discovery from registry with new and legacy schema formats
3. Empty agent list handling
4. Error handling during discovery
5. Agent information extraction with missing attributes
6. Source tier determination (system, project, user)
7. Logging of errors during extraction

TEST FOCUS:
- Validates proper integration with AgentRegistryAdapter
- Ensures backward compatibility with legacy agent formats
- Tests error resilience and graceful degradation
- Verifies source tier logic for agent prioritization

TEST COVERAGE GAPS:
- No testing of concurrent discovery operations
- No testing of large-scale agent lists (performance)
- No testing of filesystem-based discovery
- No integration tests with actual registry
"""

import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_mpm.services.agents.registry import DeployedAgentDiscovery


class TestDeployedAgentDiscovery:
    """Test cases for DeployedAgentDiscovery service.

    This test class uses mocking to isolate the discovery service
    from its dependencies (AgentRegistryAdapter, get_path_manager()).
    """

    @pytest.fixture
    def mock_agent_registry(self):
        """Create a mock agent registry."""
        with patch(
            "claude_mpm.services.deployed_agent_discovery.AgentRegistryAdapter"
        ) as mock:
            yield mock

    @pytest.fixture
    def mock_path_resolver(self):
        """Create a mock path resolver."""
        with patch(
            "claude_mpm.services.agents.registry.deployed_agent_discovery.get_path_manager"
        ) as mock_func:
            mock_manager = Mock()
            mock_manager.project_root = Path("/test/project")
            mock_func.return_value = mock_manager
            yield mock_func

    @pytest.fixture
    def discovery_service(self, mock_agent_registry, mock_path_resolver):
        """Create a DeployedAgentDiscovery instance with mocks."""
        return DeployedAgentDiscovery()

    def test_init_with_default_project_root(mock_path_resolver):
        """Test initialization with default project root."""
        service = DeployedAgentDiscovery()
        assert service.project_root == Path("/test/project")
        mock_path_resolver.assert_called_once()

    def test_init_with_custom_project_root(
        self, mock_agent_registry, mock_path_resolver
    ):
        """Test initialization with custom project root."""
        custom_root = Path("/custom/root")
        service = DeployedAgentDiscovery(project_root=custom_root)
        assert service.project_root == custom_root
        mock_path_resolver.assert_not_called()

    def test_discover_deployed_agents_success(discovery_service):
        """Test successful agent discovery.

        This test validates that the discovery service can:
        1. Handle agents with new schema format (metadata, capabilities objects)
        2. Handle agents with legacy format (flat attributes)
        3. Extract all required fields from both formats
        4. Return properly formatted agent information

        The test uses mocked agents to ensure both schema formats
        are properly supported for backward compatibility.
        """
        # Create mock agents with new schema
        mock_agent1 = Mock()
        mock_agent1.agent_id = "research"
        mock_agent1.metadata.name = "Research Agent"
        mock_agent1.metadata.description = "Analyzes codebases"
        mock_agent1.metadata.specializations = ["analysis", "patterns"]
        mock_agent1.capabilities = {
            "when_to_use": ["codebase analysis", "pattern detection"]
        }
        mock_agent1.configuration.tools = ["grep", "find"]

        # Create mock agent with legacy format
        mock_agent2 = Mock(
            spec=["type", "name", "description", "specializations", "tools"]
        )
        mock_agent2.type = "engineer"
        mock_agent2.name = "Engineer Agent"
        mock_agent2.description = "Implements solutions"
        mock_agent2.specializations = ["coding", "refactoring"]
        mock_agent2.tools = ["edit", "write"]

        discovery_service.agent_registry.list_agents.return_value = [
            mock_agent1,
            mock_agent2,
        ]

        agents = discovery_service.discover_deployed_agents()

        assert len(agents) == 2

        # Verify first agent (new schema)
        assert agents[0]["id"] == "research"
        assert agents[0]["name"] == "Research Agent"
        assert agents[0]["description"] == "Analyzes codebases"
        assert agents[0]["specializations"] == ["analysis", "patterns"]
        assert agents[0]["capabilities"] == {
            "when_to_use": ["codebase analysis", "pattern detection"]
        }
        assert agents[0]["tools"] == ["grep", "find"]

        # Verify second agent (legacy format)
        assert agents[1]["id"] == "engineer"
        assert agents[1]["name"] == "Engineer Agent"
        assert agents[1]["description"] == "Implements solutions"
        assert agents[1]["specializations"] == ["coding", "refactoring"]
        assert agents[1]["tools"] == ["edit", "write"]

    def test_discover_deployed_agents_empty_list(discovery_service):
        """Test discovery with no agents."""
        discovery_service.agent_registry.list_agents.return_value = []

        agents = discovery_service.discover_deployed_agents()

        assert agents == []

    def test_discover_deployed_agents_with_error(discovery_service):
        """Test discovery handles registry errors gracefully."""
        discovery_service.agent_registry.list_agents.side_effect = Exception(
            "Registry error"
        )

        agents = discovery_service.discover_deployed_agents()

        # Should return empty list on failure
        assert agents == []

    def test_extract_agent_info_with_error(discovery_service):
        """Test extraction handles errors gracefully."""
        # Create an agent that will cause extraction to fail
        mock_agent = Mock()
        # Make metadata access raise an exception
        type(mock_agent).metadata = property(
            lambda self: (_ for _ in ()).throw(Exception("Extraction error"))
        )

        result = discovery_service._extract_agent_info(mock_agent)

        assert result is None

    def test_determine_source_tier_with_explicit_tier(discovery_service):
        """Test source tier determination with explicit attribute.

        Validates that when an agent has an explicit source_tier attribute,
        it is used directly without any path-based inference.
        """
        mock_agent = Mock()
        mock_agent.source_tier = "project"

        tier = discovery_service._determine_source_tier(mock_agent)

        assert tier == "project"

    def test_determine_source_tier_from_path(discovery_service):
        """Test source tier determination from file path.

        This test validates the path-based tier inference logic:
        - Agents in project's .claude/agents/ → 'project' tier
        - Agents in user's home directory → 'user' tier
        - Other locations → 'system' tier (default)

        This tier system helps prioritize agent selection when
        multiple agents with the same ID exist.
        """
        mock_agent = Mock()
        del mock_agent.source_tier  # No explicit tier

        # Test project tier detection
        mock_agent.source_path = "/test/project/.claude/agents/custom.json"
        assert discovery_service._determine_source_tier(mock_agent) == "project"

        # Test user tier detection
        mock_agent.source_path = f"{Path.home()}/agents/custom.json"
        assert discovery_service._determine_source_tier(mock_agent) == "user"

    def test_determine_source_tier_default(discovery_service):
        """Test source tier defaults to system."""
        mock_agent = Mock()
        del mock_agent.source_tier  # No explicit tier
        del mock_agent.source_path  # No path

        tier = discovery_service._determine_source_tier(mock_agent)

        assert tier == "system"

    def test_extract_agent_info_handles_missing_attributes(discovery_service):
        """Test extraction handles missing attributes gracefully."""
        # Minimal legacy agent with only type attribute
        mock_agent = Mock(spec=["type"])
        mock_agent.type = "minimal"

        info = discovery_service._extract_agent_info(mock_agent)

        assert info["id"] == "minimal"
        assert info["name"] == "Minimal"  # Title case from type
        assert info["description"] == "No description available"
        assert info["specializations"] == []
        assert info["tools"] == []

    def test_logging_on_extraction_error(discovery_service, caplog):
        """Test that extraction errors are logged properly."""
        # Create agent that will cause extraction to fail
        mock_agent = Mock()
        mock_agent.agent_id = "bad-agent"

        # Force an error by making metadata access fail
        type(mock_agent).metadata = property(lambda self: 1 / 0)  # Division by zero

        with caplog.at_level(logging.ERROR):
            discovery_service._extract_agent_info(mock_agent)

        assert "Error extracting agent info" in caplog.text
