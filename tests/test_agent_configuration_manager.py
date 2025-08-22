#!/usr/bin/env python3
"""
Tests for AgentConfigurationManager Service
==========================================

Comprehensive test suite for the extracted AgentConfigurationManager service.
Tests all configuration management, base agent loading, and tool assignment functionality.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment.agent_configuration_manager import (
    AgentConfigurationManager,
)


class TestAgentConfigurationManager:
    """Test suite for AgentConfigurationManager."""

    @pytest.fixture
    def temp_base_agent_file(self):
        """Create temporary base agent file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            base_agent_data = {
                "name": "base-agent",
                "description": "Base agent for testing",
                "version": "2.1.0",
                "instructions": "You are a helpful AI assistant for testing.",
                "tools": ["Read", "Write", "Edit", "Grep"],
            }
            json.dump(base_agent_data, f, indent=2)
            f.flush()

            yield Path(f.name)

            # Cleanup
            Path(f.name).unlink(missing_ok=True)

    @pytest.fixture
    def config_manager(self, temp_base_agent_file):
        """Create AgentConfigurationManager instance."""
        return AgentConfigurationManager(temp_base_agent_file)

    @pytest.fixture
    def config_manager_no_base(self):
        """Create AgentConfigurationManager without base agent."""
        return AgentConfigurationManager()

    def test_initialization(temp_base_agent_file):
        """Test AgentConfigurationManager initialization."""
        manager = AgentConfigurationManager(temp_base_agent_file)
        assert manager.base_agent_path == temp_base_agent_file
        assert hasattr(manager, "logger")
        assert manager._base_agent_cache is None

    def test_initialization_no_base_agent():
        """Test initialization without base agent."""
        manager = AgentConfigurationManager()
        assert manager.base_agent_path is None
        assert manager._base_agent_cache is None

    def test_load_base_agent_success(config_manager):
        """Test successful base agent loading."""
        base_agent_data, base_agent_version = config_manager.load_base_agent()

        assert base_agent_data["name"] == "base-agent"
        assert base_agent_data["description"] == "Base agent for testing"
        assert base_agent_data["version"] == "2.1.0"
        assert base_agent_version == (2, 1, 0)

        # Test caching
        assert config_manager._base_agent_cache is not None

    def test_load_base_agent_cached(config_manager):
        """Test that base agent loading uses cache on second call."""
        # First call
        data1, version1 = config_manager.load_base_agent()

        # Second call should use cache
        data2, version2 = config_manager.load_base_agent()

        assert data1 is data2  # Should be same object (cached)
        assert version1 == version2

    def test_load_base_agent_no_file(config_manager_no_base):
        """Test base agent loading when file doesn't exist."""
        base_agent_data, base_agent_version = config_manager_no_base.load_base_agent()

        # Should return default base agent
        assert base_agent_data["name"] == "base-agent"
        assert base_agent_data["description"] == "Base agent configuration"
        assert base_agent_version == (1, 0, 0)

    def test_get_agent_tools_security(config_manager):
        """Test tool assignment for security agents."""
        tools = config_manager.get_agent_tools("security-scanner", {})

        assert "Read" in tools
        assert "Write" in tools
        assert "SecurityScan" in tools
        assert "VulnerabilityCheck" in tools

    def test_get_agent_tools_qa(config_manager):
        """Test tool assignment for QA agents."""
        tools = config_manager.get_agent_tools("qa-validator", {})

        assert "Read" in tools
        assert "Write" in tools
        assert "TestRunner" in tools
        assert "CodeAnalysis" in tools

    def test_get_agent_tools_documentation(config_manager):
        """Test tool assignment for documentation agents."""
        tools = config_manager.get_agent_tools("doc-generator", {})

        assert "Read" in tools
        assert "Write" in tools
        assert "DocumentGenerator" in tools
        assert "MarkdownProcessor" in tools

    def test_get_agent_tools_data(config_manager):
        """Test tool assignment for data processing agents."""
        tools = config_manager.get_agent_tools("data-processor", {})

        assert "Read" in tools
        assert "Write" in tools
        assert "DataProcessor" in tools
        assert "CSVHandler" in tools

    def test_get_agent_tools_operations(config_manager):
        """Test tool assignment for operations agents."""
        tools = config_manager.get_agent_tools("ops-monitor", {})

        assert "Read" in tools
        assert "Write" in tools
        assert "SystemMonitor" in tools
        assert "LogAnalyzer" in tools

    def test_get_agent_tools_research(config_manager):
        """Test tool assignment for research agents."""
        tools = config_manager.get_agent_tools("research-agent", {})

        assert "Read" in tools
        assert "Write" in tools
        assert "WebSearch" in tools
        assert "DataCollector" in tools

    def test_get_agent_tools_specializations(config_manager):
        """Test tool assignment based on specializations metadata."""
        metadata = {"specializations": ["security", "testing"]}
        tools = config_manager.get_agent_tools("generic-agent", metadata)

        # Should match security specialization
        assert "SecurityScan" in tools
        assert "VulnerabilityCheck" in tools

    def test_get_agent_tools_default(config_manager):
        """Test default tool assignment."""
        tools = config_manager.get_agent_tools("generic-agent", {})

        # Should have base tools plus defaults
        assert "Read" in tools
        assert "Write" in tools
        assert "Edit" in tools
        assert "Bash" in tools
        assert "WebSearch" in tools

    def test_get_agent_specific_config_security(config_manager):
        """Test security agent configuration."""
        config = config_manager.get_agent_specific_config("security-scanner")

        assert config["timeout"] == 600
        assert config["max_iterations"] == 20
        assert config["security_mode"] is True
        assert config["audit_logging"] is True

    def test_get_agent_specific_config_qa(config_manager):
        """Test QA agent configuration."""
        config = config_manager.get_agent_specific_config("qa-validator")

        assert config["timeout"] == 900
        assert config["max_iterations"] == 15
        assert config["test_mode"] is True
        assert config["coverage_reporting"] is True

    def test_get_agent_specific_config_data(config_manager):
        """Test data processing agent configuration."""
        config = config_manager.get_agent_specific_config("data-processor")

        assert config["timeout"] == 1200
        assert config["memory_limit"] == "2GB"
        assert config["parallel_execution"] is True
        assert config["data_processing_mode"] is True

    def test_get_agent_specific_config_ops(config_manager):
        """Test operations agent configuration."""
        config = config_manager.get_agent_specific_config("ops-monitor")

        assert config["timeout"] == 180
        assert config["max_iterations"] == 5
        assert config["monitoring_mode"] is True
        assert config["alert_threshold"] == "warning"

    def test_get_agent_specific_config_research(config_manager):
        """Test research agent configuration."""
        config = config_manager.get_agent_specific_config("research-agent")

        assert config["timeout"] == 1800
        assert config["max_iterations"] == 25
        assert config["research_mode"] is True
        assert config["web_search_enabled"] is True

    def test_get_agent_specific_config_default(config_manager):
        """Test default agent configuration."""
        config = config_manager.get_agent_specific_config("generic-agent")

        assert config["timeout"] == 300
        assert config["max_iterations"] == 10
        assert config["memory_limit"] == "1GB"
        assert config["parallel_execution"] is False

    def test_determine_source_tier_project(config_manager):
        """Test source tier determination for project context."""
        with tmp_path as temp_dir:
            temp_path = Path(temp_dir)

            # Create project indicator
            (temp_path / ".git").mkdir()

            with patch("pathlib.Path.cwd", return_value=temp_path):
                tier = config_manager.determine_source_tier()
                assert tier == "project"

    def test_determine_source_tier_user(config_manager):
        """Test source tier determination for user context."""
        with tmp_path as temp_dir:
            temp_path = Path(temp_dir)
            user_config = temp_path / ".claude"
            user_config.mkdir()

            with patch("pathlib.Path.cwd", return_value=temp_path), patch(
                "pathlib.Path.home", return_value=temp_path
            ):
                tier = config_manager.determine_source_tier()
                assert tier == "user"

    def test_determine_source_tier_system(config_manager):
        """Test source tier determination for system context."""
        with tmp_path as temp_dir:
            temp_path = Path(temp_dir)

            with patch("pathlib.Path.cwd", return_value=temp_path), patch(
                "pathlib.Path.home", return_value=temp_path
            ):
                tier = config_manager.determine_source_tier()
                assert tier == "system"

    def test_parse_base_agent_content_json(config_manager):
        """Test parsing JSON base agent content."""
        json_content = json.dumps(
            {
                "name": "test-agent",
                "version": "1.0.0",
                "instructions": "Test instructions",
            }
        )

        data = config_manager._parse_base_agent_content(json_content)

        assert data["name"] == "test-agent"
        assert data["version"] == "1.0.0"
        assert data["instructions"] == "Test instructions"

    def test_parse_base_agent_content_markdown(config_manager):
        """Test parsing Markdown with YAML frontmatter."""
        markdown_content = """---
name: test-agent
version: 1.0.0
description: Test agent
---

# Test Agent

This is a test agent with markdown instructions."""

        with patch("yaml.safe_load") as mock_yaml:
            mock_yaml.return_value = {
                "name": "test-agent",
                "version": "1.0.0",
                "description": "Test agent",
            }

            data = config_manager._parse_base_agent_content(markdown_content)

            assert data["name"] == "test-agent"
            assert "instructions" in data

    def test_parse_base_agent_content_plain_text(config_manager):
        """Test parsing plain text content."""
        plain_content = "You are a helpful AI assistant."

        data = config_manager._parse_base_agent_content(plain_content)

        assert data["name"] == "base-agent"
        assert data["instructions"] == plain_content

    def test_extract_base_agent_version(config_manager):
        """Test version extraction from base agent data."""
        test_cases = [
            ("1.2.3", (1, 2, 3)),
            ("v2.0.1", (2, 0, 1)),
            ("3.14.159", (3, 14, 159)),
            ("invalid", (1, 0, 0)),
            (None, (1, 0, 0)),
        ]

        for version_str, expected in test_cases:
            data = {"version": version_str} if version_str else {}
            result = config_manager._extract_base_agent_version(data)
            assert result == expected

    def test_clear_cache(config_manager):
        """Test cache clearing."""
        # Load base agent to populate cache
        config_manager.load_base_agent()
        assert config_manager._base_agent_cache is not None

        # Clear cache
        config_manager.clear_cache()
        assert config_manager._base_agent_cache is None

    def test_get_configuration_summary(config_manager):
        """Test configuration summary."""
        summary = config_manager.get_configuration_summary()

        assert "base_agent_path" in summary
        assert "base_agent_loaded" in summary
        assert "base_agent_version" in summary
        assert "base_agent_name" in summary
        assert "source_tier" in summary
        assert "cache_status" in summary

        # After loading, cache should be populated
        assert summary["base_agent_loaded"] is True
        assert summary["cache_status"] == "loaded"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])