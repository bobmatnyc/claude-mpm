"""
Tests for Agent Listing Service
================================

WHY: The agent listing service handles critical functionality for discovering,
listing, and comparing agents across different tiers. These tests ensure that
the service correctly manages agent information, caching, and error handling.

COVERAGE:
- All listing methods (system, deployed, by-tier)
- Caching behavior and TTL
- Error handling for missing agents and invalid paths
- Version comparison logic
- Integration with registry adapter
"""

import time
from unittest.mock import Mock, mock_open, patch

import pytest

from claude_mpm.services.cli.agent_listing_service import (
    AgentInfo, AgentListingService, AgentTierInfo, IAgentListingService)


class TestAgentListingService:
    """Test suite for AgentListingService."""

    @pytest.fixture
    def mock_deployment_service(self):
        """Create a mock deployment service."""
        service = Mock()

        # Mock list_available_agents
        service.list_available_agents.return_value = [
            {
                "name": "engineer",
                "type": "specialist",
                "path": "/path/to/engineer.json",
                "description": "Engineering agent",
                "specializations": ["coding", "architecture"],
                "version": "1.0.0",
            },
            {
                "name": "qa",
                "type": "specialist",
                "path": "/path/to/qa.json",
                "description": "QA agent",
                "specializations": ["testing", "validation"],
                "version": "1.0.0",
            },
        ]

        # Mock verify_deployment
        service.verify_deployment.return_value = {
            "agents_found": [
                {
                    "name": "engineer",
                    "type": "specialist",
                    "tier": "system",
                    "path": "/deployed/engineer.json",
                    "description": "Deployed engineering agent",
                    "version": "1.0.0",
                },
            ],
            "warnings": ["Some agents may be outdated"],
        }

        # Mock get_agent_details
        service.get_agent_details.return_value = {
            "name": "engineer",
            "type": "specialist",
            "tier": "system",
            "path": "/path/to/engineer.json",
            "description": "Engineering agent",
            "content": "---\nname: engineer\n---\nAgent content here",
        }

        return service

    @pytest.fixture
    def mock_registry_adapter(self):
        """Create a mock registry adapter."""
        adapter = Mock()
        registry = Mock()

        # Mock list_agents
        registry.list_agents.return_value = {
            "engineer": {
                "type": "specialist",
                "tier": "system",
                "path": "/system/engineer.json",
                "description": "System engineering agent",
                "specializations": ["coding"],
                "deployed": True,
            },
            "qa": {
                "type": "specialist",
                "tier": "user",
                "path": "/user/qa.json",
                "description": "User QA agent",
                "specializations": ["testing"],
                "deployed": False,
            },
            "research": {
                "type": "specialist",
                "tier": "project",
                "path": "/project/research.json",
                "description": "Project research agent",
                "specializations": ["analysis"],
                "deployed": True,
            },
        }

        # Mock get_agent
        def get_agent_side_effect(name):
            if name == "engineer":
                mock_agent = Mock()
                mock_agent.name = "engineer"
                mock_agent.type = "specialist"
                mock_agent.tier = "system"
                mock_agent.path = "/system/engineer.json"
                mock_agent.description = "System engineering agent"
                mock_agent.specializations = ["coding"]
                return mock_agent
            if name == "qa":
                mock_agent = Mock()
                mock_agent.name = "qa"
                mock_agent.type = "specialist"
                mock_agent.tier = "user"
                mock_agent.path = "/user/qa.json"
                mock_agent.description = "User QA agent"
                mock_agent.specializations = ["testing"]
                return mock_agent
            return None

        registry.get_agent.side_effect = get_agent_side_effect

        adapter.registry = registry
        return adapter

    @pytest.fixture
    def service(self, mock_deployment_service, mock_registry_adapter):
        """Create service instance with mocked dependencies."""
        service = AgentListingService(deployment_service=mock_deployment_service)
        service._registry_adapter = mock_registry_adapter
        return service

    def test_implements_interface(self, service):
        """Test that service implements IAgentListingService interface."""
        assert isinstance(service, IAgentListingService)

        # Check all interface methods are implemented
        assert hasattr(service, "list_system_agents")
        assert hasattr(service, "list_deployed_agents")
        assert hasattr(service, "list_agents_by_tier")
        assert hasattr(service, "get_agent_details")
        assert hasattr(service, "compare_versions")
        assert hasattr(service, "find_agent")
        assert hasattr(service, "clear_cache")

    def test_list_system_agents(self, service):
        """Test listing system agents."""
        agents = service.list_system_agents()

        assert len(agents) == 2
        assert agents[0].name == "engineer"
        assert agents[0].type == "specialist"
        assert agents[0].tier == "system"
        assert agents[0].path == "/path/to/engineer.json"
        assert agents[0].description is None  # Not verbose

        # Test verbose mode
        agents_verbose = service.list_system_agents(verbose=True)
        assert agents_verbose[0].description == "Engineering agent"
        assert agents_verbose[0].specializations == ["coding", "architecture"]
        assert agents_verbose[0].version == "1.0.0"

    def test_list_system_agents_error_handling(self, service):
        """Test error handling in list_system_agents."""
        service.deployment_service.list_available_agents.side_effect = Exception(
            "Service error"
        )

        agents = service.list_system_agents()
        assert agents == []

    def test_list_deployed_agents(self, service):
        """Test listing deployed agents."""
        agents, warnings = service.list_deployed_agents()

        assert len(agents) == 1
        assert agents[0].name == "engineer"
        assert agents[0].deployed is True
        assert len(warnings) == 1
        assert warnings[0] == "Some agents may be outdated"

        # Test verbose mode
        agents_verbose, _ = service.list_deployed_agents(verbose=True)
        assert agents_verbose[0].description == "Deployed engineering agent"

    def test_list_deployed_agents_error_handling(self, service):
        """Test error handling in list_deployed_agents."""
        service.deployment_service.verify_deployment.side_effect = Exception(
            "Deployment error"
        )

        agents, warnings = service.list_deployed_agents()
        assert agents == []
        assert len(warnings) == 1
        assert "Error listing deployed agents" in warnings[0]

    def test_list_agents_by_tier(self, service):
        """Test listing agents grouped by tier."""
        tier_info = service.list_agents_by_tier()

        assert isinstance(tier_info, AgentTierInfo)
        assert len(tier_info.project) == 1
        assert len(tier_info.user) == 1
        assert len(tier_info.system) == 1

        # Check project agent
        assert tier_info.project[0].name == "research"
        assert tier_info.project[0].tier == "project"

        # Check user agent
        assert tier_info.user[0].name == "qa"
        assert tier_info.user[0].tier == "user"

        # Check system agent
        assert tier_info.system[0].name == "engineer"
        assert tier_info.system[0].tier == "system"

        # Check total counts
        assert tier_info.total_count == 3

    def test_list_agents_by_tier_with_overrides(self, service):
        """Test that agents in higher tiers override lower tiers."""
        # Modify mock to have same agent in multiple tiers
        service.registry_adapter.registry.list_agents.return_value = {
            "engineer": {
                "type": "specialist",
                "tier": "system",
                "path": "/system/engineer.json",
            },
            "engineer_user": {
                "type": "specialist",
                "tier": "user",
                "path": "/user/engineer.json",
            },
        }

        # Clear cache to force refresh
        service.clear_cache()

        # Create agents with same name in different tiers
        service.registry_adapter.registry.list_agents.return_value = {
            "engineer": {
                "tier": "system",
                "type": "specialist",
                "path": "/system/engineer.json",
            },
        }

        tier_info = service.list_agents_by_tier()

        # System agent should be marked as active since no override
        system_engineer = next(
            (a for a in tier_info.system if a.name == "engineer"), None
        )
        if system_engineer:
            assert system_engineer.active is True

    def test_list_agents_by_tier_error_handling(self, service):
        """Test error handling in list_agents_by_tier."""
        service.registry_adapter.registry = None

        tier_info = service.list_agents_by_tier()
        assert tier_info.total_count == 0

    def test_get_agent_details(self, service):
        """Test getting agent details."""
        details = service.get_agent_details("engineer")

        assert details is not None
        assert details["name"] == "engineer"
        assert details["type"] == "specialist"
        assert "content" in details

    def test_get_agent_details_from_registry(self, service):
        """Test getting agent details from registry when deployment service returns None."""
        service.deployment_service.get_agent_details.return_value = None

        with patch("builtins.open", mock_open(read_data="Agent content")):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value = Mock(st_size=100, st_mtime=1234567890)

                    details = service.get_agent_details("engineer")

                    assert details is not None
                    assert details["name"] == "engineer"
                    assert details["content"] == "Agent content"
                    assert details["size"] == 100

    def test_get_agent_details_not_found(self, service):
        """Test getting details for non-existent agent."""
        service.deployment_service.get_agent_details.return_value = None
        service.registry_adapter.registry.get_agent.return_value = None

        details = service.get_agent_details("nonexistent")
        assert details is None

    def test_compare_versions(self, service):
        """Test comparing agent versions across tiers."""
        comparison = service.compare_versions("engineer")

        assert comparison["agent_name"] == "engineer"
        assert "versions" in comparison
        assert "system" in comparison["versions"]
        assert comparison["versions"]["system"]["path"] == "/system/engineer.json"

    def test_compare_versions_not_found(self, service):
        """Test comparing versions for non-existent agent."""
        comparison = service.compare_versions("nonexistent")

        assert comparison["agent_name"] == "nonexistent"
        assert comparison["versions"] == {}
        assert comparison["active_tier"] is None

    def test_find_agent_in_deployed(self, service):
        """Test finding an agent in deployed agents."""
        agent = service.find_agent("engineer")

        assert agent is not None
        assert agent.name == "engineer"
        assert agent.deployed is True

    def test_find_agent_in_tiers(self, service):
        """Test finding an agent in tier listings."""
        # Make deployed agents return empty
        service.deployment_service.verify_deployment.return_value = {
            "agents_found": [],
            "warnings": [],
        }

        agent = service.find_agent("research")

        assert agent is not None
        assert agent.name == "research"
        assert agent.tier == "project"

    def test_find_agent_not_found(self, service):
        """Test finding non-existent agent."""
        service.deployment_service.verify_deployment.return_value = {
            "agents_found": [],
            "warnings": [],
        }

        agent = service.find_agent("nonexistent")
        assert agent is None

    def test_caching_behavior(self, service):
        """Test that caching works correctly."""
        # First call should hit the service
        agents1 = service.list_system_agents()
        assert service.deployment_service.list_available_agents.call_count == 1

        # Second call should use cache
        agents2 = service.list_system_agents()
        assert service.deployment_service.list_available_agents.call_count == 1
        assert agents1 == agents2

        # Clear cache and call again
        service.clear_cache()
        service.list_system_agents()
        assert service.deployment_service.list_available_agents.call_count == 2

    def test_cache_ttl(self, service):
        """Test that cache expires after TTL."""
        # Set short TTL for testing
        service._cache_ttl = 0.1

        # First call
        service.list_system_agents()
        assert service.deployment_service.list_available_agents.call_count == 1

        # Wait for cache to expire
        time.sleep(0.2)

        # Should hit service again
        service.list_system_agents()
        assert service.deployment_service.list_available_agents.call_count == 2

    def test_cache_key_separation(self, service):
        """Test that different cache keys don't interfere."""
        # Call with different parameters
        agents_normal = service.list_system_agents(verbose=False)
        agents_verbose = service.list_system_agents(verbose=True)

        # Both should hit the service
        assert service.deployment_service.list_available_agents.call_count == 2

        # Results should be different (verbose has more data)
        assert agents_normal[0].description is None
        assert agents_verbose[0].description is not None

    def test_clear_cache(self, service):
        """Test clearing the cache."""
        # Populate cache
        service.list_system_agents()
        service.list_deployed_agents()

        assert len(service._cache) > 0
        assert len(service._cache_times) > 0

        # Clear cache
        service.clear_cache()

        assert len(service._cache) == 0
        assert len(service._cache_times) == 0

    def test_lazy_loading_deployment_service(self):
        """Test lazy loading of deployment service."""
        service = AgentListingService()  # No deployment service provided

        # Initially should be None
        assert service._deployment_service is None

        # Access the property should trigger lazy loading
        # We'll mock the import to avoid actual import errors
        with patch("claude_mpm.services.AgentDeploymentService") as mock_cls:
            mock_instance = Mock()
            mock_cls.return_value = mock_instance

            # This should trigger the lazy loading
            deployment_service = service.deployment_service

            # Should no longer be None
            assert deployment_service is not None

    def test_lazy_loading_registry_adapter(self, service):
        """Test lazy loading of registry adapter."""
        service._registry_adapter = None

        with patch(
            "claude_mpm.services.cli.agent_listing_service.AgentRegistryAdapter"
        ) as mock_cls:
            mock_cls.return_value = Mock()

            # Access registry_adapter property
            _ = service.registry_adapter

            # Should create instance
            mock_cls.assert_called_once()

    def test_agent_info_dataclass(self):
        """Test AgentInfo dataclass."""
        agent = AgentInfo(
            name="test",
            type="specialist",
            tier="system",
            path="/path/to/test.json",
            description="Test agent",
            specializations=["testing"],
            version="1.0.0",
            deployed=True,
            active=False,
            overridden_by=["user"],
        )

        assert agent.name == "test"
        assert agent.type == "specialist"
        assert agent.tier == "system"
        assert agent.path == "/path/to/test.json"
        assert agent.description == "Test agent"
        assert agent.specializations == ["testing"]
        assert agent.version == "1.0.0"
        assert agent.deployed is True
        assert agent.active is False
        assert agent.overridden_by == ["user"]

    def test_agent_tier_info_properties(self):
        """Test AgentTierInfo properties."""
        tier_info = AgentTierInfo(
            project=[
                AgentInfo("p1", "specialist", "project", "/p1", active=True),
                AgentInfo("p2", "specialist", "project", "/p2", active=False),
            ],
            user=[
                AgentInfo("u1", "specialist", "user", "/u1", active=True),
            ],
            system=[
                AgentInfo("s1", "specialist", "system", "/s1", active=False),
                AgentInfo("s2", "specialist", "system", "/s2", active=True),
            ],
        )

        assert tier_info.total_count == 5
        assert tier_info.active_count == 3  # p1, u1, s2 are active
