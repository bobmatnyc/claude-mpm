"""Agent validator for deployed agent files."""

import re
from pathlib import Path
from typing import Any, Dict

import yaml

from claude_mpm.core.logger import get_logger

from .validation_result import ValidationResult


class AgentValidator:
    """Validator for deployed agent markdown files.

    This validator checks deployed agent .md files for:
    - Valid YAML frontmatter
    - Required frontmatter fields
    - Proper markdown structure
    - Content validation
    """

    def __init__(self):
        """Initialize the agent validator."""
        self.logger = get_logger(__name__)

        # Required frontmatter fields
        self.required_frontmatter_fields = {
            "name": str,
            "description": str,
            "author": str,
            "version": str,
            "model": str,
            "tools": list,
        }

    def validate_agent_file(self, agent_file: Path) -> ValidationResult:
        """Validate a deployed agent file.

        Args:
            agent_file: Path to agent markdown file

        Returns:
            ValidationResult with validation outcome
        """
        result = ValidationResult(is_valid=True)

        # Check if file exists
        if not agent_file.exists():
            result.add_error(f"Agent file does not exist: {agent_file}")
            return result

        # Check if it's a file
        if not agent_file.is_file():
            result.add_error(f"Agent path is not a file: {agent_file}")
            return result

        try:
            # Read file content
            content = agent_file.read_text(encoding="utf-8")

            # Validate frontmatter
            frontmatter_result = self._validate_frontmatter(content)
            result = result.merge(frontmatter_result)

            # Validate markdown structure
            markdown_result = self._validate_markdown_structure(content)
            result = result.merge(markdown_result)

            # Add metadata
            result.metadata["agent_file"] = str(agent_file)
            result.metadata["agent_name"] = agent_file.stem

        except UnicodeDecodeError as e:
            result.add_error(f"File encoding error: {e}")
        except Exception as e:
            result.add_error(f"Unexpected error reading agent file: {e}")

        return result

    def _validate_frontmatter(self, content: str) -> ValidationResult:
        """Validate YAML frontmatter in agent file.

        Args:
            content: File content

        Returns:
            ValidationResult for frontmatter validation
        """
        result = ValidationResult(is_valid=True)

        # Check if content starts with frontmatter
        if not content.startswith("---"):
            result.add_error("Agent file must start with YAML frontmatter (---)")
            return result

        # Extract frontmatter
        frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not frontmatter_match:
            result.add_error("Invalid frontmatter format - missing closing ---")
            return result

        frontmatter_content = frontmatter_match.group(1)

        try:
            # Parse YAML
            frontmatter_data = yaml.safe_load(frontmatter_content)

            if not isinstance(frontmatter_data, dict):
                result.add_error("Frontmatter must be a YAML dictionary")
                return result

            # Validate required fields
            self._validate_frontmatter_fields(frontmatter_data, result)

            # Validate specific field values
            self._validate_frontmatter_values(frontmatter_data, result)

        except yaml.YAMLError as e:
            result.add_error(f"Invalid YAML in frontmatter: {e}")

        return result

    def _validate_frontmatter_fields(
        self, frontmatter: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate frontmatter fields.

        Args:
            frontmatter: Frontmatter dictionary
            result: ValidationResult to update
        """
        for field, expected_type in self.required_frontmatter_fields.items():
            if field not in frontmatter:
                result.add_error(f"Missing required frontmatter field: {field}")
            else:
                value = frontmatter[field]
                if not isinstance(value, expected_type):
                    result.add_error(
                        f"Frontmatter field '{field}' should be {expected_type.__name__}, got {type(value).__name__}",
                        field_name=field,
                    )

    def _validate_frontmatter_values(
        self, frontmatter: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate frontmatter field values.

        Args:
            frontmatter: Frontmatter dictionary
            result: ValidationResult to update
        """
        # Validate name
        if "name" in frontmatter:
            name = frontmatter["name"]
            if not name or not str(name).strip():
                result.add_error("Agent name cannot be empty", field_name="name")

        # Validate description
        if "description" in frontmatter:
            description = frontmatter["description"]
            if not description or not str(description).strip():
                result.add_error(
                    "Agent description cannot be empty", field_name="description"
                )

        # Validate author
        if "author" in frontmatter:
            author = frontmatter["author"]
            if not author or not str(author).strip():
                result.add_error("Agent author cannot be empty", field_name="author")

        # Validate version
        if "version" in frontmatter:
            version = frontmatter["version"]
            if not self._is_valid_version(str(version)):
                result.add_warning(
                    f"Version '{version}' does not follow semantic versioning",
                    field_name="version",
                    suggestion="Use semantic versioning (e.g., '1.0.0')",
                )

        # Validate model
        if "model" in frontmatter:
            model = frontmatter["model"]
            valid_models = ["sonnet", "haiku", "opus"]
            if model not in valid_models:
                result.add_warning(
                    f"Unknown model '{model}'",
                    field_name="model",
                    suggestion=f"Use one of: {', '.join(valid_models)}",
                )

        # Validate tools
        if "tools" in frontmatter:
            tools = frontmatter["tools"]
            if not isinstance(tools, list):
                result.add_error("Tools should be a list", field_name="tools")
            elif len(tools) == 0:
                result.add_warning("No tools specified", field_name="tools")
            else:
                # Check for common tool names
                for tool in tools:
                    if not isinstance(tool, str):
                        result.add_warning(
                            f"Tool '{tool}' should be a string", field_name="tools"
                        )

    def _validate_markdown_structure(self, content: str) -> ValidationResult:
        """Validate markdown structure of agent file.

        Args:
            content: File content

        Returns:
            ValidationResult for markdown validation
        """
        result = ValidationResult(is_valid=True)

        # Remove frontmatter for markdown analysis
        content_without_frontmatter = re.sub(
            r"^---\n.*?\n---\n", "", content, flags=re.DOTALL
        )

        # Check if there's content after frontmatter
        if not content_without_frontmatter.strip():
            result.add_warning("Agent file has no content after frontmatter")
            return result

        # Check for basic markdown structure
        lines = content_without_frontmatter.split("\n")

        # Look for at least one heading or substantial content
        has_heading = any(line.strip().startswith("#") for line in lines)
        has_content = any(len(line.strip()) > 10 for line in lines)

        if not has_heading and not has_content:
            result.add_warning("Agent file appears to have minimal content")

        # Check for common sections
        content_lower = content_without_frontmatter.lower()
        if "instruction" not in content_lower and "prompt" not in content_lower:
            result.add_info("Agent file may benefit from explicit instructions section")

        return result

    def _is_valid_version(self, version: str) -> bool:
        """Check if version follows semantic versioning.

        Args:
            version: Version string to validate

        Returns:
            True if version is valid semantic version
        """
        # Simple semantic version pattern
        pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$"
        return bool(re.match(pattern, version))

    def repair_agent_file(
        self, agent_file: Path, dry_run: bool = True
    ) -> ValidationResult:
        """Attempt to repair common issues in agent file.

        Args:
            agent_file: Path to agent file
            dry_run: If True, don't actually modify the file

        Returns:
            ValidationResult with repair information
        """
        result = ValidationResult(is_valid=True)

        try:
            content = agent_file.read_text(encoding="utf-8")
            original_content = content

            # Try to fix common frontmatter issues
            content = self._repair_frontmatter(content, result)

            # If changes were made and not dry run, write back
            if content != original_content:
                if not dry_run:
                    agent_file.write_text(content, encoding="utf-8")
                    result.add_info(f"Repaired agent file: {agent_file}")
                else:
                    result.add_info(f"Would repair agent file: {agent_file} (dry run)")
            else:
                result.add_info("No repairs needed")

        except Exception as e:
            result.add_error(f"Failed to repair agent file: {e}")

        return result

    def _repair_frontmatter(self, content: str, result: ValidationResult) -> str:
        """Attempt to repair frontmatter issues.

        Args:
            content: File content
            result: ValidationResult to update with repair info

        Returns:
            Repaired content
        """
        # This is a simplified repair - in practice, you'd want more sophisticated logic
        if not content.startswith("---"):
            result.add_info("Added missing frontmatter delimiters")
            # Add basic frontmatter if missing
            basic_frontmatter = """---
name: "Unknown Agent"
description: "Agent description needed"
author: "claude-mpm"
version: "1.0.0"
model: "sonnet"
tools: []
---

"""
            return basic_frontmatter + content

        return content
