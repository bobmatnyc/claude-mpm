"""Agent and skill generator for integrations (ISS-0014).

This module generates agent markdown files and skill files from
integration manifests, enabling automatic creation of Claude-compatible
agents for API integrations.

Example:
    generator = IntegrationGenerator()
    agent_content = generator.generate_agent(manifest)
    skill_content = generator.generate_skill(manifest)

    # Deploy to target directory
    agent_path, skill_path = generator.deploy(
        manifest,
        target_dir=Path(".claude"),
        scope="project"
    )
"""

from pathlib import Path
from typing import Literal

from .manifest import IntegrationManifest, Operation


class IntegrationGenerator:
    """Generates agent and skill files for integrations.

    Creates Claude-compatible agent markdown files and skill files
    from integration manifests, with configurable deployment to
    project or user directories.
    """

    AGENT_TEMPLATE = """---
agent_id: {name}-integration
name: {display_name} Integration Agent
version: 1.0.0
description: Specialized agent for {display_name} API operations
category: integration
toolchain: api
---

# {display_name} Integration Agent

You are a specialized agent for interacting with the {display_name} API.

## Overview

{description}

- **API Type**: {api_type}
- **Base URL**: {base_url}
- **Version**: {version}

## Available Operations

{operations_list}

## Authentication

This integration uses **{auth_type}** authentication. Credentials are managed via .env files.

{auth_details}

## Best Practices

{best_practices}

## Error Handling

When API calls fail:
1. Check if credentials are properly configured
2. Verify the operation parameters are correct
3. Check rate limits if receiving 429 errors
4. Review the error response for specific guidance

## Usage Notes

- Always validate input parameters before making API calls
- Use appropriate error handling for all operations
- Respect rate limits and implement backoff when needed
- Log operations for debugging and audit purposes
"""

    SKILL_TEMPLATE = """---
name: {name}
description: Quick operations for {display_name}
version: 1.0.0
category: integration
---

# {display_name} Integration

Quick access to {display_name} API operations.

## Common Operations

{operation_prompts}

## Quick Reference

{quick_reference}

## Examples

{examples}

## Troubleshooting

- **Authentication errors**: Run `claude-mpm configure {name}` to set credentials
- **Rate limits**: Wait and retry, or reduce request frequency
- **Invalid parameters**: Check the operation documentation above
"""

    def generate_agent(self, manifest: IntegrationManifest) -> str:
        """Generate agent markdown content.

        Args:
            manifest: Integration manifest to generate agent for.

        Returns:
            Agent markdown content.
        """
        display_name = manifest.name.replace("-", " ").replace("_", " ").title()

        # Build operations list
        operations_list = self._build_operations_list(manifest.operations)

        # Build auth details
        auth_details = self._build_auth_details(manifest)

        # Build best practices
        best_practices = self._build_best_practices(manifest)

        return self.AGENT_TEMPLATE.format(
            name=manifest.name,
            display_name=display_name,
            description=manifest.description,
            api_type=manifest.api_type.upper(),
            base_url=manifest.base_url,
            version=manifest.version,
            operations_list=operations_list,
            auth_type=manifest.auth.type,
            auth_details=auth_details,
            best_practices=best_practices,
        )

    def generate_skill(self, manifest: IntegrationManifest) -> str:
        """Generate skill markdown content.

        Args:
            manifest: Integration manifest to generate skill for.

        Returns:
            Skill markdown content.
        """
        display_name = manifest.name.replace("-", " ").replace("_", " ").title()

        # Build operation prompts
        operation_prompts = self._build_operation_prompts(manifest.operations)

        # Build quick reference
        quick_reference = self._build_quick_reference(manifest.operations)

        # Build examples
        examples = self._build_examples(manifest)

        return self.SKILL_TEMPLATE.format(
            name=manifest.name,
            display_name=display_name,
            operation_prompts=operation_prompts,
            quick_reference=quick_reference,
            examples=examples,
        )

    def deploy(
        self,
        manifest: IntegrationManifest,
        target_dir: Path,
        scope: Literal["project", "user"] = "project",
    ) -> tuple[Path, Path]:
        """Deploy agent and skill to target directory.

        Args:
            manifest: Integration manifest to deploy.
            target_dir: Base directory for deployment.
            scope: Deployment scope (project or user).

        Returns:
            Tuple of (agent_path, skill_path).
        """
        if scope == "user":
            base_dir = Path.home() / ".claude-mpm"
        else:
            base_dir = target_dir

        # Create directories
        agents_dir = base_dir / "agents"
        skills_dir = base_dir / "skills"
        agents_dir.mkdir(parents=True, exist_ok=True)
        skills_dir.mkdir(parents=True, exist_ok=True)

        # Generate content
        agent_content = self.generate_agent(manifest)
        skill_content = self.generate_skill(manifest)

        # Write files
        agent_path = agents_dir / f"{manifest.name}-integration.md"
        skill_path = skills_dir / f"{manifest.name}.md"

        agent_path.write_text(agent_content, encoding="utf-8")
        skill_path.write_text(skill_content, encoding="utf-8")

        return agent_path, skill_path

    def _build_operations_list(self, operations: list[Operation]) -> str:
        """Build formatted operations list.

        Args:
            operations: List of operations.

        Returns:
            Formatted markdown operations list.
        """
        lines = []
        for op in operations:
            lines.append(f"### {op.name}")
            lines.append("")
            lines.append(f"**Description**: {op.description}")
            lines.append(f"**Type**: `{op.type}`")

            if op.endpoint:
                lines.append(f"**Endpoint**: `{op.endpoint}`")

            if op.parameters:
                lines.append("")
                lines.append("**Parameters**:")
                for param in op.parameters:
                    required = "(required)" if param.required else "(optional)"
                    default = f", default: `{param.default}`" if param.default else ""
                    desc = f" - {param.description}" if param.description else ""
                    lines.append(
                        f"- `{param.name}` ({param.type}) {required}{default}{desc}"
                    )

            lines.append("")

        return "\n".join(lines)

    def _build_auth_details(self, manifest: IntegrationManifest) -> str:
        """Build authentication details section.

        Args:
            manifest: Integration manifest.

        Returns:
            Formatted auth details markdown.
        """
        lines = []
        auth = manifest.auth

        if auth.type == "none":
            lines.append("No authentication required.")
        else:
            lines.append("**Required Credentials**:")
            for cred in auth.credentials:
                required = "(required)" if cred.required else "(optional)"
                lines.append(f"- `{cred.name}` {required}")
                if cred.help:
                    lines.append(f"  - {cred.help}")

            lines.append("")
            lines.append("Set credentials using:")
            lines.append("```bash")
            lines.append(f"claude-mpm integrate configure {manifest.name}")
            lines.append("```")

        return "\n".join(lines)

    def _build_best_practices(self, manifest: IntegrationManifest) -> str:
        """Build best practices section.

        Args:
            manifest: Integration manifest.

        Returns:
            Formatted best practices markdown.
        """
        practices = [
            f"- Always verify {manifest.name} credentials are configured before operations",
            "- Handle rate limiting gracefully with exponential backoff",
            "- Validate input parameters match expected types",
            "- Log API responses for debugging and audit purposes",
        ]

        if manifest.api_type == "graphql":
            practices.extend(
                [
                    "- Use query variables instead of string interpolation",
                    "- Request only the fields you need to minimize payload size",
                ]
            )

        if manifest.api_type == "rest":
            practices.extend(
                [
                    "- Use appropriate HTTP methods for operations",
                    "- Handle pagination for list operations",
                ]
            )

        return "\n".join(practices)

    def _build_operation_prompts(self, operations: list[Operation]) -> str:
        """Build operation prompt templates.

        Args:
            operations: List of operations.

        Returns:
            Formatted operation prompts markdown.
        """
        lines = []
        for op in operations:
            lines.append(f"### {op.name}")
            lines.append("")
            lines.append(f"{op.description}")
            lines.append("")

            # Build example prompt
            param_examples = []
            for param in op.parameters:
                if param.required:
                    param_examples.append(f"{param.name}=<value>")

            if param_examples:
                lines.append(f"**Usage**: `{op.name} {' '.join(param_examples)}`")
            else:
                lines.append(f"**Usage**: `{op.name}`")

            lines.append("")

        return "\n".join(lines)

    def _build_quick_reference(self, operations: list[Operation]) -> str:
        """Build quick reference table.

        Args:
            operations: List of operations.

        Returns:
            Formatted quick reference markdown.
        """
        lines = [
            "| Operation | Type | Description |",
            "|-----------|------|-------------|",
        ]

        for op in operations:
            lines.append(f"| `{op.name}` | {op.type} | {op.description} |")

        return "\n".join(lines)

    def _build_examples(self, manifest: IntegrationManifest) -> str:
        """Build usage examples section.

        Args:
            manifest: Integration manifest.

        Returns:
            Formatted examples markdown.
        """
        lines = []

        # Generate example for first few operations
        for op in manifest.operations[:3]:
            lines.append(f"### Example: {op.description}")
            lines.append("")
            lines.append("```")
            lines.append(f"# {op.description}")

            if op.parameters:
                param_str = ", ".join(f'{p.name}="example"' for p in op.parameters[:2])
                lines.append(f'await client.call_operation("{op.name}", {param_str})')
            else:
                lines.append(f'await client.call_operation("{op.name}")')

            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def generate_mcp_tools(self, manifest: IntegrationManifest) -> str:
        """Generate MCP tool definitions for the integration.

        Args:
            manifest: Integration manifest.

        Returns:
            Python code for MCP tool definitions.
        """
        if not manifest.mcp.generate:
            return ""

        # Determine which operations to expose
        if manifest.mcp.tools:
            operations = [
                op for op in manifest.operations if op.name in manifest.mcp.tools
            ]
        else:
            operations = manifest.operations

        lines = [
            f'"""Auto-generated MCP tools for {manifest.name} integration."""',
            "",
            "from typing import Any",
            "",
            "from mcp.server import Server",
            "from mcp.types import Tool, TextContent",
            "",
            f"# Tools for {manifest.name} integration",
            "",
        ]

        # Generate tool definitions
        for op in operations:
            tool_name = f"{manifest.name}_{op.name}"
            lines.append(f"async def {tool_name}(")

            # Parameters
            params = []
            for p in op.parameters:
                default = (
                    f' = "{p.default}"'
                    if p.default
                    else ""
                    if p.required
                    else " = None"
                )
                params.append(f"    {p.name}: {self._python_type(p.type)}{default},")

            if params:
                lines.extend(params)

            lines.append(") -> dict[str, Any]:")
            lines.append(f'    """{op.description}"""')
            lines.append("    # Implementation")
            lines.append("    pass")
            lines.append("")

        return "\n".join(lines)

    def _python_type(self, param_type: str) -> str:
        """Convert parameter type to Python type hint.

        Args:
            param_type: Parameter type name.

        Returns:
            Python type hint string.
        """
        type_map = {
            "string": "str",
            "int": "int",
            "float": "float",
            "bool": "bool",
            "file": "str",  # File path as string
        }
        return type_map.get(param_type, "Any")
