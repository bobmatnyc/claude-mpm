"""
Skills command parser for claude-mpm CLI.

WHY: This module contains all arguments specific to skills management commands,
providing CLI access to the Skills Integration system.

DESIGN DECISION: Skills commands expose the SkillsService functionality via CLI
for listing, deploying, validating, updating, and configuring Claude Code skills.
"""

import argparse

from ...constants import CLICommands, SkillsCommands
from .base_parser import add_common_arguments


def add_skills_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Add the skills subparser with all skills management commands.

    WHY: Skills management has multiple subcommands for discovery, deployment,
    validation, updates, and configuration that need their own argument structures.

    Args:
        subparsers: The subparsers object from the main parser

    Returns:
        The configured skills subparser
    """
    # Skills command with subcommands
    skills_parser = subparsers.add_parser(
        CLICommands.SKILLS.value, help="Manage Claude Code skills"
    )
    add_common_arguments(skills_parser)

    skills_subparsers = skills_parser.add_subparsers(
        dest="skills_command", help="Skills commands", metavar="SUBCOMMAND"
    )

    # List command
    list_parser = skills_subparsers.add_parser(
        SkillsCommands.LIST.value, help="List available skills"
    )
    list_parser.add_argument(
        "--category",
        help="Filter by category (e.g., development, infrastructure, web-development)",
    )
    list_parser.add_argument(
        "--agent", help="Show skills for specific agent (e.g., engineer, pm)"
    )
    list_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed skill information",
    )

    # Deploy command
    deploy_parser = skills_subparsers.add_parser(
        SkillsCommands.DEPLOY.value, help="Deploy bundled skills to project"
    )
    deploy_parser.add_argument(
        "--force",
        action="store_true",
        help="Force redeployment of already deployed skills",
    )
    deploy_parser.add_argument(
        "--skill",
        action="append",
        dest="skills",
        help="Deploy specific skill(s) only (can be used multiple times)",
    )

    # Validate command
    validate_parser = skills_subparsers.add_parser(
        SkillsCommands.VALIDATE.value, help="Validate skill structure and metadata"
    )
    validate_parser.add_argument("skill_name", help="Name of the skill to validate")
    validate_parser.add_argument(
        "--strict",
        action="store_true",
        help="Use strict validation (treat warnings as errors)",
    )

    # Update command
    update_parser = skills_subparsers.add_parser(
        SkillsCommands.UPDATE.value, help="Check for and install skill updates"
    )
    update_parser.add_argument(
        "skill_names",
        nargs="*",
        help="Specific skills to update (default: all)",
    )
    update_parser.add_argument(
        "--check-only",
        action="store_true",
        help="Check for updates without installing them",
    )
    update_parser.add_argument(
        "--force",
        action="store_true",
        help="Force update even if versions match",
    )

    # Info command
    info_parser = skills_subparsers.add_parser(
        SkillsCommands.INFO.value, help="Show detailed skill information"
    )
    info_parser.add_argument("skill_name", help="Name of the skill")
    info_parser.add_argument(
        "--show-content",
        action="store_true",
        help="Show full skill content (SKILL.md)",
    )

    # Config command
    config_parser = skills_subparsers.add_parser(
        SkillsCommands.CONFIG.value, help="View or edit skills configuration"
    )
    config_parser.add_argument(
        "--scope",
        choices=["system", "user", "project"],
        default="project",
        help="Configuration scope (default: project)",
    )
    config_parser.add_argument(
        "--edit",
        action="store_true",
        help="Open configuration in $EDITOR",
    )
    config_parser.add_argument(
        "--path",
        action="store_true",
        help="Show configuration file path",
    )

    # Configure command (interactive skills selection)
    skills_subparsers.add_parser(
        SkillsCommands.CONFIGURE.value,
        help="Interactive skills configuration with checkbox selection (like agents configure)",
    )
    # No additional arguments needed - purely interactive

    # GitHub deployment commands
    # Deploy from GitHub command
    deploy_github_parser = skills_subparsers.add_parser(
        SkillsCommands.DEPLOY_FROM_GITHUB.value,
        help="Deploy skills from GitHub to ~/.claude/skills/ for Claude Code",
    )
    deploy_github_parser.add_argument(
        "--collection",
        "-c",
        help="Collection to deploy from (default: uses default collection)",
    )
    deploy_github_parser.add_argument(
        "--toolchain",
        nargs="+",
        help="Filter by toolchain/language (e.g., python javascript rust)",
    )
    deploy_github_parser.add_argument(
        "--categories",
        nargs="+",
        help="Filter by categories (e.g., testing debugging web)",
    )
    deploy_github_parser.add_argument(
        "--force",
        action="store_true",
        help="Force redeployment of already deployed skills",
    )

    # List available GitHub skills
    list_available_parser = skills_subparsers.add_parser(
        SkillsCommands.LIST_AVAILABLE.value,
        help="List all available skills from GitHub repository",
    )
    list_available_parser.add_argument(
        "--collection",
        "-c",
        help="Collection to list from (default: uses default collection)",
    )
    list_available_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed skill information including names",
    )

    # Check deployed skills
    skills_subparsers.add_parser(
        SkillsCommands.CHECK_DEPLOYED.value,
        help="Check which skills are currently deployed in ~/.claude/skills/",
    )

    # Remove skills
    remove_parser = skills_subparsers.add_parser(
        SkillsCommands.REMOVE.value,
        help="Remove deployed skills from ~/.claude/skills/",
    )
    remove_parser.add_argument(
        "skill_names",
        nargs="*",
        help="Specific skills to remove",
    )
    remove_parser.add_argument(
        "--all",
        action="store_true",
        help="Remove all deployed skills",
    )

    # Collection management commands
    # List collections
    skills_subparsers.add_parser(
        SkillsCommands.COLLECTION_LIST.value,
        help="List all configured skill collections",
    )

    # Add collection
    collection_add_parser = skills_subparsers.add_parser(
        SkillsCommands.COLLECTION_ADD.value,
        help="Add a new skill collection from GitHub",
    )
    collection_add_parser.add_argument(
        "collection_name",
        help="Name for the collection (e.g., obra-superpowers)",
    )
    collection_add_parser.add_argument(
        "collection_url",
        help="GitHub repository URL (e.g., https://github.com/obra/superpowers)",
    )
    collection_add_parser.add_argument(
        "--priority",
        type=int,
        default=99,
        help="Collection priority (lower = higher priority, default: 99)",
    )

    # Remove collection
    collection_remove_parser = skills_subparsers.add_parser(
        SkillsCommands.COLLECTION_REMOVE.value,
        help="Remove a skill collection",
    )
    collection_remove_parser.add_argument(
        "collection_name",
        help="Name of the collection to remove",
    )

    # Enable collection
    collection_enable_parser = skills_subparsers.add_parser(
        SkillsCommands.COLLECTION_ENABLE.value,
        help="Enable a disabled collection",
    )
    collection_enable_parser.add_argument(
        "collection_name",
        help="Name of the collection to enable",
    )

    # Disable collection
    collection_disable_parser = skills_subparsers.add_parser(
        SkillsCommands.COLLECTION_DISABLE.value,
        help="Disable a collection without removing it",
    )
    collection_disable_parser.add_argument(
        "collection_name",
        help="Name of the collection to disable",
    )

    # Set default collection
    collection_set_default_parser = skills_subparsers.add_parser(
        SkillsCommands.COLLECTION_SET_DEFAULT.value,
        help="Set the default collection for deployments",
    )
    collection_set_default_parser.add_argument(
        "collection_name",
        help="Name of the collection to set as default",
    )

    return skills_parser
