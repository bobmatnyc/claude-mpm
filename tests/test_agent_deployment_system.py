"""
Test agent deployment system.

This test suite validates the agent deployment service, including version
field generation, base_version inclusion, and proper agent filtering.
"""

import json
import os
import sys
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from claude_mpm.services.agents.deployment import AgentDeploymentService


class TestAgentDeployment:
    """Test the agent deployment service."""

    @pytest.fixture
    def deployment_service(self, tmp_path):
        """Create a deployment service with test templates."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        base_agent_path = tmp_path / "base_agent.json"
        base_agent = {
            "base_version": "1.0.0",
            "narrative_fields": {"instructions": "Base instructions for all agents."},
        }
        base_agent_path.write_text(json.dumps(base_agent))

        return AgentDeploymentService(templates_dir, base_agent_path)

    def test_version_field_generation_semantic(self, tmp_path):
        """Test that semantic version format is generated correctly."""
        # Create test agent template
        templates_dir = tmp_path / "templates"
        agent_template = {
            "agent_version": "2.1.0",
            "metadata": {"description": "Test agent"},
            "capabilities": {"tools": ["Read", "Write"], "model": "sonnet"},
            "instructions": "Test instructions",
        }

        template_file = templates_dir / "test_agent.json"
        template_file.write_text(json.dumps(agent_template))

        # Deploy agents
        target_dir = tmp_path / "deployed"
        self.deploy_agents(target_dir)

        # Check deployed agent
        deployed_file = target_dir / "test_agent.md"
        assert deployed_file.exists()

        content = deployed_file.read_text()
        assert "version: 2.1.0" in content
        assert "base_version: 1.0.0" in content

    def test_base_version_field_inclusion(self, tmp_path):
        """Test that base_version field is always included."""
        templates_dir = tmp_path / "templates"

        # Create multiple test agents
        for i in range(3):
            agent_template = {
                "agent_version": f"1.{i}.0",
                "metadata": {"description": f"Agent {i}"},
                "capabilities": {"tools": ["Read"], "model": "sonnet"},
                "instructions": f"Instructions for agent {i}",
            }

            template_file = templates_dir / f"agent_{i}.json"
            template_file.write_text(json.dumps(agent_template))

        # Deploy
        target_dir = tmp_path / "deployed"
        self.deploy_agents(target_dir)

        # Verify all agents have base_version
        for i in range(3):
            deployed_file = target_dir / f"agent_{i}.md"
            content = deployed_file.read_text()
            assert "base_version: 1.0.0" in content

    def test_agent_count_exactly_ten(self, tmp_path):
        """Test that exactly 10 agents are deployed (excluding filtered files)."""
        templates_dir = tmp_path / "templates"

        # Create exactly 10 valid agent templates
        agent_names = [
            "engineer",
            "qa",
            "documentation",
            "research",
            "security",
            "ops",
            "data_engineer",
            "version_control",
            "test_integration",
            "pm",
        ]

        for name in agent_names:
            agent_template = {
                "agent_version": "1.0.0",
                "metadata": {"description": f"{name} agent"},
                "capabilities": {"tools": ["Read", "Write"], "model": "sonnet"},
                "instructions": f"Instructions for {name}",
            }

            template_file = templates_dir / f"{name}.json"
            template_file.write_text(json.dumps(agent_template))

        # Also create files that should be filtered out
        (templates_dir / "__init__.json").write_text("{}")
        (templates_dir / ".hidden.json").write_text("{}")
        (templates_dir / "MEMORIES.json").write_text("{}")
        (templates_dir / "TODOWRITE.json").write_text("{}")

        # Deploy
        target_dir = tmp_path / "deployed"
        results = self.deploy_agents(target_dir)

        # Should deploy exactly 10 agents
        assert len(results["deployed"]) == 10
        assert results["total"] == 10

        # Verify the filtered files were not deployed
        assert not (target_dir / "__init__.md").exists()
        assert not (target_dir / ".hidden.md").exists()
        assert not (target_dir / "MEMORIES.md").exists()
        assert not (target_dir / "TODOWRITE.md").exists()

    def test_filtering_non_agent_files(self, tmp_path):
        """Test that non-agent files are properly filtered."""
        templates_dir = tmp_path / "templates"

        # Create valid agent
        valid_agent = {
            "agent_version": "1.0.0",
            "metadata": {"description": "Valid agent"},
            "capabilities": {"tools": ["Read"], "model": "sonnet"},
            "instructions": "Valid instructions",
        }
        (templates_dir / "valid_agent.json").write_text(json.dumps(valid_agent))

        # Create files that should be filtered
        files_to_filter = [
            "__init__.json",
            ".DS_Store.json",
            ".gitignore.json",
            "README.json",
            "INSTRUCTIONS.json",
            "MEMORIES.json",
            "TODOWRITE.json",
        ]

        for filename in files_to_filter:
            (templates_dir / filename).write_text("{}")

        # Deploy
        target_dir = tmp_path / "deployed"
        results = self.deploy_agents(target_dir)

        # Only valid_agent should be deployed
        assert len(results["deployed"]) == 1
        assert results["deployed"][0]["name"] == "valid_agent"

        # Filtered files should not exist in target
        for filename in files_to_filter:
            md_name = filename.replace(".json", ".md")
            assert not (target_dir / md_name).exists()

    def test_version_migration_detection(self, tmp_path):
        """Test detection and migration from old version formats."""
        templates_dir = tmp_path / "templates"
        target_dir = tmp_path / "deployed"
        target_dir.mkdir()

        # Create an agent with old version format already deployed
        old_agent_content = """---
