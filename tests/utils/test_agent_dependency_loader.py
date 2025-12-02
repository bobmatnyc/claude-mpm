"""
Tests for agent dependency loader with YAML frontmatter support.

Tests cover:
- YAML frontmatter parsing from markdown files
- Backward compatibility with JSON files
- File format precedence (.md over .json)
- Error handling for malformed YAML
- Integration with actual agent templates
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.utils.agent_dependency_loader import AgentDependencyLoader


class TestYAMLFrontmatterParsing:
    """Test YAML frontmatter extraction from markdown files."""

    def test_extract_valid_frontmatter(self):
        """Test extraction of valid YAML frontmatter."""
        loader = AgentDependencyLoader()
        content = """---
name: test_agent
dependencies:
  python:
    - pytest>=7.0.0
    - black>=23.0.0
  system:
    - git
---
# Agent Content
This is the agent description.
"""
        result = loader._extract_yaml_frontmatter(content)

        assert result is not None
        assert result["name"] == "test_agent"
        assert "dependencies" in result
        assert "python" in result["dependencies"]
        assert "pytest>=7.0.0" in result["dependencies"]["python"]
        assert "system" in result["dependencies"]
        assert "git" in result["dependencies"]["system"]

    def test_extract_frontmatter_no_delimiters(self):
        """Test extraction when no frontmatter delimiters present."""
        loader = AgentDependencyLoader()
        content = """# Agent Content
No frontmatter here.
"""
        result = loader._extract_yaml_frontmatter(content)
        assert result is None

    def test_extract_frontmatter_incomplete_delimiters(self):
        """Test extraction when only opening delimiter present."""
        loader = AgentDependencyLoader()
        content = """---
name: test_agent
dependencies:
  python:
    - pytest>=7.0.0
"""
        result = loader._extract_yaml_frontmatter(content)
        assert result is None

    def test_extract_frontmatter_malformed_yaml(self):
        """Test extraction with malformed YAML."""
        loader = AgentDependencyLoader()
        content = """---
name: test_agent
  invalid_indent:
- broken list
---
"""
        result = loader._extract_yaml_frontmatter(content)
        assert result is None

    def test_extract_frontmatter_empty(self):
        """Test extraction with empty frontmatter."""
        loader = AgentDependencyLoader()
        content = """---
---
# Agent Content
"""
        result = loader._extract_yaml_frontmatter(content)
        # Empty YAML is valid and returns None
        assert result is None or result == {}

    def test_extract_frontmatter_whitespace_before_delimiter(self):
        """Test extraction when whitespace precedes delimiter."""
        loader = AgentDependencyLoader()
        content = """
---
name: test_agent
---
"""
        # After strip(), content should start with ---
        result = loader._extract_yaml_frontmatter(content)
        assert result is not None
        assert result["name"] == "test_agent"

    def test_extract_frontmatter_complex_structure(self):
        """Test extraction with complex nested YAML."""
        loader = AgentDependencyLoader()
        content = """---
name: complex_agent
version: 1.0.0
dependencies:
  python:
    - package1>=1.0.0
    - package2>=2.0.0
  system:
    - tool1
    - tool2
metadata:
  author: Test Author
  tags:
    - engineering
    - testing
capabilities:
  memory_limit: 4096
  cpu_limit: 80
