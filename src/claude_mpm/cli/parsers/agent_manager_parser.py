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
Examples:
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
