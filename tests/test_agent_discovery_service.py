#!/usr/bin/env python3
"""
Tests for AgentDiscoveryService
==============================

Comprehensive test suite for the extracted AgentDiscoveryService.
Tests all agent discovery, filtering, and metadata extraction functionality.
"""

import json
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment.agent_discovery_service import (
    AgentDiscoveryService,
)


class TestAgentDiscoveryService:
    """Test suite for AgentDiscoveryService."""

    @pytest.fixture
    def temp_templates_dir(self):
        """Create temporary templates directory with test files."""
        with tmp_path as temp_dir:
            templates_dir = Path(temp_dir) / "templates"
            templates_dir.mkdir()

            # Create test template files using the new schema format
            test_templates = [
                {
                    "schema_version": "1.2.0",
                    "agent_id": "test-agent",
                    "agent_version": "1.0.0",
                    "agent_type": "qa",
                    "metadata": {
                        "name": "test-agent",
                        "description": "Test agent for testing",
                        "tags": ["testing"],
                        "category": "quality",
                        "author": "Test Author",
                    },
                    "capabilities": {"model": "sonnet", "tools": ["Read", "Write"]},
                    "instructions": {"system_prompt": "You are a test agent."},
                },
                {
                    "schema_version": "1.2.0",
                    "agent_id": "qa-agent",
                    "agent_version": "2.1.0",
                    "agent_type": "qa",
                    "metadata": {
                        "name": "qa-agent",
                        "description": "QA agent for quality assurance",
                        "tags": ["qa", "testing"],
                        "category": "quality",
                        "author": "Test Author",
                    },
                    "capabilities": {
                        "model": "haiku",
                        "tools": ["Read", "Write", "Test"],
                    },
                    "instructions": {"system_prompt": "You are a QA agent."},
                },
                {
                    "schema_version": "1.2.0",
                    "agent_id": "security-agent",
                    "agent_version": "1.5.0",
                    "agent_type": "security",
                    "metadata": {
                        "name": "security-agent",
                        "description": "Security analysis agent",
                        "tags": ["security"],
                        "category": "specialized",
                        "author": "Test Author",
                    },
                    "capabilities": {"model": "sonnet", "tools": ["Read", "Analyze"]},
                    "instructions": {"system_prompt": "You are a security agent."},
                },
            ]

            for template in test_templates:
                template_file = templates_dir / f"{template['metadata']['name']}.json"
                template_file.write_text(json.dumps(template, indent=2))

            # Create invalid template for testing
            invalid_template = templates_dir / "invalid-agent.json"
            invalid_template.write_text("{ invalid json")

            # Create template missing required fields (missing metadata.description)
            incomplete_template = templates_dir / "incomplete-agent.json"
            incomplete_template.write_text(
                json.dumps(
                    {
                        "schema_version": "1.2.0",
                        "agent_id": "incomplete-agent",
                        "agent_version": "1.0.0",
                        "agent_type": "qa",
                        "metadata": {
                            "name": "incomplete-agent",
                            # Missing description field
                            "tags": ["incomplete"],
                        },
                        "capabilities": {"model": "sonnet", "tools": ["Read"]},
                        "instructions": {"system_prompt": "Incomplete agent."},
                    },
                    indent=2,
                )
            )

            yield templates_dir

    @pytest.fixture
    def discovery_service(self, temp_templates_dir):
        """Create AgentDiscoveryService instance."""
        return AgentDiscoveryService(temp_templates_dir)

    def test_initialization(self):
        """Test AgentDiscoveryService initialization."""
        service = AgentDiscoveryService(self)
        assert service.templates_dir == self
        assert hasattr(service, "logger")

    def test_list_available_agents(self):
        """Test listing available agents."""
        agents = self.list_available_agents()

        # Should find 3 valid agents (invalid ones filtered out)
        assert len(agents) >= 3

        # Check agent structure
        agent_names = [agent["name"] for agent in agents]
        assert "test-agent" in agent_names
        assert "qa-agent" in agent_names
        assert "security-agent" in agent_names

        # Check agent metadata
        test_agent = next(agent for agent in agents if agent["name"] == "test-agent")
        assert test_agent["description"] == "Test agent for testing"
        assert test_agent["version"] == "1.0.0"
        assert test_agent["tools"] == ["Read", "Write"]
        assert test_agent["specializations"] == ["testing"]

    def test_list_available_agents_empty_directory():
        """Test listing agents from empty directory."""
        with tmp_path as temp_dir:
            empty_dir = Path(temp_dir) / "empty"
            empty_dir.mkdir()

            service = AgentDiscoveryService(empty_dir)
            agents = service.list_available_agents()

            assert agents == []

    def test_list_available_agents_nonexistent_directory():
        """Test listing agents from nonexistent directory."""
        nonexistent_dir = Path("/nonexistent/directory")
        service = AgentDiscoveryService(nonexistent_dir)
        agents = service.list_available_agents()

        assert agents == []

    def test_get_filtered_templates_no_exclusions(self):
        """Test getting filtered templates with no exclusions."""
        templates = self.get_filtered_templates([], None)

        # Should return all valid templates
        assert len(templates) >= 3
        template_names = [t.stem for t in templates]
        assert "test-agent" in template_names
        assert "qa-agent" in template_names
        assert "security-agent" in template_names

    def test_get_filtered_templates_with_exclusions(self):
        """Test getting filtered templates with exclusions."""
        excluded_agents = ["test-agent", "qa-agent"]
        templates = self.get_filtered_templates(excluded_agents, None)

        template_names = [t.stem for t in templates]
        assert "test-agent" not in template_names
        assert "qa-agent" not in template_names
        assert "security-agent" in template_names

    def test_get_filtered_templates_case_insensitive(self):
        """Test case-insensitive filtering."""
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "agent_deployment.case_sensitive_exclusion": False,
            "agent_deployment.exclusion_patterns": [],
            "environment": "development",
            "agent_deployment.development_exclusions": [],
        }.get(key, default)

        excluded_agents = ["TEST-AGENT", "QA-AGENT"]
        templates = self.get_filtered_templates(excluded_agents, config)

        template_names = [t.stem for t in templates]
        assert "test-agent" not in template_names
        assert "qa-agent" not in template_names
        assert "security-agent" in template_names

    def test_find_agent_template_exists(self):
        """Test finding existing agent template."""
        template_path = self.find_agent_template("test-agent")

        assert template_path is not None
        assert template_path.name == "test-agent.json"
        assert template_path.exists()

    def test_find_agent_template_not_exists(self):
        """Test finding non-existent agent template."""
        template_path = self.find_agent_template("nonexistent-agent")

        assert template_path is None

    def test_get_agent_categories(self):
        """Test getting agent categories."""
        categories = self.get_agent_categories()

        assert "testing" in categories
        assert "qa" in categories
        assert "security" in categories

        # Check category contents
        assert "test-agent" in categories["testing"]
        assert "qa-agent" in categories["testing"]
        assert "qa-agent" in categories["qa"]
        assert "security-agent" in categories["security"]

    def test_extract_agent_metadata_valid(self):
        """Test extracting metadata from valid template."""
        template_file = self.templates_dir / "test-agent.json"
        metadata = self._extract_agent_metadata(template_file)

        assert metadata is not None
        assert metadata["name"] == "test-agent"
        assert metadata["description"] == "Test agent for testing"
        assert metadata["version"] == "1.0.0"
        assert metadata["tools"] == ["Read", "Write"]
        assert metadata["specializations"] == ["testing"]

    def test_extract_agent_metadata_invalid_json(self):
        """Test extracting metadata from invalid JSON."""
        template_file = self.templates_dir / "invalid-agent.json"
        metadata = self._extract_agent_metadata(template_file)

        assert metadata is None

    def test_is_agent_excluded_explicit(self):
        """Test explicit agent exclusion."""
        excluded_agents = ["test-agent", "qa-agent"]

        assert self._is_agent_excluded("test-agent", excluded_agents, None)
        assert self._is_agent_excluded("qa-agent", excluded_agents, None)
        assert not self._is_agent_excluded("security-agent", excluded_agents, None)

    def test_is_agent_excluded_case_insensitive(self):
        """Test case-insensitive agent exclusion."""
        config = Mock()
        config.get.side_effect = lambda key, default=None: {
            "agent_deployment.case_sensitive_exclusion": False
        }.get(key, default)

        excluded_agents = ["TEST-AGENT"]

        assert self._is_agent_excluded("test-agent", excluded_agents, config)
        assert not self._is_agent_excluded("security-agent", excluded_agents, config)

    def test_validate_template_file_valid(self):
        """Test validating valid template file."""
        template_file = self.templates_dir / "test-agent.json"

        assert self._validate_template_file(template_file)

    def test_validate_template_file_invalid_json(self):
        """Test validating invalid JSON template."""
        template_file = self.templates_dir / "invalid-agent.json"

        assert not self._validate_template_file(template_file)

    def test_validate_template_file_missing_fields(self):
        """Test validating template with missing required fields."""
        template_file = self.templates_dir / "incomplete-agent.json"

        assert not self._validate_template_file(template_file)

    def test_is_valid_agent_name(self):
        """Test agent name validation."""
        # Valid names
        assert self._is_valid_agent_name("test-agent")
        assert self._is_valid_agent_name("qa-validator")
        assert self._is_valid_agent_name("security123")
        assert self._is_valid_agent_name("agent")

        # Invalid names
        assert not self._is_valid_agent_name("Test-Agent")  # uppercase
        assert not self._is_valid_agent_name("test_agent")  # underscore
        assert not self._is_valid_agent_name("test--agent")  # double hyphen
        assert not self._is_valid_agent_name("-test-agent")  # starts with hyphen
        assert not self._is_valid_agent_name("test-agent-")  # ends with hyphen
        assert not self._is_valid_agent_name("123-agent")  # starts with number

    def test_get_discovery_stats(self):
        """Test getting discovery statistics."""
        stats = self.get_discovery_stats()

        assert "total_templates" in stats
        assert "valid_templates" in stats
        assert "invalid_templates" in stats
        assert "categories" in stats
        assert "templates_directory" in stats
        assert "directory_exists" in stats

        assert stats["directory_exists"] is True
        assert stats["total_templates"] >= 3
        assert stats["valid_templates"] >= 3
        assert isinstance(stats["categories"], dict)

    def test_get_discovery_stats_nonexistent_directory():
        """Test getting stats for nonexistent directory."""
        nonexistent_dir = Path("/nonexistent/directory")
        service = AgentDiscoveryService(nonexistent_dir)
        stats = service.get_discovery_stats()

        assert stats["directory_exists"] is False
        assert stats["total_templates"] == 0
        assert stats["valid_templates"] == 0
        assert stats["invalid_templates"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
