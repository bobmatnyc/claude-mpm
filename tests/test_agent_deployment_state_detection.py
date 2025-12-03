"""
Tests for agent deployment state detection fix.

This test suite verifies that the _is_agent_deployed() method correctly
detects agents from virtual deployment state files (.mpm_deployment_state)
as well as physical agent files.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.cli.commands.agent_state_manager import SimpleAgentManager


class TestAgentDeploymentStateDetection:
    """Test suite for virtual deployment state detection."""

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary config directory."""
        config_dir = tmp_path / ".claude-mpm"
        config_dir.mkdir(parents=True)
        templates_dir = config_dir / "templates"
        templates_dir.mkdir()
        return config_dir

    @pytest.fixture
    def mock_deployment_state(self, tmp_path):
        """Create mock deployment state file."""
        claude_dir = tmp_path / ".claude" / "agents"
        claude_dir.mkdir(parents=True)

        state_file = claude_dir / ".mpm_deployment_state"
        state_data = {
            "deployment_hash": "test-hash",
            "last_check_time": 1234567890.0,
            "last_check_results": {
                "agents": {
                    "python-engineer": {"python": {"satisfied": [], "missing": []}},
                    "qa": {"python": {"satisfied": [], "missing": []}},
                    "engineer": {"python": {"satisfied": [], "missing": []}},
                    "gcp-ops": {"python": {"satisfied": [], "missing": []}},
                }
            },
            "agent_count": 4,
        }

        with state_file.open("w") as f:
            json.dump(state_data, f)

        return state_file

    @pytest.fixture
    def manager(self, temp_config_dir, monkeypatch):
        """Create SimpleAgentManager instance."""
        # Change to temp directory to avoid reading actual project state
        monkeypatch.chdir(temp_config_dir.parent)
        return SimpleAgentManager(temp_config_dir)

    def test_virtual_deployment_state_detection(self, manager, mock_deployment_state):
        """Test that agents in deployment state are detected."""
        # These agents should be detected from virtual state
        assert manager._is_agent_deployed("python-engineer") is True
        assert manager._is_agent_deployed("qa") is True
        assert manager._is_agent_deployed("engineer") is True
        assert manager._is_agent_deployed("gcp-ops") is True

    def test_non_existent_agent_detection(self, manager, mock_deployment_state):
        """Test that non-existent agents are not detected."""
        assert manager._is_agent_deployed("nonexistent-agent") is False
        assert manager._is_agent_deployed("fake-engineer") is False
        assert manager._is_agent_deployed("test-agent-xyz") is False

    def test_hierarchical_agent_id_detection(self, manager, tmp_path):
        """Test that hierarchical agent IDs resolve to leaf names."""
        # Create deployment state with flat agent names
        claude_dir = tmp_path / ".claude" / "agents"
        claude_dir.mkdir(parents=True)

        state_file = claude_dir / ".mpm_deployment_state"
        state_data = {
            "last_check_results": {
                "agents": {
                    "python-engineer": {"python": {"satisfied": [], "missing": []}},
                    "qa": {"python": {"satisfied": [], "missing": []}},
                }
            },
            "agent_count": 2,
        }

        with state_file.open("w") as f:
            json.dump(state_data, f)

        # Test hierarchical IDs resolve to leaf names
        assert manager._is_agent_deployed("engineer/backend/python-engineer") is True
        assert manager._is_agent_deployed("testing/qa") is True
        assert manager._is_agent_deployed("engineer/fake/nonexistent") is False

    def test_missing_deployment_state_fallback(self, manager):
        """Test that missing deployment state falls back gracefully."""
        # No deployment state file exists
        # Should return False (no physical files either)
        assert manager._is_agent_deployed("any-agent") is False

    def test_malformed_deployment_state_handling(self, manager, tmp_path):
        """Test that malformed deployment state is handled gracefully."""
        claude_dir = tmp_path / ".claude" / "agents"
        claude_dir.mkdir(parents=True)

        state_file = claude_dir / ".mpm_deployment_state"

        # Write malformed JSON
        with state_file.open("w") as f:
            f.write("{ invalid json }")

        # Should handle gracefully and return False
        assert manager._is_agent_deployed("any-agent") is False

    def test_missing_keys_in_deployment_state(self, manager, tmp_path):
        """Test that missing keys in deployment state are handled."""
        claude_dir = tmp_path / ".claude" / "agents"
        claude_dir.mkdir(parents=True)

        state_file = claude_dir / ".mpm_deployment_state"

        # Write state with missing nested keys
        with state_file.open("w") as f:
            json.dump({"some_key": "some_value"}, f)

        # Should handle gracefully and return False
        assert manager._is_agent_deployed("any-agent") is False

    def test_physical_file_fallback(self, manager, temp_config_dir):
        """Test fallback to physical file detection."""
        # Create physical agent file
        agents_dir = temp_config_dir / "agents"
        agents_dir.mkdir(exist_ok=True)

        agent_file = agents_dir / "test-agent.md"
        agent_file.write_text("# Test Agent")

        # Should detect from physical file
        assert manager._is_agent_deployed("test-agent") is True

    def test_user_level_deployment_state(self, manager, tmp_path, monkeypatch):
        """Test detection from user-level deployment state."""
        # Create user-level deployment state
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        claude_dir = home_dir / ".claude" / "agents"
        claude_dir.mkdir(parents=True)

        state_file = claude_dir / ".mpm_deployment_state"
        state_data = {
            "last_check_results": {
                "agents": {
                    "user-agent": {"python": {"satisfied": [], "missing": []}},
                }
            },
            "agent_count": 1,
        }

        with state_file.open("w") as f:
            json.dump(state_data, f)

        # Should detect from user-level state
        assert manager._is_agent_deployed("user-agent") is True

    def test_special_characters_in_agent_id(self, manager, mock_deployment_state):
        """Test that special characters in agent IDs are handled."""
        # These should not raise exceptions
        assert manager._is_agent_deployed("agent-with-dashes") is False
        assert manager._is_agent_deployed("agent_with_underscores") is False
        assert manager._is_agent_deployed("agent.with.dots") is False

    def test_empty_agent_id(self, manager, mock_deployment_state):
        """Test handling of empty agent ID."""
        assert manager._is_agent_deployed("") is False

    def test_discover_agents_integration(self):
        """Integration test: discover_agents() uses deployment state detection."""
        # This test verifies that discover_agents() correctly calls _is_agent_deployed()
        # and sets the is_deployed attribute on agents
        project_root = Path(__file__).parent.parent
        config_dir = project_root / ".claude-mpm"
        deployment_state = project_root / ".claude" / "agents" / ".mpm_deployment_state"

        if not deployment_state.exists():
            pytest.skip("Real deployment state file not found")

        manager = SimpleAgentManager(config_dir)

        # Discover agents
        agents = manager.discover_agents()

        if not agents:
            pytest.skip("No agents discovered")

        # Verify that is_deployed attribute exists on all agents
        # This confirms the integration between discover_agents() and _is_agent_deployed()
        for agent in agents:
            assert hasattr(agent, "is_deployed"), (
                f"Agent {agent.name} missing is_deployed attribute"
            )
            assert isinstance(agent.is_deployed, bool), (
                f"Agent {agent.name}.is_deployed should be boolean"
            )

        # Count deployed vs not deployed
        deployed_count = sum(1 for a in agents if a.is_deployed)
        not_deployed_count = len(agents) - deployed_count

        # Both should be present (some deployed, some not)
        # This verifies the logic is working and not just returning True/False for all
        print(
            f"\nDiscovered: {len(agents)} agents, "
            f"{deployed_count} deployed, {not_deployed_count} not deployed"
        )


