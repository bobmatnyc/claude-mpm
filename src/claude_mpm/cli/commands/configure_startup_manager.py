"""Startup configuration and service management for configure command.

This module handles all startup-related configuration including:
- Hook service configuration
- MCP service configuration
- System agent configuration
- Background service orchestration
- Startup configuration persistence

WHY: Startup configuration requires orchestrating multiple services (MCP, hooks, agents)
and needs a dedicated manager to handle the complexity of service dependencies and
configuration persistence.

DESIGN DECISIONS:
- Separate startup concerns from main configure command
- Use Config system for persistence
- Integrate with MCPConfigManager for service discovery
- Support interactive and batch operations
- Handle disabled_agents list (NEW LOGIC: track disabled, not enabled)
"""

import logging
import os
from pathlib import Path
from typing import Dict

from rich.box import ROUNDED
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from ...core.config import Config
from ...services.mcp_config_manager import MCPConfigManager
from .agent_state_manager import SimpleAgentManager
from .configure_validators import parse_id_selection


class StartupManager:
    """Manage startup configuration and background services.

    This manager handles:
    - Loading and saving startup configuration
    - Configuring hook services (enable/disable)
    - Configuring MCP services (enable/disable)
    - Configuring system agents
    - Managing all background services
    - Interactive startup configuration interface
    """

    def __init__(
        self,
        agent_manager: SimpleAgentManager,
        console: Console,
        current_scope: str,
        project_dir: Path,
        display_header_callback: callable,
    ):
        """Initialize startup manager.

        Args:
            agent_manager: Agent state manager for agent discovery/management
            console: Rich console for output
            current_scope: Configuration scope ('project' or 'user')
            project_dir: Path to project directory
            display_header_callback: Callback to display header in interactive mode
        """
        self.agent_manager = agent_manager
        self.console = console
        self.current_scope = current_scope
        self.project_dir = project_dir
        self.display_header = display_header_callback

    def manage_startup_configuration(self) -> bool:
        """Manage startup configuration for MCP services and agents.

        Returns:
            bool: True if user saved and wants to proceed to startup, False otherwise
        """
        # Temporarily suppress INFO logging during Config initialization
        root_logger = logging.getLogger("claude_mpm")
        original_level = root_logger.level
        root_logger.setLevel(logging.WARNING)

        try:
            # Load current configuration ONCE at the start
            config = Config()
            startup_config = self.load_startup_configuration(config)
        finally:
            # Restore original logging level
            root_logger.setLevel(original_level)

        proceed_to_startup = False
        while True:
            self.console.clear()
            self.display_header()

            self.console.print("[bold]Startup Configuration Management[/bold]\n")
            self.console.print(
                "[dim]Configure which MCP services, hook services, and system agents "
                "are enabled when Claude MPM starts.[/dim]\n"
            )

            # Display current configuration (using in-memory state)
            self.display_startup_configuration(startup_config)

            # Show menu options
            self.console.print("\n[bold]Options:[/bold]")
            self.console.print("  [cyan]1[/cyan] - Configure MCP Services")
            self.console.print("  [cyan]2[/cyan] - Configure Hook Services")
            self.console.print("  [cyan]3[/cyan] - Configure System Agents")
            self.console.print("  [cyan]4[/cyan] - Enable All")
            self.console.print("  [cyan]5[/cyan] - Disable All")
            self.console.print("  [cyan]6[/cyan] - Reset to Defaults")
            self.console.print(
                "  [cyan]s[/cyan] - Save configuration and start claude-mpm"
            )
            self.console.print("  [cyan]b[/cyan] - Cancel and return without saving")
            self.console.print()

            choice = Prompt.ask("[bold cyan]Select an option[/bold cyan]", default="s")

            if choice == "b":
                break
            if choice == "1":
                self.configure_mcp_services(startup_config, config)
            elif choice == "2":
                self.configure_hook_services(startup_config, config)
            elif choice == "3":
                self.configure_system_agents(startup_config, config)
            elif choice == "4":
                self.enable_all_services(startup_config, config)
            elif choice == "5":
                self.disable_all_services(startup_config, config)
            elif choice == "6":
                self.reset_to_defaults(startup_config, config)
            elif choice == "s":
                # Save and exit if successful
                if self.save_startup_configuration(startup_config, config):
                    proceed_to_startup = True
                    break
            else:
                self.console.print("[red]Invalid choice.[/red]")
                Prompt.ask("Press Enter to continue")

        return proceed_to_startup

    def load_startup_configuration(self, config: Config) -> Dict:
        """Load current startup configuration from config."""
        startup_config = config.get("startup", {})

        # Ensure all required sections exist
        if "enabled_mcp_services" not in startup_config:
            # Get available MCP services from MCPConfigManager
            mcp_manager = MCPConfigManager()
            available_services = list(mcp_manager.STATIC_MCP_CONFIGS.keys())
            startup_config["enabled_mcp_services"] = available_services.copy()

        if "enabled_hook_services" not in startup_config:
            # Default hook services (health-monitor enabled by default)
            startup_config["enabled_hook_services"] = [
                "monitor",
                "dashboard",
                "response-logger",
                "health-monitor",
            ]

        if "disabled_agents" not in startup_config:
            # NEW LOGIC: Track DISABLED agents instead of enabled
            # By default, NO agents are disabled (all agents enabled)
            startup_config["disabled_agents"] = []

        return startup_config

    def display_startup_configuration(self, startup_config: Dict) -> None:
        """Display current startup configuration in a table."""
        table = Table(
            title="Current Startup Configuration", box=ROUNDED, show_lines=True
        )

        table.add_column("Category", style="bold blue", width=20)
        table.add_column("Enabled Services", style="", width=50)
        table.add_column("Count", style="dim", width=10)

        # MCP Services
        mcp_services = startup_config.get("enabled_mcp_services", [])
        mcp_display = ", ".join(mcp_services[:3]) + (
            "..." if len(mcp_services) > 3 else ""
        )
        table.add_row(
            "MCP Services",
            mcp_display if mcp_services else "[dim]None[/dim]",
            str(len(mcp_services)),
        )

        # Hook Services
        hook_services = startup_config.get("enabled_hook_services", [])
        hook_display = ", ".join(hook_services[:3]) + (
            "..." if len(hook_services) > 3 else ""
        )
        table.add_row(
            "Hook Services",
            hook_display if hook_services else "[dim]None[/dim]",
            str(len(hook_services)),
        )

        # System Agents - show count of ENABLED agents (total - disabled)
        all_agents = self.agent_manager.discover_agents() if self.agent_manager else []
        disabled_agents = startup_config.get("disabled_agents", [])
        enabled_count = len(all_agents) - len(disabled_agents)

        # Show first few enabled agent names
        enabled_names = [a.name for a in all_agents if a.name not in disabled_agents]
        agent_display = ", ".join(enabled_names[:3]) + (
            "..." if len(enabled_names) > 3 else ""
        )
        table.add_row(
            "System Agents",
            agent_display if enabled_names else "[dim]All Disabled[/dim]",
            f"{enabled_count}/{len(all_agents)}",
        )

        self.console.print(table)

    def configure_mcp_services(self, startup_config: Dict, config: Config) -> None:
        """Configure which MCP services to enable at startup."""
        self.console.clear()
        self.display_header()
        self.console.print("[bold]Configure MCP Services[/bold]\n")

        # Get available MCP services
        mcp_manager = MCPConfigManager()
        available_services = list(mcp_manager.STATIC_MCP_CONFIGS.keys())
        enabled_services = set(startup_config.get("enabled_mcp_services", []))

        # Display services with checkboxes
        table = Table(box=ROUNDED, show_lines=True)
        table.add_column("ID", style="dim", width=5)
        table.add_column("Service", style="bold blue", width=25)
        table.add_column("Status", width=15)
        table.add_column("Description", style="", width=45)

        service_descriptions = {
            "kuzu-memory": "Graph-based memory system for agents",
            "mcp-ticketer": "Ticket and issue tracking integration",
            "mcp-browser": "Browser automation and web scraping",
            "mcp-vector-search": "Semantic code search capabilities",
        }

        for idx, service in enumerate(available_services, 1):
            status = (
                "[green]✓ Enabled[/green]"
                if service in enabled_services
                else "[red]✗ Disabled[/red]"
            )
            description = service_descriptions.get(service, "MCP service")
            table.add_row(str(idx), service, status, description)

        self.console.print(table)
        self.console.print("\n[bold]Commands:[/bold]")
        self.console.print("  Enter service IDs to toggle (e.g., '1,3' or '1-4')")

        text_a = Text("  ")
        text_a.append("[a]", style="bold blue")
        text_a.append(" Enable all")
        self.console.print(text_a)

        text_n = Text("  ")
        text_n.append("[n]", style="bold blue")
        text_n.append(" Disable all")
        self.console.print(text_n)

        text_b = Text("  ")
        text_b.append("[b]", style="bold blue")
        text_b.append(" Back to previous menu")
        self.console.print(text_b)

        self.console.print()

        choice = Prompt.ask("[bold cyan]Toggle services[/bold cyan]", default="b")

        if choice == "b":
            return
        if choice == "a":
            startup_config["enabled_mcp_services"] = available_services.copy()
            self.console.print("[green]All MCP services enabled![/green]")
        elif choice == "n":
            startup_config["enabled_mcp_services"] = []
            self.console.print("[green]All MCP services disabled![/green]")
        else:
            # Parse service IDs
            try:
                selected_ids = parse_id_selection(choice, len(available_services))
                for idx in selected_ids:
                    service = available_services[idx - 1]
                    if service in enabled_services:
                        enabled_services.remove(service)
                        self.console.print(f"[red]Disabled {service}[/red]")
                    else:
                        enabled_services.add(service)
                        self.console.print(f"[green]Enabled {service}[/green]")
                startup_config["enabled_mcp_services"] = list(enabled_services)
            except (ValueError, IndexError) as e:
                self.console.print(f"[red]Invalid selection: {e}[/red]")

        Prompt.ask("Press Enter to continue")

    def configure_hook_services(self, startup_config: Dict, config: Config) -> None:
        """Configure which hook services to enable at startup."""
        self.console.clear()
        self.display_header()
        self.console.print("[bold]Configure Hook Services[/bold]\n")

        # Available hook services
        available_services = [
            ("monitor", "Real-time event monitoring server (SocketIO)"),
            ("dashboard", "Web-based dashboard interface"),
            ("response-logger", "Agent response logging"),
            ("health-monitor", "Service health and recovery monitoring"),
        ]

        enabled_services = set(startup_config.get("enabled_hook_services", []))

        # Display services with checkboxes
        table = Table(box=ROUNDED, show_lines=True)
        table.add_column("ID", style="dim", width=5)
        table.add_column("Service", style="bold blue", width=25)
        table.add_column("Status", width=15)
        table.add_column("Description", style="", width=45)

        for idx, (service, description) in enumerate(available_services, 1):
            status = (
                "[green]✓ Enabled[/green]"
                if service in enabled_services
                else "[red]✗ Disabled[/red]"
            )
            table.add_row(str(idx), service, status, description)

        self.console.print(table)
        self.console.print("\n[bold]Commands:[/bold]")
        self.console.print("  Enter service IDs to toggle (e.g., '1,3' or '1-4')")

        text_a = Text("  ")
        text_a.append("[a]", style="bold blue")
        text_a.append(" Enable all")
        self.console.print(text_a)

        text_n = Text("  ")
        text_n.append("[n]", style="bold blue")
        text_n.append(" Disable all")
        self.console.print(text_n)

        text_b = Text("  ")
        text_b.append("[b]", style="bold blue")
        text_b.append(" Back to previous menu")
        self.console.print(text_b)

        self.console.print()

        choice = Prompt.ask("[bold cyan]Toggle services[/bold cyan]", default="b")

        if choice == "b":
            return
        if choice == "a":
            startup_config["enabled_hook_services"] = [s[0] for s in available_services]
            self.console.print("[green]All hook services enabled![/green]")
        elif choice == "n":
            startup_config["enabled_hook_services"] = []
            self.console.print("[green]All hook services disabled![/green]")
        else:
            # Parse service IDs
            try:
                selected_ids = parse_id_selection(choice, len(available_services))
                for idx in selected_ids:
                    service = available_services[idx - 1][0]
                    if service in enabled_services:
                        enabled_services.remove(service)
                        self.console.print(f"[red]Disabled {service}[/red]")
                    else:
                        enabled_services.add(service)
                        self.console.print(f"[green]Enabled {service}[/green]")
                startup_config["enabled_hook_services"] = list(enabled_services)
            except (ValueError, IndexError) as e:
                self.console.print(f"[red]Invalid selection: {e}[/red]")

        Prompt.ask("Press Enter to continue")

    def configure_system_agents(self, startup_config: Dict, config: Config) -> None:
        """Configure which system agents to deploy at startup.

        NEW LOGIC: Uses disabled_agents list. All agents from templates are enabled by default.
        """
        while True:
            self.console.clear()
            self.display_header()
            self.console.print("[bold]Configure System Agents[/bold]\n")
            self.console.print(
                "[dim]All agents discovered from templates are enabled by default. "
                "Mark agents as disabled to prevent deployment.[/dim]\n"
            )

            # Discover available agents from template files
            agents = self.agent_manager.discover_agents()
            disabled_agents = set(startup_config.get("disabled_agents", []))

            # Display agents with checkboxes
            table = Table(box=ROUNDED, show_lines=True)
            table.add_column("ID", style="dim", width=5)
            table.add_column("Agent", style="bold blue", width=25)
            table.add_column("Status", width=15)
            table.add_column("Description", style="bold", width=45)

            for idx, agent in enumerate(agents, 1):
                # Agent is ENABLED if NOT in disabled list
                is_enabled = agent.name not in disabled_agents
                status = (
                    "[green]✓ Enabled[/green]"
                    if is_enabled
                    else "[red]✗ Disabled[/red]"
                )
                # Format description with bright styling
                if len(agent.description) > 42:
                    desc_display = (
                        f"[cyan]{agent.description[:42]}[/cyan][dim]...[/dim]"
                    )
                else:
                    desc_display = f"[cyan]{agent.description}[/cyan]"
                table.add_row(str(idx), agent.name, status, desc_display)

            self.console.print(table)
            self.console.print("\n[bold]Commands:[/bold]")
            self.console.print("  Enter agent IDs to toggle (e.g., '1,3' or '1-4')")
            self.console.print("  [cyan]a[/cyan] - Enable all (clear disabled list)")
            self.console.print("  [cyan]n[/cyan] - Disable all")
            self.console.print("  [cyan]b[/cyan] - Back to previous menu")
            self.console.print()

            choice = Prompt.ask("[bold cyan]Select option[/bold cyan]", default="b")

            if choice == "b":
                return
            if choice == "a":
                # Enable all = empty disabled list
                startup_config["disabled_agents"] = []
                self.console.print("[green]All agents enabled![/green]")
                Prompt.ask("Press Enter to continue")
            elif choice == "n":
                # Disable all = all agents in disabled list
                startup_config["disabled_agents"] = [agent.name for agent in agents]
                self.console.print("[green]All agents disabled![/green]")
                Prompt.ask("Press Enter to continue")
            else:
                # Parse agent IDs
                try:
                    selected_ids = parse_id_selection(choice, len(agents))
                    for idx in selected_ids:
                        agent = agents[idx - 1]
                        if agent.name in disabled_agents:
                            # Currently disabled, enable it (remove from disabled list)
                            disabled_agents.remove(agent.name)
                            self.console.print(f"[green]Enabled {agent.name}[/green]")
                        else:
                            # Currently enabled, disable it (add to disabled list)
                            disabled_agents.add(agent.name)
                            self.console.print(f"[red]Disabled {agent.name}[/red]")
                    startup_config["disabled_agents"] = list(disabled_agents)
                    # Refresh the display to show updated status immediately
                except (ValueError, IndexError) as e:
                    self.console.print(f"[red]Invalid selection: {e}[/red]")
                    Prompt.ask("Press Enter to continue")

    def enable_all_services(self, startup_config: Dict, config: Config) -> None:
        """Enable all services and agents."""
        if Confirm.ask("[yellow]Enable ALL services and agents?[/yellow]"):
            # Enable all MCP services
            mcp_manager = MCPConfigManager()
            startup_config["enabled_mcp_services"] = list(
                mcp_manager.STATIC_MCP_CONFIGS.keys()
            )

            # Enable all hook services
            startup_config["enabled_hook_services"] = [
                "monitor",
                "dashboard",
                "response-logger",
                "health-monitor",
            ]

            # Enable all agents (empty disabled list)
            startup_config["disabled_agents"] = []

            self.console.print("[green]All services and agents enabled![/green]")
            Prompt.ask("Press Enter to continue")

    def disable_all_services(self, startup_config: Dict, config: Config) -> None:
        """Disable all services and agents."""
        if Confirm.ask("[yellow]Disable ALL services and agents?[/yellow]"):
            startup_config["enabled_mcp_services"] = []
            startup_config["enabled_hook_services"] = []
            # Disable all agents = add all to disabled list
            agents = self.agent_manager.discover_agents()
            startup_config["disabled_agents"] = [agent.name for agent in agents]

            self.console.print("[green]All services and agents disabled![/green]")
            self.console.print(
                "[yellow]Note: You may need to enable at least some services for Claude MPM to function properly.[/yellow]"
            )
            Prompt.ask("Press Enter to continue")

    def reset_to_defaults(self, startup_config: Dict, config: Config) -> None:
        """Reset startup configuration to defaults."""
        if Confirm.ask("[yellow]Reset startup configuration to defaults?[/yellow]"):
            # Reset to default values
            mcp_manager = MCPConfigManager()
            startup_config["enabled_mcp_services"] = list(
                mcp_manager.STATIC_MCP_CONFIGS.keys()
            )
            startup_config["enabled_hook_services"] = [
                "monitor",
                "dashboard",
                "response-logger",
                "health-monitor",
            ]
            # Default: All agents enabled (empty disabled list)
            startup_config["disabled_agents"] = []

            self.console.print(
                "[green]Startup configuration reset to defaults![/green]"
            )
            Prompt.ask("Press Enter to continue")

    def save_startup_configuration(self, startup_config: Dict, config: Config) -> bool:
        """Save startup configuration to config file and return whether to proceed to startup.

        Returns:
            bool: True if should proceed to startup, False to continue in menu
        """
        try:
            # Update the startup configuration
            config.set("startup", startup_config)

            # IMPORTANT: Also update agent_deployment.disabled_agents so the deployment
            # system actually uses the configured disabled agents list
            config.set(
                "agent_deployment.disabled_agents",
                startup_config.get("disabled_agents", []),
            )

            # Determine config file path
            if self.current_scope == "project":
                config_file = self.project_dir / ".claude-mpm" / "configuration.yaml"
            else:
                config_file = Path.home() / ".claude-mpm" / "configuration.yaml"

            # Ensure directory exists
            config_file.parent.mkdir(parents=True, exist_ok=True)

            # Temporarily suppress INFO logging to avoid duplicate save messages
            root_logger = logging.getLogger("claude_mpm")
            original_level = root_logger.level
            root_logger.setLevel(logging.WARNING)

            try:
                # Save configuration (this will log at INFO level which we've suppressed)
                config.save(config_file, format="yaml")
            finally:
                # Restore original logging level
                root_logger.setLevel(original_level)

            self.console.print(
                f"[green]✓ Startup configuration saved to {config_file}[/green]"
            )
            self.console.print(
                "\n[cyan]Applying configuration and launching Claude MPM...[/cyan]\n"
            )

            # Launch claude-mpm run command to get full startup cycle
            # This ensures:
            # 1. Configuration is loaded
            # 2. Enabled agents are deployed
            # 3. Disabled agents are removed from .claude/agents/
            # 4. MCP services and hooks are started
            try:
                # Use execvp to replace the current process with claude-mpm run
                # This ensures a clean transition from configurator to Claude MPM
                os.execvp("claude-mpm", ["claude-mpm", "run"])
            except Exception as e:
                self.console.print(
                    f"[yellow]Could not launch Claude MPM automatically: {e}[/yellow]"
                )
                self.console.print(
                    "[cyan]Please run 'claude-mpm' manually to start.[/cyan]"
                )
                Prompt.ask("Press Enter to continue")
                return True

            # This line will never be reached if execvp succeeds
            return True

        except Exception as e:
            self.console.print(f"[red]Error saving configuration: {e}[/red]")
            Prompt.ask("Press Enter to continue")
            return False

    def save_all_configuration(self) -> bool:
        """Save all configuration changes across all contexts.

        Returns:
            bool: True if all saves successful, False otherwise
        """
        try:
            # 1. Save any pending agent changes
            if self.agent_manager and self.agent_manager.has_pending_changes():
                self.agent_manager.commit_deferred_changes()
                self.console.print("[green]✓ Agent changes saved[/green]")

            # 2. Save configuration file
            config = Config()

            # Determine config file path based on scope
            if self.current_scope == "project":
                config_file = self.project_dir / ".claude-mpm" / "configuration.yaml"
            else:
                config_file = Path.home() / ".claude-mpm" / "configuration.yaml"

            config_file.parent.mkdir(parents=True, exist_ok=True)

            # Save with suppressed logging to avoid duplicate messages
            root_logger = logging.getLogger("claude_mpm")
            original_level = root_logger.level
            root_logger.setLevel(logging.WARNING)

            try:
                config.save(config_file, format="yaml")
            finally:
                root_logger.setLevel(original_level)

            self.console.print(f"[green]✓ Configuration saved to {config_file}[/green]")
            return True

        except Exception as e:
            self.console.print(f"[red]✗ Error saving configuration: {e}[/red]")
            import traceback

            traceback.print_exc()
            return False
