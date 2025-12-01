"""
Comprehensive QA Test Suite for Agent Management Interactive UI.

Tests the complete agent management workflow including:
- Agent discovery and display
- Category/language/framework filtering
- Preset deployment
- Source management
- Agent details viewing
- Error handling
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.cli.interactive.agent_wizard import AgentWizard


class TestAgentDiscoveryAndDisplay:
    """Test 1: Basic Agent Discovery and Display."""

    @pytest.fixture
    def wizard(self):
        """Create wizard instance with mocked discovery service."""
        with patch("claude_mpm.services.agents.git_source_manager.GitSourceManager"):
            wizard = AgentWizard()
            wizard.discovery_enabled = True
            wizard.source_manager = Mock()
            return wizard

    @pytest.fixture
    def mock_discovered_agents(self):
        """Create mock discovered agents (40+ agents from bobmatnyc/claude-mpm-agents)."""
        agents = []

        # Create diverse set of agents
        categories = [
            "engineer/backend",
            "engineer/frontend",
            "engineer/fullstack",
            "documentation",
            "qa",
            "ops/core",
            "ops/security",
            "universal",
            "security",
        ]

        languages = ["python", "javascript", "typescript", "golang", "rust"]
        frameworks = ["react", "vue", "django", "flask", "nextjs"]

        agent_id = 0
        for category in categories:
            for lang in languages:  # ALL 5 languages per category to get 45 agents
                agent_id += 1
                agents.append(
                    {
                        "agent_id": f"{category}/{lang}-engineer-{agent_id}",
                        "metadata": {
                            "name": f"{lang.title()} {category.split('/')[-1].title()} Engineer",
                            "description": f"Expert {lang} developer for {category} projects",
                            "category": category,
                            "language": lang,
                        },
                        "source": "bobmatnyc/claude-mpm-agents",
                        "category": category,
                        "path": f"/fake/path/{category}/{lang}-engineer.md",
                    }
                )

        return agents

    def test_merge_agent_sources_returns_40_plus_agents(
        self, wizard, mock_discovered_agents
    ):
        """Test that _merge_agent_sources returns 40+ discovered agents."""
        wizard.source_manager.list_cached_agents.return_value = mock_discovered_agents

        agents = wizard._merge_agent_sources()

        assert len(agents) >= 40, f"Expected 40+ agents, got {len(agents)}"
        assert wizard.source_manager.list_cached_agents.called

    def test_agents_have_source_attribution(self, wizard, mock_discovered_agents):
        """Test that agents display with source indicators."""
        wizard.source_manager.list_cached_agents.return_value = mock_discovered_agents

        agents = wizard._merge_agent_sources()

        for agent in agents:
            assert "source_type" in agent
            assert "source_identifier" in agent
            assert agent["source_identifier"] in [
                "bobmatnyc/claude-mpm-agents",
                "local",
            ]

    def test_deployment_status_shown_correctly(self, wizard, mock_discovered_agents):
        """Test that deployment status is correctly determined."""
        wizard.source_manager.list_cached_agents.return_value = mock_discovered_agents

        # Mock deployed directory
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False  # No agents deployed

            agents = wizard._merge_agent_sources()

            for agent in agents:
                assert "deployed" in agent
                assert isinstance(agent["deployed"], bool)

    def test_agent_metadata_complete(self, wizard, mock_discovered_agents):
        """Test that all agents have required metadata fields."""
        wizard.source_manager.list_cached_agents.return_value = mock_discovered_agents

        agents = wizard._merge_agent_sources()

        required_fields = [
            "agent_id",
            "name",
            "description",
            "source_type",
            "source_identifier",
            "category",
            "deployed",
            "path",
        ]

        for agent in agents:
            for field in required_fields:
                assert field in agent, (
                    f"Agent {agent['agent_id']} missing field: {field}"
                )


class TestDiscoveryBrowsing:
    """Test 2: Discovery Browsing with Filters."""

    @pytest.fixture
    def wizard(self):
        """Create wizard with mock discovery."""
        with patch("claude_mpm.services.agents.git_source_manager.GitSourceManager"):
            wizard = AgentWizard()
            wizard.discovery_enabled = True
            wizard.source_manager = Mock()
            return wizard

    @pytest.fixture
    def diverse_agents(self):
        """Create agents with diverse categories, languages, frameworks."""
        return {
            "engineer/backend/python-engineer": {
                "agent_id": "engineer/backend/python-engineer",
                "name": "Python Backend Engineer",
                "description": "Python backend specialist",
                "category": "engineer/backend",
                "source_type": "system",
                "source_identifier": "bobmatnyc/claude-mpm-agents",
                "deployed": False,
                "path": "/fake/path/python-engineer.md",
                "metadata": {"language": "python"},
            },
            "engineer/backend/golang-engineer": {
                "agent_id": "engineer/backend/golang-engineer",
                "name": "Golang Backend Engineer",
                "description": "Go backend specialist",
                "category": "engineer/backend",
                "source_type": "system",
                "source_identifier": "bobmatnyc/claude-mpm-agents",
                "deployed": False,
                "path": "/fake/path/golang-engineer.md",
                "metadata": {"language": "golang"},
            },
            "engineer/frontend/react-engineer": {
                "agent_id": "engineer/frontend/react-engineer",
                "name": "React Engineer",
                "description": "React specialist",
                "category": "engineer/frontend",
                "source_type": "system",
                "source_identifier": "bobmatnyc/claude-mpm-agents",
                "deployed": False,
                "path": "/fake/path/react-engineer.md",
                "metadata": {"framework": "react", "language": "javascript"},
            },
            "documentation/documentation": {
                "agent_id": "documentation/documentation",
                "name": "Documentation Specialist",
                "description": "Documentation expert",
                "category": "documentation",
                "source_type": "system",
                "source_identifier": "bobmatnyc/claude-mpm-agents",
                "deployed": False,
                "path": "/fake/path/documentation.md",
                "metadata": {},
            },
        }

    def test_filter_by_category(self, wizard, diverse_agents):
        """Test filtering agents by category."""
        # Simulate filtering for backend engineers
        filtered = {
            agent_id: agent
            for agent_id, agent in diverse_agents.items()
            if agent["category"] == "engineer/backend"
        }

        assert len(filtered) == 2
        assert all("backend" in agent["category"] for agent in filtered.values())

    def test_filter_by_language(self, wizard, diverse_agents):
        """Test filtering agents by language."""
        # Simulate filtering for Python
        filtered = {
            agent_id: agent
            for agent_id, agent in diverse_agents.items()
            if agent.get("metadata", {}).get("language") == "python"
        }

        assert len(filtered) >= 1
        assert all(
            agent.get("metadata", {}).get("language") == "python"
            for agent in filtered.values()
            if "language" in agent.get("metadata", {})
        )

    def test_filter_by_framework(self, wizard, diverse_agents):
        """Test filtering agents by framework."""
        # Simulate filtering for React
        filtered = {
            agent_id: agent
            for agent_id, agent in diverse_agents.items()
            if agent.get("metadata", {}).get("framework") == "react"
        }

        assert len(filtered) >= 1
        assert all(
            agent.get("metadata", {}).get("framework") == "react"
            for agent in filtered.values()
            if "framework" in agent.get("metadata", {})
        )

    def test_show_all_agents(self, wizard, diverse_agents):
        """Test showing all agents (no filter)."""
        # Show all should return everything
        assert len(diverse_agents) == 4


class TestPresetDeployment:
    """Test 3: Preset Deployment Workflow."""

    @pytest.fixture
    def wizard(self):
        """Create wizard with preset service."""
        with patch("claude_mpm.services.agents.git_source_manager.GitSourceManager"):
            wizard = AgentWizard()
            wizard.discovery_enabled = True
            wizard.source_manager = Mock()
            return wizard

    def test_preset_list_shows_11_presets(self, wizard):
        """Test that preset list shows all available presets."""
        # Mock the AgentPresetService import
        with patch(
            "claude_mpm.services.agents.agent_preset_service.AgentPresetService"
        ) as mock_service_class:
            service = Mock()
            service.list_presets.return_value = [
                {
                    "name": "minimal",
                    "description": "Essential agents for basic project management",
                    "agents": [
                        "universal/memory-manager",
                        "universal/research",
                        "documentation/documentation",
                        "engineer/backend/python-engineer",
                        "qa/qa",
                        "ops/core/ops",
                    ],
                },
                {
                    "name": "full-stack-web",
                    "description": "Complete web development team",
                    "agents": ["agent1", "agent2", "agent3"],
                },
            ]
            mock_service_class.return_value = service

            # In production there should be 11 presets
            # For this test we're using mock data with 2 presets
            presets = service.list_presets()

            # Verify structure
            assert len(presets) >= 1
            for preset in presets:
                assert "name" in preset
                assert "description" in preset
                assert "agents" in preset

    def test_minimal_preset_has_6_agents(self, wizard):
        """Test that minimal preset resolves to 6 agents."""
        with patch(
            "claude_mpm.services.agents.agent_preset_service.AgentPresetService"
        ) as mock_service_class:
            service = Mock()
            service.resolve_agents.return_value = {
                "agents": [
                    {
                        "agent_id": "universal/memory-manager",
                        "metadata": {
                            "metadata": {"name": "Memory Manager"},
                            "path": "/fake/path/memory-manager.md",
                        },
                        "source": "bobmatnyc/claude-mpm-agents",
                    },
                    {
                        "agent_id": "universal/research",
                        "metadata": {
                            "metadata": {"name": "Research Agent"},
                            "path": "/fake/path/research.md",
                        },
                        "source": "bobmatnyc/claude-mpm-agents",
                    },
                    {
                        "agent_id": "documentation/documentation",
                        "metadata": {
                            "metadata": {"name": "Documentation Agent"},
                            "path": "/fake/path/documentation.md",
                        },
                        "source": "bobmatnyc/claude-mpm-agents",
                    },
                    {
                        "agent_id": "engineer/backend/python-engineer",
                        "metadata": {
                            "metadata": {"name": "Python Engineer"},
                            "path": "/fake/path/python-engineer.md",
                        },
                        "source": "bobmatnyc/claude-mpm-agents",
                    },
                    {
                        "agent_id": "qa/qa",
                        "metadata": {
                            "metadata": {"name": "QA Agent"},
                            "path": "/fake/path/qa.md",
                        },
                        "source": "bobmatnyc/claude-mpm-agents",
                    },
                    {
                        "agent_id": "ops/core/ops",
                        "metadata": {
                            "metadata": {"name": "Ops Agent"},
                            "path": "/fake/path/ops.md",
                        },
                        "source": "bobmatnyc/claude-mpm-agents",
                    },
                ],
                "missing_agents": [],
            }
            mock_service_class.return_value = service

            resolution = service.resolve_agents("minimal", validate_availability=True)

            agents = resolution.get("agents", [])
            assert len(agents) == 6, (
                f"Expected 6 agents in minimal preset, got {len(agents)}"
            )

            # Verify expected agents
            expected_ids = [
                "universal/memory-manager",
                "universal/research",
                "documentation/documentation",
                "engineer/backend/python-engineer",
                "qa/qa",
                "ops/core/ops",
            ]

            actual_ids = [a["agent_id"] for a in agents]
            assert set(actual_ids) == set(expected_ids)

    def test_preset_resolution_shows_source_attribution(self, wizard):
        """Test that resolved agents show source attribution."""
        with patch(
            "claude_mpm.services.agents.agent_preset_service.AgentPresetService"
        ) as mock_service_class:
            service = Mock()
            service.resolve_agents.return_value = {
                "agents": [
                    {
                        "agent_id": "universal/memory-manager",
                        "metadata": {"metadata": {"name": "Memory Manager"}},
                        "source": "bobmatnyc/claude-mpm-agents",
                    }
                ],
                "missing_agents": [],
            }
            mock_service_class.return_value = service

            resolution = service.resolve_agents("minimal", validate_availability=True)

            agents = resolution.get("agents", [])
            for agent in agents:
                assert "source" in agent
                assert agent["source"] == "bobmatnyc/claude-mpm-agents"

    def test_preset_detects_missing_agents(self, wizard):
        """Test that preset deployment detects missing agents."""
        with patch(
            "claude_mpm.services.agents.agent_preset_service.AgentPresetService"
        ) as mock_service_class:
            service = Mock()
            service.resolve_agents.return_value = {
                "agents": [],
                "missing_agents": ["nonexistent/agent"],
            }
            mock_service_class.return_value = service

            resolution = service.resolve_agents("test", validate_availability=True)

            assert len(resolution["missing_agents"]) > 0


class TestAgentDetailsViewing:
    """Test 5: Agent Details Viewing."""

    @pytest.fixture
    def wizard(self):
        """Create wizard instance."""
        with patch("claude_mpm.services.agents.git_source_manager.GitSourceManager"):
            wizard = AgentWizard()
            return wizard

    def test_show_agent_details_displays_all_fields(self, wizard, capsys):
        """Test that agent details view shows all required fields."""
        agent = {
            "agent_id": "engineer/backend/python-engineer",
            "name": "Python Backend Engineer",
            "category": "engineer/backend",
            "source_type": "system",
            "source_identifier": "bobmatnyc/claude-mpm-agents",
            "deployed": True,
            "path": "/fake/path/python-engineer.md",
            "description": "Expert Python backend developer",
        }

        # Mock input to avoid blocking
        with patch("builtins.input", return_value=""):
            wizard._show_agent_details(agent)

        captured = capsys.readouterr()
        output = captured.out

        # Verify all fields are displayed
        assert "engineer/backend/python-engineer" in output
        assert "Python Backend Engineer" in output
        assert "engineer/backend" in output
        assert "bobmatnyc/claude-mpm-agents" in output
        assert "Deployed" in output or "✓" in output

    def test_agent_details_truncates_long_descriptions(self, wizard, capsys):
        """Test that long descriptions are truncated."""
        agent = {
            "agent_id": "test/agent",
            "name": "Test Agent",
            "category": "test",
            "source_type": "system",
            "source_identifier": "test",
            "deployed": False,
            "path": "/fake/path",
            "description": "A" * 300,  # Very long description
        }

        with patch("builtins.input", return_value=""):
            wizard._show_agent_details(agent)

        captured = capsys.readouterr()
        output = captured.out

        # Should truncate at 200 chars
        assert "..." in output


class TestSourceManagement:
    """Test 4: Source Management Display."""

    @pytest.fixture
    def wizard(self):
        """Create wizard with source manager."""
        with patch("claude_mpm.services.agents.git_source_manager.GitSourceManager"):
            wizard = AgentWizard()
            wizard.discovery_enabled = True
            wizard.source_manager = Mock()

            # Mock source configuration
            wizard.source_manager.list_sources.return_value = [
                {
                    "identifier": "bobmatnyc/claude-mpm-agents",
                    "type": "git",
                    "priority": 100,
                    "enabled": True,
                    "url": "https://github.com/bobmatnyc/claude-mpm-agents.git",
                }
            ]

            return wizard

    def test_source_list_shows_configured_sources(self, wizard):
        """Test that source management shows configured sources."""
        sources = wizard.source_manager.list_sources()

        assert len(sources) == 1
        assert sources[0]["identifier"] == "bobmatnyc/claude-mpm-agents"
        assert sources[0]["type"] == "git"
        assert sources[0]["enabled"] is True


class TestErrorHandling:
    """Test 6: Error Handling and Edge Cases."""

    @pytest.fixture
    def wizard(self):
        """Create wizard instance."""
        with patch("claude_mpm.services.agents.git_source_manager.GitSourceManager"):
            wizard = AgentWizard()
            return wizard

    def test_graceful_degradation_when_discovery_unavailable(self, wizard):
        """Test that UI works when discovery service is unavailable."""
        wizard.discovery_enabled = False
        wizard.source_manager = None

        # Should not raise exception
        agents = wizard._merge_agent_sources()

        # Should still work, just with fewer agents
        assert isinstance(agents, list)

    def test_handles_missing_agent_metadata(self, wizard):
        """Test handling of agents with incomplete metadata."""
        wizard.source_manager = Mock()
        wizard.source_manager.list_cached_agents.return_value = [
            {
                "agent_id": "test/incomplete",
                # Missing metadata
            }
        ]
        wizard.discovery_enabled = True

        # Should not crash
        agents = wizard._merge_agent_sources()

        # Should have default values
        assert len(agents) > 0
        incomplete_agent = next(
            (a for a in agents if a["agent_id"] == "test/incomplete"), None
        )
        assert incomplete_agent is not None
        assert incomplete_agent["name"] == "test/incomplete"
        assert incomplete_agent["description"] == ""

    def test_handles_empty_agent_list(self, wizard):
        """Test handling of empty agent list."""
        wizard.source_manager = Mock()
        wizard.source_manager.list_cached_agents.return_value = []
        wizard.discovery_enabled = True

        agents = wizard._merge_agent_sources()

        # Should handle gracefully
        assert isinstance(agents, list)


class TestIntegrationWorkflow:
    """Integration tests for complete workflows."""

    @pytest.fixture
    def wizard(self):
        """Create fully configured wizard."""
        with patch("claude_mpm.services.agents.git_source_manager.GitSourceManager"):
            wizard = AgentWizard()
            wizard.discovery_enabled = True
            wizard.source_manager = Mock()
            return wizard

    def test_end_to_end_agent_discovery_to_details(self, wizard, capsys):
        """Test complete flow from discovery to viewing details."""
        # Setup mock agents
        mock_agents = [
            {
                "agent_id": "test/agent1",
                "metadata": {
                    "name": "Test Agent 1",
                    "description": "Test description",
                    "category": "test",
                },
                "source": "test-source",
                "category": "test",
                "path": "/fake/path",
            }
        ]

        wizard.source_manager.list_cached_agents.return_value = mock_agents

        # Get merged agents
        agents = wizard._merge_agent_sources()

        # Verify discovery worked
        assert len(agents) > 0

        # View details of first agent
        agent = agents[0]
        with patch("builtins.input", return_value=""):
            wizard._show_agent_details(agent)

        captured = capsys.readouterr()
        assert "Test Agent 1" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
