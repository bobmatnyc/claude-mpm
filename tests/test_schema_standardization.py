#!/usr/bin/env python3
"""Comprehensive test suite for agent schema standardization."""

import json
import time
from pathlib import Path

import pytest

from claude_mpm.agents.agent_loader import AgentLoader
from claude_mpm.hooks.validation_hooks import ValidationError
from claude_mpm.services.agents.registry import AgentRegistry


class TestSchemaStandardization:
    """Test suite for agent schema standardization implementation."""

    @pytest.fixture
    def test_agents_dir(self):
        """Create a temporary agents directory for testing."""
        agents_dir = self / "agents"
        agents_dir.mkdir()
        return agents_dir

    @pytest.fixture
    def schema_path(self):
        """Return path to the agent schema."""
        return (
            Path(__file__).parent.parent
            / "src/claude_mpm/agents/schema/agent_schema.json"
        )

    @pytest.fixture
    def agent_loader(self, test_agents_dir):
        """Create an AgentLoader instance for testing."""
        return AgentLoader(agents_dir=str(test_agents_dir))

    def test_schema_file_exists(self):
        """Test that the schema file exists and is valid JSON."""
        assert self.exists(), f"Schema file not found at {self}"

        with self.open() as f:
            schema = json.load(f)

        # Verify schema structure
        assert schema.get("$schema") == "http://json-schema.org/draft-07/schema#"
        assert schema.get("type") == "object"
        assert "properties" in schema
        assert "required" in schema

    def test_schema_required_fields(self):
        """Test that schema defines all required fields."""
        with self.open() as f:
            schema = json.load(f)

        required_fields = [
            "schema_version",
            "agent_id",
            "agent_version",
            "agent_type",
            "metadata",
            "capabilities",
            "instructions",
        ]
        assert set(schema["required"]) == set(required_fields)

        # Verify property definitions
        props = schema["properties"]
        assert "agent_id" in props
        assert props["agent_id"]["pattern"] == "^[a-z][a-z0-9_]*$"

        assert "instructions" in props
        assert "content" in props["instructions"]["properties"]

    def test_valid_agent_passes_validation(self):
        """Test that a valid agent passes validation."""
        valid_agent = {
            "id": "test_engineer",
            "name": "Test Engineer",
            "description": "A test engineering agent",
            "instructions": "Test instructions for the agent",
            "model": "claude-3-5-sonnet-20241022",
            "resource_tier": "standard",
            "capabilities": ["code_review", "testing"],
            "constraints": ["no_prod_access"],
            "examples": [],
        }

        # Should not raise
        self._validate_agent(valid_agent)

    def test_invalid_agent_fails_validation(self):
        """Test that invalid agents fail validation."""
        # Missing required field
        invalid_agent = {
            "id": "test",
            "name": "Test",
            "description": "Test",
            # Missing instructions, model, resource_tier
        }

        with pytest.raises(ValidationError):
            self._validate_agent(invalid_agent)

        # Invalid ID format
        invalid_agent = {
            "id": "test-agent",  # Contains hyphen
            "name": "Test",
            "description": "Test",
            "instructions": "Test",
            "model": "claude-3-5-sonnet-20241022",
            "resource_tier": "standard",
        }

        with pytest.raises(ValidationError):
            self._validate_agent(invalid_agent)

    def test_instructions_length_limit(self):
        """Test that instructions are limited to 8000 characters."""
        agent = {
            "id": "test",
            "name": "Test",
            "description": "Test",
            "instructions": "x" * 8001,  # Exceeds limit
            "model": "claude-3-5-sonnet-20241022",
            "resource_tier": "standard",
        }

        with pytest.raises(ValidationError) as exc_info:
            self._validate_agent(agent)

        assert "8000 characters" in str(exc_info.value)

    def test_resource_tier_validation(self):
        """Test resource tier validation."""
        agent = {
            "id": "test",
            "name": "Test",
            "description": "Test",
            "instructions": "Test",
            "model": "claude-3-5-sonnet-20241022",
            "resource_tier": "invalid_tier",
        }

        with pytest.raises(ValidationError) as exc_info:
            self._validate_agent(agent)

        assert "resource_tier" in str(exc_info.value)

    def test_model_resource_tier_compatibility(self):
        """Test model and resource tier compatibility rules."""
        # Opus model requires premium tier
        agent = {
            "id": "test",
            "name": "Test",
            "description": "Test",
            "instructions": "Test",
            "model": "claude-3-opus-20240229",
            "resource_tier": "basic",  # Should be premium
        }

        with pytest.raises(ValidationError) as exc_info:
            self._validate_agent(agent)

        assert "opus" in str(exc_info.value).lower()
        assert "premium" in str(exc_info.value).lower()

    def test_migrated_agents_format():
        """Test that all migrated agents follow the new format."""
        agents_dir = Path(__file__).parent.parent / "src/claude_mpm/agents/templates"

        agent_files = [
            "engineer.json",
            "qa.json",
            "research.json",
            "documentation.json",
            "ops.json",
            "security.json",
            "data_engineer.json",
            "version_control.json",
        ]

        for agent_file in agent_files:
            agent_path = agents_dir / agent_file
            assert agent_path.exists(), f"Agent file {agent_file} not found"

            with agent_path.open() as f:
                agent = json.load(f)

            # Verify clean ID (no _agent suffix)
            assert not agent["id"].endswith("_agent"), (
                f"Agent {agent_file} has _agent suffix"
            )

            # Verify all required fields
            required = [
                "id",
                "name",
                "description",
                "instructions",
                "model",
                "resource_tier",
            ]
            for field in required:
                assert field in agent, f"Agent {agent_file} missing {field}"

            # Verify resource tier is valid
            assert agent["resource_tier"] in ["basic", "standard", "premium"]

            # Verify instructions length
            assert len(agent["instructions"]) <= 8000

    def test_backup_files_created():
        """Test that backup files were created during migration."""
        backup_dir = (
            Path(__file__).parent.parent / "src/claude_mpm/agents/templates/backup"
        )

        if backup_dir.exists():
            backup_files = list(backup_dir.glob("*_agent_*.json"))
            assert len(backup_files) >= 8, "Not all backup files found"

            # Verify backup file format
            for backup_file in backup_files:
                assert "_agent_" in backup_file.name
                assert backup_file.name.endswith(".json")

    def test_agent_loader_with_new_schema(self):
        """Test agent loader with new schema format."""
        # Create a test agent
        test_agent = {
            "id": "test_agent",
            "name": "Test Agent",
            "description": "A test agent",
            "instructions": "Test instructions",
            "model": "claude-3-5-sonnet-20241022",
            "resource_tier": "standard",
        }

        agent_path = self / "test_agent.json"
        with agent_path.open("w") as f:
            json.dump(test_agent, f)

        # Load agent
        loader = AgentLoader(agents_dir=str(self))
        agents = loader.load_agents()

        assert len(agents) == 1
        assert agents[0]["id"] == "test_agent"

    def test_agent_loader_rejects_old_format(self):
        """Test that agent loader rejects old format."""
        # Create an old format agent
        old_agent = {
            "id": "test_agent",
            "name": "Test Agent",
            "role": "Test role",  # Old format field
            "goal": "Test goal",  # Old format field
            "backstory": "Test backstory",  # Old format field
        }

        agent_path = self / "test_agent.json"
        with agent_path.open("w") as f:
            json.dump(old_agent, f)

        # Should fail to load
        loader = AgentLoader(agents_dir=str(self))
        with pytest.raises(ValidationError):
            loader.load_agents()

    def test_performance_agent_loading(self):
        """Test agent loading performance."""
        # Create multiple test agents
        for i in range(10):
            agent = {
                "id": f"test_agent_{i}",
                "name": f"Test Agent {i}",
                "description": f"Test agent {i}",
                "instructions": f"Instructions for agent {i}",
                "model": "claude-3-5-sonnet-20241022",
                "resource_tier": "standard",
            }

            with open(self / f"agent_{i}.json", "w") as f:
                json.dump(agent, f)

        loader = AgentLoader(agents_dir=str(self))

        # Measure loading time
        start_time = time.time()
        agents = loader.load_agents()
        load_time = time.time() - start_time

        assert len(agents) == 10
        # Should load in under 500ms total (50ms per agent)
        assert load_time < 0.5, f"Loading took {load_time:.3f}s, expected < 0.5s"

    def test_agent_registry_integration(self):
        """Test integration with AgentRegistry."""
        # Create a test agent
        test_agent = {
            "id": "registry_test",
            "name": "Registry Test",
            "description": "Test agent for registry",
            "instructions": "Test instructions",
            "model": "claude-3-5-sonnet-20241022",
            "resource_tier": "standard",
        }

        with open(self / "registry_test.json", "w") as f:
            json.dump(test_agent, f)

        # Test with registry
        registry = AgentRegistry(agents_dir=str(self))

        # Should find the agent
        assert registry.get_agent("registry_test") is not None
        assert registry.get_agent("registry_test")["id"] == "registry_test"

        # List agents
        agents = registry.list_agents()
        assert len(agents) == 1
        assert agents[0]["id"] == "registry_test"

    def test_task_tool_compatibility():
        """Test that agents work with Task tool."""
        # This would require actual Task tool integration
        # For now, verify agent format is compatible
        agents_dir = Path(__file__).parent.parent / "src/claude_mpm/agents/templates"

        with open(agents_dir / "engineer.json") as f:
            engineer = json.load(f)

        # Verify format expected by Task tool
        assert "id" in engineer
        assert "name" in engineer
        assert "instructions" in engineer
        assert isinstance(engineer["instructions"], str)

    def test_hook_system_compatibility():
        """Test compatibility with hook system."""
        # Verify agents can be used in hook context
        agents_dir = Path(__file__).parent.parent / "src/claude_mpm/agents/templates"

        with open(agents_dir / "qa.json") as f:
            qa_agent = json.load(f)

        # Hook system expects certain fields
        assert "id" in qa_agent
        assert "name" in qa_agent
        assert "instructions" in qa_agent

    def test_backward_compatibility_removed(self):
        """Test that backward compatibility is properly removed."""
        # Old format should not work
        old_agent = {
            "role": "Engineer",
            "goal": "Build software",
            "backstory": "Experienced engineer",
        }

        with pytest.raises(ValidationError):
            self._validate_agent(old_agent)

    def test_cache_functionality(self):
        """Test agent loader caching."""
        # Create test agent
        test_agent = {
            "id": "cache_test",
            "name": "Cache Test",
            "description": "Test caching",
            "instructions": "Test",
            "model": "claude-3-5-sonnet-20241022",
            "resource_tier": "standard",
        }

        with open(self / "cache_test.json", "w") as f:
            json.dump(test_agent, f)

        loader = AgentLoader(agents_dir=str(self))

        # First load
        agents1 = loader.load_agents()

        # Second load should use cache
        agents2 = loader.load_agents()

        assert agents1 == agents2

        # Modify file
        test_agent["name"] = "Modified"
        with open(self / "cache_test.json", "w") as f:
            json.dump(test_agent, f)

        # Should detect change and reload
        agents3 = loader.load_agents()
        assert agents3[0]["name"] == "Modified"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
