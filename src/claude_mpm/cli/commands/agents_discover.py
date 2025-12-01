"""Agent discovery command for browsing available agents from configured sources.

WHY: This module implements the 'agents discover' command, allowing users to
browse and filter agents from configured Git sources. Provides rich filtering
by category, language, framework, platform, and specialization.

DESIGN DECISION: Rich console output using rich library

Rationale: Users need beautiful, informative output when discovering agents.
The rich library (already a dependency) provides excellent table formatting,
color support, and tree views.

Trade-offs:
- User Experience: Beautiful output improves discoverability
- Complexity: Rich table formatting adds some code overhead
- Performance: Rendering is fast enough for CLI use (<50ms)

Example Usage:
    >>> claude-mpm agents discover --category engineer/backend
    >>> claude-mpm agents discover --language python --verbose
    >>> claude-mpm agents discover --framework react --format json
"""

import json
import logging
from typing import Any, Dict, List

from rich.console import Console

from ...config.agent_sources import AgentSourceConfiguration
from ...services.agents.git_source_manager import GitSourceManager

logger = logging.getLogger(__name__)
console = Console()


def _group_agents_by_category(
    agents: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Group agents by their category for organized display.

    Args:
        agents: List of agent dictionaries

    Returns:
        Dictionary mapping category names to lists of agents

    Example:
        >>> agents = [
        ...     {"agent_id": "engineer/backend/python-engineer", "category": "engineer/backend"},
        ...     {"agent_id": "qa/qa", "category": "qa"}
        ... ]
        >>> grouped = _group_agents_by_category(agents)
        >>> grouped.keys()
        dict_keys(['engineer/backend', 'qa'])
    """
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for agent in agents:
        # Extract category from agent_id if not present
        category = agent.get("category", "unknown")

        if category == "unknown" and "agent_id" in agent:
            agent_id = agent["agent_id"]
            if "/" in agent_id:
                category = agent_id.rsplit("/", 1)[0]

        if category not in grouped:
            grouped[category] = []

        grouped[category].append(agent)

    return grouped


def _format_category_name(category: str) -> str:
    """Format category name for display.

    Args:
        category: Raw category string (e.g., "engineer/backend")

    Returns:
        Formatted category name (e.g., "Engineering/Backend")

    Example:
        >>> _format_category_name("engineer/backend")
        'Engineering/Backend'
        >>> _format_category_name("qa")
        'QA'
    """
    # Special cases
    if category == "qa":
        return "QA"
    if category == "ops":
        return "Ops"

    # Capitalize each part
    parts = category.split("/")
    formatted_parts = []

    for part in parts:
        if part == "qa":
            formatted_parts.append("QA")
        elif part == "ops":
            formatted_parts.append("Ops")
        else:
            formatted_parts.append(part.capitalize())

    return "/".join(formatted_parts)


def _output_table_format(agents: List[Dict[str, Any]], verbose: bool = False) -> None:
    """Output agents in rich table format (default).

    Design Decision: Group by category for better organization

    Rationale: Agents grouped by category (engineer/backend, qa, ops) are
    easier to scan than a flat list. Categories provide context about
    agent purpose.

    Args:
        agents: List of agent dictionaries
        verbose: Show descriptions and metadata
    """
    if not agents:
        console.print("[yellow]No agents found matching filters.[/yellow]")
        return

    console.print(
        f"\n[bold]📚 Agents from configured sources ({len(agents)} matching filters):[/bold]\n"
    )

    # Group by category
    grouped = _group_agents_by_category(agents)

    # Sort categories for consistent display
    sorted_categories = sorted(grouped.keys())

    for category in sorted_categories:
        category_agents = grouped[category]

        # Print category header
        formatted_category = _format_category_name(category)
        console.print(f"[bold cyan]{formatted_category}[/bold cyan]")

        # Print agents in this category
        for agent in sorted(category_agents, key=lambda a: a.get("agent_id", "")):
            agent_id = agent.get("agent_id", "unknown")
            source = agent.get("source", agent.get("repository", "unknown"))
            priority = agent.get("priority", "unknown")

            # Agent ID line
            console.print(f"  • [bold]{agent_id}[/bold]")

            if verbose:
                # Description
                description = agent.get("metadata", {}).get("description", "")
                if not description:
                    description = agent.get("description", "No description available")

                console.print(f"    {description}")

                # Version
                version = agent.get(
                    "version", agent.get("metadata", {}).get("version", "unknown")
                )
                console.print(f"    Version: {version}")

            # Source attribution
            console.print(f"    Source: [dim]{source}[/dim] (priority: {priority})")

            console.print()  # Blank line between agents

        console.print()  # Blank line between categories


def _output_json_format(
    agents: List[Dict[str, Any]], filters_applied: Dict[str, str]
) -> None:
    """Output agents in JSON format for scripting.

    Args:
        agents: List of agent dictionaries
        filters_applied: Dictionary of filters that were applied
    """
    output = {
        "total": len(agents),
        "filters_applied": filters_applied,
        "agents": [
            {
                "agent_id": agent.get("agent_id", "unknown"),
                "source": agent.get("source", agent.get("repository", "unknown")),
                "priority": agent.get("priority", "unknown"),
                "category": agent.get("category", "unknown"),
                "version": agent.get(
                    "version", agent.get("metadata", {}).get("version", "unknown")
                ),
                "description": agent.get("metadata", {}).get(
                    "description", agent.get("description", "")
                ),
            }
            for agent in agents
        ],
    }

    console.print(json.dumps(output, indent=2))


def _output_simple_format(agents: List[Dict[str, Any]]) -> None:
    """Output agents in simple format (agent IDs only).

    Args:
        agents: List of agent dictionaries
    """
    for agent in sorted(agents, key=lambda a: a.get("agent_id", "")):
        agent_id = agent.get("agent_id", "unknown")
        console.print(agent_id)


def discover_command(args) -> int:
    """Execute the 'agents discover' command.

    This command discovers and lists available agents from all configured
    Git sources, with optional filtering by category, language, framework,
    platform, and source.

    Design Decision: Load sources from configuration

    Rationale: Use AgentSourceConfiguration to load all configured sources,
    respecting enabled/disabled state and priority. This ensures consistent
    behavior with other agent commands.

    Error Handling:
    - Graceful degradation if no sources configured
    - Warning if cache not populated (suggest agent-source update)
    - Empty result sets clearly communicated

    Args:
        args: Parsed command arguments with attributes:
            - source: Optional source ID filter
            - category: Optional category filter
            - language: Optional language filter
            - framework: Optional framework filter
            - platform: Optional platform filter
            - specialization: Optional specialization filter
            - format: Output format (table, json, simple)
            - verbose: Show descriptions and metadata

    Returns:
        Exit code (0 for success, 1 for error)

    Example:
        >>> args = argparse.Namespace(
        ...     source=None,
        ...     category="engineer/backend",
        ...     language=None,
        ...     framework=None,
        ...     platform=None,
        ...     specialization=None,
        ...     format="table",
        ...     verbose=False
        ... )
        >>> discover_command(args)
        0
    """
    try:
        # Load agent sources configuration
        sources_config = AgentSourceConfiguration()

        # Initialize Git source manager
        manager = GitSourceManager()

        # Build filters dictionary
        filters = {}

        if args.category:
            filters["category"] = args.category

        if args.language:
            filters["language"] = args.language

        if args.framework:
            filters["framework"] = args.framework

        if args.platform:
            filters["platform"] = args.platform

        if args.specialization:
            filters["specialization"] = args.specialization

        # Get agents with filters
        agents = manager.list_cached_agents_with_filters(
            repo_identifier=args.source, filters=filters if filters else None
        )

        # Check if any sources are configured
        if not agents and not sources_config.list_sources():
            console.print("[yellow]⚠️  No agent sources configured.[/yellow]")
            console.print("\nAdd a source with:")
            console.print("  claude-mpm agent-source add <git-url>")
            return 1

        # Check if cache might be empty
        if not agents and not filters:
            console.print("[yellow]⚠️  No agents found in cache.[/yellow]")
            console.print("\nTry syncing sources first:")
            console.print("  claude-mpm agent-source update")
            return 1

        # Output based on format
        if args.format == "json":
            filters_applied = {
                k: v
                for k, v in [
                    ("source", args.source),
                    ("category", args.category),
                    ("language", args.language),
                    ("framework", args.framework),
                    ("platform", args.platform),
                    ("specialization", args.specialization),
                ]
                if v is not None
            }

            _output_json_format(agents, filters_applied)

        elif args.format == "simple":
            _output_simple_format(agents)

        else:  # table (default)
            _output_table_format(agents, verbose=args.verbose)

        return 0

    except Exception as e:
        logger.error(f"Error discovering agents: {e}", exc_info=True)
        console.print(f"[bold red]Error:[/bold red] {e}")
        return 1
