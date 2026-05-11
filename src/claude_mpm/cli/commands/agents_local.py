"""
Local agent CRUD handler for agents command.

WHY: Extracted from agents.py to keep the main command file focused on routing.
This handler manages local agent template create/edit/delete and the
deprecated manage command redirect.
"""

from __future__ import annotations

import subprocess  # nosec B404
from typing import TYPE_CHECKING

from ..shared import CommandResult

if TYPE_CHECKING:
    from .agents import AgentsCommand


class AgentLocalHandler:
    """Handles local agent CRUD commands."""

    def __init__(self, cmd: AgentsCommand) -> None:
        self.cmd = cmd

    @property
    def _logger(self):
        return self.cmd.logger

    def create_local_agent(self, args) -> CommandResult:
        """Create a new local agent template."""
        try:
            if getattr(args, "interactive", False):
                # Launch interactive wizard
                from ..interactive.agent_wizard import run_interactive_agent_wizard

                exit_code = run_interactive_agent_wizard()
                if exit_code == 0:
                    return CommandResult.success_result("Agent created successfully")
                return CommandResult.error_result("Agent creation cancelled or failed")

            # Non-interactive creation
            from ...services.agents.local_template_manager import (
                LocalAgentTemplateManager,
            )

            agent_id = getattr(args, "agent_id", None)
            if not agent_id:
                return CommandResult.error_result(
                    "--agent-id is required for non-interactive creation"
                )

            manager = LocalAgentTemplateManager()
            name = getattr(args, "name", agent_id.replace("-", " ").title())
            model = getattr(args, "model", "sonnet")
            inherit_from = getattr(args, "inherit_from", None)

            # Create basic template
            template = manager.create_local_template(
                agent_id=agent_id,
                name=name,
                description=f"Local agent: {name}",
                instructions="# Agent Instructions\n\nCustomize this agent's behavior here.",
                model=model,
                parent_agent=inherit_from,
                tier="project",
            )

            if template:
                return CommandResult.success_result(
                    f"Created local agent '{agent_id}' in .claude-mpm/agents/",
                    data={
                        "agent_id": agent_id,
                        "path": f".claude-mpm/agents/{agent_id}.json",
                    },
                )
            return CommandResult.error_result("Failed to create agent template")

        except Exception as e:
            self._logger.error(f"Error creating local agent: {e}", exc_info=True)
            return CommandResult.error_result(f"Error creating local agent: {e}")

    def edit_local_agent(self, args) -> CommandResult:
        """Edit a local agent template."""
        try:
            agent_id = getattr(args, "agent_id", None)
            if not agent_id:
                return CommandResult.error_result("agent_id is required")

            import os

            from ...services.agents.local_template_manager import (
                LocalAgentTemplateManager,
            )

            manager = LocalAgentTemplateManager()
            template = manager.get_local_template(agent_id)

            if not template:
                return CommandResult.error_result(f"Local agent '{agent_id}' not found")

            # Get template file path
            template_file = None
            if template.tier == "project":
                template_file = manager.project_agents_dir / f"{agent_id}.json"
            else:
                template_file = manager.user_agents_dir / f"{agent_id}.json"

            if not template_file or not template_file.exists():
                return CommandResult.error_result(
                    f"Template file not found for '{agent_id}'"
                )

            if getattr(args, "interactive", False):
                # Launch interactive editor
                from ..interactive.agent_wizard import AgentWizard

                wizard = AgentWizard()
                success, message = wizard._edit_agent_config(template)
                if success:
                    return CommandResult.success_result(message)
                return CommandResult.error_result(message)

            # Use system editor
            editor = getattr(args, "editor", None) or os.environ.get("EDITOR", "nano")
            subprocess.run([editor, str(template_file)], check=True)  # nosec B603
            return CommandResult.success_result(
                f"Agent '{agent_id}' edited successfully"
            )

        except subprocess.CalledProcessError:
            return CommandResult.error_result("Editor exited with error")
        except Exception as e:
            self._logger.error(f"Error editing local agent: {e}", exc_info=True)
            return CommandResult.error_result(f"Error editing local agent: {e}")

    def delete_local_agent(self, args) -> CommandResult:
        """Delete local agent templates."""
        try:
            agent_ids = getattr(args, "agent_ids", [])
            if not agent_ids:
                return CommandResult.error_result("No agent IDs specified")

            from ...services.agents.local_template_manager import (
                LocalAgentTemplateManager,
            )

            manager = LocalAgentTemplateManager()
            force = getattr(args, "force", False)
            keep_deployment = getattr(args, "keep_deployment", False)
            backup = getattr(args, "backup", False)

            # Confirmation if not forced
            if not force:
                print(f"\n⚠️  This will delete {len(agent_ids)} agent(s):")
                for agent_id in agent_ids:
                    print(f"  - {agent_id}")
                confirm = input("\nAre you sure? [y/N]: ").strip().lower()
                if confirm not in ["y", "yes"]:
                    return CommandResult.error_result("Deletion cancelled")

            # Delete agents
            if len(agent_ids) == 1:
                result = manager.delete_local_template(
                    agent_id=agent_ids[0],
                    tier="all",
                    delete_deployment=not keep_deployment,
                    backup_first=backup,
                )
                if result["success"]:
                    message = f"Successfully deleted agent '{agent_ids[0]}'"
                    if result["backup_location"]:
                        message += f"\nBackup saved to: {result['backup_location']}"
                    return CommandResult.success_result(message, data=result)
                return CommandResult.error_result(
                    f"Failed to delete agent: {', '.join(result['errors'])}"
                )
            results = manager.delete_multiple_templates(
                agent_ids=agent_ids,
                tier="all",
                delete_deployment=not keep_deployment,
                backup_first=backup,
            )

            message = ""
            if results["successful"]:
                message = (
                    f"Successfully deleted {len(results['successful'])} agent(s):\n"
                )
                for agent_id in results["successful"]:
                    message += f"  - {agent_id}\n"

            if results["failed"]:
                if message:
                    message += "\n"
                message += f"Failed to delete {len(results['failed'])} agent(s):\n"
                for agent_id in results["failed"]:
                    errors = results["details"][agent_id]["errors"]
                    message += f"  - {agent_id}: {', '.join(errors)}\n"

            if results["successful"]:
                return CommandResult.success_result(message.strip(), data=results)
            return CommandResult.error_result(message.strip(), data=results)

        except Exception as e:
            self._logger.error(f"Error deleting local agents: {e}", exc_info=True)
            return CommandResult.error_result(f"Error deleting local agents: {e}")

    def manage_local_agents(self, args) -> CommandResult:
        """Redirect to main configuration interface (DEPRECATED)."""
        try:
            from rich.console import Console
            from rich.prompt import Confirm

            console = Console()

            console.print(
                "\n[bold cyan]╭─────────────────────────────────────────╮[/bold cyan]"
            )
            console.print(
                "[bold cyan]│  Agent Management Has Moved!            │[/bold cyan]"
            )
            console.print(
                "[bold cyan]╰─────────────────────────────────────────╯[/bold cyan]\n"
            )

            console.print("For a better experience with integrated configuration:")
            console.print("  • Agent management")
            console.print("  • Skills management")
            console.print("  • Startup settings\n")

            console.print("Please use: [bold green]claude-mpm config[/bold green]\n")

            if Confirm.ask("Launch configuration interface now?", default=True):
                # Import and run config command directly
                from claude_mpm.cli.commands.configure import ConfigureCommand

                config_cmd = ConfigureCommand()
                return config_cmd.execute(args)
            console.print(
                "\n[dim]Run 'claude-mpm config' anytime to access agent management[/dim]"
            )
            return CommandResult.success_result("Redirected to config interface")

        except Exception as e:
            self._logger.error(f"Error redirecting to config: {e}", exc_info=True)
            return CommandResult.error_result(f"Error redirecting to config: {e}")
