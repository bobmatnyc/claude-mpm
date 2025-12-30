"""Agent Format Converter Service

This service handles format conversion between different agent file formats,
particularly YAML to Markdown conversion and format migration utilities.

Extracted from AgentDeploymentService as part of the refactoring to improve
maintainability and testability.
"""

import re
from pathlib import Path
from typing import Any, Dict, Optional

from claude_mpm.core.logging_config import get_logger


class AgentFormatConverter:
    """Service for converting agent files between different formats.

    This service handles:
    - YAML to Markdown conversion with YAML frontmatter
    - Format migration and backward compatibility
    - Field extraction from various formats
    - Content structure transformation
    """

    def __init__(self):
        """Initialize the agent format converter."""
        self.logger = get_logger(__name__)

    def convert_yaml_to_md(self, target_dir: Path) -> Dict[str, Any]:
        """
        Convert existing YAML agent files to MD format with YAML frontmatter.

        This method handles backward compatibility by finding existing .yaml
        agent files and converting them to .md format expected by Claude Code.

        Args:
            target_dir: Directory containing agent files to convert

        Returns:
            Dictionary with conversion results
        """
        results = {"converted": [], "errors": [], "skipped": []}

        if not target_dir.exists():
            self.logger.debug(f"Target directory does not exist: {target_dir}")
            return results

        try:
            # Find YAML files that need conversion
            yaml_files = list(target_dir.glob("*.yaml"))

            for yaml_file in yaml_files:
                try:
                    # Check if corresponding MD file already exists
                    md_file = yaml_file.with_suffix(".md")

                    if md_file.exists():
                        # Check modification times
                        yaml_mtime = yaml_file.stat().st_mtime
                        md_mtime = md_file.stat().st_mtime

                        if md_mtime >= yaml_mtime:
                            # MD file is newer or same age, skip conversion
                            results["skipped"].append(yaml_file.name)
                            continue
                        # MD file is older, proceed with conversion
                        self.logger.info(
                            f"MD file {md_file.name} is older than YAML, converting..."
                        )

                    # Read YAML content
                    yaml_content = yaml_file.read_text()

                    # Convert to MD format
                    md_content = self.convert_yaml_content_to_md(
                        yaml_content, yaml_file.stem
                    )

                    # Write MD file
                    md_file.write_text(md_content)

                    # Remove original YAML file
                    yaml_file.unlink()

                    results["converted"].append(
                        {"from": yaml_file.name, "to": md_file.name}
                    )

                    self.logger.info(f"Converted {yaml_file.name} to {md_file.name}")

                except Exception as e:
                    error_msg = f"Failed to convert {yaml_file.name}: {e}"
                    results["errors"].append(error_msg)
                    self.logger.error(error_msg)

        except Exception as e:
            error_msg = f"YAML to MD conversion failed: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)

        return results

    def convert_yaml_content_to_md(self, yaml_content: str, agent_name: str) -> str:
        """
        Convert YAML agent content to MD format with YAML frontmatter.

        Args:
            yaml_content: Original YAML content
            agent_name: Name of the agent

        Returns:
            Converted Markdown content with YAML frontmatter
        """
        # Extract fields from YAML content
        name = self.extract_yaml_field(yaml_content, "name") or agent_name
        description = (
            self.extract_yaml_field(yaml_content, "description")
            or f"{agent_name.title()} agent for specialized tasks"
        )
        version = self.extract_yaml_field(yaml_content, "version") or "1.0.0"
        tools_line = (
            self.extract_yaml_field(yaml_content, "tools")
            or "Read,Write,Edit,Grep,Glob,LS"
        )

        # Convert tools string to list format if needed
        if isinstance(tools_line, str):
            if tools_line.startswith("[") and tools_line.endswith("]"):
                # Already in list format
                pass
            else:
                # Convert comma-separated to list
                tools = [tool.strip() for tool in tools_line.split(",")]
                str(tools).replace("'", '"')
        else:
            pass

        # Extract additional fields - model is optional (Claude Code uses conversation model if not set)
        model = self.extract_yaml_field(yaml_content, "model")  # None if not specified
        author = (
            self.extract_yaml_field(yaml_content, "author")
            or "claude-mpm@anthropic.com"
        )

        # Extract instructions from YAML content
        instructions = self._extract_instructions_from_yaml(yaml_content, agent_name)

        # Map model names to Claude Code format (only if model is specified)
        model_map = {
            "claude-3-5-sonnet-20241022": "sonnet",
            "claude-3-5-sonnet": "sonnet",
            "claude-3-sonnet": "sonnet",
            "claude-3-haiku": "haiku",
            "claude-3-opus": "opus",
            "sonnet": "sonnet",
            "haiku": "haiku",
            "opus": "opus",
        }

        # Only map model if it's not None (preserve None for agents without model field)
        mapped_model = model_map.get(model, model) if model is not None else None

        # Create multiline description with example (Claude Code format)
        multiline_description = f"""{description}

<example>
Context: When you need specialized assistance from the {name} agent.
user: "I need help with {agent_name.replace("_", " ").replace("-", " ")} tasks"
assistant: "I'll use the {name} agent to provide specialized assistance."
</example>"""

        # Build new YAML frontmatter - Claude Code compatible format
        # NOTE: Removed tags field and other non-essential fields for Claude Code compatibility
        frontmatter_lines = [
            "---",
            f"name: {name}",
            "description: |",
            f"  {self._indent_text(multiline_description, 2)}",
        ]

        # Only include model field if explicitly set in source
        if mapped_model is not None:
            frontmatter_lines.append(f"model: {mapped_model}")

        frontmatter_lines.extend(
            [
                f'version: "{version}"',
                f'author: "{author}"',
                "---",
                "",
            ]
        )

        new_frontmatter = "\n".join(frontmatter_lines)

        return new_frontmatter + instructions

    def extract_yaml_field(self, yaml_content: str, field_name: str) -> Optional[str]:
        """
        Extract a field value from YAML content.

        Args:
            yaml_content: YAML content string
            field_name: Name of the field to extract

        Returns:
            Field value or None if not found
        """
        # Try to match multi-line field first (with | or >)
        multiline_pattern = rf"^{field_name}:\s*[|>]\s*\n((?:[ \t]+.+\n?)*)"
        multiline_match = re.search(multiline_pattern, yaml_content, re.MULTILINE)
        if multiline_match:
            # Extract indented content and remove common indentation
            lines = multiline_match.group(1).split("\n")
            # Remove empty lines at the end
            while lines and not lines[-1].strip():
                lines.pop()

            if lines:
                # Find minimum indentation (excluding empty lines)
                min_indent = float("inf")
                for line in lines:
                    if line.strip():  # Skip empty lines
                        indent = len(line) - len(line.lstrip())
                        min_indent = min(min_indent, indent)

                # Remove common indentation
                if min_indent != float("inf"):
                    dedented_lines = []
                    for line in lines:
                        if line.strip():  # Non-empty line
                            dedented_lines.append(line[min_indent:])
                        else:  # Empty line
                            dedented_lines.append("")
                    return "\n".join(dedented_lines).strip()

        # Try to match field with various quote styles
        patterns = [
            rf'^{field_name}:\s*"([^"]*)"',  # Double quotes
            rf"^{field_name}:\s*'([^']*)'",  # Single quotes
            rf"^{field_name}:\s*([^\n\r]+)",  # No quotes
        ]

        for pattern in patterns:
            match = re.search(pattern, yaml_content, re.MULTILINE)
            if match:
                value = match.group(1).strip()
                if value:
                    return value

        return None

    def convert_md_to_yaml(self, md_content: str) -> str:
        """
        Convert Markdown with YAML frontmatter back to pure YAML format.

        Args:
            md_content: Markdown content with YAML frontmatter

        Returns:
            Pure YAML content
        """
        if not md_content.strip().startswith("---"):
            # No frontmatter, treat as plain YAML
            return md_content

        # Split frontmatter and markdown content
        parts = md_content.split("---", 2)
        if len(parts) < 3:
            return md_content

        frontmatter = parts[1].strip()
        markdown_content = parts[2].strip()

        # Add instructions field if there's markdown content
        if markdown_content:
            frontmatter += "\ninstructions: |\n"
            # Indent markdown content
            for line in markdown_content.split("\n"):
                frontmatter += f"  {line}\n"

        return frontmatter

    def detect_format(self, content: str) -> str:
        """
        Detect the format of agent content.

        Args:
            content: Agent file content

        Returns:
            Format type: 'markdown_yaml', 'yaml', 'json', or 'unknown'
        """
        content = content.strip()

        if content.startswith("---") and "---" in content[3:]:
            return "markdown_yaml"
        if content.startswith("{") and content.endswith("}"):
            return "json"
        if ":" in content and not content.startswith("#"):
            # Likely YAML if it has key-value pairs and doesn't start with markdown header
            return "yaml"
        return "unknown"

    def normalize_agent_content(
        self, content: str, agent_name: str, target_format: str = "markdown_yaml"
    ) -> str:
        """
        Normalize agent content to a specific format.

        Args:
            content: Original agent content
            agent_name: Name of the agent
            target_format: Target format ('markdown_yaml', 'yaml', 'json')

        Returns:
            Normalized content in target format
        """
        current_format = self.detect_format(content)

        if current_format == target_format:
            return content

        # Convert to intermediate format first (markdown_yaml)
        if current_format == "yaml":
            intermediate = self.convert_yaml_content_to_md(content, agent_name)
        elif current_format == "json":
            intermediate = self._convert_json_to_md(content, agent_name)
        else:
            intermediate = content

        # Convert to target format
        if target_format == "yaml":
            return self.convert_md_to_yaml(intermediate)
        if target_format == "json":
            return self._convert_md_to_json(intermediate)
        return intermediate

    def get_conversion_stats(self, target_dir: Path) -> Dict[str, Any]:
        """
        Get statistics about files that need conversion.

        Args:
            target_dir: Directory to analyze

        Returns:
            Dictionary with conversion statistics
        """
        stats = {
            "total_files": 0,
            "yaml_files": 0,
            "md_files": 0,
            "json_files": 0,
            "needs_conversion": 0,
            "formats": {},
        }

        if not target_dir.exists():
            return stats

        # Analyze all agent files
        for file_path in target_dir.glob("*"):
            if file_path.is_file() and file_path.suffix in [
                ".yaml",
                ".yml",
                ".md",
                ".json",
            ]:
                stats["total_files"] += 1

                if file_path.suffix in [".yaml", ".yml"]:
                    stats["yaml_files"] += 1
                    # Check if corresponding .md file exists
                    md_file = file_path.with_suffix(".md")
                    if not md_file.exists():
                        stats["needs_conversion"] += 1
                elif file_path.suffix == ".md":
                    stats["md_files"] += 1
                elif file_path.suffix == ".json":
                    stats["json_files"] += 1

                # Detect format
                try:
                    content = file_path.read_text()
                    format_type = self.detect_format(content)
                    stats["formats"][format_type] = (
                        stats["formats"].get(format_type, 0) + 1
                    )
                except Exception:
                    stats["formats"]["unreadable"] = (
                        stats["formats"].get("unreadable", 0) + 1
                    )

        return stats

    def _extract_instructions_from_yaml(
        self, yaml_content: str, agent_name: str
    ) -> str:
        """
        Extract instructions from YAML content.

        Args:
            yaml_content: YAML content
            agent_name: Agent name for default instructions

        Returns:
            Instructions text
        """
        # Try to extract instructions field
        instructions = self.extract_yaml_field(yaml_content, "instructions")
        if instructions:
            return instructions

        # Try to extract description as instructions
        description = self.extract_yaml_field(yaml_content, "description")
        if (
            description and len(description) > 50
        ):  # Long description might be instructions
            return f"# {agent_name.title()} Agent\n\n{description}"

        # Default instructions
        return f"# {agent_name.title()} Agent\n\nThis agent provides specialized functionality for your tasks."

    def _convert_json_to_md(self, json_content: str, agent_name: str) -> str:
        """Convert JSON content to Markdown with YAML frontmatter."""
        try:
            import json

            data = json.loads(json_content)

            # Convert JSON data to YAML-like string for processing
            yaml_lines = []
            for key, value in data.items():
                if isinstance(value, str):
                    yaml_lines.append(f'{key}: "{value}"')
                elif isinstance(value, list):
                    yaml_lines.append(f"{key}: {json.dumps(value)}")
                else:
                    yaml_lines.append(f"{key}: {value}")

            yaml_content = "\n".join(yaml_lines)
            return self.convert_yaml_content_to_md(yaml_content, agent_name)

        except Exception as e:
            self.logger.error(f"Failed to convert JSON to MD: {e}")
            return f"# {agent_name.title()} Agent\n\nConversion failed: {e}"

    def _convert_md_to_json(self, md_content: str) -> str:
        """Convert Markdown with YAML frontmatter to JSON."""
        try:
            import json

            import yaml

            if not md_content.strip().startswith("---"):
                return json.dumps({"error": "No YAML frontmatter found"})

            # Extract frontmatter
            parts = md_content.split("---", 2)
            if len(parts) < 3:
                return json.dumps({"error": "Invalid frontmatter format"})

            frontmatter = parts[1].strip()
            markdown_content = parts[2].strip()

            # Parse YAML frontmatter
            data = yaml.safe_load(frontmatter)

            # Add instructions from markdown content
            if markdown_content:
                data["instructions"] = markdown_content

            return json.dumps(data, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to convert MD to JSON: {e}")
            return json.dumps({"error": str(e)})

    def _indent_text(self, text: str, spaces: int) -> str:
        """
        Indent multiline text with specified number of spaces.

        Args:
            text: Text to indent
            spaces: Number of spaces for indentation

        Returns:
            Indented text
        """
        if not text:
            return ""

        indent = " " * spaces
        lines = text.split("\n")
        indented_lines = []

        for line in lines:
            if line.strip():  # Non-empty lines get indented
                indented_lines.append(indent + line)
            else:  # Empty lines stay empty
                indented_lines.append("")

        return "\n".join(indented_lines)
