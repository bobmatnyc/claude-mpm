"""Agent Template Builder Service

This service handles the building and generation of agent templates,
including YAML and Markdown generation, template merging, and metadata extraction.

Extracted from AgentDeploymentService as part of the refactoring to improve
maintainability and testability.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from claude_mpm.core.logging_config import get_logger


class AgentTemplateBuilder:
    """Service for building agent templates from JSON and base agent data.

    This service handles:
    - Building agent markdown files with YAML frontmatter
    - Building agent YAML files
    - Merging narrative and configuration fields
    - Extracting agent metadata
    - Formatting YAML lists
    """

    def __init__(self):
        """Initialize the template builder."""
        self.logger = get_logger(__name__)

    def build_agent_markdown(
        self,
        agent_name: str,
        template_path: Path,
        base_agent_data: dict,
        source_info: str = "unknown",
    ) -> str:
        """
        Build a complete agent markdown file with YAML frontmatter.

        Args:
            agent_name: Name of the agent
            template_path: Path to the agent template JSON file
            base_agent_data: Base agent configuration data
            source_info: Source of the agent (system/project/user)

        Returns:
            Complete markdown content with YAML frontmatter

        Raises:
            FileNotFoundError: If template file doesn't exist
            json.JSONDecodeError: If template JSON is invalid
        """
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        try:
            template_content = template_path.read_text()
            template_data = json.loads(template_content)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in template {template_path}: {e}")
            raise

        # Extract tools from template with fallback
        # Handle both dict and list formats for capabilities (backward compatibility)
        capabilities = template_data.get("capabilities", {})
        capabilities_tools = (
            capabilities.get("tools") if isinstance(capabilities, dict) else None
        )

        tools = (
            template_data.get("tools")
            or capabilities_tools
            or template_data.get("configuration_fields", {}).get("tools")
            or ["Read", "Write", "Edit", "Grep", "Glob", "LS"]  # Default fallback
        )

        # Extract model from template with fallback
        capabilities_model = (
            capabilities.get("model") if isinstance(capabilities, dict) else None
        )

        model = (
            template_data.get("model")
            or capabilities_model
            or template_data.get("configuration_fields", {}).get("model")
            or "sonnet"  # Default fallback
        )

        # Convert tools list to comma-separated string (no spaces!)
        tools_str = ",".join(tools) if isinstance(tools, list) else str(tools)

        # Validate tools format - CRITICAL: No spaces allowed!
        if ", " in tools_str:
            self.logger.error(f"Tools contain spaces: '{tools_str}'")
            raise ValueError(
                f"Tools must be comma-separated WITHOUT spaces: {tools_str}"
            )

        # Map model names to Claude Code format
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

        if model in model_map:
            model = model_map[model]

        # Get response format from template or use base agent default
        template_data.get("response", {}).get("format", "structured")

        # Create Claude Code compatible name (lowercase, hyphens only)
        claude_code_name = agent_name.lower().replace("_", "-")

        # CRITICAL: NO underscores allowed - they cause silent failures!

        # Validate the name before proceeding
        import re

        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", claude_code_name):
            self.logger.error(
                f"Invalid agent name '{claude_code_name}' - must match ^[a-z0-9]+(-[a-z0-9]+)*$"
            )
            raise ValueError(
                f"Agent name '{claude_code_name}' does not meet Claude Code requirements"
            )

        # Extract description from template with fallback
        description = (
            template_data.get("description")
            or template_data.get("metadata", {}).get("description")
            or f"{agent_name.title()} agent for specialized tasks"
        )

        # Extract custom metadata fields
        metadata = template_data.get("metadata", {})
        agent_version = (
            template_data.get("agent_version")
            or template_data.get("version")
            or metadata.get("version", "1.0.0")
        )
        agent_type = template_data.get("agent_type", "general")
        # Use the capabilities_model we already extracted earlier
        model_type = capabilities_model or "sonnet"

        # Map our model types to Claude Code format
        if model_type in ["opus", "sonnet", "haiku"]:
            # Use inherit for now - Claude Code seems to prefer this
            pass
        else:
            pass

        # Determine color - prefer template's color, fallback to type-based defaults
        template_metadata = template_data.get("metadata", {})
        template_color = template_metadata.get("color")

        if template_color:
            # Use the color specified in the template
            color = template_color
        else:
            # Fallback to default color map based on agent type
            color_map = {
                "engineer": "blue",
                "qa": "green",
                "security": "red",
                "research": "purple",
                "documentation": "cyan",  # Changed default to match template preference
                "ops": "gray",
            }
            color = color_map.get(agent_type, "blue")

        # Check if we should include tools field (only if significantly restricting)
        # Claude Code approach: omit tools field unless specifically restricting

        # Convert tools to set for comparison
        agent_tools = set(tools) if isinstance(tools, list) else set(tools.split(","))

        # Only include tools field if agent is missing several important tools
        # This matches Claude Code's approach of omitting tools for general-purpose agents
        core_tools = {"Read", "Write", "Edit", "Bash", "Grep", "Glob"}
        has_core_tools = len(agent_tools.intersection(core_tools)) >= 5

        # Include tools field only if agent is clearly restricted (missing core tools or very few tools)
        include_tools_field = not has_core_tools or len(agent_tools) < 6

        # Build YAML frontmatter using Claude Code's working format + our custom fields
        frontmatter_lines = [
            "---",
            f"name: {claude_code_name}",
            f"description: {description}",
        ]

        # Only include tools if restricting to subset
        if include_tools_field:
            frontmatter_lines.append(f"tools: {tools_str}")

        frontmatter_lines.extend(
            [
                f"model: {model_type}",  # Use explicit model type instead of inherit
                f"color: {color}",
                f"version: {agent_version}",
                f"type: {agent_type}",
                f"source: {source_info}",  # Track which source provided this agent
                "author: claude-mpm",  # Mark as system-managed agent
                "---",
                "",
            ]
        )

        frontmatter = "\n".join(frontmatter_lines)

        # Get agent instructions from template data (primary) or base agent data (fallback)
        content = (
            template_data.get("instructions")
            or base_agent_data.get("content")
            or base_agent_data.get("instructions")
            or "# Agent Instructions\n\nThis agent provides specialized assistance."
        )

        # Add memory update instructions if not already present
        if "memory-update" not in content and "Remember" not in content:
            memory_instructions = """

