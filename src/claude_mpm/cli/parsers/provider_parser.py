"""Parser for the provider command.

WHY: The provider command allows users to switch between Bedrock and Anthropic
API backends from the CLI.
"""

import argparse


def add_provider_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Add the provider subparser for API backend management.

    Args:
        subparsers: The subparsers action from the main parser.
    """
    provider_parser = subparsers.add_parser(
        "provider",
        help="Manage API provider configuration (Bedrock/Anthropic)",
        description=(
            "Switch between AWS Bedrock and Anthropic API backends for Claude Code. "
            "Configuration is stored in .claude-mpm/configuration.yaml."
        ),
    )

    # Create subcommands for provider
    provider_subparsers = provider_parser.add_subparsers(
        dest="provider_command",
        help="Provider subcommand",
        metavar="SUBCOMMAND",
    )

    # bedrock subcommand
    bedrock_parser = provider_subparsers.add_parser(
        "bedrock",
        help="Switch to AWS Bedrock backend",
        description="Configure Claude Code to use AWS Bedrock for API calls.",
    )
    bedrock_parser.add_argument(
        "--region",
        type=str,
        help="AWS region (default: us-east-1)",
    )
    bedrock_parser.add_argument(
        "--model",
        type=str,
        help="Bedrock model ID (default: us.anthropic.claude-opus-4-5-20251101-v1:0)",
    )

    # anthropic subcommand
    anthropic_parser = provider_subparsers.add_parser(
        "anthropic",
        help="Switch to Anthropic API backend",
        description="Configure Claude Code to use Anthropic's API directly.",
    )
    anthropic_parser.add_argument(
        "--model",
        type=str,
        help="Anthropic model ID (default: claude-sonnet-4-20250514)",
    )

    # status subcommand
    provider_subparsers.add_parser(
        "status",
        help="Show current API provider configuration",
        description="Display the currently configured API backend and settings.",
    )

    # Default to status if no subcommand specified
    provider_parser.set_defaults(command="provider", provider_command=None)
