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
    """Create a temporary remote agents directory with /agents/ subdirectory."""
    remote_dir = tmp_path / "remote-agents"
    remote_dir.mkdir()
    # Create /agents/ subdirectory (expected by implementation)
    agents_dir = remote_dir / "agents"
    agents_dir.mkdir()
    return remote_dir


@pytest.fixture
def sample_remote_agent_md(temp_remote_agents_dir):
    """Create a sample remote agent Markdown file in /agents/ subdirectory."""
    # Create agent in /agents/ subdirectory (Bug #4 fix)
    agents_dir = temp_remote_agents_dir / "agents"
    agent_md = agents_dir / "test_agent.md"
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
    """Create a remote agent with metadata file in /agents/ subdirectory."""
    # Create agent in /agents/ subdirectory (Bug #4 fix)
    agents_dir = temp_remote_agents_dir / "agents"
    agent_md = agents_dir / "with_meta.md"
    agent_md.write_text(
        """# Agent With Metadata

Agent with cache metadata

## Configuration
- Model: opus
- Priority: 80
"""
    )

    # Create corresponding metadata file
    meta_file = agents_dir / "with_meta.md.meta.json"
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
    """Test discovering remote agents from cache directory.

    Bug #3 fix: Agent IDs are now generated from file paths, not name headings.
    File test_agent.md -> agent_id: test_agent (not test-agent from heading)
    """
    service = RemoteAgentDiscoveryService(temp_remote_agents_dir)
    agents = service.discover_remote_agents()

    assert len(agents) == 1
    agent = agents[0]

    # Verify agent metadata structure
    # Bug #3 fix: agent_id comes from filename (test_agent.md -> test_agent)
    assert agent["agent_id"] == "test_agent"
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
    # Create agent in /agents/ subdirectory
    agents_dir = temp_remote_agents_dir / "agents"
    invalid_md = agents_dir / "invalid.md"
    invalid_md.write_text("No heading here\n\nJust some content")

    service = RemoteAgentDiscoveryService(temp_remote_agents_dir)
    result = service._parse_markdown_agent(invalid_md)

    assert result is None


def test_parse_markdown_agent_minimal(temp_remote_agents_dir):
    """Test parsing minimal Markdown agent with only name."""
    # Create agent in /agents/ subdirectory
    agents_dir = temp_remote_agents_dir / "agents"
    minimal_md = agents_dir / "minimal.md"
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
    # Create agent in /agents/ subdirectory
    agents_dir = temp_remote_agents_dir / "agents"
    complex_md = agents_dir / "complex.md"
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
    # Create multiple agents in /agents/ subdirectory
    agents_dir = temp_remote_agents_dir / "agents"
    for i in range(3):
        agent_md = agents_dir / f"agent_{i}.md"
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
    """Test agent_id is correctly generated from file path.

    Bug #4 fix: Agent IDs are now based on file paths relative to /agents/ subdirectory.
    Files must be in /agents/ subdirectory for hierarchical IDs.
    If not in /agents/, falls back to filename stem only.
    """
    test_cases = [
        ("Simple Agent", "simple-agent.md", "simple-agent"),
        (
            "Agent With Numbers 123",
            "agent-with-numbers-123.md",
            "agent-with-numbers-123",
        ),
        ("UPPERCASE AGENT", "uppercase-agent.md", "uppercase-agent"),
        (
            "Backend/Python Engineer",
            "backend/python-engineer.md",
            "backend/python-engineer",
        ),
        ("QA/Test Agent", "qa/test-agent.md", "qa/test-agent"),
    ]

    # All test cases create files in /agents/ subdirectory
    agents_dir = temp_remote_agents_dir / "agents"

    for name, filename, expected_id in test_cases:
        # Create file in /agents/ subdirectory with proper hierarchy
        agent_path = agents_dir / filename
        agent_path.parent.mkdir(parents=True, exist_ok=True)
        agent_path.write_text(f"# {name}\n\nDescription")

        service = RemoteAgentDiscoveryService(temp_remote_agents_dir)
        result = service._parse_markdown_agent(agent_path)

        assert result is not None
        assert result["agent_id"] == expected_id, (
            f"Failed for name: {name}, filename: {filename}, got: {result['agent_id']}"
        )

        # Clean up for next iteration
        agent_path.unlink()
        # Clean up empty directories
        if agent_path.parent != agents_dir and not list(agent_path.parent.iterdir()):
            agent_path.parent.rmdir()


def test_remote_agent_includes_path_field(
    temp_remote_agents_dir, sample_remote_agent_md
):
    """Test that remote agents include 'path' field for deployment compatibility (ticket 1M-480).

    WHY: Git-sourced agents must include 'path' field to match the structure
    expected by MultiSourceAgentDeploymentService. Previously only 'source_file'
    was included, causing KeyError during deployment validation.

    Related: Ticket 1M-480 - Fix 'path' field deployment for git-sourced agents
    """
    service = RemoteAgentDiscoveryService(temp_remote_agents_dir)
    agents = service.discover_remote_agents()

    assert len(agents) == 1
    agent = agents[0]

    # Verify 'path' field is present and correct
    assert "path" in agent, "Remote agent missing 'path' field (ticket 1M-480)"
    assert agent["path"] == str(sample_remote_agent_md)

    # Verify backward compatibility fields
    assert "file_path" in agent, "Remote agent missing 'file_path' field"
    assert agent["file_path"] == str(sample_remote_agent_md)
    assert "source_file" in agent, "Remote agent missing 'source_file' field"
    assert agent["source_file"] == str(sample_remote_agent_md)

    # Verify all path fields point to same file
    assert agent["path"] == agent["file_path"] == agent["source_file"]
