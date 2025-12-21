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
        CLICommands.AGENTS.value,
        help="Manage agents and deployment",
        description="""
Manage Claude MPM agents.

NOTE: For interactive agent management, use 'claude-mpm config' instead.
      The 'agents manage' command has been deprecated in favor of the
      unified configuration interface.

Available commands:
  discover    Discover available agents from configured sources
  deploy      Deploy agents to your project
  list        List available agents
  manage      (Deprecated) Use 'claude-mpm config' instead
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
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

    # Manage local agents (interactive menu) - DEPRECATED
    manage_parser = agents_subparsers.add_parser(
        "manage",
        help="(Deprecated) Manage local agents - use 'claude-mpm config' instead",
        description="Manage locally deployed agents. Note: This command has been deprecated. "
        "Please use 'claude-mpm config' for the enhanced configuration interface.",
    )
    manage_parser.epilog = (
        "\nDEPRECATION NOTICE:\n"
        "This command has been deprecated in favor of 'claude-mpm config' which provides\n"
        "a unified interface for managing agents, skills, templates, and behavior settings.\n"
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
    deploy_agents_parser.add_argument(
        "--preset",
        type=str,
        help="Deploy agents by preset name (minimal, python-dev, nextjs-fullstack, etc.)",
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

    # Cleanup: sync, install, and remove old underscore-named agents
    cleanup_parser = agents_subparsers.add_parser(
        "cleanup",
        help="Sync agents, install with new naming, and remove old underscore-named duplicates",
    )
    cleanup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it",
    )
    cleanup_parser.add_argument(
        "--target",
        type=Path,
        help="Target directory for agent deployment (default: project .claude-mpm/agents/)",
    )
    cleanup_parser.add_argument(
        "--global",
        dest="global_deployment",
        action="store_true",
        help="Deploy to global ~/.claude/agents/ instead of project directory",
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

    # Migrate user-level agents to project-level (DEPRECATION support)
    migrate_parser = agents_subparsers.add_parser(
        "migrate-to-project",
        help="Migrate user-level agents to project-level (user-level is DEPRECATED)",
    )
    migrate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually doing it",
    )
    migrate_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite existing project agents if conflicts",
    )

    # Deploy all agents from sources (single-tier deployment)
    deploy_all_parser = agents_subparsers.add_parser(
        "deploy-all",
        help="Deploy all agents from configured sources (single-tier deployment)",
    )
    deploy_all_parser.add_argument(
        "--force-sync",
        action="store_true",
        help="Force sync repositories before deploying (ignore cache)",
    )
    deploy_all_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deployed without actually deploying",
    )

    # List available agents from sources
    available_parser = agents_subparsers.add_parser(
        "available",
        help="List available agents from all configured sources",
    )
    available_parser.add_argument(
        "--source",
        help="Filter by source repository (e.g., 'owner/repo/subdirectory')",
    )
    available_parser.add_argument(
        "--format",
        choices=["table", "json", "simple"],
        default="table",
        help="Output format (default: table)",
    )

    # Discover agents with rich filtering (Phase 1: Discovery & Browsing)
    discover_parser = agents_subparsers.add_parser(
        "discover",
        help="Discover available agents from configured sources with rich filtering",
    )
    discover_parser.add_argument(
        "--source",
        help="Filter by specific source ID (e.g., 'owner/repo')",
    )
    discover_parser.add_argument(
        "--category",
        help="Filter by category (e.g., 'engineer/backend', 'qa', 'ops/platform')",
    )
    discover_parser.add_argument(
        "--language",
        help="Filter by programming language (e.g., 'python', 'javascript', 'rust')",
    )
    discover_parser.add_argument(
        "--framework",
        help="Filter by framework (e.g., 'react', 'nextjs', 'django')",
    )
    discover_parser.add_argument(
        "--platform",
        help="Filter by platform (e.g., 'vercel', 'gcp', 'docker')",
    )
    discover_parser.add_argument(
        "--specialization",
        help="Filter by specialization (e.g., 'data', 'security', 'mobile')",
    )
    discover_parser.add_argument(
        "--format",
        choices=["table", "json", "simple"],
        default="table",
        help="Output format (default: table)",
    )
    discover_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show descriptions and metadata for each agent",
    )

    # Phase 3: Agent Selection Modes (single-tier deployment)
    # Minimal configuration - deploy 6 core agents
    deploy_minimal_parser = agents_subparsers.add_parser(
        "deploy-minimal",
        help="Deploy minimal configuration (6 core agents: engineer, documentation, qa, research, ops, ticketing)",
    )
    deploy_minimal_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deployed without actually deploying",
    )

    # Auto-configure - detect toolchain and deploy matching agents
    deploy_auto_parser = agents_subparsers.add_parser(
        "deploy-auto",
        help="Auto-detect project toolchain and deploy matching agents",
    )
    deploy_auto_parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="Project path to scan for toolchain detection (default: current directory)",
    )
    deploy_auto_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deployed without actually deploying",
    )

    # ============================================================================
    # Collection-Based Agent Management Commands
    # ============================================================================
    # Purpose: Enable collection-based agent selection and deployment
    # Commands: list-collections, deploy-collection, list-by-collection
    # NEW: Enhanced agent matching with collection_id support
    # ============================================================================

    # list-collections: List all available agent collections
    agents_subparsers.add_parser(
        "list-collections",
        help="List all available agent collections",
        description="Display all agent collections with agent counts and collection metadata",
    )

    # deploy-collection: Deploy all agents from a specific collection
    deploy_collection_parser = agents_subparsers.add_parser(
        "deploy-collection",
        help="Deploy all agents from a specific collection",
        description="Deploy all agents from a named collection (e.g., 'bobmatnyc/claude-mpm-agents')",
    )
    deploy_collection_parser.add_argument(
        "collection_id",
        help="Collection ID in format 'owner/repo-name' (e.g., 'bobmatnyc/claude-mpm-agents')",
    )
    deploy_collection_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force redeployment even if agents are already deployed",
    )
    deploy_collection_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deployed without actually deploying",
    )

    # list-by-collection: List agents filtered by collection
    list_by_collection_parser = agents_subparsers.add_parser(
        "list-by-collection",
        help="List agents from a specific collection",
        description="Display agents from a specific collection with metadata",
    )
    list_by_collection_parser.add_argument(
        "collection_id",
        help="Collection ID to filter by (e.g., 'bobmatnyc/claude-mpm-agents')",
    )
    list_by_collection_parser.add_argument(
        "--format",
        choices=["table", "json", "yaml"],
        default="table",
        help="Output format (default: table)",
    )

    # ============================================================================
    # Cache Git Management Commands (claude-mpm Issue 1M-442 Phase 2)
    # ============================================================================
    # Purpose: Enable git workflow for agent cache management
    # Commands: cache-status, cache-pull, cache-commit, cache-push, cache-sync
    # Documentation: See docs/research/cache-update-workflow-analysis-2025-12-03.md
    # ============================================================================

    # cache-status: Show git status of agent cache
    agents_subparsers.add_parser(
        "cache-status",
        help="Show git status of agent cache directory",
        description="Display git status including branch, uncommitted changes, and unpushed commits",
    )

    # cache-pull: Pull latest agents from remote
    cache_pull_parser = agents_subparsers.add_parser(
        "cache-pull",
        help="Pull latest agents from remote repository",
        description="Fetch and merge latest agent changes from GitHub remote repository",
    )
    cache_pull_parser.add_argument(
        "--branch",
        default="main",
        help="Branch to pull from (default: main)",
    )

    # cache-commit: Commit changes to agent cache
    cache_commit_parser = agents_subparsers.add_parser(
        "cache-commit",
        help="Commit changes to agent cache",
        description="Stage and commit changes to local agent cache git repository",
    )
    cache_commit_parser.add_argument(
        "--message",
        "-m",
        help="Commit message (default: 'feat: update agents from local development')",
    )
    cache_commit_parser.add_argument(
        "--files",
        nargs="+",
        help="Specific files to commit (default: all modified files)",
    )

    # cache-push: Push agent changes to remote
    cache_push_parser = agents_subparsers.add_parser(
        "cache-push",
        help="Push agent changes to remote repository",
        description="Push committed changes from local cache to GitHub remote repository",
    )
    cache_push_parser.add_argument(
        "--branch",
        default="main",
        help="Branch to push to (default: main)",
    )
    cache_push_parser.add_argument(
        "--auto-commit",
        action="store_true",
        help="Automatically commit uncommitted changes before pushing",
    )

    # cache-sync: Full cache sync workflow
    cache_sync_parser = agents_subparsers.add_parser(
        "cache-sync",
        help="Full agent cache sync with remote",
        description="Complete sync workflow: pull latest, commit local changes, push to remote",
    )
    cache_sync_parser.add_argument(
        "--message",
        "-m",
        help="Commit message for any uncommitted changes",
    )
    cache_sync_parser.add_argument(
        "--skip-pull",
        action="store_true",
        help="Skip pulling from remote before sync",
    )
    cache_sync_parser.add_argument(
        "--skip-push",
        action="store_true",
        help="Skip pushing to remote after sync",
    )

    return agents_parser
