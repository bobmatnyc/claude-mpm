"""
Info command implementation for claude-mpm.

WHY: This module provides system information and configuration details to help
users understand their claude-mpm setup and troubleshoot issues.

DESIGN DECISIONS:
- Use BaseCommand for consistent CLI patterns
- Leverage shared utilities for argument parsing and output formatting
- Support multiple output formats (json, yaml, table, text)
- Provide comprehensive system information for troubleshooting
"""

import importlib.util
import shutil
from pathlib import Path
from typing import Any, Dict

from ..shared import BaseCommand, CommandResult


class InfoCommand(BaseCommand):
    """Information display command using shared utilities."""

    def __init__(self):
        super().__init__("info")

    def validate_args(self, args) -> str:
        """Validate command arguments."""
        # Info command doesn't require specific validation
        return None

    def run(self, args) -> CommandResult:
        """Execute the info command."""
        try:
            # Gather system information
            info_data = self._gather_system_info(args)

            output_format = getattr(args, "format", "text")

            if output_format in ["json", "yaml"]:
                # Structured output
                return CommandResult.success_result(
                    "System information retrieved", data=info_data
                )
            # Text output
            self._display_text_info(info_data)
            return CommandResult.success_result("System information displayed")

        except Exception as e:
            self.logger.error(f"Error gathering system info: {e}", exc_info=True)
            return CommandResult.error_result(f"Error gathering system info: {e}")

    def _gather_system_info(self, args) -> Dict[str, Any]:
        """Gather comprehensive system information."""
        try:
            from ...core.framework_loader import FrameworkLoader
        except ImportError:
            from claude_mpm.core.framework_loader import FrameworkLoader

        # Framework information
        framework_path = getattr(args, "framework_path", None)
        loader = FrameworkLoader(framework_path)

        framework_info = {
            "loaded": loader.framework_content["loaded"],
            "name": (
                "claude-multiagent-pm"
                if loader.framework_content["loaded"]
                else "Not found"
            ),
            "version": loader.framework_content.get("version", "unknown"),
            "path": str(loader.framework_path) if loader.framework_path else None,
            "agents": (
                loader.get_agent_list() if loader.framework_content["loaded"] else []
            ),
        }

        # Configuration information
        config_info = {
            "log_directory": getattr(args, "log_dir", None) or "~/.claude-mpm/logs"
        }

        # Agent hierarchy
        agent_hierarchy = {}
        core_agents = []
        if loader.agent_registry:
            hierarchy = loader.agent_registry.get_agent_hierarchy()
            agent_hierarchy = {
                "project_agents": len(hierarchy["project"]),
                "user_agents": len(hierarchy["user"]),
                "system_agents": len(hierarchy["system"]),
                "project_agent_list": hierarchy["project"],
                "user_agent_list": hierarchy["user"],
                "system_agent_list": hierarchy["system"],
            }
            core_agents = loader.agent_registry.get_core_agents()

        # Dependencies check
        dependencies = self._check_dependencies()

        return {
            "framework": framework_info,
            "configuration": config_info,
            "agent_hierarchy": agent_hierarchy,
            "core_agents": core_agents,
            "dependencies": dependencies,
        }

    def _check_dependencies(self) -> Dict[str, Any]:
        """Check system dependencies."""
        dependencies = {}

        # Check Claude CLI
        claude_path = shutil.which("claude")
        dependencies["claude_cli"] = {
            "installed": bool(claude_path),
            "path": claude_path,
            "status": "✓ Installed" if claude_path else "✗ Not found in PATH",
        }

        # Check ai-trackdown-pytools
        if importlib.util.find_spec("ai_trackdown_pytools") is not None:
            dependencies["ai_trackdown_pytools"] = {
                "installed": True,
                "status": "✓ Installed",
            }
        else:
            dependencies["ai_trackdown_pytools"] = {
                "installed": False,
                "status": "✗ Not installed",
            }

        # Check Claude Code hooks
        claude_settings = Path.home() / ".claude" / "settings.json"
        dependencies["claude_code_hooks"] = {
            "installed": claude_settings.exists(),
            "settings_path": str(claude_settings),
            "status": "✓ Installed" if claude_settings.exists() else "✗ Not installed",
            "install_command": (
                "python scripts/install_hooks.py"
                if not claude_settings.exists()
                else None
            ),
        }

        return dependencies

    def _display_text_info(self, info_data: Dict[str, Any]) -> None:
        """Display information in text format."""
        print("Claude MPM - Multi-Agent Project Manager")
        print("=" * 50)

        # Framework info
        framework = info_data["framework"]
        print(f"Framework: {framework['name']}")
        if framework["loaded"]:
            print(f"Version: {framework['version']}")
            print(f"Path: {framework['path']}")
            print(f"Agents: {', '.join(framework['agents'])}")

        print()

        # Configuration
        config = info_data["configuration"]
        print("Configuration:")
        print(f"  Log directory: {config['log_directory']}")

        # Agent hierarchy
        hierarchy = info_data["agent_hierarchy"]
        if hierarchy:
            print("\nAgent Hierarchy:")
            print(f"  Project agents: {hierarchy['project_agents']}")
            print(f"  User agents: {hierarchy['user_agents']}")
            print(f"  System agents: {hierarchy['system_agents']}")

        # Core agents
        core_agents = info_data["core_agents"]
        if core_agents:
            print(f"\nCore Agents: {', '.join(core_agents)}")

        # Dependencies
        print("\nDependencies:")
        deps = info_data["dependencies"]

        for dep_name, dep_info in deps.items():
            print(f"  {dep_info['status']}")
            if dep_name == "claude_cli" and dep_info["path"]:
                print(f"    Path: {dep_info['path']}")
            elif dep_name == "claude_code_hooks":
                if dep_info["installed"]:
                    print("     Use /mpm commands in Claude Code")
                else:
                    print(f"     Run: {dep_info['install_command']}")


def show_info(args):
    """
    Main entry point for info command.

    This function maintains backward compatibility while using the new BaseCommand pattern.
    """
    command = InfoCommand()
    result = command.execute(args)

    # Print result if structured output format is requested
    if hasattr(args, "format") and args.format in ["json", "yaml"]:
        command.print_result(result, args)

    return result.exit_code
