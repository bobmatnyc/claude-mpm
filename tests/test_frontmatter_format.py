"""
Test frontmatter format in deployed agents.

This test suite ensures that the YAML frontmatter in deployed agent files
follows the correct format and contains all required fields.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class TestFrontmatterFormat:
    """Test YAML frontmatter structure in deployed agents."""

    def test_frontmatter_structure_valid(self):
        """Test that valid frontmatter is correctly parsed."""
        # Create a valid agent file with proper frontmatter
        agent_content = """---
name: test_agent
description: Test agent for validation
version: 2.1.0
base_version: 1.0.0
tools: Read, Write, Edit, Grep, Glob, LS
model: sonnet
---

# Test Agent Instructions

This is the agent content after frontmatter.
"""
        agent_file = self / "test_agent.md"
        agent_file.write_text(agent_content)

        # Parse the frontmatter
        frontmatter = self._extract_frontmatter(agent_file)

        # Validate structure
        assert frontmatter is not None
        assert frontmatter["name"] == "test_agent"
        assert frontmatter["description"] == "Test agent for validation"
        assert frontmatter["version"] == "2.1.0"
        assert frontmatter["base_version"] == "1.0.0"
        assert frontmatter["tools"] == "Read, Write, Edit, Grep, Glob, LS"
        assert frontmatter["model"] == "sonnet"

    def test_frontmatter_required_fields(self):
        """Test that all required fields are present in frontmatter."""
        required_fields = [
            "name",
            "description",
            "version",
            "base_version",
            "tools",
            "model",
        ]

        # Test missing each required field
        for missing_field in required_fields:
            agent_content = self._create_agent_content(exclude_field=missing_field)
            agent_file = self / f"test_missing_{missing_field}.md"
            agent_file.write_text(agent_content)

            frontmatter = self._extract_frontmatter(agent_file)

            # Verify the field is missing
            assert (
                missing_field not in frontmatter or frontmatter[missing_field] is None
            )

            # Validate that this would be caught
            errors = self._validate_frontmatter(frontmatter)
            assert any(missing_field in error for error in errors)

    def test_frontmatter_version_formats(self):
        """Test various version format scenarios."""
        test_cases = [
            ("2.1.0", True, "Valid semantic version"),
            ("v2.1.0", True, "Semantic version with v prefix"),
            ("0.5.1", True, "Version starting with 0"),
            ("10.20.30", True, "Multi-digit version numbers"),
            ("2.1", False, "Missing patch version"),
            ("2", False, "Only major version"),
            ("0002-0005", False, "Old serial format"),
            ("", False, "Empty version"),
            ("invalid", False, "Non-numeric version"),
        ]

        for version, should_be_valid, description in test_cases:
            agent_content = f"""---
name: test_agent
description: Testing {description}
version: {version}
base_version: 1.0.0
tools: Read, Write
model: sonnet
---

Test content
"""
            agent_file = self / f"test_version_{version.replace('.', '_')}.md"
            agent_file.write_text(agent_content)

            frontmatter = self._extract_frontmatter(agent_file)
            is_valid = self._is_valid_semantic_version(frontmatter.get("version", ""))

            assert is_valid == should_be_valid, (
                f"Version '{version}' ({description}) validation mismatch"
            )

    def test_frontmatter_tools_format(self):
        """Test various tools field formats."""
        test_cases = [
            ("Read, Write, Edit", True, "Comma-separated tools"),
            ("Read,Write,Edit", True, "No spaces between tools"),
            ("Read", True, "Single tool"),
            (
                "Read, Write, Edit, Grep, Glob, LS, WebSearch, TodoWrite",
                True,
                "Many tools",
            ),
            ("", False, "Empty tools"),
            ("Read Write Edit", True, "Space-separated (legacy)"),
            (
                "[Read, Write, Edit]",
                True,
                "List format (parsed as string)",
            ),  # Will be parsed as string
        ]

        for tools, should_be_valid, description in test_cases:
            agent_content = f"""---
name: test_agent
description: Testing {description}
version: 1.0.0
base_version: 1.0.0
tools: {tools}
model: sonnet
---

