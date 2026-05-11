"""
Non-interactive and direct-navigation handlers for the configure command.

WHY: Extracted from configure.py to keep the main command file focused on
routing. This handler covers:

- Non-interactive agent list/enable/disable (used by ``--list-agents``,
  ``--enable-agent``, ``--disable-agent`` flags for scripting).
- Direct-navigation entry points (``--agents``, ``--templates``,
  ``--startup``) that jump straight to a sub-flow and return a CommandResult.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ..shared import CommandResult

if TYPE_CHECKING:
    from .configure import ConfigureCommand


class NonInteractiveHandler:
    """Handles non-interactive and direct-navigation commands."""

    def __init__(self, cmd: ConfigureCommand) -> None:
        self.cmd = cmd

    # ------------------------------------------------------------------
    # Non-interactive agent operations
    # ------------------------------------------------------------------

    def list_agents_non_interactive(self) -> CommandResult:
        """List agents in non-interactive mode."""
        if self.cmd.agent_manager is None:
            return CommandResult.error_result("Agent manager not initialized")
        agents = self.cmd.agent_manager.discover_agents()
        # Filter BASE_AGENT from all agent lists (1M-502 Phase 1)
        agents = self.cmd._filter_agent_configs(agents, filter_deployed=False)

        data = []
        for agent in agents:
            data.append(
                {
                    "name": agent.name,
                    "enabled": self.cmd.agent_manager.is_agent_enabled(agent.name),
                    "description": agent.description,
                    "dependencies": agent.dependencies,
                }
            )

        # Print as JSON for scripting
        print(json.dumps(data, indent=2))

        return CommandResult.success_result("Agents listed", data={"agents": data})

    def enable_agent_non_interactive(self, agent_name: str) -> CommandResult:
        """Enable an agent in non-interactive mode."""
        if self.cmd.agent_manager is None:
            return CommandResult.error_result("Agent manager not initialized")
        try:
            self.cmd.agent_manager.set_agent_enabled(agent_name, True)
            return CommandResult.success_result(f"Agent '{agent_name}' enabled")
        except Exception as e:
            return CommandResult.error_result(f"Failed to enable agent: {e}")

    def disable_agent_non_interactive(self, agent_name: str) -> CommandResult:
        """Disable an agent in non-interactive mode."""
        if self.cmd.agent_manager is None:
            return CommandResult.error_result("Agent manager not initialized")
        try:
            self.cmd.agent_manager.set_agent_enabled(agent_name, False)
            return CommandResult.success_result(f"Agent '{agent_name}' disabled")
        except Exception as e:
            return CommandResult.error_result(f"Failed to disable agent: {e}")

    # ------------------------------------------------------------------
    # Direct-navigation entry points
    # ------------------------------------------------------------------

    def run_agent_management(self) -> CommandResult:
        """Jump directly to agent management."""
        try:
            self.cmd._manage_agents()
            return CommandResult.success_result("Agent management completed")
        except KeyboardInterrupt:
            return CommandResult.success_result("Agent management cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Agent management failed: {e}")

    def run_template_editing(self) -> CommandResult:
        """Jump directly to template editing."""
        try:
            self.cmd._edit_templates()
            return CommandResult.success_result("Template editing completed")
        except KeyboardInterrupt:
            return CommandResult.success_result("Template editing cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Template editing failed: {e}")

    def run_startup_configuration(self) -> CommandResult:
        """Jump directly to startup configuration."""
        try:
            proceed = self.cmd._manage_startup_configuration()
            if proceed:
                return CommandResult.success_result(
                    "Startup configuration saved, proceeding to startup"
                )
            return CommandResult.success_result("Startup configuration completed")
        except KeyboardInterrupt:
            return CommandResult.success_result("Startup configuration cancelled")
        except Exception as e:
            return CommandResult.error_result(f"Startup configuration failed: {e}")
