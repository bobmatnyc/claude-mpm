from pathlib import Path

"""
Agent profile generator using template system.

Inspired by awesome-claude-code's template generation approach.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import yaml


class AgentProfileGenerator:
    """Generates agent profiles from templates."""

    def __init__(self, template_path: Optional[Path] = None):
        """Initialize the generator with a template path."""
        self.template_path = (
            template_path
            or Path(__file__).parent.parent / "agents" / "agent-template.yaml"
        )
        self.template = self._load_template()

    def _load_template(self) -> Dict[str, Any]:
        """Load the agent profile template."""
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found: {self.template_path}")

        with self.template_path.open() as f:
            return yaml.safe_load(f)

    def generate_profile(self, config: Dict[str, Any]) -> str:
        """Generate an agent profile from configuration."""
        # Set default values
        config.setdefault("VERSION", "1.0.0")
        config.setdefault(
            "CREATED_DATE", datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )
        config.setdefault("AUTHOR", "claude-mpm")

        # Convert template to string
        template_str = yaml.dump(self.template, default_flow_style=False)

        # Replace placeholders
        result = self._replace_placeholders(template_str, config)

        # Clean up any remaining placeholders
        return re.sub(r"\{\{[^}]+\}\}", "", result)

    def _replace_placeholders(self, template: str, values: Dict[str, Any]) -> str:
        """Replace template placeholders with actual values."""
        for key, value in values.items():
            placeholder = f"{{{{{key}}}}}"
            if isinstance(value, list):
                # Format lists nicely
                formatted_list = "\n".join(f'      - "{item}"' for item in value)
                template = template.replace(placeholder, formatted_list)
            else:
                template = template.replace(placeholder, str(value))

        return template

    def generate_agent_documentation(self, agent_config: Dict[str, Any]) -> str:
        """Generate markdown documentation for an agent."""
        doc_lines = []

        # Header
        doc_lines.append(f"# {agent_config.get('name', 'Agent')} Documentation")
        doc_lines.append("")

        # Description
        if "description" in agent_config:
            doc_lines.append("## Description")
            doc_lines.append(agent_config["description"])
            doc_lines.append("")

        # Capabilities
        if "capabilities" in agent_config:
            doc_lines.append("## Capabilities")
            for capability in agent_config["capabilities"]:
                doc_lines.append(f"- {capability}")
            doc_lines.append("")

        # Tools
        if "tools" in agent_config:
            doc_lines.append("## Required Tools")
            for tool in agent_config["tools"]:
                if isinstance(tool, dict):
                    doc_lines.append(
                        f"- **{tool['name']}**: {tool.get('description', '')}"
                    )
                else:
                    doc_lines.append(f"- {tool}")
            doc_lines.append("")

        # Examples
        if "examples" in agent_config:
            doc_lines.append("## Usage Examples")
            for i, example in enumerate(agent_config["examples"], 1):
                doc_lines.append(
                    f"### Example {i}: {example.get('scenario', 'Scenario')}"
                )
                doc_lines.append("```")
                doc_lines.append(f"Input: {example.get('input', '')}")
                doc_lines.append("```")
                doc_lines.append("Expected Output:")
                doc_lines.append("```")
                doc_lines.append(example.get("expected_output", ""))
                doc_lines.append("```")
                doc_lines.append("")

        # Best Practices
        if "best_practices" in agent_config:
            doc_lines.append("## Best Practices")
            for practice in agent_config["best_practices"]:
                doc_lines.append(f"- {practice}")
            doc_lines.append("")

        return "\n".join(doc_lines)

    def create_agent_from_template(
        self, agent_name: str, role: str, category: str = "analysis"
    ) -> Dict[str, Any]:
        """Create a new agent configuration from template."""
        return {
            "AGENT_NAME": agent_name,
            "AGENT_ID": agent_name.lower().replace(" ", "_"),
            "ROLE": role,
            "CATEGORY": category,
            "DESCRIPTION": f"Agent profile for {agent_name}",
            "AGENT_DESCRIPTION": f"Specialized {role} agent",
            "SPECIALIZATION": role.lower(),
            "CAPABILITIES_LIST": "- Analyze code structure\n- Identify patterns\n- Generate reports",
            "CONSTRAINTS_LIST": "- Read-only operations\n- Respect file permissions",
            "TOOL_NAME": "code_analysis",
            "TOOL_DESCRIPTION": "Analyzes code structure and patterns",
            "EXAMPLE_SCENARIO": "Analyzing a Python project",
            "EXAMPLE_INPUT": "Analyze the architecture of this codebase",
            "EXAMPLE_OUTPUT": "Detailed analysis report with recommendations",
            "BEST_PRACTICE_1": "Always validate input parameters",
            "BEST_PRACTICE_2": "Provide clear, actionable insights",
            "BEST_PRACTICE_3": "Include examples in reports",
            "ADDITIONAL_INSTRUCTIONS": "Be thorough but concise in your analysis.",
        }