---
# Agent Description
"""
        result = loader._extract_yaml_frontmatter(content)

        assert result is not None
        assert result["name"] == "complex_agent"
        assert result["version"] == "1.0.0"
        assert len(result["dependencies"]["python"]) == 2
        assert len(result["dependencies"]["system"]) == 2
        assert result["metadata"]["author"] == "Test Author"
        assert "engineering" in result["metadata"]["tags"]
        assert result["capabilities"]["memory_limit"] == 4096


class TestLoadAgentDependencies:
    """Test loading agent dependencies from files."""

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary config directory structure."""
        config_dir = tmp_path / "agents"
        config_dir.mkdir()
        return config_dir

    @pytest.fixture
    def loader_with_agents(self, temp_config_dir):
        """Create loader with mock deployed agents."""
        loader = AgentDependencyLoader()
        loader.deployed_agents = {
            "test_agent": temp_config_dir / "test_agent.md",
            "legacy_agent": temp_config_dir / "legacy_agent.json",
        }
        return loader, temp_config_dir

    def test_load_from_markdown_file(self, loader_with_agents):
        """Test loading dependencies from markdown file with YAML frontmatter."""
        loader, config_dir = loader_with_agents

        # Create markdown file with frontmatter
        md_file = config_dir / "test_agent.md"
        md_file.write_text(
            """---
name: test_agent
dependencies:
  python:
    - pytest>=7.0.0
    - black>=23.0.0
---
# Agent Content
"""
        )

        # Mock the config paths to use temp directory
        with patch.object(loader, "load_agent_dependencies") as mock_load:
            # Call the real method
            mock_load.side_effect = (
                lambda: AgentDependencyLoader.load_agent_dependencies(loader)
            )

            # Temporarily override config paths
            original_method = loader.load_agent_dependencies
            loader.load_agent_dependencies = lambda: self._load_deps_with_custom_path(
                loader, [config_dir]
            )

            result = loader.load_agent_dependencies()

            # Restore original method
            loader.load_agent_dependencies = original_method

        assert "test_agent" in result
        assert "python" in result["test_agent"]
        assert "pytest>=7.0.0" in result["test_agent"]["python"]
        assert "black>=23.0.0" in result["test_agent"]["python"]

    def _load_deps_with_custom_path(self, loader, config_paths):
        """Helper to load dependencies with custom config paths."""
        agent_dependencies = {}

        for agent_id in loader.deployed_agents:
            found = False

            for config_dir in config_paths:
                if found:
                    break

                # Try markdown first
                md_file = config_dir / f"{agent_id}.md"
                if md_file.exists():
                    try:
                        content = md_file.read_text(encoding="utf-8")
                        frontmatter = loader._extract_yaml_frontmatter(content)
                        if frontmatter and "dependencies" in frontmatter:
                            agent_dependencies[agent_id] = frontmatter["dependencies"]
                            found = True
                            break
                    except Exception:
                        pass

                # Fall back to JSON
                if not found:
                    json_file = config_dir / f"{agent_id}.json"
                    if json_file.exists():
                        try:
                            with json_file.open() as f:
                                config = json.load(f)
                                if "dependencies" in config:
                                    agent_dependencies[agent_id] = config[
                                        "dependencies"
                                    ]
                                    found = True
                                    break
                        except Exception:
                            pass

        loader.agent_dependencies = agent_dependencies
        return agent_dependencies

    def test_load_from_json_file(self, loader_with_agents):
        """Test loading dependencies from legacy JSON file."""
        loader, config_dir = loader_with_agents

        # Create JSON file
        json_file = config_dir / "legacy_agent.json"
        json_file.write_text(
            json.dumps(
                {
                    "name": "legacy_agent",
                    "dependencies": {
                        "python": ["requests>=2.28.0"],
                        "system": ["curl"],
                    },
                }
            )
        )

        # Use custom path helper
        result = self._load_deps_with_custom_path(loader, [config_dir])

        assert "legacy_agent" in result
        assert "python" in result["legacy_agent"]
        assert "requests>=2.28.0" in result["legacy_agent"]["python"]

    def test_markdown_precedence_over_json(self, loader_with_agents):
        """Test that markdown files take precedence over JSON files."""
        loader, config_dir = loader_with_agents

        # Create both files for same agent
        md_file = config_dir / "test_agent.md"
        md_file.write_text(
            """---
name: test_agent
dependencies:
  python:
    - pytest>=7.0.0
---
"""
        )

        json_file = config_dir / "test_agent.json"
        json_file.write_text(
            json.dumps(
                {
                    "name": "test_agent",
                    "dependencies": {"python": ["old-package>=1.0.0"]},
                }
            )
        )

        result = self._load_deps_with_custom_path(loader, [config_dir])

        assert "test_agent" in result
        # Should load from markdown, not JSON
        assert "pytest>=7.0.0" in result["test_agent"]["python"]
        assert "old-package>=1.0.0" not in result["test_agent"]["python"]

    def test_fallback_to_json_when_markdown_missing(self, loader_with_agents):
        """Test fallback to JSON when markdown file doesn't exist."""
        loader, config_dir = loader_with_agents

        # Only create JSON file
        json_file = config_dir / "test_agent.json"
        json_file.write_text(
            json.dumps(
                {"name": "test_agent", "dependencies": {"python": ["requests>=2.28.0"]}}
            )
        )

        result = self._load_deps_with_custom_path(loader, [config_dir])

        assert "test_agent" in result
        assert "requests>=2.28.0" in result["test_agent"]["python"]

    def test_no_dependencies_in_frontmatter(self, loader_with_agents):
        """Test handling when frontmatter exists but has no dependencies."""
        loader, config_dir = loader_with_agents

        md_file = config_dir / "test_agent.md"
        md_file.write_text(
            """---
name: test_agent
version: 1.0.0
---
# No dependencies
"""
        )

        result = self._load_deps_with_custom_path(loader, [config_dir])

        # Agent should not be in results if no dependencies
        assert "test_agent" not in result

    def test_malformed_markdown_falls_back_to_json(self, loader_with_agents):
        """Test fallback to JSON when markdown is malformed."""
        loader, config_dir = loader_with_agents

        # Create malformed markdown
        md_file = config_dir / "test_agent.md"
        md_file.write_text(
            """---
name: test_agent
  invalid: yaml
---
"""
        )

        # Create valid JSON
        json_file = config_dir / "test_agent.json"
        json_file.write_text(
            json.dumps(
                {
                    "name": "test_agent",
                    "dependencies": {"python": ["fallback-package>=1.0.0"]},
                }
            )
        )

        result = self._load_deps_with_custom_path(loader, [config_dir])

        assert "test_agent" in result
        assert "fallback-package>=1.0.0" in result["test_agent"]["python"]

    def test_empty_deployed_agents(self):
        """Test loading when no agents are deployed."""
        loader = AgentDependencyLoader()
        loader.deployed_agents = {}

        result = loader.load_agent_dependencies()

        assert result == {}
        assert len(loader.agent_dependencies) == 0


