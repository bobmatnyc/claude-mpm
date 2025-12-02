"""Unit tests for AgentPresetService.

Tests preset resolution, validation, and agent lookup functionality.
"""

import pytest

from src.claude_mpm.config.agent_presets import get_preset_names
from src.claude_mpm.services.agents.agent_preset_service import \
    AgentPresetService


class TestAgentPresetService:
    """Test suite for AgentPresetService."""

    @pytest.fixture
    def mock_source_manager(self, mocker):
        """Create mock GitSourceManager."""
        mock = mocker.Mock()
        # Return empty list by default (no agents cached)
        mock.list_cached_agents.return_value = []
        return mock

    @pytest.fixture
    def service(self, mock_source_manager):
        """Create AgentPresetService with mock."""
        return AgentPresetService(mock_source_manager)

    def test_list_presets(self, service):
        """Test listing all available presets."""
        presets = service.list_presets()

        assert len(presets) >= 10  # At least 10 presets defined
        assert all("name" in p for p in presets)
        assert all("description" in p for p in presets)
        assert all("agent_count" in p for p in presets)
        assert all("use_cases" in p for p in presets)

        # Verify specific presets exist
        preset_names = [p["name"] for p in presets]
        assert "minimal" in preset_names
        assert "python-dev" in preset_names
        assert "nextjs-fullstack" in preset_names

    def test_validate_preset_valid(self, service):
        """Test preset name validation with valid names."""
        assert service.validate_preset("minimal")
        assert service.validate_preset("python-dev")
        assert service.validate_preset("nextjs-fullstack")

    def test_validate_preset_invalid(self, service):
        """Test preset name validation with invalid names."""
        assert not service.validate_preset("invalid-preset")
        assert not service.validate_preset("nonexistent")
        assert not service.validate_preset("")

    def test_get_preset_agents(self, service):
        """Test getting agent list for preset."""
        # Test minimal preset
        agents = service.get_preset_agents("minimal")
        assert len(agents) == 6
        assert "universal/memory-manager" in agents
        assert "universal/research" in agents

        # Test python-dev preset
        agents = service.get_preset_agents("python-dev")
        assert len(agents) == 8
        assert "engineer/backend/python-engineer" in agents
        assert "security/security" in agents

    def test_get_preset_agents_invalid(self, service):
        """Test getting agents for invalid preset."""
        with pytest.raises(ValueError, match="Unknown preset"):
            service.get_preset_agents("invalid-preset")

    def test_resolve_agents_without_validation(self, service):
        """Test resolving preset without availability validation."""
        result = service.resolve_agents("minimal", validate_availability=False)

        assert "preset_info" in result
        assert "agents" in result
        assert "missing_agents" in result
        assert "conflicts" in result

        # Should have agent IDs without validation
        assert len(result["agents"]) == 6
        assert all("agent_id" in agent for agent in result["agents"])

        # No missing or conflicts when validation disabled
        assert len(result["missing_agents"]) == 0
        assert len(result["conflicts"]) == 0

    def test_resolve_agents_all_available(self, service, mock_source_manager):
        """Test resolving preset when all agents are available."""
        # Mock cached agents to match minimal preset
        mock_source_manager.list_cached_agents.return_value = [
            {
                "agent_id": "universal/memory-manager",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "Memory Manager"},
            },
            {
                "agent_id": "universal/research",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "Research"},
            },
            {
                "agent_id": "documentation/documentation",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "Documentation"},
            },
            {
                "agent_id": "engineer/backend/python-engineer",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "Python Engineer"},
            },
            {
                "agent_id": "qa/qa",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "QA"},
            },
            {
                "agent_id": "ops/core/ops",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "Ops"},
            },
        ]

        result = service.resolve_agents("minimal", validate_availability=True)

        # All agents should be found
        assert len(result["agents"]) == 6
        assert len(result["missing_agents"]) == 0
        assert len(result["conflicts"]) == 0

        # Verify agent metadata
        for agent in result["agents"]:
            assert "agent_id" in agent
            assert "source" in agent
            assert "metadata" in agent

    def test_resolve_agents_missing_some(self, service, mock_source_manager):
        """Test resolving preset with some missing agents."""
        # Mock only 2 out of 6 agents available
        mock_source_manager.list_cached_agents.return_value = [
            {
                "agent_id": "universal/memory-manager",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "Memory Manager"},
            },
            {
                "agent_id": "universal/research",
                "source": {"identifier": "test-repo"},
                "metadata": {"name": "Research"},
            },
        ]

        result = service.resolve_agents("minimal", validate_availability=True)

        # Should have 2 available, 4 missing
        assert len(result["agents"]) == 2
        assert len(result["missing_agents"]) == 4

        # Verify missing agent IDs
        assert "documentation/documentation" in result["missing_agents"]
        assert "engineer/backend/python-engineer" in result["missing_agents"]

    def test_resolve_agents_with_conflicts(self, service, mock_source_manager):
        """Test resolving preset with source conflicts."""
        # Mock same agent in multiple sources (priority conflict)
        mock_source_manager.list_cached_agents.return_value = [
            {
                "agent_id": "universal/memory-manager",
                "source": {"identifier": "repo-a"},
                "metadata": {"name": "Memory Manager A"},
            },
            {
                "agent_id": "universal/memory-manager",
                "source": {"identifier": "repo-b"},
                "metadata": {"name": "Memory Manager B"},
            },
            {
                "agent_id": "universal/research",
                "source": {"identifier": "repo-a"},
                "metadata": {"name": "Research"},
            },
            {
                "agent_id": "documentation/documentation",
                "source": {"identifier": "repo-a"},
                "metadata": {"name": "Documentation"},
            },
            {
                "agent_id": "engineer/backend/python-engineer",
                "source": {"identifier": "repo-a"},
                "metadata": {"name": "Python Engineer"},
            },
            {
                "agent_id": "qa/qa",
                "source": {"identifier": "repo-a"},
                "metadata": {"name": "QA"},
            },
            {
                "agent_id": "ops/core/ops",
                "source": {"identifier": "repo-a"},
                "metadata": {"name": "Ops"},
            },
        ]

        result = service.resolve_agents("minimal", validate_availability=True)

        # Should detect conflict for memory-manager
        assert len(result["conflicts"]) == 1
        assert result["conflicts"][0]["agent_id"] == "universal/memory-manager"
        assert "repo-a" in result["conflicts"][0]["sources"]
        assert "repo-b" in result["conflicts"][0]["sources"]

        # Should still resolve to 6 agents (first source wins)
        assert len(result["agents"]) == 6

    def test_resolve_agents_invalid_preset(self, service):
        """Test resolving invalid preset."""
        with pytest.raises(ValueError, match="Unknown preset"):
            service.resolve_agents("invalid-preset", validate_availability=True)

    def test_preset_info_structure(self, service):
        """Test preset info has correct structure."""
        presets = service.list_presets()

        for preset in presets:
            # Required fields
            assert "name" in preset
            assert "description" in preset
            assert "agent_count" in preset
            assert "use_cases" in preset

            # Type checks
            assert isinstance(preset["name"], str)
            assert isinstance(preset["description"], str)
            assert isinstance(preset["agent_count"], int)
            assert isinstance(preset["use_cases"], list)

            # Value checks
            assert len(preset["name"]) > 0
            assert len(preset["description"]) > 0
            assert preset["agent_count"] > 0
            assert len(preset["use_cases"]) > 0

    def test_preset_consistency(self, service):
        """Test that preset agent counts match actual lists."""
        for preset_name in get_preset_names():
            preset_info = service.list_presets()
            matching = [p for p in preset_info if p["name"] == preset_name]
            assert len(matching) == 1

            info = matching[0]
            agents = service.get_preset_agents(preset_name)

            # Agent count should match actual list length
            assert info["agent_count"] == len(agents)

    def test_all_presets_have_unique_names(self, service):
        """Test that all preset names are unique."""
        presets = service.list_presets()
        names = [p["name"] for p in presets]

        # No duplicates
        assert len(names) == len(set(names))

    def test_preset_agents_no_duplicates(self, service):
        """Test that preset agent lists have no duplicates."""
        for preset_name in get_preset_names():
            agents = service.get_preset_agents(preset_name)

            # No duplicate agent IDs within preset
            assert len(agents) == len(set(agents))