name: test_agent
description: Test agent
version: 0002-0005
tools: Read, Write
model: sonnet
author: claude-mpm
---

Old agent content
"""
        old_agent_file = target_dir / "test_agent.md"
        old_agent_file.write_text(old_agent_content)

        # Create new template with semantic version
        new_template = {
            "agent_version": "2.5.0",
            "metadata": {"description": "Updated test agent"},
            "capabilities": {"tools": ["Read", "Write"], "model": "sonnet"},
            "instructions": "New agent content",
        }
        (templates_dir / "test_agent.json").write_text(json.dumps(new_template))

        # Deploy (should detect migration needed)
        results = self.deploy_agents(target_dir)

        # Check migration occurred
        assert len(results["migrated"]) == 1
        assert results["migrated"][0]["name"] == "test_agent"
        assert "migration needed" in results["migrated"][0]["reason"]

        # Verify new version format
        updated_content = old_agent_file.read_text()
        assert "version: 2.5.0" in updated_content
        assert "0002-0005" not in updated_content

    def test_force_rebuild_option(self, tmp_path):
        """Test that force_rebuild bypasses version checking."""
        templates_dir = tmp_path / "templates"
        target_dir = tmp_path / "deployed"

        # Create and deploy initial agent
        template = {
            "agent_version": "1.0.0",
            "metadata": {"description": "Test agent"},
            "capabilities": {"tools": ["Read"], "model": "sonnet"},
            "instructions": "Initial content",
        }
        (templates_dir / "test_agent.json").write_text(json.dumps(template))

        # First deployment
        results1 = self.deploy_agents(target_dir)
        assert len(results1["deployed"]) == 1

        # Second deployment without force (should skip)
        results2 = self.deploy_agents(target_dir, force_rebuild=False)
        assert len(results2["skipped"]) == 1
        assert len(results2["deployed"]) == 0

        # Third deployment with force (should update)
        results3 = self.deploy_agents(target_dir, force_rebuild=True)
        assert len(results3["updated"]) == 1
        assert len(results3["skipped"]) == 0

    def test_metadata_field_extraction(self, tmp_path):
        """Test extraction of metadata fields from templates."""
        templates_dir = tmp_path / "templates"

        # Create agent with full metadata
        template = {
            "agent_version": "3.2.1",
            "metadata": {
                "name": "Research Agent",
                "description": "Advanced research and analysis",
                "tags": ["research", "analysis", "ai"],
                "category": "analysis",
                "specializations": ["code-analysis", "documentation"],
            },
            "capabilities": {
                "tools": ["Read", "Grep", "WebSearch"],
                "model": "opus",
                "temperature": 0.3,
                "max_tokens": 8192,
            },
            "instructions": "Research agent instructions",
        }
        (templates_dir / "research.json").write_text(json.dumps(template))

        # Deploy
        target_dir = tmp_path / "deployed"
        self.deploy_agents(target_dir)

        # Check deployed content
        deployed_file = target_dir / "research.md"
        content = deployed_file.read_text()

        # Verify metadata is properly included
        assert "name: research" in content
        assert "description: Advanced research and analysis" in content
        assert "version: 3.2.1" in content
        assert "tools: Read, Grep, WebSearch" in content
        assert "model: opus" in content

    def test_deployment_metrics_collection(self, tmp_path):
        """Test that deployment metrics are properly collected."""
        templates_dir = tmp_path / "templates"

        # Create multiple agents
        for i in range(5):
            template = {
                "agent_version": f"1.{i}.0",
                "metadata": {"description": f"Agent {i}"},
                "capabilities": {"tools": ["Read"], "model": "sonnet"},
                "instructions": f"Agent {i} instructions",
            }
            (templates_dir / f"agent_{i}.json").write_text(json.dumps(template))

        # Deploy
        target_dir = tmp_path / "deployed"
        results = self.deploy_agents(target_dir)

        # Check metrics in results
        assert "metrics" in results
        metrics = results["metrics"]

        assert "start_time" in metrics
        assert "end_time" in metrics
        assert "duration_ms" in metrics
        assert metrics["duration_ms"] > 0

        assert "agent_timings" in metrics
        assert len(metrics["agent_timings"]) == 5

        # Get service metrics
        service_metrics = self.get_deployment_metrics()
        assert service_metrics["total_deployments"] == 1
        assert service_metrics["successful_deployments"] == 1

    def test_yaml_to_md_conversion(self, tmp_path):
        """Test conversion of existing YAML files to MD format."""
        target_dir = tmp_path / "deployed"
        target_dir.mkdir()

        # Create old YAML format agent file
        yaml_content = """---