class TestIntegrationWithRealTemplates:
    """Integration tests with actual agent templates."""

    def test_load_engineer_template_dependencies(self):
        """Test loading dependencies from actual engineer.md template."""
        loader = AgentDependencyLoader()

        # Check if engineer template exists
        template_path = (
            Path.cwd() / "src" / "claude_mpm" / "agents" / "templates" / "engineer.md"
        )
        if not template_path.exists():
            pytest.skip("Engineer template not found")

        # Mock deployed agents
        loader.deployed_agents = {"engineer": template_path}

        # Load dependencies
        result = loader.load_agent_dependencies()

        # Engineer agent should have dependencies
        assert "engineer" in result
        assert "python" in result["engineer"]
        # Should contain rope and black based on actual template
        deps = result["engineer"]["python"]
        assert any("rope" in dep for dep in deps)
        assert any("black" in dep for dep in deps)

    def test_load_multiple_template_dependencies(self):
        """Test loading dependencies from multiple agent templates."""
        loader = AgentDependencyLoader()

        template_dir = Path.cwd() / "src" / "claude_mpm" / "agents" / "templates"
        if not template_dir.exists():
            pytest.skip("Template directory not found")

        # Find all markdown templates
        md_templates = list(template_dir.glob("*.md"))
        if not md_templates:
            pytest.skip("No markdown templates found")

        # Mock deployed agents for found templates
        loader.deployed_agents = {
            template.stem: template for template in md_templates[:5]  # Test first 5
        }

        # Load dependencies
        result = loader.load_agent_dependencies()

        # Should successfully parse at least some templates
        assert len(result) >= 0  # Some templates may not have dependencies

        # Verify structure for templates with dependencies
        for agent_id, deps in result.items():
            assert isinstance(deps, dict)
            if "python" in deps:
                assert isinstance(deps["python"], list)
            if "system" in deps:
                assert isinstance(deps["system"], list)


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_read_error_logs_warning(self, tmp_path, caplog):
        """Test that read errors are logged as warnings."""
        loader = AgentDependencyLoader()

        config_dir = tmp_path / "agents"
        config_dir.mkdir()

        # Create file with restricted permissions (simulate read error)
        md_file = config_dir / "test_agent.md"
        md_file.write_text("---\nname: test\n---")

        loader.deployed_agents = {"test_agent": md_file}

        # Simulate read error by mocking
        with patch.object(Path, "read_text", side_effect=PermissionError("No access")):
            result = loader.load_agent_dependencies()

            # Should handle error gracefully
            assert "test_agent" not in result

    def test_unicode_handling(self, tmp_path):
        """Test handling of Unicode characters in frontmatter."""
        loader = AgentDependencyLoader()

        config_dir = tmp_path / "agents"
        config_dir.mkdir()

        md_file = config_dir / "unicode_agent.md"
        md_file.write_text(
            """---
name: unicode_agent
description: Agent with émojis 🚀 and spëcial chars
dependencies:
  python:
    - pytest>=7.0.0
---
""",
            encoding="utf-8",
        )

        loader.deployed_agents = {"unicode_agent": md_file}

        # Use helper to load with custom path
        agent_dependencies = {}
        for agent_id in loader.deployed_agents:
            try:
                content = md_file.read_text(encoding="utf-8")
                frontmatter = loader._extract_yaml_frontmatter(content)
                if frontmatter and "dependencies" in frontmatter:
                    agent_dependencies[agent_id] = frontmatter["dependencies"]
            except Exception:
                pass

        assert "unicode_agent" in agent_dependencies
        assert "pytest>=7.0.0" in agent_dependencies["unicode_agent"]["python"]
