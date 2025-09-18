"""
Agent Manager parser module for claude-mpm CLI.

This module defines the argument parser for the agent-manager command,
which provides comprehensive agent lifecycle management capabilities.
"""

import argparse


def add_agent_manager_subparser(subparsers: argparse._SubParsersAction) -> None:
    """
    Add the agent-manager subcommand to the parser.

    Args:
        subparsers: The subparsers object to add to
    """
    # Create the agent-manager parser
    agent_manager_parser = subparsers.add_parser(
        "agent-manager",
        help="Manage agent creation, customization, and deployment",
        description="Comprehensive agent lifecycle management for Claude MPM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Standard Commands:
  claude-mpm agent-manager list                          # List all agents across tiers
  claude-mpm agent-manager create                        # Interactive agent creation
  claude-mpm agent-manager create --id my-agent          # Create agent with ID
  claude-mpm agent-manager variant --base research       # Create research variant
  claude-mpm agent-manager deploy --id my-agent --tier user  # Deploy to user tier
  claude-mpm agent-manager customize-pm --level project  # Edit .claude-mpm/INSTRUCTIONS.md
  claude-mpm agent-manager show --id engineer            # Show agent details
  claude-mpm agent-manager test --id my-agent            # Test agent configuration
  claude-mpm agent-manager templates                     # List available templates
  claude-mpm agent-manager reset --dry-run               # Preview agent cleanup
  claude-mpm agent-manager reset --force                 # Remove all claude-mpm agents
  claude-mpm agent-manager reset --project-only          # Clean only project agents

Local Agent Commands:
  claude-mpm agent-manager create-local --agent-id my-custom  # Create local template
  claude-mpm agent-manager deploy-local --agent-id my-custom  # Deploy local template
  claude-mpm agent-manager list-local                         # List local templates
  claude-mpm agent-manager sync-local                         # Sync templates with deployment
  claude-mpm agent-manager export-local --output ./agents     # Export templates
  claude-mpm agent-manager import-local --input ./agents      # Import templates
  claude-mpm agent-manager delete-local --agent-id my-custom  # Delete single agent
  claude-mpm agent-manager delete-local --all --backup        # Delete all with backup
""",
    )

    # Create subcommands for agent-manager
    agent_subparsers = agent_manager_parser.add_subparsers(
        dest="agent_manager_command",
        help="Agent management operations",
        metavar="OPERATION",
    )

    # List command
    list_parser = agent_subparsers.add_parser(
        "list", help="List all agents across tiers with hierarchy"
    )
    list_parser.add_argument(
        "--format",
        choices=["text", "json", "yaml"],
        default="text",
        help="Output format (default: text)",
    )

    # Create command
    create_parser = agent_subparsers.add_parser(
        "create", help="Create a new agent (interactive or with arguments)"
    )
    create_parser.add_argument(
        "--id", dest="agent_id", help="Agent ID (lowercase, hyphens only)"
    )
    create_parser.add_argument("--name", help="Display name for the agent")
    create_parser.add_argument("--description", help="Agent purpose and capabilities")
    create_parser.add_argument(
        "--model",
        choices=["sonnet", "opus", "haiku"],
        default="sonnet",
        help="LLM model to use (default: sonnet)",
    )
    create_parser.add_argument(
        "--tool-choice",
        choices=["auto", "required", "any", "none"],
        default="auto",
        help="Tool selection strategy (default: auto)",
    )
    create_parser.add_argument("--template", help="Base template to extend from")
    create_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    # Variant command
    variant_parser = agent_subparsers.add_parser(
        "variant", help="Create an agent variant based on existing agent"
    )
    variant_parser.add_argument(
        "--base",
        dest="base_agent",
        required=True,
        help="Base agent ID to create variant from",
    )
    variant_parser.add_argument(
        "--id", dest="variant_id", required=True, help="Variant agent ID"
    )
    variant_parser.add_argument("--name", help="Display name for the variant")
    variant_parser.add_argument(
        "--model",
        choices=["sonnet", "opus", "haiku"],
        help="Override model for variant",
    )
    variant_parser.add_argument(
        "--tool-choice",
        choices=["auto", "required", "any", "none"],
        help="Override tool choice for variant",
    )
    variant_parser.add_argument(
        "--instructions", help="Additional instructions to append for variant"
    )
    variant_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    # Deploy command
    deploy_parser = agent_subparsers.add_parser(
        "deploy", help="Deploy agent to specified tier"
    )
    deploy_parser.add_argument(
        "--id", dest="agent_id", required=True, help="Agent ID to deploy"
    )
    deploy_parser.add_argument(
        "--tier",
        choices=["project", "user"],
        default="user",
        help="Deployment tier (default: user)",
    )
    deploy_parser.add_argument(
        "--force", action="store_true", help="Force deployment even if agent exists"
    )
    deploy_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    # Customize PM command
    pm_parser = agent_subparsers.add_parser(
        "customize-pm", help="Customize PM instructions via .claude-mpm/INSTRUCTIONS.md"
    )
    pm_parser.add_argument(
        "--level",
        choices=["user", "project"],
        default="user",
        help="PM instruction level - user (~/.claude-mpm) or project (./.claude-mpm) (default: user)",
    )
    pm_parser.add_argument("--template", help="Use predefined PM template")
    pm_parser.add_argument("--patterns", nargs="+", help="Custom delegation patterns")
    pm_parser.add_argument("--rules", nargs="+", help="Additional PM rules")
    pm_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    # Show command
    show_parser = agent_subparsers.add_parser(
        "show", help="Display detailed agent information"
    )
    show_parser.add_argument(
        "--id", dest="agent_id", required=True, help="Agent ID to show"
    )
    show_parser.add_argument(
        "--format",
        choices=["text", "json", "yaml"],
        default="text",
        help="Output format (default: text)",
    )

    # Test command
    test_parser = agent_subparsers.add_parser(
        "test", help="Test and validate agent configuration"
    )
    test_parser.add_argument(
        "--id", dest="agent_id", required=True, help="Agent ID to test"
    )
    test_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    # Templates command
    templates_parser = agent_subparsers.add_parser(
        "templates", help="List available agent templates"
    )
    templates_parser.add_argument(
        "--format",
        choices=["text", "json", "yaml"],
        default="text",
        help="Output format (default: text)",
    )

    # Reset command
    reset_parser = agent_subparsers.add_parser(
        "reset", help="Remove claude-mpm authored agents for clean install"
    )
    reset_parser.add_argument(
        "--force",
        action="store_true",
        help="Execute cleanup immediately without confirmation",
    )
    reset_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be removed without making changes",
    )
    reset_parser.add_argument(
        "--project-only",
        action="store_true",
        help="Only clean project-level agents (.claude/agents)",
    )
    reset_parser.add_argument(
        "--user-only",
        action="store_true",
        help="Only clean user-level agents (~/.claude/agents)",
    )
    reset_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    # === Interactive Commands ===

    # Create interactive command
    agent_subparsers.add_parser(
        "create-interactive", help="🧙‍♂️ Launch step-by-step agent creation wizard"
    )

    # Manage local interactive command
    agent_subparsers.add_parser(
        "manage-local", help="🔧 Interactive menu for managing local agents"
    )

    # Edit interactive command
    edit_interactive_parser = agent_subparsers.add_parser(
        "edit-interactive", help="✏️ Edit agent configuration interactively"
    )
    edit_interactive_parser.add_argument(
        "--agent-id", required=True, help="Agent ID to edit"
    )

    # Test local command
    test_local_parser = agent_subparsers.add_parser(
        "test-local", help="🧪 Test local agent with validation and deployment"
    )
    test_local_parser.add_argument("--agent-id", required=True, help="Agent ID to test")

    # === Local Agent Commands ===

    # Create local command
    create_local_parser = agent_subparsers.add_parser(
        "create-local", help="Create a local JSON agent template"
    )
    create_local_parser.add_argument(
        "--agent-id", required=True, help="Unique agent identifier"
    )
    create_local_parser.add_argument("--name", help="Human-readable agent name")
    create_local_parser.add_argument("--description", help="Agent description")
    create_local_parser.add_argument("--instructions", help="Agent instructions")
    create_local_parser.add_argument(
        "--model",
        choices=["sonnet", "opus", "haiku"],
        default="sonnet",
        help="Model to use (default: sonnet)",
    )
    create_local_parser.add_argument(
        "--tools", help="Tools available to agent (default: *)"
    )
    create_local_parser.add_argument("--parent", help="Parent agent to inherit from")
    create_local_parser.add_argument(
        "--tier",
        choices=["project", "user"],
        default="project",
        help="Tier level (default: project)",
    )

    # Deploy local command
    deploy_local_parser = agent_subparsers.add_parser(
        "deploy-local", help="Deploy local JSON templates to Claude Code"
    )
    deploy_local_parser.add_argument(
        "--agent-id", help="Specific agent to deploy (deploy all if not specified)"
    )
    deploy_local_parser.add_argument(
        "--force", action="store_true", help="Force deployment even if file exists"
    )
    deploy_local_parser.add_argument(
        "--tier", choices=["project", "user"], help="Filter by tier for bulk deployment"
    )

    # List local command
    list_local_parser = agent_subparsers.add_parser(
        "list-local", help="List all local agent templates"
    )
    list_local_parser.add_argument(
        "--tier", choices=["project", "user"], help="Filter by tier"
    )
    list_local_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    # Sync local command
    agent_subparsers.add_parser(
        "sync-local", help="Synchronize local templates with deployed agents"
    )

    # Export local command
    export_local_parser = agent_subparsers.add_parser(
        "export-local", help="Export local templates to a directory"
    )
    export_local_parser.add_argument(
        "--output",
        default="./exported-agents",
        help="Output directory (default: ./exported-agents)",
    )

    # Import local command
    import_local_parser = agent_subparsers.add_parser(
        "import-local", help="Import templates from a directory"
    )
    import_local_parser.add_argument(
        "--input", required=True, help="Input directory containing templates"
    )
    import_local_parser.add_argument(
        "--tier",
        choices=["project", "user"],
        default="project",
        help="Tier to import into (default: project)",
    )

    # Delete local command
    delete_local_parser = agent_subparsers.add_parser(
        "delete-local", help="Delete local agent templates with safety checks"
    )
    delete_local_parser.add_argument(
        "--agent-id",
        nargs="+",
        dest="agent_id",
        help="Agent ID(s) to delete (space-separated for multiple)",
    )
    delete_local_parser.add_argument(
        "--all",
        action="store_true",
        help="Delete all local agents (requires confirmation)",
    )
    delete_local_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Skip confirmation prompts",
    )
    delete_local_parser.add_argument(
        "--keep-deployment",
        action="store_true",
        help="Keep Claude Code deployment, only delete template",
    )
    delete_local_parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup before deletion",
    )
    delete_local_parser.add_argument(
        "--tier",
        choices=["project", "user", "all"],
        default="project",
        help="Tier to delete from (default: project)",
    )