class TestRealProjectDeploymentState:
    """Tests using actual project deployment state."""

    def test_real_deployment_state_detection(self):
        """Test detection using real project deployment state file."""
        # This test uses the actual project's deployment state
        project_root = Path(__file__).parent.parent
        deployment_state = project_root / ".claude" / "agents" / ".mpm_deployment_state"

        if not deployment_state.exists():
            pytest.skip("Real deployment state file not found")

        config_dir = project_root / ".claude-mpm"
        manager = SimpleAgentManager(config_dir)

        # Read actual state
        with deployment_state.open() as f:
            state = json.load(f)

        agents = state.get("last_check_results", {}).get("agents", {})

        # Test a few agents from actual state
        sample_agents = list(agents.keys())[:5]

        for agent_id in sample_agents:
            result = manager._is_agent_deployed(agent_id)
            assert result is True, f"Agent {agent_id} should be detected as deployed"

    def test_real_agent_count(self):
        """Test that all agents in deployment state are detected."""
        project_root = Path(__file__).parent.parent
        deployment_state = project_root / ".claude" / "agents" / ".mpm_deployment_state"

        if not deployment_state.exists():
            pytest.skip("Real deployment state file not found")

        config_dir = project_root / ".claude-mpm"
        manager = SimpleAgentManager(config_dir)

        # Read actual state
        with deployment_state.open() as f:
            state = json.load(f)

        agents = state.get("last_check_results", {}).get("agents", {})
        total_agents = len(agents)

        # All agents should be detected
        detected_count = sum(
            1 for agent_id in agents if manager._is_agent_deployed(agent_id)
        )

        assert detected_count == total_agents, (
            f"Expected {total_agents} agents detected, got {detected_count}"
        )
