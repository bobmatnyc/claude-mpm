"""CLI command to clean up orphaned agents without templates.

This command helps manage deployed agents that no longer have corresponding
templates, which can happen when agents are removed from the system or when
switching between different agent sources.
"""

import argparse
from pathlib import Path
from typing import Optional

from claude_mpm.core.logging_config import get_logger
from claude_mpm.services.agents.deployment.multi_source_deployment_service import (
    MultiSourceAgentDeploymentService,
)


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the cleanup-orphaned-agents command parser.

    Args:
        subparsers: The subparsers object from argparse
    """
    parser = subparsers.add_parser(
        "cleanup-orphaned-agents",
        help="Clean up orphaned agents that don't have templates",
        description=(
            "Detect and optionally remove deployed agents that no longer have "
            "corresponding templates. This can happen when agents are removed "
            "from the system or when switching between agent sources."
        ),
    )

    parser.add_argument(
        "--agents-dir",
        type=Path,
        help="Directory containing deployed agents (default: .claude/agents/)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Only show what would be removed without actually removing (default)",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Actually remove orphaned agents (disables dry-run)",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only show summary, not individual agents",
    )

    parser.set_defaults(func=cleanup_orphaned_agents)


def cleanup_orphaned_agents(args: argparse.Namespace) -> int:
    """Clean up orphaned agents.

    Args:
        args: Command line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    logger = get_logger(__name__)

    # Determine agents directory
    if args.agents_dir:
        agents_dir = args.agents_dir
    else:
        # Check for project-level .claude/agents first
        project_agents_dir = Path.cwd() / ".claude" / "agents"
        if project_agents_dir.exists():
            agents_dir = project_agents_dir
        else:
            # Fall back to user home directory
            agents_dir = Path.home() / ".claude" / "agents"

    if not agents_dir.exists():
        logger.info(f"Agents directory not found: {agents_dir}")
        return 0

    logger.info(f"Checking for orphaned agents in: {agents_dir}")

    # Initialize service
    service = MultiSourceAgentDeploymentService()

    # Determine if we're doing a dry run
    dry_run = args.dry_run and not args.force

    try:
        # Perform cleanup
        results = service.cleanup_orphaned_agents(agents_dir, dry_run=dry_run)

        # Handle results
        if not results["orphaned"]:
            logger.info("✅ No orphaned agents found")
            return 0

        if not args.quiet:
            logger.info(f"\nFound {len(results['orphaned'])} orphaned agent(s):")
            for orphan in results["orphaned"]:
                logger.info(f"  - {orphan['name']} v{orphan['version']}")

        if dry_run:
            logger.info(
                f"\n📝 This was a dry run. Use --force to actually remove "
                f"{len(results['orphaned'])} orphaned agent(s)"
            )
        else:
            if results["removed"]:
                logger.info(
                    f"\n✅ Successfully removed {len(results['removed'])} orphaned agent(s)"
                )

            if results["errors"]:
                logger.error(f"\n❌ Encountered {len(results['errors'])} error(s):")
                for error in results["errors"]:
                    logger.error(f"  - {error}")
                return 1

        return 0

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return 1


# For backward compatibility
def main(args: Optional[argparse.Namespace] = None) -> int:
    """Main entry point for the command.

    Args:
        args: Command line arguments

    Returns:
        Exit code
    """
    if args is None:
        parser = argparse.ArgumentParser()
        add_parser(parser.add_subparsers())
        args = parser.parse_args()

    return cleanup_orphaned_agents(args)
