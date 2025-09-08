from pathlib import Path

"""
Agents command parser for claude-mpm CLI.

WHY: This module contains all arguments specific to agent management commands,
extracted from the monolithic parser.py for better organization.

DESIGN DECISION: Agent commands are complex with multiple subcommands for
deployment, listing, validation, etc., warranting their own module.
"""

import argparse

from ...constants import AgentCommands, CLICommands
from .base_parser import add_common_arguments


def add_agents_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Add the agents subparser with all agent management commands.

    WHY: Agent management has multiple complex subcommands (list, deploy, validate, etc.)
    that need their own argument structures.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured agents subparser
    """
    # Agents command with subcommands
    agents_parser = subparsers.add_parser(
        CLICommands.AGENTS.value, help="Manage agents and deployment"
    )
    add_common_arguments(agents_parser)

    agents_subparsers = agents_parser.add_subparsers(
        dest="agents_command", help="Agent commands", metavar="SUBCOMMAND"
    )

    # List agents
    list_agents_parser = agents_subparsers.add_parser(
        AgentCommands.LIST.value, help="List available agents"
    )
    list_agents_parser.add_argument(
        "--system", action="store_true", help="List system agents"
    )
    list_agents_parser.add_argument(
        "--deployed", action="store_true", help="List deployed agents"
    )
    list_agents_parser.add_argument(
        "--by-tier",
        action="store_true",
        help="List agents grouped by precedence tier (PROJECT > USER > SYSTEM)",
    )

    # View agent details
    view_agent_parser = agents_subparsers.add_parser(
        AgentCommands.VIEW.value,
        help="View detailed information about a specific agent",
    )
    view_agent_parser.add_argument("agent_name", help="Name of the agent to view")
    view_agent_parser.add_argument(
        "--show-dependencies", action="store_true", help="Show agent dependencies"
    )
    view_agent_parser.add_argument(
        "--show-config", action="store_true", help="Show agent configuration"
    )

    # Create local agent
    create_agent_parser = agents_subparsers.add_parser(
        "create", help="Create a new local agent template"
    )
    create_agent_parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Launch interactive agent creation wizard",
    )
    create_agent_parser.add_argument("--agent-id", help="Agent ID (lowercase, hyphens)")
    create_agent_parser.add_argument("--name", help="Agent display name")
    create_agent_parser.add_argument(
        "--model",
        choices=["sonnet", "opus", "haiku"],
        default="sonnet",
        help="Model to use",
    )
    create_agent_parser.add_argument(
        "--inherit-from", help="System agent to inherit from"
    )

    # Edit local agent
    edit_agent_parser = agents_subparsers.add_parser(
        "edit", help="Edit a local agent template"
    )
    edit_agent_parser.add_argument("agent_id", help="Agent ID to edit")
    edit_agent_parser.add_argument(
        "--interactive", "-i", action="store_true", help="Use interactive editor"
    )
    edit_agent_parser.add_argument(
        "--editor", help="Editor to use (default: $EDITOR or nano)"
    )

    # Delete local agent
    delete_agent_parser = agents_subparsers.add_parser(
        "delete", help="Delete a local agent template"
    )
    delete_agent_parser.add_argument(
        "agent_ids", nargs="+", help="Agent ID(s) to delete"
    )
    delete_agent_parser.add_argument(
        "--force", "-f", action="store_true", help="Skip confirmation prompts"
    )
    delete_agent_parser.add_argument(
        "--keep-deployment",
        action="store_true",
        help="Keep Claude Code deployment, only delete template",
    )
    delete_agent_parser.add_argument(
        "--backup", action="store_true", help="Create backup before deletion"
    )

    # Manage local agents (interactive menu)
    manage_agents_parser = agents_subparsers.add_parser(
        "manage", help="Interactive menu for managing local agents"
    )

    # Configure agent deployment settings
    configure_agents_parser = agents_subparsers.add_parser(
        "configure", help="Configure which agents are deployed"
    )
    configure_agents_parser.add_argument(
        "--enable",
        nargs="+",
        metavar="AGENT_ID",
        help="Enable specific agents for deployment",
    )
    configure_agents_parser.add_argument(
        "--disable",
        nargs="+",
        metavar="AGENT_ID",
        help="Disable specific agents from deployment",
    )
    configure_agents_parser.add_argument(
        "--enable-all", action="store_true", help="Enable all agents for deployment"
    )
    configure_agents_parser.add_argument(
        "--disable-system",
        action="store_true",
        help="Disable all system agents from deployment",
    )
    configure_agents_parser.add_argument(
        "--enable-system",
        action="store_true",
        help="Enable system agents for deployment",
    )
    configure_agents_parser.add_argument(
        "--disable-local",
        action="store_true",
        help="Disable local project agents from deployment",
    )
    configure_agents_parser.add_argument(
        "--enable-local",
        action="store_true",
        help="Enable local project agents for deployment",
    )
    configure_agents_parser.add_argument(
        "--show", action="store_true", help="Show current deployment configuration"
    )
    configure_agents_parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive configuration mode",
    )

    # Deploy agents
    deploy_agents_parser = agents_subparsers.add_parser(
        AgentCommands.DEPLOY.value, help="Deploy agents to target directory"
    )
    deploy_agents_parser.add_argument(
        "--target", type=Path, help="Target directory (default: .claude/)"
    )
    deploy_agents_parser.add_argument(
        "--agents", nargs="*", help="Specific agents to deploy (default: all)"
    )
    deploy_agents_parser.add_argument(
        "--force", action="store_true", help="Force deployment even if target exists"
    )
    deploy_agents_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deployed without actually deploying",
    )

    # Validate agents
    validate_agents_parser = agents_subparsers.add_parser(
        AgentCommands.FIX.value, help="Validate agent configurations"
    )
    validate_agents_parser.add_argument(
        "--agents", nargs="*", help="Specific agents to validate (default: all)"
    )
    validate_agents_parser.add_argument(
        "--strict", action="store_true", help="Use strict validation rules"
    )

    # Clean agents
    clean_agents_parser = agents_subparsers.add_parser(
        AgentCommands.CLEAN.value, help="Remove deployed system agents"
    )
    clean_agents_parser.add_argument(
        "--target", type=Path, help="Target directory (default: .claude/)"
    )

    # Dependencies management
    deps_list_parser = agents_subparsers.add_parser(
        "deps-list", help="List agent dependencies and their status"
    )
    deps_list_parser.add_argument(
        "--agents", nargs="*", help="Specific agents to check (default: all)"
    )
    deps_list_parser.add_argument(
        "--missing-only", action="store_true", help="Show only missing dependencies"
    )
    deps_list_parser.add_argument(
        "--format",
        choices=["text", "pip", "json"],
        default="text",
        help="Output format for dependency list",
    )

    deps_fix_parser = agents_subparsers.add_parser(
        "deps-fix", help="Fix missing agent dependencies with robust retry logic"
    )
    deps_fix_parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts per package (default: 3)",
    )

    # Cleanup orphaned agents
    cleanup_orphaned_parser = agents_subparsers.add_parser(
        "cleanup-orphaned", help="Clean up orphaned agents that don't have templates"
    )
    cleanup_orphaned_parser.add_argument(
        "--agents-dir",
        type=Path,
        help="Directory containing deployed agents (default: .claude/agents/)",
    )
    cleanup_orphaned_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Only show what would be removed without actually removing (default)",
    )
    cleanup_orphaned_parser.add_argument(
        "--force",
        action="store_true",
        help="Actually remove orphaned agents (disables dry-run)",
    )
    cleanup_orphaned_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only show summary, not individual agents",
    )

    return agents_parser
