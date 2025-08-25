"""Agent output formatting service for CLI commands.

WHY: This service extracts output formatting logic from agents.py to reduce
duplication, improve maintainability, and provide consistent formatting across
all agent-related CLI commands. Following SOLID principles, this service has
a single responsibility: formatting agent data for display.

DESIGN DECISIONS:
- Interface-based design for dependency injection and testability
- Single responsibility: output formatting only
- Support for multiple formats (json, yaml, table, text)
- Quiet and verbose mode handling
- Reusable across all agent commands
- Consistent formatting patterns
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import yaml

from claude_mpm.core.logger import get_logger


# Interface Definition
class IAgentOutputFormatter(ABC):
    """Interface for agent output formatting service."""

    @abstractmethod
    def format_agent_list(
        self,
        agents: List[Dict[str, Any]],
        output_format: str = "text",
        verbose: bool = False,
        quiet: bool = False,
    ) -> str:
        """Format list of agents for display."""

    @abstractmethod
    def format_agent_details(
        self, agent: Dict[str, Any], output_format: str = "text", verbose: bool = False
    ) -> str:
        """Format single agent details."""

    @abstractmethod
    def format_dependency_report(
        self,
        dependencies: Dict[str, Any],
        output_format: str = "text",
        show_status: bool = True,
    ) -> str:
        """Format dependency information."""

    @abstractmethod
    def format_deployment_result(
        self, result: Dict[str, Any], output_format: str = "text", verbose: bool = False
    ) -> str:
        """Format deployment results."""

    @abstractmethod
    def format_cleanup_result(
        self, result: Dict[str, Any], output_format: str = "text", dry_run: bool = False
    ) -> str:
        """Format cleanup results."""

    @abstractmethod
    def format_as_json(self, data: Any, pretty: bool = True) -> str:
        """Format data as JSON."""

    @abstractmethod
    def format_as_yaml(self, data: Any) -> str:
        """Format data as YAML."""

    @abstractmethod
    def format_as_table(
        self, headers: List[str], rows: List[List[str]], min_column_width: int = 10
    ) -> str:
        """Format data as table."""

    @abstractmethod
    def format_agents_by_tier(
        self, agents_by_tier: Dict[str, List[str]], output_format: str = "text"
    ) -> str:
        """Format agents grouped by tier."""

    @abstractmethod
    def format_fix_result(
        self, result: Dict[str, Any], output_format: str = "text"
    ) -> str:
        """Format fix operation results."""


class AgentOutputFormatter(IAgentOutputFormatter):
    """Implementation of agent output formatting service.

    WHY: Centralizes all agent output formatting logic to ensure consistency
    and reduce code duplication across agent commands.
    """

    def __init__(self):
        """Initialize the formatter."""
        self.logger = get_logger(self.__class__.__name__)

    def format_agent_list(
        self,
        agents: List[Dict[str, Any]],
        output_format: str = "text",
        verbose: bool = False,
        quiet: bool = False,
    ) -> str:
        """Format list of agents for display.

        Args:
            agents: List of agent dictionaries
            output_format: Output format (text, json, yaml, table)
            verbose: Include extra details
            quiet: Minimal output

        Returns:
            Formatted string for display
        """
        if output_format == "json":
            return self.format_as_json({"agents": agents, "count": len(agents)})
        if output_format == "yaml":
            return self.format_as_yaml({"agents": agents, "count": len(agents)})
        if output_format == "table":
            return self._format_agents_as_table(agents, verbose, quiet)
        # text format
        return self._format_agents_as_text(agents, verbose, quiet)

    def format_agent_details(
        self, agent: Dict[str, Any], output_format: str = "text", verbose: bool = False
    ) -> str:
        """Format single agent details.

        Args:
            agent: Agent dictionary with details
            output_format: Output format (text, json, yaml)
            verbose: Include extra details

        Returns:
            Formatted string for display
        """
        if output_format == "json":
            return self.format_as_json(agent)
        if output_format == "yaml":
            return self.format_as_yaml(agent)
        # text format
        lines = []
        lines.append(f"Agent: {agent.get('name', 'Unknown')}")
        lines.append("-" * 40)

        # Basic info
        for key in ["file", "path", "version", "description", "tier"]:
            if key in agent:
                lines.append(f"{key.capitalize()}: {agent[key]}")

        # Specializations
        if agent.get("specializations"):
            lines.append(f"Specializations: {', '.join(agent['specializations'])}")

        # Verbose mode additions
        if verbose:
            if "dependencies" in agent:
                lines.append("\nDependencies:")
                deps = agent["dependencies"]
                if deps.get("python"):
                    lines.append(f"  Python: {', '.join(deps['python'])}")
                if deps.get("system"):
                    lines.append(f"  System: {', '.join(deps['system'])}")

            if "metadata" in agent:
                lines.append("\nMetadata:")
                for k, v in agent["metadata"].items():
                    lines.append(f"  {k}: {v}")

        return "\n".join(lines)

    def format_dependency_report(
        self,
        dependencies: Dict[str, Any],
        output_format: str = "text",
        show_status: bool = True,
    ) -> str:
        """Format dependency information.

        Args:
            dependencies: Dictionary with dependency info
            output_format: Output format (text, json, yaml)
            show_status: Show installation status

        Returns:
            Formatted string for display
        """
        if output_format == "json":
            return self.format_as_json(dependencies)
        if output_format == "yaml":
            return self.format_as_yaml(dependencies)
        # text format
        lines = []
        lines.append("Agent Dependencies:")
        lines.append("-" * 40)

        # Python dependencies
        if dependencies.get("python"):
            lines.append(f"\nPython Dependencies ({len(dependencies['python'])}):")
            for dep in dependencies["python"]:
                if show_status and isinstance(dep, dict):
                    status = "✓" if dep.get("installed") else "✗"
                    lines.append(f"  {status} {dep.get('name', dep)}")
                else:
                    lines.append(f"  - {dep}")

        # System dependencies
        if dependencies.get("system"):
            lines.append(f"\nSystem Dependencies ({len(dependencies['system'])}):")
            for dep in dependencies["system"]:
                if show_status and isinstance(dep, dict):
                    status = "✓" if dep.get("installed") else "✗"
                    lines.append(f"  {status} {dep.get('name', dep)}")
                else:
                    lines.append(f"  - {dep}")

        # Missing dependencies
        if "missing" in dependencies:
            if dependencies["missing"].get("python"):
                lines.append(
                    f"\n❌ Missing Python: {len(dependencies['missing']['python'])}"
                )
                for dep in dependencies["missing"]["python"][:5]:
                    lines.append(f"   - {dep}")
                if len(dependencies["missing"]["python"]) > 5:
                    lines.append(
                        f"   ... and {len(dependencies['missing']['python']) - 5} more"
                    )

            if dependencies["missing"].get("system"):
                lines.append(
                    f"\n❌ Missing System: {len(dependencies['missing']['system'])}"
                )
                for dep in dependencies["missing"]["system"]:
                    lines.append(f"   - {dep}")

        return "\n".join(lines)

    def format_deployment_result(
        self, result: Dict[str, Any], output_format: str = "text", verbose: bool = False
    ) -> str:
        """Format deployment results.

        Args:
            result: Deployment result dictionary
            output_format: Output format (text, json, yaml)
            verbose: Include extra details

        Returns:
            Formatted string for display
        """
        if output_format == "json":
            return self.format_as_json(result)
        if output_format == "yaml":
            return self.format_as_yaml(result)
        # text format
        lines = []

        # Deployed agents
        deployed_count = result.get("deployed_count", 0)
        if deployed_count > 0:
            lines.append(f"✓ Deployed {deployed_count} agents")
            if verbose and "deployed" in result:
                for agent in result["deployed"]:
                    lines.append(f"  - {agent.get('name', agent)}")

        # Updated agents
        updated_count = result.get("updated_count", 0)
        if updated_count > 0:
            lines.append(f"✓ Updated {updated_count} agents")
            if verbose and "updated" in result:
                for agent in result["updated"]:
                    lines.append(f"  - {agent.get('name', agent)}")

        # Skipped agents
        if result.get("skipped"):
            lines.append(f"→ Skipped {len(result['skipped'])} up-to-date agents")
            if verbose:
                for agent in result["skipped"]:
                    lines.append(f"  - {agent.get('name', agent)}")

        # Errors
        if result.get("errors"):
            lines.append(f"\n❌ Encountered {len(result['errors'])} errors:")
            for error in result["errors"]:
                lines.append(f"  - {error}")

        # Target directory
        if "target_dir" in result:
            lines.append(f"\nTarget directory: {result['target_dir']}")

        if not lines:
            lines.append("No agents were deployed (all up to date)")

        return "\n".join(lines)

    def format_cleanup_result(
        self, result: Dict[str, Any], output_format: str = "text", dry_run: bool = False
    ) -> str:
        """Format cleanup results.

        Args:
            result: Cleanup result dictionary
            output_format: Output format (text, json, yaml)
            dry_run: Whether this was a dry run

        Returns:
            Formatted string for display
        """
        if output_format == "json":
            result["dry_run"] = dry_run
            return self.format_as_json(result)
        if output_format == "yaml":
            result["dry_run"] = dry_run
            return self.format_as_yaml(result)
        # text format
        lines = []

        # Orphaned agents found
        if result.get("orphaned"):
            lines.append(f"Found {len(result['orphaned'])} orphaned agent(s):")
            for orphan in result["orphaned"]:
                name = orphan.get("name", "Unknown")
                version = orphan.get("version", "Unknown")
                lines.append(f"  - {name} v{version}")

        # Dry run vs actual cleanup
        if dry_run:
            if result.get("orphaned"):
                lines.append(
                    f"\n📝 This was a dry run. Use --force to actually remove "
                    f"{len(result['orphaned'])} orphaned agent(s)"
                )
            else:
                lines.append("✅ No orphaned agents found")
        else:
            # Removed agents
            if result.get("removed"):
                lines.append(
                    f"\n✅ Successfully removed {len(result['removed'])} orphaned agent(s)"
                )
                for agent in result["removed"]:
                    lines.append(f"  - {agent}")
            elif "cleaned_count" in result:
                cleaned_count = result["cleaned_count"]
                if cleaned_count > 0:
                    lines.append(f"✓ Cleaned {cleaned_count} deployed agents")
                else:
                    lines.append("No deployed agents to clean")
            else:
                lines.append("✅ No orphaned agents found")

            # Errors
            if result.get("errors"):
                lines.append(f"\n❌ Encountered {len(result['errors'])} error(s):")
                for error in result["errors"]:
                    lines.append(f"  - {error}")

        return "\n".join(lines)

    def format_as_json(self, data: Any, pretty: bool = True) -> str:
        """Format data as JSON.

        Args:
            data: Data to format
            pretty: Use pretty printing with indentation

        Returns:
            JSON string
        """
        if pretty:
            return json.dumps(data, indent=2, sort_keys=True)
        return json.dumps(data)

    def format_as_yaml(self, data: Any) -> str:
        """Format data as YAML.

        Args:
            data: Data to format

        Returns:
            YAML string
        """
        return yaml.dump(data, default_flow_style=False, sort_keys=True)

    def format_as_table(
        self, headers: List[str], rows: List[List[str]], min_column_width: int = 10
    ) -> str:
        """Format data as table.

        Args:
            headers: Table headers
            rows: Table rows
            min_column_width: Minimum column width

        Returns:
            Formatted table string
        """
        # Calculate column widths
        col_widths = [max(min_column_width, len(h)) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))

        # Build table
        lines = []

        # Header
        header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
        lines.append(header_line)
        lines.append("-" * len(header_line))

        # Rows
        for row in rows:
            row_line = " | ".join(
                str(cell).ljust(col_widths[i]) if i < len(row) else " " * col_widths[i]
                for i in range(len(headers))
                for cell in [row[i] if i < len(row) else ""]
            )
            lines.append(row_line)

        return "\n".join(lines)

    def _format_agents_as_text(
        self, agents: List[Dict[str, Any]], verbose: bool, quiet: bool
    ) -> str:
        """Format agents as text output.

        Args:
            agents: List of agent dictionaries
            verbose: Include extra details
            quiet: Minimal output

        Returns:
            Formatted text string
        """
        if not agents:
            return "No agents found"

        lines = []

        if not quiet:
            lines.append("Available Agents:")
            lines.append("-" * 80)

        for agent in agents:
            if quiet:
                # Minimal output - just names
                lines.append(agent.get("name", agent.get("file", "Unknown")))
            else:
                # Standard output
                lines.append(f"📄 {agent.get('file', 'Unknown')}")
                if "name" in agent:
                    lines.append(f"   Name: {agent['name']}")
                if "description" in agent:
                    lines.append(f"   Description: {agent['description']}")
                if "version" in agent:
                    lines.append(f"   Version: {agent['version']}")

                # Verbose additions
                if verbose:
                    if "path" in agent:
                        lines.append(f"   Path: {agent['path']}")
                    if "tier" in agent:
                        lines.append(f"   Tier: {agent['tier']}")
                    if agent.get("specializations"):
                        lines.append(
                            f"   Specializations: {', '.join(agent['specializations'])}"
                        )

                if not quiet:
                    lines.append("")  # Empty line between agents

        return "\n".join(lines)

    def _format_agents_as_table(
        self, agents: List[Dict[str, Any]], verbose: bool, quiet: bool
    ) -> str:
        """Format agents as table output.

        Args:
            agents: List of agent dictionaries
            verbose: Include extra details
            quiet: Minimal output

        Returns:
            Formatted table string
        """
        if not agents:
            return "No agents found"

        # Define headers based on verbosity
        if quiet:
            headers = ["Name"]
            rows = [
                [agent.get("name", agent.get("file", "Unknown"))] for agent in agents
            ]
        elif verbose:
            headers = ["Name", "Version", "Tier", "Description", "Path"]
            rows = []
            for agent in agents:
                rows.append(
                    [
                        agent.get("name", agent.get("file", "Unknown")),
                        agent.get("version", "-"),
                        agent.get("tier", "-"),
                        agent.get("description", "-")[
                            :50
                        ],  # Truncate long descriptions
                        str(agent.get("path", "-"))[:40],  # Truncate long paths
                    ]
                )
        else:
            headers = ["Name", "Version", "Description"]
            rows = []
            for agent in agents:
                rows.append(
                    [
                        agent.get("name", agent.get("file", "Unknown")),
                        agent.get("version", "-"),
                        agent.get("description", "-")[
                            :60
                        ],  # Truncate long descriptions
                    ]
                )

        return self.format_as_table(headers, rows)

    def format_agents_by_tier(
        self, agents_by_tier: Dict[str, List[str]], output_format: str = "text"
    ) -> str:
        """Format agents grouped by tier.

        Args:
            agents_by_tier: Dictionary mapping tier names to agent lists
            output_format: Output format (text, json, yaml)

        Returns:
            Formatted string for display
        """
        if output_format == "json":
            return self.format_as_json(agents_by_tier)
        if output_format == "yaml":
            return self.format_as_yaml(agents_by_tier)
        # text format
        lines = []
        lines.append("Agents by Tier/Precedence:")
        lines.append("=" * 50)

        for tier, agents in agents_by_tier.items():
            lines.append(f"\n{tier.upper()}:")
            lines.append("-" * 20)
            if agents:
                for agent in agents:
                    lines.append(f"  • {agent}")
            else:
                lines.append("  (none)")

        return "\n".join(lines)

    def format_fix_result(
        self, result: Dict[str, Any], output_format: str = "text"
    ) -> str:
        """Format fix operation results.

        Args:
            result: Fix operation result dictionary
            output_format: Output format (text, json, yaml)

        Returns:
            Formatted string for display
        """
        if output_format == "json":
            return self.format_as_json(result)
        if output_format == "yaml":
            return self.format_as_yaml(result)
        # text format
        lines = []
        lines.append("✓ Agent deployment issues fixed")

        if result.get("fixes_applied"):
            lines.append("\nFixes applied:")
            for fix in result["fixes_applied"]:
                lines.append(f"  - {fix}")

        if result.get("errors"):
            lines.append(f"\n❌ Encountered {len(result['errors'])} error(s):")
            for error in result["errors"]:
                lines.append(f"  - {error}")

        if result.get("warnings"):
            lines.append("\n⚠️ Warnings:")
            for warning in result["warnings"]:
                lines.append(f"  - {warning}")

        return "\n".join(lines)