Test content
"""
            agent_file = self / f"test_tools_{description.replace(' ', '_')}.md"
            agent_file.write_text(agent_content)

            frontmatter = self._extract_frontmatter(agent_file)
            # Basic validation - tools should be a non-empty string
            tools_value = frontmatter.get("tools", "") if frontmatter else ""
            # Handle None or other types
            if tools_value is None:
                tools_value = ""
            elif not isinstance(tools_value, str):
                tools_value = str(tools_value)
            is_valid = bool(tools_value.strip())

            assert is_valid == should_be_valid, (
                f"Tools '{tools}' ({description}) validation mismatch"
            )

    def test_frontmatter_model_values(self):
        """Test valid model values in frontmatter."""
        valid_models = ["haiku", "sonnet", "opus"]

        for model in valid_models:
            agent_content = f"""---
name: test_agent
description: Test agent with {model} model
version: 1.0.0
base_version: 1.0.0
tools: Read, Write
model: {model}
---

Test content
"""
            agent_file = self / f"test_model_{model}.md"
            agent_file.write_text(agent_content)

            frontmatter = self._extract_frontmatter(agent_file)
            assert frontmatter["model"] == model
            assert frontmatter["model"] in valid_models

    def test_frontmatter_parsing_edge_cases(self):
        """Test edge cases in frontmatter parsing."""
        # Test with quotes in description
        agent_content = """---
name: test_agent
description: Agent for 'special' tasks with "quotes"
version: 1.0.0
base_version: 1.0.0
tools: Read, Write
model: sonnet
---

Content
"""
        agent_file = self / "test_quotes.md"
        agent_file.write_text(agent_content)
        frontmatter = self._extract_frontmatter(agent_file)

        # Check that frontmatter was extracted successfully
        assert frontmatter is not None, "Failed to extract frontmatter"
        assert "special" in frontmatter["description"]
        assert "quotes" in frontmatter["description"]

        # Test with colons in values
        agent_content = """---
name: test_agent
description: "Agent: Advanced testing module"
version: 1.0.0
base_version: 1.0.0
tools: Read, Write
model: sonnet
---

Content
"""
        agent_file = self / "test_colons.md"
        agent_file.write_text(agent_content)
        frontmatter = self._extract_frontmatter(agent_file)
        assert "Agent: Advanced" in frontmatter["description"]

        # Test with multiline description
        agent_content = """---
name: test_agent
description: |
  This is a multiline
  description for testing
version: 1.0.0
base_version: 1.0.0
tools: Read, Write
model: sonnet
---

Content
"""
        agent_file = self / "test_multiline.md"
        agent_file.write_text(agent_content)
        frontmatter = self._extract_frontmatter(agent_file)
        assert "multiline" in frontmatter["description"]

    def test_frontmatter_separator_detection(self):
        """Test that content after frontmatter separator is correctly identified."""
        agent_content = """---
name: test_agent
description: Test agent
version: 1.0.0
base_version: 1.0.0
tools: Read, Write
model: sonnet
---

# Agent Instructions

This is the main content.

---

This should still be part of content, not frontmatter.
"""
        agent_file = self / "test_separator.md"
        agent_file.write_text(agent_content)

        # Extract frontmatter and content
        frontmatter, content = self._extract_frontmatter_and_content(agent_file)

        assert frontmatter is not None
        assert "# Agent Instructions" in content
        assert "This should still be part of content" in content
        assert "---" in content  # The second separator should be in content

    def test_frontmatter_without_separator(self):
        """Test handling of files without proper frontmatter separator."""
        agent_content = """name: test_agent
description: Test agent
version: 1.0.0

# Agent Instructions

This file has no frontmatter separators.
"""
        agent_file = self / "test_no_separator.md"
        agent_file.write_text(agent_content)

        frontmatter = self._extract_frontmatter(agent_file)

        # Should return None or empty dict for invalid format
        assert frontmatter is None or len(frontmatter) == 0

    def test_frontmatter_optional_fields(self):
        """Test optional fields in frontmatter."""
        agent_content = """---
