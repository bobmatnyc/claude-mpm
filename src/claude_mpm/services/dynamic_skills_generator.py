"""Dynamic Skills Generator - Generate agent and tool selection skills on startup."""

from datetime import datetime
from pathlib import Path
from typing import Dict

from claude_mpm.services.agent_capabilities_service import (
    AgentCapabilitiesService,
)
from claude_mpm.services.setup_registry import SetupRegistry


class DynamicSkillsGenerator:
    """Generate dynamic skills for agent and tool selection."""

    def __init__(
        self,
        skills_dir: Path | None = None,
        setup_registry: SetupRegistry | None = None,
    ):
        """Initialize dynamic skills generator.

        Args:
            skills_dir: Directory for dynamic skills (default: ~/.claude-mpm/skills/dynamic/)
            setup_registry: Setup registry instance
        """
        if skills_dir is None:
            skills_dir = Path.home() / ".claude-mpm" / "skills" / "dynamic"

        self.skills_dir = skills_dir
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        self.setup_registry = setup_registry or SetupRegistry()
        self.agent_service = AgentCapabilitiesService()

    def generate_all(self) -> None:
        """Generate all dynamic skills."""
        self.generate_agent_selection_skill()
        self.generate_tool_selection_skill()

    def generate_agent_selection_skill(self) -> Path:
        """Generate mpm-select-agents skill.

        Returns:
            Path to generated skill file
        """
        # Get all agents
        agents = self.agent_service.get_all_agents()

        # Build skill content
        content = self._build_agent_skill_content(agents)

        # Write skill file
        skill_path = self.skills_dir / "mpm-select-agents.md"
        skill_path.write_text(content)

        return skill_path

    def generate_tool_selection_skill(self) -> Path:
        """Generate mpm-select-tools skill.

        Returns:
            Path to generated skill file
        """
        # Get all services from registry
        services = self.setup_registry.get_services_with_details()

        # Build skill content
        content = self._build_tool_skill_content(services)

        # Write skill file
        skill_path = self.skills_dir / "mpm-select-tools.md"
        skill_path.write_text(content)

        return skill_path

    def _build_agent_skill_content(self, agents: Dict) -> str:
        """Build content for agent selection skill.

        Args:
            agents: Dict of agent data from AgentCapabilitiesService

        Returns:
            Markdown skill content
        """
        timestamp = datetime.now().astimezone().isoformat()

        lines = [
            "---",
            "name: mpm-select-agents",
            "description: Agent selection guide for PM delegation",
            "version: 1.0.0",
            "auto_generated: true",
            f"generated_at: {timestamp}",
            "when_to_use: When PM needs to select an agent for delegation",
            "---",
            "",
            "# Agent Selection Guide",
            "",
            "Use this guide to select the appropriate agent for delegation tasks.",
            "",
            "## Available Agents",
            "",
        ]

        # Group agents by type/location if available
        for agent_id, agent_info in sorted(agents.items()):
            name = agent_info.get("name", agent_id)
            description = agent_info.get("description", "")
            agent_type = agent_info.get("type", "general-purpose")
            location = agent_info.get("location", "system")

            lines.append(f"### {name}")
            lines.append(f"- **ID**: `{agent_id}`")
            lines.append(f"- **Type**: {agent_type}")
            lines.append(f"- **Location**: {location}")

            if description:
                lines.append(f"- **Description**: {description}")

            # Add capabilities if available
            capabilities = agent_info.get("capabilities", [])
            if capabilities:
                lines.append("- **Capabilities**:")
                for cap in capabilities:
                    lines.append(f"  - {cap}")

            lines.append("")

        lines.append("## Selection Guidelines")
        lines.append("")
        lines.append("- **Research**: Codebase analysis, investigation, understanding")
        lines.append("- **Engineer**: Implementation, code writing, refactoring")
        lines.append("- **QA**: Testing, verification, quality assurance")
        lines.append("- **Ops**: Deployment, infrastructure, operations")
        lines.append(
            "- **Documentation**: Writing docs, guides, technical specifications"
        )
        lines.append("")

        return "\n".join(lines)

    def _build_tool_skill_content(self, services: Dict[str, Dict]) -> str:
        """Build content for tool selection skill.

        Args:
            services: Dict of service data from SetupRegistry

        Returns:
            Markdown skill content
        """
        timestamp = datetime.now().astimezone().isoformat()

        lines = [
            "---",
            "name: mpm-select-tools",
            "description: MCP and CLI tool selection guide",
            "version: 1.0.0",
            "auto_generated: true",
            f"generated_at: {timestamp}",
            "when_to_use: When PM needs to select an MCP tool or CLI command",
            "---",
            "",
            "# Tool Selection Guide",
            "",
            "Use this guide to select the appropriate MCP tool or CLI command.",
            "",
        ]

        # Separate MCP and CLI services
        mcp_services = {k: v for k, v in services.items() if v.get("type") == "mcp"}
        cli_services = {k: v for k, v in services.items() if v.get("type") == "cli"}

        # MCP Tools section
        if mcp_services:
            lines.append("## MCP Tools")
            lines.append("")

            for service_name, details in sorted(mcp_services.items()):
                lines.append(f"### {service_name}")
                lines.append(f"- **Setup Date**: {details.get('setup_date', 'N/A')}")
                lines.append(f"- **Version**: {details.get('version', 'N/A')}")
                lines.append(
                    f"- **Location**: {details.get('config_location', 'user')}"
                )

                tools = details.get("tools", [])
                if tools:
                    lines.append("- **Available Tools**:")
                    for tool in tools:
                        lines.append(f"  - `{tool}`")

                cli_help = details.get("cli_help", "")
                if cli_help:
                    lines.append("")
                    lines.append("**CLI Help**:")
                    lines.append("```")
                    lines.append(cli_help.strip())
                    lines.append("```")

                lines.append("")

        # CLI Tools section
        if cli_services:
            lines.append("## CLI Tools")
            lines.append("")

            for service_name, details in sorted(cli_services.items()):
                lines.append(f"### {service_name}")
                lines.append(f"- **Setup Date**: {details.get('setup_date', 'N/A')}")
                lines.append(f"- **Version**: {details.get('version', 'N/A')}")

                cli_help = details.get("cli_help", "")
                if cli_help:
                    lines.append("")
                    lines.append("**Help**:")
                    lines.append("```")
                    lines.append(cli_help.strip())
                    lines.append("```")

                lines.append("")

        if not mcp_services and not cli_services:
            lines.append("*No MCP or CLI tools configured yet.*")
            lines.append("")
            lines.append("Run `claude-mpm setup <service>` to configure tools.")
            lines.append("")

        return "\n".join(lines)