name: old_agent
description: "Old format agent"
version: "1.0.0"
tools: ["Read", "Write"]
---

Agent instructions in YAML format.
"""
        yaml_file = target_dir / "old_agent.yaml"
        yaml_file.write_text(yaml_content)

        # Create corresponding template
        templates_dir = tmp_path / "templates"
        template = {
            "agent_version": "1.0.0",
            "metadata": {"description": "Old format agent"},
            "capabilities": {"tools": ["Read", "Write"], "model": "sonnet"},
            "instructions": "Updated instructions",
        }
        (templates_dir / "old_agent.json").write_text(json.dumps(template))

        # Deploy (should convert YAML to MD)
        results = self.deploy_agents(target_dir)

        # Check conversion
        assert len(results["converted"]) == 1
        assert results["converted"][0]["agent"] == "old_agent"

        # Verify MD file exists and YAML is backed up
        assert (target_dir / "old_agent.md").exists()
        assert (target_dir / "old_agent.yaml.backup").exists()
        assert not yaml_file.exists()  # Original should be removed

    def test_error_handling_invalid_template(self, tmp_path):
        """Test error handling for invalid agent templates."""
        templates_dir = tmp_path / "templates"

        # Create template with missing fields (will use defaults)
        minimal_template = {
            "metadata": {"description": "Minimal agent"}
            # Missing agent_version, capabilities, instructions - will use defaults
        }
        (templates_dir / "minimal_agent.json").write_text(json.dumps(minimal_template))

        # Create valid template
        valid_template = {
            "agent_version": "1.0.0",
            "metadata": {"description": "Valid agent"},
            "capabilities": {"tools": ["Read"], "model": "sonnet"},
            "instructions": "Valid instructions",
        }
        (templates_dir / "valid_agent.json").write_text(json.dumps(valid_template))

        # Create truly invalid template (malformed JSON)
        (templates_dir / "invalid_agent.json").write_text("{invalid json}")

        # Deploy
        target_dir = tmp_path / "deployed"
        results = self.deploy_agents(target_dir)

        # Both minimal and valid should deploy, invalid JSON should error
        assert len(results["deployed"]) == 2
        assert {r["name"] for r in results["deployed"]} == {
            "minimal_agent",
            "valid_agent",
        }
        assert len(results["errors"]) == 1
        assert "invalid_agent" in results["errors"][0]

    def test_environment_variable_setup(self):
        """Test setting of Claude environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            env_vars = self.set_claude_environment()

            # Check required environment variables
            assert "CLAUDE_CONFIG_DIR" in env_vars
            assert "CLAUDE_MAX_PARALLEL_SUBAGENTS" in env_vars
            assert "CLAUDE_TIMEOUT" in env_vars

            # Verify they're set in os.environ
            assert os.environ.get("CLAUDE_CONFIG_DIR") is not None
            assert os.environ.get("CLAUDE_MAX_PARALLEL_SUBAGENTS") == "10"
            assert os.environ.get("CLAUDE_TIMEOUT") == "600000"

    def test_deployment_verification(self, tmp_path):
        """Test post-deployment verification."""
        templates_dir = tmp_path / "templates"
        target_dir = tmp_path / ".claude"
        agents_dir = target_dir / "agents"

        # Create and deploy agents
        for name in ["agent1", "agent2"]:
            template = {
                "agent_version": "1.0.0",
                "metadata": {"description": f"{name} description"},
                "capabilities": {"tools": ["Read"], "model": "sonnet"},
                "instructions": f"{name} instructions",
            }
            (templates_dir / f"{name}.json").write_text(json.dumps(template))

        self.deploy_agents(agents_dir)

        # Set environment variables for verification
        self.set_claude_environment(target_dir)

        # Verify deployment
        verification = self.verify_deployment(target_dir)

        assert len(verification["agents_found"]) == 2
        assert len(verification["warnings"]) == 0
        assert len(verification["agents_needing_migration"]) == 0

        # Check agent details
        agent_names = [a["name"] for a in verification["agents_found"]]
        assert "agent1" in agent_names
        assert "agent2" in agent_names