name: test_agent
description: Test agent with optional fields
version: 1.0.0
base_version: 1.0.0
tools: Read, Write
model: sonnet
color: blue
priority: high
tags: testing, validation, frontmatter
---

Content
"""
        agent_file = self / "test_optional.md"
        agent_file.write_text(agent_content)

        frontmatter = self._extract_frontmatter(agent_file)

        # Required fields should be present
        assert frontmatter["name"] == "test_agent"
        assert frontmatter["version"] == "1.0.0"

        # Optional fields should also be present
        assert frontmatter.get("color") == "blue"
        assert frontmatter.get("priority") == "high"
        assert "testing" in frontmatter.get("tags", "")

    # Helper methods

    def _extract_frontmatter(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Extract YAML frontmatter from a markdown file."""
        content = file_path.read_text()

        # Check for frontmatter delimiters
        if not content.startswith("---"):
            return None

        # Find the closing delimiter
        lines = content.split("\n")
        end_index = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_index = i
                break

        if end_index == -1:
            return None

        # Extract YAML content
        yaml_content = "\n".join(lines[1:end_index])

        try:
            return yaml.safe_load(yaml_content)
        except yaml.YAMLError:
            return None

    def _extract_frontmatter_and_content(self, file_path: Path) -> tuple:
        """Extract both frontmatter and content from a markdown file."""
        content = file_path.read_text()

        if not content.startswith("---"):
            return None, content

        lines = content.split("\n")
        end_index = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_index = i
                break

        if end_index == -1:
            return None, content

        yaml_content = "\n".join(lines[1:end_index])
        main_content = "\n".join(lines[end_index + 1 :])

        try:
            frontmatter = yaml.safe_load(yaml_content)
            return frontmatter, main_content
        except yaml.YAMLError:
            return None, content

    def _validate_frontmatter(self, frontmatter: Optional[Dict[str, Any]]) -> List[str]:
        """Validate frontmatter and return list of errors."""
        errors = []

        if frontmatter is None:
            errors.append("No valid frontmatter found")
            return errors

        # Check required fields
        required_fields = [
            "name",
            "description",
            "version",
            "base_version",
            "tools",
            "model",
        ]
        for field in required_fields:
            if field not in frontmatter or not frontmatter[field]:
                errors.append(f"Missing required field: {field}")

        # Validate version format
        if "version" in frontmatter:
            if not self._is_valid_semantic_version(frontmatter["version"]):
                errors.append(f"Invalid version format: {frontmatter['version']}")

        if "base_version" in frontmatter:
            if not self._is_valid_semantic_version(frontmatter["base_version"]):
                errors.append(
                    f"Invalid base_version format: {frontmatter['base_version']}"
                )

        # Validate model value
        if "model" in frontmatter:
            valid_models = ["haiku", "sonnet", "opus"]
            if frontmatter["model"] not in valid_models:
                errors.append(
                    f"Invalid model: {frontmatter['model']}. Must be one of {valid_models}"
                )

        return errors

    def _is_valid_semantic_version(self, version) -> bool:
        """Check if a version string follows semantic versioning format."""
        # Convert to string if not already
        version = str(version) if version is not None else ""

        if not version:
            return False

        # Remove 'v' prefix if present
        if version.startswith("v"):
            version = version[1:]

        # Check for semantic version pattern
        pattern = r"^\d+\.\d+\.\d+$"
        return bool(re.match(pattern, version))

    def _create_agent_content(self, exclude_field: Optional[str] = None) -> str:
        """Create agent content with optional field exclusion."""
        fields = {
            "name": "test_agent",
            "description": "Test agent",
            "version": "1.0.0",
            "base_version": "1.0.0",
            "tools": "Read, Write",
            "model": "sonnet",
        }

        if exclude_field and exclude_field in fields:
            del fields[exclude_field]

        yaml_lines = ["---"]
        for key, value in fields.items():
            yaml_lines.append(f"{key}: {value}")
        yaml_lines.append("---")
        yaml_lines.append("")
        yaml_lines.append("Test content")

        return "\n".join(yaml_lines)
