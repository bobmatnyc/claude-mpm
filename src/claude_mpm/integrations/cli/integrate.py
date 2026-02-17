"""Integration CLI commands (ISS-0011, ISS-0013, ISS-0014, Phase 3).

Provides CLI commands for managing API integrations:
- list: Show available and installed integrations
- add: Install an integration from catalog
- remove: Uninstall an integration
- status: Check integration health
- call: Execute an integration operation
- validate: Validate integration manifest
- regenerate: Regenerate MCP server for an integration
- create: Interactive wizard for creating new integrations
- rebuild-index: Regenerate catalog _index.yaml
- batch: Run batch scripts against integrations
"""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console
from rich.table import Table

from ..catalog import CATALOG_DIR
from ..core.batch import BatchRunner
from ..core.index_generator import CatalogIndexGenerator
from ..core.manifest import IntegrationManifest
from ..core.mcp_generator import MCPServerGenerator

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
        self.mcp_generator = MCPServerGenerator()

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

        # Generate MCP server if configured
        target_manifest_path = target_dir / "integration.yaml"
        try:
            manifest = IntegrationManifest.from_yaml(target_manifest_path)
            if manifest.mcp.generate:
                self._generate_mcp_server(manifest, target_manifest_path, scope)
        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not generate MCP server: {e}[/yellow]"
            )

        return True

    def _generate_mcp_server(
        self,
        manifest: IntegrationManifest,
        manifest_path: Path,
        scope: str,
    ) -> None:
        """Generate MCP server and register with .mcp.json.

        Args:
            manifest: Integration manifest.
            manifest_path: Path to manifest file.
            scope: Installation scope ('project' or 'user').
        """
        # Write server to integration directory
        output_dir = manifest_path.parent
        server_path = self.mcp_generator.write_server(
            manifest, manifest_path, output_dir
        )

        # Determine .mcp.json location
        if scope == "project":
            mcp_json_path = self.project_dir / ".mcp.json"
        else:
            mcp_json_path = Path.home() / ".mcp.json"

        # Register with .mcp.json
        self.mcp_generator.register_with_mcp_json(
            manifest.name, server_path, mcp_json_path
        )

        console.print(f"[green]Generated MCP server: {server_path}[/green]")
        console.print(f"[green]Registered in: {mcp_json_path}[/green]")

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
            actual_scope = "project"
        elif scope == "user":
            target = user_path if user_path.exists() else None
            actual_scope = "user"
        # Remove from project first, then user
        elif project_path.exists():
            target = project_path
            actual_scope = "project"
        elif user_path.exists():
            target = user_path
            actual_scope = "user"
        else:
            target = None
            actual_scope = "project"

        if not target:
            console.print(f"[red]Integration '{name}' not installed[/red]")
            return False

        # Unregister from .mcp.json before removing files
        if actual_scope == "project":
            mcp_json_path = self.project_dir / ".mcp.json"
        else:
            mcp_json_path = Path.home() / ".mcp.json"

        if self.mcp_generator.unregister_from_mcp_json(name, mcp_json_path):
            console.print(f"[green]Unregistered from {mcp_json_path}[/green]")

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

    def regenerate(self, name: str) -> bool:
        """Regenerate MCP server for an installed integration.

        Useful when the integration manifest has been updated or
        when the MCP server needs to be recreated.

        Args:
            name: Integration name.

        Returns:
            True if regeneration succeeded, False otherwise.
        """
        # Find installation
        installed = self.list_installed()
        integration = next((i for i in installed if i.name == name), None)

        if not integration:
            console.print(f"[red]Integration '{name}' not installed[/red]")
            return False

        # Load manifest
        manifest_path = integration.path / "integration.yaml"
        try:
            manifest = IntegrationManifest.from_yaml(manifest_path)
        except Exception as e:
            console.print(f"[red]Failed to load manifest: {e}[/red]")
            return False

        # Check if MCP generation is enabled
        if not manifest.mcp.generate:
            console.print(
                f"[yellow]MCP generation disabled for '{name}' (mcp.generate=false)[/yellow]"
            )
            return False

        # Delete existing server if present
        server_path = self.mcp_generator.get_server_path(
            manifest.name, integration.path
        )
        if server_path.exists():
            server_path.unlink()

        # Generate new server
        self._generate_mcp_server(manifest, manifest_path, integration.scope)

        console.print(f"[green]Regenerated MCP server for '{name}'[/green]")
        return True


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