## Memory Updates

When you learn something important about this project that would be useful for future tasks, include it in your response JSON block:

```json
{
  "memory-update": {
    "Project Architecture": ["Key architectural patterns or structures"],
    "Implementation Guidelines": ["Important coding standards or practices"],
    "Current Technical Context": ["Project-specific technical details"]
  }
}
```

Or use the simpler "remember" field for general learnings:

```json
{
  "remember": ["Learning 1", "Learning 2"]
}
```

Only include memories that are:
- Project-specific (not generic programming knowledge)
- Likely to be useful in future tasks
- Not already documented elsewhere
"""
            content = content + memory_instructions

        return frontmatter + content

    def build_agent_yaml(
        self, agent_name: str, template_path: Path, base_agent_data: dict
    ) -> str:
        """
        Build a complete agent YAML file by combining base agent and template.
        Only includes essential fields for Claude Code best practices.

        Args:
            agent_name: Name of the agent
            template_path: Path to the agent template JSON file
            base_agent_data: Base agent configuration data

        Returns:
            Complete YAML content

        Raises:
            FileNotFoundError: If template file doesn't exist
            json.JSONDecodeError: If template JSON is invalid
        """
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        try:
            template_content = template_path.read_text()
            template_data = json.loads(template_content)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in template {template_path}: {e}")
            raise

        # Merge narrative and configuration fields
        self.merge_narrative_fields(base_agent_data, template_data)
        merged_config = self.merge_configuration_fields(base_agent_data, template_data)

        # Extract essential fields for Claude Code
        name = template_data.get("name", agent_name)
        description = template_data.get(
            "description", f"{name} agent for specialized tasks"
        )

        # Get tools and model with fallbacks
        tools = merged_config.get("tools", ["Read", "Write", "Edit"])
        model = merged_config.get("model", "sonnet")

        # Format tools as YAML list
        tools_yaml = self.format_yaml_list(tools, 2)

        # Build YAML content with only essential fields
        return f"""name: {name}
description: {description}
model: {model}
tools:
{tools_yaml}
"""

    def merge_narrative_fields(self, base_data: dict, template_data: dict) -> dict:
        """
        Merge narrative fields from base and template, combining arrays.

        Args:
            base_data: Base agent data
            template_data: Template agent data

        Returns:
            Merged narrative fields
        """
        merged = {}

        # Fields that should be combined (arrays)
        combinable_fields = [
            "when_to_use",
            "specialized_knowledge",
            "unique_capabilities",
        ]

        for field in combinable_fields:
            base_value = base_data.get(field, [])
            template_value = template_data.get(field, [])

            # Ensure both are lists
            if not isinstance(base_value, list):
                base_value = [base_value] if base_value else []
            if not isinstance(template_value, list):
                template_value = [template_value] if template_value else []

            # Combine and deduplicate
            combined = list(set(base_value + template_value))
            merged[field] = combined

        return merged

    def merge_configuration_fields(self, base_data: dict, template_data: dict) -> dict:
        """
        Merge configuration fields, with template overriding base.

        Args:
            base_data: Base agent data
            template_data: Template agent data

        Returns:
            Merged configuration fields
        """
        merged = {}

        # Start with base configuration
        if "configuration_fields" in base_data:
            merged.update(base_data["configuration_fields"])

        # Override with template configuration
        if "configuration_fields" in template_data:
            merged.update(template_data["configuration_fields"])

        # Also check for direct fields in template
        direct_fields = ["tools", "model", "timeout", "max_tokens"]
        for field in direct_fields:
            if field in template_data:
                merged[field] = template_data[field]

        return merged

    def extract_agent_metadata(self, template_content: str) -> Dict[str, Any]:
        """
        Extract metadata from simplified agent template content.

        Args:
            template_content: Agent template markdown content

        Returns:
            Dictionary containing extracted metadata
        """
        metadata = {}
        current_section = None
        section_content = []

        lines = template_content.split("\n")

        for line in lines:
            line = line.strip()

            # Check for section headers
            if line.startswith("## "):
                # Save previous section
                if current_section and section_content:
                    metadata[current_section] = section_content.copy()

                # Start new section
                current_section = line[3:].lower().replace(" ", "_")
                section_content = []

            elif line.startswith("- ") and current_section:
                # Add list item to current section
                section_content.append(line[2:])

            elif line and current_section and not line.startswith("#"):
                # Add non-empty, non-header line to current section
                section_content.append(line)

        # Save final section
        if current_section and section_content:
            metadata[current_section] = section_content.copy()

        # Ensure all required fields have defaults
        metadata.setdefault("when_to_use", [])
        metadata.setdefault("specialized_knowledge", [])
        metadata.setdefault("unique_capabilities", [])

        return metadata

    def format_yaml_list(self, items: List[str], indent: int) -> str:
        """
        Format a list for YAML with proper indentation.

        Args:
            items: List of items to format
            indent: Number of spaces for indentation

        Returns:
            Formatted YAML list string
        """
        if not items:
            return ""

        indent_str = " " * indent
        formatted_items = []

        for item in items:
            formatted_items.append(f"{indent_str}- {item}")

        return "\n".join(formatted_items)
