"""Tests for RemoteAgentDiscoveryService.

WHY: Test the 4th tier of agent discovery - remote agents cached from GitHub.
These tests verify that Markdown agents are correctly parsed and converted to
JSON template format for deployment.
"""

import json
from pathlib import Path

import pytest

from claude_mpm.services.agents.deployment.remote_agent_discovery_service import (
    RemoteAgentDiscoveryService,
    RemoteAgentMetadata,
)


@pytest.fixture
def temp_remote_agents_dir(tmp_path):
    """Create a temporary remote agents directory."""
    remote_dir = tmp_path / "remote-agents"
    remote_dir.mkdir()
    return remote_dir


@pytest.fixture
def sample_remote_agent_md(temp_remote_agents_dir):
    """Create a sample remote agent Markdown file."""
    agent_md = temp_remote_agents_dir / "test_agent.md"
    agent_md.write_text(
        """# Test Agent

This is a test agent for remote discovery.

## Configuration
- Model: sonnet
- Priority: 100

## Routing
- Keywords: test, example, sample
- Paths: /test/, /example/
"""
    )
    return agent_md


@pytest.fixture
def sample_remote_agent_with_metadata(temp_remote_agents_dir):
    """Create a remote agent with metadata file."""
    agent_md = temp_remote_agents_dir / "with_meta.md"
    agent_md.write_text(
        """# Agent With Metadata

Agent with cache metadata

## Configuration
- Model: opus
- Priority: 80
"""
    )

    # Create corresponding metadata file
    meta_file = temp_remote_agents_dir / "with_meta.md.meta.json"
    meta_file.write_text(
        json.dumps(
            {
                "content_hash": "abc123def456",
                "etag": 'W/"abc123"',
                "last_modified": "2025-11-30T10:00:00Z",
            }
        )
    )
    return agent_md


def test_discover_remote_agents(temp_remote_agents_dir, sample_remote_agent_md):
    """Test discovering remote agents from cache directory."""
    service = RemoteAgentDiscoveryService(temp_remote_agents_dir)
    agents = service.discover_remote_agents()

    assert len(agents) == 1
    agent = agents[0]

    # Verify agent metadata structure
    assert agent["agent_id"] == "test-agent"
    assert agent["metadata"]["name"] == "Test Agent"
    assert (
        agent["metadata"]["description"] == "This is a test agent for remote discovery."
    )
    assert agent["model"] == "sonnet"
    assert agent["source"] == "remote"

    # Verify routing information
    assert agent["routing"]["priority"] == 100
    assert "test" in agent["routing"]["keywords"]
    assert "example" in agent["routing"]["keywords"]
    assert "/test/" in agent["routing"]["paths"]
    assert "/example/" in agent["routing"]["paths"]


def test_discover_remote_agents_no_directory(tmp_path):
    """Test discovering when remote agents directory doesn't exist."""
    non_existent_dir = tmp_path / "does-not-exist"
    service = RemoteAgentDiscoveryService(non_existent_dir)

    agents = service.discover_remote_agents()

    assert len(agents) == 0


def test_discover_remote_agents_empty_directory(temp_remote_agents_dir):
    """Test discovering from empty directory."""
    service = RemoteAgentDiscoveryService(temp_remote_agents_dir)

    agents = service.discover_remote_agents()

    assert len(agents) == 0


def test_parse_markdown_agent_missing_name(temp_remote_agents_dir):
    """Test parsing Markdown agent without name heading."""
    invalid_md = temp_remote_agents_dir / "invalid.md"
    invalid_md.write_text("No heading here\n\nJust some content")

    service = RemoteAgentDiscoveryService(temp_remote_agents_dir)
    result = service._parse_markdown_agent(invalid_md)

    assert result is None


def test_parse_markdown_agent_minimal(temp_remote_agents_dir):
    """Test parsing minimal Markdown agent with only name."""
    minimal_md = temp_remote_agents_dir / "minimal.md"
    minimal_md.write_text("# Minimal Agent\n\nMinimal description")

    service = RemoteAgentDiscoveryService(temp_remote_agents_dir)
    result = service._parse_markdown_agent(minimal_md)

    assert result is not None
    assert result["metadata"]["name"] == "Minimal Agent"
    assert result["model"] == "sonnet"  # Default
    assert result["routing"]["priority"] == 50  # Default


