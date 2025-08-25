"""Shared fixtures for agent tests."""

import json
from typing import Any, Dict

import pytest


@pytest.fixture
def mock_agent_data() -> Dict[str, Any]:
    """Create mock agent data matching the schema."""
    return {
        "schema_version": "1.1.0",
        "agent_id": "test_agent",
        "agent_version": "1.0.0",
        "agent_type": "base",
        "metadata": {
            "name": "Test Agent",
            "description": "A test agent for unit testing",
            "category": "quality",
            "tags": ["test", "mock"],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        },
        "capabilities": {
            "model": "claude-sonnet-4-20250514",
            "resource_tier": "standard",
            "tools": ["Read", "Grep"],
            "features": ["caching", "validation"],
        },
        "instructions": "# Test Agent Instructions\n\nThis is a test agent for unit testing purposes.\n\n## Purpose\n\nThe test agent is designed to validate the agent loading functionality, including:\n- Schema validation\n- Caching behavior\n- Error handling\n- Performance characteristics\n\n## Capabilities\n\nThis agent supports various testing scenarios and can be used to verify:\n1. Agent discovery and registration\n2. Prompt loading and caching\n3. Metadata retrieval\n4. Dynamic model selection\n\n## Testing Guidelines\n\nWhen using this agent for testing:\n- Ensure all required fields are populated\n- Verify caching behavior works as expected\n- Test error conditions and edge cases\n- Monitor performance metrics\n\n## Additional Context\n\nThis agent is part of the comprehensive test suite for the Claude MPM agent loading system. It provides a minimal but complete implementation that satisfies all schema requirements while being simple enough for testing purposes.",
        "knowledge": {
            "domain_expertise": ["testing", "mocking"],
            "codebase_patterns": ["pytest", "unittest"],
        },
        "interactions": {
            "input_format": {"required_fields": ["text"]},
            "output_format": {"structure": "markdown"},
        },
    }


@pytest.fixture
def temp_agent_dir(tmp_path, mock_agent_data):
    """Create a temporary directory with test agent files."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    # Create test agent file
    agent_file = templates_dir / "test_agent.json"
    agent_file.write_text(json.dumps(mock_agent_data, indent=2))

    # Create another test agent
    research_data = mock_agent_data.copy()
    research_data.update(
        {
            "agent_id": "research_agent",
            "agent_type": "research",
            "metadata": mock_agent_data["metadata"].copy(),
        }
    )
    research_data["metadata"].update(
        {
            "name": "Research Agent",
            "description": "Agent for research tasks",
            "category": "research",
        }
    )
    research_data["capabilities"] = mock_agent_data["capabilities"].copy()
    research_data["capabilities"].update(
        {"model": "claude-opus-4-20250514", "resource_tier": "intensive"}
    )
    research_data["instructions"] = (
        "# Research Agent\n\nSpecialized for research and analysis tasks.\n\n## Core Functionality\n\nThe Research Agent is optimized for:\n- Deep codebase analysis using tree-sitter AST\n- Pattern recognition and identification\n- Security vulnerability assessment\n- Performance optimization opportunities\n- Architecture documentation\n\n## Research Capabilities\n\n1. **Code Analysis**: Leverages tree-sitter for syntactic and semantic analysis\n2. **Pattern Detection**: Identifies common patterns and anti-patterns\n3. **Documentation**: Generates comprehensive technical documentation\n4. **Metrics Collection**: Gathers code quality and complexity metrics\n\n## Best Practices\n\nWhen conducting research:\n- Start with high-level architecture overview\n- Drill down into specific components as needed\n- Document findings with clear examples\n- Provide actionable recommendations\n- Include confidence levels in assessments\n\n## Integration\n\nThis agent integrates with other system components to provide comprehensive analysis capabilities for the Claude MPM system."
    )
    research_file = templates_dir / "research_agent.json"
    research_file.write_text(json.dumps(research_data, indent=2))

    # Create schema file (should be ignored)
    schema_file = templates_dir / "agent_schema.json"
    schema_file.write_text(json.dumps({"type": "object"}, indent=2))

    return templates_dir
