"""Unit tests for Phase 2 AgentManager additions.

Tests list_agent_names() and _extract_enrichment_fields() methods
added in Phase 2 Steps 0 and 1.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def temp_agents_dir():
    """Create a temporary agents directory with fixture files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        agents_dir = Path(tmpdir) / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        yield agents_dir


@pytest.fixture
def agent_manager(temp_agents_dir):
    """Create an AgentManager with temporary directories."""
    with patch(
        "claude_mpm.services.agents.management.agent_management_service.get_path_manager"
    ) as mock_pm:
        mock_pm.return_value.get_project_root.return_value = (
            temp_agents_dir.parent.parent
        )
        mock_pm.return_value.get_agents_dir.return_value = temp_agents_dir

        from claude_mpm.services.agents.management.agent_management_service import (
            AgentManager,
        )

        framework_dir = Path(tmpdir) if (tmpdir := tempfile.mkdtemp()) else Path("/tmp")
        mgr = AgentManager(
            framework_dir=Path(framework_dir),
            project_dir=temp_agents_dir,
        )
        yield mgr


class TestListAgentNames:
    """Step 0: list_agent_names() returns filenames without parsing."""

    def test_list_agent_names_returns_stems(self, agent_manager, temp_agents_dir):
        """Verify globs .md files and returns stem names."""
        (temp_agents_dir / "engineer.md").write_text("# Engineer\n")
        (temp_agents_dir / "python-engineer.md").write_text("# Python\n")
        (temp_agents_dir / "qa.md").write_text("# QA\n")

        names = agent_manager.list_agent_names(location="project")
        assert names == {"engineer", "python-engineer", "qa"}

    def test_list_agent_names_empty_dir(self, agent_manager, temp_agents_dir):
        """Verify empty set when no agents exist."""
        names = agent_manager.list_agent_names(location="project")
        assert names == set()

    def test_list_agent_names_ignores_non_md_files(
        self, agent_manager, temp_agents_dir
    ):
        """Verify non-.md files are ignored."""
        (temp_agents_dir / "engineer.md").write_text("# Engineer\n")
        (temp_agents_dir / "notes.txt").write_text("notes\n")
        (temp_agents_dir / "config.yaml").write_text("key: value\n")

        names = agent_manager.list_agent_names(location="project")
        assert names == {"engineer"}

    def test_list_agent_names_nonexistent_dir(self, agent_manager):
        """Verify empty set when directory does not exist."""
        agent_manager.project_dir = Path("/nonexistent/path")
        names = agent_manager.list_agent_names(location="project")
        assert names == set()


class TestExtractEnrichmentFields:
    """Step 1: _extract_enrichment_fields() parses frontmatter data."""

    def test_full_frontmatter(self, agent_manager):
        """Verify all fields extracted from well-formed frontmatter."""
        content = """---
description: "Python specialist"
category: engineering
color: green
tags:
  - python
  - async
resource_tier: standard
capabilities:
  network_access: true
skills:
  required:
    - pytest
    - mypy
  optional:
    - dspy
---
# Agent Content
"""
        result = agent_manager._extract_enrichment_fields(content)
        assert result["description"] == "Python specialist"
        assert result["category"] == "engineering"
        assert result["color"] == "green"
        assert result["tags"] == ["python", "async"]
        assert result["resource_tier"] == "standard"
        assert result["network_access"] is True
        assert result["skills_count"] == 3  # 2 required + 1 optional

    def test_missing_optional_fields(self, agent_manager):
        """Verify defaults for missing fields."""
        content = """---
type: core
version: "1.0"
---
# Simple Agent
"""
        result = agent_manager._extract_enrichment_fields(content)
        assert result["description"] == ""
        assert result["category"] == ""
        assert result["color"] == "gray"
        assert result["tags"] == []
        assert result["resource_tier"] == ""
        assert result["network_access"] is None
        assert result["skills_count"] == 0

    def test_list_format_skills(self, agent_manager):
        """Verify skills_count for list-format skills field."""
        content = """---
skills:
  - git-workflow
  - tdd
  - debugging
---
# Agent
"""
        result = agent_manager._extract_enrichment_fields(content)
        assert result["skills_count"] == 3

    def test_no_frontmatter(self, agent_manager):
        """Verify defaults when content has no frontmatter."""
        content = "# Just a Heading\n\nSome content."
        result = agent_manager._extract_enrichment_fields(content)
        assert result["color"] == "gray"
        assert result["tags"] == []
        assert result["skills_count"] == 0

    def test_malformed_yaml(self, agent_manager):
        """Verify defaults for malformed YAML frontmatter."""
        content = """---
description: [unbalanced bracket
tags: {invalid
---
# Agent
"""
        result = agent_manager._extract_enrichment_fields(content)
        # Should fall back to defaults on parse error
        assert result["color"] == "gray"
        assert result["tags"] == []

    def test_non_list_tags(self, agent_manager):
        """Verify tags defaults to [] when not a list."""
        content = """---
tags: "not-a-list"
---
# Agent
"""
        result = agent_manager._extract_enrichment_fields(content)
        assert result["tags"] == []

    def test_non_dict_capabilities(self, agent_manager):
        """Verify network_access is None when capabilities is not a dict."""
        content = """---
capabilities: "string-value"
---
# Agent
"""
        result = agent_manager._extract_enrichment_fields(content)
        assert result["network_access"] is None

    def test_skills_neither_list_nor_dict(self, agent_manager):
        """Verify skills_count is 0 when skills is neither list nor dict."""
        content = """---
skills: 42
---
# Agent
"""
        result = agent_manager._extract_enrichment_fields(content)
        assert result["skills_count"] == 0
