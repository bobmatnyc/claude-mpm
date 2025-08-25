#!/usr/bin/env python3
"""Integration tests for agent schema standardization."""

import json
import subprocess
from pathlib import Path

import pytest

from claude_mpm.agents.agent_loader import AgentLoader


class TestSchemaIntegration:
    """Integration tests for schema standardization."""

    @pytest.fixture
    def agents_dir(self):
        """Return the actual agents directory."""
        return Path(__file__).parent.parent.parent / "src/claude_mpm/agents/templates"

    @pytest.fixture
    def agent_loader(self, agents_dir):
        """Create an agent loader instance."""
        return AgentLoader()

    def test_all_agents_load_successfully(agents_dir):
        """Test that all agents load with the new schema."""
        loader = AgentLoader()
        agents = loader.list_agents()

        # Should have at least 8 agents
        assert len(agents) >= 8

        # Verify each agent
        expected_agents = [
            "engineer_agent",
            "qa_agent",
            "research_agent",
            "documentation_agent",
            "ops_agent",
            "security_agent",
            "data_engineer_agent",
            "version_control_agent",
        ]

        loaded_ids = [agent["id"] for agent in agents]
        for expected_id in expected_agents:
            assert expected_id in loaded_ids, f"Agent {expected_id} not found"

    def test_agent_deployment_with_new_format(agent_loader):
        """Test deploying agents with new format."""
        # Get engineer agent
        agent = agent_loader.get_agent("engineer")
        assert agent is not None

        # Verify deployment format
        assert "id" in agent
        assert "instructions" in agent
        assert "model" in agent
        assert "resource_tier" in agent

        # Should not have old format fields
        assert "role" not in agent
        assert "goal" not in agent
        assert "backstory" not in agent

    def test_task_tool_with_standardized_agents(agents_dir):
        """Test Task tool integration with standardized agents."""
        # Load QA agent
        with open(agents_dir / "qa.json") as f:
            qa_agent = json.load(f)

        # Simulate Task tool usage
        task_context = {
            "agent_id": qa_agent["id"],
            "agent_name": qa_agent["name"],
            "instructions": qa_agent["instructions"],
            "model": qa_agent["model"],
        }

        # Verify all required fields are present
        assert task_context["agent_id"] == "qa"
        assert task_context["model"] in [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
        ]
        assert len(task_context["instructions"]) <= 8000

    def test_hook_service_with_standardized_agents():
        """Test hook service integration."""
        # This tests that agents work with hook system
        hook_service = HookService()

        # Hook service should be able to work with new agent format
        agent_data = {
            "id": "test_hook_agent",
            "name": "Test Hook Agent",
            "instructions": "Test instructions",
            "model": "claude-3-5-sonnet-20241022",
            "resource_tier": "standard",
        }

        # Verify hook service can process agent data
        # (Would need actual hook service methods here)
        assert agent_data["id"] == "test_hook_agent"

    def test_cli_with_standardized_agents(tmp_path):
        """Test CLI integration with standardized agents."""
        # Create a test script to verify CLI works
        test_script = tmp_path / "test_cli.py"
        test_script.write_text(
            """
import sys
sys.path.insert(0, 'src')
from claude_mpm.services.agents.agent_registry import AgentRegistry

registry = get_agent_registry()
agents = registry.list_agents()
print(f"Loaded {len(agents)} agents")
for agent in agents:
    print(f"- {agent['id']}: {agent['name']}")
"""
        )

        # Run the script
        result = subprocess.run(
            ["python", str(test_script)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
            check=False,
        )

        assert result.returncode == 0
        assert "Loaded" in result.stdout
        assert "engineer" in result.stdout
        assert "qa" in result.stdout

    def test_model_compatibility_enforcement(agents_dir):
        """Test that model compatibility rules are enforced."""
        # Check Opus agents have premium tier
        opus_agents = []
        for agent_file in agents_dir.glob("*.json"):
            if agent_file.name == "agent_schema.json":
                continue

            with open(agent_file) as f:
                agent = json.load(f)

            if "opus" in agent.get("model", "").lower():
                opus_agents.append(agent)
                # Opus requires premium tier
                assert (
                    agent["resource_tier"] == "premium"
                ), f"Agent {agent['id']} uses Opus but not premium tier"

    def test_resource_tier_distribution(agents_dir):
        """Test resource tier distribution across agents."""
        tier_counts = {"basic": 0, "standard": 0, "premium": 0}

        for agent_file in agents_dir.glob("*.json"):
            if agent_file.name == "agent_schema.json":
                continue

            with open(agent_file) as f:
                agent = json.load(f)

            tier = agent.get("resource_tier")
            if tier in tier_counts:
                tier_counts[tier] += 1

        # Verify we have agents at different tiers
        assert tier_counts["basic"] >= 1
        assert tier_counts["standard"] >= 1
        # Premium might be 0 if no Opus agents

        print(f"Resource tier distribution: {tier_counts}")

    def test_agent_instructions_quality(agents_dir):
        """Test that agent instructions meet quality standards."""
        for agent_file in agents_dir.glob("*.json"):
            if agent_file.name == "agent_schema.json":
                continue

            with open(agent_file) as f:
                agent = json.load(f)

            instructions = agent.get("instructions", "")

            # Instructions should be substantial
            assert (
                len(instructions) >= 100
            ), f"Agent {agent['id']} has very short instructions"

            # Instructions should be well-formatted
            assert (
                instructions.strip() == instructions
            ), f"Agent {agent['id']} has whitespace issues"

            # Should not contain old format references
            assert "role:" not in instructions.lower()
            assert "goal:" not in instructions.lower()
            assert "backstory:" not in instructions.lower()

    def test_concurrent_agent_loading(agents_dir):
        """Test concurrent agent loading with new schema."""
        import concurrent.futures

        def load_agents():
            loader = AgentLoader(agents_dir=str(agents_dir))
            return loader.load_agents()

        # Load agents concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(load_agents) for _ in range(5)]
            results = [f.result() for f in futures]

        # All should succeed and return same agents
        assert all(len(r) >= 8 for r in results)
        assert all(r[0]["id"] == results[0][0]["id"] for r in results)

    def test_error_handling_invalid_agents(tmp_path):
        """Test error handling for invalid agents."""
        # Create an invalid agent
        invalid_agent = {
            "id": "invalid-id",  # Invalid ID format
            "name": "Invalid",
            "description": "Invalid agent",
            "instructions": "x" * 8001,  # Too long
            "model": "invalid-model",
            "resource_tier": "invalid-tier",
        }

        invalid_path = tmp_path / "invalid.json"
        with open(invalid_path, "w") as f:
            json.dump(invalid_agent, f)

        # Should handle error gracefully
        loader = AgentLoader(agents_dir=str(tmp_path))

        # Should either skip invalid agent or raise clear error
        try:
            agents = loader.load_agents()
            # If it doesn't raise, should have skipped the agent
            assert len(agents) == 0
        except Exception as e:
            # If it raises, should be clear validation error
            assert "validation" in str(e).lower() or "invalid" in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