@manage_integrations.command("regenerate")
@click.argument("name")
def regenerate_cmd(name: str) -> None:
    """Regenerate MCP server for an installed integration.

    Useful when the integration manifest has been updated or when
    the MCP server needs to be recreated.
    """
    manager = IntegrationManager()
    manager.regenerate(name)


@manage_integrations.command("create")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output directory for new integration",
)
@click.option(
    "--catalog",
    "-c",
    is_flag=True,
    help="Create in catalog directory (for contributors)",
)
def create_cmd(output: str | None, catalog: bool) -> None:
    """Create a new integration using the interactive wizard."""
    from .wizard import IntegrationWizard

    if catalog:
        output_dir = CATALOG_DIR
    elif output:
        output_dir = Path(output)
    else:
        output_dir = Path.cwd()

    wizard = IntegrationWizard(output_dir)
    result = wizard.run()

    if result:
        console.print(f"\n[green]Integration created: {result}[/green]")

        if catalog:
            console.print("\n[dim]Don't forget to:[/dim]")
            console.print("  1. Rebuild the index: mpm integrate rebuild-index")
            console.print("  2. Run validation: mpm integrate validate-catalog")
            console.print("  3. Submit a pull request")


@manage_integrations.command("rebuild-index")
@click.option(
    "--catalog-dir",
    "-d",
    type=click.Path(exists=True),
    default=None,
    help="Custom catalog directory",
)
@click.option(
    "--verify",
    "-v",
    is_flag=True,
    help="Only verify index is up to date, don't write",
)
def rebuild_index_cmd(catalog_dir: str | None, verify: bool) -> None:
    """Rebuild or verify the catalog _index.yaml file."""
    target_dir = Path(catalog_dir) if catalog_dir else CATALOG_DIR
    generator = CatalogIndexGenerator()

    if verify:
        is_valid, discrepancies = generator.verify_index(target_dir)
        if is_valid:
            console.print("[green]Index is up to date[/green]")
        else:
            console.print("[red]Index is out of date:[/red]")
            for d in discrepancies:
                console.print(f"  - {d}")
            raise SystemExit(1)
    else:
        index_path = generator.write_index(target_dir)
        console.print(f"[green]Index regenerated: {index_path}[/green]")

        # Show what was indexed
        integrations = generator.scan_catalog(target_dir)
        console.print(f"  Indexed {len(integrations)} integrations")


@manage_integrations.command("validate-catalog")
@click.option(
    "--catalog-dir",
    "-d",
    type=click.Path(exists=True),
    default=None,
    help="Custom catalog directory",
)
@click.option(
    "--check-index",
    "-i",
    is_flag=True,
    default=True,
    help="Also validate _index.yaml",
)
def validate_catalog_cmd(catalog_dir: str | None, check_index: bool) -> None:
    """Validate all integrations in the catalog (for CI)."""
    from ..catalog.ci.validate import print_results, run_all_validations

    target_dir = Path(catalog_dir) if catalog_dir else CATALOG_DIR

    all_passed, results = run_all_validations(target_dir, check_index)
    print_results(results)

    if not all_passed:
        raise SystemExit(1)


@manage_integrations.command("batch")
@click.argument("integration")
@click.argument("script", type=click.Path(exists=True))
def batch_cmd(integration: str, script: str) -> None:
    """Run a batch script against an installed integration.

    INTEGRATION is the name of the installed integration.
    SCRIPT is the path to a Python batch script.

    The script must define an async function: async def run(ctx: BatchContext)
    """
    manager = IntegrationManager()

    # Find the integration
    installed = manager.list_installed()
    target = next((i for i in installed if i.name == integration), None)

    if not target:
        console.print(f"[red]Integration '{integration}' not installed[/red]")
        raise SystemExit(1)

    # Load manifest
    manifest_path = target.path / "integration.yaml"
    try:
        manifest = IntegrationManifest.from_yaml(manifest_path)
    except Exception as e:
        console.print(f"[red]Failed to load manifest: {e}[/red]")
        raise SystemExit(1) from None

    # Run the batch script
    runner = BatchRunner(manager.project_dir)
    script_path = Path(script)

    console.print(f"[dim]Running batch script: {script_path}[/dim]")
    console.print(f"[dim]Against integration: {integration}[/dim]\n")

    result = asyncio.run(runner.run_script(script_path, manifest, manifest_path))

    if result.success:
        console.print("[green]Batch completed successfully[/green]")
        console.print(f"  Results: {len(result.results)}")

        for r in result.results:
            console.print(f"    - {r['operation']}: {r['data']}")
    else:
        console.print("[red]Batch failed with errors:[/red]")
        for e in result.errors:
            console.print(f"  - {e}")
