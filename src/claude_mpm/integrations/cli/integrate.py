"""Integration CLI commands (ISS-0011, ISS-0013).

Provides CLI commands for managing API integrations:
- list: Show available and installed integrations
- add: Install an integration from catalog
- remove: Uninstall an integration
- status: Check integration health
- call: Execute an integration operation
- validate: Validate integration manifest
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console
from rich.table import Table

from ..catalog import CATALOG_DIR
from ..core.manifest import IntegrationManifest

console = Console()


@dataclass
class InstalledIntegration:
    """Represents an installed integration."""

    name: str
    version: str
    path: Path
    scope: str  # 'project' or 'user'


class IntegrationManager:
    """Manages integration lifecycle: install, remove, status, execute.

    Handles both project-level (.claude/integrations/) and user-level
    (~/.claude-mpm/integrations/) installations.
    """

    def __init__(self, project_dir: Path | None = None) -> None:
        """Initialize manager with optional project directory.

        Args:
            project_dir: Project root directory. If None, uses current directory.
        """
        self.project_dir = project_dir or Path.cwd()
        self.catalog_dir = CATALOG_DIR
        self.project_integrations = self.project_dir / ".claude" / "integrations"
        self.user_integrations = Path.home() / ".claude-mpm" / "integrations"

    def list_available(self) -> list[dict[str, Any]]:
        """List all integrations available in the catalog.

        Returns:
            List of integration metadata dictionaries.
        """
        available: list[dict[str, Any]] = []

        for item in self.catalog_dir.iterdir():
            if not item.is_dir():
                continue
            manifest_path = item / "integration.yaml"
            if not manifest_path.exists():
                continue

            try:
                with manifest_path.open() as f:
                    data = yaml.safe_load(f)
                available.append(
                    {
                        "name": data.get("name", item.name),
                        "version": data.get("version", "unknown"),
                        "description": data.get("description", ""),
                        "path": str(manifest_path),
                    }
                )
            except Exception:  # nosec B112
                continue

        return sorted(available, key=lambda x: x["name"])

    def list_installed(self) -> list[InstalledIntegration]:
        """List all installed integrations (project and user scope).

        Returns:
            List of InstalledIntegration objects.
        """
        installed: list[InstalledIntegration] = []

        # Check project-level installations
        if self.project_integrations.exists():
            for item in self.project_integrations.iterdir():
                manifest_path = item / "integration.yaml"
                if manifest_path.exists():
                    try:
                        with manifest_path.open() as f:
                            data = yaml.safe_load(f)
                        installed.append(
                            InstalledIntegration(
                                name=data.get("name", item.name),
                                version=data.get("version", "unknown"),
                                path=item,
                                scope="project",
                            )
                        )
                    except Exception:  # nosec B112
                        continue

        # Check user-level installations
        if self.user_integrations.exists():
            for item in self.user_integrations.iterdir():
                manifest_path = item / "integration.yaml"
                if manifest_path.exists():
                    try:
                        with manifest_path.open() as f:
                            data = yaml.safe_load(f)
                        installed.append(
                            InstalledIntegration(
                                name=data.get("name", item.name),
                                version=data.get("version", "unknown"),
                                path=item,
                                scope="user",
                            )
                        )
                    except Exception:  # nosec B112
                        continue

        return sorted(installed, key=lambda x: (x.scope, x.name))

    def add(self, name: str, scope: str = "project") -> bool:
        """Install an integration from the catalog.

        Args:
            name: Integration name from catalog.
            scope: Installation scope ('project' or 'user').

        Returns:
            True if installation succeeded, False otherwise.
        """
        # Find in catalog
        source_dir = self.catalog_dir / name
        if not source_dir.exists():
            console.print(f"[red]Integration '{name}' not found in catalog[/red]")
            return False

        manifest_path = source_dir / "integration.yaml"
        if not manifest_path.exists():
            console.print("[red]Invalid integration: missing manifest[/red]")
            return False

        # Determine target directory
        if scope == "project":
            target_dir = self.project_integrations / name
        else:
            target_dir = self.user_integrations / name

        # Check if already installed
        if target_dir.exists():
            console.print(
                f"[yellow]Integration '{name}' already installed at {scope} level[/yellow]"
            )
            return False

        # Create parent directory and copy
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, target_dir)

        console.print(f"[green]Installed '{name}' to {scope} scope[/green]")
        return True

    def remove(self, name: str, scope: str | None = None) -> bool:
        """Remove an installed integration.

        Args:
            name: Integration name.
            scope: Specific scope to remove from. If None, removes from first found.

        Returns:
            True if removal succeeded, False otherwise.
        """
        # Find the integration
        project_path = self.project_integrations / name
        user_path = self.user_integrations / name

        if scope == "project":
            target = project_path if project_path.exists() else None
        elif scope == "user":
            target = user_path if user_path.exists() else None
        else:
            # Remove from project first, then user
            target = project_path if project_path.exists() else None
            if not target:
                target = user_path if user_path.exists() else None

        if not target:
            console.print(f"[red]Integration '{name}' not installed[/red]")
            return False

        shutil.rmtree(target)
        console.print(f"[green]Removed '{name}'[/green]")
        return True

    def status(self, name: str) -> dict[str, Any]:
        """Get status of an installed integration.

        Args:
            name: Integration name.

        Returns:
            Status dictionary with health check results.
        """
        # Find installation
        installed = self.list_installed()
        integration = next((i for i in installed if i.name == name), None)

        if not integration:
            return {"installed": False, "error": f"Integration '{name}' not installed"}

        # Load manifest
        manifest_path = integration.path / "integration.yaml"
        try:
            manifest = IntegrationManifest.from_yaml(manifest_path)
        except Exception as e:
            return {"installed": True, "healthy": False, "error": str(e)}

        return {
            "installed": True,
            "name": manifest.name,
            "version": manifest.version,
            "scope": integration.scope,
            "path": str(integration.path),
            "operations": len(manifest.operations),
            "healthy": True,  # Would run actual health check with credentials
        }

    def call(
        self, name: str, operation: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute an integration operation.

        Args:
            name: Integration name.
            operation: Operation name.
            params: Operation parameters.

        Returns:
            Result dictionary with response or error.
        """
        # Find installation
        installed = self.list_installed()
        integration = next((i for i in installed if i.name == name), None)

        if not integration:
            return {"success": False, "error": f"Integration '{name}' not installed"}

        # Load manifest
        manifest_path = integration.path / "integration.yaml"
        try:
            manifest = IntegrationManifest.from_yaml(manifest_path)
        except Exception as e:
            return {"success": False, "error": f"Failed to load manifest: {e}"}

        # Find operation
        op = manifest.get_operation(operation)
        if not op:
            return {
                "success": False,
                "error": f"Operation '{operation}' not found",
                "available": [o.name for o in manifest.operations],
            }

        # Return operation info (actual execution requires IntegrationClient)
        return {
            "success": True,
            "integration": name,
            "operation": operation,
            "endpoint": op.endpoint,
            "method": op.type,
            "params": params or {},
            "note": "Use IntegrationClient for actual API execution",
        }

    def validate(self, path: Path) -> list[str]:
        """Validate an integration manifest.

        Args:
            path: Path to integration directory or manifest file.

        Returns:
            List of validation errors. Empty if valid.
        """
        if path.is_dir():
            path = path / "integration.yaml"

        if not path.exists():
            return [f"Manifest not found: {path}"]

        try:
            manifest = IntegrationManifest.from_yaml(path)
            return manifest.validate()
        except Exception as e:
            return [f"Failed to parse manifest: {e}"]


