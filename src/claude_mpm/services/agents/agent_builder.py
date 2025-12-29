"""Agent Builder Service for programmatic agent creation and management.

This service provides comprehensive agent lifecycle management including:
- Template-based agent generation
- Agent variant creation with inheritance
- Configuration validation and sanitization
- PM instruction customization
- Integration with deployment services
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Tuple

import yaml

from claude_mpm.core.exceptions import AgentDeploymentError
from claude_mpm.core.logging_config import get_logger


class AgentBuilderService:
    """Service for building and managing agent configurations."""

    # Valid agent models
    VALID_MODELS: ClassVar[list[str]] = ["sonnet", "opus", "haiku"]

    # Valid tool choices
    VALID_TOOL_CHOICES: ClassVar[list[str]] = ["auto", "required", "any", "none"]

    # Agent categories
    AGENT_CATEGORIES: ClassVar[list[str]] = [
        "engineering",
        "qa",
        "documentation",
        "ops",
        "research",
        "security",
        "system",
        "utility",
    ]

    def __init__(self, templates_dir: Optional[Path] = None):
        """Initialize the Agent Builder Service.

        Args:
            templates_dir: Path to agent templates directory
        """
        self.logger = get_logger(__name__)
        self.templates_dir = (
            templates_dir
            or Path(__file__).parent.parent.parent / "agents" / "templates"
        )
        self._template_cache = {}

    def create_agent(
        self,
        agent_id: str,
        name: str,
        description: str,
        model: str = "sonnet",
        tool_choice: str = "auto",
        instructions: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        base_template: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new agent configuration.

        Args:
            agent_id: Unique identifier for the agent
            name: Display name for the agent
            description: Agent purpose and capabilities
            model: LLM model to use (sonnet/opus/haiku)
            tool_choice: Tool selection strategy
            instructions: Markdown instructions content
            metadata: Additional agent metadata
            base_template: Optional base template to extend

        Returns:
            Complete agent configuration dictionary

        Raises:
            AgentDeploymentError: If validation fails
        """
        # Validate inputs
        self._validate_agent_id(agent_id)
        self._validate_model(model)
        self._validate_tool_choice(tool_choice)

        # Start with base template if provided
        if base_template:
            config = self._load_template(base_template)
            config["id"] = agent_id  # Override ID
        else:
            config = {}

        # Build agent configuration
        config.update(
            {
                "id": agent_id,
                "name": name,
                "prompt": f"{agent_id}.md",
                "model": model,
                "tool_choice": tool_choice,
            }
        )

        # Build metadata
        agent_metadata = {
            "description": description,
            "version": "1.0.0",
            "created": datetime.now(timezone.utc).isoformat(),
            "author": "Agent Manager",
            "category": "custom",
        }

        if metadata:
            agent_metadata.update(metadata)

        config["metadata"] = agent_metadata

        # Generate instructions if not provided
        if instructions is None:
            instructions = self._generate_default_instructions(
                agent_id, name, description
            )

        return config, instructions

    def create_variant(
        self,
        base_agent_id: str,
        variant_id: str,
        variant_name: str,
        modifications: Dict[str, Any],
        instructions_append: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], str]:
        """Create an agent variant based on an existing agent.

        Args:
            base_agent_id: ID of the base agent to extend
            variant_id: Unique ID for the variant
            variant_name: Display name for the variant
            modifications: Configuration changes for the variant
            instructions_append: Additional instructions to append

        Returns:
            Tuple of (variant configuration, variant instructions)

        Raises:
            AgentDeploymentError: If base agent not found or validation fails
        """
        # Load base agent
        base_config = self._load_template(base_agent_id)
        base_instructions = self._load_instructions(base_agent_id)

        # Validate variant ID
        self._validate_agent_id(variant_id)

        # Create variant configuration
        variant_config = base_config.copy()
        variant_config["id"] = variant_id
        variant_config["name"] = variant_name
        variant_config["prompt"] = f"{variant_id}.md"

        # Apply modifications
        for key, value in modifications.items():
            if key in ["model", "tool_choice"]:
                if key == "model":
                    self._validate_model(value)
                elif key == "tool_choice":
                    self._validate_tool_choice(value)
            variant_config[key] = value

        # Update metadata
        if "metadata" not in variant_config:
            variant_config["metadata"] = {}

        variant_config["metadata"].update(
            {
                "base_agent": base_agent_id,
                "variant": True,
                "variant_created": datetime.now(timezone.utc).isoformat(),
            }
        )

        # Build variant instructions
        variant_instructions = f"# {variant_name} (Variant of {base_config.get('name', base_agent_id)})\n\n"
        variant_instructions += base_instructions

        if instructions_append:
            variant_instructions += (
                f"\n\n## Variant-Specific Instructions\n\n{instructions_append}"
            )

        return variant_config, variant_instructions

    def validate_configuration(self, config: Dict[str, Any]) -> List[str]:
        """Validate an agent configuration.

        Args:
            config: Agent configuration to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Required fields (model is optional - defaults to sonnet if not specified)
        required_fields = ["id", "name", "prompt"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        # Validate ID
        if "id" in config:
            try:
                self._validate_agent_id(config["id"])
            except AgentDeploymentError as e:
                errors.append(str(e))

        # Validate model (only if present)
        if "model" in config:
            try:
                self._validate_model(config["model"])
            except AgentDeploymentError as e:
                errors.append(str(e))

        # Validate tool_choice
        if "tool_choice" in config:
            try:
                self._validate_tool_choice(config["tool_choice"])
            except AgentDeploymentError as e:
                errors.append(str(e))

        # Validate metadata
        if "metadata" in config and not isinstance(config["metadata"], dict):
            errors.append("Metadata must be a dictionary")

        return errors

    def generate_pm_instructions(
        self,
        delegation_patterns: Optional[List[str]] = None,
        workflow_overrides: Optional[Dict[str, str]] = None,
        custom_rules: Optional[List[str]] = None,
    ) -> str:
        """Generate customized PM instructions.

        Args:
            delegation_patterns: Custom delegation patterns
            workflow_overrides: Workflow sequence modifications
            custom_rules: Additional PM rules

        Returns:
            Customized PM instructions markdown
        """
        instructions = "# Custom PM Instructions\n\n"

        if delegation_patterns:
            instructions += "## Custom Delegation Patterns\n\n"
            for pattern in delegation_patterns:
                instructions += f"- {pattern}\n"
            instructions += "\n"

        if workflow_overrides:
            instructions += "## Workflow Overrides\n\n"
            for workflow, override in workflow_overrides.items():
                instructions += f"### {workflow}\n{override}\n\n"

        if custom_rules:
            instructions += "## Additional Rules\n\n"
            for rule in custom_rules:
                instructions += f"- {rule}\n"

        return instructions

    def list_available_templates(self) -> List[Dict[str, Any]]:
        """List all available agent templates.

        Returns:
            List of template metadata dictionaries
        """
        templates = []

        if not self.templates_dir.exists():
            return templates

        # Agent templates migrated to Markdown with YAML frontmatter (v4.26.0+)
        for template_file in self.templates_dir.glob("*.md"):
            try:
                # Read markdown content and extract YAML frontmatter
                content = template_file.read_text()
                config = self._extract_yaml_frontmatter(content)
                if not config:
                    self.logger.warning(f"No YAML frontmatter in {template_file.name}")
                    continue

                # Use filename stem as ID if not specified in config
                template_id = config.get("id") or template_file.stem

                templates.append(
                    {
                        "id": template_id,
                        "name": config.get("name", template_id),
                        "description": config.get("metadata", {}).get("description"),
                        "category": config.get("metadata", {}).get("category"),
                        "version": config.get("metadata", {}).get("version"),
                        "file": str(template_file),
                    }
                )
            except Exception as e:
                self.logger.warning(f"Failed to load template {template_file}: {e}")

        return templates

    def _extract_yaml_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract and parse YAML frontmatter from markdown content.

        Args:
            content: File content to parse

        Returns:
            Parsed YAML frontmatter as dict, or None if not found/invalid
        """
        if not content.strip().startswith("---"):
            return None

        # Split on --- delimiters
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        try:
            return yaml.safe_load(parts[1])
        except yaml.YAMLError as e:
            self.logger.warning(f"Failed to parse YAML frontmatter: {e}")
            return None

    def _validate_agent_id(self, agent_id: str) -> None:
        """Validate agent ID format.

        Args:
            agent_id: Agent ID to validate

        Raises:
            AgentDeploymentError: If ID is invalid
        """
        if not agent_id:
            raise AgentDeploymentError("Agent ID cannot be empty")

        if len(agent_id) > 50:
            raise AgentDeploymentError("Agent ID must be 50 characters or less")

        if not re.match(r"^[a-z0-9-]+$", agent_id):
            raise AgentDeploymentError(
                "Agent ID must contain only lowercase letters, numbers, and hyphens"
            )

    def _validate_model(self, model: str) -> None:
        """Validate model selection.

        Args:
            model: Model to validate

        Raises:
            AgentDeploymentError: If model is invalid
        """
        if model not in self.VALID_MODELS:
            raise AgentDeploymentError(
                f"Invalid model '{model}'. Must be one of: {', '.join(self.VALID_MODELS)}"
            )

    def _validate_tool_choice(self, tool_choice: str) -> None:
        """Validate tool choice setting.

        Args:
            tool_choice: Tool choice to validate

        Raises:
            AgentDeploymentError: If tool choice is invalid
        """
        if tool_choice not in self.VALID_TOOL_CHOICES:
            raise AgentDeploymentError(
                f"Invalid tool_choice '{tool_choice}'. Must be one of: {', '.join(self.VALID_TOOL_CHOICES)}"
            )

    def _load_template(self, template_id: str) -> Dict[str, Any]:
        """Load an agent template.

        Args:
            template_id: Template ID to load

        Returns:
            Template configuration dictionary

        Raises:
            AgentDeploymentError: If template not found
        """
        if template_id in self._template_cache:
            return self._template_cache[template_id].copy()

        # Agent templates migrated to Markdown with YAML frontmatter (v4.26.0+)
        template_file = self.templates_dir / f"{template_id}.md"

        if not template_file.exists():
            raise AgentDeploymentError(f"Template '{template_id}' not found")

        try:
            # Read markdown content and extract YAML frontmatter
            content = template_file.read_text()
            config = self._extract_yaml_frontmatter(content)
            if not config:
                raise AgentDeploymentError(
                    f"No YAML frontmatter in template '{template_id}'"
                )
            self._template_cache[template_id] = config
            return config.copy()
        except Exception as e:
            raise AgentDeploymentError(
                f"Failed to load template '{template_id}': {e}"
            ) from e

    def _load_instructions(self, agent_id: str) -> str:
        """Load agent instructions.

        Args:
            agent_id: Agent ID to load instructions for

        Returns:
            Instructions markdown content

        Raises:
            AgentDeploymentError: If instructions not found
        """
        # Try multiple possible locations
        possible_files = [
            self.templates_dir / f"{agent_id}.md",
            self.templates_dir / f"{agent_id}_instructions.md",
            self.templates_dir / f"{agent_id}-instructions.md",
        ]

        for instructions_file in possible_files:
            if instructions_file.exists():
                try:
                    with instructions_file.open() as f:
                        return f.read()
                except Exception as e:
                    self.logger.warning(
                        f"Failed to read instructions from {instructions_file}: {e}"
                    )

        # If no instructions found, return empty
        return ""

    def _generate_default_instructions(
        self, agent_id: str, name: str, description: str
    ) -> str:
        """Generate default agent instructions.

        Args:
            agent_id: Agent identifier
            name: Agent display name
            description: Agent description

        Returns:
            Default instructions markdown
        """
        return f"""# {name}

## Core Identity

You are {name}, a specialized agent in the Claude MPM framework.

## Purpose

{description}

## Responsibilities

- Primary focus on your specialized domain
- Collaborate with other agents as needed
- Follow Claude MPM framework conventions
- Maintain high quality standards

## Operating Principles

1. **Expertise**: Apply deep knowledge in your domain
2. **Efficiency**: Complete tasks effectively and quickly
3. **Communication**: Provide clear, actionable responses
4. **Collaboration**: Work well with other agents
5. **Quality**: Maintain high standards in all outputs

## Output Format

Provide structured responses with:
- Clear summaries of actions taken
- Detailed results when appropriate
- Any issues or blockers encountered
- Recommendations for next steps

## Integration

- Follow framework patterns and conventions
- Use appropriate tools for the task
- Coordinate with PM for complex workflows
- Report completion status clearly

---

*Agent ID: {agent_id}*
*Generated by Agent Manager*
"""
