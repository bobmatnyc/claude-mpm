"""Agent Template Builder Service

This service handles the building and generation of agent templates,
including YAML and Markdown generation, template merging, and metadata extraction.

Extracted from AgentDeploymentService as part of the refactoring to improve
maintainability and testability.
"""

import json
import re
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

    def _load_base_agent_instructions(self, agent_type: str) -> str:
        """Load BASE instructions for a specific agent type.

        Args:
            agent_type: The type of agent (engineer, qa, ops, research, documentation)

        Returns:
            The BASE instructions content or empty string if not found
        """
        if not agent_type:
            return ""

        try:
            # Construct BASE file name
            base_file = f"BASE_{agent_type.upper()}.md"

            # Try to find BASE file in agents directory
            # First try current working directory structure
            agents_dir = Path(__file__).parent.parent.parent.parent / "agents"
            base_path = agents_dir / base_file

            if not base_path.exists():
                # Try packaged resources if available
                try:
                    from importlib.resources import files

                    agents_package = files("claude_mpm.agents")
                    base_resource = agents_package / base_file
                    if base_resource.is_file():
                        content = base_resource.read_text(encoding="utf-8")
                        self.logger.debug(
                            f"Loaded BASE instructions from package: {base_file}"
                        )
                        return content
                except (ImportError, Exception) as e:
                    self.logger.debug(
                        f"Could not load BASE instructions from package: {e}"
                    )

                # Final fallback - try multiple possible locations
                possible_paths = [
                    Path.cwd() / "src" / "claude_mpm" / "agents" / base_file,
                    Path(__file__).parent.parent.parent.parent / "agents" / base_file,
                    Path.home() / ".claude-mpm" / "agents" / base_file,
                ]

                for path in possible_paths:
                    if path.exists():
                        base_path = path
                        break
                else:
                    self.logger.debug(
                        f"No BASE instructions found for type: {agent_type}"
                    )
                    return ""

            if base_path.exists():
                self.logger.debug(f"Loading BASE instructions from {base_path}")
                return base_path.read_text(encoding="utf-8")
            self.logger.debug(f"No BASE instructions found for type: {agent_type}")
            return ""

        except Exception as e:
            self.logger.warning(
                f"Error loading BASE instructions for {agent_type}: {e}"
            )
            return ""

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

        # Map model names to Claude Code format (as required)
        model_map = {
            "claude-3-5-sonnet-20241022": "sonnet",
            "claude-3-5-haiku-20241022": "haiku",
            "claude-3-opus-20240229": "opus",
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
        else:
            # Default to sonnet if model not found in map
            model = "sonnet"

        # Get response format from template or use base agent default
        template_data.get("response", {}).get("format", "structured")

        # Create Claude Code compatible name (lowercase, hyphens only)
        claude_code_name = agent_name.lower().replace("_", "-")

        # CRITICAL: NO underscores allowed - they cause silent failures!

        # Validate the name before proceeding
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", claude_code_name):
            self.logger.error(
                f"Invalid agent name '{claude_code_name}' - must match ^[a-z0-9]+(-[a-z0-9]+)*$"
            )
            raise ValueError(
                f"Agent name '{claude_code_name}' does not meet Claude Code requirements"
            )

        # Extract description from template with fallback
        raw_description = (
            template_data.get("description")
            or template_data.get("metadata", {}).get("description")
            or f"{agent_name.title()} agent for specialized tasks"
        )

        # Convert to multiline format with examples for Claude Code compatibility
        description = self._create_multiline_description(
            raw_description, agent_name, template_data
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
            pass
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
            color_map.get(agent_type, "blue")

        # Check if we should include tools field (only if significantly restricting)
        # Claude Code approach: omit tools field unless specifically restricting

        # Convert tools to set for comparison
        agent_tools = set(tools) if isinstance(tools, list) else set(tools.split(","))

        # Only include tools field if agent is missing several important tools
        # This matches Claude Code's approach of omitting tools for general-purpose agents
        core_tools = {"Read", "Write", "Edit", "Bash", "Grep", "Glob"}
        has_core_tools = len(agent_tools.intersection(core_tools)) >= 5

        # Include tools field only if agent is clearly restricted (missing core tools or very few tools)
        not has_core_tools or len(agent_tools) < 6

        # Build YAML frontmatter using Claude Code's compatible format
        # ONLY include fields that Claude Code recognizes
        #
        # CLAUDE CODE COMPATIBLE FORMAT:
        # - name: kebab-case agent name (required)
        # - description: when/why to use this agent with examples (required, multiline)
        # - model: mapped model name (required)
        # - color: visual identifier (optional)
        # - version: agent version for update tracking (optional)
        # - author: creator information (optional)
        # NOTE: tags field REMOVED - not supported by Claude Code
        frontmatter_lines = [
            "---",
            f"name: {claude_code_name}",
        ]

        # Add description as single-line YAML string with \n escapes
        frontmatter_lines.append(
            f"description: {self._format_description_for_yaml(description)}"
        )

        # Add model field (required for Claude Code)
        frontmatter_lines.append(f"model: {model}")

        # Add optional metadata (excluding tags field completely)
        if metadata.get("color"):
            frontmatter_lines.append(f"color: {metadata['color']}")
        if (
            agent_version and agent_version != "1.0.0"
        ):  # Only include non-default versions
            frontmatter_lines.append(f'version: "{agent_version}"')
        if metadata.get("author"):
            frontmatter_lines.append(f'author: "{metadata["author"]}"')

        frontmatter_lines.extend(
            [
                "---",
                "",
            ]
        )

        frontmatter = "\n".join(frontmatter_lines)

        # Load BASE instructions for this agent type
        base_instructions = self._load_base_agent_instructions(agent_type)

        # Get agent instructions from template data (primary) or base agent data (fallback)
        agent_specific_instructions = (
            template_data.get("instructions")
            or base_agent_data.get("content")
            or base_agent_data.get("instructions")
            or "# Agent Instructions\n\nThis agent provides specialized assistance."
        )

        # Combine BASE instructions with agent-specific instructions
        if base_instructions:
            # Create a combined instruction set
            content = f"{base_instructions}\n\n---\n\n{agent_specific_instructions}"
            self.logger.debug(
                f"Combined BASE instructions with agent-specific instructions for {agent_type}"
            )
        else:
            content = agent_specific_instructions

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

    def _create_multiline_description(
        self, raw_description: str, agent_name: str, template_data: dict
    ) -> str:
        """
        Create a comprehensive multiline description with examples for Claude Code compatibility.
        Based on Claude's software-engineer.md format: detailed when/why description with examples.

        Args:
            raw_description: Original single-line description
            agent_name: Name of the agent
            template_data: Template data for extracting examples

        Returns:
            Formatted multiline description with examples in Claude Code format
        """
        raw_description = self._format_to_single_line(raw_description)

        # Get agent type for creating targeted descriptions
        agent_type = template_data.get("agent_type", "general")

        # Create enhanced description based on agent type
        enhanced_description = self._create_enhanced_description(
            raw_description, agent_name, agent_type, template_data
        )

        # Add examples
        examples = self._extract_examples_from_template(template_data, agent_name)
        if not examples:
            examples = self._generate_default_examples(agent_name, template_data)

        # Combine enhanced description with examples
        if examples:
            description_parts = [enhanced_description, "", *examples]
        else:
            description_parts = [enhanced_description]

        return "\n".join(description_parts)

    def _format_to_single_line(self, description: str) -> str:
        """
        Format description to single line by removing line breaks and normalizing whitespace.

        Args:
            description: Raw description text

        Returns:
            Single-line formatted description
        """
        if not description:
            return description

        # Remove all line breaks and normalize whitespace
        single_line = " ".join(description.strip().split())

        # Remove redundant spaces around punctuation
        single_line = re.sub(r"\s+([,.!?;:])", r"\1", single_line)
        return re.sub(r"([,.!?;:])\s+", r"\1 ", single_line)

    def _create_enhanced_description(
        self,
        raw_description: str,
        agent_name: str,
        agent_type: str,
        template_data: dict,
    ) -> str:
        """
        Create an enhanced description based on agent type that follows Claude's format.

        Args:
            raw_description: Original description
            agent_name: Name of the agent
            agent_type: Type of agent (engineer, qa, research, etc.)
            template_data: Template data for additional context

        Returns:
            Enhanced description string
        """
        # Type-specific enhanced descriptions following Claude's software-engineer.md pattern
        enhanced_descriptions = {
            "engineer": "Use this agent when you need to implement new features, write production-quality code, refactor existing code, or solve complex programming challenges. This agent excels at translating requirements into well-architected, maintainable code solutions across various programming languages and frameworks.",
            "qa": "Use this agent when you need comprehensive testing, quality assurance validation, or test automation. This agent specializes in creating robust test suites, identifying edge cases, and ensuring code quality through systematic testing approaches across different testing methodologies.",
            "research": "Use this agent when you need to investigate codebases, analyze system architecture, or gather technical insights. This agent excels at code exploration, pattern identification, and providing comprehensive analysis of existing systems while maintaining strict memory efficiency.",
            "ops": "Use this agent when you need infrastructure management, deployment automation, or operational excellence. This agent specializes in DevOps practices, cloud operations, monitoring setup, and maintaining reliable production systems.",
            "security": "Use this agent when you need security analysis, vulnerability assessment, or secure coding practices. This agent excels at identifying security risks, implementing security best practices, and ensuring applications meet security standards.",
            "documentation": "Use this agent when you need to create, update, or maintain technical documentation. This agent specializes in writing clear, comprehensive documentation including API docs, user guides, and technical specifications.",
        }

        # Get the enhanced description or fallback to the original with improvements
        if agent_type in enhanced_descriptions:
            return enhanced_descriptions[agent_type]
        # Enhance the raw description if it's a custom type
        if raw_description and len(raw_description) > 10:
            return f"Use this agent when you need specialized assistance with {raw_description.lower()}. This agent provides targeted expertise and follows best practices for {agent_name.replace('-', ' ')} related tasks."
        return f"Use this agent when you need specialized assistance from the {agent_name.replace('-', ' ')} agent. This agent provides targeted expertise and follows established best practices."

    def _extract_examples_from_template(
        self, template_data: dict, agent_name: str
    ) -> List[str]:
        """
        Extract examples from template data and format with commentary.
        Creates ONE example with commentary from template data.

        Args:
            template_data: Template data
            agent_name: Name of the agent

        Returns:
            List of example strings (single example with commentary)
        """
        examples = []

        # Check for examples in knowledge section
        knowledge = template_data.get("knowledge", {})
        template_examples = knowledge.get("examples", [])

        if template_examples:
            # Take only the first example and add commentary
            example = template_examples[0]
            scenario = example.get("scenario", "")
            approach = example.get("approach", "")
            commentary = example.get("commentary", "")

            if scenario and approach:
                examples.extend(
                    [
                        "<example>",
                        f"Context: {scenario}",
                        f'user: "I need help with {scenario.lower()}"',
                        f'assistant: "I\'ll use the {agent_name} agent to {approach.lower()}."',
                        "<commentary>",
                        (
                            commentary
                            if commentary
                            else f"This agent is well-suited for {scenario.lower()} because it specializes in {approach.lower()} with targeted expertise."
                        ),
                        "</commentary>",
                        "</example>",
                    ]
                )

        # Check for triggers that can be converted to examples
        interactions = template_data.get("interactions", {})
        triggers = interactions.get("triggers", [])

        if triggers and not examples:
            # Convert first trigger to example with commentary
            trigger = triggers[0]

            # Handle both string and dict trigger formats
            if isinstance(trigger, dict):
                # New format with pattern and confidence
                trigger_text = trigger.get("pattern", "")
            else:
                # Old format with simple string
                trigger_text = str(trigger)

            # Skip if we don't have valid trigger text
            if not trigger_text:
                return examples

            agent_type = template_data.get("agent_type", "general")

            examples.extend(
                [
                    "<example>",
                    f"Context: When user needs {trigger_text}",
                    f'user: "{trigger_text}"',
                    f'assistant: "I\'ll use the {agent_name} agent for {trigger_text}."',
                    "<commentary>",
                    f"This {agent_type} agent is appropriate because it has specialized capabilities for {trigger_text.lower()} tasks.",
                    "</commentary>",
                    "</example>",
                ]
            )

        return examples

    def _generate_default_examples(
        self, agent_name: str, template_data: dict
    ) -> List[str]:
        """
        Generate default examples when none are available in template.
        Creates ONE example with commentary for each agent type.

        Args:
            agent_name: Name of the agent
            template_data: Template data for context

        Returns:
            List of example strings (single example with commentary)
        """
        agent_type = template_data.get("agent_type", "general")

        # Create type-specific examples with commentary inside
        type_examples = {
            "engineer": [
                "<example>",
                "Context: When you need to implement new features or write code.",
                'user: "I need to add authentication to my API"',
                f'assistant: "I\'ll use the {agent_name} agent to implement a secure authentication system for your API."',
                "<commentary>",
                "The engineer agent is ideal for code implementation tasks because it specializes in writing production-quality code, following best practices, and creating well-architected solutions.",
                "</commentary>",
                "</example>",
            ],
            "ops": [
                "<example>",
                "Context: When you need to deploy or manage infrastructure.",
                'user: "I need to deploy my application to the cloud"',
                f'assistant: "I\'ll use the {agent_name} agent to set up and deploy your application infrastructure."',
                "<commentary>",
                "The ops agent excels at infrastructure management and deployment automation, ensuring reliable and scalable production systems.",
                "</commentary>",
                "</example>",
            ],
            "qa": [
                "<example>",
                "Context: When you need to test or validate functionality.",
                'user: "I need to write tests for my new feature"',
                f'assistant: "I\'ll use the {agent_name} agent to create comprehensive tests for your feature."',
                "<commentary>",
                "The QA agent specializes in comprehensive testing strategies, quality assurance validation, and creating robust test suites that ensure code reliability.",
                "</commentary>",
                "</example>",
            ],
            "research": [
                "<example>",
                "Context: When you need to investigate or analyze existing codebases.",
                'user: "I need to understand how the authentication system works in this project"',
                f'assistant: "I\'ll use the {agent_name} agent to analyze the codebase and explain the authentication implementation."',
                "<commentary>",
                "The research agent is perfect for code exploration and analysis tasks, providing thorough investigation of existing systems while maintaining memory efficiency.",
                "</commentary>",
                "</example>",
            ],
            "security": [
                "<example>",
                "Context: When you need to review code for security vulnerabilities.",
                'user: "I need a security review of my authentication implementation"',
                f'assistant: "I\'ll use the {agent_name} agent to conduct a thorough security analysis of your authentication code."',
                "<commentary>",
                "The security agent specializes in identifying security risks, vulnerability assessment, and ensuring applications meet security standards and best practices.",
                "</commentary>",
                "</example>",
            ],
            "documentation": [
                "<example>",
                "Context: When you need to create or update technical documentation.",
                'user: "I need to document this new API endpoint"',
                f'assistant: "I\'ll use the {agent_name} agent to create comprehensive API documentation."',
                "<commentary>",
                "The documentation agent excels at creating clear, comprehensive technical documentation including API docs, user guides, and technical specifications.",
                "</commentary>",
                "</example>",
            ],
        }

        return type_examples.get(
            agent_type,
            [
                "<example>",
                f"Context: When you need specialized assistance from the {agent_name} agent.",
                f'user: "I need help with {agent_name.replace("-", " ")} tasks"',
                f'assistant: "I\'ll use the {agent_name} agent to provide specialized assistance."',
                "<commentary>",
                f"This agent provides targeted expertise for {agent_name.replace('-', ' ')} related tasks and follows established best practices.",
                "</commentary>",
                "</example>",
            ],
        )

    def _indent_multiline_text(self, text: str, spaces: int) -> str:
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

    def _format_description_for_yaml(self, description: str) -> str:
        """Format description as a single-line YAML string with escaped newlines.

        Args:
            description: Multi-line description text

        Returns:
            Single-line YAML-formatted string with \n escapes
        """
        if not description:
            return '""'

        # The description already contains actual newlines, we need to escape them
        # Replace actual newlines with \n escape sequence
        escaped = description.replace("\n", "\\n")

        # Escape any quotes in the description
        escaped = escaped.replace('"', '\\"')

        # Return as quoted string
        return f'"{escaped}"'