# CLI Commands


@click.group("integrate")
def manage_integrations() -> None:
    """Manage API integrations."""


@manage_integrations.command("list")
@click.option("--available", "-a", is_flag=True, help="Show available integrations")
@click.option("--installed", "-i", is_flag=True, help="Show installed integrations")
def list_cmd(available: bool, installed: bool) -> None:
    """List integrations (default: both available and installed)."""
    manager = IntegrationManager()

    # Default to showing both
    if not available and not installed:
        available = installed = True

    if available:
        console.print("\n[bold]Available Integrations[/bold]")
        items = manager.list_available()
        if items:
            table = Table()
            table.add_column("Name", style="cyan")
            table.add_column("Version")
            table.add_column("Description")
            for item in items:
                table.add_row(item["name"], item["version"], item["description"])
            console.print(table)
        else:
            console.print("[dim]No integrations in catalog[/dim]")

    if installed:
        console.print("\n[bold]Installed Integrations[/bold]")
        items = manager.list_installed()
        if items:
            table = Table()
            table.add_column("Name", style="cyan")
            table.add_column("Version")
            table.add_column("Scope")
            table.add_column("Path")
            for item in items:
                table.add_row(item.name, item.version, item.scope, str(item.path))
            console.print(table)
        else:
            console.print("[dim]No integrations installed[/dim]")


