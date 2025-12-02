#!/usr/bin/env python3
"""
Tests for UnifiedAgentRegistry to ensure correct agent counting and tier precedence.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from claude_mpm.core.unified_agent_registry import AgentTier, UnifiedAgentRegistry


class TestUnifiedAgentRegistry(unittest.TestCase):
    """Test suite for UnifiedAgentRegistry."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # Create mock directory structure
        self.system_dir = self.temp_path / "system"
        self.system_dir.mkdir()
        self.user_dir = self.temp_path / "user"
        self.user_dir.mkdir()
        self.project_dir = self.temp_path / "project"
        self.project_dir.mkdir()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_duplicate_agent_tier_precedence(self):
        """Test that duplicate agents are correctly resolved by tier precedence."""
        # Create duplicate agents in different tiers
        agents = ["agent1", "agent2", "agent3"]

        # Create system tier agents
        for agent in agents:
            (self.system_dir / f"{agent}.md").write_text(f"# System {agent}")

        # Create user tier agents (overlapping with system)
        for agent in agents[:2]:  # Only agent1 and agent2
            (self.user_dir / f"{agent}.md").write_text(f"# User {agent}")

        # Create project tier agent (overlapping with others)
        (self.project_dir / "agent1.md").write_text("# Project agent1")

        # Mock the path manager
        mock_path_manager = MagicMock()
        mock_path_manager.get_project_agents_dir.return_value = self.project_dir
        mock_path_manager.get_user_agents_dir.return_value = self.user_dir
        mock_path_manager.get_system_agents_dir.return_value = self.system_dir
        mock_path_manager.get_templates_dir.return_value = self.temp_path / "templates"
        mock_path_manager.get_memories_dir.return_value = self.temp_path / "memories"

        with patch(
            "claude_mpm.core.unified_agent_registry.get_path_manager",
            return_value=mock_path_manager,
        ):
            registry = UnifiedAgentRegistry(cache_enabled=False)
            agents_dict = registry.discover_agents(force_refresh=True)

            # Should have exactly 3 unique agents
            self.assertEqual(len(agents_dict), 3)
            self.assertIn("agent1", agents_dict)
            self.assertIn("agent2", agents_dict)
            self.assertIn("agent3", agents_dict)

            # Check tier precedence
            # agent1 should be from project tier (highest precedence)
            self.assertEqual(agents_dict["agent1"].tier, AgentTier.PROJECT)
            # agent2 should be from user tier (no project version)
            self.assertEqual(agents_dict["agent2"].tier, AgentTier.USER)
            # agent3 should be from system tier (no user or project version)
            self.assertEqual(agents_dict["agent3"].tier, AgentTier.SYSTEM)

    def test_no_double_counting_with_templates(self):
        """Test that agents aren't double-counted when templates exist."""
        # Create agents with same names in different directories
        agent_names = [f"agent_{i}" for i in range(20)]

        # Create system/template agents
        templates_dir = self.system_dir / "templates"
        templates_dir.mkdir()
        for name in agent_names:
            (templates_dir / f"{name}.json").write_text(f'{{"name": "{name}"}}')

        # Create user agents (overlapping)
        for name in agent_names[:18]:  # 18 of the 20
            (self.user_dir / f"{name}.md").write_text(f"# {name}")

        # Mock the path manager
        mock_path_manager = MagicMock()
        mock_path_manager.get_project_agents_dir.return_value = self.project_dir
        mock_path_manager.get_user_agents_dir.return_value = self.user_dir
        mock_path_manager.get_system_agents_dir.return_value = self.system_dir
        mock_path_manager.get_templates_dir.return_value = templates_dir
        mock_path_manager.get_memories_dir.return_value = self.temp_path / "memories"

        with patch(
            "claude_mpm.core.unified_agent_registry.get_path_manager",
            return_value=mock_path_manager,
        ):
            registry = UnifiedAgentRegistry(cache_enabled=False)
            agents_dict = registry.discover_agents(force_refresh=True)

            # Should have exactly 20 unique agents (not 38)
            self.assertEqual(len(agents_dict), 20)

            # Check that user agents take precedence over templates
            user_agents = [a for a in agents_dict.values() if a.tier == AgentTier.USER]
            system_agents = [
                a for a in agents_dict.values() if a.tier == AgentTier.SYSTEM
            ]

            self.assertEqual(len(user_agents), 18)
            self.assertEqual(len(system_agents), 2)

    def test_registry_stats_accuracy(self):
        """Test that registry stats report correct counts."""
        # Create a simple set of agents
        for i in range(5):
            (self.user_dir / f"agent_{i}.md").write_text(f"# Agent {i}")

        mock_path_manager = MagicMock()
        mock_path_manager.get_project_agents_dir.return_value = self.project_dir
        mock_path_manager.get_user_agents_dir.return_value = self.user_dir
        mock_path_manager.get_system_agents_dir.return_value = self.system_dir
        mock_path_manager.get_templates_dir.return_value = self.temp_path / "templates"
        mock_path_manager.get_memories_dir.return_value = self.temp_path / "memories"

        with patch(
            "claude_mpm.core.unified_agent_registry.get_path_manager",
            return_value=mock_path_manager,
        ):
            registry = UnifiedAgentRegistry(cache_enabled=False)
            agents_dict = registry.discover_agents(force_refresh=True)

            stats = registry.get_registry_stats()

            # Stats should match actual registry
            self.assertEqual(stats["total_agents"], 5)
            self.assertEqual(stats["total_discovered"], 5)
            self.assertEqual(len(agents_dict), 5)


if __name__ == "__main__":
    unittest.main()