def test_parse_markdown_agent_with_metadata(
    temp_remote_agents_dir, sample_remote_agent_with_metadata
):
    """Test parsing agent and extracting version from metadata file."""
    service = RemoteAgentDiscoveryService(temp_remote_agents_dir)
    result = service._parse_markdown_agent(sample_remote_agent_with_metadata)

    assert result is not None
    assert result["metadata"]["name"] == "Agent With Metadata"
    assert result["version"] == "abc123def456"  # From metadata file


def test_get_agent_version_no_metadata(temp_remote_agents_dir, sample_remote_agent_md):
    """Test getting version when metadata file doesn't exist."""
    service = RemoteAgentDiscoveryService(temp_remote_agents_dir)
    version = service._get_agent_version(sample_remote_agent_md)

    assert version == "unknown"


def test_get_agent_version_with_metadata(
    temp_remote_agents_dir, sample_remote_agent_with_metadata
):
    """Test getting version from metadata file."""
    service = RemoteAgentDiscoveryService(temp_remote_agents_dir)
    version = service._get_agent_version(sample_remote_agent_with_metadata)

    assert version == "abc123def456"


def test_get_remote_agent_metadata(temp_remote_agents_dir, sample_remote_agent_md):
    """Test retrieving metadata for specific agent."""
    service = RemoteAgentDiscoveryService(temp_remote_agents_dir)
    metadata = service.get_remote_agent_metadata("Test Agent")

    assert metadata is not None
    assert isinstance(metadata, RemoteAgentMetadata)
    assert metadata.name == "Test Agent"
    assert metadata.model == "sonnet"
    assert metadata.routing_priority == 100
    assert "test" in metadata.routing_keywords


def test_get_remote_agent_metadata_not_found(temp_remote_agents_dir):
    """Test retrieving metadata for non-existent agent."""
    service = RemoteAgentDiscoveryService(temp_remote_agents_dir)
    metadata = service.get_remote_agent_metadata("Non Existent Agent")

    assert metadata is None


def test_parse_markdown_agent_complex_keywords(temp_remote_agents_dir):
    """Test parsing agent with complex keyword lists."""
    complex_md = temp_remote_agents_dir / "complex.md"
    complex_md.write_text(
        """# Complex Agent

Complex description

## Configuration
- Model: haiku
- Priority: 200

## Routing
- Keywords: security, audit, compliance, vulnerability, scanning
- Paths: /security/, /audit/, /compliance/
"""
    )

    service = RemoteAgentDiscoveryService(temp_remote_agents_dir)
    result = service._parse_markdown_agent(complex_md)

    assert result is not None
    assert len(result["routing"]["keywords"]) == 5
    assert "security" in result["routing"]["keywords"]
    assert "vulnerability" in result["routing"]["keywords"]
    assert len(result["routing"]["paths"]) == 3


def test_discover_multiple_agents(temp_remote_agents_dir):
    """Test discovering multiple remote agents."""
    # Create multiple agents
    for i in range(3):
        agent_md = temp_remote_agents_dir / f"agent_{i}.md"
        agent_md.write_text(
            f"""# Agent {i}

Description for agent {i}

## Configuration
- Model: sonnet
- Priority: {i * 10}
"""
        )

    service = RemoteAgentDiscoveryService(temp_remote_agents_dir)
    agents = service.discover_remote_agents()

    assert len(agents) == 3
    # Verify all agents were parsed
    agent_names = [a["metadata"]["name"] for a in agents]
    assert "Agent 0" in agent_names
    assert "Agent 1" in agent_names
    assert "Agent 2" in agent_names


def test_agent_id_generation(temp_remote_agents_dir):
    """Test agent_id is correctly generated from name."""
    test_cases = [
        ("Simple Agent", "simple-agent"),
        ("Agent With Numbers 123", "agent-with-numbers-123"),
        ("UPPERCASE AGENT", "uppercase-agent"),
        ("Agent_With_Underscores", "agent-with-underscores"),
        ("Agent!!!Special###Chars", "agentspecialchars"),
    ]

    for name, expected_id in test_cases:
        agent_md = temp_remote_agents_dir / f"test_{expected_id}.md"
        agent_md.write_text(f"# {name}\n\nDescription")

        service = RemoteAgentDiscoveryService(temp_remote_agents_dir)
        result = service._parse_markdown_agent(agent_md)

        assert result is not None
        assert result["agent_id"] == expected_id, f"Failed for name: {name}"

        # Clean up for next iteration
        agent_md.unlink()