@manage_integrations.command("add")
@click.argument("name")
@click.option(
    "--scope",
    "-s",
    type=click.Choice(["project", "user"]),
    default="project",
    help="Installation scope",
)
def add_cmd(name: str, scope: str) -> None:
    """Install an integration from the catalog."""
    manager = IntegrationManager()
    manager.add(name, scope)


@manage_integrations.command("remove")
@click.argument("name")
@click.option(
    "--scope",
    "-s",
    type=click.Choice(["project", "user"]),
    help="Specific scope to remove from",
)
def remove_cmd(name: str, scope: str | None) -> None:
    """Remove an installed integration."""
    manager = IntegrationManager()
    manager.remove(name, scope)


@manage_integrations.command("status")
@click.argument("name")
def status_cmd(name: str) -> None:
    """Check status of an installed integration."""
    manager = IntegrationManager()
    status = manager.status(name)

    if not status.get("installed"):
        console.print(f"[red]{status.get('error')}[/red]")
        return

    console.print(f"\n[bold]{status['name']}[/bold] v{status['version']}")
    console.print(f"  Scope: {status['scope']}")
    console.print(f"  Path: {status['path']}")
    console.print(f"  Operations: {status['operations']}")

    if status.get("healthy"):
        console.print("  Status: [green]healthy[/green]")
    else:
        console.print(f"  Status: [red]unhealthy[/red] - {status.get('error')}")


@manage_integrations.command("call")
@click.argument("name")
@click.argument("operation")
@click.option("--param", "-p", multiple=True, help="Parameters as key=value")
def call_cmd(name: str, operation: str, param: tuple[str, ...]) -> None:
    """Execute an integration operation."""
    manager = IntegrationManager()

    # Parse parameters
    params: dict[str, str] = {}
    for p in param:
        if "=" in p:
            key, value = p.split("=", 1)
            params[key] = value

    result = manager.call(name, operation, params)

    if result.get("success"):
        console.print(f"[green]Operation: {result['operation']}[/green]")
        console.print(f"  Endpoint: {result.get('endpoint')}")
        console.print(f"  Method: {result.get('method')}")
        if result.get("note"):
            console.print(f"  [dim]{result['note']}[/dim]")
    else:
        console.print(f"[red]Error: {result.get('error')}[/red]")
        if result.get("available"):
            console.print(f"  Available: {', '.join(result['available'])}")


@manage_integrations.command("validate")
@click.argument("path", type=click.Path(exists=True))
def validate_cmd(path: str) -> None:
    """Validate an integration manifest."""
    manager = IntegrationManager()
    errors = manager.validate(Path(path))

    if errors:
        console.print("[red]Validation errors:[/red]")
        for error in errors:
            console.print(f"  - {error}")
    else:
        console.print("[green]Manifest is valid[/green]")
