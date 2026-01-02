"""
Agent/Skill Reconciliation CLI Command

Shows the reconciliation view between configured and deployed agents/skills,
and performs reconciliation (deploy missing, remove unneeded).

Usage:
    claude-mpm agents reconcile [--dry-run] [--show-only]
    claude-mpm skills reconcile [--dry-run] [--show-only]
"""

from pathlib import Path

from rich.console import Console
from rich.table import Table

from ...core.unified_config import UnifiedConfig
from ...services.agents.deployment.deployment_reconciler import (
    DeploymentReconciler,
    ReconciliationState,
)
from ..shared import BaseCommand, CommandResult


class AgentsReconcileCommand(BaseCommand):
    """CLI command for agent reconciliation."""

    def __init__(self):
        super().__init__("agents-reconcile")
        self.console = Console()

    def run(self, args) -> CommandResult:
        """Execute reconciliation."""
        # Load config
        config = UnifiedConfig()
        reconciler = DeploymentReconciler(config)

        # Get project path
        project_path = Path(getattr(args, "project_path", "."))

        # Show current state
        if getattr(args, "show_only", False) or getattr(args, "dry_run", False):
            return self._show_reconciliation_view(reconciler, project_path)

        # Perform reconciliation
        return self._reconcile_agents(reconciler, project_path)

    def _show_reconciliation_view(
        self, reconciler: DeploymentReconciler, project_path: Path
    ) -> CommandResult:
        """Show reconciliation view without making changes."""
        view = reconciler.get_reconciliation_view(project_path)
        agent_state = view["agents"]
        skill_state = view["skills"]

        # Display agents table
        self.console.print(
            "\n[bold blue]═══ Agent Reconciliation View ═══[/bold blue]\n"
        )
        agent_table = self._build_reconciliation_table(agent_state, "Agent")
        self.console.print(agent_table)

        # Display skills table
        self.console.print(
            "\n[bold blue]═══ Skill Reconciliation View ═══[/bold blue]\n"
        )
        skill_table = self._build_reconciliation_table(skill_state, "Skill")
        self.console.print(skill_table)

        # Show summary
        self._show_summary(agent_state, skill_state)

        return CommandResult.success_result("Reconciliation view displayed")

    def _build_reconciliation_table(
        self, state: ReconciliationState, item_type: str
    ) -> Table:
        """Build Rich table for reconciliation state."""
        table = Table(title=f"{item_type} Deployment Status")

        table.add_column(f"{item_type}", style="cyan", no_wrap=True)
        table.add_column("Configured", style="green")
        table.add_column("Deployed", style="yellow")
        table.add_column("Action", style="magenta")

        # All items to consider
        all_items = state.configured | state.deployed | state.cached

        for item_id in sorted(all_items):
            configured = "✓" if item_id in state.configured else "✗"
            deployed = "✓" if item_id in state.deployed else "✗"

            # Determine action
            if item_id in state.to_deploy:
                if item_id in state.cached:
                    action = "Will deploy"
                else:
                    action = "[red]Missing in cache![/red]"
            elif item_id in state.to_remove:
                action = "Will remove"
            elif item_id in state.unchanged:
                action = "-"
            elif item_id in state.cached and item_id not in state.configured:
                action = "[dim]Available (not configured)[/dim]"
            else:
                action = "-"

            table.add_row(item_id, configured, deployed, action)

        return table

    def _show_summary(
        self, agent_state: ReconciliationState, skill_state: ReconciliationState
    ) -> None:
        """Show reconciliation summary."""
        self.console.print("\n[bold]Summary:[/bold]")

        # Agents
        self.console.print("\nAgents:")
        self.console.print(f"  Configured: {len(agent_state.configured)}")
        self.console.print(f"  Deployed: {len(agent_state.deployed)}")
        self.console.print(f"  To deploy: {len(agent_state.to_deploy)}")
        self.console.print(f"  To remove: {len(agent_state.to_remove)}")
        self.console.print(f"  Unchanged: {len(agent_state.unchanged)}")

        # Skills
        self.console.print("\nSkills:")
        self.console.print(f"  Configured: {len(skill_state.configured)}")
        self.console.print(f"  Deployed: {len(skill_state.deployed)}")
        self.console.print(f"  To deploy: {len(skill_state.to_deploy)}")
        self.console.print(f"  To remove: {len(skill_state.to_remove)}")
        self.console.print(f"  Unchanged: {len(skill_state.unchanged)}")

        # Show next steps
        if agent_state.to_deploy or skill_state.to_deploy:
            self.console.print(
                "\n[yellow]Run without --show-only to perform deployment[/yellow]"
            )

    def _reconcile_agents(
        self, reconciler: DeploymentReconciler, project_path: Path
    ) -> CommandResult:
        """Perform agent and skill reconciliation."""
        # Show current state first
        self._show_reconciliation_view(reconciler, project_path)

        self.console.print("\n[bold blue]Performing reconciliation...[/bold blue]\n")

        # Reconcile agents
        self.console.print("[cyan]Reconciling agents...[/cyan]")
        agent_result = reconciler.reconcile_agents(project_path)

        if agent_result.deployed:
            self.console.print(
                f"  [green]✓ Deployed: {', '.join(agent_result.deployed)}[/green]"
            )
        if agent_result.removed:
            self.console.print(
                f"  [yellow]✓ Removed: {', '.join(agent_result.removed)}[/yellow]"
            )
        if agent_result.errors:
            for error in agent_result.errors:
                self.console.print(f"  [red]✗ {error}[/red]")

        # Reconcile skills
        self.console.print("\n[cyan]Reconciling skills...[/cyan]")
        skill_result = reconciler.reconcile_skills(project_path)

        if skill_result.deployed:
            self.console.print(
                f"  [green]✓ Deployed: {', '.join(skill_result.deployed)}[/green]"
            )
        if skill_result.removed:
            self.console.print(
                f"  [yellow]✓ Removed: {', '.join(skill_result.removed)}[/yellow]"
            )
        if skill_result.errors:
            for error in skill_result.errors:
                self.console.print(f"  [red]✗ {error}[/red]")

        # Final summary
        total_errors = len(agent_result.errors) + len(skill_result.errors)
        if total_errors == 0:
            self.console.print("\n[bold green]✓ Reconciliation complete![/bold green]")
            return CommandResult.success_result("Reconciliation successful")
        self.console.print(
            f"\n[bold yellow]⚠ Reconciliation complete with {total_errors} errors[/bold yellow]"
        )
        return CommandResult.error_result(f"Reconciliation had {total_errors} errors")


class SkillsReconcileCommand(AgentsReconcileCommand):
    """CLI command for skill reconciliation (alias to agents reconcile)."""

    def __init__(self):
        BaseCommand.__init__(self, "skills-reconcile")
        self.console = Console()
